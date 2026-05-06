"""Tests for backend-loading workflows documented in references/storage-backends.md.

These tests stay focused on the documented loading patterns themselves. Fresh
generation and descriptor validation of the example assets are covered
separately in test_generate_examples.py.

Run:  pixi run pytest dev/skills/datapackage/tests/test_backends.py -v
"""

import json
import sqlite3

import duckdb
import pandas as pd
import polars as pl
import pytest
from conftest import (
    EXAMPLES,
    READING_COLUMNS,
    READING_COUNT,
    STATION_COLUMNS,
    STATION_COUNT,
)

# ---------------------------------------------------------------------------
# Helper: load a descriptor
# ---------------------------------------------------------------------------


def load_descriptor(version: str, backend: str) -> dict:
    path = EXAMPLES / version / backend / "datapackage.json"
    return json.loads(path.read_text())


def resource_by_name(descriptor: dict, name: str) -> dict:
    return next(r for r in descriptor["resources"] if r["name"] == name)


# ---------------------------------------------------------------------------
# DuckDB — .df() shorthand for pandas output
# Reference: "Getting a pandas DataFrame from DuckDB" section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_duckdb_sql_df_stations(version):
    """duckdb.sql(...).df() returns a pandas DataFrame for a Parquet file."""
    path = str(EXAMPLES / version / "parquet" / "stations.parquet")
    df = duckdb.sql(f"SELECT * FROM read_parquet('{path}') LIMIT 100").df()
    assert isinstance(df, pd.DataFrame), (
        f"{version}/parquet/stations: expected pandas DataFrame from .df(), "
        f"got {type(df)}"
    )
    assert df.shape == (STATION_COUNT, len(STATION_COLUMNS)), (
        f"{version}/parquet/stations: expected shape ({STATION_COUNT}, {len(STATION_COLUMNS)}), "
        f"got {df.shape}"
    )
    assert list(df.columns) == STATION_COLUMNS


# ---------------------------------------------------------------------------
# DuckDB — read_csv
# Reference: "DuckDB" section, "SELECT * FROM read_csv(...)"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_duckdb_read_csv_stations(version):
    """read_csv loads 5 station rows with the expected column names."""
    path = str(EXAMPLES / version / "csv" / "stations.csv")
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_csv('{path}')").df()
    assert df.shape == (STATION_COUNT, len(STATION_COLUMNS)), (
        f"{version}/csv/stations: expected shape ({STATION_COUNT}, {len(STATION_COLUMNS)}), "
        f"got {df.shape}"
    )
    assert list(df.columns) == STATION_COLUMNS


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_duckdb_read_csv_readings(version):
    """read_csv loads 150 reading rows."""
    path = str(EXAMPLES / version / "csv" / "daily-readings.csv")
    con = duckdb.connect()
    count = con.execute(f"SELECT count(*) FROM read_csv('{path}')").fetchall()[0][0]
    assert count == READING_COUNT, (
        f"{version}/csv/daily-readings: expected {READING_COUNT} rows, got {count}"
    )


# ---------------------------------------------------------------------------
# DuckDB ATTACH — SQLite backend
# Reference: "SQLite" section — "Via DuckDB (preferred)"
#
# The resource's sqlite_table extension field identifies which table inside the
# .sqlite file corresponds to this resource.  Using it is the correct approach
# per storage-backends.md.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,resource_name,expected_count",
    [
        ("v1", "stations", STATION_COUNT),
        ("v1", "daily-readings", READING_COUNT),
        ("v2", "stations", STATION_COUNT),
        ("v2", "daily-readings", READING_COUNT),
    ],
)
def test_duckdb_attach_sqlite(version, resource_name, expected_count):
    """ATTACH sqlite reads the table named by the sqlite_table extension field."""
    descriptor = load_descriptor(version, "sqlite")
    resource = resource_by_name(descriptor, resource_name)

    # Use the sqlite_table extension field as documented in storage-backends.md
    table_name = resource["sqlite_table"]
    db_path = str(EXAMPLES / version / "sqlite" / resource["path"])

    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS db (TYPE sqlite, READ_ONLY)")
    count = con.execute(f'SELECT count(*) FROM db."{table_name}"').fetchall()[0][0]
    assert count == expected_count, (
        f"{version}/sqlite/{resource_name}: expected {expected_count} rows "
        f"in table '{table_name}', got {count}"
    )


# ---------------------------------------------------------------------------
# DuckDB ATTACH — DuckDB file backend
# Reference: "DuckDB" section — ATTACH for .duckdb files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,resource_name,expected_count",
    [
        ("v1", "stations", STATION_COUNT),
        ("v1", "daily-readings", READING_COUNT),
        ("v2", "stations", STATION_COUNT),
        ("v2", "daily-readings", READING_COUNT),
    ],
)
def test_duckdb_attach_duckdb_file(version, resource_name, expected_count):
    """ATTACH duckdb reads the table named by the duckdb_table extension field."""
    descriptor = load_descriptor(version, "duckdb")
    resource = resource_by_name(descriptor, resource_name)

    # Use the duckdb_table extension field as documented in storage-backends.md
    table_name = resource["duckdb_table"]
    db_path = str(EXAMPLES / version / "duckdb" / resource["path"])

    con = duckdb.connect()
    con.execute(f"ATTACH '{db_path}' AS db (READ_ONLY)")
    count = con.execute(f'SELECT count(*) FROM db."{table_name}"').fetchall()[0][0]
    assert count == expected_count, (
        f"{version}/duckdb/{resource_name}: expected {expected_count} rows "
        f"in table '{table_name}', got {count}"
    )


# ---------------------------------------------------------------------------
# polars — preferred for large Python workflows
# Reference: "Polars" section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_polars_read_parquet_stations(version):
    """Polars lazy parquet pattern (scan -> select/filter -> collect) works for stations."""
    path = str(EXAMPLES / version / "parquet" / "stations.parquet")
    df_polars = (
        pl.scan_parquet(path)
        .select(["station_id", "commissioned_date", "latitude"])
        .filter(pl.col("latitude") > -90)
        .collect()
    )
    assert isinstance(df_polars, pl.DataFrame)
    assert df_polars.height > 0
    assert set(["station_id", "commissioned_date", "latitude"]).issubset(
        df_polars.columns
    )


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_polars_read_parquet_readings(version):
    """Polars lazy parquet pattern works for daily-readings."""
    path = str(EXAMPLES / version / "parquet" / "daily-readings.parquet")
    df_polars = (
        pl.scan_parquet(path)
        .select(["station_id", "date", "temp_max_c"])
        .filter(pl.col("temp_max_c") > -273.15)
        .collect()
    )
    assert isinstance(df_polars, pl.DataFrame)
    assert df_polars.height > 0
    assert set(["station_id", "date", "temp_max_c"]).issubset(df_polars.columns)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_polars_to_pandas_stations(version):
    """polars.to_pandas() produces a pandas DataFrame with the correct shape and columns.

    Documents the recommended conversion pattern from the "Polars" section:
    read with polars (which handles date32 natively), then convert to pandas
    only when a pandas-idiomatic workflow is required downstream.
    """
    path = str(EXAMPLES / version / "parquet" / "stations.parquet")
    df_polars = (
        pl.scan_parquet(path)
        .select(["station_id", "commissioned_date", "latitude"])
        .filter(pl.col("latitude") > -90)
        .collect()
    )
    assert isinstance(df_polars, pl.DataFrame)
    df_pandas = df_polars.to_pandas()
    assert isinstance(df_pandas, pd.DataFrame), (
        f"{version}/parquet/stations: expected pandas DataFrame after .to_pandas(), "
        f"got {type(df_pandas)}"
    )
    assert not df_pandas.empty
    assert set(["station_id", "commissioned_date", "latitude"]).issubset(
        df_pandas.columns
    )


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_polars_scan_csv_to_pandas(version):
    """Polars lazy CSV scan pattern can be collected and converted to pandas."""
    path = str(EXAMPLES / version / "csv" / "stations.csv")
    df_polars = pl.scan_csv(path).select(["station_id", "latitude"]).collect()
    assert isinstance(df_polars, pl.DataFrame)
    df_pandas = df_polars.to_pandas()

    assert isinstance(df_pandas, pd.DataFrame)
    assert not df_pandas.empty
    assert set(["station_id", "latitude"]).issubset(df_pandas.columns)


# ---------------------------------------------------------------------------
# pandas
# Reference: "pandas" section
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_pandas_read_parquet_stations(version):
    """pandas read_parquet loads stations with the expected shape."""
    path = str(EXAMPLES / version / "parquet" / "stations.parquet")
    df = pd.read_parquet(path)
    assert df.shape == (STATION_COUNT, len(STATION_COLUMNS)), (
        f"{version}/parquet/stations: expected shape ({STATION_COUNT}, {len(STATION_COLUMNS)}), "
        f"got {df.shape}"
    )
    assert list(df.columns) == STATION_COLUMNS


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_pandas_read_parquet_readings(version):
    """pandas read_parquet loads daily-readings with the expected shape."""
    path = str(EXAMPLES / version / "parquet" / "daily-readings.parquet")
    df = pd.read_parquet(path)
    assert df.shape == (READING_COUNT, len(READING_COLUMNS)), (
        f"{version}/parquet/daily-readings: expected shape "
        f"({READING_COUNT}, {len(READING_COLUMNS)}), got {df.shape}"
    )


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_pandas_read_csv_stations(version):
    """pandas read_csv loads stations as a DataFrame."""
    path = str(EXAMPLES / version / "csv" / "stations.csv")
    df = pd.read_csv(path)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "station_id" in df.columns


# ---------------------------------------------------------------------------
# Python sqlite3 stdlib
# Reference: "SQLite" section — "Via Python stdlib (when DuckDB is unavailable)"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_sqlite3_stations(version):
    """Python sqlite3 + pandas.read_sql pattern works for a sqlite-backed resource."""
    descriptor = load_descriptor(version, "sqlite")
    resource = resource_by_name(descriptor, "stations")
    table_name = resource["sqlite_table"]
    db_path = str(EXAMPLES / version / "sqlite" / resource["path"])

    con = sqlite3.connect(db_path)
    df = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 100', con)
    con.close()

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "station_id" in df.columns
