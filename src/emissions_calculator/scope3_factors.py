import json
import os
from typing import Dict
from .scope3_models import Scope3EmissionFactor

class Scope3FactorLoadError(Exception):
    """Custom exception raised when Scope 3 factors fail to load or are malformed."""
    pass

def load_scope3_factors(path: str) -> Dict[str, Scope3EmissionFactor]:
    """Loads Scope 3 spend-based emission factors from a JSON file.

    Args:
        path: Absolute or relative path to the JSON factors file.

    Returns:
        A dictionary mapping factor_key (str) to Scope3EmissionFactor.

    Raises:
        Scope3FactorLoadError: If the file does not exist, is invalid JSON, or lacks required fields.
    """
    if not os.path.exists(path):
        raise Scope3FactorLoadError(f"Scope 3 factors file not found at path: {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise Scope3FactorLoadError(f"Failed to parse Scope 3 factors file as JSON: {str(e)}")

    if not isinstance(data, list):
        raise Scope3FactorLoadError("Scope 3 factors file must contain a JSON array (list) of factors.")

    required_keys = {
        "factor_key", "naics_code", "commodity_name", "factor_type", 
        "factor_value", "factor_unit", "data_year", "currency_year", 
        "publication_year", "model_version", "gwp_basis", "notes"
    }

    factors: Dict[str, Scope3EmissionFactor] = {}
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise Scope3FactorLoadError(f"Factor at index {idx} is not a valid JSON object.")
        
        missing_keys = required_keys - item.keys()
        if missing_keys:
            raise Scope3FactorLoadError(
                f"Factor at index {idx} (factor_key: {item.get('factor_key', 'unknown')}) "
                f"is missing required keys: {', '.join(missing_keys)}"
            )
        
        try:
            factor = Scope3EmissionFactor(
                factor_key=str(item["factor_key"]),
                naics_code=str(item["naics_code"]),
                commodity_name=str(item["commodity_name"]),
                factor_type=str(item["factor_type"]),
                factor_value=float(item["factor_value"]),
                factor_unit=str(item["factor_unit"]),
                data_year=int(item["data_year"]),
                currency_year=int(item["currency_year"]),
                publication_year=int(item["publication_year"]),
                model_version=str(item["model_version"]),
                gwp_basis=str(item["gwp_basis"]),
                notes=str(item["notes"])
            )
            factors[factor.factor_key] = factor
        except (ValueError, TypeError) as e:
            raise Scope3FactorLoadError(
                f"Factor at index {idx} (factor_key: {item.get('factor_key', 'unknown')}) "
                f"has invalid data types: {str(e)}"
            )

    return factors
