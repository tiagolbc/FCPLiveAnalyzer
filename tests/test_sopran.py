"""Agreement with Sopran (tolvan.com), the program used by Lã et al. (2023).

Reference values were produced by Tiago Cruz in Sopran on 2026-11-25: Spectrum,
Hanning window, 350 Hz bandwidth ("Window length: 5.7143 ms"), averaging over the
whole file, plus Sopran's own FCP report (FCP, FCP f, slope). Unvoiced parts were
NOT removed, so the app runs with voiced_only=False here.

Sopran labels its frequencies k*fs/(nfft-1) (255 instead of 256), so its FCP
frequency reads 0.4 % higher than the true bin frequency used by the app.
"""
import os

import numpy as np
import pytest

from conftest import ROOT
from fcp_analyzer.core import AnalysisSettings, analyse_file
from fcp_analyzer.core.spectral import make_config

VAL = os.path.join(ROOT, "validation", "sopran")
EX = os.path.join(ROOT, "examples")

# file: (FCP dB, FCP f Hz as labelled by Sopran, slope dB/oct)
SOPRAN = {
    os.path.join(VAL, "val1_noise_cluster.wav"): (10.15, 3112.9, -11.488),
    os.path.join(VAL, "val2_noise_flat.wav"): (0.04, 3977.6, -12.1),
    os.path.join(EX, "tenor_example.wav"): (18.47, 3112.9, -22.449),
    os.path.join(EX, "rock_example.wav"): (2.93, 3977.6, -9.2064),
}


def test_window_length_matches_sopran():
    cfg = make_config(44100, AnalysisSettings())
    assert cfg.win_len / 44100 * 1000 == pytest.approx(5.7143, abs=0.01)


@pytest.mark.parametrize("path", list(SOPRAN), ids=[os.path.basename(p) for p in SOPRAN])
def test_fcp_and_slope_match_sopran(path):
    if not os.path.exists(path):
        pytest.skip("file missing")
    fcp, f_lab, slope = SOPRAN[path]
    m = analyse_file(path, AnalysisSettings(voiced_only=False)).global_result.measures
    assert m.fcp_db == pytest.approx(fcp, abs=0.1)
    assert m.trend_slope_db_oct == pytest.approx(slope, abs=0.05)
    assert m.fcp_freq_hz * 256 / 255 == pytest.approx(f_lab, abs=1.0)


def _read(txt):
    f, L = [], []
    for line in open(txt):
        if line.startswith("#") or not line[0].isdigit():
            continue
        a, b = line.split()
        f.append(float(a)); L.append(float(b))
    return np.array(f), np.array(L)


@pytest.mark.parametrize("stem", ["val1_noise_cluster", "val2_noise_flat", "tenor_example", "rock_example"])
def test_ltas_shape_matches_sopran(stem):
    txt = os.path.join(VAL, stem + ".txt")
    wav = os.path.join(VAL, stem + ".wav")
    if not os.path.exists(wav):
        wav = os.path.join(EX, stem + ".wav")
    fS, LS = _read(txt)
    g = analyse_file(wav, AnalysisSettings(voiced_only=False)).global_result
    true_f = fS * 255 / 256
    Li = np.interp(true_f, g.freqs, g.ltas_db)
    sel = (true_f >= 300) & (true_f <= 8000)
    d = Li[sel] - LS[sel]
    # constant scale difference: Sopran reads 6.02 dB lower (two-sided amplitude); same shape
    assert np.median(d) == pytest.approx(6.02, abs=0.15)
    assert np.max(np.abs(d - np.median(d))) < 0.6
