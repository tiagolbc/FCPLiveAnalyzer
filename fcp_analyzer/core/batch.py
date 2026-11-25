"""Batch analysis of many files (used by the GUI and the command line)."""
from __future__ import annotations

import os
import traceback

import numpy as np

from .analysis import analyse_file
from . import export


def run_batch(paths, settings, out_dir, *, progress=None, per_file_figures=True, lang="en",
              cancelled=lambda: False):
    """Analyse ``paths``; write batch_summary.csv, batch_windows.csv and per-file folders.

    Returns (out_dir, list of (path, error or None)).
    """
    os.makedirs(out_dir, exist_ok=True)
    summary, windows, status = [], [], []
    n = len(paths)
    for i, p in enumerate(paths):
        if cancelled():
            break
        name = os.path.basename(p)
        try:
            def sub(frac, i=i):
                if progress:
                    progress((i + frac) / n, name)
            fa = analyse_file(p, settings, progress=sub)
            wf, wb = fa.series("fcp_db"), fa.series("buzz_db")
            summary.append(export.summary_row(name, fa.duration_s, fa.global_result, settings, wf, wb, lang))
            windows.extend(export.window_rows(name, fa))
            if per_file_figures:
                export.export_file_analysis(os.path.join(out_dir, os.path.splitext(name)[0]), fa, name, lang)
            status.append((p, None))
        except Exception as e:  # keep going
            row = [name] + [np.nan] * (len(export.summary_header()) - 3) + [f"ERROR: {e}", settings.describe()]
            summary.append(row)
            status.append((p, f"{e}\n{traceback.format_exc()}"))
    export.write_rows(os.path.join(out_dir, "batch_summary.csv"), export.summary_header(), summary)
    export.write_rows(os.path.join(out_dir, "batch_windows.csv"), export.window_header(), windows)
    if progress:
        progress(1.0, "")
    return out_dir, status
