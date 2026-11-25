"""LTAS measures of Lã, Silva & Granqvist (2023), J Voice 37(4):631.e7-631.e15.

* Lmax(0-2), Lmax(2-5), Lmax(5-8): maximum LTAS level in each band.
* ΔL1 = Lmax(0-2) - Lmax(2-5)   (Hammarberg index)
* ΔL2 = Lmax(2-5) - Lmax(5-8)
* ΔL3 = ΔL1 - ΔL2
* ΔL4 = Lmax(0-2) - Lmax(5-8)
* FCP: a trendline is fitted to the LTAS between 1 and 5 kHz; FCP is the
  *maximum difference* between the LTAS and that trendline inside 2-4 kHz.
  The trendline is linear in log(frequency): in the paper's figures it is a
  straight line on a logarithmic frequency axis (Excel logarithmic trendline).
  The fit uses the LTAS points as sampled (uniform in Hz), as a spreadsheet
  trendline over the exported LTAS would.

The signs were checked against Table 2 of the paper (see tests/test_paper.py).

Buzz (experimental, NOT from the literature): the ``buzz_percentile`` of the
LTAS inside the buzz band minus the FCP trendline evaluated at the lower edge of
that band (the trendline is not extrapolated beyond the 1-5 kHz fit range).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np

from .settings import AnalysisSettings


@dataclass
class TrendLine:
    slope_per_log2: float   # dB per octave
    intercept: float        # dB at f = 1 Hz (log2 f = 0)

    def __call__(self, f):
        f = np.asarray(f, dtype=float)
        return self.slope_per_log2 * np.log2(f) + self.intercept


@dataclass
class LtasMeasures:
    fcp_db: float = np.nan
    fcp_freq_hz: float = np.nan
    peak_2_4_db: float = np.nan          # LTAS maximum inside 2-4 kHz
    peak_2_4_freq_hz: float = np.nan
    fcp_at_peak_db: float = np.nan       # v1.x definition (peak minus trend at the peak), for comparison
    trend_slope_db_oct: float = np.nan
    trend_intercept_db: float = np.nan
    lmax_0_2: float = np.nan
    lmax_2_5: float = np.nan
    lmax_5_8: float = np.nan
    dl1: float = np.nan
    dl2: float = np.nan
    dl3: float = np.nan
    dl4: float = np.nan
    buzz_db: float = np.nan
    buzz_freq_hz: float = np.nan

    def as_dict(self) -> dict:
        return asdict(self)


def fit_trend(freqs, ltas_db, band=(1000.0, 5000.0)) -> TrendLine | None:
    f = np.asarray(freqs, float)
    L = np.asarray(ltas_db, float)
    sel = (f >= band[0]) & (f <= band[1]) & np.isfinite(L) & (f > 0)
    if np.count_nonzero(sel) < 2:
        return None
    a, b = np.polyfit(np.log2(f[sel]), L[sel], 1)
    return TrendLine(float(a), float(b))


def band_max(freqs, L, lo, hi, *, include_hi=False):
    f = np.asarray(freqs, float)
    sel = (f >= lo) & ((f <= hi) if include_hi else (f < hi)) & np.isfinite(L)
    if not np.any(sel):
        return np.nan, np.nan
    i = int(np.argmax(np.where(sel, L, -np.inf)))
    return float(L[i]), float(f[i])


def deltas(l02, l25, l58):
    dl1 = l02 - l25
    dl2 = l25 - l58
    return dl1, dl2, dl1 - dl2, l02 - l58


def compute_measures(freqs, ltas_db, settings: AnalysisSettings | None = None) -> LtasMeasures:
    s = settings or AnalysisSettings()
    f = np.asarray(freqs, float)
    L = np.asarray(ltas_db, float)
    m = LtasMeasures()
    if f.size == 0 or not np.any(np.isfinite(L)):
        return m

    e0, e1, e2, e3 = s.band_edges_hz
    nyq_ok = f.max() >= e3 - 1e-6 or np.isclose(f.max(), e3, atol=s.bandwidth_hz)
    m.lmax_0_2, _ = band_max(f, L, max(e0, s.lmax_min_freq_hz), e1)
    if f.max() >= e2:
        m.lmax_2_5, _ = band_max(f, L, e1, e2)
    if f.max() >= e3 - s.bandwidth_hz:  # band reaches (almost) 8 kHz
        m.lmax_5_8, _ = band_max(f, L, e2, e3, include_hi=True)
    m.dl1, m.dl2, m.dl3, m.dl4 = deltas(m.lmax_0_2, m.lmax_2_5, m.lmax_5_8)

    trend = fit_trend(f, L, s.trend_band_hz)
    if trend is not None and f.max() >= s.fcp_band_hz[1] - 1e-6:
        m.trend_slope_db_oct = trend.slope_per_log2
        m.trend_intercept_db = trend.intercept
        lo, hi = s.fcp_band_hz
        sel = (f >= lo) & (f <= hi) & np.isfinite(L)
        if np.any(sel):
            fs_ = f[sel]
            diff = L[sel] - trend(fs_)
            i = int(np.argmax(diff))
            m.fcp_db = float(diff[i])
            m.fcp_freq_hz = float(fs_[i])
            j = int(np.argmax(L[sel]))
            m.peak_2_4_db = float(L[sel][j])
            m.peak_2_4_freq_hz = float(fs_[j])
            m.fcp_at_peak_db = float(L[sel][j] - trend(fs_[j]))

        b_lo, b_hi = s.buzz_band_hz
        selb = (f >= b_lo) & (f <= b_hi) & np.isfinite(L)
        if np.any(selb) and f.max() >= b_hi - s.bandwidth_hz:
            vals = L[selb]
            q = np.percentile(vals, s.buzz_percentile)
            k = int(np.argmin(np.abs(vals - q)))
            eval_f = min(max(b_lo, s.trend_band_hz[0]), s.trend_band_hz[1])
            m.buzz_db = float(vals[k] - trend(eval_f))
            m.buzz_freq_hz = float(f[selb][k])
    return m


# Display colours: visual bands only (NOT validated thresholds). Reference points
# from Lã et al. 2023: reading 4.2-5.3 dB, Fado-Canção 10 dB (3.7-14.3), opera baritones 14.8 and 20 dB.
FCP_COLOR_BANDS = [
    (5.0, "#3b82f6"),    # < 5 dB    blue
    (10.0, "#22c55e"),   # 5-10 dB   green
    (15.0, "#f59e0b"),   # 10-15 dB  amber
    (np.inf, "#ef4444"), # >= 15 dB  red
]


def fcp_color(fcp_db: float) -> str:
    if fcp_db is None or not np.isfinite(fcp_db):
        return "#9ca3af"
    for lim, col in FCP_COLOR_BANDS:
        if fcp_db < lim:
            return col
    return FCP_COLOR_BANDS[-1][1]
