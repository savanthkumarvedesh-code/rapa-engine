"""
Comprehensive Statistical Index Number Formulas for RAPA Engine.
Formulas Supported for MoSPI Formula Customization Lab:
1. Jevons Geometric Index: Primary UN/ONS standard: exp( (1/n) * sum(ln(p_t/p_0)) ) * 100
2. Carli Arithmetic Index: Arithmetic mean of price relatives: (1/n) * sum(p_t/p_0) * 100
3. Dutot Simple Average Index: Ratio of arithmetic means: (mean(p_t) / mean(p_0)) * 100
4. Laspeyres Index: Base-weighted arithmetic relative: sum(w_i * (p_{i,t}/p_{i,0})) * 100
5. Törnqvist Superlative Index: Weighted geometric index with period average weights
6. Weighted Basket Aggregator: Aggregation across customizable route passenger weights
7. Axiomatic Verification: Time-reversal test (I_0:t * I_t:0 = 10000.0)
"""

import math
from typing import List, Dict, Any, Optional


def geometric_mean(values: List[float]) -> float:
    """Computes geometric mean of positive numbers using log transform."""
    if not values:
        raise ValueError("Cannot compute geometric mean of an empty list.")
    if any(v <= 0 for v in values):
        raise ValueError("All values for geometric mean must be strictly positive.")
    log_sum = sum(math.log(v) for v in values)
    return math.exp(log_sum / len(values))


def jevons_index(current_prices: List[float], base_prices: List[float]) -> float:
    """
    Jevons Index (Primary Official Model, Base = 100.0):
    Geometric mean of matched price relatives: exp( (1/n) * sum( ln(p_t / p_0) ) ) * 100.0
    """
    if not current_prices or not base_prices:
        return 100.0
    gm_t = geometric_mean(current_prices)
    gm_0 = geometric_mean(base_prices)
    return round((gm_t / gm_0) * 100.0, 4)


def carli_index(current_prices: List[float], base_prices: List[float]) -> float:
    """
    Carli Index (Arithmetic mean of price relatives, Base = 100.0):
    I_C = ( (1/n) * sum(p_{i,t} / p_{i,0}) ) * 100.0
    Note: Upward biased; fails the time-reversal test.
    """
    if not current_prices or not base_prices or len(current_prices) != len(base_prices):
        return 100.0
    relatives = [p_t / p_0 for p_t, p_0 in zip(current_prices, base_prices) if p_0 > 0]
    if not relatives:
        return 100.0
    return round((sum(relatives) / len(relatives)) * 100.0, 4)


def dutot_index(current_prices: List[float], base_prices: List[float]) -> float:
    """
    Dutot Index (Ratio of unweighted arithmetic means, Base = 100.0):
    I_D = ( Mean(p_t) / Mean(p_0) ) * 100.0
    """
    if not current_prices or not base_prices:
        return 100.0
    mean_t = sum(current_prices) / len(current_prices)
    mean_0 = sum(base_prices) / len(base_prices)
    return round((mean_t / mean_0) * 100.0, 4)


def naive_arithmetic_index(current_prices: List[float], base_prices: List[float]) -> float:
    """Alias for Dutot Index."""
    return dutot_index(current_prices, base_prices)


def laspeyres_index(current_prices: List[float], base_prices: List[float], item_weights: Optional[List[float]] = None) -> float:
    """
    Laspeyres Price Index (Base-weighted index, Base = 100.0):
    I_L = ( sum(w_i * (p_{i,t} / p_{i,0})) / sum(w_i) ) * 100.0
    """
    if not current_prices or not base_prices or len(current_prices) != len(base_prices):
        return 100.0
    if not item_weights:
        # If no item weights, defaults to Carli
        return carli_index(current_prices, base_prices)

    weighted_relatives = 0.0
    total_w = 0.0
    for p_t, p_0, w in zip(current_prices, base_prices, item_weights):
        if p_0 > 0:
            weighted_relatives += w * (p_t / p_0)
            total_w += w

    if total_w == 0:
        return 100.0
    return round((weighted_relatives / total_w) * 100.0, 4)


def tornqvist_index(current_prices: List[float], base_prices: List[float], weights_base: Optional[List[float]] = None, weights_current: Optional[List[float]] = None) -> float:
    """
    Törnqvist Superlative Index:
    I_T = exp( sum( (w_{i,0} + w_{i,t})/2 * ln(p_{i,t} / p_{i,0}) ) ) * 100.0
    """
    if not current_prices or not base_prices or len(current_prices) != len(base_prices):
        return 100.0
    n = len(current_prices)
    w0 = weights_base if weights_base and len(weights_base) == n else [1.0 / n] * n
    wt = weights_current if weights_current and len(weights_current) == n else w0

    log_sum = 0.0
    for p_t, p_0, w_0, w_t in zip(current_prices, base_prices, w0, wt):
        if p_0 > 0 and p_t > 0:
            avg_w = (w_0 + w_t) / 2.0
            log_sum += avg_w * math.log(p_t / p_0)

    return round(math.exp(log_sum) * 100.0, 4)


def calculate_formula_matrix(current_prices: List[float], base_prices: List[float]) -> Dict[str, Any]:
    """
    Computes all standard econometric index formulas simultaneously for methodology comparison.
    """
    j_val = jevons_index(current_prices, base_prices)
    c_val = carli_index(current_prices, base_prices)
    d_val = dutot_index(current_prices, base_prices)
    l_val = laspeyres_index(current_prices, base_prices)
    t_val = tornqvist_index(current_prices, base_prices)

    return {
        "jevons": {
            "name": "Jevons (Geometric Mean)",
            "value": j_val,
            "type": "Superlative / Geometric",
            "time_reversal_status": "PASSES (Free of chain drift)",
            "policy_recommendation": "Recommended by UN CPI Manual (2020) & UK ONS"
        },
        "carli": {
            "name": "Carli (Arithmetic Relatives)",
            "value": c_val,
            "type": "Arithmetic Mean",
            "time_reversal_status": "FAILS (Upward bias)",
            "bias_vs_jevons": round(c_val - j_val, 2)
        },
        "dutot": {
            "name": "Dutot (Simple Average)",
            "value": d_val,
            "type": "Arithmetic Ratio",
            "time_reversal_status": "FAILS (Sensitive to base price dispersion)",
            "bias_vs_jevons": round(d_val - j_val, 2)
        },
        "laspeyres": {
            "name": "Laspeyres (Base Weighted)",
            "value": l_val,
            "type": "Fixed Base Basket",
            "time_reversal_status": "FAILS (Substitution bias)",
            "bias_vs_jevons": round(l_val - j_val, 2)
        },
        "tornqvist": {
            "name": "Törnqvist (Superlative Weighted)",
            "value": t_val,
            "type": "Superlative Symmetric",
            "time_reversal_status": "PASSES (Second-order Taylor approximation)",
            "bias_vs_jevons": round(t_val - j_val, 2)
        }
    }


def weighted_basket_aggregate(sub_indices: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Aggregates route sub-indices into composite national index using route passenger weights.
    """
    if not sub_indices or not weights:
        return 100.0

    weighted_sum = 0.0
    total_weight = 0.0
    for k, idx in sub_indices.items():
        if k in weights:
            w = weights[k]
            weighted_sum += idx * w
            total_weight += w

    if total_weight == 0:
        return 100.0
    return round(weighted_sum / total_weight, 4)


def verify_time_reversal(p0: List[float], pt: List[float]) -> Dict[str, Any]:
    """
    Axiomatic validation: verifies that Jevons satisfies Time Reversality (I_0:t * I_t:0 = 10000.0)
    and evaluates whether Naive arithmetic average violates it.
    """
    j_fwd = jevons_index(pt, p0)
    j_bwd = jevons_index(p0, pt)
    j_product = round(j_fwd * j_bwd, 4)
    j_passes = math.isclose(j_product, 10000.0, rel_tol=1e-4)

    c_fwd = carli_index(pt, p0)
    c_bwd = carli_index(p0, pt)
    c_product = round(c_fwd * c_bwd, 4)
    c_passes = math.isclose(c_product, 10000.0, rel_tol=1e-4)

    d_fwd = dutot_index(pt, p0)
    d_bwd = dutot_index(p0, pt)
    d_product = round(d_fwd * d_bwd, 4)
    d_passes = math.isclose(d_product, 10000.0, rel_tol=1e-4)

    return {
        "jevons": {
            "forward": j_fwd,
            "backward": j_bwd,
            "product": j_product,
            "passes_time_reversal": j_passes
        },
        "carli": {
            "forward": c_fwd,
            "backward": c_bwd,
            "product": c_product,
            "passes_time_reversal": c_passes
        },
        "dutot": {
            "forward": d_fwd,
            "backward": d_bwd,
            "product": d_product,
            "passes_time_reversal": d_passes
        }
    }
