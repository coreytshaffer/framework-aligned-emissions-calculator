import pytest
from src.emissions_calculator.scope3_models import Scope3EmissionFactor
from src.emissions_calculator.scope3_calculator import (
    calculate_scope3_purchase_emissions,
    calculate_scope3_inventory
)

@pytest.fixture
def sample_scope3_factors():
    """Returns a dictionary of mock Scope 3 emission factors for testing."""
    return {
        "laboratory_supplies": Scope3EmissionFactor(
            factor_key="laboratory_supplies",
            naics_code="325413",
            commodity_name="In-vitro diagnostic substance manufacturing",
            factor_type="SEF+MEF",
            factor_value=0.284,
            factor_unit="kg CO2e / USD2021",
            data_year=2019,
            currency_year=2021,
            publication_year=2023,
            model_version="EPA Supply Chain Factors v1.2",
            gwp_basis="IPCC AR4 100-year GWP",
            notes="Mock lab supplies factor."
        ),
        "office_supplies": Scope3EmissionFactor(
            factor_key="office_supplies",
            naics_code="322230",
            commodity_name="Stationery product manufacturing",
            factor_type="SEF+MEF",
            factor_value=0.148,
            factor_unit="kg CO2e / USD2021",
            data_year=2019,
            currency_year=2021,
            publication_year=2023,
            model_version="EPA Supply Chain Factors v1.2",
            gwp_basis="IPCC AR4 100-year GWP",
            notes="Mock office supplies factor."
        )
    }

def test_scope3_basic_multiplication(sample_scope3_factors):
    """Verify that spend-based calculation mathematically multiplies spend * factor / 1000."""
    lab_factor = sample_scope3_factors["laboratory_supplies"]
    emissions = calculate_scope3_purchase_emissions(5000.0, lab_factor)
    # Expected: (5000 * 0.284) / 1000 = 1.42 MT CO2e
    assert emissions == pytest.approx(1.42)

def test_scope3_negative_spend_rejection(sample_scope3_factors):
    """Verify that negative spend values are strictly rejected."""
    lab_factor = sample_scope3_factors["laboratory_supplies"]
    with pytest.raises(ValueError):
        calculate_scope3_purchase_emissions(-100.0, lab_factor)

def test_scope3_unmapped_factor_handling(sample_scope3_factors):
    """Verify unmapped spend tracking, unmapped warning creation, and zero emission allocation."""
    ledger = [
        {
            "facility_name": "Clear Lake Lab",
            "reporting_year": 2026,
            "supplier_name": "Unknown Supplies LLC",
            "purchase_category": "Specialized Metals",
            "amount_spent_usd": 2500.0,
            "factor_key": "specialized_metals"  # unmapped
        },
        {
            "facility_name": "Clear Lake Lab",
            "reporting_year": 2026,
            "supplier_name": "Lab Supplies Inc",
            "purchase_category": "Lab Supplies",
            "amount_spent_usd": 1000.0,
            "factor_key": "laboratory_supplies"  # mapped
        }
    ]

    summary = calculate_scope3_inventory(ledger, sample_scope3_factors)
    
    assert summary.mapped_spend == 1000.0
    assert summary.unmapped_spend == 2500.0
    # Expected percent mapping: (1000 / 3500) * 100 = 28.57%
    assert summary.percent_spend_mapped == pytest.approx(28.57, abs=0.01)
    
    # Assert grand total emissions only includes mapped row
    # Expected emissions: 1000 * 0.284 / 1000 = 0.284 MT CO2e
    assert summary.grand_total_emissions == pytest.approx(0.284)

    # Verify result row structures
    res_unmapped = [r for r in summary.results if r.calculation_status == "unmapped_factor"][0]
    assert res_unmapped.included_in_total is False
    assert res_unmapped.emissions_mt_co2e == 0.0
    assert "No factor found" in res_unmapped.warning
    assert len(summary.warnings) == 1

    res_mapped = [r for r in summary.results if r.calculation_status == "calculated"][0]
    assert res_mapped.included_in_total is True
    assert res_mapped.emissions_mt_co2e == pytest.approx(0.284)
    assert res_mapped.warning == ""

def test_scope3_supplier_and_category_summarization(sample_scope3_factors):
    """Verify emissions are correctly aggregated by supplier and by purchase category."""
    ledger = [
        {
            "facility_name": "Clear Lake Lab",
            "reporting_year": 2026,
            "supplier_name": "Supplier A",
            "purchase_category": "Laboratory",
            "amount_spent_usd": 1000.0,
            "factor_key": "laboratory_supplies"
        },
        {
            "facility_name": "Clear Lake Lab",
            "reporting_year": 2026,
            "supplier_name": "Supplier A",
            "purchase_category": "Office Products",
            "amount_spent_usd": 2000.0,
            "factor_key": "office_supplies"
        },
        {
            "facility_name": "Clear Lake Lab",
            "reporting_year": 2026,
            "supplier_name": "Supplier B",
            "purchase_category": "Laboratory",
            "amount_spent_usd": 3000.0,
            "factor_key": "laboratory_supplies"
        }
    ]

    summary = calculate_scope3_inventory(ledger, sample_scope3_factors)

    # Supplier A emissions: (1000 * 0.284 + 2000 * 0.148) / 1000 = 0.284 + 0.296 = 0.580
    # Supplier B emissions: 3000 * 0.284 / 1000 = 0.852
    assert summary.total_by_supplier["Supplier A"] == pytest.approx(0.580)
    assert summary.total_by_supplier["Supplier B"] == pytest.approx(0.852)

    # Category "Laboratory" emissions: 4000 * 0.284 / 1000 = 1.136
    # Category "Office Products" emissions: 2000 * 0.148 / 1000 = 0.296
    assert summary.total_by_category["Laboratory"] == pytest.approx(1.136)
    assert summary.total_by_category["Office Products"] == pytest.approx(0.296)
