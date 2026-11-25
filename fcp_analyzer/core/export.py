"""CSV / PNG export. Column names are stable and documented in the manuals."""
from __future__ import annotations

import csv
import os
from datetime import datetime

import numpy as np

from .metrics import fit_trend, fcp_color
from .quality import message

MEASURE_COLS = [
    ("FCP_dB", "fcp_db"), ("FCP_freq_Hz", "fcp_freq_hz"),
    ("Peak_2_4_dB", "peak_2_4_db"), ("Peak_2_4_freq_Hz", "peak_2_4_freq_hz"),
    ("FCP_at_peak_v1_dB", "fcp_at_peak_db"),
    ("Trend_slope_dB_per_oct", "trend_slope_db_oct"), ("Trend_intercept_dB", "trend_intercept_db"),
    ("Lmax_0_2_dB", "lmax_0_2"), ("Lmax_2_5_dB", "lmax_2_5"), ("Lmax_5_8_dB", "lmax_5_8"),
    ("dL1_dB", "dl1"), ("dL2_dB", "dl2"), ("dL3_dB", "dl3"), ("dL4_dB", "dl4"),
    ("Buzz_experimental_dB", "buzz_db"), ("Buzz_experimental_freq_Hz", "buzz_freq_hz"),
]


def _fmt(v, nd=2):
    if v is None:
        return ""
    if isinstance(v, (float, np.floating)):
        return "" if not np.isfinite(v) else f"{float(v):.{nd}f}"
    return v


def timestamped_dir(base: str, prefix: str) -> str:
    d = os.path.join(base, f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    os.makedirs(d, exist_ok=True)
    return d


def write_rows(path: str, header: list[str], rows: list[list]):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([_fmt(v) for v in r])


def summary_header():
    return (["file", "duration_s", "voiced_s", "level_unit", "Leq_C_voiced_dB", "Leq_C_all_dB", "F0_mean_Hz",
             "pitch_range_st"] + [c for c, _ in MEASURE_COLS] +
            ["windows_n", "windows_FCP_mean_dB", "windows_FCP_sd_dB", "windows_r_FCP_Buzz", "warnings", "settings"])


def summary_row(name, duration_s, res, settings, window_fcps=None, window_buzz=None, lang="en"):
    m = res.measures
    wf = np.asarray(window_fcps if window_fcps is not None else [], float)
    wb = np.asarray(window_buzz if window_buzz is not None else [], float)
    ok = np.isfinite(wf)
    r = np.nan
    both = ok & np.isfinite(wb) if len(wb) == len(wf) else np.zeros(0, bool)
    if np.count_nonzero(both) >= 3 and np.std(wf[both]) > 0 and np.std(wb[both]) > 0:
        r = float(np.corrcoef(wf[both], wb[both])[0, 1])
    warn = " | ".join(message(c, p, lang) for c, p in res.warnings)
    return ([name, duration_s, res.voiced_s, settings.level_unit(), res.leq_c_db, res.leq_c_all_db,
             res.f0_mean_hz, res.pitch_range_st] + [getattr(m, k) for _, k in MEASURE_COLS] +
            [int(np.count_nonzero(ok)), float(np.mean(wf[ok])) if ok.any() else np.nan,
             float(np.std(wf[ok], ddof=1)) if ok.sum() > 1 else np.nan, r, warn, settings.describe()])


def window_header():
    return ["file", "t_start_s", "t_end_s", "voiced_s", "Leq_C_voiced_dB", "F0_mean_Hz"] + [c for c, _ in MEASURE_COLS]


def window_rows(name, fa):
    rows = []
    W = fa.settings.window_s
    for i, t in enumerate(fa.times):
        m = fa.window_measures[i]
        rows.append([name, max(0.0, t - W), t, fa.window_voiced_s[i], fa.window_leq[i], fa.window_f0[i]] +
                    [getattr(m, k) for _, k in MEASURE_COLS])
    return rows


def write_ltas_csv(path, freqs, ltas_db, settings, unit):
    tr = fit_trend(freqs, ltas_db, settings.trend_band_hz)
    rows = []
    for f, L in zip(freqs, ltas_db):
        rows.append([f, L, tr(f) if (tr is not None and f > 0) else np.nan])
    write_rows(path, ["freq_Hz", f"LTAS_{unit}", "trendline_1_5kHz"], rows)


# ---------------------------------------------------------------------------- figures
def save_ltas_png(path, res, settings, title="", lang="en"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f, L, m = res.freqs, res.ltas_db, res.measures
    fig, ax = plt.subplots(figsize=(10, 5.2))
    sel = f > 0
    ax.semilogx(f[sel], L[sel], color="black", lw=1.6, label="LTAS")
    tr = fit_trend(f, L, settings.trend_band_hz)
    if tr is not None:
        ft = np.linspace(settings.trend_band_hz[0], settings.trend_band_hz[1], 100)
        ax.semilogx(ft, tr(ft), ":", color="0.3", lw=1.6,
                    label="trendline 1–5 kHz" if lang == "en" else "reta de tendência 1–5 kHz")
        if np.isfinite(m.fcp_db):
            col = fcp_color(m.fcp_db)
            ax.axvspan(*settings.fcp_band_hz, color=col, alpha=0.12)
            ax.annotate("", xy=(m.fcp_freq_hz, m.fcp_db + tr(m.fcp_freq_hz)),
                        xytext=(m.fcp_freq_hz, tr(m.fcp_freq_hz)),
                        arrowprops=dict(arrowstyle="<->", color=col, lw=2))
            ax.text(0.02, 0.95, f"FCP = {m.fcp_db:.1f} dB @ {m.fcp_freq_hz:.0f} Hz", transform=ax.transAxes,
                    va="top", fontsize=12, fontweight="bold", color=col,
                    bbox=dict(boxstyle="round", fc="white", ec=col))
    txt = (f"ΔL1 {m.dl1:.1f}  ΔL2 {m.dl2:.1f}  ΔL3 {m.dl3:.1f}  ΔL4 {m.dl4:.1f} dB")
    ax.text(0.98, 0.95, txt, transform=ax.transAxes, ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    ax.set_xlim(50, min(10000, f.max()))
    finite = L[sel & np.isfinite(L)]
    if finite.size:
        ax.set_ylim(np.nanmax(finite) - 70, np.nanmax(finite) + 8)
    ax.set_xticks([100, 200, 500, 1000, 2000, 3000, 4000, 5000, 8000])
    ax.set_xticklabels(["100", "200", "500", "1k", "2k", "3k", "4k", "5k", "8k"])
    ax.set_xlabel("Frequency (Hz)" if lang == "en" else "Frequência (Hz)")
    ax.set_ylabel(f"Level ({settings.level_unit()})" if lang == "en" else f"Nível ({settings.level_unit()})")
    ax.set_title(title)
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def save_timeline_png(path, times, fcp, buzz=None, title="", lang="en"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.plot(times, fcp, lw=1.8, color="#2563eb", label="FCP")
    if buzz is not None and np.any(np.isfinite(buzz)):
        ax.plot(times, buzz, lw=1.0, color="#9333ea", alpha=0.7,
                label="Buzz (experimental)" if lang == "en" else "Buzz (experimental)")
    ax.set_xlabel("Time (s)" if lang == "en" else "Tempo (s)")
    ax.set_ylabel("dB")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def save_fcp_buzz_png(path, fcp, buzz, title="", lang="en"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f = np.asarray(fcp, float); b = np.asarray(buzz, float)
    ok = np.isfinite(f) & np.isfinite(b)
    if ok.sum() < 3:
        return False
    fig, ax = plt.subplots(figsize=(5.8, 5.2))
    ax.scatter(f[ok], b[ok], s=10, alpha=0.6, color="#2563eb")
    ax.axvline(np.median(f[ok]), ls="--", lw=1, color="0.5")
    ax.axhline(np.median(b[ok]), ls="--", lw=1, color="0.5")
    r = np.corrcoef(f[ok], b[ok])[0, 1] if np.std(f[ok]) > 0 and np.std(b[ok]) > 0 else np.nan
    ax.set_xlabel("FCP (dB)")
    ax.set_ylabel("Buzz (experimental, dB)")
    ax.set_title(f"{title}\nr = {r:.2f}" if np.isfinite(r) else title)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return True


# ---------------------------------------------------------------------------- bundles
def export_file_analysis(out_dir, fa, name=None, lang="en"):
    """Writes summary.csv, windows.csv, ltas.csv and three PNGs. Returns the folder."""
    os.makedirs(out_dir, exist_ok=True)
    name = name or os.path.basename(fa.path) or "signal"
    g = fa.global_result
    s = fa.settings
    wf, wb = fa.series("fcp_db"), fa.series("buzz_db")
    write_rows(os.path.join(out_dir, "summary.csv"), summary_header(),
               [summary_row(name, fa.duration_s, g, s, wf, wb, lang)])
    write_rows(os.path.join(out_dir, "windows.csv"), window_header(), window_rows(name, fa))
    write_ltas_csv(os.path.join(out_dir, "ltas_global.csv"), g.freqs, g.ltas_db, s, s.level_unit())
    save_ltas_png(os.path.join(out_dir, "ltas_global.png"), g, s, title=f"LTAS – {name}", lang=lang)
    save_timeline_png(os.path.join(out_dir, "fcp_timeline.png"), fa.times, wf, wb,
                      title=f"FCP ({s.window_s:g} s) – {name}", lang=lang)
    save_fcp_buzz_png(os.path.join(out_dir, "fcp_vs_buzz.png"), wf, wb, title=name, lang=lang)
    return out_dir
