"""
Tests for nlp4j_local_search.cli.search.main

Covers the three changes introduced for DATE histogram support:
  1. view(..., interval=...) keyword is accepted
  2. Unknown view kwargs raise ValueError
  3. --time-zone argument is parsed and passed to SearchCli / SearchEngine

All tests that touch SearchCli.view() use a stub engine so that no JVM
is required.
"""
from __future__ import annotations

import pytest

# parse_function_call, parse_args, SearchCli, create_parser are pure Python
# and do not require readline or JVM.
from nlp4j_local_search.cli.search.main import (
    SearchCli,
    create_parser,
    parse_args,
    parse_function_call,
)
from nlp4j_local_search.errors import InvalidDocumentError


# ---------------------------------------------------------------------------
# Stub engine — no JVM needed
# ---------------------------------------------------------------------------

class _ViewResult:
    """Minimal ViewResult stub."""

    def __init__(self, field, interval=None):
        self.fields = [type("VF", (), {"field": field, "interval": interval, "buckets": []})()]
        self.sort_key = "key" if interval else "count"

    def filter(self, **_kw):
        return self

    def __str__(self):
        return f"<ViewResult field={self.fields[0].field} interval={self.fields[0].interval}>"


class _StubEngine:
    """Minimal engine stub that records view() calls."""

    def __init__(self):
        self.last_view_kwargs = {}

    def view(self, field=None, query=None, *, size=None, interval=None):
        self.last_view_kwargs = {
            "field": field,
            "query": query,
            "size": size,
            "interval": interval,
        }
        return _ViewResult(field, interval=interval)

    def count(self):
        return 0

    def fields(self):
        return []

    def aggregatable_fields(self):
        return []

    def close(self):
        pass


def _make_cli(time_zone=None) -> SearchCli:
    cli = SearchCli(lang="en", time_zone=time_zone)
    cli.engine = _StubEngine()
    return cli


# ---------------------------------------------------------------------------
# 1. parse_function_call — keyword argument round-trip
# ---------------------------------------------------------------------------

def test_parse_function_call_with_interval_kwarg():
    name, args, kwargs = parse_function_call('view("created_dt", interval="year")')
    assert name == "view"
    assert args == ["created_dt"]
    assert kwargs == {"interval": "year"}


def test_parse_function_call_with_query_and_interval():
    name, args, kwargs = parse_function_call(
        'view("created_dt", "Nissan", interval="year")'
    )
    assert name == "view"
    assert args == ["created_dt", "Nissan"]
    assert kwargs == {"interval": "year"}


# ---------------------------------------------------------------------------
# 2. execute() — view with interval= accepted
# ---------------------------------------------------------------------------

def test_cli_view_date_histogram_year(capsys):
    cli = _make_cli()
    cli.execute('view("created_dt", interval="year")')

    kw = cli.engine.last_view_kwargs
    assert kw["field"] == "created_dt"
    assert kw["interval"] == "year"
    assert kw["query"] is None


def test_cli_view_date_histogram_month(capsys):
    cli = _make_cli()
    cli.execute('view("created_dt", interval="month")')

    assert cli.engine.last_view_kwargs["interval"] == "month"


def test_cli_view_date_histogram_with_query(capsys):
    cli = _make_cli()
    cli.execute('view("created_dt", "Nissan", interval="year")')

    kw = cli.engine.last_view_kwargs
    assert kw["field"] == "created_dt"
    assert kw["query"] == "Nissan"
    assert kw["interval"] == "year"


# ---------------------------------------------------------------------------
# 3. execute() — unknown view kwargs raise ValueError
# ---------------------------------------------------------------------------

def test_cli_view_unknown_option_raises():
    cli = _make_cli()
    with pytest.raises(ValueError, match="Unknown view options"):
        cli.execute('view("created_dt", foo="year")')


def test_cli_view_unknown_option_name_shown():
    cli = _make_cli()
    try:
        cli.execute('view("created_dt", foo="year")')
    except ValueError as e:
        assert "foo" in str(e)


# ---------------------------------------------------------------------------
# 4. SearchCli.view() — interval branch does NOT pass size=
# ---------------------------------------------------------------------------

def test_cli_view_interval_does_not_pass_size():
    cli = _make_cli()
    cli.view("created_dt", interval="year")

    kw = cli.engine.last_view_kwargs
    assert kw["interval"] == "year"
    assert kw["size"] is None  # size must not be forwarded in interval mode


def test_cli_view_no_interval_passes_size():
    cli = _make_cli()
    cli.view("created_dt")

    kw = cli.engine.last_view_kwargs
    assert kw["interval"] is None
    assert kw["size"] == 10  # default size forwarded


# ---------------------------------------------------------------------------
# 5. --time-zone argument parsing
# ---------------------------------------------------------------------------

def test_parse_args_time_zone():
    parsed = parse_args(["--lang", "ja", "--time-zone", "Asia/Tokyo"])
    assert parsed.time_zone == "Asia/Tokyo"


def test_parse_args_time_zone_utc():
    parsed = parse_args(["--lang", "en", "--time-zone", "UTC"])
    assert parsed.time_zone == "UTC"


def test_parse_args_no_time_zone_defaults_none():
    parsed = parse_args(["--lang", "ja"])
    assert parsed.time_zone is None


# ---------------------------------------------------------------------------
# 6. SearchCli stores time_zone and would pass it to SearchEngine
# ---------------------------------------------------------------------------

def test_search_cli_stores_time_zone():
    cli = SearchCli(lang="ja", time_zone="Asia/Tokyo")
    assert cli.time_zone == "Asia/Tokyo"


def test_search_cli_default_time_zone_is_none():
    cli = SearchCli(lang="ja")
    assert cli.time_zone is None
