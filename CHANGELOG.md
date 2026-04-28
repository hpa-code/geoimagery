# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-28

### Added

- Initial public release.
- `geoimagery.initialize()` for one-time Earth Engine setup.
- `geoimagery.list_available_dates()` builds a per-geometry inventory of
  NAIP months over a date range.
- `geoimagery.download()` exports NAIP imagery clipped to each input
  polygon, with automatic resolution fallback when GEE's payload cap is
  hit and skip-existing behaviour for resumable runs.
- `geoimagery.load_geometries()` accepts `GeoDataFrame`, GeoJSON path,
  Shapefile, GeoPackage, KML, single shapely geometry, list of shapely
  geometries, or GeoJSON-shaped dict.
- Pure-Python helpers: `parse_available_dates()`,
  `build_month_window()`, `sanitize_filename_component()`.
- `py.typed` marker (PEP 561).
- MIT license, Contributor Covenant 2.1 code of conduct, security
  policy, citation file.
- GitHub Actions CI on Python 3.10-3.13 across Ubuntu/macOS/Windows.
- Trusted-publishing release workflow.

[Unreleased]: https://github.com/hpa-code/geoimagery/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/hpa-code/geoimagery/releases/tag/v0.1.0
