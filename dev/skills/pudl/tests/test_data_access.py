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

from pathlib import Path

import duckdb
import pandas as pd
import polars as pl
import pytest

# Smallest core_*__codes_* parquet file in the nightly build (a few KB) --
# exercises the documented "read_parquet over s3://" pattern cheaply.
SMALL_PARQUET_TABLE = "core_rus__codes_fuel_types"
SMALL_PARQUET_URL = f"s3://pudl.catalyst.coop/nightly/{SMALL_PARQUET_TABLE}.parquet"

# Smallest of the five FERC XBRL DuckDB databases (~50 MB) -- exercises the
# documented "ATTACH a remote .duckdb file" pattern. ATTACH is queried over
# https://, not s3://, per the note in data-access.md.
FERC60_XBRL_HTTPS_URL = (
    "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/ferc60_xbrl.duckdb"
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


def test_attach_ferc_xbrl_duckdb_over_https() -> None:
    """DuckDB's ATTACH rejects s3:// URIs outright (regardless of s3_url_style),
    so the documented pattern uses the https:// form instead. That form doesn't go
    through DuckDB's S3 credential-signing path at all, so no anonymous-access
    setting is needed here."""
    con = duckdb.connect()
    con.execute(f"ATTACH '{FERC60_XBRL_HTTPS_URL}' AS ferc60 (READ_ONLY)")
    tables = con.execute(
        "SELECT table_name FROM duckdb_tables() WHERE database_name = 'ferc60' LIMIT 1"
    ).fetchall()
    assert tables, "Expected at least one table in the attached ferc60 XBRL database"
