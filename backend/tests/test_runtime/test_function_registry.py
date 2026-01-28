"""Tests for the function registry."""

import pytest
from datetime import datetime
from backend.runtime.function_registry import (
    monte_carlo_sim,
    boq_quantity_check,
    cost_variance,
    schedule_slip_forecast,
    pnl_attribution,
    sensitivity_analysis,
    APPROVED_FUNCTIONS,
    get_function,
    list_functions,
)


class TestMonteCarloSim:
    """Test Monte Carlo simulation function."""

    def test_basic_simulation(self):
        """Test basic Monte Carlo simulation."""
        values = [100, 110, 105, 95, 100]
        result = monte_carlo_sim(values, iterations=1000)

        assert "mean" in result
        assert "std" in result
        assert "percentile_10" in result
        assert "percentile_90" in result
        assert result["iterations"] == 1000

    def test_iteration_limit(self):
        """Test that iterations are capped at 10000."""
        values = [100, 200, 300]
        result = monte_carlo_sim(values, iterations=20000)

        assert result["iterations"] == 10000

    def test_empty_values(self):
        """Test with empty values list."""
        result = monte_carlo_sim([])

        assert "error" in result

    def test_single_value(self):
        """Test with single value."""
        result = monte_carlo_sim([100], iterations=100)

        assert "mean" in result
        assert result["mean"] == pytest.approx(100, rel=0.1)

    def test_confidence_level(self):
        """Test custom confidence level."""
        values = [100, 110, 105, 95, 100]
        result = monte_carlo_sim(values, confidence_level=0.95)

        assert "lower_bound" in result
        assert "upper_bound" in result
        assert result["confidence_level"] == 0.95


class TestBOQQuantityCheck:
    """Test BOQ quantity check function."""

    def test_basic_check(self):
        """Test basic BOQ quantity check."""
        boq_items = [
            {"id": 1, "description": "Concrete", "quantity": 100, "unit_cost": 150},
            {"id": 2, "description": "Steel", "quantity": 50, "unit_cost": 2500},
        ]
        result = boq_quantity_check(boq_items)

        assert result["total_items"] == 2
        assert result["total_quantity"] == 150
        assert result["total_cost"] == 100 * 150 + 50 * 2500

    def test_with_specs(self):
        """Test with specification comparison."""
        boq_items = [
            {"id": 1, "quantity": 100, "unit_cost": 150},
            {"id": 2, "quantity": 60, "unit_cost": 2500},
        ]
        specs = {
            "1": {"quantity": 90},  # Over by 10
            "2": {"quantity": 70},  # Under by 10
        }
        result = boq_quantity_check(boq_items, specs)

        assert result["items_over_spec"] == 1
        assert result["items_under_spec"] == 1

    def test_empty_items(self):
        """Test with empty BOQ items."""
        result = boq_quantity_check([])

        assert "error" in result


class TestCostVariance:
    """Test cost variance function."""

    def test_under_budget(self):
        """Test when under budget."""
        result = cost_variance(budget=1000000, actual=800000)

        assert result["variance"] == 200000
        assert result["variance_pct"] == 20
        assert result["status"] == "under_budget"

    def test_over_budget(self):
        """Test when over budget."""
        result = cost_variance(budget=1000000, actual=1200000)

        assert result["variance"] == -200000
        assert result["variance_pct"] == -20
        assert result["status"] == "over_budget"

    def test_with_forecast(self):
        """Test with forecast value."""
        result = cost_variance(budget=1000000, actual=500000, forecast=1100000)

        assert result["forecast"] == 1100000
        assert result["at_completion_variance"] == -100000
        assert result["forecast_status"] == "unfavorable"

    def test_zero_budget(self):
        """Test with zero budget."""
        result = cost_variance(budget=0, actual=100)

        assert "error" in result


class TestScheduleSlipForecast:
    """Test schedule slip forecast function."""

    def test_on_track(self):
        """Test when on track (SPI = 1)."""
        tasks = [
            {"planned_value": 100, "earned_value": 100},
            {"planned_value": 100, "earned_value": 100},
        ]
        result = schedule_slip_forecast(tasks)

        assert result["spi"] == 1.0
        assert result["status"] == "on_track"

    def test_behind_schedule(self):
        """Test when behind schedule (SPI < 1)."""
        tasks = [
            {"planned_value": 100, "earned_value": 80},
            {"planned_value": 100, "earned_value": 70},
        ]
        result = schedule_slip_forecast(tasks)

        assert result["spi"] < 1.0
        assert result["status"] == "behind"

    def test_ahead_of_schedule(self):
        """Test when ahead of schedule (SPI > 1)."""
        tasks = [
            {"planned_value": 100, "earned_value": 120},
            {"planned_value": 100, "earned_value": 110},
        ]
        result = schedule_slip_forecast(tasks)

        assert result["spi"] > 1.0
        assert result["status"] == "ahead"

    def test_empty_tasks(self):
        """Test with empty tasks."""
        result = schedule_slip_forecast([])

        assert "error" in result


class TestPNLAttribution:
    """Test P&L attribution function."""

    def test_basic_attribution(self):
        """Test basic P&L attribution."""
        cost_data = {
            "Materials": 100000,
            "Labor": 80000,
            "Equipment": 30000,
            "Overhead": -10000,
        }
        result = pnl_attribution(cost_data)

        assert result["total_variance"] == 200000
        assert result["category_count"] == 4
        assert len(result["category_impacts"]) == 4

    def test_with_category_filter(self):
        """Test with category filter."""
        cost_data = {
            "Materials": 100000,
            "Labor": 80000,
            "Equipment": 30000,
        }
        result = pnl_attribution(cost_data, categories=["Materials", "Labor"])

        assert len(result["category_impacts"]) == 2

    def test_empty_data(self):
        """Test with empty cost data."""
        result = pnl_attribution({})

        assert "error" in result

    def test_top_contributors(self):
        """Test top contributors are returned."""
        cost_data = {
            "A": 100,
            "B": -50,
            "C": 200,
            "D": -100,
        }
        result = pnl_attribution(cost_data)

        assert len(result["top_positive_contributors"]) <= 3
        assert len(result["top_negative_contributors"]) <= 3


class TestSensitivityAnalysis:
    """Test sensitivity analysis function."""

    def test_basic_analysis(self):
        """Test basic sensitivity analysis."""
        result = sensitivity_analysis(
            base_value=1000000,
            variables={"Material Cost": 0.4, "Labor Cost": 0.3},
        )

        assert result["base_value"] == 1000000
        assert result["variables_analyzed"] == 2
        assert "Material Cost" in result["results"]
        assert "Labor Cost" in result["results"]

    def test_custom_percentages(self):
        """Test with custom impact percentages."""
        result = sensitivity_analysis(
            base_value=1000,
            variables={"Cost": 1.0},
            impact_percentages=[-10, 0, 10],
        )

        assert result["impact_percentages"] == [-10, 0, 10]
        assert len(result["results"]["Cost"]["impacts"]) == 3


class TestFunctionRegistry:
    """Test function registry operations."""

    def test_approved_functions_exist(self):
        """Test that all expected functions exist."""
        expected = [
            "monte_carlo_sim",
            "boq_quantity_check",
            "cost_variance",
            "schedule_slip_forecast",
            "pnl_attribution",
            "sensitivity_analysis",
        ]
        for name in expected:
            assert name in APPROVED_FUNCTIONS

    def test_get_function_exists(self):
        """Test getting an existing function."""
        func = get_function("monte_carlo_sim")
        assert func is not None
        assert callable(func)

    def test_get_function_not_exists(self):
        """Test getting a non-existing function."""
        func = get_function("nonexistent_function")
        assert func is None

    def test_list_functions(self):
        """Test listing all functions."""
        functions = list_functions()
        assert len(functions) >= 5

        for func_info in functions:
            assert "name" in func_info
            assert "signature" in func_info
            assert "description" in func_info
            assert "risk_level" in func_info

    def test_function_metadata(self):
        """Test function metadata is complete."""
        func_info = APPROVED_FUNCTIONS["monte_carlo_sim"]
        assert "function" in func_info
        assert "signature" in func_info
        assert "description" in func_info
        assert "risk_level" in func_info
        assert "max_runtime" in func_info
