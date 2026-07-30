"""Tests for the pandas/DuckDB/polars S3 query patterns documented in
references/data-access.md.

All tests make a real network call against the live PUDL S3 bucket, following the
same live-call precedent as test_fetch_descriptor.py: this suite exists specifically
to catch regressions in *reachability* (SSL/addressing quirks, stale table names,
credential handling), which a mocked or local fixture can't surface. Each test
targets the smallest resource that still exercises the documented pattern, to keep
the live calls cheap.

pudl.catalyst.coop is free and public and needs no AWS credentials. But whether a
developer's machine happens to have credentials configured (valid, invalid, or none)
must not change whether these tests pass -- that would make the suite's result an
accident of the local environment rather than a check of whether the documented
patterns actually work for a user with nothing configured. The autouse fixture below
strips every source of ambient AWS credentials so the tests are hermetic; each
library's read then relies solely on the documented anonymous-access options
(`s3_access_key_id`/`s3_secret_access_key` for DuckDB, `anon` for pandas,
`aws_skip_signature` for polars) to prove those options are sufficient on their own.

Run:  pixi run pytest dev/skills/pudl/tests/test_data_access.py -v
"""

import datetime
from pathlib import Path

import duckdb
import pandas as pd
import polars as pl
import pytest

# Smallest core_*__codes_* parquet file in the nightly build (a few KB) --
# exercises the documented "read_parquet over s3://" pattern cheaply.
SMALL_PARQUET_TABLE = "core_rus__codes_fuel_types"
SMALL_PARQUET_URL = f"s3://pudl.catalyst.coop/nightly/{SMALL_PARQUET_TABLE}.parquet"

# Used for the column+row pushdown tests below -- large enough that pulling it in
# full would be wasteful, which is exactly the point of those tests: a pushed-down
# filter should only read the matching row groups, not the whole file.
GENERATION_TABLE_URL = "s3://pudl.catalyst.coop/nightly/out_eia923__generation.parquet"
FILTER_CUTOFF_DATE = datetime.date(2020, 1, 1)

# A table from the raw per-form FERC Parquet directories -- exercises the documented
# "raw per-form Parquet directory" pattern (one Parquet file per table, alongside a
# datapackage.json, under nightly/<form>_<era>/).
FERC1_XBRL_TABLE_URL = (
    "s3://pudl.catalyst.coop/nightly/ferc1_xbrl/identification_001_duration.parquet"
)


@pytest.fixture(autouse=True)
def _no_ambient_aws_credentials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Strip every source of ambient AWS credentials for every test in this module.

    boto3 (pandas/s3fs) and the object_store crate (polars) both consult
    AWS_* environment variables and the default credentials/config files before
    falling back to instance-metadata lookups. Clearing all of them means a test
    only passes because the documented anonymous-access option actually works --
    not because the machine running the suite happens to have (valid or invalid)
    credentials lying around.
    """
    for var in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv(
        "AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no-such-credentials-file")
    )
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-such-config-file"))


def test_read_parquet_from_s3_with_path_style_addressing() -> None:
    """The documented fix (SET s3_url_style = 'path') makes read_parquet() over
    s3:// work against the pudl.catalyst.coop bucket, whose dotted name otherwise
    breaks DuckDB's default virtual-hosted-style S3 addressing. Clearing the S3
    credential settings forces the anonymous request this public bucket needs,
    rather than relying on no credentials being configured."""
    con = duckdb.connect()
    con.execute("SET s3_url_style = 'path'")
    con.execute("SET s3_access_key_id = ''")
    con.execute("SET s3_secret_access_key = ''")
    df = con.execute(f"SELECT * FROM read_parquet('{SMALL_PARQUET_URL}') LIMIT 5").df()
    assert not df.empty
    assert "code" in df.columns
    assert "description" in df.columns


def test_pandas_read_parquet_from_s3() -> None:
    """pandas (via s3fs) needs storage_options={"anon": True} to guarantee anonymous
    access -- without it, s3fs tries to sign requests with whatever credentials (even
    invalid ones) it finds first, which fails against a public bucket that never
    expected them."""
    df = pd.read_parquet(SMALL_PARQUET_URL, storage_options={"anon": True})
    assert not df.empty
    assert "code" in df.columns
    assert "description" in df.columns


def test_pandas_read_parquet_with_column_and_row_filters() -> None:
    """pandas' `filters=` pushes a row filter down to the Parquet reader alongside
    `columns=`, so only matching row groups are ever read. `filters=` must compare
    against the column's actual type -- a `datetime.date`, not a string, for a date
    column -- or pyarrow raises ArrowNotImplementedError."""
    df = pd.read_parquet(
        GENERATION_TABLE_URL,
        columns=["plant_id_eia", "report_date"],
        filters=[("report_date", ">=", FILTER_CUTOFF_DATE)],
        storage_options={"anon": True},
    )
    assert not df.empty
    assert list(df.columns) == ["plant_id_eia", "report_date"]
    # report_date round-trips as plain datetime.date (object dtype), not Timestamp.
    assert (df["report_date"] >= FILTER_CUTOFF_DATE).all()


def test_polars_scan_parquet_from_s3() -> None:
    """polars needs storage_options={"aws_skip_signature": "true", "aws_region": ...}
    -- unlike pandas/s3fs, it doesn't fall back to anonymous access on its own, so
    without this it either hangs on an EC2 instance-metadata lookup or fails because
    it can't determine the bucket's region."""
    df = (
        pl.scan_parquet(
            SMALL_PARQUET_URL,
            storage_options={"aws_skip_signature": "true", "aws_region": "us-west-2"},
        )
        .select(["code", "description"])
        .collect()
    )
    assert not df.is_empty()
    assert df.columns == ["code", "description"]


def test_polars_scan_parquet_with_select_and_filter() -> None:
    """Chaining .select()/.filter() before .collect() on a lazy scan pushes both
    the column and row selection down to the Parquet reader, same as pandas'
    columns=/filters=, rather than materializing the full table first."""
    df = (
        pl.scan_parquet(
            GENERATION_TABLE_URL,
            storage_options={"aws_skip_signature": "true", "aws_region": "us-west-2"},
        )
        .select(["plant_id_eia", "report_date"])
        .filter(pl.col("report_date") >= pl.lit(FILTER_CUTOFF_DATE))
        .collect()
    )
    assert not df.is_empty()
    assert df.columns == ["plant_id_eia", "report_date"]
    assert (df["report_date"] >= FILTER_CUTOFF_DATE).all()


def test_read_raw_ferc_xbrl_parquet_table_from_s3() -> None:
    """Raw per-form FERC data (DBF- and XBRL-derived) is published as one Parquet
    file per table inside a per-form/era directory, read the same way as any other
    PUDL Parquet table -- no SQLite/DuckDB database or download required."""
    con = duckdb.connect()
    con.execute("SET s3_url_style = 'path'")
    con.execute("SET s3_access_key_id = ''")
    con.execute("SET s3_secret_access_key = ''")
    df = con.execute(
        f"SELECT * FROM read_parquet('{FERC1_XBRL_TABLE_URL}') LIMIT 5"
    ).df()
    assert not df.empty
