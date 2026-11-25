"""Short-time power spectra used to build the LTAS.

Two engines are offered (see ``settings``):

* ``sopran``: Hann window whose bandwidth equals ``bandwidth_hz``
  (default -6 dB definition, as Sopran appears to use: N = 2 * fs / B samples,
  50 % overlap). The averaged spectrum is a smooth
  curve sampled on a dense grid (about 20 Hz spacing, zero padding). Each value is
  the *band level*: the power a 350 Hz-wide analysis filter centred on that
  frequency would read. A sinusoid of mean square ``a2`` reads ``a2`` at its
  frequency. This is our reading of "Hanning window and 350 Hz bandwidth" in
  Lã et al. (2023), who used Sopran (tolvan.com).
* ``praat``: 40 ms Hann frames (10 ms hop) give a fine power spectral density;
  after averaging, the mean density inside consecutive ``bandwidth_hz`` bands is
  multiplied by the bandwidth (band power), as Praat's ``To Ltas`` does.

Both engines average *power* (not dB) across frames. Frames are accumulated per
storage segment so that any window, and the whole recording, can be obtained by
adding segment sums.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .settings import AnalysisSettings, ENGINE_PRAAT, ENGINE_SOPRAN, HANN_BW_BINS


def _next_pow2(n: float) -> int:
    return int(2 ** int(np.ceil(np.log2(max(2.0, n)))))


@dataclass
class SpectralConfig:
    fs: int
    engine: str
    bandwidth_hz: float
    win_len: int
    hop: int
    nfft: int
    window: np.ndarray
    fine_freqs: np.ndarray      # frequencies of the stored (fine) bins
    nbins: int
    scale: float                # |X|^2 * scale -> power (sopran) or PSD (praat)
    out_freqs: np.ndarray       # frequencies of the final LTAS
    measure_idx: np.ndarray     # indices of out_freqs on which the measures are computed

    def measure_view(self, ltas_db):
        return self.out_freqs[self.measure_idx], np.asarray(ltas_db)[..., self.measure_idx]

    def finalize(self, mean_fine: np.ndarray) -> np.ndarray:
        """Convert the averaged fine spectrum (last axis) into the final LTAS power."""
        if self.engine == ENGINE_SOPRAN:
            return mean_fine
        # praat: mean PSD within each band times the bandwidth -> band power
        B = self.bandwidth_hz
        idx = np.floor(self.fine_freqs / B).astype(int)
        nb = len(self.out_freqs)
        out_shape = mean_fine.shape[:-1] + (nb,)
        out = np.zeros(out_shape, dtype=float)
        for k in range(nb):
            sel = idx == k
            if np.any(sel):
                out[..., k] = mean_fine[..., sel].mean(axis=-1) * B
        return out


def make_config(fs: int, settings: AnalysisSettings) -> SpectralConfig:
    fs = int(fs)
    nyq = fs / 2.0
    fmax = min(float(settings.fmax_hz), nyq)
    B = float(settings.bandwidth_hz)
    if settings.engine == ENGINE_SOPRAN:
        win_len = max(8, int(round(HANN_BW_BINS[settings.bandwidth_definition] * fs / B)))
        hop = max(1, win_len // 2)
        nfft = _next_pow2(max(win_len, fs / 25.0))
    elif settings.engine == ENGINE_PRAAT:
        win_len = max(16, int(round(settings.praat_frame_s * fs)))
        hop = max(1, int(round(0.010 * fs)))
        nfft = _next_pow2(win_len)
    else:
        raise ValueError(f"unknown engine {settings.engine!r}")

    window = np.hanning(win_len + 2)[1:-1]  # strictly positive (periodic-like) Hann
    all_f = np.fft.rfftfreq(nfft, 1.0 / fs)
    nbins = int(np.searchsorted(all_f, fmax, side="right"))
    fine = all_f[:nbins]

    if settings.engine == ENGINE_SOPRAN:
        scale = 2.0 / (np.sum(window) ** 2)      # sinusoid of mean square a2 -> a2
        out_freqs = fine.copy()
    else:
        scale = 2.0 / (fs * np.sum(window ** 2))  # one-sided PSD
        nb = int(np.floor(fmax / B))
        out_freqs = (np.arange(nb) + 0.5) * B
    if settings.engine == ENGINE_SOPRAN and getattr(settings, "measure_grid", "fine") == "sopran":
        # Sopran evaluates the spectrum with an FFT of the next power of two of the window length
        # (252 -> 256 samples at 44.1 kHz). Those bins are every (nfft / n_sopran)-th fine bin.
        step = max(1, nfft // _next_pow2(win_len))
        measure_idx = np.arange(0, len(out_freqs), step)
    else:
        measure_idx = np.arange(len(out_freqs))
    return SpectralConfig(fs, settings.engine, B, win_len, hop, nfft, window,
                          fine, nbins, float(scale), out_freqs, measure_idx)


def frame_powers(x: np.ndarray, cfg: SpectralConfig, starts: np.ndarray) -> np.ndarray:
    """Power spectra (fine bins) of frames starting at ``starts`` (indices into x)."""
    if len(starts) == 0:
        return np.zeros((0, cfg.nbins))
    idx = starts[:, None] + np.arange(cfg.win_len)[None, :]
    frames = x[idx]  # DC is removed beforehand by a 20 Hz high-pass (see analysis.DCBlocker)
    spec = np.fft.rfft(frames * cfg.window[None, :], n=cfg.nfft, axis=1)[:, :cfg.nbins]
    p = (spec.real ** 2 + spec.imag ** 2) * cfg.scale
    if cfg.engine == ENGINE_SOPRAN:
        p[:, 0] *= 0.5  # DC is not doubled in a one-sided spectrum
    return p


def power_to_db(p: np.ndarray, offset_db: float = 0.0) -> np.ndarray:
    with np.errstate(divide="ignore"):
        return 10.0 * np.log10(np.maximum(p, 1e-30)) + offset_db
