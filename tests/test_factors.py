import os
import tempfile
import pytest
from src.emissions_calculator.factors import load_emission_factors, FactorLoadError

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
