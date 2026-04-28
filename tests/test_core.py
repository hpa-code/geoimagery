"""Tests for geoimagery.core.

Anything that would actually call Earth Engine is marked
``@pytest.mark.integration`` and skipped by default.  The tests here
focus on pure-logic pieces (task building, filename construction)
using monkey-patching where needed.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from geoimagery import __version__
from geoimagery.core import DownloadResult, _build_tasks


def test_version_string_is_pep440() -> None:
    # SemVer-ish; PEP 440 is fine with 0.1.0.
    assert __version__ == "0.1.0"


def test_download_result_as_dict_round_trips() -> None:
    res = DownloadResult(
        id="42",
        name="My Place",
        month="June, 2023",
        filename="42_My Place_June_2023.tif",
        status="Downloaded",
        extra={"state": "NY"},
    )
    d = res.as_dict()
    assert d["id"] == "42"
    assert d["name"] == "My Place"
    assert d["status"] == "Downloaded"
    assert d["state"] == "NY"


def test_build_tasks_with_explicit_dates(require_geo, sample_geojson_dict) -> None:
    pytest.importorskip("geopandas")
    from geoimagery.geometry import load_geometries

    gdf = load_geometries(sample_geojson_dict)
    tasks = _build_tasks(gdf, ["June 2023", "July 2023"])

    # 2 features x 2 months = 4 tasks
    assert len(tasks) == 4
    months = {t["month_label"] for t in tasks}
    assert months == {"June 2023", "July 2023"}
    ids = {t["id"] for t in tasks}
    assert ids == {"A", "B"}


def test_build_tasks_with_per_feature_dataframe(
    require_geo,
    sample_geojson_dict: dict,
) -> None:
    pd = pytest.importorskip("pandas")
    from geoimagery.geometry import load_geometries

    gdf = load_geometries(sample_geojson_dict)

    inventory = pd.DataFrame(
        {
            "id": ["A", "B"],
            "available_dates": ["June 2023, July 2023", "August 2023"],
        }
    )
    tasks = _build_tasks(gdf, inventory)

    # A gets 2 months, B gets 1 -> 3 tasks total.
    assert len(tasks) == 3
    a_months = sorted(t["month_label"] for t in tasks if t["id"] == "A")
    b_months = sorted(t["month_label"] for t in tasks if t["id"] == "B")
    assert a_months == ["July 2023", "June 2023"]
    assert b_months == ["August 2023"]


def test_build_tasks_dataframe_missing_columns_raises(
    require_geo,
    sample_geojson_dict: dict,
) -> None:
    pd = pytest.importorskip("pandas")
    from geoimagery.geometry import load_geometries

    gdf = load_geometries(sample_geojson_dict)
    bad = pd.DataFrame({"id": ["A"], "wrong_column": ["June 2023"]})
    with pytest.raises(ValueError, match="available_dates"):
        _build_tasks(gdf, bad)


# ---------------------------------------------------------------------------
# Lazy import behaviour
# ---------------------------------------------------------------------------


def test_importing_top_level_does_not_require_ee() -> None:
    """Importing the package shouldn't drag in earthengine-api.

    Heavy deps are gated behind helper functions so e.g. doc builds and
    tooling work even on machines without GEE installed.
    """
    mod = importlib.import_module("geoimagery")
    # Public API surface is exported regardless of whether ee is present.
    for name in (
        "download",
        "initialize",
        "list_available_dates",
        "load_geometries",
        "parse_available_dates",
        "build_month_window",
        "sanitize_filename_component",
    ):
        assert hasattr(mod, name), f"missing public symbol: {name}"


# ---------------------------------------------------------------------------
# Integration tests (skipped by default; require GEE auth)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_download_real_naip_image(tmp_path: Path) -> None:
    """End-to-end smoke test against real Earth Engine.

    Run with: ``pytest -m integration``.
    Requires ``earthengine authenticate`` to have been run beforehand
    and the env var ``GEE_PROJECT`` to be set.
    """
    import os

    pytest.importorskip("ee")
    pytest.importorskip("geemap")
    pytest.importorskip("geopandas")
    pytest.importorskip("rioxarray")
    project = os.environ.get("GEE_PROJECT")
    if not project:
        pytest.skip("GEE_PROJECT env var not set")

    from shapely.geometry import box

    import geoimagery as gi

    gi.initialize(project=project)

    # A 200m-square patch -- well under any payload limit.
    aoi = box(-77.6105, 43.1305, -77.6085, 43.1325)
    out = gi.download(
        aoi,
        dates=["June 2023"],
        output_dir=tmp_path,
        max_workers=1,
    )

    assert len(out) == 1
    status = out.iloc[0]["status"]
    # Either we got data or the month had none -- both are valid outcomes.
    assert status in {"Downloaded", "No Data for Month", "Already Downloaded"}
