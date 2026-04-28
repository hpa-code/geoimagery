"""Tests for geoimagery.geometry.load_geometries.

These tests need shapely + geopandas; they're skipped if those aren't
installed (e.g. on a stripped-down lint-only CI matrix entry).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geoimagery import load_geometries


def test_loads_from_single_shapely_geometry(require_shapely, sample_polygon) -> None:
    pytest.importorskip("geopandas")
    gdf = load_geometries(sample_polygon)

    assert len(gdf) == 1
    assert "id" in gdf.columns
    assert "name" in gdf.columns
    assert "geometry" in gdf.columns
    assert str(gdf.crs).upper() == "EPSG:4326"


def test_loads_from_list_of_geometries(require_shapely, sample_polygon) -> None:
    pytest.importorskip("geopandas")
    gdf = load_geometries([sample_polygon, sample_polygon])

    assert len(gdf) == 2
    # Auto-generated ids are unique.
    assert gdf["id"].nunique() == 2


def test_loads_from_geojson_dict(require_geo, sample_geojson_dict) -> None:
    gdf = load_geometries(sample_geojson_dict)

    assert len(gdf) == 2
    # Properties round-trip from the dict to dataframe columns.
    assert set(gdf["id"].astype(str)) == {"A", "B"}
    assert set(gdf["name"].astype(str)) == {"First", "Second"}


def test_loads_from_geojson_file(
    require_geo,
    sample_geojson_dict: dict,
    tmp_path: Path,
) -> None:
    path = tmp_path / "areas.geojson"
    path.write_text(json.dumps(sample_geojson_dict))

    gdf = load_geometries(str(path))
    assert len(gdf) == 2


def test_explicit_id_and_name_columns(require_geo) -> None:
    geopandas = pytest.importorskip("geopandas")
    from shapely.geometry import Point

    src = geopandas.GeoDataFrame(
        {"FARM_ID": ["F1", "F2"], "OWNER": ["Alice", "Bob"]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    gdf = load_geometries(src, id_column="FARM_ID", name_column="OWNER")

    assert list(gdf["id"]) == ["F1", "F2"]
    assert list(gdf["name"]) == ["Alice", "Bob"]


def test_unknown_explicit_id_column_raises(require_geo) -> None:
    geopandas = pytest.importorskip("geopandas")
    from shapely.geometry import Point

    src = geopandas.GeoDataFrame(
        {"some_col": [1]},
        geometry=[Point(0, 0)],
        crs="EPSG:4326",
    )
    with pytest.raises(KeyError):
        load_geometries(src, id_column="MISSING")


def test_reprojects_to_wgs84(require_geo) -> None:
    geopandas = pytest.importorskip("geopandas")
    from shapely.geometry import Point

    # EPSG:3857 (Web Mercator) input -- should be reprojected to WGS84.
    src = geopandas.GeoDataFrame(
        {"id": ["x"]},
        geometry=[Point(-8_641_000, 5_350_000)],
        crs="EPSG:3857",
    )
    gdf = load_geometries(src)
    assert str(gdf.crs).upper() == "EPSG:4326"


def test_empty_input_raises(require_geo) -> None:
    geopandas = pytest.importorskip("geopandas")

    src = geopandas.GeoDataFrame(geometry=[], crs="EPSG:4326")
    with pytest.raises(ValueError, match="empty"):
        load_geometries(src)


def test_unsupported_input_type_raises(require_geo) -> None:
    with pytest.raises(ValueError):
        load_geometries(12345)  # type: ignore[arg-type]
