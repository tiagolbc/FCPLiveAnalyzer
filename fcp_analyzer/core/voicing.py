"""Voiced/unvoiced decision with Praat's pitch tracker (via praat-parselmouth).

Lã et al. (2023) removed unvoiced segments before the LTAS. Here a frame is
voiced when Praat finds a pitch at the frame centre (nearest pitch frame).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class VoicingTrack:
    t0: float               # time (s, absolute) of the first pitch frame
    dt: float
    f0: np.ndarray          # Hz, 0 = unvoiced

    def _index(self, t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        t = np.asarray(t, dtype=float)
        if len(self.f0) == 0:
            return np.zeros(t.shape, int), np.zeros(t.shape, bool)
        i = np.rint((t - self.t0) / self.dt).astype(int)
        ok = (i >= 0) & (i < len(self.f0))
        return np.clip(i, 0, len(self.f0) - 1), ok

    def voiced_at(self, t) -> np.ndarray:
        i, ok = self._index(t)
        if len(self.f0) == 0:
            return ok
        return ok & (self.f0[i] > 0)

    def f0_at(self, t) -> np.ndarray:
        i, ok = self._index(t)
        if len(self.f0) == 0:
            return np.zeros(np.shape(t))
        return np.where(ok, self.f0[i], 0.0)


def compute_voicing(x: np.ndarray, fs: int, *, floor: float, ceiling: float,
                    time_step: float, t_offset: float = 0.0) -> VoicingTrack:
    import parselmouth

    x = np.asarray(x, dtype=float)
    min_len = int(3.0 / floor * fs) + 2
    if len(x) < min_len:
        return VoicingTrack(t_offset, time_step, np.zeros(0))
    snd = parselmouth.Sound(x, sampling_frequency=float(fs))
    pitch = snd.to_pitch_ac(time_step=time_step, pitch_floor=floor, pitch_ceiling=ceiling)
    f0 = np.asarray(pitch.selected_array["frequency"], dtype=float)
    xs = np.asarray(pitch.xs(), dtype=float)
    if len(xs) == 0:
        return VoicingTrack(t_offset, time_step, np.zeros(0))
    return VoicingTrack(float(xs[0]) + t_offset, float(pitch.dx), np.nan_to_num(f0))


def always_voiced_track(duration_s: float, dt: float = 0.01) -> VoicingTrack:
    n = int(np.ceil(duration_s / dt)) + 2
    return VoicingTrack(0.0, dt, np.full(n, 1.0))
