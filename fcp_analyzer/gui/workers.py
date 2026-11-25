"""Background work (analysis never runs on the GUI thread)."""
from __future__ import annotations

import queue
import time
import traceback

import numpy as np
from PySide6.QtCore import QThread, Signal

from ..core.analysis import analyse_signal, LiveAnalyzer
from ..core.audio_io import load_audio
from ..core.batch import run_batch


class FileWorker(QThread):
    progress = Signal(float)
    done = Signal(object)          # FileAnalysis
    failed = Signal(str)

    def __init__(self, settings, path=None, signal=None, fs=None):
        super().__init__()
        self.settings, self.path, self.signal, self.fs = settings, path, signal, fs

    def run(self):
        try:
            if self.signal is None:
                x, fs = load_audio(self.path)
            else:
                x, fs = self.signal, self.fs
            fa = analyse_signal(x, fs, self.settings, path=self.path or "",
                                progress=lambda p: self.progress.emit(float(p)))
            self.done.emit(fa)
        except Exception as e:
            self.failed.emit(f"{e}\n\n{traceback.format_exc()}")


class BatchWorker(QThread):
    progress = Signal(float, str)
    done = Signal(str, object)
    failed = Signal(str)

    def __init__(self, paths, settings, out_dir, lang):
        super().__init__()
        self.paths, self.settings, self.out_dir, self.lang = paths, settings, out_dir, lang
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            out, status = run_batch(self.paths, self.settings, self.out_dir, lang=self.lang,
                                    progress=lambda p, n: self.progress.emit(float(p), n),
                                    cancelled=lambda: self._cancel)
            self.done.emit(out, status)
        except Exception as e:
            self.failed.emit(f"{e}\n\n{traceback.format_exc()}")


class LiveWorker(QThread):
    """Consumes the recorder queue, runs LiveAnalyzer.update(), emits the latest results."""
    result = Signal(object, object, float)   # window LtasResult, global LtasResult, session time
    level = Signal(float)                    # input peak (dBFS)

    def __init__(self, recorder, settings):
        super().__init__()
        self.rec = recorder
        self.live = LiveAnalyzer(recorder.fs, settings)
        self._stop = False
        self._last_global = 0.0

    def stop(self):
        self._stop = True

    def run(self):
        live = self.live
        while not self._stop:
            got = False
            try:
                while True:
                    x = self.rec.q.get(timeout=0.02)
                    live.feed(x)
                    got = True
                    pk = float(np.max(np.abs(x))) if len(x) else 0.0
                    self.level.emit(20 * np.log10(max(pk, 1e-6)))
                    if self.rec.q.empty():
                        break
            except queue.Empty:
                pass
            if not got:
                continue
            try:
                res = live.update()
            except Exception:
                traceback.print_exc()
                continue
            if res:
                g = live.global_result() if live.done_segments else None
                self.result.emit(res[-1], g, live.done_segments * live.s.segment_s)
        # drain and flush
        while not self.rec.q.empty():
            live.feed(self.rec.q.get_nowait())
        try:
            live.flush()
        except Exception:
            traceback.print_exc()
