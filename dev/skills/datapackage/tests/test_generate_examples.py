"""Tests for the generate_examples.py script.

These tests exercise the generator as a script against a temporary output
directory so they verify generation behavior independently from the skill
workflow tests that operate on the checked-in example assets.
"""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import duckdb
import polars as pl
import pyarrow.parquet as pq
import pytest
from conftest import DATE_COLUMNS


SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "generate_examples.py"


def run_generator(output_root: Path) -> subprocess.CompletedProcess[str]:
    """Run the example generator script against a temporary output directory."""
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output-root", str(output_root)],
        check=True,
        capture_output=True,
        text=True,
    )


def frictionless_validate(
    descriptor_path: Path, extra_args: list[str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Validate a generated datapackage descriptor with the frictionless CLI."""
    args = extra_args or []
    return subprocess.run(
        [sys.executable, "-m", "frictionless", "validate", str(descriptor_path), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def assert_file_matches_extension(file_path: Path) -> None:
    """Perform a lightweight format-consistency check based on file extension."""
    suffix = file_path.suffix

    if suffix == ".json":
        descriptor = json.loads(file_path.read_text(encoding="utf-8"))
        assert "resources" in descriptor and isinstance(descriptor["resources"], list)
        return

    if suffix == ".csv":
        df = pl.read_csv(file_path, n_rows=1)
        assert len(df.columns) > 0
        return

    if suffix == ".parquet":
        schema = pq.read_schema(file_path)
        assert len(schema) > 0
        return

    if suffix == ".duckdb":
        con = duckdb.connect(str(file_path), read_only=True)
        row = con.execute("SELECT count(*) FROM (SHOW TABLES)").fetchone()
        con.close()
        assert row is not None
        table_count = row[0]
        assert table_count > 0
        return

    if suffix == ".sqlite":
        con = sqlite3.connect(str(file_path))
        table_count = con.execute(
            "SELECT count(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0]
        con.close()
        assert table_count > 0
        return

    raise AssertionError(f"No format-consistency check implemented for: {file_path}")


@pytest.fixture(scope="module")
def generated_examples(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a fresh example tree under pytest-managed temporary storage."""
    output_root = tmp_path_factory.mktemp("generated-examples")
    run_generator(output_root)
    return output_root


@pytest.mark.parametrize(
    "version,backend,expected_files",
    [
        ("v1", "csv", ["datapackage.json", "stations.csv", "daily-readings.csv"]),
        (
            "v1",
            "parquet",
            ["datapackage.json", "stations.parquet", "daily-readings.parquet"],
        ),
        ("v1", "duckdb", ["datapackage.json", "weather.duckdb"]),
        ("v1", "duckdb-no-ext", ["datapackage.json", "weather.duckdb"]),
        ("v1", "sqlite", ["datapackage.json", "weather.sqlite"]),
        ("v2", "csv", ["datapackage.json", "stations.csv", "daily-readings.csv"]),
        (
            "v2",
            "parquet",
            ["datapackage.json", "stations.parquet", "daily-readings.parquet"],
        ),
        ("v2", "duckdb", ["datapackage.json", "weather.duckdb"]),
        ("v2", "duckdb-no-ext", ["datapackage.json", "weather.duckdb"]),
        ("v2", "sqlite", ["datapackage.json", "weather.sqlite"]),
    ],
)
def test_generate_examples_writes_expected_files(
    generated_examples: Path,
    version: str,
    backend: str,
    expected_files: list[str],
) -> None:
    """The generator writes the expected file set for each backend variant."""
    backend_dir = generated_examples / version / backend
    assert backend_dir.is_dir(), f"Missing generated directory: {backend_dir}"

    for filename in expected_files:
        file_path = backend_dir / filename
        assert file_path.exists(), f"Missing generated file: {file_path}"
        assert file_path.stat().st_size > 0, f"Generated file is empty: {file_path}"
        assert_file_matches_extension(file_path)


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_duckdb_parquet_date_columns(generated_examples: Path, version: str) -> None:
    """Parquet date columns expose as DuckDB DATE, not VARCHAR/TIMESTAMP."""
    for resource_name, date_cols in DATE_COLUMNS.items():
        filename = f"{resource_name}.parquet"
        path = generated_examples / version / "parquet" / filename
        con = duckdb.connect()
        schema = {
            row[0]: row[1]
            for row in con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{path}')"
            ).fetchall()
        }
        con.close()
        for col in date_cols:
            assert schema[col] == "DATE", (
                f"{version}/parquet/{filename}: column '{col}' has type '{schema[col]}', "
                "expected 'DATE'."
            )


@pytest.mark.parametrize("version", ["v1", "v2"])
def test_polars_precipitation_has_nulls(generated_examples: Path, version: str) -> None:
    """precipitation_mm should contain null values for non-reporting stations."""
    path = generated_examples / version / "parquet" / "daily-readings.parquet"
    df = pl.read_parquet(path, columns=["precipitation_mm"])
    null_count = df["precipitation_mm"].null_count()
    assert null_count > 0, (
        f"{version}/parquet: expected some null precipitation_mm values, got 0 nulls."
    )


@pytest.mark.parametrize(
    "version,resource_name,expected_date_cols",
    [
        ("v1", "stations", DATE_COLUMNS["stations"]),
        ("v2", "stations", DATE_COLUMNS["stations"]),
        ("v1", "daily-readings", DATE_COLUMNS["daily-readings"]),
        ("v2", "daily-readings", DATE_COLUMNS["daily-readings"]),
    ],
)
def test_parquet_date32_schema(
    generated_examples: Path,
    version: str,
    resource_name: str,
    expected_date_cols: list[str],
) -> None:
    """Parquet date columns are stored as date32[day], not string or timestamp."""
    filename = f"{resource_name}.parquet"
    path = generated_examples / version / "parquet" / filename
    schema = pq.read_schema(path)
    pa_types = {field.name: str(field.type) for field in schema}
    for col in expected_date_cols:
        assert pa_types[col] == "date32[day]", (
            f"{version}/parquet/{filename}: column '{col}' has pyarrow type "
            f"'{pa_types[col]}', expected 'date32[day]'."
        )


@pytest.mark.parametrize(
    "version,backend,extra_args",
    [
        ("v1", "csv", ["--standards", "v1"]),
        ("v2", "csv", ["--standards", "v2"]),
        ("v1", "parquet", ["--skip-errors", "byte-count,type-error,primary-key"]),
        ("v2", "parquet", ["--skip-errors", "byte-count,type-error,primary-key"]),
        ("v1", "sqlite", []),
        ("v2", "sqlite", []),
        ("v1", "duckdb", []),
        ("v2", "duckdb", []),
        ("v1", "duckdb-no-ext", []),
        ("v2", "duckdb-no-ext", []),
    ],
)
def test_generate_examples_outputs_valid_datapackages(
    generated_examples: Path,
    version: str,
    backend: str,
    extra_args: list[str],
) -> None:
    """Every generated descriptor validates with the same backend-appropriate flags."""
    descriptor_path = generated_examples / version / backend / "datapackage.json"
    result = frictionless_validate(descriptor_path, extra_args)
    assert result.returncode == 0
