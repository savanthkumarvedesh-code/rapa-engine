"""
Unit Tests for Statistical Index Formulas and Axiomatic Validation.
Covers: Jevons, Carli, Dutot, Laspeyres, Törnqvist, and Time-Reversal tests.
"""

import math
import pytest
from index.formulas import (
    geometric_mean,
    jevons_index,
    carli_index,
    dutot_index,
    laspeyres_index,
    tornqvist_index,
    weighted_basket_aggregate,
    verify_time_reversal,
    calculate_formula_matrix
)


def test_geometric_mean_basic():
    vals = [4.0, 9.0]
    assert math.isclose(geometric_mean(vals), 6.0, rel_tol=1e-5)


def test_jevons_homogeneous_price_change():
    p0 = [3000.0, 4000.0, 5000.0]
    pt = [3300.0, 4400.0, 5500.0]  # +10% uniform rise
    assert math.isclose(jevons_index(pt, p0), 110.0, rel_tol=1e-4)
    assert math.isclose(dutot_index(pt, p0), 110.0, rel_tol=1e-4)
    assert math.isclose(carli_index(pt, p0), 110.0, rel_tol=1e-4)


def test_jevons_moderates_outlier_surge():
    p0 = [4000.0, 4000.0, 4000.0]
    pt = [4000.0, 4000.0, 12000.0]  # One extreme surge
    j_idx = jevons_index(pt, p0)
    d_idx = dutot_index(pt, p0)
    c_idx = carli_index(pt, p0)
    assert j_idx < d_idx
    assert j_idx < c_idx


def test_formula_matrix_computation():
    p0 = [3500.0, 4200.0, 6100.0]
    pt = [3800.0, 4900.0, 6500.0]
    fmatrix = calculate_formula_matrix(pt, p0)
    assert "jevons" in fmatrix
    assert "carli" in fmatrix
    assert "dutot" in fmatrix
    assert "laspeyres" in fmatrix
    assert "tornqvist" in fmatrix
    assert fmatrix["jevons"]["value"] > 100.0


def test_time_reversal_axiomatic_test():
    p0 = [3500.0, 4200.0, 6100.0, 7800.0]
    pt = [4100.0, 3900.0, 6800.0, 9200.0]
    res = verify_time_reversal(p0, pt)
    assert res["jevons"]["passes_time_reversal"] is True


def test_weighted_basket_aggregation():
    sub_indices = {"DEL-BOM": 110.0, "DEL-BLR": 120.0}
    weights = {"DEL-BOM": 0.60, "DEL-BLR": 0.40}
    agg = weighted_basket_aggregate(sub_indices, weights)
    assert math.isclose(agg, 114.0, rel_tol=1e-4)
