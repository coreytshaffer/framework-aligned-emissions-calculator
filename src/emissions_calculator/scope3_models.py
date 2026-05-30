from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Scope3EmissionFactor:
    """Represents an EPA Supply Chain v1.2 spend-based emission factor with NAICS commodities mapping."""
    factor_key: str
    naics_code: str
    commodity_name: str
    factor_type: str
    factor_value: float
    factor_unit: str
    data_year: int
    currency_year: int
    publication_year: int
    model_version: str
    gwp_basis: str
    notes: str

@dataclass
class Scope3PurchaseResult:
    """Holds calculated emissions and metadata for a single supply chain purchase transaction."""
    facility_name: str
    reporting_year: int
    supplier_name: str
    purchase_category: str
    amount_spent_usd: float
    factor_key: str
    emissions_mt_co2e: float
    calculation_status: str  # "calculated" or "unmapped_factor"
    included_in_total: bool
    warning: str
    factor_value: float
    factor_unit: str
    factor_source: str
    factor_year: int
    factor_file: str
    currency_year: int
    gwp_basis: str

@dataclass
class Scope3InventorySummary:
    """Holds the fully aggregated greenhouse gas emissions inventory and mapping rates for Scope 3."""
    results: List[Scope3PurchaseResult]
    grand_total_emissions: float
    mapped_spend: float
    unmapped_spend: float
    percent_spend_mapped: float
    total_by_supplier: Dict[str, float]
    total_by_category: Dict[str, float]
    warnings: List[str]
