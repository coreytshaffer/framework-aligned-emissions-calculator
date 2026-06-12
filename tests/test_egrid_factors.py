import pytest
import os
import tempfile
import json
from src.emissions_calculator.models import EmissionFactor
from src.emissions_calculator.egrid_factors import (
    lb_per_mwh_to_metric_tons_per_kwh,
    normalize_egrid_subregion,
    load_egrid_subregion_factors,
    EgridFactorLoadError,
    with_egrid_electricity_factor,
)

def test_lb_per_mwh_to_metric_tons_per_kwh():
    # 1 lb = 0.00045359237 metric tons
    # 1 MWh = 1000 kWh
    assert lb_per_mwh_to_metric_tons_per_kwh(1000) == pytest.approx(0.00045359237)
    
    with pytest.raises(ValueError, match="cannot be negative"):
        lb_per_mwh_to_metric_tons_per_kwh(-1.5)

def test_normalize_egrid_subregion():
    assert normalize_egrid_subregion("  camx  ") == "CAMX"
    assert normalize_egrid_subregion("U.S.") == "US"
    assert normalize_egrid_subregion("usa") == "US"
    assert normalize_egrid_subregion("UNITED STATES") == "US"
    assert normalize_egrid_subregion("nwpp") == "NWPP"

def test_normalize_egrid_subregion_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        normalize_egrid_subregion("   ")
    with pytest.raises(ValueError, match="empty"):
        normalize_egrid_subregion("")

def test_load_egrid_subregion_factors_valid():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump([
            {
                "subregion_code": "CAMX", 
                "subregion_name": "WECC California", 
                "co2e_lb_per_mwh": 400.0
            }
        ], f)
        path = f.name
    try:
        factors = load_egrid_subregion_factors(path)
        assert "CAMX" in factors
        assert factors["CAMX"].scope == 2
        assert factors["CAMX"].activity_type == "electricity"
        assert factors["CAMX"].factor_value == pytest.approx(0.000181436948)
    finally:
        os.remove(path)

def test_load_egrid_subregion_factors_malformed_json():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        f.write("{bad json")
        path = f.name
    try:
        with pytest.raises(EgridFactorLoadError, match="Failed to parse"):
            load_egrid_subregion_factors(path)
    finally:
        os.remove(path)

def test_load_egrid_subregion_factors_missing_keys():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump([{"subregion_code": "CAMX"}], f)
        path = f.name
    try:
        with pytest.raises(EgridFactorLoadError, match="missing required keys"):
            load_egrid_subregion_factors(path)
    finally:
        os.remove(path)

def test_load_egrid_subregion_factors_duplicate_code():
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
        json.dump([
            {"subregion_code": "CAMX", "subregion_name": "A", "co2e_lb_per_mwh": 10},
            {"subregion_code": "CAMX", "subregion_name": "B", "co2e_lb_per_mwh": 20}
        ], f)
        path = f.name
    try:
        with pytest.raises(EgridFactorLoadError, match="Duplicate"):
            load_egrid_subregion_factors(path)
    finally:
        os.remove(path)

def test_with_egrid_electricity_factor_success():
    base = {
        "natural_gas": EmissionFactor(source_name="", activity_type="natural_gas", scope=1, input_unit="", factor_value=1.0, factor_unit="", gas_basis="", source_reference="", source_year=2023, notes=""),
        "electricity": EmissionFactor(source_name="Old", activity_type="electricity", scope=2, input_unit="", factor_value=2.0, factor_unit="", gas_basis="", source_reference="", source_year=2023, notes="")
    }
    egrid = {
        "CAMX": EmissionFactor(source_name="eGRID", activity_type="electricity", scope=2, input_unit="", factor_value=3.0, factor_unit="", gas_basis="", source_reference="", source_year=2023, notes="")
    }
    updated = with_egrid_electricity_factor(base, egrid, "camx")
    
    assert updated["natural_gas"].factor_value == 1.0
    assert updated["electricity"].factor_value == 3.0
    assert updated["electricity"].source_name == "eGRID"
    
    # Original base should be unmodified
    assert base["electricity"].factor_value == 2.0

def test_with_egrid_electricity_factor_unknown():
    base = {}
    egrid = {}
    with pytest.raises(KeyError, match="Unknown eGRID"):
        with_egrid_electricity_factor(base, egrid, "UNKNOWN")
