import pytest
from src.emissions_calculator.models import EmissionFactor
from src.emissions_calculator.calculator import (
    calculate_emissions,
    calculate_inventory,
    summarize_by_scope,
    UnknownActivityError
)

@pytest.fixture
def sample_factors():
    """Returns a dictionary of mock emission factors for testing."""
    return {
        "natural_gas": EmissionFactor(
            source_name="Test EPA",
            activity_type="natural_gas",
            scope=1,
            input_unit="therms",
            factor_value=0.005306,
            factor_unit="metric tons CO2e / therm",
            gas_basis="CO2e",
            source_reference="Ref A",
            source_year=2023,
            notes="Note NG"
        ),
        "diesel_fuel": EmissionFactor(
            source_name="Test EPA",
            activity_type="diesel_fuel",
            scope=1,
            input_unit="gallons",
            factor_value=0.01021,
            factor_unit="metric tons CO2e / gallon",
            gas_basis="CO2e",
            source_reference="Ref B",
            source_year=2023,
            notes="Note DF"
        ),
        "electricity": EmissionFactor(
            source_name="Test eGRID",
            activity_type="electricity",
            scope=2,
            input_unit="kWh",
            factor_value=0.000371,
            factor_unit="metric tons CO2e / kWh",
            gas_basis="CO2e",
            source_reference="Ref C",
            source_year=2023,
            notes="Note EL"
        )
    }

def test_basic_multiplication(sample_factors):
    """Verify that calculation mathematically multiplies activity_value * factor_value."""
    ng_factor = sample_factors["natural_gas"]
    emissions = calculate_emissions(100.0, ng_factor)
    assert emissions == pytest.approx(100.0 * 0.005306)

def test_negative_input_rejection(sample_factors):
    """Verify that negative activity inputs are rejected with a ValueError."""
    ng_factor = sample_factors["natural_gas"]
    with pytest.raises(ValueError) as exc_info:
        calculate_emissions(-10.0, ng_factor)
    assert "cannot be negative" in str(exc_info.value).lower()

    # Test via calculate_inventory as well
    with pytest.raises(ValueError) as exc_info:
        calculate_inventory({"natural_gas": -5.0}, sample_factors)
    assert "cannot be negative" in str(exc_info.value).lower()

def test_scope_categorization(sample_factors):
    """Verify that scope categorizations match standard rules: direct/indirect Scope 1 & 2."""
    results = calculate_inventory(
        {
            "natural_gas": 1000.0,
            "diesel_fuel": 500.0,
            "electricity": 2000.0
        },
        sample_factors
    )

    results_dict = {res.activity_type: res for res in results}

    assert results_dict["natural_gas"].scope == 1
    assert results_dict["diesel_fuel"].scope == 1
    assert results_dict["electricity"].scope == 2

def test_inventory_totals_and_percentages(sample_factors):
    """Verify that the inventory summaries aggregate properly by scope and calculate percentage contributions."""
    activity_data = {
        "natural_gas": 10000.0,  # Scope 1: 10000 * 0.005306 = 53.06
        "diesel_fuel": 1000.0,   # Scope 1: 1000 * 0.01021 = 10.21
        "electricity": 50000.0   # Scope 2: 50000 * 0.000371 = 18.55
    }
    
    results = calculate_inventory(activity_data, sample_factors)
    summary = summarize_by_scope("Springfield Factory", 2025, results)

    # Expected values
    expected_s1 = 53.06 + 10.21  # 63.27
    expected_s2 = 18.55         # 18.55
    expected_total = expected_s1 + expected_s2  # 81.82
    expected_s1_pct = (expected_s1 / expected_total) * 100.0
    expected_s2_pct = (expected_s2 / expected_total) * 100.0

    assert summary.facility_name == "Springfield Factory"
    assert summary.reporting_year == 2025
    assert summary.scope_1_total == pytest.approx(expected_s1)
    assert summary.scope_2_total == pytest.approx(expected_s2)
    assert summary.grand_total == pytest.approx(expected_total)
    assert summary.scope_1_percentage == pytest.approx(expected_s1_pct, abs=0.01)
    assert summary.scope_2_percentage == pytest.approx(expected_s2_pct, abs=0.01)

def test_missing_values_safe_treatment(sample_factors):
    """Verify that missing/None values are safely treated as 0.0 without crash."""
    results = calculate_inventory(
        {
            "natural_gas": None,
            "electricity": 10000.0
        },
        sample_factors
    )
    
    results_dict = {res.activity_type: res for res in results}
    assert results_dict["natural_gas"].activity_value == 0.0
    assert results_dict["natural_gas"].emissions_mt_co2e == 0.0
    assert results_dict["electricity"].activity_value == 10000.0
    assert results_dict["electricity"].emissions_mt_co2e == pytest.approx(10000.0 * 0.000371)

def test_unknown_activity_type_error(sample_factors):
    """Verify that an unknown activity type produces a clear custom exception."""
    with pytest.raises(UnknownActivityError) as exc_info:
        calculate_inventory({"wood_waste": 100.0}, sample_factors)
    assert "unknown activity type" in str(exc_info.value).lower()

def test_zero_emissions_totals_graceful_handling(sample_factors):
    """Verify that if grand total is zero, we avoid DivisionByZero and return 0.0 percentages."""
    results = calculate_inventory(
        {
            "natural_gas": 0.0,
            "electricity": 0.0
        },
        sample_factors
    )
    summary = summarize_by_scope("Empty Facility", 2025, results)
    assert summary.scope_1_total == 0.0
    assert summary.scope_2_total == 0.0
    assert summary.grand_total == 0.0
    assert summary.scope_1_percentage == 0.0
    assert summary.scope_2_percentage == 0.0


def test_factor_provenance_propagation(sample_factors):
    """Verify that calculate_inventory propagates factor_year and factor_file correctly."""
    custom_file = "test_custom_factors_v2.json"
    results = calculate_inventory(
        {
            "natural_gas": 1500.0,
            "electricity": 3200.0
        },
        sample_factors,
        factor_file=custom_file
    )
    
    results_dict = {res.activity_type: res for res in results}
    
    # Assert natural gas values propagated properly
    ng_res = results_dict["natural_gas"]
    assert ng_res.factor_year == 2023
    assert ng_res.factor_file == custom_file
    assert ng_res.factor_value == 0.005306
    
    # Assert electricity values propagated properly
    elec_res = results_dict["electricity"]
    assert elec_res.factor_year == 2023
    assert elec_res.factor_file == custom_file
    assert elec_res.factor_value == 0.000371


def test_activity_specific_factor_file_mapping(sample_factors):
    """Verify mixed factor sources can be preserved in result provenance."""
    file_map = {
        "natural_gas": "emission_factors.json",
        "diesel_fuel": "emission_factors.json",
        "electricity": "egrid2023_subregion_factors.json",
    }

    results = calculate_inventory(
        {"natural_gas": 100.0, "electricity": 1000.0},
        sample_factors,
        factor_file=file_map,
    )
    results_dict = {res.activity_type: res for res in results}

    assert results_dict["natural_gas"].factor_file == "emission_factors.json"
    assert results_dict["electricity"].factor_file == "egrid2023_subregion_factors.json"

def test_factor_file_type_error(sample_factors):
    """Verify that unsupported factor_file types raise a TypeError."""
    with pytest.raises(TypeError) as exc_info:
        calculate_inventory(
            {"natural_gas": 100.0},
            sample_factors,
            factor_file=12345
        )
    assert "must be None, a string, a Path, or a dictionary" in str(exc_info.value)
    
    with pytest.raises(TypeError) as exc_info:
        calculate_inventory(
            {"natural_gas": 100.0},
            sample_factors,
            factor_file=["list", "of", "strings"]
        )
    assert "Got unsupported type: list" in str(exc_info.value)
