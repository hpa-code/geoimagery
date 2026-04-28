"""Pure-Python helpers used by the rest of the package.

These functions deliberately have no Earth Engine, GeoPandas, or rasterio
dependency so they can be tested quickly and without network access.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import datetime

# A practical superset of characters that are illegal or awkward across
# Windows, macOS, Linux, and zip archives.
_FILENAME_FORBIDDEN = re.compile(r'[\\/:*?"<>|]+')


def sanitize_filename_component(value: str) -> str:
    """Make ``value`` safe to use as one component of a file name.

    Replaces forbidden characters with underscores and collapses any run of
    whitespace into a single space. Leading/trailing whitespace is removed.

    Examples
    --------
    >>> sanitize_filename_component("Some / Place: 2024")
    'Some _ Place_ 2024'
    >>> sanitize_filename_component("  multi   spaces  ")
    'multi spaces'
    """
    cleaned = _FILENAME_FORBIDDEN.sub("_", value)
    return " ".join(cleaned.split()).strip()


def parse_available_dates(value: object) -> list[str]:
    """Parse a comma-separated 'Available_Dates' string into a list.

    Accepts the loose CSV format produced by :func:`list_available_dates`
    (e.g. ``"June 2023, August 2023, June 2024"``) and returns a
    de-duplicated, order-preserving list of month labels.

    Empty values, ``None``, ``"N/A"``, and rows that begin with ``"Error:"``
    all collapse to an empty list.
    """
    if value is None:
        return []

    text = str(value).strip()
    if not text or text == "N/A" or text.startswith("Error:") or text.lower() == "nan":
        return []

    parts = [part.strip() for part in text.split(",") if part.strip()]
    # dict.fromkeys preserves order while removing duplicates.
    return list(dict.fromkeys(parts))


def build_month_window(month_label: str) -> tuple[str, str, str]:
    """Convert a 'June 2023' style label into a date window.

    Returns
    -------
    (start, end, display_label)
        ``start`` is inclusive (``YYYY-MM-DD``), ``end`` is the first day
        of the *following* month (Earth Engine's ``filterDate`` is
        end-exclusive), and ``display_label`` is a friendly form suitable
        for filenames.

    Examples
    --------
    >>> build_month_window("June 2023")
    ('2023-06-01', '2023-07-01', 'June, 2023')
    >>> build_month_window("December 2024")
    ('2024-12-01', '2025-01-01', 'December, 2024')
    """
    month_start = datetime.strptime(month_label, "%B %Y")
    if month_start.month == 12:
        next_month = datetime(month_start.year + 1, 1, 1)
    else:
        next_month = datetime(month_start.year, month_start.month + 1, 1)
    return (
        month_start.strftime("%Y-%m-%d"),
        next_month.strftime("%Y-%m-%d"),
        month_start.strftime("%B, %Y"),
    )


def chunked(items: Iterable[object], size: int) -> Iterable[list[object]]:
    """Yield successive ``size``-sized chunks from ``items``.

    Used internally to batch GEE requests below the per-request payload
    limit. ``size`` must be at least 1.
    """
    if size < 1:
        raise ValueError("chunk size must be >= 1")

    bucket: list[object] = []
    for item in items:
        bucket.append(item)
        if len(bucket) == size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket
