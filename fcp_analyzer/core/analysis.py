"""File, window and live analysis built on one segment accumulator.

The signal is cut into frames (see ``spectral``). Voiced frames are summed per
storage segment (``settings.segment_s``, 100 ms). A window LTAS or the global
LTAS is then a sum of segment sums divided by the number of voiced frames, so
the file analysis, the live analysis and the exported values all come from the
same numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy import signal

from .settings import AnalysisSettings
from .spectral import make_config, frame_powers, power_to_db, SpectralConfig
from .voicing import VoicingTrack, compute_voicing
from .metrics import compute_measures, LtasMeasures
from .calibration import weighting_sos
from . import quality

CLIP_LEVEL = 0.999


class DCBlocker:
    """2nd-order Butterworth high-pass at 20 Hz (removes DC/rumble; same for file and live)."""

    def __init__(self, fs):
        self.sos = signal.butter(2, 20.0, "highpass", fs=fs, output="sos")
        self.zi = np.zeros((self.sos.shape[0], 2))

    def __call__(self, x):
        y, self.zi = signal.sosfilt(self.sos, x, zi=self.zi)
        return y


@dataclass
class LtasResult:
    """LTAS and measures for one time span (a window or the whole recording)."""
    freqs: np.ndarray
    ltas_db: np.ndarray
    measures: LtasMeasures
    t_start: float
    t_end: float
    voiced_s: float
    total_s: float
    leq_c_db: float        # C-weighted Leq of the voiced part (calibrated if settings say so)
    leq_c_all_db: float    # C-weighted Leq of everything
    f0_mean_hz: float      # geometric mean F0 of the voiced frames
    clip_fraction: float
    warnings: list = field(default_factory=list)
    pitch_range_st: float = np.nan

    @property
    def valid(self) -> bool:
        return self.ltas_db is not None and np.isfinite(self.measures.fcp_db)


class SegmentStore:
    """Growable per-segment sums."""

    def __init__(self, nbins: int):
        self.nbins = nbins
        self.n = 0
        cap = 64
        self.P = np.zeros((cap, nbins))
        self.scal = {k: np.zeros(cap) for k in
                     ("nv", "nt", "cw_v", "ns_v", "cw_all", "ns_all", "peak", "nclip", "lf0", "nf0")}

    def ensure(self, nseg: int):
        if nseg <= self.n:
            return
        cap = self.P.shape[0]
        if nseg > cap:
            new = max(nseg, cap * 2)
            P = np.zeros((new, self.nbins)); P[:cap] = self.P; self.P = P
            for k, v in self.scal.items():
                a = np.zeros(new); a[:cap] = v; self.scal[k] = a
        self.n = nseg

    def sums(self, a: int, b: int) -> tuple[np.ndarray, dict]:
        a = max(0, a); b = min(self.n, b)
        if b <= a:
            return np.zeros(self.nbins), {k: 0.0 for k in self.scal}
        return self.P[a:b].sum(axis=0), {k: float(v[a:b].sum()) if k != "peak" else float(v[a:b].max())
                                          for k, v in self.scal.items()}


class SegmentProcessor:
    """Incrementally turns samples into segment sums. Used by files and live input."""

    def __init__(self, fs: int, settings: AnalysisSettings):
        self.fs = int(fs)
        self.s = settings
        self.cfg: SpectralConfig = make_config(fs, settings)
        self.seg_len = max(1, int(round(settings.segment_s * fs)))
        self.store = SegmentStore(self.cfg.nbins)
        self.next_frame = 0          # index k of the next frame (start = k*hop)
        self.next_sample = 0         # next sample for level/clipping sums
        self.cw_sos = weighting_sos(fs, "C")
        self.cw_zi = np.zeros((self.cw_sos.shape[0], 2))

    # ------------------------------------------------------------------
    def process(self, buf: np.ndarray, buf_start: int, voicing: VoicingTrack, final_sample: int,
                raw: np.ndarray | None = None):
        """Consume frames whose centre is < final_sample and samples < final_sample.

        ``buf`` holds samples [buf_start, buf_start + len(buf)).
        """
        cfg, fs, s = self.cfg, self.fs, self.s
        buf_end = buf_start + len(buf)
        final_sample = min(final_sample, buf_end)
        half = cfg.win_len / 2.0
        # frames
        k_last = int(np.floor((final_sample - half - 1e-9) / cfg.hop))
        k_last = min(k_last, (buf_end - cfg.win_len) // cfg.hop)
        if k_last >= self.next_frame:
            ks = np.arange(self.next_frame, k_last + 1)
            starts = ks * cfg.hop
            ok = starts >= buf_start
            ks, starts = ks[ok], starts[ok]
            centers = starts + half
            nseg_needed = int(centers[-1] // self.seg_len) + 1 if len(centers) else 0
            self.store.ensure(nseg_needed)
            t_c = centers / fs
            voiced = voicing.voiced_at(t_c) if s.voiced_only else np.ones(len(ks), bool)
            f0 = voicing.f0_at(t_c)
            seg = (centers // self.seg_len).astype(int)
            np.add.at(self.store.scal["nt"], seg, 1.0)
            chunk = 4096
            for i in range(0, len(ks), chunk):
                sl = slice(i, i + chunk)
                vmask = voiced[sl]
                if not np.any(vmask):
                    continue
                P = frame_powers(buf, cfg, starts[sl][vmask] - buf_start)
                sg = seg[sl][vmask]
                cut = np.concatenate([[0], np.flatnonzero(np.diff(sg)) + 1])
                self.store.P[sg[cut]] += np.add.reduceat(P, cut, axis=0)
                np.add.at(self.store.scal["nv"], sg, 1.0)
            f0ok = voiced & (f0 > 0)
            np.add.at(self.store.scal["lf0"], seg[f0ok], np.log2(f0[f0ok]))
            np.add.at(self.store.scal["nf0"], seg[f0ok], 1.0)
            self.next_frame = int(k_last) + 1
        # sample-level sums (C-weighted level, clipping)
        a = max(self.next_sample, buf_start)
        if final_sample > a:
            x = buf[a - buf_start: final_sample - buf_start]
            y, self.cw_zi = signal.sosfilt(self.cw_sos, x, zi=self.cw_zi)
            idx = np.arange(a, final_sample)
            seg = idx // self.seg_len
            self.store.ensure(int(seg[-1]) + 1)
            sq = y * y
            # voicing at 5 ms resolution
            if s.voiced_only:
                step = max(1, int(round(0.005 * fs)))
                tt = (idx[::step] + step / 2) / fs
                vv = np.repeat(voicing.voiced_at(tt), step)[: len(idx)]
            else:
                vv = np.ones(len(idx), bool)
            nseg = self.store.n
            st = self.store.scal
            st["cw_all"][:nseg] += np.bincount(seg, weights=sq, minlength=nseg)[:nseg]
            st["ns_all"][:nseg] += np.bincount(seg, minlength=nseg)[:nseg]
            st["cw_v"][:nseg] += np.bincount(seg[vv], weights=sq[vv], minlength=nseg)[:nseg]
            st["ns_v"][:nseg] += np.bincount(seg[vv], minlength=nseg)[:nseg]
            ax = np.abs(raw[a - buf_start: final_sample - buf_start]) if raw is not None else np.abs(x)
            st["nclip"][:nseg] += np.bincount(seg[ax >= CLIP_LEVEL], minlength=nseg)[:nseg]
            cut = np.concatenate([[0], np.flatnonzero(np.diff(seg)) + 1])
            sgu = seg[cut]
            st["peak"][sgu] = np.maximum(st["peak"][sgu], np.maximum.reduceat(ax, cut))
            self.next_sample = final_sample

    # ------------------------------------------------------------------
    def result(self, seg_a: int, seg_b: int, *, check_quality=True,
               seg_spectra_for_quality: bool = False) -> LtasResult:
        cfg, s = self.cfg, self.s
        seg_a = max(0, seg_a)
        seg_b = min(self.store.n, seg_b)
        Psum, sc = self.store.sums(seg_a, seg_b)
        t0 = seg_a * self.seg_len / self.fs
        t1 = seg_b * self.seg_len / self.fs
        off = s.level_offset_db()
        voiced_s = sc["nv"] * cfg.hop / self.fs
        total_s = sc["ns_all"] / self.fs
        leq_v = 10 * np.log10(sc["cw_v"] / sc["ns_v"]) + off if sc["ns_v"] > 0 and sc["cw_v"] > 0 else np.nan
        leq_all = 10 * np.log10(sc["cw_all"] / sc["ns_all"]) + off if sc["ns_all"] > 0 and sc["cw_all"] > 0 else np.nan
        f0 = float(2 ** (sc["lf0"] / sc["nf0"])) if sc["nf0"] > 0 else np.nan
        clip = sc["nclip"] / sc["ns_all"] if sc["ns_all"] > 0 else 0.0
        if sc["nv"] > 0:
            mean_fine = Psum / sc["nv"]
            ltas = power_to_db(cfg.finalize(mean_fine), off)
            m = compute_measures(*cfg.measure_view(ltas), s)
        else:
            ltas = np.full(len(cfg.out_freqs), np.nan)
            m = LtasMeasures()
        res = LtasResult(cfg.out_freqs, ltas, m, t0, t1, voiced_s, total_s, float(leq_v),
                         float(leq_all), f0, float(clip))
        if check_quality:
            pr = self.pitch_range_st(seg_a, seg_b) if seg_spectra_for_quality else None
            res.pitch_range_st = pr if pr is not None else np.nan
            res.warnings = quality.assess(res, self.fs, s, pitch_range_st=pr)
        return res

    def pitch_range_st(self, seg_a: int, seg_b: int) -> float:
        """10th-90th percentile range (semitones) of the per-segment mean F0.
        One sustained note gives < ~1 st (vibrato is averaged out); sung phrases give > 5 st."""
        lf = self.store.scal["lf0"][max(0, seg_a):seg_b]
        nf = self.store.scal["nf0"][max(0, seg_a):seg_b]
        ok = nf >= 3
        if np.count_nonzero(ok) < 10:
            return np.nan
        st = 12.0 * lf[ok] / nf[ok]
        return float(np.percentile(st, 90) - np.percentile(st, 10))


# ----------------------------------------------------------------------------
@dataclass
class FileAnalysis:
    path: str
    fs: int
    duration_s: float
    settings: AnalysisSettings
    proc: SegmentProcessor
    global_result: LtasResult
    times: np.ndarray            # end time of each sliding window (s)
    window_measures: list        # LtasMeasures per window (NaN-filled if not enough voice)
    window_ltas: np.ndarray      # (n_windows, n_freqs) float32, NaN rows when invalid
    window_voiced_s: np.ndarray
    window_leq: np.ndarray
    window_f0: np.ndarray
    signal: np.ndarray | None = None

    @property
    def freqs(self):
        return self.proc.cfg.out_freqs

    def index_at(self, t: float) -> int:
        """Window whose end is the last one <= t (what has been heard so far)."""
        if len(self.times) == 0:
            return -1
        i = int(np.searchsorted(self.times, t + 1e-9, side="right") - 1)
        return max(0, min(i, len(self.times) - 1))

    def series(self, name: str) -> np.ndarray:
        return np.array([getattr(m, name) for m in self.window_measures], float)


MIN_WINDOW_VOICED_S = 0.5


def analyse_signal(x: np.ndarray, fs: int, settings: AnalysisSettings, *, path: str = "",
                   progress: Callable[[float], None] | None = None,
                   keep_signal: bool = True) -> FileAnalysis:
    x_raw = np.asarray(x, dtype=float)
    s = settings
    prog = progress or (lambda p: None)
    peak_raw = x_raw  # clipping is judged on the raw samples
    x = DCBlocker(fs)(x_raw) if len(x_raw) else x_raw
    prog(0.02)
    # pitch is computed even when voiced_only is off (F0 is reported)
    voicing = compute_voicing(x, fs, floor=s.pitch_floor_hz, ceiling=s.pitch_ceiling_hz,
                              time_step=s.pitch_time_step_s)
    prog(0.25)
    proc = SegmentProcessor(fs, s)
    # process in blocks of ~5 s so that progress can be reported
    blk = int(5 * fs)
    pos = 0
    n = len(x)
    while pos < n:
        end = min(n, pos + blk)
        proc.process(x, 0, voicing, end if end < n else n, raw=peak_raw)
        pos = end
        prog(0.25 + 0.55 * pos / max(1, n))
    nseg = proc.store.n
    glob = proc.result(0, nseg, seg_spectra_for_quality=True)

    W = max(1, int(round(s.window_s / s.segment_s)))
    cfg = proc.cfg
    P_cum = np.vstack([np.zeros((1, cfg.nbins)), np.cumsum(proc.store.P[:nseg], axis=0)])
    nv_cum = np.concatenate([[0.0], np.cumsum(proc.store.scal["nv"][:nseg])])
    cw_cum = np.concatenate([[0.0], np.cumsum(proc.store.scal["cw_v"][:nseg])])
    nsv_cum = np.concatenate([[0.0], np.cumsum(proc.store.scal["ns_v"][:nseg])])
    lf0_cum = np.concatenate([[0.0], np.cumsum(proc.store.scal["lf0"][:nseg])])
    nf0_cum = np.concatenate([[0.0], np.cumsum(proc.store.scal["nf0"][:nseg])])
    off = s.level_offset_db()
    ends = np.arange(1, nseg + 1)
    starts = np.maximum(0, ends - W)
    nv = nv_cum[ends] - nv_cum[starts]
    voiced_s = nv * cfg.hop / fs
    valid = voiced_s >= MIN_WINDOW_VOICED_S
    nout = len(cfg.out_freqs)
    win_ltas = np.full((nseg, nout), np.nan, dtype=np.float32)
    measures = []
    with np.errstate(divide="ignore", invalid="ignore"):
        leq = 10 * np.log10((cw_cum[ends] - cw_cum[starts]) / (nsv_cum[ends] - nsv_cum[starts])) + off
        f0 = 2 ** ((lf0_cum[ends] - lf0_cum[starts]) / (nf0_cum[ends] - nf0_cum[starts]))
    for i in range(nseg):
        if valid[i]:
            mean_fine = (P_cum[ends[i]] - P_cum[starts[i]]) / nv[i]
            L = power_to_db(cfg.finalize(np.maximum(mean_fine, 0)), off)
            win_ltas[i] = L
            measures.append(compute_measures(*cfg.measure_view(L), s))
        else:
            measures.append(LtasMeasures())
        if i % 50 == 0:
            prog(0.8 + 0.2 * i / max(1, nseg))
    prog(1.0)
    times = ends * proc.seg_len / fs
    return FileAnalysis(path, int(fs), n / fs, s, proc, glob, times, measures, win_ltas,
                        voiced_s, np.where(valid, leq, np.nan), np.where(valid, f0, np.nan),
                        x_raw if keep_signal else None)


def analyse_file(path: str, settings: AnalysisSettings, progress=None) -> FileAnalysis:
    from .audio_io import load_audio
    x, fs = load_audio(path)
    return analyse_signal(x, fs, settings, path=path, progress=progress)


# ----------------------------------------------------------------------------
class LiveAnalyzer:
    """Streaming analysis. Feed blocks of samples; call ``update()`` to process.

    Voicing is computed on a sliding context (``context_s`` before the frames being
    finalised), with ``lookahead_s`` of audio after them, so results lag the input
    by about ``lookahead_s + segment_s``.
    """

    def __init__(self, fs: int, settings: AnalysisSettings, *, context_s=0.6, lookahead_s=0.08,
                 keep_audio=True):
        self.fs = int(fs)
        self.s = settings
        self.proc = SegmentProcessor(fs, settings)
        self.context = int(context_s * fs)
        self.lookahead = int(lookahead_s * fs)
        self.chunks: list[np.ndarray] = []
        self.total = 0                 # samples received
        self.buf = np.zeros(0)
        self.buf_start = 0
        self.keep_audio = keep_audio
        self.done_segments = 0
        self.W = max(1, int(round(settings.window_s / settings.segment_s)))
        self.history: list[tuple[float, LtasResult]] = []
        self.dc = DCBlocker(fs)
        self.rawbuf = np.zeros(0)

    def feed(self, x: np.ndarray):
        x = np.asarray(x, dtype=float).ravel()
        if self.keep_audio:
            self.chunks.append(x.astype(np.float32))
        self.buf = np.concatenate([self.buf, self.dc(x)])
        self.rawbuf = np.concatenate([self.rawbuf, x])
        self.total += len(x)

    def audio(self) -> np.ndarray:
        return np.concatenate(self.chunks) if self.chunks else np.zeros(0)

    def update(self) -> list[LtasResult]:
        """Process what is available. Returns window results for each newly completed segment."""
        s, fs = self.s, self.fs
        final = self.total - self.lookahead
        if final <= self.proc.next_sample + self.proc.seg_len // 2:
            return []
        first_needed = min(self.proc.next_frame * self.proc.cfg.hop, self.proc.next_sample)
        ctx_start = max(self.buf_start, first_needed - self.context)
        x = self.buf[ctx_start - self.buf_start:]
        voicing = compute_voicing(x, fs, floor=s.pitch_floor_hz, ceiling=s.pitch_ceiling_hz,
                                  time_step=s.pitch_time_step_s, t_offset=ctx_start / fs)
        self.proc.process(self.buf, self.buf_start, voicing, final, raw=self.rawbuf)
        # trim buffer
        keep_from = max(0, min(self.proc.next_frame * self.proc.cfg.hop, self.proc.next_sample) - self.context)
        if keep_from > self.buf_start:
            self.buf = self.buf[keep_from - self.buf_start:]
            self.rawbuf = self.rawbuf[keep_from - self.buf_start:]
            self.buf_start = keep_from
        complete = int(self.proc.next_sample // self.proc.seg_len)
        out = []
        for e in range(self.done_segments + 1, complete + 1):
            r = self.proc.result(e - self.W, e)
            self.history.append((e * s.segment_s, r))
            out.append(r)
        self.done_segments = max(self.done_segments, complete)
        return out

    def global_result(self) -> LtasResult:
        return self.proc.result(0, self.done_segments, seg_spectra_for_quality=True)

    def flush(self):
        """Process the remaining audio (end of session)."""
        self.lookahead = 0
        return self.update()
