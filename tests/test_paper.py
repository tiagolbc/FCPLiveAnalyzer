"""Checks against the numbers published by Lã, Silva & Granqvist (2023), J Voice 37(4).

Table 2 (singing) and Table 3 (reading) list Lmax(0-2), Lmax(2-5), Lmax(5-8) and
ΔL1-ΔL4 for 16 singers. Our delta definitions must reproduce the published ΔL
from the published Lmax (to rounding, 0.1 dB per term -> tolerance 0.25 dB).
"""
import numpy as np
import pytest

from fcp_analyzer.core.metrics import deltas

# Table 2 - singing
SING = dict(
    l02=[-21.9, -34.8, -23.1, -12.8, -19.8, -22.6, -22.6, -21.1, -17.4, -25.6, -20.2, -24.8, -20.5, -21.9, -21.7, -17.7],
    l25=[-43.1, -53.8, -40.9, -31.2, -33.2, -41.1, -47.1, -44.4, -31.1, -31.6, -44.7, -50.1, -34.7, -38.7, -35.8, -25.8],
    l58=[-59.0, -71.5, -59.3, -51.6, -52.8, -58.1, -61.0, -52.5, -46.0, -60.0, -54.7, -63.0, -54.8, -52.3, -59.6, -55.5],
    dl1=[21.3, 19.0, 17.7, 18.4, 13.4, 18.5, 24.5, 23.3, 13.7, 6.0, 24.5, 25.3, 14.3, 16.8, 14.2, 8.1],
    dl2=[15.9, 17.7, 18.5, 20.3, 19.6, 17.0, 13.9, 8.2, 14.9, 28.5, 10.1, 12.9, 20.1, 13.6, 23.8, 29.7],
    dl3=[5.4, 1.2, -0.7, -1.9, -6.2, 1.6, 10.6, 15.1, -1.2, -22.5, 14.4, 12.4, -5.8, 3.2, -9.6, -21.6],
    dl4=[37.1, 36.7, 36.2, 38.7, 33.0, 35.5, 38.4, 31.4, 28.6, 34.4, 34.5, 38.2, 34.3, 30.4, 37.9, 37.8],
)
# Table 3 - reading
READ = dict(
    l02=[-38.4, -36.2, -39.5, -42.7, -45.2, -39.1, -32.1, -29.0, -39.0, -39.3, -41.4, -36.0, -37.3, -36.2, -40.4, -34.8],
    l25=[-64.4, -60.7, -62.4, -71.5, -67.8, -63.2, -54.6, -51.8, -62.7, -62.7, -67.4, -63.7, -58.6, -59.3, -66.5, -55.5],
    l58=[-77.1, -80.1, -80.9, -85.0, -85.8, -83.8, -68.4, -67.6, -81.3, -77.9, -76.9, -76.5, -82.4, -75.0, -82.4, -79.6],
    dl1=[26.0, 24.5, 22.9, 28.8, 22.6, 24.1, 22.6, 22.7, 23.8, 23.4, 26.0, 27.7, 21.2, 23.1, 26.0, 20.7],
    dl2=[12.7, 19.4, 18.5, 13.5, 18.0, 20.6, 13.7, 15.9, 18.5, 15.1, 9.5, 12.8, 23.8, 15.8, 15.9, 24.2],
    dl4=[38.7, 43.8, 41.4, 42.3, 40.6, 44.7, 36.3, 38.6, 42.3, 38.6, 35.5, 40.5, 45.0, 38.8, 42.0, 44.8],
)


@pytest.mark.parametrize("table", [SING, READ], ids=["table2_singing", "table3_reading"])
def test_deltas_reproduce_published_tables(table):
    l02, l25, l58 = (np.array(table[k]) for k in ("l02", "l25", "l58"))
    d1, d2, d3, d4 = deltas(l02, l25, l58)
    np.testing.assert_allclose(d1, table["dl1"], atol=0.25)
    np.testing.assert_allclose(d2, table["dl2"], atol=0.25)
    np.testing.assert_allclose(d4, table["dl4"], atol=0.25)
    if "dl3" in table:
        np.testing.assert_allclose(d3, table["dl3"], atol=0.35)


def test_v1_delta_columns_had_inverted_sign():
    """v1.2.1 exported Delta_0_2_2_5 = Lmax(2-5) - Lmax(0-2), i.e. -ΔL1."""
    l02, l25 = np.array(SING["l02"]), np.array(SING["l25"])
    v1 = l25 - l02
    d1, *_ = deltas(l02, l25, np.array(SING["l58"]))
    np.testing.assert_allclose(v1, -d1)


def test_table4_mean_differences():
    """Table 4: mean (singing - reading) ΔL1 = -6.7, ΔL2 = 1.0, ΔL4 = -5.6 dB."""
    s = [np.array(SING[k]) for k in ("l02", "l25", "l58")]
    r = [np.array(READ[k]) for k in ("l02", "l25", "l58")]
    ds, dr = deltas(*s), deltas(*r)
    assert np.mean(ds[0] - dr[0]) == pytest.approx(-6.7, abs=0.2)
    assert np.mean(ds[1] - dr[1]) == pytest.approx(1.0, abs=0.2)
    assert np.mean(ds[3] - dr[3]) == pytest.approx(-5.6, abs=0.2)
