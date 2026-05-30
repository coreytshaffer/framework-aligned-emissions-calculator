from typing import List, Dict
from .scope3_models import Scope3EmissionFactor, Scope3PurchaseResult, Scope3InventorySummary

def calculate_scope3_purchase_emissions(amount_spent_usd: float, factor: Scope3EmissionFactor) -> float:
    """Calculates emissions by multiplying purchase spend by the supply chain emission factor.

    Formula:
        (Amount Spent (USD) * Emission Factor (kg CO2e/USD)) / 1000.0 = Emissions (MT CO2e)

    Args:
        amount_spent_usd: The numerical spend value in USD.
        factor: The Scope3EmissionFactor instance to use.

    Returns:
        The calculated greenhouse gas emissions in metric tons CO2e.

    Raises:
        ValueError: If amount_spent_usd is negative.
    """
    if amount_spent_usd < 0:
        raise ValueError(
            f"Spend amount cannot be negative. Provided: {amount_spent_usd} "
            f"for category: '{factor.commodity_name}'"
        )
    return float((amount_spent_usd * factor.factor_value) / 1000.0)

def calculate_scope3_inventory(
    purchase_rows: List[Dict], 
    factors: Dict[str, Scope3EmissionFactor], 
    factor_file: str = "scope3_supply_chain_factors.json"
) -> Scope3InventorySummary:
    """Processes a ledger of purchase records and compiles a Scope 3 inventory.

    Handles unmapped factor keys gracefully by registering a status flag, calculating 0.0 emissions,
    and recording warning events to maintain an honest spend-mapping overview.

    Args:
        purchase_rows: List of dicts representing transactions (facility_name, reporting_year,
                       supplier_name, purchase_category, amount_spent_usd, factor_key).
        factors: Dictionary mapping factor_key (str) to Scope3EmissionFactor.
        factor_file: The name of the factor database used.

    Returns:
        A compiled Scope3InventorySummary instance.
    """
    results: List[Scope3PurchaseResult] = []
    grand_total_emissions = 0.0
    mapped_spend = 0.0
    unmapped_spend = 0.0
    total_by_supplier: Dict[str, float] = {}
    total_by_category: Dict[str, float] = {}
    warnings: List[str] = []

    for idx, row in enumerate(purchase_rows):
        facility = str(row.get("facility_name", "Unknown Facility"))
        year = int(row.get("reporting_year", 2026))
        supplier = str(row.get("supplier_name", "Unknown Supplier"))
        category = str(row.get("purchase_category", "Unknown Category"))
        
        # Safely extract and parse spend
        raw_spend = row.get("amount_spent_usd", 0.0)
        spend = 0.0 if raw_spend is None else float(raw_spend)
        if spend < 0:
            raise ValueError(f"Purchase record at index {idx} has a negative spend: {spend}")

        factor_key = str(row.get("factor_key", "")).strip()

        if not factor_key or factor_key not in factors:
            # Unmapped factor handling
            calc_status = "unmapped_factor"
            included = False
            emissions = 0.0
            warning_msg = f"No factor found for factor_key: '{factor_key}' (Supplier: '{supplier}', Category: '{category}')"
            warnings.append(warning_msg)
            unmapped_spend += spend

            result = Scope3PurchaseResult(
                facility_name=facility,
                reporting_year=year,
                supplier_name=supplier,
                purchase_category=category,
                amount_spent_usd=spend,
                factor_key=factor_key,
                emissions_mt_co2e=0.0,
                calculation_status=calc_status,
                included_in_total=included,
                warning=warning_msg,
                factor_value=0.0,
                factor_unit="kg CO2e / USD2021",
                factor_source="Unmapped",
                factor_year=0,
                factor_file=factor_file,
                currency_year=2021,
                gwp_basis="IPCC AR4 100-year GWP"
            )
        else:
            # Mapped factor calculation
            factor = factors[factor_key]
            calc_status = "calculated"
            included = True
            emissions = calculate_scope3_purchase_emissions(spend, factor)
            warning_msg = ""
            mapped_spend += spend
            grand_total_emissions += emissions

            # Aggregate breakdown maps
            total_by_supplier[supplier] = total_by_supplier.get(supplier, 0.0) + emissions
            total_by_category[category] = total_by_category.get(category, 0.0) + emissions

            result = Scope3PurchaseResult(
                facility_name=facility,
                reporting_year=year,
                supplier_name=supplier,
                purchase_category=category,
                amount_spent_usd=spend,
                factor_key=factor_key,
                emissions_mt_co2e=emissions,
                calculation_status=calc_status,
                included_in_total=included,
                warning=warning_msg,
                factor_value=factor.factor_value,
                factor_unit=factor.factor_unit,
                factor_source=factor.model_version,
                factor_year=factor.publication_year,
                factor_file=factor_file,
                currency_year=factor.currency_year,
                gwp_basis=factor.gwp_basis
            )
        
        results.append(result)

    # Compute final percentage rates
    total_spend = mapped_spend + unmapped_spend
    percent_spend_mapped = (mapped_spend / total_spend) * 100.0 if total_spend > 0 else 0.0

    return Scope3InventorySummary(
        results=results,
        grand_total_emissions=round(grand_total_emissions, 4),
        mapped_spend=round(mapped_spend, 2),
        unmapped_spend=round(unmapped_spend, 2),
        percent_spend_mapped=round(percent_spend_mapped, 2),
        total_by_supplier={k: round(v, 4) for k, v in total_by_supplier.items()},
        total_by_category={k: round(v, 4) for k, v in total_by_category.items()},
        warnings=warnings
    )
