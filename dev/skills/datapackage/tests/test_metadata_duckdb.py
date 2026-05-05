"""Tests for jq-to-DuckDB handoff patterns from references/metadata-querying.md.

The metadata workflow is jq-first: use jq to discover resource paths from
`datapackage.json`, then use DuckDB to query the referenced data files.

Run:  pixi run pytest dev/skills/datapackage/tests/test_metadata_duckdb.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

import duckdb
import pytest
from conftest import EXAMPLES, READING_COUNT, RESOURCE_NAMES, STATION_COUNT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def jq(expr: str, path: Path) -> Any:
    """Run a jq expression and return parsed JSON output."""
    result = subprocess.run(
        ["jq", "-c", expr, str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"jq exited {result.returncode}\n"
        f"expression: {expr!r}\n"
        f"file: {path}\n"
        f"stderr: {result.stderr}"
    )
    lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    if len(lines) == 1:
        return json.loads(lines[0])
    return [json.loads(ln) for ln in lines]


# ---------------------------------------------------------------------------
# Policy-aligned handoff: jq for metadata, DuckDB for data
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,backend",
    [
        ("v1", "csv"),
        ("v2", "csv"),
        ("v1", "parquet"),
        ("v2", "parquet"),
    ],
)
def test_jq_discovers_paths_then_duckdb_reads_data(version, backend):
    """Use jq to discover resource paths, then query those files with DuckDB."""
    pkg_dir = EXAMPLES / version / backend
    pkg = pkg_dir / "datapackage.json"

    resources = jq("[.resources[] | {name, path}]", pkg)
    by_name = {item["name"]: item["path"] for item in resources}
    assert set(by_name) == set(RESOURCE_NAMES), (
        f"{version}/{backend}: expected resources {RESOURCE_NAMES}, got {set(by_name)}"
    )

    stations_path = str(pkg_dir / by_name["stations"])
    readings_path = str(pkg_dir / by_name["daily-readings"])

    if backend == "csv":
        stations_count = duckdb.sql(
            f"SELECT count(*) FROM read_csv('{stations_path}')"
        ).fetchall()[0][0]
        readings_count = duckdb.sql(
            f"SELECT count(*) FROM read_csv('{readings_path}')"
        ).fetchall()[0][0]
    else:
        stations_count = duckdb.sql(
            f"SELECT count(*) FROM read_parquet('{stations_path}')"
        ).fetchall()[0][0]
        readings_count = duckdb.sql(
            f"SELECT count(*) FROM read_parquet('{readings_path}')"
        ).fetchall()[0][0]

    assert stations_count == STATION_COUNT, (
        f"{version}/{backend}/stations: expected {STATION_COUNT}, got {stations_count}"
    )
    assert readings_count == READING_COUNT, (
        f"{version}/{backend}/daily-readings: expected {READING_COUNT}, got {readings_count}"
    )


def test_jq_extracts_relative_path_string_for_handoff():
    """Step 4 handoff query returns a relative path string from the descriptor."""
    pkg = EXAMPLES / "v2" / "parquet" / "datapackage.json"
    rel_path = jq(
        '.resources[] | select(.name == "stations") | .path',
        pkg,
    )
    assert isinstance(rel_path, str)
    assert rel_path == "stations.parquet", (
        f"Expected relative path 'stations.parquet', got {rel_path!r}"
    )
