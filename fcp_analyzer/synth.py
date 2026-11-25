"""Synthetic test signals with a known spectral envelope (and therefore a known FCP).

The envelope is described in dB as a function of frequency::

    E(f) = slope * log2(f / 1000) + sum_k  h_k * exp(-0.5 * (log2(f / fc_k) / w_k)^2)

i.e. a straight line in log-frequency (the shape the FCP trendline is fitted to)
plus Gaussian bumps on a log-frequency axis (a "formant cluster").
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Envelope:
    slope_db_oct: float = -12.0
    bumps: list = field(default_factory=list)  # (fc_hz, height_db, width_oct)
    lowpass_hz: float | None = None            # optional steep roll-off
    flat_below_hz: float | None = 500.0        # envelope is flat below this (voice-like)

    def db(self, f) -> np.ndarray:
        f = np.maximum(np.asarray(f, float), 1.0)
        fl = np.maximum(f, self.flat_below_hz) if self.flat_below_hz else f
        e = self.slope_db_oct * np.log2(fl / 1000.0)
        for fc, h, w in self.bumps:
            e = e + h * np.exp(-0.5 * (np.log2(f / fc) / w) ** 2)
        if self.lowpass_hz:
            e = e - 60.0 * np.clip(np.log2(f / self.lowpass_hz), 0, None)
        return e


def shaped_noise(env: Envelope, fs: int, dur_s: float, seed: int = 0, level_dbfs: float = -20.0):
    """Gaussian noise whose power spectrum is 10**(E(f)/10) (frequency-domain shaping)."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * fs)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / fs)
    g = 10 ** (env.db(np.maximum(f, 20.0)) / 20.0)
    g[f < 20] = 0
    x = np.fft.irfft(X * g, n)
    return _set_level(x, level_dbfs)


def harmonic_phrase(env: Envelope, fs: int, dur_s: float, *, f0_notes=(110, 123.5, 138.6, 146.8, 164.8),
                    note_s: float = 0.6, vibrato_cents: float = 0.0, seed: int = 0,
                    level_dbfs: float = -20.0, gap_s: float = 0.0):
    """Sum of harmonics with amplitudes from the envelope; F0 steps through ``f0_notes``.

    Phase-continuous synthesis; each harmonic's amplitude follows E(k*F0(t)).
    Optional silent gaps between notes (unvoiced, should be excluded).
    """
    rng = np.random.default_rng(seed)
    n = int(dur_s * fs)
    t = np.arange(n) / fs
    idx = (t // note_s).astype(int) % len(f0_notes)
    f0 = np.asarray(f0_notes, float)[idx]
    if vibrato_cents:
        f0 = f0 * 2 ** (vibrato_cents / 1200 * np.sin(2 * np.pi * 5.5 * t))
    phase0 = np.cumsum(f0) / fs * 2 * np.pi
    x = np.zeros(n)
    nyq = fs / 2
    kmax = int(nyq / min(f0_notes)) + 1
    for k in range(1, kmax + 1):
        fk = k * f0
        alive = fk < nyq * 0.98
        if not np.any(alive):
            break
        amp = 10 ** (env.db(fk) / 20.0) * alive
        x += amp * np.sin(k * phase0 + rng.uniform(0, 2 * np.pi))
    if gap_s > 0:
        pos = t % note_s
        x[pos > note_s - gap_s] = 0.0
    return _set_level(x, level_dbfs)


def sine(freq, fs, dur_s, rms_dbfs=-20.0):
    t = np.arange(int(dur_s * fs)) / fs
    a = np.sqrt(2) * 10 ** (rms_dbfs / 20)
    return a * np.sin(2 * np.pi * freq * t)


def _set_level(x, level_dbfs):
    r = np.sqrt(np.mean(x ** 2))
    return x * (10 ** (level_dbfs / 20) / r) if r > 0 else x


def expected_ltas_noise(env: Envelope, cfg) -> np.ndarray:
    """Expected LTAS (dB, up to a constant) of ``shaped_noise(env)`` for a spectral config.

    E[P(f0)] is proportional to sum_d |H(f0+d)|^2 |W(d)|^2 (window kernel), then the
    engine's band post-processing is applied.
    """
    fs = cfg.fs
    big = 1 << 16
    W2 = np.abs(np.fft.fft(cfg.window, big)) ** 2
    d = np.fft.fftfreq(big, 1 / fs)
    keep = np.abs(d) <= 6 * fs / cfg.win_len
    d, W2 = d[keep], W2[keep]
    W2 = W2 / W2.sum()
    f = cfg.fine_freqs
    ff = f[:, None] + d[None, :]
    S = np.where(np.abs(ff) >= 20, 10 ** (env.db(np.abs(ff)) / 10), 0.0)
    P = (S * W2[None, :]).sum(axis=1)
    P = cfg.finalize(P)
    return 10 * np.log10(np.maximum(P, 1e-30))
