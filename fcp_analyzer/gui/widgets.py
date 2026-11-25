"""Plots and panels (pyqtgraph for fast redraws)."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget)

from ..core.metrics import fcp_color, fit_trend, FCP_COLOR_BANDS
from . import theme
from .i18n import tr

pg.setConfigOptions(antialias=True, background=theme.PANEL, foreground=theme.MUTED)

TICKS = [100, 200, 500, 1000, 2000, 3000, 4000, 5000, 8000]
TICK_LABELS = ["100", "200", "500", "1k", "2k", "3k", "4k", "5k", "8k"]


def _qc(hex_, alpha=255):
    c = QColor(hex_)
    c.setAlpha(alpha)
    return c


class LtasPlot(pg.PlotWidget):
    """Log-frequency LTAS with trendline, shaded 2-4 kHz band and FCP arrow."""

    def __init__(self, settings):
        super().__init__()
        self.s = settings
        self.setLogMode(x=True, y=False)
        self.showGrid(x=True, y=True, alpha=0.15)
        self.setLabel("bottom", tr("freq"))
        self.setLabel("left", "dB")
        ax = self.getAxis("bottom")
        ax.setTicks([[(np.log10(t), l) for t, l in zip(TICKS, TICK_LABELS)]])
        self.setXRange(np.log10(60), np.log10(10000), padding=0)
        self.setMouseEnabled(x=False, y=True)
        self.legend = self.addLegend(offset=(-10, 10), labelTextColor=theme.MUTED)
        self.band = pg.LinearRegionItem(values=(np.log10(2000), np.log10(4000)), movable=False,
                                        brush=_qc("#3b82f6", 30), pen=pg.mkPen(None))
        self.band.setZValue(-10)
        self.addItem(self.band)
        self.buzz_band = pg.LinearRegionItem(values=(np.log10(5000), np.log10(8000)), movable=False,
                                             brush=_qc(theme.BUZZ, 22), pen=pg.mkPen(None))
        self.buzz_band.setZValue(-11)
        self.addItem(self.buzz_band)
        self.buzz_band.setVisible(False)
        self.global_curve = self.plot(pen=pg.mkPen(theme.GLOBAL_CURVE, width=1.4), name=tr("curve_global"))
        self.curve = self.plot(pen=pg.mkPen(theme.LTAS_CURVE, width=2.4), name=tr("curve_window"))
        self.trend = self.plot(pen=pg.mkPen(theme.TREND, width=1.6, style=Qt.DashLine), name=tr("curve_trend"))
        self.arrow = self.plot(pen=pg.mkPen("#ffffff", width=3))
        self.fcp_text = pg.TextItem(anchor=(0, 1), color=theme.TEXT)
        self.fcp_text.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.addItem(self.fcp_text)
        self.lmax_dots = self.plot(pen=None, symbol="o", symbolSize=8, symbolBrush=_qc("#94a3b8"),
                                   symbolPen=None)
        self._yrange = None

    def set_ylabel(self, unit):
        self.setLabel("left", unit)

    def clear_data(self):
        for c in (self.curve, self.global_curve, self.trend, self.arrow):
            c.setData([], [])
        self.fcp_text.setText("")
        self.lmax_dots.setData([], [])

    def show_result(self, freqs, ltas, measures, global_ltas=None, show_buzz=False):
        f = np.asarray(freqs)
        sel = f >= 50
        if ltas is None or not np.any(np.isfinite(ltas)):
            self.curve.setData([], []); self.trend.setData([], []); self.arrow.setData([], [])
            self.fcp_text.setText("")
        else:
            L = np.asarray(ltas, float)
            self.curve.setData(f[sel], L[sel])
            m = measures
            col = fcp_color(m.fcp_db)
            self.band.setBrush(_qc(col, 40))
            if np.isfinite(m.trend_slope_db_oct):
                ft = np.geomspace(self.s.trend_band_hz[0], self.s.trend_band_hz[1], 60)
                self.trend.setData(ft, m.trend_slope_db_oct * np.log2(ft) + m.trend_intercept_db)
            else:
                self.trend.setData([], [])
            if np.isfinite(m.fcp_db):
                tf = m.trend_slope_db_oct * np.log2(m.fcp_freq_hz) + m.trend_intercept_db
                self.arrow.setData([m.fcp_freq_hz, m.fcp_freq_hz], [tf, tf + m.fcp_db])
                self.arrow.setPen(pg.mkPen(col, width=3))
                self.fcp_text.setText(f" FCP {m.fcp_db:.1f} dB")
                self.fcp_text.setColor(col)
                self.fcp_text.setPos(np.log10(m.fcp_freq_hz * 1.03), tf + m.fcp_db + 2)
            else:
                self.arrow.setData([], []); self.fcp_text.setText("")
            pts = []
            for v, lo, hi in ((m.lmax_0_2, 50, 2000), (m.lmax_2_5, 2000, 5000), (m.lmax_5_8, 5000, 8000)):
                if np.isfinite(v):
                    band = (f >= lo) & (f <= hi) & np.isfinite(L)
                    if np.any(band):
                        i = np.argmin(np.abs(np.where(band, L, np.inf) - v))
                        pts.append((f[i], v))
            if pts:
                self.lmax_dots.setData([p[0] for p in pts], [p[1] for p in pts])
            self._autoscale(L[sel])
        if global_ltas is not None and np.any(np.isfinite(global_ltas)):
            self.global_curve.setData(f[sel], np.asarray(global_ltas)[sel])
        else:
            self.global_curve.setData([], [])
        self.buzz_band.setVisible(bool(show_buzz))
        self.buzz_band.setRegion((np.log10(self.s.buzz_band_hz[0]), np.log10(self.s.buzz_band_hz[1])))

    def _autoscale(self, L):
        fin = L[np.isfinite(L)]
        if not fin.size:
            return
        top = np.ceil((fin.max() + 6) / 5) * 5
        # hysteresis: avoid jumping every frame
        if self._yrange is None or abs(self._yrange[1] - top) >= 10:
            self._yrange = (top - 75, top)
            self.setYRange(*self._yrange, padding=0)


class TimelinePlot(pg.PlotWidget):
    """FCP (and optionally Buzz) over time, waveform envelope, playhead. Click to seek."""
    seek = Signal(float)

    def __init__(self):
        super().__init__()
        self.showGrid(x=True, y=True, alpha=0.12)
        self.setLabel("bottom", tr("time"))
        self.setLabel("left", "FCP (dB)")
        self.setMouseEnabled(x=True, y=False)
        self.env_item = pg.PlotDataItem(pen=pg.mkPen(None), fillLevel=0, brush=_qc("#64748b", 70))
        self.addItem(self.env_item)
        self.fcp_curve = self.plot(pen=pg.mkPen(theme.ACCENT, width=2))
        self.buzz_curve = self.plot(pen=pg.mkPen(theme.BUZZ, width=1.2))
        self.global_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("#e5e7eb", width=1, style=Qt.DashLine))
        self.global_line.setVisible(False)
        self.addItem(self.global_line)
        self.playhead = pg.InfiniteLine(angle=90, pen=pg.mkPen("#ef4444", width=2))
        self.addItem(self.playhead)
        self.scene().sigMouseClicked.connect(self._clicked)
        self._duration = 0.0

    def set_file(self, times, fcp, buzz, signal, fs, global_fcp, show_buzz):
        self._duration = len(signal) / fs if signal is not None else float(times[-1] if len(times) else 0)
        self.fcp_curve.setData(times, fcp, connect="finite")
        self.buzz_curve.setData(times, buzz if show_buzz else [], connect="finite")
        self._set_env(signal, fs, fcp)
        self._set_global(global_fcp)
        self.setXRange(0, max(1.0, self._duration), padding=0.01)

    def _set_env(self, x, fs, fcp):
        if x is None or len(x) == 0:
            self.env_item.setData([], [])
            return
        hop = max(1, int(0.02 * fs))
        n = len(x) // hop
        env = np.abs(x[: n * hop]).reshape(n, hop).max(axis=1)
        env_db = 20 * np.log10(np.maximum(env, 1e-5))
        fin = np.asarray(fcp)[np.isfinite(fcp)]
        top = (fin.max() if fin.size else 20)
        h = (env_db + 60).clip(0) / 60 * max(5.0, top * 0.35)
        self.env_item.setData(np.arange(n) * hop / fs, h)

    def _set_global(self, g):
        if g is not None and np.isfinite(g):
            self.global_line.setPos(g); self.global_line.setVisible(True)
        else:
            self.global_line.setVisible(False)

    def set_live(self, times, fcp, buzz, global_fcp, show_buzz, span=30.0):
        self.env_item.setData([], [])
        self.fcp_curve.setData(times, fcp, connect="finite")
        self.buzz_curve.setData(times, buzz if show_buzz else [], connect="finite")
        self._set_global(global_fcp)
        t = times[-1] if len(times) else 0.0
        self.setXRange(max(0, t - span), max(span, t), padding=0)
        self.playhead.setPos(t)

    def set_time(self, t):
        self.playhead.setPos(t)

    def _clicked(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        p = self.plotItem.vb.mapSceneToView(ev.scenePos())
        if self._duration > 0:
            self.seek.emit(float(np.clip(p.x(), 0, self._duration)))


class ScatterPlot(pg.PlotWidget):
    def __init__(self):
        super().__init__()
        self.showGrid(x=True, y=True, alpha=0.15)
        self.setLabel("bottom", "FCP (dB)")
        self.setLabel("left", "Buzz (experimental, dB)")
        self.sc = pg.ScatterPlotItem(size=6, brush=_qc(theme.ACCENT, 150), pen=pg.mkPen(None))
        self.addItem(self.sc)
        self.cur = pg.ScatterPlotItem(size=14, brush=_qc("#ef4444"), pen=pg.mkPen("w"))
        self.addItem(self.cur)
        self.txt = pg.TextItem(anchor=(0, 0), color=theme.TEXT)
        self.addItem(self.txt)

    def set_data(self, fcp, buzz):
        f, b = np.asarray(fcp, float), np.asarray(buzz, float)
        ok = np.isfinite(f) & np.isfinite(b)
        self.sc.setData(f[ok], b[ok])
        if ok.sum() >= 3 and np.std(f[ok]) > 0 and np.std(b[ok]) > 0:
            r = np.corrcoef(f[ok], b[ok])[0, 1]
            self.txt.setText(f"r = {r:.2f}  (n = {ok.sum()})")
            self.txt.setPos(np.nanmin(f[ok]), np.nanmax(b[ok]))
        else:
            self.txt.setText("")

    def set_current(self, f, b):
        if np.isfinite(f) and np.isfinite(b):
            self.cur.setData([f], [b])
        else:
            self.cur.setData([], [])


class Card(QFrame):
    def __init__(self, title, value_style="midValue", badge=None):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        top = QHBoxLayout()
        self.title = QLabel(title); self.title.setObjectName("cardTitle")
        top.addWidget(self.title)
        if badge:
            b = QLabel(badge); b.setObjectName("badge"); top.addWidget(b)
        top.addStretch(1)
        lay.addLayout(top)
        self.value = QLabel("—"); self.value.setObjectName(value_style)
        lay.addWidget(self.value)
        self.sub = QLabel(""); self.sub.setObjectName("muted")
        lay.addWidget(self.sub)

    def set(self, text, color=None, sub=""):
        self.value.setText(text)
        self.value.setStyleSheet(f"color: {color};" if color else "")
        self.sub.setText(sub)


class BandTable(QFrame):
    """Lmax and ΔL values in a compact grid."""

    ROWS = [("Lmax 0–2", "lmax_0_2"), ("Lmax 2–5", "lmax_2_5"), ("Lmax 5–8", "lmax_5_8"),
            ("ΔL1", "dl1"), ("ΔL2", "dl2"), ("ΔL3", "dl3"), ("ΔL4", "dl4")]

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        g = QGridLayout(self)
        g.setContentsMargins(14, 10, 14, 10)
        g.setHorizontalSpacing(18)
        t = QLabel(tr("band_levels")); t.setObjectName("cardTitle")
        g.addWidget(t, 0, 0, 1, 3)
        h1 = QLabel(tr("tbl_window")); h1.setObjectName("muted")
        h2 = QLabel(tr("tbl_global")); h2.setObjectName("muted")
        g.addWidget(h1, 1, 1, Qt.AlignRight); g.addWidget(h2, 1, 2, Qt.AlignRight)
        self.cells = {}
        tips = {"dl1": "Lmax(0–2) − Lmax(2–5)", "dl2": "Lmax(2–5) − Lmax(5–8)", "dl3": "ΔL1 − ΔL2",
                "dl4": "Lmax(0–2) − Lmax(5–8)"}
        for r, (lab, key) in enumerate(self.ROWS, start=2):
            l = QLabel(lab); l.setToolTip(tips.get(key, "dB"))
            g.addWidget(l, r, 0)
            a, b = QLabel("—"), QLabel("—")
            a.setAlignment(Qt.AlignRight); b.setAlignment(Qt.AlignRight)
            g.addWidget(a, r, 1); g.addWidget(b, r, 2)
            self.cells[key] = (a, b)

    def set(self, win, glob):
        for key, (a, b) in self.cells.items():
            for lab, m in ((a, win), (b, glob)):
                v = getattr(m, key) if m is not None else np.nan
                lab.setText(f"{v:.1f}" if np.isfinite(v) else "—")


class ColorLegend(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        t = QLabel(tr("legend_title")); t.setObjectName("muted"); t.setWordWrap(True)
        lay.addWidget(t)
        row = QHBoxLayout()
        lo = 0
        for lim, col in FCP_COLOR_BANDS:
            lab = f"{lo:g}–{lim:g}" if np.isfinite(lim) else f"≥{lo:g}"
            sw = QLabel(f"  {lab} dB  ")
            sw.setStyleSheet(f"background:{col}; color:#0b0d12; border-radius:6px; font-weight:600;")
            row.addWidget(sw)
            lo = lim
        row.addStretch(1)
        lay.addLayout(row)
        r = QLabel(tr("legend_refs")); r.setObjectName("muted"); r.setWordWrap(True)
        lay.addWidget(r)


class LevelMeter(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(70, 10)
        self.db = -90.0
        self.setToolTip("Input peak (dBFS)")

    def set_db(self, db):
        self.db = db
        self.update()

    def paintEvent(self, ev):
        from PySide6.QtGui import QPainter
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.PANEL2))
        frac = np.clip((self.db + 60) / 60, 0, 1)
        col = "#22c55e" if self.db < -12 else ("#f59e0b" if self.db < -1 else "#ef4444")
        p.fillRect(0, 0, int(self.width() * frac), self.height(), QColor(col))
        p.end()
