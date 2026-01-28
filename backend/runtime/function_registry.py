"""Registry of approved analytical functions for the runtime system."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np


def monte_carlo_sim(
    values: List[float],
    iterations: int = 1000,
    confidence_level: float = 0.9,
) -> Dict[str, Any]:
    """Run Monte Carlo simulation on values.

    Args:
        values: List of numeric values to simulate.
        iterations: Number of simulation iterations (max 10000).
        confidence_level: Confidence level for percentile calculation.

    Returns:
        Dictionary with simulation results.
    """
    # Limit iterations for safety
    iterations = min(iterations, 10000)

    if not values:
        return {"error": "No values provided for simulation"}

    mean_val = np.mean(values)
    std_val = np.std(values) if len(values) > 1 else 0

    # Run simulation
    simulations = np.random.normal(mean_val, std_val, iterations)

    lower_pct = (1 - confidence_level) / 2 * 100
    upper_pct = (1 + confidence_level) / 2 * 100

    return {
        "mean": float(np.mean(simulations)),
        "std": float(np.std(simulations)),
        "min": float(np.min(simulations)),
        "max": float(np.max(simulations)),
        "percentile_10": float(np.percentile(simulations, 10)),
        "percentile_90": float(np.percentile(simulations, 90)),
        "lower_bound": float(np.percentile(simulations, lower_pct)),
        "upper_bound": float(np.percentile(simulations, upper_pct)),
        "iterations": iterations,
        "confidence_level": confidence_level,
    }


def boq_quantity_check(
    boq_items: List[Dict[str, Any]],
    specs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify BOQ quantities against specifications.

    Args:
        boq_items: List of BOQ items with quantity and unit_cost.
        specs: Optional specification requirements.

    Returns:
        Dictionary with quantity analysis.
    """
    if not boq_items:
        return {"error": "No BOQ items provided"}

    specs = specs or {}
    total_items = len(boq_items)
    total_quantity = sum(item.get("quantity", 0) for item in boq_items)
    total_cost = sum(
        item.get("quantity", 0) * item.get("unit_cost", 0) for item in boq_items
    )

    # Check against specs if provided
    items_over = 0
    items_under = 0
    variance_details = []

    for item in boq_items:
        item_id = item.get("id", item.get("description", "unknown"))
        quantity = item.get("quantity", 0)
        spec_qty = specs.get(str(item_id), {}).get("quantity")

        if spec_qty is not None:
            variance = quantity - spec_qty
            variance_pct = (variance / spec_qty * 100) if spec_qty > 0 else 0

            if variance > 0:
                items_over += 1
            elif variance < 0:
                items_under += 1

            variance_details.append({
                "item_id": item_id,
                "quantity": quantity,
                "spec_quantity": spec_qty,
                "variance": variance,
                "variance_pct": variance_pct,
            })

    return {
        "total_items": total_items,
        "total_quantity": total_quantity,
        "total_cost": total_cost,
        "items_over_spec": items_over,
        "items_under_spec": items_under,
        "items_on_spec": total_items - items_over - items_under,
        "variance_details": variance_details[:10],  # Limit details
    }


def cost_variance(
    budget: float,
    actual: float,
    forecast: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate cost variance metrics.

    Args:
        budget: Budgeted cost.
        actual: Actual cost to date.
        forecast: Forecasted total cost (optional).

    Returns:
        Dictionary with cost variance analysis.
    """
    if budget <= 0:
        return {"error": "Budget must be positive"}

    variance = budget - actual
    variance_pct = (variance / budget) * 100

    result = {
        "budget": budget,
        "actual": actual,
        "variance": variance,
        "variance_pct": round(variance_pct, 2),
        "status": "under_budget" if variance >= 0 else "over_budget",
    }

    if forecast is not None:
        at_completion_variance = budget - forecast
        at_completion_variance_pct = (at_completion_variance / budget) * 100
        result.update({
            "forecast": forecast,
            "at_completion_variance": at_completion_variance,
            "at_completion_variance_pct": round(at_completion_variance_pct, 2),
            "forecast_status": "favorable" if at_completion_variance >= 0 else "unfavorable",
        })

    return result


def schedule_slip_forecast(
    tasks: List[Dict[str, Any]],
    baseline: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Forecast schedule delays using earned value analysis.

    Args:
        tasks: List of tasks with planned_value, earned_value, actual_duration.
        baseline: Baseline completion date.

    Returns:
        Dictionary with schedule analysis.
    """
    if not tasks:
        return {"error": "No tasks provided"}

    total_planned = sum(task.get("planned_value", 0) for task in tasks)
    total_earned = sum(task.get("earned_value", 0) for task in tasks)

    # Schedule Performance Index
    spi = total_earned / total_planned if total_planned > 0 else 1.0

    # Schedule Variance (in value terms)
    schedule_variance = total_earned - total_planned
    schedule_variance_pct = (schedule_variance / total_planned * 100) if total_planned > 0 else 0

    # Calculate delay in days
    total_planned_duration = sum(task.get("planned_duration", 0) for task in tasks)
    total_actual_duration = sum(task.get("actual_duration", 0) for task in tasks)

    delay_days = 0
    forecasted_completion = None

    if baseline:
        if isinstance(baseline, str):
            baseline = datetime.fromisoformat(baseline)

        # Estimate delay based on SPI
        if spi > 0 and spi != 1.0:
            remaining_work = total_planned - total_earned
            remaining_duration = (remaining_work / total_earned * total_actual_duration) if total_earned > 0 else 0
            delay_days = int(remaining_duration - (total_planned_duration - total_actual_duration))

        forecasted_completion = baseline + timedelta(days=delay_days)

    return {
        "spi": round(spi, 3),
        "schedule_variance": round(schedule_variance, 2),
        "schedule_variance_pct": round(schedule_variance_pct, 2),
        "total_planned_value": total_planned,
        "total_earned_value": total_earned,
        "delay_days": delay_days,
        "forecasted_completion": forecasted_completion.isoformat() if forecasted_completion else None,
        "status": "ahead" if spi > 1 else ("behind" if spi < 1 else "on_track"),
    }


def pnl_attribution(
    cost_data: Dict[str, float],
    categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate P&L attribution by category.

    Args:
        cost_data: Dictionary mapping category to cost value.
        categories: Optional list of categories to include.

    Returns:
        Dictionary with P&L attribution analysis.
    """
    if not cost_data:
        return {"error": "No cost data provided"}

    # Filter categories if specified
    if categories:
        filtered_data = {k: v for k, v in cost_data.items() if k in categories}
    else:
        filtered_data = cost_data

    total = sum(filtered_data.values())

    # Calculate attribution
    category_impacts = []
    for category, value in sorted(filtered_data.items(), key=lambda x: abs(x[1]), reverse=True):
        pct = (value / total * 100) if total != 0 else 0
        category_impacts.append({
            "category": category,
            "value": value,
            "percentage": round(pct, 2),
            "impact": "positive" if value > 0 else "negative",
        })

    # Get top contributors
    top_positive = [c for c in category_impacts if c["value"] > 0][:3]
    top_negative = [c for c in category_impacts if c["value"] < 0][:3]

    return {
        "total_variance": total,
        "category_count": len(category_impacts),
        "category_impacts": category_impacts,
        "top_positive_contributors": top_positive,
        "top_negative_contributors": top_negative,
    }


def sensitivity_analysis(
    base_value: float,
    variables: Dict[str, float],
    impact_percentages: Optional[List[float]] = None,
) -> Dict[str, Any]:
    """Perform sensitivity analysis on base value.

    Args:
        base_value: The base/baseline value.
        variables: Dictionary of variable names to their weights/impacts.
        impact_percentages: List of percentage changes to test (default: -20%, -10%, 0%, +10%, +20%).

    Returns:
        Dictionary with sensitivity analysis results.
    """
    if impact_percentages is None:
        impact_percentages = [-20, -10, 0, 10, 20]

    results = {}
    for var_name, weight in variables.items():
        impacts = []
        for pct in impact_percentages:
            change = base_value * (pct / 100) * weight
            new_value = base_value + change
            impacts.append({
                "percentage_change": pct,
                "new_value": round(new_value, 2),
                "absolute_change": round(change, 2),
            })
        results[var_name] = {
            "weight": weight,
            "impacts": impacts,
        }

    return {
        "base_value": base_value,
        "variables_analyzed": len(variables),
        "impact_percentages": impact_percentages,
        "results": results,
    }


# Registry of all approved functions with metadata
APPROVED_FUNCTIONS: Dict[str, Dict[str, Any]] = {
    "monte_carlo_sim": {
        "function": monte_carlo_sim,
        "signature": "monte_carlo_sim(values: List[float], iterations: int = 1000, confidence_level: float = 0.9) -> Dict",
        "description": "Run Monte Carlo simulation on a list of values. Returns mean, std, and percentiles.",
        "risk_level": "low",
        "max_runtime": 5.0,
    },
    "boq_quantity_check": {
        "function": boq_quantity_check,
        "signature": "boq_quantity_check(boq_items: List[Dict], specs: Dict = None) -> Dict",
        "description": "Verify BOQ quantities against specifications. Returns variance analysis.",
        "risk_level": "low",
        "max_runtime": 3.0,
    },
    "cost_variance": {
        "function": cost_variance,
        "signature": "cost_variance(budget: float, actual: float, forecast: float = None) -> Dict",
        "description": "Calculate cost variance metrics including at-completion variance.",
        "risk_level": "low",
        "max_runtime": 1.0,
    },
    "schedule_slip_forecast": {
        "function": schedule_slip_forecast,
        "signature": "schedule_slip_forecast(tasks: List[Dict], baseline: datetime = None) -> Dict",
        "description": "Forecast schedule delays using earned value analysis. Returns SPI and delay days.",
        "risk_level": "low",
        "max_runtime": 3.0,
    },
    "pnl_attribution": {
        "function": pnl_attribution,
        "signature": "pnl_attribution(cost_data: Dict[str, float], categories: List[str] = None) -> Dict",
        "description": "Calculate P&L attribution by category. Returns category impacts and top contributors.",
        "risk_level": "low",
        "max_runtime": 2.0,
    },
    "sensitivity_analysis": {
        "function": sensitivity_analysis,
        "signature": "sensitivity_analysis(base_value: float, variables: Dict[str, float], impact_percentages: List[float] = None) -> Dict",
        "description": "Perform sensitivity analysis on base value with multiple variables.",
        "risk_level": "low",
        "max_runtime": 2.0,
    },
}


def get_function(name: str):
    """Get an approved function by name.

    Args:
        name: Function name.

    Returns:
        The function if found, None otherwise.
    """
    entry = APPROVED_FUNCTIONS.get(name)
    return entry["function"] if entry else None


def list_functions() -> List[Dict[str, Any]]:
    """List all approved functions with their metadata.

    Returns:
        List of function metadata dictionaries.
    """
    return [
        {
            "name": name,
            "signature": info["signature"],
            "description": info["description"],
            "risk_level": info["risk_level"],
            "max_runtime": info["max_runtime"],
        }
        for name, info in APPROVED_FUNCTIONS.items()
    ]
