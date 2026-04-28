"""Shared pytest fixtures for the geoimagery test suite.

The pure-Python helpers in :mod:`geoimagery.utils` require no third-party
deps. The geometry tests need ``shapely`` / ``geopandas``; if those are
unavailable, those tests are skipped automatically (rather than
exploding) so the suite still runs in a stripped-down environment.
"""

from __future__ import annotations

import importlib.util

import pytest

_HAS_SHAPELY = importlib.util.find_spec("shapely") is not None
_HAS_GEOPANDAS = importlib.util.find_spec("geopandas") is not None


def _skip_if_missing(*modules: str) -> None:
    """Skip the calling test if any of *modules* cannot be imported."""
    for mod in modules:
        if importlib.util.find_spec(mod) is None:
            pytest.skip(f"{mod} not installed", allow_module_level=False)


@pytest.fixture
def require_shapely() -> None:
    """Skip the test if shapely isn't installed."""
    _skip_if_missing("shapely")


@pytest.fixture
def require_geo() -> None:
    """Skip the test if shapely or geopandas aren't installed."""
    _skip_if_missing("shapely", "geopandas")


@pytest.fixture
def sample_polygon() -> object:
    """A small WGS84 polygon around downtown Rochester, NY.

    Returned as a shapely Polygon. The fixture skips the test if
    shapely is unavailable.
    """
    if not _HAS_SHAPELY:
        pytest.skip("shapely not installed")
    from shapely.geometry import box

    return box(-77.62, 43.12, -77.60, 43.14)


@pytest.fixture
def sample_geojson_dict() -> dict:
    """A FeatureCollection with two tiny polygons."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"id": "A", "name": "First"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-77.62, 43.12],
                            [-77.60, 43.12],
                            [-77.60, 43.14],
                            [-77.62, 43.14],
                            [-77.62, 43.12],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"id": "B", "name": "Second"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-77.65, 43.10],
                            [-77.63, 43.10],
                            [-77.63, 43.12],
                            [-77.65, 43.12],
                            [-77.65, 43.10],
                        ]
                    ],
                },
            },
        ],
    }
