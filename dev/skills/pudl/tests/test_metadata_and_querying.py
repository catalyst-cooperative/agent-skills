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

import pint
import pytest

from .conftest import SAMPLE_DESCRIPTOR


def jq(expr: str, path: Path = SAMPLE_DESCRIPTOR) -> Any:
    """Run a jq expression and return the parsed output (list if multi-line)."""
    result = subprocess.run(
        ["jq", "-c", expr, str(path)],
        capture_output=True,
        text=True,
        check=False,
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


def test_first_line_summary_per_resource() -> None:
    """Splitting on '\\n' and taking [0] yields just the docstring summary line."""
    rows = jq(r'.resources[] | "\(.name): \(.description | split("\n")[0])"')
    assert rows, "Expected at least one resource summary"
    for row in rows:
        name, _, summary = row.partition(": ")
        assert summary, f"Resource {name} produced an empty first-line summary"
        assert "\n" not in summary, (
            f"First-line summary for {name} leaked a newline: {summary!r}"
        )


def test_keyword_search_on_first_line_only() -> None:
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


def test_full_description_has_usage_warnings_section() -> None:
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


def test_provenance_for_every_source_dataset() -> None:
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


def test_license_pudl_for_known_resource() -> None:
    """license_pudl is almost always CC-BY-4.0, distinct from the source's original license_raw."""
    license_pudl = jq(
        '.resources[] | select(.name == "_core_eia860__cooling_equipment") | .sources[0].license_pudl'
    )
    assert license_pudl["name"] == "CC-BY-4.0"


# ---------------------------------------------------------------------------
# Package-level unit registry
# ---------------------------------------------------------------------------


def test_unit_registry_definitions() -> None:
    """unit_registry.definitions lists Pint-format definitions for non-SI units."""
    definitions = jq(".unit_registry.definitions[]")
    assert definitions
    assert any(d.startswith("MMBtu =") for d in definitions)


def test_unit_registry_lookup_for_specific_unit() -> None:
    """Looking up a specific unit's definition by prefix match."""
    definition = jq(
        r'.unit_registry.definitions[] | select(startswith("MMBtu" + " ="))'
    )
    assert definition.startswith("MMBtu =")


def test_field_unit_lookup_before_combining_columns() -> None:
    """The two-field unit check from 'Using units safely when combining data'."""
    fuel_unit = jq(
        '.resources[] | select(.name == "out_ferc1__yearly_steam_plants_fuel_by_plant_sched402")'
        ' | .schema.fields[] | select(.name == "fuel_mmbtu") | {name, unit}'
    )
    assert fuel_unit["unit"] == "MMBtu"


def test_default_pint_registry_parses_standard_units_unaided() -> None:
    """Pint's plain UnitRegistry() already understands common PUDL units.

    No unit_registry.definitions needed for units like MW or foot -- confirms
    the "Most unit values need no lookup at all" claim.
    """
    ureg = pint.UnitRegistry()
    for unit_string in ("MW", "foot", "acre", "gallon / minute", "percent"):
        ureg.parse_expression(unit_string)  # raises if Pint can't parse it


def test_default_pint_registry_rejects_pudls_custom_units() -> None:
    """Pint's plain UnitRegistry() cannot parse PUDL's non-standard unit names.

    Confirms these genuinely need unit_registry.definitions loaded first --
    the doc's central claim about which units require the extra step.
    """
    ureg = pint.UnitRegistry()
    for unit_string in ("MMBtu", "Mcf", "MMcf", "VAr", "MVAr", "USD"):
        with pytest.raises(pint.errors.UndefinedUnitError):
            ureg.parse_expression(unit_string)


def test_unit_registry_definition_names_match_custom_units_documented() -> None:
    """Every unit named in unit_registry.definitions is one Pint can't parse by default."""
    definitions = jq(".unit_registry.definitions[]")
    custom_unit_names = [d.split(" ")[0] for d in definitions]
    assert set(custom_unit_names) == {
        "MMBtu",
        "Mcf",
        "MMcf",
        "TBtu",
        "VAr",
        "MVAr",
        "USD",
    }


def test_mmbtu_and_mcf_worked_failure_mode() -> None:
    """The doc's worked failure mode: Pint converts correctly; raw magnitudes don't.

    Loads the real unit_registry definitions (as an agent would) and reproduces
    both the wrong (magnitude-only) and right (unit-aware) totals documented in
    metadata-and-querying.md's "Using units safely when combining data" section.
    """
    descriptor = json.loads(SAMPLE_DESCRIPTOR.read_text(encoding="utf-8"))
    ureg = pint.UnitRegistry()
    for definition in descriptor["unit_registry"]["definitions"]:
        ureg.define(definition)

    # ureg.Quantity(...) is pint's documented constructor, but its stubs leave
    # QuantityT unbound on a bare UnitRegistry(), so pyrefly can't resolve the
    # call itself even though the returned Quantity is used correctly below.
    gas_a = ureg.Quantity(1_200, "Mcf")  # pyrefly: ignore[not-callable]
    gas_b = ureg.Quantity(1.5, "MMcf")  # pyrefly: ignore[not-callable]

    wrong_total = gas_a.magnitude + gas_b.magnitude
    assert wrong_total == 1_201.5

    right_total = gas_a + gas_b.to("Mcf")
    assert right_total.to("Mcf").magnitude == 2_700
    # gas_b's real contribution (1,500 Mcf) is what the wrong total collapsed down
    # to its raw magnitude (1.5) -- a 1,000x understatement of that component.
    gas_b_real_contribution_mcf = right_total.to("Mcf").magnitude - gas_a.magnitude
    gas_b_raw_magnitude = wrong_total - gas_a.magnitude
    assert gas_b_real_contribution_mcf / gas_b_raw_magnitude == 1_000


# ---------------------------------------------------------------------------
# Other field-level extensions
# ---------------------------------------------------------------------------


def test_geometry_format_field_extension() -> None:
    """A geometry_format key appears alongside the standard field keys, not as an error."""
    field = jq(
        '.resources[] | select(.name == "out_ferc714__georeferenced_respondents")'
        " | .schema.fields[] | select(.geometry_format != null)"
    )
    assert field["geometry_format"] == "wkt"
    assert field["name"] == "geometry"
    assert field["type"] == "string"
