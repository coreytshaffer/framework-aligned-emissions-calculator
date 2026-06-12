import os
import tempfile
import pytest
from src.emissions_calculator.factors import load_emission_factors, FactorLoadError
from src.emissions_calculator.egrid_factors import (
    EgridFactorLoadError,
    build_factor_file_map,
    lb_per_mwh_to_metric_tons_per_kwh,
    load_egrid_subregion_factors,
    normalize_egrid_subregion,
    with_egrid_electricity_factor,
)

def test_load_valid_factors():
    """Verify that loaded factors have correct schema, structures, and mappings."""
    # Resolve the path relative to this test file or use absolute path of the workspace
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    factors_path = os.path.join(base_dir, "data", "emission_factors.json")
    
    factors = load_emission_factors(factors_path)
    
    assert "natural_gas" in factors
    assert "diesel_fuel" in factors
    assert "electricity" in factors
    
    ng_factor = factors["natural_gas"]
    assert ng_factor.scope == 1
    assert ng_factor.input_unit == "therms"
    assert ng_factor.factor_value == 0.005306
    
    elec_factor = factors["electricity"]
    assert elec_factor.scope == 2
    assert elec_factor.input_unit == "kWh"
    assert elec_factor.factor_value == 0.000371

def test_load_nonexistent_file():
    """Verify that trying to load a nonexistent file produces a FactorLoadError."""
    with pytest.raises(FactorLoadError) as exc_info:
        load_emission_factors("nonexistent_factors.json")
    assert "file not found" in str(exc_info.value).lower()

def test_load_malformed_json():
    """Verify that loading an invalid JSON file produces a FactorLoadError."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as f:
        f.write("{invalid_json:")
        f_path = f.name
    
    try:
        with pytest.raises(FactorLoadError) as exc_info:
            load_emission_factors(f_path)
        assert "failed to parse" in str(exc_info.value).lower()
    finally:
        os.remove(f_path)

def test_load_missing_required_keys():
    """Verify that loading a factor missing required fields produces a FactorLoadError."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as f:
        f.write('[{"activity_type": "natural_gas", "scope": 1}]')  # Missing other keys
        f_path = f.name

    try:
        with pytest.raises(FactorLoadError) as exc_info:
            load_emission_factors(f_path)
        assert "missing required keys" in str(exc_info.value).lower()
    finally:
        os.remove(f_path)

def test_load_valid_csv_factors():
    """Verify that valid CSV factors are parsed correctly."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as f:
        f.write("activity_type,scope,input_unit,factor_value,factor_unit,gas_basis,source_reference,source_year,notes,source_name\n")
        f.write("natural_gas,1,therms,0.0053,mt/therm,CO2e,EPA,2024,test,test_source\n")
        f_path = f.name
        
    try:
        factors = load_emission_factors(f_path)
        assert "natural_gas" in factors
        ng_factor = factors["natural_gas"]
        assert ng_factor.scope == 1
        assert ng_factor.factor_value == 0.0053
    finally:
        os.remove(f_path)

def test_load_csv_missing_columns():
    """Verify that CSV with missing required columns raises an error."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".csv") as f:
        f.write("activity_type,scope\n")
        f.write("natural_gas,1\n")
        f_path = f.name
        
    try:
        with pytest.raises(FactorLoadError) as exc_info:
            load_emission_factors(f_path)
        assert "missing required keys" in str(exc_info.value).lower()
    finally:
        os.remove(f_path)


def test_lb_per_mwh_to_metric_tons_per_kwh_conversion():
    """Verify eGRID lb/MWh values convert to metric tons CO2e/kWh."""
    assert lb_per_mwh_to_metric_tons_per_kwh(770.884) == pytest.approx(0.000349667)


def test_load_egrid_subregion_factors():
    """Verify eGRID subregion factors load as Scope 2 electricity factors."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    factors_path = os.path.join(base_dir, "data", "egrid2023_subregion_factors.json")

    egrid_factors = load_egrid_subregion_factors(factors_path)

    assert "US" in egrid_factors
    assert "CAMX" in egrid_factors
    assert egrid_factors["CAMX"].scope == 2
    assert egrid_factors["CAMX"].activity_type == "electricity"
    assert egrid_factors["CAMX"].factor_value == pytest.approx(0.000195037)
    assert "WECC California" in egrid_factors["CAMX"].source_name


def test_egrid_factor_replaces_only_electricity():
    """Verify selecting an eGRID subregion only replaces the electricity factor."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base_factors = load_emission_factors(os.path.join(base_dir, "data", "emission_factors.json"))
    egrid_factors = load_egrid_subregion_factors(
        os.path.join(base_dir, "data", "egrid2023_subregion_factors.json")
    )

    selected = with_egrid_electricity_factor(base_factors, egrid_factors, "CAMX")

    assert selected["natural_gas"].factor_value == base_factors["natural_gas"].factor_value
    assert selected["diesel_fuel"].factor_value == base_factors["diesel_fuel"].factor_value
    assert selected["electricity"].factor_value == pytest.approx(0.000195037)
    assert normalize_egrid_subregion("U.S.") == "US"


def test_factor_file_map_supports_mixed_factor_sources():
    """Verify provenance can distinguish Scope 1/2 base files from eGRID files."""
    file_map = build_factor_file_map("emission_factors.json", "egrid2023_subregion_factors.json")
    assert file_map["natural_gas"] == "emission_factors.json"
    assert file_map["electricity"] == "egrid2023_subregion_factors.json"


def test_load_egrid_missing_file():
    """Verify missing eGRID factor files produce a clear loader error."""
    with pytest.raises(EgridFactorLoadError):
        load_egrid_subregion_factors("missing_egrid.json")
