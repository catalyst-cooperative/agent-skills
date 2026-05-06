# Storage Backends

## Use this when

- Loading data from a file referenced in a datapackage.json descriptor.
- Choosing the right tool for a given file format.
- Writing reproducible data-loading code for a user.

**Only proceed here if the user has explicitly asked to query or load data.** Metadata
exploration (descriptor querying) does not require touching data files at all.

---

## How datapackage.json describes data files

Each resource has:

- `path`: relative path **or URL** to the data file. If relative, resolve it against
    the base directory or base URL of the descriptor (see `metadata-querying.md`).
- `format`: file format string (e.g. `"parquet"`, `"csv"`, `"sqlite"`, `"duckdb"`)
- `mediatype`: MIME type (e.g. `"application/parquet"`, `"text/csv"`)

```bash
# Get all resource names, paths, and formats
jq -r '.resources[] | "\(.name)\t\(.path)\t\(.format // "unknown")"' datapackage.json
```

**Format preference**: when a dataset offers the same data in multiple formats, prefer
Parquet or DuckDB over SQLite or CSV — they are faster, typed, and support remote
access without downloading. SQLite files **must be local** (see below).

---

## DuckDB (preferred)

DuckDB is the preferred tool for data querying. It is a standalone CLI tool — no Python
environment required. If DuckDB is not installed, use `/duckdb-skills:install-duckdb` to
install it before proceeding. It handles Parquet, CSV, and DuckDB files with a unified
SQL interface, reads remote files over HTTPS or S3 without downloading them, and can
combine descriptor metadata queries with data queries in a single session.

Use `/duckdb-skills:query` to run SQL or natural language queries through it, and
`/duckdb-skills:attach-db` to register database files.

You are not limited to `read_parquet` — DuckDB can query any supported format
directly:

```sql
-- Parquet (local or remote)
SELECT * FROM read_parquet('/path/to/my_table.parquet') LIMIT 100;
SELECT * FROM read_parquet('https://example.com/data/my_table.parquet') LIMIT 100;
SELECT * FROM read_parquet('s3://my-bucket/my_table.parquet') LIMIT 100;

-- JSON
SELECT * FROM read_json('/path/to/data.json', format='auto') LIMIT 100;

-- Multiple files as one table (glob)
SELECT * FROM read_parquet('/data/part-*.parquet') LIMIT 100;

-- Attached DuckDB or SQLite database (via attach-db)
SELECT * FROM my_db.my_table LIMIT 100;
```

```sql
SELECT * FROM read_csv('/path/to/my_table.csv') LIMIT 100;
SELECT * FROM read_csv('https://example.com/data/my_table.csv') LIMIT 100;
```

```sql
ATTACH '/path/to/my_database.duckdb' AS db (READ_ONLY);
SELECT * FROM db.my_table LIMIT 100;
```

### Finding the correct table name in a database file

The Frictionless spec has no standard field for specifying which table inside a
`.duckdb` or `.sqlite` file a resource refers to — the `path` field only points to the
database file itself. Table names are indicated by non-standard extension fields, and
practice varies by publisher. Work through these in order:

**1. Check the resource for a table-name extension field.** Common field names:

```bash
jq '.resources[] | select(.name == "my_resource") | {table, duckdb_table, sqlite_table}' datapackage.json
```

If any of those is non-null, that is the table name to use.

**2. Try the resource `name` or `title`.** Publishers often name the table to match
the resource identifier. Try both as-is and with hyphens replaced by underscores
(SQL identifiers cannot contain hyphens).

**3. List all tables in the database** and match by inspection:

```sql
-- After attaching the file as `db`:

-- DuckDB file: SHOW TABLES only lists the in-memory database; use SHOW ALL TABLES
-- and filter to the attached database name.
SELECT name FROM (SHOW ALL TABLES) WHERE database = 'db' ORDER BY name;

-- SQLite file
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;
```

Compare the table names against the resource `name`, `title`, and `description` to
find the right one.

### Exploring unfamiliar tables

Always start with a small `LIMIT` — **10 to 100 rows** is enough to understand
structure, spot nulls, and get a feel for the data. Only increase the limit once you
know what you're working with. The `/duckdb-skills:query` skill warns before executing
queries that would return more than 1M rows, but that is a safety ceiling, not a
target. To interrupt a running query, press `Ctrl+C` in the terminal.

### Combining descriptor metadata with data queries

```sql
-- Find tables with a specific column, then sample one
WITH tables_with_col AS (
    SELECT r->>'$.name' AS table_name, r->>'$.path' AS path
    FROM (SELECT unnest(resources) AS r FROM read_json('datapackage.json', format='auto'))
    WHERE list_contains(
        [f->>'$.name' FOR f IN r->'$.schema.fields'],
        'plant_id_eia'
    )
)
SELECT * FROM read_parquet(base_url || '/' || path)
FROM tables_with_col
LIMIT 10;
```

### Getting a pandas DataFrame from DuckDB

```python
import duckdb

df = duckdb.sql("SELECT * FROM read_parquet('my_table.parquet') LIMIT 100").df()
```

---

## Polars (preferred for large Python workflows)

Polars is preferred over pandas for large datasets — it is faster, more
memory-efficient, and supports lazy evaluation. If the user ultimately needs a pandas
DataFrame, convert at the end:

```python
import polars as pl

# Parquet — lazy (pushes filters and column selection into the reader)
lf = pl.scan_parquet("/path/to/data/my_table.parquet")
df_polars = (
    lf.select(["id", "date", "value"]).filter(pl.col("date") >= "2020-01-01").collect()
)

# Convert to pandas only if needed downstream
df_pandas = df_polars.to_pandas()
```

```python
# CSV — lazy
lf = pl.scan_csv("/path/to/data/my_table.csv")
df_polars = lf.select(["id", "date", "value"]).collect()
df_pandas = df_polars.to_pandas()  # only if needed
```

---

## pandas

Use pandas when the user specifically needs a pandas-idiomatic workflow.

```python
import pandas as pd

# Parquet (local or remote — requires s3fs for S3, fsspec for HTTPS)
df = pd.read_parquet("/path/to/data/my_table.parquet")
df = pd.read_parquet("s3://my-bucket/path/my_table.parquet")

# Column projection (much faster for wide tables)
df = pd.read_parquet("/path/to/data/my_table.parquet", columns=["id", "date", "value"])
```

## CSV

```python
df = pd.read_csv("/path/to/data/my_table.csv")
```

---

## SQLite

**SQLite files must be local.** DuckDB and the Python `sqlite3` module cannot read
SQLite over HTTP or S3 — download the file first if it is remote. Prefer Parquet or
DuckDB formats if the dataset offers them.

```bash
# Download first if remote
curl -O https://example.com/data/my_database.sqlite
```

Via DuckDB (preferred — use `/duckdb-skills:attach-db`):

```sql
-- attach-db handles this; shown here for reference
ATTACH '/path/to/my_database.sqlite' AS db (TYPE sqlite, READ_ONLY);
SELECT * FROM db.my_table LIMIT 100;
```

To find the correct table name, follow the same process as for DuckDB files — see
**Finding the correct table name in a database file** above.

Via Python stdlib (when DuckDB is unavailable):

```python
import sqlite3, pandas as pd

con = sqlite3.connect("/path/to/data/my_database.sqlite")
df = pd.read_sql("SELECT * FROM my_table LIMIT 100", con)
con.close()
```

---

## Quick reference

- **Any format, SQL or natural language** — `/duckdb-skills:query`
- **Attach a .duckdb or .sqlite file for session queries** — `/duckdb-skills:attach-db`
- **Remote Parquet/CSV (HTTPS/S3), no download** — `/duckdb-skills:query`
- **Metadata + data in one session** — `/duckdb-skills:query` with `read_json` + data query
- **Large dataset in Python** — polars (convert to pandas at the end if needed)
- **SQLite** — download first, then DuckDB `ATTACH` or `sqlite3`
- **Typed, reproducible loading** — Parquet > DuckDB > CSV > SQLite
