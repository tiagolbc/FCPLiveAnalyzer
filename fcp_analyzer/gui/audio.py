"""Audio input/output with sounddevice. Callbacks never touch Qt objects.

* ``Player`` plays a buffer and keeps the exact output position (samples handed to the
  device minus the device latency), which drives the synchronised display.
* ``Recorder`` pushes microphone blocks into a thread-safe queue.
"""
from __future__ import annotations

import queue
import threading
import time

import numpy as np


def _sd():
    import sounddevice as sd
    return sd


def list_devices(kind: str):
    """[(index, label, default_samplerate)] for 'input' or 'output'."""
    sd = _sd()
    out = []
    try:
        devs = sd.query_devices()
        apis = sd.query_hostapis()
        default = sd.default.device[0 if kind == "input" else 1]
    except Exception:
        return []
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    for i, d in enumerate(devs):
        if d[key] > 0:
            api = apis[d["hostapi"]]["name"]
            out.append((i, f"{d['name']} ({api})", float(d["default_samplerate"])))
    out.sort(key=lambda t: (t[0] != default,))
    return out


def pick_samplerate(device, kind="input", preferred=(44100, 48000)):
    sd = _sd()
    for fs in preferred:
        try:
            if kind == "input":
                sd.check_input_settings(device=device, samplerate=fs, channels=1)
            else:
                sd.check_output_settings(device=device, samplerate=fs, channels=1)
            return fs
        except Exception:
            continue
    return int(sd.query_devices(device)["default_samplerate"])


class Player:
    def __init__(self):
        self.stream = None
        self.audio = None
        self.fs = 44100
        self.pos = 0            # next sample to hand to the device
        self.playing = False
        self.latency = 0.0
        self._lock = threading.Lock()
        self.finished = False

    def load(self, x: np.ndarray, fs: int):
        self.stop()
        peak = float(np.max(np.abs(x))) if len(x) else 0.0
        self.audio = (x / max(peak, 1e-9) * 0.9 if peak > 1.0 else x).astype(np.float32)
        self.fs = int(fs)
        self.pos = 0
        self.finished = False

    def _callback(self, outdata, frames, t, status):
        with self._lock:
            a = self.audio
            p = self.pos
            n = min(frames, max(0, len(a) - p)) if a is not None else 0
            outdata[:n, 0] = a[p:p + n] if n else 0
            outdata[n:, 0] = 0
            self.pos = p + n
            if n < frames:
                self.finished = True
                raise _sd().CallbackStop()

    def play(self, device=None):
        sd = _sd()
        if self.audio is None:
            return
        if self.pos >= len(self.audio):
            self.pos = 0
        self.close_stream()
        self.finished = False
        self.stream = sd.OutputStream(samplerate=self.fs, channels=1, dtype="float32", device=device,
                                      callback=self._callback, latency="low", blocksize=0)
        self.latency = float(self.stream.latency)
        self.stream.start()
        self.playing = True

    def pause(self):
        self.close_stream()
        # step back by what was still in the device buffer
        with self._lock:
            self.pos = max(0, self.pos - int(self.latency * self.fs))
        self.playing = False

    def stop(self):
        self.close_stream()
        self.pos = 0
        self.playing = False

    def close_stream(self):
        if self.stream is not None:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
            self.stream = None

    def seek(self, t: float):
        if self.audio is None:
            return
        with self._lock:
            self.pos = int(np.clip(t * self.fs, 0, len(self.audio)))
            self.finished = False

    def time(self) -> float:
        """Time (s) of the sample currently heard."""
        if self.audio is None:
            return 0.0
        if self.playing and self.stream is not None:
            heard = self.pos - self.latency * self.fs
            return max(0.0, heard / self.fs)
        return self.pos / self.fs

    def is_active(self) -> bool:
        if not self.playing:
            return False
        if self.finished and (self.stream is None or not self.stream.active):
            self.playing = False
            self.close_stream()
            self.pos = len(self.audio)
        return self.playing


class Recorder:
    def __init__(self):
        self.stream = None
        self.q: queue.Queue = queue.Queue()
        self.fs = 44100
        self.peak = 0.0
        self.overflows = 0

    def _callback(self, indata, frames, t, status):
        if status:
            self.overflows += 1
        x = indata[:, 0].copy()
        self.peak = max(self.peak * 0.0, float(np.max(np.abs(x))) if len(x) else 0.0)
        self.q.put(x)

    def start(self, device, fs):
        sd = _sd()
        self.stop()
        self.q = queue.Queue()
        self.fs = int(fs)
        self.overflows = 0
        self.stream = sd.InputStream(samplerate=self.fs, channels=1, dtype="float32", device=device,
                                     callback=self._callback, blocksize=int(0.02 * self.fs))
        self.stream.start()

    def stop(self):
        if self.stream is not None:
            try:
                self.stream.stop(); self.stream.close()
            except Exception:
                pass
            self.stream = None


def record_blocking(device, fs, seconds):
    sd = _sd()
    x = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype="float32", device=device)
    sd.wait()
    return x[:, 0].astype(float)
