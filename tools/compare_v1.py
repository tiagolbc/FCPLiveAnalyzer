"""Compare v1.2.1 and v2.0 results on WAV files.

Usage:  python tools/compare_v1.py file1.wav [file2.wav ...]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fcp_analyzer.core import AnalysisSettings, analyse_signal  # noqa: E402
from fcp_analyzer.core.audio_io import load_audio  # noqa: E402
from fcp_analyzer.core.legacy import legacy_global  # noqa: E402


def main(paths):
    print(f"{'file':28s} {'v1 FCP':>8s} {'v2 sopran':>10s} {'v2 praat':>9s} {'v1 Delta_0_2_2_5':>17s} {'v2 dL1':>7s}")
    for p in paths:
        x, fs = load_audio(p)
        v1 = legacy_global(x * 32767, fs)
        a = analyse_signal(x, fs, AnalysisSettings()).global_result.measures
        b = analyse_signal(x, fs, AnalysisSettings(engine="praat")).global_result.measures
        print(f"{os.path.basename(p)[:28]:28s} {v1['fcp']:8.2f} {a.fcp_db:10.2f} {b.fcp_db:9.2f} "
              f"{v1.get('Delta_0_2_2_5', float('nan')):17.2f} {a.dl1:7.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
