"""Audio file reading (WAV, FLAC, AIFF, OGG ... via libsndfile)."""
from __future__ import annotations

import numpy as np

SUPPORTED_EXT = (".wav", ".flac", ".aif", ".aiff", ".ogg", ".mp3")


def load_audio(path: str) -> tuple[np.ndarray, int]:
    """Return (mono float64 signal in [-1, 1], sample rate). Channels are averaged."""
    import soundfile as sf

    x, fs = sf.read(path, dtype="float64", always_2d=True)
    x = x.mean(axis=1)
    return np.ascontiguousarray(x), int(fs)


def save_wav(path: str, x: np.ndarray, fs: int) -> None:
    import soundfile as sf

    sf.write(path, np.asarray(x, dtype=np.float32), int(fs), subtype="FLOAT")
