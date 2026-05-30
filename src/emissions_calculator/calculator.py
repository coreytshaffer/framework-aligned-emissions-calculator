from typing import Dict, List
from .models import EmissionFactor, EmissionResult, InventorySummary

class UnknownActivityError(ValueError):
    """Exception raised when an input activity type is not recognized in the loaded factors database."""
    pass

def calculate_emissions(activity_value: float, factor: EmissionFactor) -> float:
    """Calculates emissions by multiplying activity data by the emission factor.

    Formula:
        Activity Data * Emission Factor = Greenhouse Gas Emissions (MT CO2e)

    Args:
        activity_value: The numerical activity value (e.g. 500 therms).
        factor: The EmissionFactor instance to use.

    Returns:
        The calculated greenhouse gas emissions in metric tons CO2e.

    Raises:
        ValueError: If activity_value is negative.
    """
    if activity_value < 0:
        raise ValueError(
            f"Activity value cannot be negative. Provided: {activity_value} "
            f"for activity type: '{factor.activity_type}'"
        )
    return float(activity_value * factor.factor_value)

def calculate_inventory(
    activity_inputs: Dict[str, float], 
    factors: Dict[str, EmissionFactor],
    factor_file: str = "emission_factors.json"
) -> List[EmissionResult]:
    """Calculates the individual emissions for a dictionary of activity inputs.

    Args:
        activity_inputs: Dict mapping activity keys (e.g. 'natural_gas') to numerical values.
        factors: Dict mapping activity keys to EmissionFactor instances.
        factor_file: Optional filename of the factor database used for calculations.

    Returns:
        A list of EmissionResult instances representing the calculations.

    Raises:
        UnknownActivityError: If an activity type in the inputs is not present in factors.
        ValueError: If any input activity value is negative.
    """
    results: List[EmissionResult] = []

    for activity_type, raw_value in activity_inputs.items():
        if activity_type not in factors:
            raise UnknownActivityError(
                f"Unknown activity type: '{activity_type}'. "
                f"Available activity types are: {', '.join(factors.keys())}"
            )
        
        # Safely treat missing / None values as 0.0
        activity_value = 0.0 if raw_value is None else float(raw_value)

        factor = factors[activity_type]
        emissions = calculate_emissions(activity_value, factor)

        result = EmissionResult(
            activity_type=activity_type,
            scope=factor.scope,
            activity_value=activity_value,
            input_unit=factor.input_unit,
            emissions_mt_co2e=emissions,
            factor_value=factor.factor_value,
            factor_unit=factor.factor_unit,
            source_name=factor.source_name,
            source_reference=factor.source_reference,
            factor_year=factor.source_year,
            factor_file=factor_file
        )
        results.append(result)

    return results

def summarize_by_scope(
    facility_name: str, 
    reporting_year: int, 
    results: List[EmissionResult]
) -> InventorySummary:
    """Aggregates individual emission results into direct (Scope 1) and indirect (Scope 2) totals.

    Args:
        facility_name: Name of the facility.
        reporting_year: Reporting calendar year.
        results: A list of EmissionResult objects to summarize.

    Returns:
        An InventorySummary detailing totals and percentages by scope.
    """
    scope_1_total = 0.0
    scope_2_total = 0.0

    for res in results:
        if res.scope == 1:
            scope_1_total += res.emissions_mt_co2e
        elif res.scope == 2:
            scope_2_total += res.emissions_mt_co2e

    grand_total = scope_1_total + scope_2_total

    if grand_total > 0:
        scope_1_percentage = (scope_1_total / grand_total) * 100.0
        scope_2_percentage = (scope_2_total / grand_total) * 100.0
    else:
        scope_1_percentage = 0.0
        scope_2_percentage = 0.0

    return InventorySummary(
        facility_name=facility_name,
        reporting_year=reporting_year,
        results=results,
        scope_1_total=round(scope_1_total, 4),
        scope_2_total=round(scope_2_total, 4),
        grand_total=round(grand_total, 4),
        scope_1_percentage=round(scope_1_percentage, 2),
        scope_2_percentage=round(scope_2_percentage, 2)
    )
