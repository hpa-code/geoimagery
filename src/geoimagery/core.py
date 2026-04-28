"""High-level NAIP download + inventory functions.

Public API
----------
* :func:`initialize` -- one-time Earth Engine init.
* :func:`list_available_dates` -- find which months of NAIP imagery exist
  for each input geometry over a date range.
* :func:`download` -- download NAIP imagery clipped to each geometry, for
  a given list of months.
* :class:`DownloadResult` -- typed status row returned by :func:`download`.

The implementation here is a generalised refactor of the original
"university satellite imagery" script -- nothing in this module is
specific to universities or to any single dataset of polygons.
"""

from __future__ import annotations

import contextlib
import logging
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from geoimagery.geometry import GeometryInput, load_geometries
from geoimagery.utils import (
    build_month_window,
    parse_available_dates,
    sanitize_filename_component,
)

if TYPE_CHECKING:  # pragma: no cover
    import geopandas as gpd
    import pandas as pd

log = logging.getLogger(__name__)

#: NAIP DOQQ image collection on Earth Engine.
NAIP_COLLECTION = "USDA/NAIP/DOQQ"

#: Successive scales (m/px) tried when an export hits GEE's payload cap.
DEFAULT_SCALES_TO_TRY: tuple[float, ...] = (0.6, 1.0, 2.0, 4.0)

# Minimum file size we accept before declaring a temp download a success;
# GEE occasionally writes a 0-byte placeholder when the request is malformed.
_MIN_TEMP_BYTES = 10_000


@dataclass(frozen=True)
class DownloadResult:
    """One row of the download log returned by :func:`download`.

    Attributes
    ----------
    id, name
        Mirror the input geometry's identifier columns.
    month
        The requested month label, e.g. ``"June, 2023"``.
    filename
        The basename of the produced GeoTIFF (or the planned name, even
        if the download didn't succeed).
    status
        One of ``"Downloaded"``, ``"Already Downloaded"``,
        ``"No Data for Month"``, ``"Download Failed"``, or
        ``"Error: <details>"``.
    extra
        Pass-through of any additional input-row columns the caller
        wanted preserved (e.g. ``state``, ``country``).
    """

    id: str
    name: str
    month: str
    filename: str
    status: str
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return a flat dict suitable for ``pandas.DataFrame.from_records``."""
        return {
            "id": self.id,
            "name": self.name,
            "month": self.month,
            "filename": self.filename,
            "status": self.status,
            **self.extra,
        }


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def initialize(
    project: str | None = None,
    *,
    opt_url: str | None = None,
) -> None:
    """Initialise the Earth Engine Python client.

    Each user of this library must have their own Google Earth Engine
    account and Cloud project. See
    https://earthengine.google.com/signup/ to register, then run
    ``earthengine authenticate`` once on the machine to store
    credentials.

    Parameters
    ----------
    project
        Your Google Cloud project ID, e.g. ``"my-gee-project"``.
        Required by GEE for almost all calls.
    opt_url
        Optional override for the Earth Engine endpoint
        (passed through to ``ee.Initialize``).
    """
    ee = _import_ee()
    kwargs: dict[str, Any] = {}
    if project is not None:
        kwargs["project"] = project
    if opt_url is not None:
        kwargs["opt_url"] = opt_url
    ee.Initialize(**kwargs)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


def list_available_dates(
    source: GeometryInput,
    *,
    start_date: str = "2010-01-01",
    end_date: str | None = None,
    max_workers: int = 10,
    id_column: str | None = None,
    name_column: str | None = None,
) -> pd.DataFrame:
    """Find which months of NAIP imagery exist for each input geometry.

    Parameters
    ----------
    source
        Anything accepted by :func:`geoimagery.load_geometries`.
    start_date, end_date
        ISO ``YYYY-MM-DD`` bounds (inclusive of start, exclusive of end).
        ``end_date`` defaults to today.
    max_workers
        Thread pool size for parallel GEE inventory queries.
    id_column, name_column
        Forwarded to :func:`load_geometries` if your input has
        non-standard column names.

    Returns
    -------
    DataFrame
        One row per input geometry, with columns ``id``, ``name``, and
        ``available_dates`` (a comma-separated string of month labels
        like ``"June 2023, August 2023"`` -- compatible with
        :func:`geoimagery.parse_available_dates`).
    """
    pd = _import_pandas()

    if end_date is None:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

    gdf = load_geometries(source, id_column=id_column, name_column=name_column)
    rows = list(gdf.itertuples(index=False))

    def _query(row: Any) -> dict[str, Any]:
        return _query_dates_for_row(row, start_date=start_date, end_date=end_date)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(_query, rows))

    return pd.DataFrame.from_records(results)


def _query_dates_for_row(
    row: Any,
    *,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    ee = _import_ee()
    try:
        ee_geom = ee.Geometry(row.geometry.__geo_interface__)
        coll = (
            ee.ImageCollection(NAIP_COLLECTION)
            .filterBounds(ee_geom)
            .filterDate(start_date, end_date)
        )
        timestamps = coll.aggregate_array("system:time_start").getInfo()
        if not timestamps:
            return {"id": row.id, "name": row.name, "available_dates": "N/A"}

        labels = sorted(
            {datetime.fromtimestamp(ts / 1000.0).strftime("%B %Y") for ts in timestamps},
            key=lambda v: datetime.strptime(v, "%B %Y"),
        )
        return {
            "id": row.id,
            "name": row.name,
            "available_dates": ", ".join(labels),
        }
    except Exception as exc:
        return {
            "id": row.id,
            "name": row.name,
            "available_dates": f"Error: {exc}",
        }


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download(
    source: GeometryInput,
    *,
    dates: Iterable[str] | pd.DataFrame | None = None,
    output_dir: str | Path,
    temp_dir: str | Path | None = None,
    max_workers: int = 5,
    scales_to_try: Iterable[float] = DEFAULT_SCALES_TO_TRY,
    id_column: str | None = None,
    name_column: str | None = None,
    skip_existing: bool = True,
) -> pd.DataFrame:
    """Download NAIP imagery clipped to each input geometry.

    Parameters
    ----------
    source
        Anything accepted by :func:`geoimagery.load_geometries`.
    dates
        Either:

        * an iterable of month labels (``"June 2023"``) applied to *every*
          geometry, **or**
        * a DataFrame in the format produced by
          :func:`list_available_dates` (columns ``id``, ``available_dates``)
          to download per-geometry months, **or**
        * ``None`` to first call :func:`list_available_dates` and download
          every available month.
    output_dir
        Where final clipped GeoTIFFs are written. Created if missing.
    temp_dir
        Where un-clipped GEE downloads are staged. Defaults to
        ``output_dir / "_temp"``.
    max_workers
        Thread pool size for parallel downloads. Earth Engine has its own
        concurrent-request quota; values above ~10 may be throttled.
    scales_to_try
        Successive resolutions (m/px) attempted if a download exceeds
        GEE's per-request payload limit. The first that fits wins.
    id_column, name_column
        Forwarded to :func:`load_geometries`.
    skip_existing
        If ``True`` (default), skips months whose output file already
        exists -- making this function safe to re-run.

    Returns
    -------
    DataFrame
        One row per (geometry, month) attempted, mirroring
        :class:`DownloadResult`.
    """
    pd = _import_pandas()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "_temp" if temp_dir is None else Path(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    gdf = load_geometries(source, id_column=id_column, name_column=name_column)
    tasks = _build_tasks(gdf, dates)
    if not tasks:
        log.warning("No download tasks were created -- check your inputs.")
        return pd.DataFrame()

    log.info(
        "Scheduled %d downloads across %d geometries.",
        len(tasks),
        gdf.shape[0],
    )

    def _run(task: dict[str, Any]) -> DownloadResult:
        return _download_one(
            task,
            output_dir=output_dir,
            temp_dir=temp_dir,
            scales_to_try=tuple(scales_to_try),
            skip_existing=skip_existing,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        results = list(pool.map(_run, tasks))

    return pd.DataFrame.from_records([r.as_dict() for r in results])


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_tasks(
    gdf: gpd.GeoDataFrame,
    dates: Iterable[str] | pd.DataFrame | None,
) -> list[dict[str, Any]]:
    """Cross-join geometries with the months requested for each."""
    pd = _import_pandas()

    if dates is None:
        # Inventory-then-download convenience path.
        inventory = list_available_dates(gdf)
        return _build_tasks(gdf, inventory)

    if isinstance(dates, pd.DataFrame):
        if "id" not in dates.columns or "available_dates" not in dates.columns:
            raise ValueError("dates DataFrame must have 'id' and 'available_dates' columns.")
        dates_by_id: dict[str, list[str]] = {
            str(row.id): parse_available_dates(row.available_dates)
            for row in dates.itertuples(index=False)
        }
        per_row = lambda row_id: dates_by_id.get(str(row_id), [])  # noqa: E731
    else:
        explicit = list(dates)
        per_row = lambda _row_id: explicit  # noqa: E731

    tasks: list[dict[str, Any]] = []
    for row in gdf.itertuples(index=False):
        for month_label in per_row(row.id):
            tasks.append(
                {
                    "id": str(row.id),
                    "name": str(row.name),
                    "geometry": row.geometry,
                    "month_label": month_label,
                    "extra": _extra_columns(row),
                }
            )
    return tasks


def _extra_columns(row: Any) -> dict[str, Any]:
    """Capture user-supplied columns to round-trip into the result log."""
    fields = getattr(row, "_fields", ())
    return {f: getattr(row, f) for f in fields if f not in {"id", "name", "geometry"}}


def _download_one(
    task: dict[str, Any],
    *,
    output_dir: Path,
    temp_dir: Path,
    scales_to_try: tuple[float, ...],
    skip_existing: bool,
) -> DownloadResult:
    ee = _import_ee()
    geemap = _import_geemap()
    rioxarray = _import_rioxarray()

    geom = task["geometry"]
    month_label = task["month_label"]
    start, end, display = build_month_window(month_label)

    safe_name = sanitize_filename_component(task["name"]) or "feature"
    safe_display = re.sub(r"[, ]+", "_", display)
    base = f"{task['id']}_{safe_name}_{safe_display}"
    final_path = output_dir / f"{base}.tif"
    temp_path = temp_dir / f"{base}__temp.tif"

    if skip_existing and final_path.exists():
        return DownloadResult(
            id=task["id"],
            name=task["name"],
            month=display,
            filename=final_path.name,
            status="Already Downloaded",
            extra=task["extra"],
        )

    try:
        bounds = geom.bounds
        ee_bounds = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])
        coll = ee.ImageCollection(NAIP_COLLECTION).filterBounds(ee_bounds).filterDate(start, end)
        if coll.size().getInfo() == 0:
            return DownloadResult(
                id=task["id"],
                name=task["name"],
                month=display,
                filename=final_path.name,
                status="No Data for Month",
                extra=task["extra"],
            )

        image = coll.mosaic().select(["R", "G", "B"])
        if not _try_export(image, ee_bounds, temp_path, geemap, scales_to_try):
            return DownloadResult(
                id=task["id"],
                name=task["name"],
                month=display,
                filename=final_path.name,
                status="Download Failed",
                extra=task["extra"],
            )

        # Clip the bounding-box export back to the user's true geometry.
        raster = rioxarray.open_rasterio(temp_path, masked=True)
        clipped = raster.rio.clip([geom], crs="EPSG:4326")
        clipped.rio.to_raster(final_path)

        log.info("Saved %s", final_path.name)
        return DownloadResult(
            id=task["id"],
            name=task["name"],
            month=display,
            filename=final_path.name,
            status="Downloaded",
            extra=task["extra"],
        )

    except Exception as exc:
        log.warning("Error on %s: %s", base, exc)
        return DownloadResult(
            id=task["id"],
            name=task["name"],
            month=display,
            filename=final_path.name,
            status=f"Error: {exc}",
            extra=task["extra"],
        )
    finally:
        if temp_path.exists():
            # Best-effort cleanup; ignore platform-specific unlink failures.
            with contextlib.suppress(OSError):
                temp_path.unlink()


def _try_export(
    image: Any,
    region: Any,
    temp_path: Path,
    geemap: Any,
    scales_to_try: tuple[float, ...],
) -> bool:
    """Attempt the GEE export at progressively coarser scales.

    NAIP at native 0.6 m can blow past GEE's per-request payload limit
    for large polygons; falling back to 1 m, 2 m, 4 m almost always
    succeeds.
    """
    for scale in scales_to_try:
        try:
            geemap.ee_export_image(
                image,
                filename=str(temp_path),
                scale=scale,
                region=region,
                file_per_band=False,
            )
            if temp_path.exists() and temp_path.stat().st_size > _MIN_TEMP_BYTES:
                return True
        except Exception as exc:
            # Only fall back when the failure was a payload-cap error;
            # otherwise the next scale won't help either.
            if "must be less than or equal to" not in str(exc):
                log.debug("Non-recoverable export error: %s", exc)
                return False
    return False


# ---------------------------------------------------------------------------
# Lazy imports -- heavy geospatial deps shouldn't be required to *import*
# this module (e.g. for tooling, docs builds, or testing pure helpers).
# ---------------------------------------------------------------------------


def _import_ee() -> Any:
    try:
        import ee
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Earth Engine support requires the 'earthengine-api' package. "
            "Install with: pip install 'geoimagery[gee]'"
        ) from exc
    return ee


def _import_geemap() -> Any:
    try:
        import geemap
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "geemap is required for downloading. Install with: pip install 'geoimagery[gee]'"
        ) from exc
    return geemap


def _import_rioxarray() -> Any:
    try:
        import rioxarray  # noqa: F401 -- imported for its side effect of

        # registering the .rio accessor on xarray DataArrays.
        import rioxarray as rx
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "rioxarray is required for clipping. Install with: pip install 'geoimagery[geo]'"
        ) from exc
    return rx


def _import_pandas() -> Any:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise ImportError("pandas is required. Install with: pip install pandas") from exc
    return pd
