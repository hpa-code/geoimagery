"""Loading and normalising user-supplied geometry inputs.

The public functions in this package accept a forgiving union of inputs
so callers don't have to convert their data first:

* a :class:`shapely.geometry.base.BaseGeometry`
* an iterable of shapely geometries
* a :class:`geopandas.GeoDataFrame`
* a string or :class:`pathlib.Path` pointing to any GDAL/OGR-readable
  vector file (GeoJSON, Shapefile, GeoPackage, KML, ...)
* a GeoJSON-shaped ``dict`` (a single Feature, FeatureCollection, or
  bare geometry)

:func:`load_geometries` always returns a :class:`geopandas.GeoDataFrame`
in EPSG:4326, with at least the columns ``id`` and ``name`` populated
(filled from the input if available, otherwise auto-generated).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:  # pragma: no cover - type-checking only
    import geopandas as gpd
    from shapely.geometry.base import BaseGeometry

GeometryInput = Union[
    "BaseGeometry",
    Iterable["BaseGeometry"],
    "gpd.GeoDataFrame",
    str,
    Path,
    dict,
]
"""Anything :func:`load_geometries` accepts."""

# Standard ID/name column candidates we'll look for in a user-supplied
# dataframe, in order of preference. Lower-case comparison.
_ID_CANDIDATES = ("id", "uniqueid", "unique_id", "fid", "objectid")
_NAME_CANDIDATES = ("name", "title", "label")

CRS_WGS84 = "EPSG:4326"


def load_geometries(
    source: GeometryInput,
    *,
    id_column: str | None = None,
    name_column: str | None = None,
) -> gpd.GeoDataFrame:
    """Coerce *source* into a WGS84 ``GeoDataFrame`` with ``id`` and ``name``.

    Parameters
    ----------
    source
        See :data:`GeometryInput`. The most common cases are a path to a
        GeoJSON file or a shapely geometry.
    id_column, name_column
        Optional explicit column names if your input dataframe already
        has identifiers. If omitted, the loader looks for common names
        (``id``, ``uniqueid``, ``name``, ...) and falls back to
        auto-generated values like ``feature_0``.

    Returns
    -------
    GeoDataFrame
        Reprojected to ``EPSG:4326``, with at minimum the columns
        ``id`` (str), ``name`` (str), and ``geometry``.

    Raises
    ------
    ImportError
        If geopandas / shapely aren't installed.
    ValueError
        If *source* is empty or not a recognised type.
    """
    try:
        import geopandas as gpd
        from shapely.geometry import shape
        from shapely.geometry.base import BaseGeometry
    except ImportError as exc:  # pragma: no cover - exercised in install errors
        raise ImportError(
            "geoimagery.load_geometries requires geopandas and shapely. "
            "Install them with: pip install 'geoimagery[geo]'"
        ) from exc

    # 1. Already a GeoDataFrame: just normalise CRS and columns.
    if isinstance(source, gpd.GeoDataFrame):
        gdf = source.copy()

    # 2. Path-like: read with GeoPandas (delegates to pyogrio/fiona).
    elif isinstance(source, (str, Path)):
        gdf = gpd.read_file(source)

    # 3. Single shapely geometry.
    elif isinstance(source, BaseGeometry):
        gdf = gpd.GeoDataFrame(geometry=[source], crs=CRS_WGS84)

    # 4. GeoJSON-shaped dict.
    elif isinstance(source, dict):
        gdf = _gdf_from_geojson_dict(source, gpd, shape)

    # 5. Iterable of shapely geometries.
    else:
        try:
            geoms = list(source)
        except TypeError as exc:
            raise ValueError(
                f"Unsupported geometry source of type {type(source).__name__}"
            ) from exc
        if not all(isinstance(g, BaseGeometry) for g in geoms):
            raise ValueError("Iterable input must contain shapely geometries only.")
        gdf = gpd.GeoDataFrame(geometry=geoms, crs=CRS_WGS84)

    if gdf.empty:
        raise ValueError("Geometry source is empty.")

    # Reproject to WGS84 if needed (GEE expects lon/lat).
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_WGS84)
    elif str(gdf.crs).upper() != CRS_WGS84:
        gdf = gdf.to_crs(CRS_WGS84)

    # Resolve id / name columns.
    id_col = _resolve_column(gdf, id_column, _ID_CANDIDATES)
    name_col = _resolve_column(gdf, name_column, _NAME_CANDIDATES)

    if id_col is not None:
        gdf["id"] = gdf[id_col].astype(str)
    else:
        gdf["id"] = [f"feature_{i}" for i in range(len(gdf))]

    if name_col is not None:
        gdf["name"] = gdf[name_col].astype(str).fillna("")
    else:
        gdf["name"] = gdf["id"]

    # Reorder columns so id/name/geometry come first; keep any extras.
    other_cols = [c for c in gdf.columns if c not in ("id", "name", "geometry")]
    return gdf[["id", "name", *other_cols, "geometry"]]


def _gdf_from_geojson_dict(
    obj: dict,
    gpd: Any,
    shape_fn: Any,
) -> gpd.GeoDataFrame:
    """Build a GeoDataFrame from a GeoJSON-shaped dict."""
    obj_type = obj.get("type")
    if obj_type == "FeatureCollection":
        features = obj.get("features", [])
        rows = []
        for feat in features:
            props = dict(feat.get("properties") or {})
            props["geometry"] = shape_fn(feat["geometry"])
            rows.append(props)
        return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS_WGS84)
    if obj_type == "Feature":
        props = dict(obj.get("properties") or {})
        props["geometry"] = shape_fn(obj["geometry"])
        return gpd.GeoDataFrame([props], geometry="geometry", crs=CRS_WGS84)
    if obj_type in {
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
        "GeometryCollection",
    }:
        return gpd.GeoDataFrame(geometry=[shape_fn(obj)], crs=CRS_WGS84)
    raise ValueError(f"Unrecognised GeoJSON type: {obj_type!r}")


def _resolve_column(
    gdf: gpd.GeoDataFrame,
    explicit: str | None,
    candidates: tuple[str, ...],
) -> str | None:
    """Pick a column from *gdf* matching *explicit* or any of *candidates*.

    Comparison is case-insensitive. Returns ``None`` if nothing matches.
    """
    if explicit is not None:
        if explicit in gdf.columns:
            return explicit
        raise KeyError(f"Column {explicit!r} not found in dataframe.")

    lower_map = {c.lower(): c for c in gdf.columns}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None
