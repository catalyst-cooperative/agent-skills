"""Tests for jq query patterns documented in references/metadata-querying.md.

Exercises each jq command from that reference against our example packages,
verifying that the queries return the expected values.  A failing test names
the jq expression that broke so an agent can look it up in the reference.

Run:  pixi run pytest dev/skills/datapackage/tests/test_metadata_jq.py -v
"""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    EXAMPLES,
    READING_COLUMNS,
    RESOURCE_NAMES,
    STATION_COLUMNS,
)

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def jq(expr: str, path: Path) -> Any:
    """Run a jq expression and return the parsed output.

    Multiple output lines (e.g. from .[] iterations) are returned as a list.
    Single values are returned directly.
    """
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


# Use the v2 CSV package as the canonical test subject for most queries.
# v1-vs-v2 structural differences are tested explicitly below.
PKG = EXAMPLES / "v2" / "csv" / "datapackage.json"


# ---------------------------------------------------------------------------
# Step 2: Identify candidate resources
# Reference: "Step 2: Identify candidate resources" section
# ---------------------------------------------------------------------------


def test_resource_count():
    """.resources | length → 2."""
    assert jq(".resources | length", PKG) == 2, (
        "Expected 2 resources (stations, daily-readings). "
        "See Step 2 in metadata-querying.md."
    )


def test_resource_names_in_order():
    """[.resources[].name] → [\"stations\", \"daily-readings\"]."""
    names = jq("[.resources[].name]", PKG)
    assert names == RESOURCE_NAMES, (
        f"Expected resource names {RESOURCE_NAMES}, got {names}"
    )


def test_resource_names_and_formats():
    """Each resource reports its format via \\(.format // \"unknown\")."""
    rows = jq('[.resources[] | {name: .name, fmt: (.format // "unknown")}]', PKG)
    by_name = {r["name"]: r["fmt"] for r in rows}
    assert by_name == {"stations": "csv", "daily-readings": "csv"}, (
        f"Unexpected formats: {by_name}"
    )


def test_keyword_search_in_description():
    """select(.description | test(...)) finds resources by keyword."""
    result = jq(
        '[.resources[] | select(.description | test("calibration"; "i")) | .name]',
        PKG,
    )
    assert "daily-readings" in result, (
        "Keyword search for 'calibration' should match daily-readings description"
    )


# ---------------------------------------------------------------------------
# Step 3: Read resource and field descriptions
# Reference: "Step 3: Read resource and field descriptions" section
# ---------------------------------------------------------------------------


def test_resource_description_nonempty():
    """stations resource has a non-empty description."""
    desc = jq('.resources[] | select(.name == "stations") | .description', PKG)
    assert isinstance(desc, str) and len(desc) > 20, (
        f"Expected a non-empty description, got: {desc!r}"
    )


def test_station_field_names():
    """stations schema has exactly the expected column names, in order."""
    names = jq(
        '[.resources[] | select(.name == "stations") | .schema.fields[].name]',
        PKG,
    )
    assert names == STATION_COLUMNS, (
        f"stations field names mismatch.\nExpected: {STATION_COLUMNS}\nGot: {names}"
    )


def test_reading_field_names():
    """daily-readings schema has exactly the expected column names, in order."""
    names = jq(
        '[.resources[] | select(.name == "daily-readings") | .schema.fields[].name]',
        PKG,
    )
    assert names == READING_COLUMNS, (
        f"daily-readings field names mismatch.\nExpected: {READING_COLUMNS}\nGot: {names}"
    )


def test_fields_with_unit():
    """select(.unit != null) returns the four measurement columns."""
    fields = jq(
        '[.resources[] | select(.name == "daily-readings")'
        " | .schema.fields[] | select(.unit != null) | .name]",
        PKG,
    )
    expected = {"temp_min_c", "temp_max_c", "precipitation_mm", "wind_speed_avg_ms"}
    assert set(fields) == expected, (
        f"Fields with unit: expected {expected}, got {set(fields)}"
    )


def test_field_with_warning():
    """select(.warning != null) returns only precipitation_mm."""
    fields = jq(
        '[.resources[] | select(.name == "daily-readings")'
        " | .schema.fields[] | select(.warning != null) | .name]",
        PKG,
    )
    assert fields == ["precipitation_mm"], (
        f"Expected only precipitation_mm to carry a warning, got: {fields}"
    )


def test_all_keys_on_resource():
    """keys reveals non-spec extension fields on a resource."""
    keys = jq(
        '.resources[] | select(.name == "stations") | keys',
        PKG,
    )
    # Standard spec fields
    for key in ("name", "title", "description", "schema", "path", "format"):
        assert key in keys, f"Missing expected key '{key}' on stations resource"
    # Integrity extension fields added by generate_examples.py
    for key in ("bytes", "hash"):
        assert key in keys, (
            f"Missing integrity field '{key}' on stations resource. "
            "See integrity section of metadata-querying.md."
        )


# ---------------------------------------------------------------------------
# Integrity fields
# Reference: "Integrity fields" section
# ---------------------------------------------------------------------------


def test_integrity_fields_format():
    """hash is in 'algorithm:hex' format; bytes is a positive integer."""
    resource = jq(".resources[0]", PKG)
    assert isinstance(resource["bytes"], int) and resource["bytes"] > 0, (
        f"Expected bytes > 0, got: {resource['bytes']!r}"
    )
    assert ":" in resource["hash"], (
        f"Expected hash in 'algorithm:hex' format (e.g. 'md5:abc...'), "
        f"got: {resource['hash']!r}. See metadata-querying.md."
    )
    algorithm, hex_digest = resource["hash"].split(":", 1)
    assert algorithm == "md5"
    assert len(hex_digest) == 32, (
        f"MD5 hex digest should be 32 chars, got {len(hex_digest)}"
    )


@pytest.mark.parametrize(
    "version,backend",
    [
        ("v1", "csv"),
        ("v2", "csv"),
        ("v1", "parquet"),
        ("v2", "parquet"),
    ],
)
def test_integrity_values_match_actual_files(version, backend):
    """bytes and hash in the descriptor match the actual data files on disk."""
    pkg_dir = EXAMPLES / version / backend
    pkg = pkg_dir / "datapackage.json"
    resources = jq("[.resources[] | select(.bytes != null)]", pkg)
    assert resources, f"No resources with integrity fields found in {version}/{backend}"

    for resource in resources:
        data_file = pkg_dir / resource["path"]
        data = data_file.read_bytes()

        assert resource["bytes"] == len(data), (
            f"{version}/{backend}/{resource['path']}: "
            f"descriptor says {resource['bytes']} bytes, actual file is {len(data)} bytes"
        )

        algorithm, expected_hex = resource["hash"].split(":", 1)
        actual_hex = hashlib.new(algorithm, data).hexdigest()
        assert actual_hex == expected_hex, (
            f"{version}/{backend}/{resource['path']}: "
            f"descriptor hash {expected_hex!r} doesn't match computed {actual_hex!r}"
        )


# ---------------------------------------------------------------------------
# Package-level metadata
# Reference: "Package-level metadata" section and spec version examples
# ---------------------------------------------------------------------------


def test_package_top_level_keys():
    """del(.resources) returns expected package-level fields."""
    meta = jq("del(.resources)", PKG)
    for key in ("name", "title", "licenses", "sources", "$schema"):
        assert key in meta, (
            f"Missing package-level key {key!r} in v2 descriptor. "
            "See metadata-querying.md."
        )


def test_v1_uses_profile_not_schema():
    """v1 descriptor has 'profile', not '$schema' (spec version difference)."""
    v1_pkg = EXAMPLES / "v1" / "csv" / "datapackage.json"
    meta = jq("del(.resources)", v1_pkg)
    assert "profile" in meta, "v1 descriptor missing 'profile' field"
    assert "$schema" not in meta, "v1 descriptor should not have '$schema'"


def test_v2_uses_schema_not_profile():
    """v2 descriptor has '$schema', not 'profile' (spec version difference)."""
    meta = jq("del(.resources)", PKG)
    assert "$schema" in meta, "v2 descriptor missing '$schema' field"
    assert "profile" not in meta, "v2 descriptor should not have 'profile'"


def test_v1_contributors_use_role_string():
    """v1 contributors use 'role' (string), not 'roles' (array)."""
    v1_pkg = EXAMPLES / "v1" / "csv" / "datapackage.json"
    contributors = jq(".contributors", v1_pkg)
    for c in contributors:
        assert "role" in c, f"v1 contributor missing 'role': {c}"
        assert "roles" not in c, f"v1 contributor should not have 'roles': {c}"


def test_v2_contributors_use_roles_array():
    """v2 contributors use 'roles' (array), not 'role' (string)."""
    contributors = jq(".contributors", PKG)
    for c in contributors:
        assert "roles" in c, f"v2 contributor missing 'roles': {c}"
        assert isinstance(c["roles"], list), f"v2 'roles' should be a list: {c}"
        assert "role" not in c, f"v2 contributor should not have singular 'role': {c}"


# ---------------------------------------------------------------------------
# Foreign keys
# Reference: schema section of readings_resource.json
# ---------------------------------------------------------------------------


def test_foreign_key_references_stations():
    """daily-readings has a foreign key referencing stations.station_id."""
    fks = jq(
        '.resources[] | select(.name == "daily-readings") | .schema.foreignKeys',
        PKG,
    )
    assert len(fks) == 1, f"Expected 1 foreign key, got {len(fks)}"
    fk = fks[0]
    assert fk["fields"] == ["station_id"]
    assert fk["reference"]["resource"] == "stations"
    assert fk["reference"]["fields"] == ["station_id"]


# ---------------------------------------------------------------------------
# Steps 4–5: Confirm the path
# ---------------------------------------------------------------------------


def test_resource_paths_resolve_to_existing_files():
    """Every resource path in each descriptor resolves to an existing file."""
    for version in ("v1", "v2"):
        for backend in ("csv", "parquet", "sqlite", "duckdb"):
            pkg_dir = EXAMPLES / version / backend
            pkg = pkg_dir / "datapackage.json"
            paths = jq("[.resources[].path]", pkg)
            seen = set()
            for rel_path in paths:
                if rel_path in seen:
                    continue  # DB backends share a single file across resources
                seen.add(rel_path)
                full_path = pkg_dir / rel_path
                assert full_path.exists(), (
                    f"{version}/{backend}: path '{rel_path}' in descriptor "
                    f"does not exist at {full_path}"
                )
