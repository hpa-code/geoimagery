"""Smallest possible example: one polygon, one month, one GeoTIFF.

Usage:
    export GEE_PROJECT=your-gcp-project-id
    python examples/quickstart.py
"""

from __future__ import annotations

import os
from pathlib import Path

from shapely.geometry import box

import geoimagery as gi


def main() -> None:
    project = os.environ.get("GEE_PROJECT")
    if not project:
        raise SystemExit(
            "Please set the GEE_PROJECT environment variable to your Google Cloud project ID."
        )

    # 1. Initialise Earth Engine (one-time per process).
    gi.initialize(project=project)

    # 2. Define a tiny area of interest. Anywhere in the contiguous US works.
    #    This is a small patch of Rochester, NY.
    aoi = box(-77.62, 43.12, -77.60, 43.14)

    # 3. (Optional) See what NAIP imagery is available for this area.
    inventory = gi.list_available_dates(
        aoi,
        start_date="2018-01-01",
        end_date="2025-01-01",
    )
    print("Available NAIP dates for this AOI:")
    print(inventory.to_string(index=False))

    # 4. Pick one of those months and download.
    months = gi.parse_available_dates(inventory.iloc[0]["available_dates"])
    if not months:
        print("No NAIP coverage for this area in the requested window.")
        return

    out_dir = Path("./naip_output")
    print(f"\nDownloading {months[0]} into {out_dir}/ ...")
    results = gi.download(
        aoi,
        dates=[months[0]],
        output_dir=out_dir,
        max_workers=1,
    )
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
