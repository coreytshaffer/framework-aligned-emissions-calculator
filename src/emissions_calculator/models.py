from dataclasses import dataclass
from typing import Dict, List

@dataclass
class EmissionFactor:
    """Represents a standard Greenhouse Gas Protocol conversion factor with complete metadata."""
    source_name: str
    activity_type: str
    scope: int
    input_unit: str
    factor_value: float
    factor_unit: str
    gas_basis: str
    source_reference: str
    source_year: int
    notes: str

@dataclass
class ActivityInput:
    """Represents the raw facility activity data for a given reporting year."""
    facility_name: str
    reporting_year: int
    activities: Dict[str, float]  # Maps activity_type (e.g. 'natural_gas') to activity value

@dataclass
class EmissionResult:
    """Holds the calculated emissions and metadata for a single facility activity."""
    activity_type: str
    scope: int
    activity_value: float
    input_unit: str
    emissions_mt_co2e: float
    factor_value: float
    factor_unit: str
    source_name: str
    source_reference: str
    factor_year: int
    factor_file: str

@dataclass
class InventorySummary:
    """Holds the fully aggregated greenhouse gas emissions inventory for a facility."""
    facility_name: str
    reporting_year: int
    results: List[EmissionResult]
    scope_1_total: float
    scope_2_total: float
    grand_total: float
    scope_1_percentage: float
    scope_2_percentage: float
