"""Tests for pure-Python helpers in geoimagery.utils."""

from __future__ import annotations

import pytest

from geoimagery import (
    build_month_window,
    parse_available_dates,
    sanitize_filename_component,
)
from geoimagery.utils import chunked

# ---------------------------------------------------------------------------
# sanitize_filename_component
# ---------------------------------------------------------------------------


class TestSanitizeFilenameComponent:
    def test_replaces_path_separators(self) -> None:
        assert sanitize_filename_component("foo/bar") == "foo_bar"
        assert sanitize_filename_component("foo\\bar") == "foo_bar"

    def test_replaces_other_forbidden_chars(self) -> None:
        assert sanitize_filename_component('a:b*c?d"e<f>g|h') == "a_b_c_d_e_f_g_h"

    def test_collapses_whitespace(self) -> None:
        assert sanitize_filename_component("  multi   spaces  ") == "multi spaces"

    def test_leaves_safe_strings_alone(self) -> None:
        assert sanitize_filename_component("June 2023") == "June 2023"
        assert sanitize_filename_component("MIT_Cambridge") == "MIT_Cambridge"

    def test_empty_string(self) -> None:
        assert sanitize_filename_component("") == ""

    def test_idempotent(self) -> None:
        once = sanitize_filename_component("Some/odd:name")
        twice = sanitize_filename_component(once)
        assert once == twice


# ---------------------------------------------------------------------------
# parse_available_dates
# ---------------------------------------------------------------------------


class TestParseAvailableDates:
    def test_normal_csv(self) -> None:
        out = parse_available_dates("June 2023, August 2023, June 2024")
        assert out == ["June 2023", "August 2023", "June 2024"]

    def test_dedup_preserves_order(self) -> None:
        out = parse_available_dates("June 2023, June 2023, August 2023")
        assert out == ["June 2023", "August 2023"]

    def test_handles_extra_whitespace(self) -> None:
        out = parse_available_dates("  June 2023 ,  August 2023 ")
        assert out == ["June 2023", "August 2023"]

    def test_empty_inputs_become_empty_list(self) -> None:
        assert parse_available_dates(None) == []
        assert parse_available_dates("") == []
        assert parse_available_dates("   ") == []

    def test_sentinels_become_empty_list(self) -> None:
        assert parse_available_dates("N/A") == []
        assert parse_available_dates("Error: something exploded") == []
        assert parse_available_dates("nan") == []

    def test_non_string_value_coerced(self) -> None:
        # A pandas NaN ends up as a float; we should treat it gracefully.
        assert parse_available_dates(float("nan")) == []


# ---------------------------------------------------------------------------
# build_month_window
# ---------------------------------------------------------------------------


class TestBuildMonthWindow:
    def test_mid_year_month(self) -> None:
        start, end, label = build_month_window("June 2023")
        assert start == "2023-06-01"
        assert end == "2023-07-01"
        assert label == "June, 2023"

    def test_december_rolls_year(self) -> None:
        start, end, label = build_month_window("December 2024")
        assert start == "2024-12-01"
        assert end == "2025-01-01"
        assert label == "December, 2024"

    def test_january_rolls_correctly(self) -> None:
        start, end, _ = build_month_window("January 2024")
        assert start == "2024-01-01"
        assert end == "2024-02-01"

    def test_invalid_label_raises(self) -> None:
        with pytest.raises(ValueError):
            build_month_window("Junuary 2023")
        with pytest.raises(ValueError):
            build_month_window("2023-06")


# ---------------------------------------------------------------------------
# chunked
# ---------------------------------------------------------------------------


class TestChunked:
    def test_even_chunks(self) -> None:
        assert list(chunked([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]

    def test_uneven_remainder(self) -> None:
        assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]

    def test_size_larger_than_input(self) -> None:
        assert list(chunked([1, 2], 10)) == [[1, 2]]

    def test_empty_input(self) -> None:
        assert list(chunked([], 3)) == []

    def test_invalid_size(self) -> None:
        with pytest.raises(ValueError):
            list(chunked([1, 2], 0))
        with pytest.raises(ValueError):
            list(chunked([1, 2], -1))
