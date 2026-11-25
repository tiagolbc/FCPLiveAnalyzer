"""Regression on the three v1.2.1 example recordings (values recorded for v2.0.0)."""
import os

import numpy as np
import pytest

from conftest import EXAMPLES
from fcp_analyzer.core import AnalysisSettings, analyse_file


def _p(n):
    p = os.path.join(EXAMPLES, n)
    if not os.path.exists(p):
        pytest.skip("example missing")
    return p


def test_tenor_has_clear_cluster():
    g = analyse_file(_p("tenor_example.wav"), AnalysisSettings()).global_result
    assert g.measures.fcp_db > 12
    assert 2500 < g.measures.fcp_freq_hz < 3500
    assert "sustained" not in [c for c, _ in g.warnings]


def test_rock_has_less_cluster_than_tenor():
    t = analyse_file(_p("tenor_example.wav"), AnalysisSettings()).global_result.measures.fcp_db
    r = analyse_file(_p("rock_example.wav"), AnalysisSettings()).global_result.measures.fcp_db
    assert t > r + 8


def test_sustained_example_is_flagged():
    g = analyse_file(_p("female_sustained.wav"), AnalysisSettings()).global_result
    codes = [c for c, _ in g.warnings]
    assert "sustained" in codes and "short_ltas" in codes and "high_f0" in codes
