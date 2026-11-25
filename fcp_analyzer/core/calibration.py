"""Level calibration and frequency weighting.

Calibration follows Lã et al. (2023): a steady 1 kHz tone is recorded and its SPL
at the microphone is read on a sound level meter. Then

    cal_offset_db = SPL_ref - 10*log10(mean square of the recorded tone)

so that ``10*log10(power) + cal_offset_db`` is in dB SPL. Levels are then
normalised to 30 cm with ``20*log10(d/30)`` (d = mouth-to-microphone distance).
"""
from __future__ import annotations

import numpy as np
from scipy import signal


def weighting_sos(fs: float, kind: str = "C") -> np.ndarray | None:
    """IEC 61672 A/C weighting as second-order sections (bilinear transform)."""
    kind = kind.upper()
    if kind == "Z":
        return None
    f1, f2, f3, f4 = 20.598997, 107.65265, 737.86223, 12194.217
    w = lambda f: 2 * np.pi * f
    if kind == "C":
        z = [0, 0]
        p = [-w(f1), -w(f1), -w(f4), -w(f4)]
    elif kind == "A":
        z = [0, 0, 0, 0]
        p = [-w(f1), -w(f1), -w(f2), -w(f3), -w(f4), -w(f4)]
    else:
        raise ValueError(kind)
    zd, pd, kd = signal.bilinear_zpk(z, p, 1.0, fs)
    sos = signal.zpk2sos(zd, pd, kd)
    _, h = signal.sosfreqz(sos, worN=[1000.0], fs=fs)
    sos[0, :3] /= abs(h[0])  # 0 dB at 1 kHz
    return sos


def mean_square(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.mean((x - x.mean()) ** 2)) if x.size else np.nan


def offset_from_reference(x_ref, spl_ref_db: float) -> float:
    """Calibration offset from a recorded reference tone of known SPL (Z-weighted)."""
    ms = mean_square(x_ref)
    if not np.isfinite(ms) or ms <= 0:
        raise ValueError("reference recording is silent")
    return float(spl_ref_db - 10.0 * np.log10(ms))


def distance_correction_db(distance_cm: float | None, ref_cm: float = 30.0) -> float:
    if not distance_cm:
        return 0.0
    return float(20.0 * np.log10(distance_cm / ref_cm))
