# CarbonAware MVP Portfolio Summary

## What This Project Does

CarbonAware is a local-first greenhouse gas emissions calculator that converts facility activity data into estimated metric tons of carbon dioxide equivalent (CO2e).

It currently supports:

- Scope 1 stationary combustion examples: natural gas and diesel fuel.
- Scope 2 purchased electricity using a generic national grid-average factor.
- Scope 3 Category 1 purchased goods and services using an educational spend-based screening workflow.

## Why The Scope Boundaries Matter

Scope separation is the core accounting concept this project demonstrates.

- Scope 1 tracks direct emissions from sources owned or controlled by the facility.
- Scope 2 tracks indirect emissions from purchased energy.
- Scope 3 tracks value-chain activities outside direct operations, such as supplier purchases.

Keeping these categories separate prevents misleading totals and makes the assumptions behind each estimate easier to inspect.

## Production-Like Parts

- Calculation logic is separated from the Streamlit interface.
- Emission factors live in JSON data files instead of being hardcoded into UI controls.
- Exports include factor provenance fields such as source name, factor value, factor year, and factor file.
- Pytest tests cover core math, scope categorization, factor loading, negative inputs, missing factors, and Scope 3 mapping behavior.
- GitHub Actions runs the test suite on pushes and pull requests.

## Educational Or Simplified Parts

- The tool is not a certified greenhouse gas inventory system.
- Scope 2 uses a generic electricity factor rather than regional eGRID subregions.
- Scope 3 uses a small educational subset of EPA supply-chain factors, not the full factor library.
- Spend-based Scope 3 estimates are screening estimates, not supplier-specific primary-data accounting.
- Market-based Scope 2 accounting, renewable energy certificates, and formal inventory management workflows are out of scope for this MVP.

## What Reviewers Should Inspect First

1. `README.md` for the project purpose, disclaimer, setup, and limitations.
2. `src/emissions_calculator/calculator.py` for Scope 1 and Scope 2 calculation logic.
3. `src/emissions_calculator/scope3_calculator.py` for spend-based Scope 3 logic and unmapped-spend warnings.
4. `data/emission_factors.json` and `data/scope3_supply_chain_factors.json` for factor metadata.
5. `tests/` for automated verification.
6. `examples/` for CSV input formats.

## Suggested Release Title

CarbonAware MVP v0.1.0

## Suggested Release Notes

Initial public MVP release featuring Scope 1, Scope 2, and educational spend-based Scope 3 screening workflows with provenance-friendly factor metadata, CSV exports, pytest coverage, and GitHub Actions CI.
