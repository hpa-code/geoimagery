"""Batch example: read a GeoJSON, inventory, then download every month.

Usage:
    export GEE_PROJECT=your-gcp-project-id
    python examples/from_geojson.py path/to/areas.geojson ./output
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import geoimagery as gi


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)

    geojson_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    project = os.environ.get("GEE_PROJECT")
    if not project:
        raise SystemExit("Please set GEE_PROJECT to your Google Cloud project ID.")

    gi.initialize(project=project)

    print(f"Building availability inventory from {geojson_path} ...")
    inventory = gi.list_available_dates(
        geojson_path,
        start_date="2018-01-01",
        end_date="2025-01-01",
    )
    inv_path = output_dir / "availability.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(inv_path, index=False)
    print(f"Inventory written to {inv_path}")

    print("\nDownloading imagery (this may take a while)...")
    results = gi.download(
        geojson_path,
        dates=inventory,
        output_dir=output_dir,
        max_workers=5,
    )

    log_path = output_dir / "download_log.csv"
    results.to_csv(log_path, index=False)
    print(f"\nDownload log written to {log_path}")

    by_status = results["status"].value_counts()
    print("\nSummary:")
    print(by_status.to_string())


if __name__ == "__main__":
    main()
