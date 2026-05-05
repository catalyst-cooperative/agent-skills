"""Tests for frictionless validate patterns documented in references/frictionless-validate.md.

Each test exercises a specific CLI pattern from that reference so a failing test
immediately tells an agent which documented command broke and what the actual
output was.

Run:  pixi run pytest dev/skills/datapackage/tests/test_frictionless.py -v
"""

import json
import subprocess
from pathlib import Path

import pytest
from conftest import EXAMPLES, READING_COUNT, RESOURCE_NAMES, STATION_COUNT

# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


def frictionless(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Invoke the frictionless CLI and return the CompletedProcess."""
    return subprocess.run(
        ["frictionless", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def assert_exit_zero(result: subprocess.CompletedProcess) -> None:
    """Assert frictionless exited 0; include full output on failure."""
    assert result.returncode == 0, (
        f"frictionless exited {result.returncode}\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Basic validation — all 8 packages should validate cleanly
#
# Parquet: skip all row-level errors — frictionless is used for descriptor
#   validation only; row data is validated in test_backends.py via DuckDB/polars.
#
#   fastparquet (frictionless's Parquet backend) has two problems that prevent
#   meaningful row-level validation:
#
#   - byte-count: fastparquet doesn't expose raw file bytes, so the file-size
#     integrity check always fails.
#   - type-error: fastparquet misreads Parquet date32 columns as nanosecond
#     epoch integers, which frictionless cannot validate against "type": "date".
#   - primary-key: once date values fail to parse, frictionless treats them as
#     null, making every (station_id, null) pair look like a duplicate.
#
#   Note: "--limit-rows 0" does NOT help here — fastparquet reads the entire
#   file into memory when it opens it, so frictionless receives all rows
#   regardless.  Skipping the error types is the only workable approach.
#
#   These errors reflect fastparquet limitations, not actual data quality issues.
#   The Parquet files correctly encode dates as INT32 with DATE logical type.
#
# SQLite and DuckDB validate at file level only (type="file"); they don't read
# rows, so no row-level flags are needed.
# ---------------------------------------------------------------------------

_PARQUET_DESCRIPTOR_ONLY = ["--skip-errors", "byte-count,type-error,primary-key"]


@pytest.mark.parametrize(
    "version,backend,extra_args",
    [
        ("v1", "csv", ["--standards", "v1"]),
        ("v2", "csv", ["--standards", "v2"]),
        ("v1", "parquet", _PARQUET_DESCRIPTOR_ONLY),
        ("v2", "parquet", _PARQUET_DESCRIPTOR_ONLY),
        ("v1", "sqlite", []),
        ("v2", "sqlite", []),
        ("v1", "duckdb", []),
        ("v2", "duckdb", []),
    ],
    ids=lambda x: "/".join(x) if isinstance(x, list) and x else (x or "no-flags"),
)
def test_validates(version, backend, extra_args):
    """Every example package validates without errors (basic usage from the reference)."""
    pkg = EXAMPLES / version / backend / "datapackage.json"
    result = frictionless("validate", str(pkg), *extra_args)
    assert_exit_zero(result)


# ---------------------------------------------------------------------------
# --json output structure (frictionless validate --json)
# Reference: "Machine-readable output" section
# ---------------------------------------------------------------------------


def test_json_output_structure_csv():
    """--json output matches the documented structure: valid, stats, tasks."""
    pkg = EXAMPLES / "v2" / "csv" / "datapackage.json"
    result = frictionless("validate", "--json", str(pkg))
    assert_exit_zero(result)
    report = json.loads(result.stdout)

    # Top-level fields documented in the reference
    assert report["valid"] is True, (
        f"Package reported invalid:\n{json.dumps(report, indent=2)}"
    )
    assert report["stats"]["tasks"] == 2
    assert report["stats"]["errors"] == 0

    task_names = {t["name"] for t in report["tasks"]}
    assert task_names == set(RESOURCE_NAMES), f"Unexpected task names: {task_names}"

    for task in report["tasks"]:
        assert task["valid"] is True, (
            f"Task '{task['name']}' is invalid:\n{json.dumps(task['errors'], indent=2)}"
        )
        assert task["type"] == "table", (
            f"Expected type='table' for CSV resource '{task['name']}', "
            f"got '{task['type']}'. "
            "See 'Storage backend behavior' in frictionless-validate.md."
        )
        assert task["stats"]["errors"] == 0

    # Verify documented row counts
    by_name = {t["name"]: t for t in report["tasks"]}
    assert by_name["stations"]["stats"]["rows"] == STATION_COUNT, (
        f"Expected {STATION_COUNT} station rows, "
        f"got {by_name['stations']['stats']['rows']}"
    )
    assert by_name["daily-readings"]["stats"]["rows"] == READING_COUNT, (
        f"Expected {READING_COUNT} reading rows, "
        f"got {by_name['daily-readings']['stats']['rows']}"
    )


# ---------------------------------------------------------------------------
# --resource-name: validate a single resource
# Reference: "Basic usage" section
# ---------------------------------------------------------------------------


def test_resource_name_flag():
    """--resource-name limits validation to one named resource."""
    pkg = EXAMPLES / "v2" / "csv" / "datapackage.json"
    result = frictionless("validate", "--json", "--resource-name", "stations", str(pkg))
    assert_exit_zero(result)
    report = json.loads(result.stdout)
    assert report["stats"]["tasks"] == 1, (
        f"Expected 1 task with --resource-name stations, got {report['stats']['tasks']}"
    )
    assert report["tasks"][0]["name"] == "stations"


# ---------------------------------------------------------------------------
# --standards flag
# Reference: "Spec version handling" section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version,standards", [("v1", "v1"), ("v2", "v2")])
def test_standards_flag(version, standards):
    """--standards v1/v2 validates the matching spec-version descriptor."""
    pkg = EXAMPLES / version / "csv" / "datapackage.json"
    result = frictionless("validate", "--standards", standards, "--json", str(pkg))
    assert_exit_zero(result)
    report = json.loads(result.stdout)
    assert report["valid"] is True


# ---------------------------------------------------------------------------
# --checks table-dimensions
# Reference: "Adding extra checks" section
# ---------------------------------------------------------------------------


def test_table_dimensions_check_stations():
    """--checks table-dimensions:numRows=5 passes for the 5-row stations file.

    frictionless rejects absolute paths as 'not safe' when using --checks on a
    standalone file, so this test runs from the file's parent directory and
    passes a relative path — matching the usage shown in the reference.
    """
    csv_dir = EXAMPLES / "v2" / "csv"
    result = frictionless(
        "validate",
        "--checks",
        f"table-dimensions:numRows={STATION_COUNT}",
        "stations.csv",
        cwd=csv_dir,
    )
    assert_exit_zero(result)


def test_table_dimensions_check_readings():
    """--checks table-dimensions:numRows=150 passes for 150 daily readings (5×30)."""
    pkg = EXAMPLES / "v2" / "csv" / "datapackage.json"
    result = frictionless(
        "validate",
        "--json",
        "--resource-name",
        "daily-readings",
        "--checks",
        f"table-dimensions:numRows={READING_COUNT}",
        str(pkg),
    )
    assert_exit_zero(result)
    report = json.loads(result.stdout)
    assert report["valid"] is True


# ---------------------------------------------------------------------------
# --limit-rows 0: fast descriptor check without reading any data
# Reference: "Diagnosing an unknown descriptor" section
# ---------------------------------------------------------------------------


def test_limit_rows_zero_is_fast_structural_check():
    """--limit-rows 0 validates descriptor structure without reading data rows."""
    pkg = EXAMPLES / "v2" / "csv" / "datapackage.json"
    result = frictionless("validate", "--limit-rows", "0", "--json", str(pkg))
    assert_exit_zero(result)
    report = json.loads(result.stdout)
    assert report["valid"] is True


# ---------------------------------------------------------------------------
# Storage backend behavior: type in JSON output
# Reference: "Storage backend behavior" table
#
# SQLite and DuckDB produce type="file" because frictionless checks file
# existence and integrity but cannot read rows from these formats.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,backend",
    [
        ("v1", "sqlite"),
        ("v2", "sqlite"),
        ("v1", "duckdb"),
        ("v2", "duckdb"),
    ],
)
def test_db_backends_produce_type_file(version, backend):
    """SQLite and DuckDB resources report type='file', not type='table'."""
    pkg = EXAMPLES / version / backend / "datapackage.json"
    result = frictionless("validate", "--json", str(pkg))
    assert_exit_zero(result)
    report = json.loads(result.stdout)
    for task in report["tasks"]:
        assert task["type"] == "file", (
            f"{version}/{backend} resource '{task['name']}': "
            f"expected type='file', got '{task['type']}'. "
            "See 'Storage backend behavior' in frictionless-validate.md."
        )


# ---------------------------------------------------------------------------
# frictionless describe: schema inference from a raw file
# Reference: "Inferring schemas from raw files" section
# ---------------------------------------------------------------------------


def test_describe_infers_schema_from_csv():
    """frictionless describe --json infers a resource descriptor from a CSV file."""
    stations_csv = EXAMPLES / "v2" / "csv" / "stations.csv"
    result = frictionless("describe", "--json", str(stations_csv))
    assert result.returncode == 0, (
        f"frictionless describe failed:\nstderr: {result.stderr}"
    )
    descriptor = json.loads(result.stdout)
    assert "schema" in descriptor, "Inferred descriptor missing 'schema' key"
    inferred_names = [f["name"] for f in descriptor["schema"]["fields"]]
    for col in ("station_id", "commissioned_date", "latitude"):
        assert col in inferred_names, (
            f"Expected column '{col}' in inferred schema, got: {inferred_names}"
        )
