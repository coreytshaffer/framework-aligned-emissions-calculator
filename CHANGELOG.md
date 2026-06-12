# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- EPA eGRID2023 Revision 2 subregion factor library for location-based Scope 2 electricity calculations.
- eGRID subregion selector in the single-facility Streamlit workflow.
- Optional `egrid_subregion` column support for bulk Scope 1/2 facility uploads.
- Fallback warnings when uploaded bulk rows use unknown eGRID subregion codes.
- Unit tests covering eGRID factor loading, lb/MWh to MT/kWh conversion, selected-factor replacement, and mixed factor-file provenance.

### Changed
- Scope 2 CSV exports now preserve mixed provenance by recording eGRID electricity factors separately from the base Scope 1 factor file.
- README and portfolio summary now describe eGRID subregion selection as implemented, while keeping ZIP/address lookup and market-based Scope 2 accounting on the roadmap.
- Replaced deprecated Streamlit `use_container_width` calls with `width="stretch"` for current Streamlit compatibility.

## [1.0.0] - 2026-05-30

### Added
- Standard Git configuration with a new `.gitignore` file.
- MIT open-source software license.
- Rebuilt virtual environment (.venv) using standard Anaconda Python 3.13 configuration, moving away from sandbox-restricted WindowsApps stubs.
- Comprehensive technical roadmap detailing improvements for Scope 2 dual-reporting and zip-code-based grid lookup.
- Factor provenance columns in detailed CSV exports, preserving source names, reference years, database files, and conversion parameters.
- Upgraded bulk batch processor to output dual download files: a facility-level summaries CSV and a transaction-level detailed master ledger CSV.
- Added custom pytest suite evaluating factor details propagation.
- Completely decoupled Scope 3 submodules (`scope3_models.py`, `scope3_factors.py`, `scope3_calculator.py`) isolating spend-based value-chain calculations.
- EPA Supply Chain Factors v1.2 JSON database mapping NAICS categories, 2019 data baselines, 2021 USD baselines, and SEF+MEF coefficients.
- A new 'Scope 3 Supply Chain' interactive tab inside the Streamlit dashboard.
- Traceable detailed Scope 3 calculations ledger download including 15 column metadata parameters.
- Detailed mapping rate metrics displaying mapped spend ($), unmapped spend ($), and percent spend mapped (%) side-by-side with grand total emissions.
- Prominent mapping warning lists alerting users to unmapped categories.
- Dedicated unit test suite `test_scope3.py` verifying model loaders, multiplication math, status mappings, and supplier groupings.
- Scope 3 purchase-ledger example CSV for quick manual testing.
- GitHub Actions workflow that runs the pytest suite on pushes to `main` and pull requests.
- Git attributes file to keep text file line endings predictable across Windows and Linux CI.
- Reviewer-facing portfolio summary in `docs/portfolio-summary.md`.
- README badges, preview section, and reviewer start guide.

### Changed
- Softened documentation claims in `README.md` to clarify prototype status and avoid unsupported certainty.
- Added clear documentation clarifying that Scope 2 electricity factors represent generic national grid averages, highlighting regional eGRID subregions as future roadmap enhancements.
- Refined the operational standards disclosures to strictly communicate the learning/portfolio purpose of the MVP.
- Appended spend-based Scope 3 Category 1 screening methodology boundaries and structural limitations to README.md.
- Tightened README language around framework alignment, factor-library completeness, and formal reporting limitations.
- Added a faster reviewer-oriented README path with quick-start commands and example-data notes.
- Clarified Scope 3 upload messaging so unmapped categories are not implied to be successfully mapped.

### Release Checklist
- [ ] Confirm GitHub Actions test workflow passes on `main`.
- [ ] Confirm README preview image renders on GitHub.
- [ ] Publish GitHub release `v0.1.0-carbonaware-mvp`.
- [ ] Use release title `CarbonAware MVP v0.1.0`.
- [ ] Include release notes: Initial public MVP release featuring Scope 1, Scope 2, and educational spend-based Scope 3 screening workflows.
