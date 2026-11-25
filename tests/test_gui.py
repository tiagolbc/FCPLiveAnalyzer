"""GUI smoke test (offscreen): load a file, seek, render, export."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_main_window_file_flow(app, tmp_path):
    from fcp_analyzer.gui.config import AppConfig
    from fcp_analyzer.gui import i18n
    from fcp_analyzer.gui.main_window import MainWindow
    from fcp_analyzer.core import AnalysisSettings, analyse_signal
    from fcp_analyzer.synth import Envelope, harmonic_phrase

    cfg = AppConfig()
    cfg.path = str(tmp_path / "s.json")
    cfg.exports_dir = str(tmp_path / "exp")
    i18n.set_language("en")
    w = MainWindow(cfg)
    x = harmonic_phrase(Envelope(-12, [(3000, 12, 0.1)], lowpass_hz=9000), 22050, 5.0)
    fa = analyse_signal(x, 22050, AnalysisSettings(), path=str(tmp_path / "syn.wav"))
    w._file_ready(fa)
    assert w.mode == "file"
    w.seek(3.0)
    assert w._last_idx == fa.index_at(3.0)
    assert w.card_fcp.value.text().endswith("dB")
    w._export_to(str(tmp_path / "out"), quiet=True)
    assert (tmp_path / "out" / "summary.csv").exists()
    w.close()
