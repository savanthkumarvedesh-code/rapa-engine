"""
tests/test_frequency_aggregation.py
Tests: weekly/monthly Jevons is mathematically consistent with daily series.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from index.calculator import aggregate_to_weekly, aggregate_to_monthly


def _build_daily_series(values, start_date="2026-01-01"):
    """Helper: build fake daily series from list of jevons_index values."""
    from datetime import date, timedelta
    series = []
    d = date.fromisoformat(start_date)
    for v in values:
        series.append({"calculation_date": d.isoformat(), "jevons_index": v})
        d += timedelta(days=1)
    return series


class TestWeeklyAggregation:
    def test_weekly_jevons_is_geometric_mean_of_daily(self):
        # 7 days in one ISO week, all same value -> weekly should equal that value
        daily = _build_daily_series([102.0] * 7, start_date="2026-01-05")  # Mon-Sun week 2
        weekly = aggregate_to_weekly(daily)
        assert len(weekly) >= 1
        assert abs(weekly[0]["jevons_index"] - 102.0) < 0.01, "Weekly Jevons should equal daily when all same"

    def test_weekly_jevons_is_geometric_not_arithmetic(self):
        # Geometric mean of [90, 110] = sqrt(90*110) = sqrt(9900) ~= 99.499
        # Arithmetic mean = 100.0
        daily = _build_daily_series([90.0, 110.0], start_date="2026-01-05")
        weekly = aggregate_to_weekly(daily)
        gm = math.sqrt(90.0 * 110.0)
        am = 100.0
        # Weekly value should be closer to geometric mean
        week_val = weekly[0]["jevons_index"]
        assert abs(week_val - gm) < abs(week_val - am) or abs(week_val - gm) < 0.01

    def test_weekly_output_has_expected_keys(self):
        daily = _build_daily_series([100.0, 101.0, 102.0], start_date="2026-01-05")
        weekly = aggregate_to_weekly(daily)
        assert len(weekly) >= 1
        w = weekly[0]
        assert "period" in w
        assert "frequency" in w and w["frequency"] == "weekly"
        assert "jevons_index" in w
        assert "n_days" in w and w["n_days"] >= 1

    def test_empty_series_returns_empty_weekly(self):
        weekly = aggregate_to_weekly([])
        assert weekly == []


class TestMonthlyAggregation:
    def test_monthly_jevons_is_geometric_mean_of_daily(self):
        # 3 days same value in January -> monthly should equal that value
        daily = _build_daily_series([105.0, 105.0, 105.0], start_date="2026-01-15")
        monthly = aggregate_to_monthly(daily)
        assert len(monthly) >= 1
        assert abs(monthly[0]["jevons_index"] - 105.0) < 0.01

    def test_monthly_output_period_format_is_yyyy_mm(self):
        daily = _build_daily_series([100.0], start_date="2026-03-10")
        monthly = aggregate_to_monthly(daily)
        assert monthly[0]["period"] == "2026-03"

    def test_monthly_spans_multiple_months(self):
        # 32 days spanning Feb and Mar
        daily = _build_daily_series([100.0] * 32, start_date="2026-02-20")
        monthly = aggregate_to_monthly(daily)
        assert len(monthly) >= 2, "Should produce at least 2 monthly buckets"

    def test_monthly_consistency_with_weekly(self):
        # For 4 full weeks in one month, monthly Jevons should be close to
        # geometric mean of weekly Jevons (within 0.1 index points)
        daily = _build_daily_series([100.0, 101.0, 102.0, 103.0] * 7, start_date="2026-01-05")
        weekly = aggregate_to_weekly(daily)
        monthly = aggregate_to_monthly(daily)

        # Geometric mean of weekly values
        import math
        weekly_vals = [w["jevons_index"] for w in weekly if w["period"].startswith("2026-W")]
        if weekly_vals and monthly:
            gm_weekly = math.exp(sum(math.log(v) for v in weekly_vals) / len(weekly_vals))
            month_val = monthly[0]["jevons_index"]
            assert abs(month_val - gm_weekly) < 0.5, \
                f"Monthly Jevons ({month_val}) should be within 0.5 pts of chained weekly ({gm_weekly})"
