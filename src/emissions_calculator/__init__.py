"""
Framework-Aligned Emissions Calculator MVP Core Package.
Provides data models, loading utility for conversion factors, and calculation logic.
"""

from .models import (
    EmissionFactor,
    ActivityInput,
    EmissionResult,
    InventorySummary
)
from .factors import (
    load_emission_factors,
    FactorLoadError
)
from .calculator import (
    calculate_emissions,
    calculate_inventory,
    summarize_by_scope,
    UnknownActivityError
)
from .egrid_factors import (
    EgridFactorLoadError,
    build_factor_file_map,
    lb_per_mwh_to_metric_tons_per_kwh,
    load_egrid_subregion_factors,
    normalize_egrid_subregion,
    with_egrid_electricity_factor
)

# Isolated Scope 3 Submodules
from .scope3_models import (
    Scope3EmissionFactor,
    Scope3PurchaseResult,
    Scope3InventorySummary
)
from .scope3_factors import (
    load_scope3_factors,
    Scope3FactorLoadError
)
from .scope3_calculator import (
    calculate_scope3_purchase_emissions,
    calculate_scope3_inventory
)

__all__ = [
    "EmissionFactor",
    "ActivityInput",
    "EmissionResult",
    "InventorySummary",
    "load_emission_factors",
    "FactorLoadError",
    "calculate_emissions",
    "calculate_inventory",
    "summarize_by_scope",
    "UnknownActivityError",
    "EgridFactorLoadError",
    "build_factor_file_map",
    "lb_per_mwh_to_metric_tons_per_kwh",
    "load_egrid_subregion_factors",
    "normalize_egrid_subregion",
    "with_egrid_electricity_factor",
    
    # Scope 3 Exports
    "Scope3EmissionFactor",
    "Scope3PurchaseResult",
    "Scope3InventorySummary",
    "load_scope3_factors",
    "Scope3FactorLoadError",
    "calculate_scope3_purchase_emissions",
    "calculate_scope3_inventory"
]
