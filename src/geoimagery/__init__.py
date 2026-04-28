"""geoimagery: download satellite imagery for arbitrary polygons.

A small, focused library that wraps Google Earth Engine to download
NAIP (National Agriculture Imagery Program) imagery for any polygon
or set of polygons you supply.

Quickstart
----------
>>> import geoimagery as gi
>>> gi.initialize(project="my-gcp-project")
>>> # Any of these work as input:
>>> #  - a shapely geometry
>>> #  - a list of shapely geometries
>>> #  - a GeoDataFrame
>>> #  - a path to a GeoJSON / Shapefile / any GDAL-readable file
>>> inventory = gi.list_available_dates(
...     "my_areas.geojson",
...     start_date="2022-01-01",
...     end_date="2024-12-31",
... )
>>> results = gi.download(
...     "my_areas.geojson",
...     dates=["June 2023", "August 2024"],
...     output_dir="./naip_output",
... )
"""

from __future__ import annotations

from geoimagery.__version__ import __version__
from geoimagery.core import (
    DownloadResult,
    download,
    initialize,
    list_available_dates,
)
from geoimagery.geometry import load_geometries
from geoimagery.utils import (
    build_month_window,
    parse_available_dates,
    sanitize_filename_component,
)

__all__ = [
    "DownloadResult",
    "__version__",
    "build_month_window",
    "download",
    "initialize",
    "list_available_dates",
    "load_geometries",
    "parse_available_dates",
    "sanitize_filename_component",
]
