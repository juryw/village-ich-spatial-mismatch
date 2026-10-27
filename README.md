# Spatial mismatch between traditional villages and national-level ICH in China — reproduction package

中国传统村落与国家级非物质文化遗产空间错位研究：可复现程序包（论文投稿配套存档）

GitHub: https://github.com/juryw （仓库建立后此行更新为实际仓库地址；投稿时另在 Zenodo 存档获取 DOI）

## Contents

- `scripts/` — 56 numbered Python scripts in execution order. Key ones:
  - `01–07` data inspection, county-boundary download/repair, village merge & dedup
  - `09` county-level point-in-polygon aggregation (grid index + ray casting)
  - `13` registration-site effect: rule-based sensitivity (calibers A/B/C/D)
  - `14` NNI / VMR / KDE / SDE / Gini (note: authoritative NNI-Z and fixed-grid VMR live in `51`)
  - `15` coupling coordination degree (758 dual-element counties in the final version)
  - `16`, `43`, `44` bivariate LISA (Queen weights, permutation tests, BH-FDR, three-layer robustness)
  - `19`, `20`, `22`, `28`, `51–55` factor table, GDP/population/elevation zonal statistics, rectifications
  - `23` geographical detector v2 (758 dual-element counties, 7 factors, 999-permutation q tests)
  - `53` demonstration-list hit-rate test
- `results/` — county-level output tables (UTF-8 with BOM): village/ICH counts per caliber, coupling degrees, LISA classes, driver-factor table, removal lists, GDP/population/elevation/road-density zonal statistics.

## Random seeds & determinism

All stochastic steps (LISA permutation tests, detector permutation tests) are seeded with `random.seed(42)` / `numpy.random.default_rng(42)`; reported p-values are reproducible to within Monte-Carlo tolerance.

## Data sources (all openly available; see the manuscript's Table 1 for full citations)

- National ICH (five batches, 3,610 sub-items): geodoi.ac.cn, DOI 10.3974/geodb.2021.12.01.V1
- Traditional villages (batches 1–5, 6,817 after dedup): geodoi.ac.cn / escience.org.cn (three datasets)
- County boundaries: Alibaba DataV GeoAtlas (open service); geometry repaired with shapely `make_valid`
- GDP grid (2020): resdc.cn, DOI 10.12078/2017121102
- Population grid (2020): WorldPop (unconstrained)
- Elevation: Mapzen Terrain Tiles on AWS Open Data (zoom 7)
- Roads: OpenStreetMap/Geofabrik China extract (© OpenStreetMap contributors, ODbL)

## Notes

- Large rasters and boundary files are NOT included here (available from the sources above); the package covers scripts and county-level results.
- Calibers: A = full sample (3,610); B = excluding 434 nationally scoped institutions; C = strict lower bound (1,126 removed); D = broad-institution-only (archived).
- Correspondence: first author (landscape architecture, master's candidate).
