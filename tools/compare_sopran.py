"""Compare LTAS exported from Sopran ("Log spectrum") with the app's sopran engine.

Usage:  python tools/compare_sopran.py validation/sopran [--bwdef -6dB]

For every <name>.txt next to <name>.wav (or in examples/), reads the (frequency, dB)
pairs from the Sopran log, computes FCP/ΔL with the app's measure code, runs the
app on the WAV (voiced-only off and on) and prints the differences.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from fcp_analyzer.core import AnalysisSettings, analyse_file, compute_measures  # noqa: E402

NUM = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")


def read_sopran_log(path):
    f, L = [], []
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line.lstrip().startswith("#"):
                continue
            nums = NUM.findall(line.replace("\t", " "))
            if len(nums) >= 2:
                try:
                    a = float(nums[0].replace(",", ".")); b = float(nums[1].replace(",", "."))
                except ValueError:
                    continue
                if a >= 0 and -300 < b < 300:
                    f.append(a); L.append(b)
    f, L = np.array(f), np.array(L)
    order = np.argsort(f)
    return f[order], L[order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--bwdef", default="-6dB")
    a = ap.parse_args()
    for txt in sorted(glob.glob(os.path.join(a.folder, "*.txt"))):
        stem = os.path.splitext(os.path.basename(txt))[0]
        wav = next((p for p in (os.path.join(a.folder, stem + ".wav"), os.path.join(ROOT, "examples", stem + ".wav"))
                    if os.path.exists(p)), None)
        fS, LS = read_sopran_log(txt)
        if len(fS) < 10:
            print(f"{stem}: could not read spectrum from {txt}")
            continue
        s = AnalysisSettings(bandwidth_definition=a.bwdef)
        mS = compute_measures(fS, LS, s)
        print(f"\n=== {stem}  (Sopran: {len(fS)} points, spacing {np.median(np.diff(fS)):.1f} Hz)")
        print(f"Sopran LTAS -> FCP {mS.fcp_db:.2f} dB @ {mS.fcp_freq_hz:.0f} Hz, slope {mS.trend_slope_db_oct:.2f} | dL1 {mS.dl1:.2f} dL2 {mS.dl2:.2f} dL4 {mS.dl4:.2f}")
        if wav is None:
            continue
        for vo in (False, True):
            s = AnalysisSettings(bandwidth_definition=a.bwdef, voiced_only=vo)
            g = analyse_file(wav, s).global_result
            m = g.measures
            Li = np.interp(fS, g.freqs, g.ltas_db)
            sel = (fS >= 300) & (fS <= 8000)
            d = Li[sel] - LS[sel]
            mg = compute_measures(fS, Li, s)   # app LTAS sampled on Sopran's frequency grid
            print(f"app (voiced_only={vo}) -> FCP {m.fcp_db:.2f} dB @ {m.fcp_freq_hz:.0f} Hz, slope {m.trend_slope_db_oct:.2f} | dL1 {m.dl1:.2f} "
                  f"dL2 {m.dl2:.2f} dL4 {m.dl4:.2f} | shape diff 0.3-8 kHz: offset {np.median(d):+.2f} dB, "
                  f"spread (p95-p5) {np.percentile(d, 95) - np.percentile(d, 5):.2f} dB")
            print(f"   same, on Sopran grid -> FCP {mg.fcp_db:.2f} dB @ {mg.fcp_freq_hz:.0f} Hz, slope {mg.trend_slope_db_oct:.2f} | dL1 {mg.dl1:.2f} dL2 {mg.dl2:.2f} dL4 {mg.dl4:.2f}")


if __name__ == "__main__":
    main()
