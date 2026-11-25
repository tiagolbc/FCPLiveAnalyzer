"""Analysis settings shared by file, batch and live analysis.

Every number that changes a result lives here, so that an exported CSV can
state exactly how it was produced (see ``AnalysisSettings.describe``).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json

# Engines -------------------------------------------------------------------
ENGINE_SOPRAN = "sopran"   # Hann window whose bandwidth = bandwidth_hz, power average
ENGINE_PRAAT = "praat"     # 40 ms Hann frames, power average, then mean power in bandwidth_hz bands

# Hann window bandwidth in FFT bins (Harris 1978, Table 1). Sopran shows
# "Blackman, 30 Hz -> window length 80 ms" in its manual, which matches the
# -6 dB definition (Blackman: 2.35 bins / 30 Hz = 78 ms). Default: "-6dB".
HANN_BW_BINS = {"-6dB": 2.00, "-3dB": 1.44, "enbw": 1.50}


@dataclass
class AnalysisSettings:
    # LTAS -------------------------------------------------------------------
    engine: str = ENGINE_SOPRAN
    bandwidth_hz: float = 350.0          # Lã et al. 2023: Hanning window, 350 Hz bandwidth
    bandwidth_definition: str = "-6dB"   # how bandwidth_hz maps to window length (sopran engine)
    measure_grid: str = "sopran"         # "sopran": measures on Sopran's FFT grid (nfft = next pow2 of the
                                         # window, ~172 Hz at 44.1 kHz); "fine": on the zero-padded ~20 Hz grid
    praat_frame_s: float = 0.040         # frame length of the Praat-like engine
    fmax_hz: float = 10000.0             # highest frequency kept in memory
    segment_s: float = 0.100             # time resolution of stored results (= live update rate)

    # Voicing (Praat pitch) ---------------------------------------------------
    voiced_only: bool = True             # Lã et al. 2023 removed unvoiced segments
    pitch_floor_hz: float = 60.0
    pitch_ceiling_hz: float = 1200.0     # singers reach far above Praat's 600 Hz default
    pitch_time_step_s: float = 0.010

    # FCP / band measures (Lã et al. 2023) -------------------------------------
    trend_band_hz: tuple = (1000.0, 5000.0)
    fcp_band_hz: tuple = (2000.0, 4000.0)
    band_edges_hz: tuple = (0.0, 2000.0, 5000.0, 8000.0)
    lmax_min_freq_hz: float = 50.0       # ignore DC / rumble in Lmax(0-2)

    # Experimental Buzz --------------------------------------------------------
    buzz_band_hz: tuple = (5000.0, 8000.0)
    buzz_percentile: float = 90.0

    # Windows ------------------------------------------------------------------
    window_s: float = 3.0                # sliding ("dynamic") FCP window

    # Calibration --------------------------------------------------------------
    cal_offset_db: float | None = None   # dB SPL = 10*log10(power) + cal_offset_db
    distance_cm: float | None = None     # mic-to-mouth distance; normalised to 30 cm
    ref_distance_cm: float = 30.0

    @property
    def calibrated(self) -> bool:
        return self.cal_offset_db is not None

    def level_offset_db(self) -> float:
        """Constant added to 10*log10(power): SPL calibration + distance normalisation."""
        off = 0.0
        if self.cal_offset_db is not None:
            off += float(self.cal_offset_db)
        if self.distance_cm:
            import math
            off += 20.0 * math.log10(float(self.distance_cm) / float(self.ref_distance_cm))
        return off

    def level_unit(self) -> str:
        if self.calibrated:
            return "dB SPL @30 cm" if self.distance_cm else "dB SPL"
        return "dB (rel. full scale)"

    def to_dict(self) -> dict:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, tuple):
                d[k] = list(v)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisSettings":
        base = cls()
        kw = {}
        for k, v in d.items():
            if hasattr(base, k):
                cur = getattr(base, k)
                kw[k] = tuple(v) if isinstance(cur, tuple) and isinstance(v, list) else v
        return cls(**kw)

    def describe(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
