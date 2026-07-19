"""Tests for the jq examples in references/metadata-and-querying.md.

Runs each documented query against the small offline descriptor fixture (see
../scripts/build_metadata_fixture.py) rather than the live nightly descriptor,
so these tests stay fast, deterministic, and network-free.

Run:  pixi run pytest dev/skills/pudl/tests/test_metadata_and_querying.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from .conftest import SAMPLE_DESCRIPTOR


def jq(expr: str, path: Path = SAMPLE_DESCRIPTOR) -> Any:
    """Run a jq expression and return the parsed output (list if multi-line)."""
    result = subprocess.run(
        ["jq", "-c", expr, str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"jq exited {result.returncode}\nexpression: {expr!r}\nstderr: {result.stderr}"
    )
    lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    if len(lines) == 1:
        return json.loads(lines[0])
    return [json.loads(ln) for ln in lines]


# ---------------------------------------------------------------------------
# Descriptions: RST, docstrings, and structured sections
# ---------------------------------------------------------------------------


def test_first_line_summary_per_resource():
    """Splitting on '\\n' and taking [0] yields just the docstring summary line."""
    rows = jq(r'.resources[] | "\(.name): \(.description | split("\n")[0])"')
    assert rows, "Expected at least one resource summary"
    for row in rows:
        name, _, summary = row.partition(": ")
        assert summary, f"Resource {name} produced an empty first-line summary"
        assert "\n" not in summary, (
            f"First-line summary for {name} leaked a newline: {summary!r}"
        )


def test_keyword_search_on_first_line_only():
    """Searching only the first line finds a resource whose summary mentions 'generator'."""
    rows = jq(
        r'.resources[] | select(.description | split("\n")[0] | test("generator"; "i"))'
        r' | "\(.name): \(.description | split("\n")[0])"'
    )
    if not isinstance(rows, list):
        rows = [rows]
    assert any("core_eia860__scd_generators" in row for row in rows), (
        "Expected core_eia860__scd_generators to match a first-line search for 'generator'"
    )


def test_full_description_has_usage_warnings_section():
    """Once a table looks relevant, the full description exposes RST sections."""
    description = jq(
        '.resources[] | select(.name == "core_eia860__scd_generators") | .description'
    )
    assert "Usage Warnings" in description
    assert "^^^^^^^^^^^^^^" in description, (
        "Expected the RST underline for the section header"
    )


# ---------------------------------------------------------------------------
# Per-resource provenance: sources
# ---------------------------------------------------------------------------


def test_provenance_for_every_source_dataset():
    """Every resource's sources[] carries a name + documentation link."""
    rows = jq(r'.resources[0].sources[] | "\(.name): \(.documentation)"')
    if not isinstance(rows, list):
        rows = [rows]
    assert rows
    for row in rows:
        name, _, doc = row.partition(": ")
        assert name
        assert doc.startswith("http") or doc == "null", (
            f"Unexpected documentation value: {doc!r}"
        )


def test_license_pudl_for_known_resource():
    """license_pudl is almost always CC-BY-4.0, distinct from the source's original license_raw."""
    license_pudl = jq(
        '.resources[] | select(.name == "_core_eia860__cooling_equipment") | .sources[0].license_pudl'
    )
    assert license_pudl["name"] == "CC-BY-4.0"


# ---------------------------------------------------------------------------
# Package-level unit registry
# ---------------------------------------------------------------------------


def test_unit_registry_definitions():
    """unit_registry.definitions lists Pint-format definitions for non-SI units."""
    definitions = jq(".unit_registry.definitions[]")
    assert definitions
    assert any(d.startswith("MMBtu =") for d in definitions)


def test_unit_registry_lookup_for_specific_unit():
    """Looking up a specific unit's definition by prefix match."""
    definition = jq(
        r'.unit_registry.definitions[] | select(startswith("MMBtu" + " ="))'
    )
    assert definition.startswith("MMBtu =")


# ---------------------------------------------------------------------------
# Other field-level extensions
# ---------------------------------------------------------------------------


def test_geometry_format_field_extension():
    """A geometry_format key appears alongside the standard field keys, not as an error."""
    field = jq(
        '.resources[] | select(.name == "out_ferc714__georeferenced_respondents")'
        " | .schema.fields[] | select(.geometry_format != null)"
    )
    assert field["geometry_format"] == "wkt"
    assert field["name"] == "geometry"
    assert field["type"] == "string"
