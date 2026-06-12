import json
import os
from typing import Dict, Mapping

from .models import EmissionFactor


LB_TO_METRIC_TON = 0.00045359237
KWH_PER_MWH = 1000.0
EGRID_SOURCE_NAME = "EPA eGRID2023 Revision 2"
EGRID_SOURCE_REFERENCE = (
    "EPA eGRID 2023 Summary Tables, Revision 2; eGRID Subregion Total "
    "Output Emission Rates (lb/MWh)"
)


class EgridFactorLoadError(Exception):
    """Raised when eGRID subregion factors fail to load or validate."""


def lb_per_mwh_to_metric_tons_per_kwh(lb_per_mwh: float) -> float:
    """Convert pounds per MWh into metric tons per kWh."""
    if lb_per_mwh < 0:
        raise ValueError(f"eGRID emission rate cannot be negative: {lb_per_mwh}")
    return lb_per_mwh * LB_TO_METRIC_TON / KWH_PER_MWH


def normalize_egrid_subregion(value: str) -> str:
    """Normalize user-facing eGRID codes into JSON lookup keys."""
    cleaned = str(value).strip().upper()
    if not cleaned:
        raise ValueError("eGRID subregion cannot be empty.")
    return "US" if cleaned in {"U.S.", "USA", "UNITED STATES"} else cleaned


def load_egrid_subregion_factors(path: str) -> Dict[str, EmissionFactor]:
    """Load eGRID subregion electricity factors as Scope 2 EmissionFactor objects."""
    if not os.path.exists(path):
        raise EgridFactorLoadError(f"eGRID factor file not found at path: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise EgridFactorLoadError(f"Failed to parse eGRID factor file as JSON: {str(e)}")

    if not isinstance(data, list):
        raise EgridFactorLoadError("eGRID factor file must contain a JSON array of factors.")

    required_keys = {"subregion_code", "subregion_name", "co2e_lb_per_mwh"}
    factors: Dict[str, EmissionFactor] = {}

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise EgridFactorLoadError(f"eGRID factor at index {idx} is not a JSON object.")

        missing_keys = required_keys - item.keys()
        if missing_keys:
            raise EgridFactorLoadError(
                f"eGRID factor at index {idx} is missing required keys: "
                f"{', '.join(sorted(missing_keys))}"
            )

        try:
            code = normalize_egrid_subregion(str(item["subregion_code"]))
            name = str(item["subregion_name"])
            lb_per_mwh = float(item["co2e_lb_per_mwh"])
            factor_value = lb_per_mwh_to_metric_tons_per_kwh(lb_per_mwh)
        except (ValueError, TypeError) as e:
            raise EgridFactorLoadError(
                f"eGRID factor at index {idx} has invalid data types: {str(e)}"
            )

        if code in factors:
            raise EgridFactorLoadError(f"Duplicate eGRID subregion code found: {code}")

        factors[code] = EmissionFactor(
            source_name=f"{EGRID_SOURCE_NAME} - {code} {name}",
            activity_type="electricity",
            scope=2,
            input_unit="kWh",
            factor_value=factor_value,
            factor_unit="metric tons CO2e / kWh",
            gas_basis="CO2e",
            source_reference=EGRID_SOURCE_REFERENCE,
            source_year=2023,
            notes=(
                f"Location-based Scope 2 electricity factor for eGRID subregion {code} "
                f"({name}). EPA reported {lb_per_mwh} lb CO2e/MWh total output "
                "emission rate for eGRID2023 Revision 2, converted to metric tons "
                "CO2e/kWh."
            ),
        )

    return factors


def with_egrid_electricity_factor(
    base_factors: Mapping[str, EmissionFactor],
    egrid_factors: Mapping[str, EmissionFactor],
    subregion_code: str,
) -> Dict[str, EmissionFactor]:
    """Return a copy of base factors with electricity replaced by an eGRID factor."""
    code = normalize_egrid_subregion(subregion_code)
    if code not in egrid_factors:
        raise KeyError(f"Unknown eGRID subregion code: {subregion_code}")

    scoped_factors = dict(base_factors)
    scoped_factors["electricity"] = egrid_factors[code]
    return scoped_factors


def build_factor_file_map(base_factor_file: str, egrid_factor_file: str) -> Dict[str, str]:
    """Map activity types to their source factor files for provenance exports."""
    return {
        "natural_gas": base_factor_file,
        "diesel_fuel": base_factor_file,
        "electricity": egrid_factor_file,
    }
