#!/usr/bin/env python3
"""Generate example datapackage assets for all four supported storage backends.

Creates two parallel sets of examples — one for each major revision of the
Frictionless Data Package specification — each containing the same
weather-station dataset (5 stations, 30 daily readings) stored as:

  v1/csv/          — tabular-data-package with tabular-data-resource (fully spec-compliant)
  v1/parquet/      — data-package with community Parquet extension pattern
  v1/duckdb/       — data-package with community duckdb_table extension pattern
  v1/duckdb-no-ext/ — data-package WITHOUT duckdb_table; table names use underscores
  v1/sqlite/       — data-package with community sqlite_table extension pattern

  v2/csv/          — $schema v2 descriptor with CSV resources
  v2/parquet/      — $schema v2 descriptor with Parquet resources
  v2/duckdb/       — $schema v2 descriptor with duckdb_table extension
  v2/duckdb-no-ext/ — $schema v2 descriptor WITHOUT duckdb_table; table names use underscores
  v2/sqlite/       — $schema v2 descriptor with sqlite_table extension

The duckdb-no-ext variants are used exclusively by the table-discovery tests to
exercise the fallback process documented in storage-backends.md: when no extension
field is present, an agent must try the resource name directly, then with
hyphens replaced by underscores, and finally list all tables in the database.

The data files are identical across spec versions; only the descriptor structure
and content differ, illustrating the key breaking changes between v1 and v2:

  - Package-level identifier: v1 uses "profile", v2 uses "$schema"
  - Contributors: v1 uses "role" (string), v2 uses "roles" (array)
  - Resource profile: v1 CSV resources declare "profile": "tabular-data-resource"
  - Version field: v1 spec doesn't define "version"; v2 does (we omit it from v1)
  - Non-CSV backends: not defined in either spec; community patterns apply to both

Run from the skill root:

    python scripts/generate_examples.py

Requires: pandas, pyarrow, duckdb (all available in the agent-skills pixi env).
SQLite is in the Python stdlib.
"""

import argparse
import datetime
import hashlib
import json
import random
import sqlite3
import sys
from collections.abc import Sequence
from functools import cache
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
from duckdb import DuckDBPyConnection
from pydantic import BaseModel, Field, field_serializer


class Station(BaseModel):
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    elevation_m: int
    active: bool
    commissioned_date: datetime.date


class ClimateParams(BaseModel):
    min: float
    max: float
    precip_chance: float


class Reading(BaseModel):
    station_id: str
    date: datetime.date
    temp_min_c: float
    temp_max_c: float
    precipitation_mm: float | None
    wind_speed_avg_ms: float


class FileStats(BaseModel):
    bytes: int
    hash: str  # raw hex digest
    hash_algorithm: str = Field(
        default="md5", exclude=True
    )  # excluded from model_dump() output

    @field_serializer("hash")
    def serialize_hash(self, value: str) -> str:
        return f"{self.hash_algorithm}:{value}"


# ---------------------------------------------------------------------------
# Sample data (identical for both spec versions)
# ---------------------------------------------------------------------------

# ASSETS is not yet defined at module level here; resolve the path directly.
_EXAMPLES_DIR = Path(__file__).parent.parent / "assets" / "examples"
STATIONS: list[Station] = [
    Station.model_validate(s)
    for s in json.loads((_EXAMPLES_DIR / "stations_data.json").read_text())
]

# Base temps (°C) and precipitation frequency per station (Jan 2024 approximations)
_STATION_CLIMATE: dict[str, ClimateParams] = {
    "WS-0001": ClimateParams(min=1.0, max=9.0, precip_chance=0.65),
    "WS-0002": ClimateParams(min=-6.0, max=0.0, precip_chance=0.70),
    "WS-0003": ClimateParams(min=-10.0, max=-2.0, precip_chance=0.50),
    "WS-0004": ClimateParams(min=2.0, max=8.0, precip_chance=0.75),
    "WS-0005": ClimateParams(min=-4.0, max=5.0, precip_chance=0.25),
}

SAMPLE_START_DATE = "2024-01-01"
SAMPLE_PERIODS = 30


def generate_readings(
    stations: list[Station],
    climate_by_station: dict[str, ClimateParams],
    dates: list[datetime.date],
    seed: int = 42,
) -> list[Reading]:
    """Generate deterministic daily readings for the example stations."""
    rng = random.Random(seed)
    readings: list[Reading] = []

    for station in stations:
        climate: ClimateParams = climate_by_station[station.station_id]
        for date in dates:
            temp_min = round(climate.min + rng.gauss(0, 1.5), 1)
            temp_max = round(climate.max + rng.gauss(0, 1.5), 1)
            if temp_max < temp_min:
                temp_min, temp_max = temp_max, temp_min

            if rng.random() < climate.precip_chance:
                precipitation_mm: float | None = round(rng.uniform(0.5, 25.0), 1)
            else:
                precipitation_mm = None  # station did not report

            readings.append(
                Reading(
                    station_id=station.station_id,
                    date=date,
                    temp_min_c=temp_min,
                    temp_max_c=temp_max,
                    precipitation_mm=precipitation_mm,
                    wind_speed_avg_ms=round(rng.uniform(0.5, 8.0), 1),
                )
            )

    return readings


@cache
def build_sample_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the example station and reading tables on first use."""
    dates: list[datetime.date] = [
        d.date() for d in pd.date_range(SAMPLE_START_DATE, periods=SAMPLE_PERIODS)
    ]
    readings: list[Reading] = generate_readings(STATIONS, _STATION_CLIMATE, dates)
    return (
        pd.DataFrame([s.model_dump() for s in STATIONS]),
        pd.DataFrame([r.model_dump() for r in readings]),
    )


ASSETS: Path = Path(__file__).parent.parent / "assets" / "examples"

# ---------------------------------------------------------------------------
# Resource base definitions — loaded from JSON assets to avoid duplication
# ---------------------------------------------------------------------------

STATIONS_RESOURCE_BASE: dict[str, Any] = json.loads(
    (ASSETS / "stations_resource.json").read_text()
)
READINGS_RESOURCE_BASE: dict[str, Any] = json.loads(
    (ASSETS / "readings_resource.json").read_text()
)

# Fields shared between v1 and v2 package metadata.
_PACKAGE_META_COMMON: dict[str, Any] = json.loads(
    (ASSETS / "package_meta_common.json").read_text()
)


# ---------------------------------------------------------------------------
# Spec-version-specific package metadata
# ---------------------------------------------------------------------------
# Both bases are merged with _PACKAGE_META_COMMON (name, title, licenses,
# sources). Only the fields that actually differ between versions appear here.
#
# Key differences:
#   1. Spec version declaration: v1 uses "profile"; v2 uses "$schema"
#   2. Contributors: v1 uses "role" (string); v2 uses "roles" (array)
#   3. "version" and "created": defined by v2 spec, omitted from v1
#
# Note: for v1, "profile" is NOT included here because its value depends on
# the backend (CSV uses "tabular-data-package"; others use "data-package").
# It is prepended by the caller in __main__.

V1_PACKAGE_META_BASE: dict[str, Any] = {
    **_PACKAGE_META_COMMON,
    "description": (
        "A demonstration datapackage containing two related tables: station metadata"
        " and daily temperature readings. Illustrates Frictionless Data Package v1"
        " structure including field types, constraints, foreign keys, and common"
        " non-standard extensions (unit, warning)."
    ),
    "contributors": [
        # v1: "role" is a singular string (default: "contributor")
        {"title": "Example Organization", "email": "data@example.org", "role": "author"}
    ],
}

V2_PACKAGE_META_BASE: dict[str, Any] = {
    # "$schema" is the v2 way to declare the spec version.
    "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
    **_PACKAGE_META_COMMON,
    "description": (
        "A demonstration datapackage containing two related tables: station metadata"
        " and daily temperature readings. Illustrates Frictionless Data Package v2"
        " structure including field types, constraints, foreign keys, and common"
        " non-standard extensions (unit, warning)."
    ),
    "version": "1.0.0",  # v2 defines a "version" field
    "created": "2025-01-01T00:00:00Z",  # v2 recommends ISO 8601 datetime
    "contributors": [
        # v2: "roles" is an array (breaking change from v1's singular "role")
        {
            "title": "Example Organization",
            "email": "data@example.org",
            "roles": ["author"],
        }
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def file_stats(path: Path) -> FileStats:
    """Return bytes and MD5 hash for a file — useful for integrity checking."""
    data = path.read_bytes()
    return FileStats(bytes=len(data), hash=hashlib.md5(data).hexdigest())


def write_descriptor(
    directory: Path, package_meta: dict[str, Any], resources: list[dict[str, Any]]
) -> None:
    descriptor = {**package_meta, "resources": resources}
    (directory / "datapackage.json").write_text(json.dumps(descriptor, indent=4) + "\n")


def write_data_files(out: Path) -> None:
    """Write the data files to the output directory (CSV, Parquet, DuckDB, SQLite).

    This is separated so that data files are shared / written once regardless of
    how many descriptor variants we generate against them.
    """
    out.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Backend generators
#
# Each function writes one backend variant for a single spec version.
# All spec-version differences are captured in the package_meta argument
# supplied by the caller — these functions know nothing about v1 vs v2.
#
# CSV has one additional v1-specific wrinkle: resources must declare
# profile="tabular-data-resource". Pass v1_resource_profiles=True for that.
# ---------------------------------------------------------------------------


def generate_csv(
    out: Path,
    package_meta: dict[str, Any],
    *,
    v1_resource_profiles: bool = False,
) -> None:
    stations_df, readings_df = build_sample_dataframes()
    out.mkdir(parents=True, exist_ok=True)
    stations_df.to_csv(out / "stations.csv", index=False)
    readings_df.to_csv(out / "daily-readings.csv", index=False)

    # "tabular-data-resource" is the v1 profile for a CSV resource with a schema.
    resource_profile = (
        {"profile": "tabular-data-resource"} if v1_resource_profiles else {}
    )
    write_descriptor(
        out,
        package_meta,
        [
            {
                **resource_profile,
                **STATIONS_RESOURCE_BASE,
                "path": "stations.csv",
                "format": "csv",
                "mediatype": "text/csv",
                **file_stats(out / "stations.csv").model_dump(),
            },
            {
                **resource_profile,
                **READINGS_RESOURCE_BASE,
                "path": "daily-readings.csv",
                "format": "csv",
                "mediatype": "text/csv",
                **file_stats(out / "daily-readings.csv").model_dump(),
            },
        ],
    )
    print(f"CSV example written to {out}")


def generate_parquet(out: Path, package_meta: dict[str, Any]) -> None:
    # Community pattern for Parquet resources:
    # - Declare mediatype "application/parquet" and format "parquet"
    # - Keep the "schema" field for documentation; it is valid as a custom
    #   extension in both v1 and v2 even though v1 strictly defines schema
    #   for CSV only.
    stations_df, readings_df = build_sample_dataframes()
    out.mkdir(parents=True, exist_ok=True)
    stations_df.to_parquet(out / "stations.parquet", index=False)
    readings_df.to_parquet(out / "daily-readings.parquet", index=False)
    write_descriptor(
        out,
        package_meta,
        [
            {
                **STATIONS_RESOURCE_BASE,
                "path": "stations.parquet",
                "format": "parquet",
                "mediatype": "application/parquet",
                **file_stats(out / "stations.parquet").model_dump(),
            },
            {
                **READINGS_RESOURCE_BASE,
                "path": "daily-readings.parquet",
                "format": "parquet",
                "mediatype": "application/parquet",
                **file_stats(out / "daily-readings.parquet").model_dump(),
            },
        ],
    )
    print(f"Parquet example written to {out}")


def generate_duckdb(out: Path, package_meta: dict[str, Any]) -> None:
    # Community pattern for DuckDB resources:
    # - Both resources share the same "path" (the .duckdb file)
    # - The non-standard "duckdb_table" key identifies which table inside the DB
    # - bytes/hash appear only on the first resource (shared-file convention)
    stations_df, readings_df = build_sample_dataframes()
    out.mkdir(parents=True, exist_ok=True)
    db_path = out / "weather.duckdb"
    db_path.unlink(missing_ok=True)
    con: DuckDBPyConnection = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE stations AS SELECT * FROM stations_df")
    con.execute('CREATE TABLE "daily-readings" AS SELECT * FROM readings_df')
    con.close()
    db_stats = file_stats(db_path).model_dump()
    write_descriptor(
        out,
        package_meta,
        [
            {
                **STATIONS_RESOURCE_BASE,
                "path": "weather.duckdb",
                "format": "duckdb",
                "mediatype": "application/octet-stream",
                "duckdb_table": "stations",
                **db_stats,
            },
            {
                **READINGS_RESOURCE_BASE,
                "path": "weather.duckdb",
                "format": "duckdb",
                "mediatype": "application/octet-stream",
                "duckdb_table": "daily-readings",
            },
        ],
    )
    print(f"DuckDB example written to {out}")


def generate_duckdb_no_ext(out: Path, package_meta: dict[str, Any]) -> None:
    """DuckDB variant without duckdb_table extension fields.

    Table names inside the database use underscores (SQL-safe identifiers):
      - resource "stations"      → table "stations"       (direct name match)
      - resource "daily-readings" → table "daily_readings" (hyphen→underscore)

    No duckdb_table field appears in the descriptor, so an agent must infer the
    correct table name using the fallback process documented in storage-backends.md:
    try the resource name directly, then replace hyphens with underscores, then
    list all tables and match by inspection.

    These packages are used exclusively by test_table_discovery.py.
    """
    stations_df, readings_df = build_sample_dataframes()
    out.mkdir(parents=True, exist_ok=True)
    db_path = out / "weather.duckdb"
    db_path.unlink(missing_ok=True)
    con: DuckDBPyConnection = duckdb.connect(str(db_path))
    con.execute("CREATE TABLE stations AS SELECT * FROM stations_df")
    con.execute("CREATE TABLE daily_readings AS SELECT * FROM readings_df")
    con.close()
    db_stats = file_stats(db_path).model_dump()
    write_descriptor(
        out,
        package_meta,
        [
            {
                **STATIONS_RESOURCE_BASE,
                "path": "weather.duckdb",
                "format": "duckdb",
                "mediatype": "application/octet-stream",
                **db_stats,
            },
            {
                **READINGS_RESOURCE_BASE,
                "path": "weather.duckdb",
                "format": "duckdb",
                "mediatype": "application/octet-stream",
            },
        ],
    )
    print(f"DuckDB (no-ext) example written to {out}")


def generate_sqlite(out: Path, package_meta: dict[str, Any]) -> None:
    stations_df, readings_df = build_sample_dataframes()
    out.mkdir(parents=True, exist_ok=True)
    db_path: Path = out / "weather.sqlite"
    db_path.unlink(missing_ok=True)
    con: sqlite3.Connection = sqlite3.connect(str(db_path))
    stations_df.to_sql("stations", con, index=False, if_exists="replace")
    readings_df.to_sql("daily-readings", con, index=False, if_exists="replace")
    con.close()
    db_stats = file_stats(db_path).model_dump()
    write_descriptor(
        out,
        package_meta,
        [
            {
                **STATIONS_RESOURCE_BASE,
                "path": "weather.sqlite",
                "format": "sqlite",
                "mediatype": "application/vnd.sqlite3",
                "sqlite_table": "stations",
                **db_stats,
            },
            {
                **READINGS_RESOURCE_BASE,
                "path": "weather.sqlite",
                "format": "sqlite",
                "mediatype": "application/vnd.sqlite3",
                "sqlite_table": "daily-readings",
            },
        ],
    )
    print(f"SQLite example written to {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate_all_examples(output_root: Path) -> None:
    """Generate all example packages under the provided output root."""
    # v1 CSV uses "tabular-data-package" at the package level and
    # "tabular-data-resource" on each resource — the most spec-compliant v1 form.
    # All other v1 backends use "data-package" (non-CSV resources are not
    # tabular-data-resources by spec).
    v1_csv_meta = {"profile": "tabular-data-package", **V1_PACKAGE_META_BASE}
    v1_other_meta = {"profile": "data-package", **V1_PACKAGE_META_BASE}

    print("Generating v1 examples...")
    generate_csv(output_root / "v1" / "csv", v1_csv_meta, v1_resource_profiles=True)
    generate_parquet(output_root / "v1" / "parquet", v1_other_meta)
    generate_duckdb(output_root / "v1" / "duckdb", v1_other_meta)
    generate_duckdb_no_ext(output_root / "v1" / "duckdb-no-ext", v1_other_meta)
    generate_sqlite(output_root / "v1" / "sqlite", v1_other_meta)

    print("\nGenerating v2 examples...")
    generate_csv(output_root / "v2" / "csv", V2_PACKAGE_META_BASE)
    generate_parquet(output_root / "v2" / "parquet", V2_PACKAGE_META_BASE)
    generate_duckdb(output_root / "v2" / "duckdb", V2_PACKAGE_META_BASE)
    generate_duckdb_no_ext(output_root / "v2" / "duckdb-no-ext", V2_PACKAGE_META_BASE)
    generate_sqlite(output_root / "v2" / "sqlite", V2_PACKAGE_META_BASE)

    print("\nDone.")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments for example generation."""
    parser = argparse.ArgumentParser(
        description="Generate datapackage example assets for all supported backends."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ASSETS,
        help="Directory that will receive the generated v1/ and v2/ example trees.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the example generator CLI."""
    args = parse_args(argv)
    generate_all_examples(args.output_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
