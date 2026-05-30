import json
import os
from typing import Dict
from .models import EmissionFactor

class FactorLoadError(Exception):
    """Custom exception raised when emission factors fail to load or are malformed."""
    pass

def load_emission_factors(path: str) -> Dict[str, EmissionFactor]:
    """Loads emission factors from a JSON file and returns a mapping from activity_type to EmissionFactor.

    Args:
        path: Absolute or relative path to the JSON factors file.

    Returns:
        A dictionary mapping activity_type (str) to EmissionFactor.

    Raises:
        FactorLoadError: If the file does not exist, is invalid JSON, or lacks required fields.
    """
    if not os.path.exists(path):
        raise FactorLoadError(f"Emission factors file not found at path: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise FactorLoadError(f"Failed to parse emission factors file as JSON: {str(e)}")

    if not isinstance(data, list):
        raise FactorLoadError("Emission factors file must contain a JSON array (list) of factors.")

    required_keys = {
        "source_name", "activity_type", "scope", "input_unit", 
        "factor_value", "factor_unit", "gas_basis", "source_reference", 
        "source_year", "notes"
    }

    factors: Dict[str, EmissionFactor] = {}
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise FactorLoadError(f"Factor at index {idx} is not a valid JSON object.")
        
        missing_keys = required_keys - item.keys()
        if missing_keys:
            raise FactorLoadError(
                f"Factor at index {idx} (activity_type: {item.get('activity_type', 'unknown')}) "
                f"is missing required keys: {', '.join(missing_keys)}"
            )
        
        # Validate data types
        try:
            factor = EmissionFactor(
                source_name=str(item["source_name"]),
                activity_type=str(item["activity_type"]),
                scope=int(item["scope"]),
                input_unit=str(item["input_unit"]),
                factor_value=float(item["factor_value"]),
                factor_unit=str(item["factor_unit"]),
                gas_basis=str(item["gas_basis"]),
                source_reference=str(item["source_reference"]),
                source_year=int(item["source_year"]),
                notes=str(item["notes"])
            )
            factors[factor.activity_type] = factor
        except (ValueError, TypeError) as e:
            raise FactorLoadError(
                f"Factor at index {idx} (activity_type: {item.get('activity_type', 'unknown')}) "
                f"has invalid data types: {str(e)}"
            )

    return factors
