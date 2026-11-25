"""End-to-end checks on synthetic audio whose spectrum (and FCP) is known."""
import numpy as np
import pytest

from fcp_analyzer.core import AnalysisSettings, analyse_signal, LiveAnalyzer, compute_measures
from fcp_analyzer.core.spectral import make_config
from fcp_analyzer.synth import Envelope, shaped_noise, harmonic_phrase, sine, expected_ltas_noise

FS = 44100
CLUSTER = Envelope(-12, [(3000, 14, 0.10)], lowpass_hz=9500)       # strong formant cluster
SPEECHY = Envelope(-12, [(3000, 4, 0.10)], lowpass_hz=9500)        # weak cluster
FLAT = Envelope(-12, [], lowpass_hz=9500)


def _noise_settings(**kw):
    return AnalysisSettings(voiced_only=False, **kw)


@pytest.mark.parametrize("engine", ["sopran", "praat"])
@pytest.mark.parametrize("env", [CLUSTER, SPEECHY, FLAT], ids=["cluster", "speechy", "flat"])
def test_noise_fcp_matches_expected_ltas(engine, env):
    """Shaped noise: measured FCP equals the FCP of the analytically expected LTAS."""
    s = _noise_settings(engine=engine)
    x = shaped_noise(env, FS, 20.0, seed=3)
    a = analyse_signal(x, FS, s)
    cfg = make_config(FS, s)
    exp = compute_measures(*cfg.measure_view(expected_ltas_noise(env, cfg)), s)
    got = a.global_result.measures
    assert got.fcp_db == pytest.approx(exp.fcp_db, abs=0.5)
    assert got.dl1 == pytest.approx(exp.dl1, abs=0.6)
    assert got.dl2 == pytest.approx(exp.dl2, abs=0.6)
    assert got.dl4 == pytest.approx(exp.dl4, abs=0.6)


def test_cluster_bigger_than_speech_bigger_than_flat():
    s = _noise_settings()
    f = [analyse_signal(shaped_noise(e, FS, 10.0, seed=1), FS, s).global_result.measures.fcp_db
         for e in (CLUSTER, SPEECHY, FLAT)]
    assert f[0] > f[1] > f[2]
    assert f[2] < 1.5
    assert 9 < f[0] < 15


def test_flat_noise_ltas_is_flat_and_calibrated_band_level():
    """White noise of mean square s2: sopran band level = s2 * B_enbw/(fs/2) (Hann ENBW=1.5 bins)."""
    s = _noise_settings()
    rng = np.random.default_rng(0)
    x = rng.standard_normal(FS * 10) * 0.1
    a = analyse_signal(x, FS, s)
    cfg = a.proc.cfg
    L = a.global_result.ltas_db
    sel = (cfg.out_freqs > 500) & (cfg.out_freqs < 9000)
    assert np.ptp(L[sel]) < 1.0
    enbw = 1.5 * FS / cfg.win_len
    expected = 10 * np.log10(0.01 * enbw / (FS / 2))
    assert np.median(L[sel]) == pytest.approx(expected, abs=0.3)


def test_sine_reads_its_mean_square_in_sopran_engine():
    s = _noise_settings(measure_grid="fine")
    x = sine(1000, FS, 3.0, rms_dbfs=-20)
    a = analyse_signal(x, FS, s)
    L = a.global_result.ltas_db
    assert L.max() == pytest.approx(-20.0, abs=0.2)
    assert a.global_result.measures.lmax_0_2 == pytest.approx(-20.0, abs=0.2)


def test_harmonic_phrase_fcp_close_to_envelope():
    """Voiced harmonic phrase (male F0 range): FCP within 1.5 dB of the shaped-noise value."""
    s = AnalysisSettings()
    x = harmonic_phrase(CLUSTER, FS, 12.0, vibrato_cents=40)
    a = analyse_signal(x, FS, s)
    n = analyse_signal(shaped_noise(CLUSTER, FS, 12.0), FS, _noise_settings())
    assert a.global_result.voiced_s > 10
    assert a.global_result.measures.fcp_db == pytest.approx(n.global_result.measures.fcp_db, abs=1.5)
    assert abs(a.global_result.measures.fcp_freq_hz - 3000) < 300
    assert not any(c == "sustained" for c, _ in a.global_result.warnings)


def test_unvoiced_parts_are_excluded():
    """Voiced phrase with loud noise bursts in between: voiced-only LTAS ignores the noise."""
    s = AnalysisSettings()
    v = harmonic_phrase(CLUSTER, FS, 12.0, gap_s=0.25, level_dbfs=-20)
    t = np.arange(len(v)) / FS
    burst = (t % 0.6) > 0.6 - 0.22
    noise = shaped_noise(Envelope(0, [(6500, 10, 0.2)]), FS, 12.0, level_dbfs=-25)
    x = v + noise * burst
    clean = analyse_signal(v, FS, s).global_result.measures.fcp_db
    mixed = analyse_signal(x, FS, s).global_result.measures.fcp_db
    off = analyse_signal(x, FS, AnalysisSettings(voiced_only=False)).global_result.measures.fcp_db
    assert mixed == pytest.approx(clean, abs=1.0)
    assert abs(off - clean) > abs(mixed - clean)


@pytest.mark.parametrize("grid,tol", [("fine", 0.6), ("sopran", 1.0)])
@pytest.mark.parametrize("fs", [16000, 22050, 44100, 48000])
def test_sample_rate_independence(fs, grid, tol):
    """Fine grid: <0.6 dB. Sopran grid (spacing fs/nfft changes with fs): <1 dB."""
    s = _noise_settings(measure_grid=grid)
    ref = analyse_signal(shaped_noise(CLUSTER, 44100, 8.0), 44100, s).global_result.measures.fcp_db
    got = analyse_signal(shaped_noise(CLUSTER, fs, 8.0), fs, s).global_result.measures.fcp_db
    assert got == pytest.approx(ref, abs=tol)


def test_low_sample_rate_warns_and_drops_5_8():
    s = _noise_settings()
    a = analyse_signal(shaped_noise(CLUSTER, 11025, 6.0), 11025, s)
    codes = [c for c, _ in a.global_result.warnings]
    assert "low_fs" in codes
    assert np.isnan(a.global_result.measures.lmax_5_8)
    assert np.isfinite(a.global_result.measures.fcp_db)


def test_calibration_and_distance():
    x = sine(1000, FS, 4.0, rms_dbfs=-20)
    s = _noise_settings(cal_offset_db=94.0 + 20.0)   # this tone = 94 dB SPL
    g = analyse_signal(x, FS, s).global_result
    assert g.leq_c_db == pytest.approx(94.0, abs=0.1)
    assert g.ltas_db.max() == pytest.approx(94.0, abs=0.2)
    s2 = _noise_settings(cal_offset_db=114.0, distance_cm=15.0)
    g2 = analyse_signal(x, FS, s2).global_result
    assert g2.leq_c_db == pytest.approx(94.0 - 6.02, abs=0.1)
    assert g2.measures.fcp_db == pytest.approx(g.measures.fcp_db, abs=1e-6)


def test_windows_equal_direct_computation():
    s = _noise_settings(window_s=2.0)
    x = shaped_noise(CLUSTER, FS, 6.0)
    a = analyse_signal(x, FS, s)
    i = a.index_at(4.0)
    direct = analyse_signal(x[int(2.0 * FS): int(4.0 * FS)], FS, s).global_result.measures.fcp_db
    assert a.window_measures[i].fcp_db == pytest.approx(direct, abs=0.3)


def test_live_matches_file_analysis():
    s = AnalysisSettings()
    x = harmonic_phrase(CLUSTER, FS, 8.0, vibrato_cents=30)
    fa = analyse_signal(x, FS, s).global_result
    live = LiveAnalyzer(FS, s)
    blk = int(0.05 * FS)
    n_results = 0
    for i in range(0, len(x), blk):
        live.feed(x[i:i + blk])
        n_results += len(live.update())
    live.flush()
    g = live.global_result()
    assert n_results > 50
    assert g.voiced_s == pytest.approx(fa.voiced_s, rel=0.05)
    assert g.measures.fcp_db == pytest.approx(fa.measures.fcp_db, abs=0.5)
    assert g.measures.dl1 == pytest.approx(fa.measures.dl1, abs=0.5)
    assert len(live.audio()) == len(x)


def test_sustained_note_is_flagged():
    s = AnalysisSettings()
    x = harmonic_phrase(CLUSTER, FS, 6.0, f0_notes=(220.0,), vibrato_cents=50)
    codes = [c for c, _ in analyse_signal(x, FS, s).global_result.warnings]
    assert "sustained" in codes and "short_ltas" in codes


def test_clipping_is_flagged():
    x = np.clip(harmonic_phrase(CLUSTER, FS, 4.0, level_dbfs=-3) * 3, -1, 1)
    codes = [c for c, _ in analyse_signal(x, FS, AnalysisSettings()).global_result.warnings]
    assert "clipping" in codes


def test_silence_and_tiny_inputs_do_not_crash():
    s = AnalysisSettings()
    for x in (np.zeros(FS * 2), np.zeros(100), np.zeros(0)):
        a = analyse_signal(x, FS, s)
        assert np.isnan(a.global_result.measures.fcp_db)
    live = LiveAnalyzer(FS, s)
    live.feed(np.zeros(FS))
    live.update()
    live.flush()
    assert np.isnan(live.global_result().measures.fcp_db)


def test_praat_engine_matches_praat_to_ltas():
    """Praat-like engine vs Praat's own 'To Ltas: 350' on shaped noise (same band grid)."""
    import parselmouth
    from parselmouth.praat import call
    x = shaped_noise(CLUSTER, FS, 15.0, seed=7)
    a = analyse_signal(x, FS, _noise_settings(engine="praat"))
    ours = a.global_result.ltas_db
    ltas = call(parselmouth.Sound(x, FS), "To Ltas", 350.0)
    n = min(len(ours), int(call(ltas, "Get number of bins")))
    praat = np.array([call(ltas, "Get value in bin", i + 1) for i in range(n)])
    assert call(ltas, "Get frequency from bin number", 1) == pytest.approx(a.freqs[0])
    sel = (a.freqs[:n] > 300) & (a.freqs[:n] < 9000)
    d = ours[:n][sel] - praat[sel]
    assert np.ptp(d) < 0.6, d   # same shape up to a constant (Praat uses dB/Hz re 2e-5 Pa)
    ours_m = compute_measures(a.freqs[:n], ours[:n], a.settings)  # praat engine: all bands are used
    praat_m = compute_measures(a.freqs[:n], praat, a.settings)
    assert ours_m.fcp_db == pytest.approx(praat_m.fcp_db, abs=0.3)
