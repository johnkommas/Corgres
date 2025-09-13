# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

### Added
- Retail Pricing: Added new origin Πολωνία (PL) with Groupage enabled and manual entry of final freight cost specifically for Poland.
- Retail Pricing: Display an alternative retail price per m² next to the main retail price on /pricing, computed as A: +35% then B: +10% (shown as “Λιανική (35/10)/ m²”).
- Retail Pricing: New checkbox on /pricing to include/exclude pallet cost (10€/EU, 30€/Industrial) without changing the number of pallets used for weight and island surcharges.

### Changed
- Retail Pricing: Alternative retail price is now calculated based on Κόστος ανά m² (cost_per_m2) rather than purchase price, matching expected business logic (e.g., 36.80 × 1.35 × 1.10 = 54.65 €).
- Retail Pricing: On /pricing, default pallets to 1 and disallow 0 in “Αριθμός Παλετών”. Use the checkbox to include/exclude pallet cost without altering pallet count.
- Retail Pricing frontend and backend updated to support Poland-specific freight override and Groupage availability for ES and PL.
- SLABs: Switched purchase price input from per piece to per square meter in UI and API. New field buy_price_eur_m2 is preferred; legacy buy_per_unit still accepted for backward compatibility (converted using m² per unit).

## [0.1.0] - 2025-09-11

This release groups the most recent user-facing changes from the last commits on the default branch. The inferred version bump is minor (new features and UI enhancements, no breaking changes detected).

### Added
- Pallet type icons in SLABs template for clearer visual cues ([d068989](https://github.com/johnkommas/Corgres/commit/d068989)).
- Dynamic thickness and dimension selection controls in SLABs template ([29f9bf8](https://github.com/johnkommas/Corgres/commit/29f9bf8)).
- Detailed business rules for auto-pallet allocation covering mixed and large shipments ([6100a46](https://github.com/johnkommas/Corgres/commit/6100a46)).

### Changed
- Responsive design improvements and visual updates to SLABs template ([d068989](https://github.com/johnkommas/Corgres/commit/d068989)).
- Enhanced SLABs template with compact chip groups for a more compact UI ([29f9bf8](https://github.com/johnkommas/Corgres/commit/29f9bf8)).
- Improved auto-pallet allocation logic to align with new business rules ([6100a46](https://github.com/johnkommas/Corgres/commit/6100a46)).
- Refactored SLABs Pricing Calculator UI and strengthened validation logic ([6bd3541](https://github.com/johnkommas/Corgres/commit/6bd3541)).
- Updated SLABs Pricing Calculator static template ([48d7809](https://github.com/johnkommas/Corgres/commit/48d7809)).

[Unreleased]: https://github.com/johnkommas/Corgres/compare/0.1.0...HEAD
[0.1.0]: https://github.com/johnkommas/Corgres/releases/tag/0.1.0

- Retail Pricing: Updated alternative retail label on /pricing to two-line format “Λιανική Τιμή / m²” and “A35% B10%” for clarity.
