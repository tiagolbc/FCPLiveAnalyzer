# fcp_ltas.py
import numpy as np
from scipy.signal import get_window

def compute_ltas_like_praat(y, fs, bandwidth=350, win_len=0.04, hop_len=0.01):
    """
    Compute LTAS as average of dB spectra of short windows (like Praat).
    y: audio array
    fs: sample rate
    bandwidth: bin width (Hz)
    win_len: window length in seconds (default 40 ms)
    hop_len: hop size in seconds (default 10 ms)
    """
    n_win = int(win_len * fs)
    n_hop = int(hop_len * fs)
    window = np.hanning(n_win)
    frames_db = []
    for start in range(0, len(y) - n_win + 1, n_hop):
        segment = y[start:start + n_win] * window
        spectrum = np.abs(np.fft.rfft(segment))
        spectrum_db = 20 * np.log10(spectrum + 1e-12)
        frames_db.append(spectrum_db)
    if not frames_db:
        return np.array([]), np.array([])
    frames_db = np.stack(frames_db)
    avg_db_spectrum = np.mean(frames_db, axis=0)
    freqs = np.fft.rfftfreq(n_win, 1/fs)
    bins = np.arange(0, freqs[-1] + bandwidth, bandwidth)
    ltas = [np.max(avg_db_spectrum[(freqs >= bins[i]) & (freqs < bins[i+1])])
            for i in range(len(bins) - 1)]
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    return bin_centers, np.array(ltas)



def compute_fcp_praat_style(freqs, ltas):
    # Faixas
    def band_max(f_lo, f_hi):
        idx = np.where((freqs >= f_lo) & (freqs < f_hi))[0]
        return np.max(ltas[idx]) if len(idx) else np.nan

    Lmax_0_2 = band_max(0, 2000)
    Lmax_2_5 = band_max(2000, 5000)
    Lmax_5_8 = band_max(5000, 8000)
    Lmax_2_4 = band_max(2000, 4000)

    idx_1_5 = np.where((freqs >= 1000) & (freqs <= 5000))[0]
    x_trend = freqs[idx_1_5]
    y_trend = ltas[idx_1_5]
    m, b = np.polyfit(x_trend, y_trend, 1)

    # Trendline nos pontos do LTAS em 2-4kHz
    idx_2_4 = np.where((freqs >= 2000) & (freqs < 4000))[0]
    x_peak = freqs[idx_2_4]
    y_peak = ltas[idx_2_4]
    peak_rel = np.argmax(y_peak)
    f_peak = x_peak[peak_rel]
    trend_at_peak = m * f_peak + b
    fcp = y_peak[peak_rel] - trend_at_peak
    return Lmax_0_2, Lmax_2_5, Lmax_5_8, Lmax_2_4, fcp, trend_at_peak

def get_fcp_color(fcp):
    if fcp < 5:
        return '#1f77b4'  # blue
    elif fcp < 10:
        return '#2ca02c'  # green
    elif fcp < 15:
        return '#ff7f0e'  # orange
    else:
        return '#d62728'  # red