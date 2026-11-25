"""Main window: live input, file playback with synchronised display, batch, export."""
from __future__ import annotations

import os
import sys
import time

import numpy as np
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QProgressBar, QProgressDialog, QScrollArea, QSplitter,
                               QTableWidget, QTableWidgetItem, QTabWidget, QToolBar, QVBoxLayout, QWidget,
                               QFrame, QHeaderView)

from .. import __version__, APP_NAME
from ..core import export
from ..core.audio_io import SUPPORTED_EXT, save_wav
from ..core.metrics import fcp_color
from ..core.quality import message
from . import theme
from .audio import Player, Recorder, list_devices, pick_samplerate
from .dialogs import AboutDialog, CalibrationDialog, SettingsDialog
from .i18n import lang, tr
from .widgets import BandTable, Card, ColorLegend, LevelMeter, LtasPlot, ScatterPlot, TimelinePlot
from .workers import BatchWorker, FileWorker, LiveWorker


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    return os.path.join(base, *parts)


def _f(v, fmt="{:.1f}", unit=""):
    return (fmt.format(v) + unit) if v is not None and np.isfinite(v) else "—"


class MainWindow(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        icon = resource_path("assets", "logo_fcp.ico")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.setAcceptDrops(True)
        self.mode = "idle"            # idle | file | live
        self.fa = None                # FileAnalysis
        self.player = Player()
        self.recorder = Recorder()
        self.live_worker = None
        self.file_worker = None
        self.live_latest = None       # (window result, global result, t)
        self.live_series = ([], [], [])
        self.cursor_t = 0.0
        self._last_idx = None
        self._last_live_draw = 0.0
        self._build_ui()
        self._refresh_devices()
        self._update_status_cal()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)
        self.status(tr("ready"))

    # ------------------------------------------------------------------ UI
    def _act(self, text, slot, shortcut=None, tip=None, checkable=False):
        a = QAction(text, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        if tip:
            a.setToolTip(tip)
        a.setCheckable(checkable)
        return a

    def _build_ui(self):
        tb = QToolBar(); tb.setMovable(False); tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)
        self.a_live = self._act("●  " + tr("live"), self.toggle_live, "Ctrl+L", checkable=True)
        self.a_open = self._act(tr("open"), self.open_file, "Ctrl+O")
        self.a_play = self._act("▶  " + tr("play"), self.toggle_play)
        self.a_batch = self._act(tr("batch"), self.batch, "Ctrl+B")
        for a in (self.a_live, self.a_open, self.a_play, self.a_batch):
            tb.addAction(a)
        self.a_play.setEnabled(False)
        tb.addSeparator()
        tb.addWidget(QLabel(" " + tr("input") + " "))
        self.in_combo = QComboBox(); self.in_combo.setFixedWidth(190)
        tb.addWidget(self.in_combo)
        self.meter = LevelMeter(); tb.addWidget(self.meter)
        tb.addWidget(QLabel("  " + tr("output") + " "))
        self.out_combo = QComboBox(); self.out_combo.setFixedWidth(170)
        tb.addWidget(self.out_combo)
        tb.addAction(self._act("⟳", self._refresh_devices, tip=tr("refresh")))
        spacer = QWidget(); spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,
                                                 spacer.sizePolicy().verticalPolicy().Preferred)
        tb.addWidget(spacer)
        for a in (self._act(tr("calibrate"), self.calibrate), self._act(tr("export"), self.export_current, "Ctrl+E"),
                  self._act(tr("screenshot"), self.screenshot, "Ctrl+Shift+S"),
                  self._act(tr("settings"), self.open_settings, "Ctrl+,"),
                  self._act(tr("help"), self.open_manual, "F1"), self._act(tr("about"), self.about)):
            tb.addAction(a)
        self.in_combo.currentIndexChanged.connect(self._device_changed)
        self.out_combo.currentIndexChanged.connect(self._device_changed)

        central = QWidget(); central.setObjectName("central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(10, 10, 10, 10); root.setSpacing(10)
        split = QSplitter(Qt.Horizontal)
        root.addWidget(split)

        # left: tabs + timeline
        left = QSplitter(Qt.Vertical)
        self.tabs = QTabWidget()
        s = self.cfg.analysis
        self.ltas_plot = LtasPlot(s)
        self.ltas_plot.set_ylabel(s.level_unit())
        ltas_box = QWidget(); lb = QVBoxLayout(ltas_box); lb.setContentsMargins(6, 6, 6, 6)
        self.ltas_title = QLabel(tr("ltas_title")); self.ltas_title.setObjectName("muted")
        lb.addWidget(self.ltas_title)
        lb.addWidget(self.ltas_plot, 1)
        opts = QHBoxLayout()
        self.cb_global = QCheckBox(tr("show_global")); self.cb_global.setChecked(self.cfg.show_global)
        self.cb_buzz = QCheckBox(tr("show_buzz")); self.cb_buzz.setChecked(self.cfg.show_buzz)
        self.cb_freeze = QCheckBox(tr("freeze"))
        for c in (self.cb_global, self.cb_buzz, self.cb_freeze):
            opts.addWidget(c); c.toggled.connect(self._options_changed)
        opts.addStretch(1)
        lb.addLayout(opts)
        self.tabs.addTab(ltas_box, tr("tab_ltas"))
        self.scatter = ScatterPlot()
        self.tabs.addTab(self.scatter, tr("tab_scatter"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr("tbl_measure"), tr("tbl_window"), tr("tbl_global"), tr("tbl_def")])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.tabs.addTab(self.table, tr("tab_table"))
        left.addWidget(self.tabs)
        self.timeline = TimelinePlot()
        self.timeline.seek.connect(self.seek)
        left.addWidget(self.timeline)
        left.setSizes([620, 220])
        split.addWidget(left)

        # right: metrics
        panel = QWidget(); panel.setObjectName("central"); pv = QVBoxLayout(panel); pv.setContentsMargins(0, 0, 0, 0); pv.setSpacing(8)
        self.card_fcp = Card(tr("fcp_window", w=s.window_s), "bigValue")
        self.card_glob = Card(tr("fcp_global"), "midValue")
        pv.addWidget(self.card_fcp); pv.addWidget(self.card_glob)
        self.bands = BandTable(); pv.addWidget(self.bands)
        row = QHBoxLayout()
        self.card_leq = Card(tr("leq"), "midValue"); self.card_f0 = Card(tr("f0"), "midValue")
        row.addWidget(self.card_leq); row.addWidget(self.card_f0)
        pv.addLayout(row)
        self.card_voiced = Card(tr("voiced"), "midValue")
        pv.addWidget(self.card_voiced)
        self.card_buzz = Card(tr("buzz"), "midValue", badge=tr("experimental"))
        pv.addWidget(self.card_buzz)
        self.card_buzz.setVisible(self.cfg.show_buzz)
        wbox = QFrame(); wbox.setObjectName("card"); wl = QVBoxLayout(wbox); wl.setContentsMargins(14, 10, 14, 10)
        t = QLabel(tr("warnings")); t.setObjectName("cardTitle"); wl.addWidget(t)
        self.warn_label = QLabel(tr("no_warnings")); self.warn_label.setWordWrap(True); self.warn_label.setObjectName("warn")
        wl.addWidget(self.warn_label)
        pv.addWidget(wbox)
        pv.addWidget(ColorLegend())
        pv.addStretch(1)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(panel)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(360); scroll.setMaximumWidth(440)
        split.addWidget(scroll)
        split.setStretchFactor(0, 1)

        self.progress = QProgressBar(); self.progress.setMaximumWidth(220); self.progress.setVisible(False)
        self.cal_label = QLabel("")
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().addPermanentWidget(self.cal_label)
        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.toggle_play)
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=lambda: self.nudge(-1.0))
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=lambda: self.nudge(1.0))
        QShortcut(QKeySequence(Qt.Key_Home), self, activated=lambda: self.seek(0.0))

    def status(self, msg):
        self.statusBar().showMessage(msg)

    def _update_status_cal(self):
        s = self.cfg.analysis
        txt = tr("calibrated", off=s.cal_offset_db) if s.calibrated else tr("uncalibrated")
        if s.distance_cm:
            txt += f" · {s.distance_cm:g} cm → 30 cm"
        self.cal_label.setText(txt + "  ")
        self.ltas_plot.set_ylabel(s.level_unit())

    # ------------------------------------------------------------------ devices
    def _refresh_devices(self):
        for combo, kind, saved in ((self.in_combo, "input", self.cfg.input_device),
                                   (self.out_combo, "output", self.cfg.output_device)):
            combo.blockSignals(True)
            combo.clear()
            for idx, label, fs in list_devices(kind):
                combo.addItem(label, idx)
            if saved is not None:
                i = combo.findData(saved)
                if i >= 0:
                    combo.setCurrentIndex(i)
            combo.blockSignals(False)

    def _device_changed(self):
        self.cfg.input_device = self.in_combo.currentData()
        self.cfg.output_device = self.out_combo.currentData()
        self.cfg.save()

    # ------------------------------------------------------------------ files
    def open_file(self):
        exts = " ".join("*" + e for e in SUPPORTED_EXT)
        p, _ = QFileDialog.getOpenFileName(self, tr("open"), "", f"{tr('audio_files')} ({exts})")
        if p:
            self.load_path(p)

    def load_path(self, path, signal=None, fs=None, after=None):
        if self.mode == "live":
            self.stop_live()
        self.player.stop()
        self._set_play_text(False)
        self.status(tr("analysing", name=os.path.basename(path)))
        self.progress.setVisible(True); self.progress.setValue(0)
        self.a_open.setEnabled(False); self.a_live.setEnabled(False)
        w = FileWorker(self._settings_copy(), path=path, signal=signal, fs=fs)
        w.progress.connect(lambda p: self.progress.setValue(int(p * 100)))
        w.done.connect(lambda fa: self._file_ready(fa, after))
        w.failed.connect(self._file_failed)
        self.file_worker = w
        w.start()

    def _settings_copy(self):
        from ..core.settings import AnalysisSettings
        return AnalysisSettings.from_dict(self.cfg.analysis.to_dict())

    def _file_failed(self, msg):
        self.progress.setVisible(False)
        self.a_open.setEnabled(True); self.a_live.setEnabled(True)
        QMessageBox.critical(self, tr("error"), tr("load_error", e=msg.split("\n")[0]))
        self.status(tr("ready"))

    def _file_ready(self, fa, after=None):
        self.progress.setVisible(False)
        self.a_open.setEnabled(True); self.a_live.setEnabled(True)
        self.fa = fa
        self.mode = "file"
        self.player.load(fa.signal, fa.fs)
        self.a_play.setEnabled(True)
        self.cursor_t = 0.0
        self._last_idx = None
        name = os.path.basename(fa.path) or "take"
        self.ltas_title.setText(f"{tr('ltas_title')} — {name}")
        show_buzz = self.cb_buzz.isChecked()
        self.timeline.set_file(fa.times, fa.series("fcp_db"), fa.series("buzz_db"), fa.signal, fa.fs,
                               fa.global_result.measures.fcp_db, show_buzz)
        self.scatter.set_data(fa.series("fcp_db"), fa.series("buzz_db"))
        self.card_fcp.title.setText(tr("fcp_window", w=fa.settings.window_s))
        self.card_glob.title.setText(tr("fcp_global"))
        self._show_global(fa.global_result)
        self._render_file(0.0, force=True)
        self.status(tr("loaded", name=name, dur=fa.duration_s, fs=fa.fs))
        if fa.global_result.voiced_s <= 0:
            QMessageBox.information(self, APP_NAME, tr("no_voice"))
        if after:
            after()

    # ------------------------------------------------------------------ playback
    def _set_play_text(self, playing):
        self.a_play.setText(("⏸  " + tr("pause")) if playing else ("▶  " + tr("play")))

    def toggle_play(self):
        if self.mode != "file" or self.fa is None:
            return
        if self.player.is_active():
            self.player.pause()
            self.cursor_t = self.player.time()
            self._set_play_text(False)
        else:
            try:
                self.player.seek(self.cursor_t if self.cursor_t < self.fa.duration_s - 0.05 else 0.0)
                self.player.play(self.out_combo.currentData())
            except Exception as e:
                QMessageBox.critical(self, tr("error"), tr("audio_error", e=e)); return
            self._set_play_text(True)

    def seek(self, t):
        if self.mode != "file" or self.fa is None:
            return
        self.cursor_t = float(np.clip(t, 0, self.fa.duration_s))
        was = self.player.is_active()
        if was:
            self.player.pause()
        self.player.seek(self.cursor_t)
        if was:
            self.player.play(self.out_combo.currentData())
        self._render_file(self.cursor_t, force=True)

    def nudge(self, dt):
        if self.mode == "file":
            t = self.player.time() if self.player.is_active() else self.cursor_t
            self.seek(t + dt)

    # ------------------------------------------------------------------ render loop
    def _tick(self):
        if self.mode == "file" and self.fa is not None:
            if self.player.is_active():
                t = self.player.time()
                self.cursor_t = t
                self._render_file(t)
            elif self.player.playing is False and self.a_play.text().startswith("⏸"):
                self._set_play_text(False)
        elif self.mode == "live" and self.live_latest is not None:
            now = time.perf_counter()
            if now - self._last_live_draw >= 0.05:
                self._last_live_draw = now
                self._render_live()

    def _render_file(self, t, force=False):
        fa = self.fa
        self.timeline.set_time(t)
        i = fa.index_at(t)
        if i < 0 or (i == self._last_idx and not force) or self.cb_freeze.isChecked() and not force:
            return
        self._last_idx = i
        m = fa.window_measures[i]
        L = fa.window_ltas[i]
        g = fa.global_result
        self.ltas_plot.show_result(fa.freqs, L, m, g.ltas_db if self.cb_global.isChecked() else None,
                                   self.cb_buzz.isChecked())
        self._show_window(m, fa.window_leq[i], fa.window_f0[i], fa.window_voiced_s[i])
        self.scatter.set_current(m.fcp_db, m.buzz_db)
        self.bands.set(m, g.measures)
        self._fill_table(m, g.measures)

    def _render_live(self):
        res, g, t = self.live_latest
        if not self.cb_freeze.isChecked():
            self.ltas_plot.show_result(res.freqs, res.ltas_db, res.measures,
                                       g.ltas_db if (g is not None and self.cb_global.isChecked()) else None,
                                       self.cb_buzz.isChecked())
            self._show_window(res.measures, res.leq_c_db, res.f0_mean_hz, res.voiced_s)
            if g is not None:
                self._show_global(g, live=True)
                self._fill_table(res.measures, g.measures)
            self.bands.set(res.measures, g.measures if g is not None else None)
        ts, fs_, bs = self.live_series
        self.timeline.set_live(np.array(ts), np.array(fs_), np.array(bs),
                               g.measures.fcp_db if g is not None else np.nan, self.cb_buzz.isChecked())
        self.scatter.set_data(fs_, bs)
        self.scatter.set_current(res.measures.fcp_db, res.measures.buzz_db)

    def _show_window(self, m, leq, f0, voiced_s):
        col = fcp_color(m.fcp_db)
        self.card_fcp.set(_f(m.fcp_db, "{:.1f}", " dB"), col,
                          f"{tr('at')} {m.fcp_freq_hz:.0f} Hz" if np.isfinite(m.fcp_freq_hz) else "")
        self.card_leq.set(_f(leq, "{:.1f}", " dB"), sub=self.cfg.analysis.level_unit())
        self.card_f0.set(_f(f0, "{:.0f}", " Hz"))
        self.card_buzz.set(_f(m.buzz_db, "{:.1f}", " dB"), theme.BUZZ,
                           f"{tr('at')} {m.buzz_freq_hz/1000:.1f} kHz" if np.isfinite(m.buzz_freq_hz) else "")
        self._win_measures = m

    def _show_global(self, g, live=False):
        m = g.measures
        self.card_glob.title.setText(tr("fcp_global_live") if live else tr("fcp_global"))
        self.card_glob.set(_f(m.fcp_db, "{:.1f}", " dB"), fcp_color(m.fcp_db),
                           f"{tr('at')} {m.fcp_freq_hz:.0f} Hz" if np.isfinite(m.fcp_freq_hz) else "")
        self.card_voiced.set(f"{g.voiced_s:.1f} s", sub=f"/ {g.total_s:.1f} s")
        self.bands.set(getattr(self, "_win_measures", None), m)
        w = [message(c, p, lang()) for c, p in g.warnings]
        if self.mode == "live" or live:
            w = [x for x, (c, _) in zip(w, g.warnings) if c != "short_ltas" or g.voiced_s > 0]
        self.warn_label.setText("\n".join("• " + x for x in w) if w else tr("no_warnings"))

    def _fill_table(self, wm, gm):
        rows = [("FCP", "fcp_db", "max[LTAS − reta] em 2–4 kHz" if lang() == "pt" else "max[LTAS − trend] in 2–4 kHz"),
                ("FCP freq (Hz)", "fcp_freq_hz", ""),
                ("Peak 2–4 kHz", "peak_2_4_db", ""),
                ("FCP v1 (peak − trend)", "fcp_at_peak_db", "v1.x" + (" (comparação)" if lang() == "pt" else " (comparison)")),
                ("Trend slope (dB/oct)", "trend_slope_db_oct", "1–5 kHz, log f"),
                ("Lmax(0–2)", "lmax_0_2", ""), ("Lmax(2–5)", "lmax_2_5", ""), ("Lmax(5–8)", "lmax_5_8", ""),
                ("ΔL1", "dl1", "Lmax(0–2) − Lmax(2–5)"), ("ΔL2", "dl2", "Lmax(2–5) − Lmax(5–8)"),
                ("ΔL3", "dl3", "ΔL1 − ΔL2"), ("ΔL4", "dl4", "Lmax(0–2) − Lmax(5–8)"),
                ("Buzz (exp.)", "buzz_db", "P90(LTAS, buzz band) − trend(5 kHz)")]
        self.table.setRowCount(len(rows))
        for r, (lab, key, d) in enumerate(rows):
            vals = [lab, _f(getattr(wm, key), "{:.2f}"), _f(getattr(gm, key), "{:.2f}"), d]
            for c, v in enumerate(vals):
                it = self.table.item(r, c)
                if it is None:
                    it = QTableWidgetItem(); self.table.setItem(r, c, it)
                it.setText(v)

    def _options_changed(self):
        self.cfg.show_buzz = self.cb_buzz.isChecked()
        self.cfg.show_global = self.cb_global.isChecked()
        self.cfg.save()
        self.card_buzz.setVisible(self.cfg.show_buzz)
        if self.mode == "file" and self.fa is not None:
            fa = self.fa
            self.timeline.set_file(fa.times, fa.series("fcp_db"), fa.series("buzz_db"), fa.signal, fa.fs,
                                   fa.global_result.measures.fcp_db, self.cfg.show_buzz)
            self._render_file(self.cursor_t, force=True)

    # ------------------------------------------------------------------ live
    def toggle_live(self):
        if self.mode == "live":
            self.stop_live()
        else:
            self.start_live()

    def start_live(self):
        self.player.stop(); self._set_play_text(False)
        dev = self.in_combo.currentData()
        s = self._settings_copy()
        if s.calibrated and self.cfg.cal_device is not None and dev != self.cfg.cal_device:
            QMessageBox.warning(self, tr("calibrate"),
                                "A calibração foi feita com outro microfone; os níveis em dB SPL não valem para este."
                                if lang() == "pt" else
                                "Calibration was made with another microphone; dB SPL levels do not apply to this one.")
        try:
            fs = pick_samplerate(dev, "input")
            self.recorder.start(dev, fs)
        except Exception as e:
            self.a_live.setChecked(False)
            QMessageBox.critical(self, tr("error"), tr("audio_error", e=e)); return
        self.mode = "live"
        self.fa = None
        self.live_series = ([], [], [])
        self.live_latest = None
        self.ltas_plot.clear_data()
        self.ltas_title.setText(tr("ltas_title"))
        self.card_fcp.title.setText(tr("fcp_window", w=s.window_s))
        self.live_worker = LiveWorker(self.recorder, s)
        self.live_worker.result.connect(self._live_result)
        self.live_worker.level.connect(self.meter.set_db)
        self.live_worker.start()
        self.a_live.setChecked(True); self.a_live.setText("■  " + tr("stop"))
        self.a_play.setEnabled(False); self.a_open.setEnabled(False); self.a_batch.setEnabled(False)
        self.in_combo.setEnabled(False)
        self.status(tr("live_running", dev=self.in_combo.currentText(), fs=fs))

    def _live_result(self, res, g, t):
        self.live_latest = (res, g, t)
        ts, fs_, bs = self.live_series
        ts.append(t); fs_.append(res.measures.fcp_db); bs.append(res.measures.buzz_db)

    def stop_live(self):
        if self.mode != "live":
            return
        self.recorder.stop()
        w = self.live_worker
        w.stop(); w.wait(3000)
        self.meter.set_db(-90)
        self.a_live.setChecked(False); self.a_live.setText("●  " + tr("live"))
        self.a_open.setEnabled(True); self.a_batch.setEnabled(True); self.in_combo.setEnabled(True)
        self.mode = "idle"
        audio = w.live.audio()
        fs = w.live.fs
        if len(audio) < fs * 0.5:
            self.status(tr("ready")); return
        out_dir = export.timestamped_dir(self.cfg.exports_dir, "Live")
        wav = os.path.join(out_dir, "take.wav")
        try:
            save_wav(wav, audio, fs)
        except Exception as e:
            QMessageBox.warning(self, tr("error"), str(e))
        # re-analyse the whole take with the file engine (identical numbers to a later LOAD),
        # export it and keep it open for review with synchronised playback
        self.load_path(wav, signal=audio.astype(float), fs=fs,
                       after=lambda: self._export_to(out_dir, quiet=True))
        self.status(tr("live_saved", path=out_dir))

    # ------------------------------------------------------------------ export
    def export_current(self):
        if self.mode != "file" or self.fa is None:
            QMessageBox.information(self, APP_NAME, tr("nothing_export")); return
        stem = os.path.splitext(os.path.basename(self.fa.path) or "take")[0]
        self._export_to(export.timestamped_dir(self.cfg.exports_dir, stem))

    def _export_to(self, out_dir, quiet=False):
        try:
            export.export_file_analysis(out_dir, self.fa, os.path.basename(self.fa.path) or "take", lang())
            self.ltas_plot.grab().save(os.path.join(out_dir, "screen_ltas.png"))
        except Exception as e:
            QMessageBox.warning(self, tr("error"), str(e)); return
        self.status(tr("export_done", path=out_dir).replace("\n", " "))
        if not quiet:
            box = QMessageBox(self); box.setWindowTitle(APP_NAME); box.setText(tr("export_done", path=out_dir))
            ob = box.addButton(tr("open_folder"), QMessageBox.ActionRole); box.addButton(QMessageBox.Ok)
            box.exec()
            if box.clickedButton() is ob:
                QDesktopServices.openUrl(QUrl.fromLocalFile(out_dir))

    def screenshot(self):
        p, _ = QFileDialog.getSaveFileName(self, tr("screenshot"), os.path.join(self.cfg.exports_dir, "fcp_screen.png"),
                                           "PNG (*.png)")
        if p:
            self.grab().save(p)

    # ------------------------------------------------------------------ batch
    def batch(self):
        exts = " ".join("*" + e for e in SUPPORTED_EXT)
        paths, _ = QFileDialog.getOpenFileNames(self, tr("batch_select"), "", f"{tr('audio_files')} ({exts})")
        if not paths:
            return
        out_dir = export.timestamped_dir(self.cfg.exports_dir, "Batch")
        dlg = QProgressDialog(tr("batch_running"), tr("cancel"), 0, 100, self)
        dlg.setWindowModality(Qt.WindowModal); dlg.setMinimumDuration(0)
        w = BatchWorker(paths, self._settings_copy(), out_dir, lang())
        w.progress.connect(lambda p, n: (dlg.setValue(int(p * 100)), dlg.setLabelText(f"{tr('batch_running')}\n{n}")))
        dlg.canceled.connect(w.cancel)

        def finished(out, status):
            dlg.close()
            ok = sum(1 for _, e in status if e is None)
            box = QMessageBox(self); box.setWindowTitle(APP_NAME)
            box.setText(tr("batch_done", ok=ok, n=len(paths), path=out))
            ob = box.addButton(tr("open_folder"), QMessageBox.ActionRole); box.addButton(QMessageBox.Ok)
            box.exec()
            if box.clickedButton() is ob:
                QDesktopServices.openUrl(QUrl.fromLocalFile(out))
        w.done.connect(finished)
        w.failed.connect(lambda m: (dlg.close(), QMessageBox.critical(self, tr("error"), m)))
        self.batch_worker = w
        w.start()

    # ------------------------------------------------------------------ dialogs
    def open_settings(self):
        d = SettingsDialog(self.cfg, self)
        if d.exec():
            if d.apply():
                QMessageBox.information(self, APP_NAME, tr("lang_restart"))
            self.ltas_plot.s = self.cfg.analysis
            self._update_status_cal()
            if self.mode == "file" and self.fa is not None:
                self.load_path(self.fa.path, signal=self.fa.signal, fs=self.fa.fs)

    def calibrate(self):
        dev = self.in_combo.currentData()
        try:
            fs = pick_samplerate(dev, "input") if dev is not None else 44100
        except Exception:
            fs = 44100
        d = CalibrationDialog(self.cfg, dev, fs, self)
        if d.exec():
            d.apply()
            self._update_status_cal()
            if self.mode == "file" and self.fa is not None:
                self.load_path(self.fa.path, signal=self.fa.signal, fs=self.fa.fs)

    def open_manual(self):
        name = "Manual_FCP_Live_Analyzer_pt-BR.pdf" if lang() == "pt" else "Manual_FCP_Live_Analyzer_EN.pdf"
        for p in (resource_path("docs", name), resource_path("docs", name.replace(".pdf", ".html"))):
            if os.path.exists(p):
                QDesktopServices.openUrl(QUrl.fromLocalFile(p)); return
        QMessageBox.information(self, APP_NAME, name)

    def about(self):
        AboutDialog(resource_path("assets", "logo_fcp.png"), self).exec()

    # ------------------------------------------------------------------ drag & drop / close
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(SUPPORTED_EXT):
                self.load_path(p); break

    def closeEvent(self, e):
        try:
            if self.mode == "live":
                self.recorder.stop()
                self.live_worker.stop(); self.live_worker.wait(2000)
            self.player.stop()
        finally:
            self.cfg.save()
        super().closeEvent(e)
