import csv
import os

import numpy as np
import pytest

from fcp_analyzer.core import AnalysisSettings, analyse_signal
from fcp_analyzer.core.audio_io import save_wav
from fcp_analyzer.core.batch import run_batch
from fcp_analyzer.core import export
from fcp_analyzer.synth import Envelope, harmonic_phrase

FS = 22050
ENV = Envelope(-12, [(3000, 12, 0.1)], lowpass_hz=9000)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def test_export_bundle_and_delta_signs(tmp_path):
    x = harmonic_phrase(ENV, FS, 6.0)
    fa = analyse_signal(x, FS, AnalysisSettings(), path="synthetic.wav")
    export.export_file_analysis(str(tmp_path), fa)
    for f in ("summary.csv", "windows.csv", "ltas_global.csv", "ltas_global.png", "fcp_timeline.png"):
        assert (tmp_path / f).exists(), f
    row = _read(tmp_path / "summary.csv")[0]
    l02, l25, l58 = (float(row[k]) for k in ("Lmax_0_2_dB", "Lmax_2_5_dB", "Lmax_5_8_dB"))
    assert float(row["dL1_dB"]) == pytest.approx(l02 - l25, abs=0.02)
    assert float(row["dL2_dB"]) == pytest.approx(l25 - l58, abs=0.02)
    assert float(row["dL3_dB"]) == pytest.approx((l02 - l25) - (l25 - l58), abs=0.03)
    assert float(row["dL4_dB"]) == pytest.approx(l02 - l58, abs=0.02)
    assert float(row["dL1_dB"]) > 0          # voice spectra fall with frequency
    assert "engine" in row["settings"]
    w = _read(tmp_path / "windows.csv")
    assert len(w) == len(fa.times)


def test_batch(tmp_path):
    p1 = tmp_path / "a.wav"; p2 = tmp_path / "b.wav"; bad = tmp_path / "bad.wav"
    save_wav(str(p1), harmonic_phrase(ENV, FS, 4.0), FS)
    save_wav(str(p2), harmonic_phrase(Envelope(-12, [], lowpass_hz=9000), FS, 4.0), FS)
    bad.write_bytes(b"not audio")
    out, status = run_batch([str(p1), str(p2), str(bad)], AnalysisSettings(), str(tmp_path / "out"))
    rows = _read(os.path.join(out, "batch_summary.csv"))
    assert len(rows) == 3
    assert float(rows[0]["FCP_dB"]) > float(rows[1]["FCP_dB"]) + 5
    assert "ERROR" in rows[2]["warnings"]
    assert status[2][1] is not None
