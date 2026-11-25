"""Measures computed on analytic LTAS curves (no audio): exact expected values."""
import numpy as np
import pytest

from fcp_analyzer.core.metrics import compute_measures, fit_trend, deltas, fcp_color
from fcp_analyzer.core.settings import AnalysisSettings
from fcp_analyzer.synth import Envelope

F = np.arange(0, 10001, 10.0)
F[0] = 1.0
S = AnalysisSettings()


def test_pure_log_line_gives_zero_fcp():
    L = -12 * np.log2(F / 1000) - 20
    m = compute_measures(F, L, S)
    assert m.fcp_db == pytest.approx(0.0, abs=1e-9)
    assert m.trend_slope_db_oct == pytest.approx(-12.0, abs=1e-9)


@pytest.mark.parametrize("slope", [-18, -12, -6, 0, 3])
def test_tilt_invariance(slope):
    """Adding any tilt linear in log2(f) must not change FCP (the trendline absorbs it)."""
    base = Envelope(-10, [(3000, 15, 0.12)])
    tilted = Envelope(-10 + slope, [(3000, 15, 0.12)])
    m0 = compute_measures(F, base.db(F), S)
    m1 = compute_measures(F, tilted.db(F), S)
    assert m1.fcp_db == pytest.approx(m0.fcp_db, abs=1e-6)
    assert m1.fcp_freq_hz == pytest.approx(m0.fcp_freq_hz)


@pytest.mark.parametrize("gain", [-40, -6, 0, 12, 94])
def test_gain_invariance(gain):
    env = Envelope(-12, [(2900, 12, 0.1)])
    m0 = compute_measures(F, env.db(F), S)
    m1 = compute_measures(F, env.db(F) + gain, S)
    for k in ("fcp_db", "dl1", "dl2", "dl3", "dl4", "buzz_db"):
        assert getattr(m1, k) == pytest.approx(getattr(m0, k), abs=1e-9)
    assert m1.lmax_0_2 == pytest.approx(m0.lmax_0_2 + gain)


def test_fcp_is_max_difference_not_peak():
    """Peak of the LTAS at 2 kHz, but the largest excess over a falling trendline at 3.6 kHz.
    Lã et al.: 'the maximum difference was measured between this trendline and the LTAS'."""
    f = F
    L = -20 * np.log2(f / 1000)
    L = L + 2 * np.exp(-0.5 * ((f - 2050) / 60) ** 2)    # small bump near 2 kHz (LTAS peak there)
    L = L + 9 * np.exp(-0.5 * ((f - 3600) / 80) ** 2)    # larger excess at 3.6 kHz
    m = compute_measures(f, L, S)
    assert m.peak_2_4_freq_hz < 2200
    assert 3500 < m.fcp_freq_hz < 3700
    assert m.fcp_db > m.fcp_at_peak_db + 3


def test_trend_fit_matches_least_squares_on_log2():
    rng = np.random.default_rng(1)
    L = -9 * np.log2(F / 1000) + rng.normal(0, 2, F.size)
    t = fit_trend(F, L)
    sel = (F >= 1000) & (F <= 5000)
    a, b = np.polyfit(np.log2(F[sel]), L[sel], 1)
    assert t.slope_per_log2 == pytest.approx(a)
    assert t.intercept == pytest.approx(b)


def test_known_bump_height():
    """A narrow bump of h dB at 3 kHz on a log-line raises FCP by ~h minus the trend lift."""
    env = Envelope(-12, [(3000, 10, 0.05)])
    m = compute_measures(F, env.db(F), S)
    sel = (F >= 1000) & (F <= 5000)
    # analytic: fit over the bump curve gives a small lift; FCP = 10 - lift at 3 kHz
    a, b = np.polyfit(np.log2(F[sel]), env.db(F[sel]), 1)
    expected = env.db(3000.0) - (a * np.log2(3000.0) + b)
    assert m.fcp_db == pytest.approx(expected, abs=0.05)
    assert m.fcp_freq_hz == pytest.approx(3000, abs=10)
    assert 8.0 < m.fcp_db < 10.0


def test_band_maxima_and_delta_signs():
    L = np.full(F.shape, -60.0)
    L[(F > 400) & (F < 600)] = -20     # Lmax(0-2)
    L[(F > 2900) & (F < 3100)] = -40   # Lmax(2-5)
    L[(F > 6000) & (F < 6200)] = -55   # Lmax(5-8)
    m = compute_measures(F, L, S)
    assert (m.lmax_0_2, m.lmax_2_5, m.lmax_5_8) == (-20, -40, -55)
    assert m.dl1 == 20 and m.dl2 == 15 and m.dl3 == 5 and m.dl4 == 35


def test_dc_ignored_in_lmax_0_2():
    L = -12 * np.log2(F / 1000) - 20
    L[F < 40] = 50.0
    m = compute_measures(F, L, S)
    assert m.lmax_0_2 < 50


def test_buzz_experimental_rises_with_high_band_energy():
    base = Envelope(-12, [(3000, 10, 0.1)])
    hi = Envelope(-12, [(3000, 10, 0.1), (6500, 15, 0.1)])
    assert compute_measures(F, hi.db(F), S).buzz_db > compute_measures(F, base.db(F), S).buzz_db + 10


def test_short_spectrum_gives_nan_not_crash():
    f = np.arange(0, 3000, 25.0)
    m = compute_measures(f, -12 * np.log2(np.maximum(f, 1) / 1000), S)
    assert np.isnan(m.fcp_db) and np.isnan(m.lmax_5_8)
    m2 = compute_measures(np.array([]), np.array([]), S)
    assert np.isnan(m2.fcp_db)


def test_colors_are_display_bands():
    assert fcp_color(np.nan) == "#9ca3af"
    assert fcp_color(4.9) != fcp_color(5.0)
    assert fcp_color(25) == fcp_color(15)
