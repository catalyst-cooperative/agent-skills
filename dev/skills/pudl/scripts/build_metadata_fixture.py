#!/usr/bin/env python3
"""Build a small, offline PUDL descriptor fixture for the dev test suite.

The jq examples in ``metadata-and-querying.md`` and ``data-sources.md`` run against
a live ``pudl_parquet_datapackage.json`` descriptor, which is ~4.4 MB and refreshed
nightly — too large and too volatile to check into the repo whole. This script
extracts a handful of real resources and sources from a locally cached copy of
that descriptor and writes them out verbatim (field values are not invented or
edited, only the *set* of resources/sources/fields is narrowed) so the tests can
exercise the same query patterns without a network call.

Usage:
    python skills/pudl/scripts/fetch_descriptor.py pudl_parquet_datapackage.json
    python dev/skills/pudl/scripts/build_metadata_fixture.py

Rerun both commands whenever the fixture needs to reflect a newer PUDL schema
(e.g. a field, description, or the unit registry changed upstream).
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
CACHE = (
    REPO_ROOT / "skills" / "pudl" / "assets" / "cache" / "pudl_parquet_datapackage.json"
)
OUT = Path(__file__).parent.parent / "assets" / "pudl_parquet_datapackage_sample.json"

# Top-level sources kept, chosen to cover the lookups documented in data-sources.md:
# keyword/title search ("balancing authority" -> eia930, "CEMS" -> epacems), a known
# short code -> docs URL (ferc1), and sources with no documentation page (mshamines).
SOURCE_NAMES = [
    "eia860",
    "eia923",
    "eia930",
    "epacems",
    "ferc1",
    "ferc714",
    "mshamines",
    "pudl",
]

# Resources kept, and the schema fields to narrow each down to. `None` means keep
# all fields (the resource is already small). Each subset still includes whatever
# fields the documented jq examples or primaryKey reference.
RESOURCE_FIELDS: dict[str, list[str] | None] = {
    # Docstring-convention + Usage Warnings + RST-role example (metadata-and-querying.md).
    "core_eia860__scd_generators": [
        "plant_id_eia",
        "generator_id",
        "report_date",
        "operational_status_code",
        "capacity_mw",
    ],
    # Preliminary-tier resource with a per-resource `sources[0].license_pudl` lookup.
    "_core_eia860__cooling_equipment": [
        "plant_id_eia",
        "utility_id_eia",
        "cooling_id_eia",
        "report_date",
        "cooling_type_1",
        "cooling_water_source",
        "pond_surface_area_acres",
        "power_requirement_mw",
    ],
    # unit_id_pudl usage-warning example + data-access.md loading example columns.
    "out_eia923__generation": None,
    # unit_registry / MMBtu cross-reference example.
    "out_ferc1__yearly_steam_plants_fuel_by_plant_sched402": [
        "report_year",
        "utility_id_ferc1",
        "plant_name_ferc1",
        "fuel_mmbtu",
        "fuel_cost",
    ],
    # geometry_format field-level extension example.
    "out_ferc714__georeferenced_respondents": None,
}


# Keywords the data-sources.md examples search for; kept verbatim wherever a
# source has them, on top of the first few keywords, so a blind slice can't
# silently drop the one keyword a documented query relies on.
_KEYWORDS_TO_KEEP = {"emissions", "cems"}


def trim_source(source: dict) -> dict:
    """Keep a source record's real values but cap its keyword list."""
    trimmed = dict(source)
    if "keywords" in trimmed:
        head = trimmed["keywords"][:5]
        extra = [
            k for k in trimmed["keywords"] if k in _KEYWORDS_TO_KEEP and k not in head
        ]
        trimmed["keywords"] = head + extra
    return trimmed


def trim_resource(resource: dict, fields: list[str] | None) -> dict:
    """Keep a resource's real values but narrow schema fields and drop bulk keys."""
    trimmed = dict(resource)
    trimmed.pop("bytes", None)
    trimmed.pop("hash", None)
    if "keywords" in trimmed:
        trimmed["keywords"] = trimmed["keywords"][:5]
    if "sources" in trimmed:
        trimmed["sources"] = [trim_source(s) for s in trimmed["sources"]]
    schema = dict(trimmed["schema"])
    schema.pop("foreignKeys", None)
    if fields is not None:
        by_name = {f["name"]: f for f in schema["fields"]}
        schema["fields"] = [by_name[name] for name in fields if name in by_name]
    trimmed["schema"] = schema
    return trimmed


def main() -> None:
    if not CACHE.exists():
        raise SystemExit(
            f"Missing {CACHE}. Fetch it first:\n"
            "  python skills/pudl/scripts/fetch_descriptor.py pudl_parquet_datapackage.json"
        )
    descriptor = json.loads(CACHE.read_text(encoding="utf-8"))

    resources_by_name = {r["name"]: r for r in descriptor["resources"]}
    sources_by_name = {s["name"]: s for s in descriptor["sources"]}

    sample = {
        key: descriptor[key]
        for key in (
            "name",
            "title",
            "description",
            "homepage",
            "licenses",
            "version",
            "$schema",
            "unit_registry",
        )
    }
    sample["sources"] = [trim_source(sources_by_name[name]) for name in SOURCE_NAMES]
    sample["resources"] = [
        trim_resource(resources_by_name[name], fields)
        for name, fields in RESOURCE_FIELDS.items()
    ]

    OUT.write_text(
        json.dumps(sample, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
