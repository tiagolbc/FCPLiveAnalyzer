"""Settings, calibration and about dialogs."""
from __future__ import annotations

import os

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
                               QTextBrowser, QVBoxLayout)

from .. import __version__, APP_NAME
from ..core.settings import AnalysisSettings, ENGINE_PRAAT, ENGINE_SOPRAN
from ..core.calibration import offset_from_reference, mean_square
from .i18n import tr, lang


def _spin(lo, hi, val, dec=1, step=1.0, suffix=""):
    s = QDoubleSpinBox()
    s.setRange(lo, hi); s.setDecimals(dec); s.setSingleStep(step); s.setValue(val)
    if suffix:
        s.setSuffix(suffix)
    return s


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle(tr("set_title"))
        s = cfg.analysis
        form = QFormLayout()
        self.engine = QComboBox()
        self.engine.addItem(tr("set_engine_sopran"), ENGINE_SOPRAN)
        self.engine.addItem(tr("set_engine_praat"), ENGINE_PRAAT)
        self.engine.setCurrentIndex(0 if s.engine == ENGINE_SOPRAN else 1)
        form.addRow(tr("set_engine"), self.engine)
        self.bw = _spin(50, 1000, s.bandwidth_hz, 0, 10)
        form.addRow(tr("set_bw"), self.bw)
        self.bwdef = QComboBox()
        for k in ("-6dB", "-3dB", "enbw"):
            self.bwdef.addItem(k, k)
        self.bwdef.setCurrentIndex(["-6dB", "-3dB", "enbw"].index(s.bandwidth_definition))
        form.addRow(tr("set_bwdef"), self.bwdef)
        self.grid = QComboBox()
        self.grid.addItem(tr("set_grid_sopran"), "sopran"); self.grid.addItem(tr("set_grid_fine"), "fine")
        self.grid.setCurrentIndex(0 if s.measure_grid == "sopran" else 1)
        form.addRow(tr("set_grid"), self.grid)
        self.win = _spin(0.5, 30, s.window_s, 1, 0.5)
        form.addRow(tr("set_window"), self.win)
        self.voiced = QCheckBox(); self.voiced.setChecked(s.voiced_only)
        form.addRow(tr("set_voiced"), self.voiced)
        self.floor = _spin(30, 300, s.pitch_floor_hz, 0, 5)
        self.ceil = _spin(300, 2000, s.pitch_ceiling_hz, 0, 50)
        form.addRow(tr("set_floor"), self.floor)
        form.addRow(tr("set_ceiling"), self.ceil)
        self.buzz = QComboBox()
        for lo, hi in ((5000, 8000), (4000, 8000), (5000, 9000)):
            self.buzz.addItem(f"{lo/1000:g}–{hi/1000:g} kHz", (lo, hi))
        bands = [(5000, 8000), (4000, 8000), (5000, 9000)]
        cur = tuple(int(v) for v in s.buzz_band_hz)
        self.buzz.setCurrentIndex(bands.index(cur) if cur in bands else 0)
        form.addRow(tr("set_buzz_band"), self.buzz)
        self.lang = QComboBox()
        self.lang.addItem("Português (Brasil)", "pt"); self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(0 if cfg.language == "pt" else 1)
        form.addRow(tr("set_lang"), self.lang)
        row = QHBoxLayout()
        self.exp = QLineEdit(cfg.exports_dir)
        b = QPushButton(tr("set_browse")); b.clicked.connect(self._browse)
        row.addWidget(self.exp); row.addWidget(b)
        form.addRow(tr("set_exports"), row)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        note = QLabel(tr("set_note")); note.setObjectName("muted"); note.setWordWrap(True)
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        bb.button(QDialogButtonBox.RestoreDefaults).setText(tr("set_defaults"))
        bb.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._defaults)
        lay.addWidget(bb)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, tr("set_exports"), self.exp.text())
        if d:
            self.exp.setText(d)

    def _defaults(self):
        d = AnalysisSettings()
        self.engine.setCurrentIndex(0); self.bw.setValue(d.bandwidth_hz); self.bwdef.setCurrentIndex(0)
        self.grid.setCurrentIndex(0)
        self.win.setValue(d.window_s); self.voiced.setChecked(True)
        self.floor.setValue(d.pitch_floor_hz); self.ceil.setValue(d.pitch_ceiling_hz); self.buzz.setCurrentIndex(0)

    def apply(self) -> bool:
        """Write the dialog into cfg. Returns True if the language changed."""
        s = self.cfg.analysis
        s.engine = self.engine.currentData()
        s.bandwidth_hz = self.bw.value()
        s.bandwidth_definition = self.bwdef.currentData()
        s.measure_grid = self.grid.currentData()
        s.window_s = self.win.value()
        s.voiced_only = self.voiced.isChecked()
        s.pitch_floor_hz = self.floor.value()
        s.pitch_ceiling_hz = self.ceil.value()
        s.buzz_band_hz = tuple(float(v) for v in self.buzz.currentData())
        self.cfg.exports_dir = self.exp.text()
        changed = self.lang.currentData() != self.cfg.language
        self.cfg.language = self.lang.currentData()
        self.cfg.save()
        return changed


class CalibrationDialog(QDialog):
    def __init__(self, cfg, input_device, input_fs, parent=None):
        super().__init__(parent)
        self.cfg, self.dev, self.fs = cfg, input_device, input_fs
        self.setWindowTitle(tr("cal_title"))
        self.setMinimumWidth(520)
        s = cfg.analysis
        lay = QVBoxLayout(self)
        intro = QLabel(tr("cal_intro")); intro.setWordWrap(True)
        lay.addWidget(intro)
        form = QFormLayout()
        self.spl = _spin(40, 140, 94.0, 1, 0.5, " dB")
        form.addRow(tr("cal_spl"), self.spl)
        row = QHBoxLayout()
        b1 = QPushButton(tr("cal_record")); b1.clicked.connect(self._record)
        b2 = QPushButton(tr("cal_load")); b2.clicked.connect(self._load)
        row.addWidget(b1); row.addWidget(b2)
        form.addRow("", row)
        self.offset = _spin(-200, 300, s.cal_offset_db if s.cal_offset_db is not None else 0.0, 2, 0.1, " dB")
        form.addRow(tr("cal_manual"), self.offset)
        self.use = QCheckBox(); self.use.setChecked(s.cal_offset_db is not None)
        form.addRow(tr("calibrate"), self.use)
        self.dist = _spin(0, 300, s.distance_cm or 0.0, 1, 1, " cm")
        self.dist.setSpecialValueText("—")
        form.addRow(tr("cal_distance"), self.dist)
        lay.addLayout(form)
        self.info = QLabel(""); self.info.setObjectName("muted")
        lay.addWidget(self.info)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def _apply_tone(self, x):
        try:
            off = offset_from_reference(x, self.spl.value())
        except ValueError as e:
            QMessageBox.warning(self, tr("error"), str(e)); return
        self.offset.setValue(off)
        self.use.setChecked(True)
        self.info.setText(tr("cal_result", off=off, lvl=10 * np.log10(mean_square(x))))

    def _record(self):
        from .audio import record_blocking
        self.info.setText(tr("cal_recording")); self.repaint()
        try:
            x = record_blocking(self.dev, self.fs, 3.0)
        except Exception as e:
            QMessageBox.warning(self, tr("error"), tr("audio_error", e=e)); return
        self._apply_tone(x[int(0.3 * self.fs):])

    def _load(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("cal_load"), "", "Audio (*.wav *.flac *.aif *.aiff)")
        if p:
            from ..core.audio_io import load_audio
            x, _ = load_audio(p)
            self._apply_tone(x)

    def apply(self):
        s = self.cfg.analysis
        s.cal_offset_db = float(self.offset.value()) if self.use.isChecked() else None
        s.distance_cm = float(self.dist.value()) or None
        self.cfg.cal_device = self.dev if self.use.isChecked() else None
        self.cfg.save()


BUZZ_EN = "<b>Buzz</b> is the author's own experimental measure, not validated in the literature."


def about_html():
    pt = lang() == "pt"
    return f"""
<h2>{APP_NAME} {__version__}</h2>
<p>{'Medida' if pt else 'Measure'}: <b>Formant Cluster Prominence (FCP)</b> –
Lã FMB, Silva LS, Granqvist S. Long-term average spectrum characteristics of Portuguese Fado-Canção
from Coimbra. <i>Journal of Voice</i> 37(4):631.e7–631.e15, 2023.</p>
<p>{'FCP = maior diferença entre o LTAS e uma reta de tendência ajustada entre 1 e 5 kHz, dentro de 2–4 kHz. '
    'ΔL1–ΔL4 seguem as definições do mesmo artigo.' if pt else
    'FCP = largest difference between the LTAS and a trendline fitted between 1 and 5 kHz, inside 2–4 kHz. '
    'ΔL1–ΔL4 follow the same paper.'}</p>
<p>{'O <b>Buzz</b> é uma medida própria e experimental, ainda não validada na literatura.' if pt else
    BUZZ_EN}</p>
<p>{'Autor' if pt else 'Author'}: Tiago Lima Bicalho Cruz, PhD · fonotechacademy@gmail.com</p>
<p>{'Licença' if pt else 'License'}: Apache 2.0 – {'uso livre, com crédito ao autor (arquivo NOTICE).' if pt else
    'free use with credit to the author (NOTICE file).'}</p>
<p>{'Bibliotecas' if pt else 'Libraries'}: Praat/Parselmouth (GPL), NumPy, SciPy, PySide6 (LGPL), pyqtgraph, sounddevice, soundfile, Matplotlib.</p>
"""


class AboutDialog(QDialog):
    def __init__(self, logo_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about"))
        self.resize(620, 520)
        lay = QVBoxLayout(self)
        if logo_path and os.path.exists(logo_path):
            l = QLabel(); l.setPixmap(QPixmap(logo_path).scaledToHeight(110, Qt.SmoothTransformation))
            l.setAlignment(Qt.AlignCenter); lay.addWidget(l)
        t = QTextBrowser(); t.setOpenExternalLinks(True); t.setHtml(about_html())
        lay.addWidget(t)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.reject)
        lay.addWidget(bb)
