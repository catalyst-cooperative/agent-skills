"""Tests for the table-name discovery process documented in storage-backends.md.

Exercises the duckdb-no-ext example packages, which contain a DuckDB file
whose resource descriptors carry no duckdb_table extension field.  The tests
walk through the three-step fallback in "Finding the correct table name in a
database file":

  Step 1 (extension field)    — explicitly absent; confirmed by
                                test_no_extension_fields.
  Step 2a (direct name)       — resource "stations" → table "stations"
                                (name matches directly).
  Step 2b (hyphen→underscore) — resource "daily-readings" → table
                                "daily_readings" (raw name raises an error;
                                normalised name succeeds).
  Step 3 (list tables)        — SELECT name FROM (SHOW ALL TABLES) reveals
                                both table names; normalisation maps them back
                                to both resource descriptors.

These tests are parametrized over v1 and v2 only.  The discovery process is
independent of the database engine, so testing on DuckDB alone is sufficient
(SQLite would use sqlite_master instead of SHOW ALL TABLES, but the logic is
identical).

Run:  pixi run pytest dev/skills/datapackage/tests/test_table_discovery.py -v
"""

import json

import duckdb
import pytest
from conftest import EXAMPLES, READING_COUNT, RESOURCE_NAMES, STATION_COUNT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_descriptor(version: str) -> dict:
    path = EXAMPLES / version / "duckdb-no-ext" / "datapackage.json"
    return json.loads(path.read_text())


def resource_by_name(descriptor: dict, name: str) -> dict:
    return next(r for r in descriptor["resources"] if r["name"] == name)


def attach_no_ext(version: str) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection with the no-ext weather.duckdb attached as 'db'."""
    db_path = str(EXAMPLES / version / "duckdb-no-ext" / "weather.duckdb")
    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS db (READ_ONLY)")
    return con


# ---------------------------------------------------------------------------
# Step 1: Confirm that no duckdb_table extension field is present.
#
# This establishes the scenario that triggers the fallback process — if the
# extension field were present, the agent would use it directly and skip
# steps 2 and 3 entirely.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_no_extension_fields(version):
    """No resource in the duckdb-no-ext descriptor has a duckdb_table field."""
    descriptor = load_descriptor(version)
    for resource in descriptor["resources"]:
        assert "duckdb_table" not in resource, (
            f"{version}/duckdb-no-ext: resource '{resource['name']}' unexpectedly "
            "has a duckdb_table field — this fixture should have none."
        )


# ---------------------------------------------------------------------------
# Step 2a: Try resource name directly.
#
# "stations" (the resource name) is also the table name inside the DuckDB
# file — no transformation required.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_step2a_direct_name_match(version):
    """Resource name 'stations' matches the DuckDB table name directly."""
    descriptor = load_descriptor(version)
    resource = resource_by_name(descriptor, "stations")
    table_name = resource["name"]  # "stations"

    con = attach_no_ext(version)
    count = con.execute(f'SELECT count(*) FROM db."{table_name}"').fetchall()[0][0]
    assert count == STATION_COUNT, (
        f"{version}/duckdb-no-ext: expected {STATION_COUNT} rows via direct name "
        f"'{table_name}', got {count}"
    )


# ---------------------------------------------------------------------------
# Step 2b: Resource name does not match; hyphen → underscore transform finds it.
#
# "daily-readings" contains a hyphen, which is not a valid SQL identifier
# character.  The table was created as "daily_readings".  The agent should:
#   1. Try the raw resource name → expect a CatalogException (table not found)
#   2. Replace hyphens with underscores → query succeeds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_step2b_raw_name_fails(version):
    """Querying 'daily-readings' by the raw resource name raises CatalogException."""
    con = attach_no_ext(version)
    with pytest.raises(duckdb.CatalogException):
        con.execute('SELECT count(*) FROM db."daily-readings"').fetchall()


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_step2b_hyphen_to_underscore(version):
    """Replacing hyphens with underscores in 'daily-readings' finds the table."""
    descriptor = load_descriptor(version)
    resource = resource_by_name(descriptor, "daily-readings")
    table_name = resource["name"].replace("-", "_")  # "daily_readings"

    con = attach_no_ext(version)
    count = con.execute(f'SELECT count(*) FROM db."{table_name}"').fetchall()[0][0]
    assert count == READING_COUNT, (
        f"{version}/duckdb-no-ext: expected {READING_COUNT} rows after "
        f"hyphen→underscore transform "
        f"('{resource['name']}' → '{table_name}'), got {count}"
    )


# ---------------------------------------------------------------------------
# Step 3: List tables and infer the resource → table mapping.
#
# When neither the extension field nor name-based heuristics are obvious,
# the agent lists all tables in the attached database, then matches each
# resource name against the table list using normalisation (lower-case,
# hyphens→underscores).
#
# Note: SHOW TABLES only lists the in-memory database.  Use SHOW ALL TABLES
# (documented in storage-backends.md) and filter by the attached database
# name to list tables in an attached file.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_step3_show_tables_returns_expected_names(version):
    """SHOW ALL TABLES filtered by 'db' returns exactly the two expected table names."""
    con = attach_no_ext(version)
    rows = con.execute(
        "SELECT name FROM (SHOW ALL TABLES) WHERE database = 'db' ORDER BY name"
    ).fetchall()
    table_names = {row[0] for row in rows}
    assert table_names == {"daily_readings", "stations"}, (
        f"{version}/duckdb-no-ext: SHOW ALL TABLES returned {table_names!r}, "
        "expected {'daily_readings', 'stations'}"
    )


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_step3_infer_resource_to_table_mapping(version):
    """Normalising resource names maps every resource to a real table.

    Models the agent algorithm: list all tables, then for each resource try
    the name as-is, then with hyphens replaced by underscores.  A complete
    mapping means the agent can proceed to query every resource.
    """
    descriptor = load_descriptor(version)
    con = attach_no_ext(version)

    available_tables = {
        row[0]
        for row in con.execute(
            "SELECT name FROM (SHOW ALL TABLES) WHERE database = 'db'"
        ).fetchall()
    }

    resource_to_table: dict[str, str] = {}
    for resource in descriptor["resources"]:
        name = resource["name"]
        if name in available_tables:
            resource_to_table[name] = name
        elif (normalised := name.replace("-", "_")) in available_tables:
            resource_to_table[name] = normalised

    assert set(resource_to_table.keys()) == set(RESOURCE_NAMES), (
        f"{version}/duckdb-no-ext: could not map all resources to tables.\n"
        f"  Resources:        {RESOURCE_NAMES}\n"
        f"  Available tables: {sorted(available_tables)}\n"
        f"  Mapped:           {resource_to_table}"
    )
    assert resource_to_table["stations"] == "stations", (
        f"{version}/duckdb-no-ext: 'stations' should map directly to 'stations'"
    )
    assert resource_to_table["daily-readings"] == "daily_readings", (
        f"{version}/duckdb-no-ext: 'daily-readings' should map to 'daily_readings' "
        "after hyphen→underscore normalisation"
    )
