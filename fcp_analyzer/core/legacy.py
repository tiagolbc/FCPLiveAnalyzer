"""Verbatim copy of the v1.2.1 LTAS/FCP code, kept ONLY for comparison and
regression checks (``compare_v1`` in tools/). Do not use for new results.

Known issues fixed in 2.0 (see CHANGELOG): dB averaging of frames, maximum
(not power mean) inside 350 Hz bins, FCP taken at the LTAS peak instead of the
maximum LTAS-minus-trendline difference.
"""
import numpy as np
import parselmouth

# ---------------- Utilities ----------------
def _frame_to_db_spectrum_pm(snd_frame):
    """
    Convert a short Sound frame to magnitude spectrum in dB using Parselmouth/Praat.
    Returns (freqs_hz, spectrum_db).
    """
    spec = snd_frame.to_spectrum()
    freqs = spec.xs()
    vals = spec.values

    # Praat: vals.shape == (2, N) com partes real/imag separadas (dtype real).
    if vals.ndim == 2 and vals.shape[0] == 2:
        re = vals[0, :]
        im = vals[1, :]
        mag = np.hypot(re, im)  # sqrt(re^2 + im^2) → vetor (N,)
    else:
        # Fallback: caso venha 1D ou complexo, usa módulo direto
        mag = np.abs(vals).ravel()

    spectrum_db = 20.0 * np.log10(mag + 1e-12)  # evita -inf
    return freqs, spectrum_db

def _apply_distance_calibration_db(ltas_db, *, distance_cm=None, ref_cm=30.0, spl_offset_db=0.0):
    """
    Apply 30 cm distance normalization (+ optional SPL offset).
    Paper-level normalization: Δ = 20*log10(distance/ref_distance) + spl_offset_db
    Note: FCP (a relative metric) is invariant to constant dB shifts, but we apply
    this so LTAS levels are distance-normalized as in the article.
    """
    if distance_cm is None:
        return ltas_db
    delta = 20.0 * np.log10(max(distance_cm, 1e-6) / ref_cm) + float(spl_offset_db)
    return ltas_db + delta

# ---------------- LTAS (Praat-style) ----------------
def compute_ltas_parselmouth(
    y,
    fs,
    *,
    bandwidth_hz=350.0,
    win_len_s=0.040,
    hop_s=0.010,
    voiced_only=True,
    pitch_time_step_s=0.010,
    distance_cm=None,
    spl_offset_db=0.0,
):
    """
    LTAS as in the paper: average of per-frame dB spectra (40 ms Hann, 10 ms hop),
    optional voiced-only gating via Parselmouth Pitch (>0 Hz).
    Bins to the requested bandwidth (350 Hz) and returns (centers, LTAS dB),
    then applies 30 cm distance normalization (+ optional SPL offset).
    """
    if y is None or len(y) == 0:
        return np.array([]), np.array([])

    snd_full = parselmouth.Sound(y, fs)

    # ---- voiced gate (Pitch) ----
    voiced_mask_frames = None
    if voiced_only:
        pitch = snd_full.to_pitch(time_step=pitch_time_step_s)
        freqs_hz = pitch.selected_array['frequency']
        times_s  = pitch.xs()
        voiced_tf = freqs_hz > 0.0
        voiced_mask_frames = (times_s, voiced_tf)

    # ---- frame scan (40 ms / 10 ms, Hann) ----
    n_win = int(round(win_len_s * fs))
    n_hop = int(round(hop_s    * fs))
    if n_win <= 0 or n_hop <= 0 or n_win > len(y):
        return np.array([]), np.array([])

    window = np.hanning(n_win)

    frames_db = []
    ref_freqs = None

    def _is_voiced(frame_start):
        if not voiced_only:
            return True
        t_center = (frame_start + n_win * 0.5) / fs
        idx = int(round(t_center / pitch_time_step_s))
        idx = max(0, min(idx, len(voiced_mask_frames[1]) - 1))
        return bool(voiced_mask_frames[1][idx])

    i = 0
    N = len(y)
    while i + n_win <= N:
        if _is_voiced(i):
            seg = y[i:i + n_win] * window
            snd_frame = parselmouth.Sound(seg, fs)
            freqs, db_spec = _frame_to_db_spectrum_pm(snd_frame)
            if ref_freqs is None:
                ref_freqs = freqs
            else:
                if len(freqs) != len(ref_freqs):
                    db_spec = np.interp(ref_freqs, freqs, db_spec)
            frames_db.append(db_spec)
        i += n_hop

    if not frames_db:
        return np.array([]), np.array([])

    frames_db = np.stack(frames_db, axis=0)
    avg_db_spectrum = np.nanmean(frames_db, axis=0)
    freqs = ref_freqs

    # ---- 350 Hz binning (paper) ----
    max_freq = float(freqs[-1]) if len(freqs) > 0 else 0.0
    bins = np.arange(0.0, max_freq + bandwidth_hz, bandwidth_hz)
    ltas_vals = []
    for k in range(len(bins) - 1):
        lo, hi = bins[k], bins[k + 1]
        sel = (freqs >= lo) & (freqs < hi)
        if not np.any(sel):
            ltas_vals.append(np.nan)
        else:
            # Use the maximum within each 350 Hz bin on the averaged spectrum
            ltas_vals.append(np.nanmax(avg_db_spectrum[sel]))
    ltas = np.array(ltas_vals)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    good = ~np.isnan(ltas)
    freqs_ltas = bin_centers[good]
    ltas_db    = ltas[good]

    # ---- Apply 30 cm distance normalization (+ optional SPL offset) ----
    ltas_db = _apply_distance_calibration_db(
        ltas_db, distance_cm=distance_cm, ref_cm=30.0, spl_offset_db=spl_offset_db
    )

    return freqs_ltas, ltas_db

# ---------------- FCP on top of LTAS ----------------
def compute_fcp_praat_style(freqs, ltas):
    """
    Sopran-like:
      - Trendline: regressão linear de L(dB) ~ a*log2(f) + b em 1–5 kHz
      - FCP: pico(2–4 kHz) – trend(previsto no pico)
      - Bandas com limite superior inclusivo (… ≤ hi)
    """
    f = np.asarray(freqs, dtype=float)
    L = np.asarray(ltas,  dtype=float)

    def band_max(f_lo, f_hi, inclusive_hi=False):
        if inclusive_hi:
            idx = np.where((f >= f_lo) & (f <= f_hi))[0]
        else:
            idx = np.where((f >= f_lo) & (f <  f_hi))[0]
        return np.max(L[idx]) if len(idx) else np.nan

    # Picos por banda (para logs/relatórios)
    Lmax_0_2 = band_max(0,    2000, inclusive_hi=True)
    Lmax_2_5 = band_max(2000, 5000, inclusive_hi=True)
    Lmax_5_8 = band_max(5000, 8000, inclusive_hi=True)
    Lmax_2_4 = band_max(2000, 4000, inclusive_hi=True)

    # Regressão 1–5 kHz em log2(f)
    idx_tr = np.where((f >= 1000) & (f <= 5000))[0]
    if len(idx_tr) < 2:
        return Lmax_0_2, Lmax_2_5, Lmax_5_8, Lmax_2_4, np.nan, np.nan

    x_tr = np.log2(f[idx_tr])
    y_tr = L[idx_tr]
    a, b = np.polyfit(x_tr, y_tr, 1)  # dB ~ a*log2(Hz) + b

    # Pico em 2–4 kHz (inclui 4000 Hz)
    idx_24 = np.where((f >= 2000) & (f <= 4000))[0]
    if len(idx_24) == 0:
        return Lmax_0_2, Lmax_2_5, Lmax_5_8, Lmax_2_4, np.nan, np.nan

    y24 = L[idx_24]
    ipeak = int(np.argmax(y24))
    f_peak = float(f[idx_24][ipeak])

    trend_at_peak = float(a * np.log2(f_peak) + b)
    fcp = float(y24[ipeak] - trend_at_peak)

    return Lmax_0_2, Lmax_2_5, Lmax_5_8, Lmax_2_4, fcp, trend_at_peak




def legacy_global(y, fs):
    """v1.2.1 'Global FCP' (voiced-only, 40 ms / 10 ms, max in 350 Hz bins)."""
    freqs, ltas = compute_ltas_parselmouth(y, fs, bandwidth_hz=350.0, win_len_s=0.040, hop_s=0.010,
                                           voiced_only=True)
    if ltas.size == 0:
        return dict(fcp=np.nan)
    l02, l25, l58, l24, fcp, trend = compute_fcp_praat_style(freqs, ltas)
    return dict(freqs=freqs, ltas=ltas, fcp=fcp, Lmax_0_2=l02, Lmax_2_5=l25, Lmax_5_8=l58,
                Delta_0_2_2_5=l25 - l02, Delta_2_5_5_8=l58 - l25, Delta_0_2_5_8=l58 - l02)
