"""Persistent user configuration (JSON in the user's app-data folder)."""
from __future__ import annotations

import json
import os

from ..core.settings import AnalysisSettings


def config_dir() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = os.path.join(base, "FCP Live Analyzer")
    os.makedirs(d, exist_ok=True)
    return d


def default_exports_dir() -> str:
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(docs if os.path.isdir(docs) else os.path.expanduser("~"), "FCP Live Analyzer", "Exports")


class AppConfig:
    def __init__(self):
        self.path = os.path.join(config_dir(), "settings.json")
        self.analysis = AnalysisSettings()
        self.language = "en"
        self.exports_dir = default_exports_dir()
        self.input_device = None
        self.output_device = None
        self.show_buzz = False
        self.show_global = True
        self.cal_device = None          # device the calibration was made with
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            return
        self.analysis = AnalysisSettings.from_dict(d.get("analysis", {}))
        for k in ("language", "exports_dir", "input_device", "output_device", "show_buzz", "show_global",
                  "cal_device"):
            if k in d:
                setattr(self, k, d[k])

    def save(self):
        d = {"analysis": self.analysis.to_dict(), "language": self.language, "exports_dir": self.exports_dir,
             "input_device": self.input_device, "output_device": self.output_device,
             "show_buzz": self.show_buzz, "show_global": self.show_global, "cal_device": self.cal_device}
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
