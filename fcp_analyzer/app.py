"""Application entry point."""
from __future__ import annotations

import os
import sys


def selftest(out_path):
    """Headless check used after building the executable: analyse the bundled example."""
    import json, traceback
    try:
        from .gui.main_window import resource_path
        from .core import AnalysisSettings, analyse_file
        import PySide6.QtWidgets, pyqtgraph, sounddevice, soundfile  # noqa: F401
        fa = analyse_file(resource_path("examples", "tenor_example.wav"), AnalysisSettings())
        m = fa.global_result.measures
        res = {"ok": True, "fcp_db": m.fcp_db, "dl1": m.dl1, "windows": len(fa.times),
               "manual_pt": os.path.exists(resource_path("docs", "Manual_FCP_Live_Analyzer_pt-BR.pdf"))}
    except Exception:
        res = {"ok": False, "error": traceback.format_exc()}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f)
    return 0 if res["ok"] else 1


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--selftest" in argv:
        return selftest(argv[argv.index("--selftest") + 1])
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QApplication, QSplashScreen

    app = QApplication(argv)
    app.setApplicationName("FCP Live Analyzer")
    app.setOrganizationName("Tiago Cruz")

    from .gui.main_window import resource_path
    splash = None
    logo = resource_path("assets", "logo_fcp.png")
    if os.path.exists(logo):
        splash = QSplashScreen(QPixmap(logo).scaledToHeight(360, Qt.SmoothTransformation))
        splash.show()
        app.processEvents()

    from .gui.config import AppConfig
    from .gui import i18n, theme
    cfg = AppConfig()
    i18n.set_language(cfg.language)
    app.setStyleSheet(theme.QSS)
    from .gui.main_window import MainWindow
    win = MainWindow(cfg)
    win.resize(1440, 900)
    win.showMaximized()
    if splash:
        splash.finish(win)
    files = [a for a in argv[1:] if os.path.isfile(a)]
    if files:
        QTimer.singleShot(200, lambda: win.load_path(files[0]))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
