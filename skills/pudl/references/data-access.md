# Data Access

## Use this when

- Loading PUDL tables in a script.
- Choosing between S3 and a local copy.
- Generating reproducible data-loading code for a user.
- Deciding how to access raw FERC form data.

---

## Choosing local vs. remote data

**Always check for local data before defaulting to S3.** Remote queries are convenient
but can be slow on poor connections or with heavy usage. Follow this decision tree
every time you are about to generate data-loading code:

1. **Check environment variables** — run `echo $PUDL_OUTPUT` and `echo $PUDL_DATA`
    in the user's shell. If either is set and points to a directory that exists, it
    likely contains a local copy of the PUDL Parquet files:

    - `$PUDL_DATA` — the standard download location for the distributed Parquet bundle
    - `$PUDL_OUTPUT` — the output directory of a local PUDL pipeline run; Parquet
        files are under `$PUDL_OUTPUT/parquet/`

    If a local directory is found, ask the user: *"I found a local PUDL data directory
    at `<path>`. Would you like to read from there instead of S3?"*

1. **Ask if neither is set** — if neither variable is set (or neither points to a
    real directory), ask: *"Do you have a local copy of the PUDL data somewhere?
    If so, reading locally will be faster than S3."*

1. **Suggest downloading if queries are slow** — if you find yourself making many
    long or slow remote queries, suggest that the user download the full Parquet bundle:

    ```text
    https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/pudl_parquet.zip
    ```

    > **Size warning**: `pudl_parquet.zip` is approximately 10 GB. Ask the user where
    > they would like to save it before downloading.

    After downloading, suggest they set `$PUDL_DATA` to point at the unzipped
    directory so future sessions can find it automatically. Offer to add the export
    line to their shell startup file (e.g. `~/.zshrc`, `~/.bashrc`, or
    `~/.profile`) if you have permission to edit environment files.

---

## Data locations

All PUDL outputs — Parquet files and datapackage.json descriptors — are free and
publicly accessible on AWS S3. No AWS credentials or account needed.

### Core PUDL outputs

| Location                                    | Path pattern                                              |
| ------------------------------------------- | --------------------------------------------------------- |
| S3 nightly (latest)                         | `s3://pudl.catalyst.coop/nightly/<table_name>.parquet`    |
| S3 versioned                                | `s3://pudl.catalyst.coop/v2024.11.0/<table_name>.parquet` |
| Local download (`$PUDL_DATA`)               | `$PUDL_DATA/<table_name>.parquet`                         |
| Local PUDL pipeline output (`$PUDL_OUTPUT`) | `$PUDL_OUTPUT/parquet/<table_name>.parquet`               |

The core PUDL Parquet outputs share a single descriptor at the same base path:
`pudl_parquet_datapackage.json`. The raw per-form FERC data described in
[FERC historical form data](#ferc-historical-form-data) below has its own
`datapackage.json` per form/era directory.

**Use S3 nightly** for most exploratory work. For production pipelines or academic
citation, use a fixed versioned path (e.g. `v2024.11.0`) so results are reproducible
and the data never changes under you.

### DuckDB and S3: required setup

The `pudl.catalyst.coop` bucket name contains dots. DuckDB's default S3 addressing mode
is virtual-hosted-style, which folds the bucket name into the hostname
(`pudl.catalyst.coop.s3.us-west-2.amazonaws.com`). AWS's S3 TLS certificate only covers
one wildcard level (`*.s3.<region>.amazonaws.com`), so that hostname doesn't match the
certificate, and DuckDB fails with an `SSL peer certificate or SSH remote key was not OK`
error — not a permissions or connectivity problem.

This bucket is free and public and needs **no** AWS credentials — but if the user
happens to have credentials configured (even invalid or expired ones, e.g. a stale SSO
token), DuckDB picks up `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` from the environment
automatically and tries to sign requests with them, turning a should-just-work public
read into a confusing `403 Forbidden` / `InvalidAccessKeyId` error. Clear them
explicitly rather than assuming their absence.

Run this once per DuckDB session before any query touching `s3://pudl.catalyst.coop/...`
(including through `/query`):

```sql
SET s3_url_style = 'path';
SET s3_access_key_id = '';
SET s3_secret_access_key = '';
```

The first line switches to path-style addressing
(`s3.us-west-2.amazonaws.com/pudl.catalyst.coop/...`), which keeps the bucket name out of
the hostname and avoids the certificate mismatch. The next two force anonymous requests
regardless of what's in the environment. Every DuckDB SQL example below assumes all
three have already been set.

### FERC EQR (Electric Quarterly Reports / Form 920)

The FERC EQR dataset (also known as **FERC Form 920**) is distributed separately at
`s3://pudl.catalyst.coop/ferceqr/` due to its size. **Only one version is publicly
available at a time** — there is no versioned path.

EQR data is updated **monthly**: the pipeline runs at the start of each month and new
data typically appears by the 3rd day of the month.

EQR tables are **partitioned into quarterly Parquet files** inside a per-table directory:

```text
s3://pudl.catalyst.coop/ferceqr/<table_name>/<year>q<quarter>.parquet
```

Examples:

- `s3://pudl.catalyst.coop/ferceqr/core_ferceqr__transactions/2024q1.parquet`
- `s3://pudl.catalyst.coop/ferceqr/core_ferceqr__transactions/2013q3.parquet`

> **Size warning**: `core_ferceqr__transactions` is ~100 GB total; recent quarterly
> files are ~3.5 GB each as compressed Parquet. **Never load the full table into
> memory.** Load only the quarters you need, and push down column/row filters.
> Other EQR tables are tens to hundreds of MB.

**With DuckDB (pure SQL — no Python required):**

```sql
SET s3_url_style = 'path';
SET s3_access_key_id = '';
SET s3_secret_access_key = '';

-- Attach the EQR descriptor (optional, for schema inspection)
-- Then query specific quarters directly
SELECT * FROM read_parquet(
    's3://pudl.catalyst.coop/ferceqr/core_ferceqr__transactions/2023q*.parquet'
)
WHERE report_year = 2023
LIMIT 1000;
```

Use the `/query` skill to run queries against EQR data — DuckDB can scan
Parquet files from S3 without downloading them.

**With polars (memory-efficient Python):**

```python
import polars as pl

storage_options = {"aws_skip_signature": "true", "aws_region": "us-west-2"}

# Load a single quarter
df = (
    pl.scan_parquet(
        "s3://pudl.catalyst.coop/ferceqr/core_ferceqr__transactions/2023q1.parquet",
        storage_options=storage_options,
    )
    .select(["seller_name", "buyer_name", "transaction_quantity"])
    .collect()
)

# Load all quarters for a year using a glob
df = pl.scan_parquet(
    "s3://pudl.catalyst.coop/ferceqr/core_ferceqr__transactions/2023q*.parquet",
    storage_options=storage_options,
).collect()
```

Descriptor:

- S3: `s3://pudl.catalyst.coop/ferceqr/ferceqr_parquet_datapackage.json`
- HTTPS: `https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr/ferceqr_parquet_datapackage.json`

---

## FERC historical form data

FERC Forms 1, 2, 6, 60, and 714 span two distinct filing eras with different source
formats. PUDL converts each form/era combination into a set of raw Parquet files
published alongside the core PUDL outputs at the same S3 base path — one Parquet file
per table, plus a `datapackage.json` descriptor, inside a per-form/era directory.

### Reporting epochs

| Form                                                            | Legacy format    | Legacy years | XBRL years   |
| --------------------------------------------------------------- | ---------------- | ------------ | ------------ |
| Form 1 (Electric Utilities)                                     | DBF              | 1994–2020    | 2021–present |
| Form 2 (Interstate Gas Transmission Companies)                  | DBF              | 1996–2020    | 2021–present |
| Form 6 (Oil Pipeline Companies)                                 | DBF              | 2000–2020    | 2021–present |
| Form 60 (Centralized Service Companies)                         | DBF              | 2006–2020    | 2021–present |
| Form 714 (Electricity Balancing Authorities and Planning Areas) | CSV (DBF export) | 2006-2020    | 2021–present |

**Form 714 has no DBF-derived Parquet data.** The legacy CSV export was never
converted; only the XBRL-derived raw data (2021–present) and the integrated PUDL
tables (2006–present) are available for Form 714.

### PUDL integration status

Always check whether a PUDL integrated table exists before falling back to raw
per-form data. Integrated tables are cleaned, entity-resolved, and span all years with
a uniform schema.

- **FERC Form 1**: Only some schedules have been integrated. See
    [FERC Form 1 Schedules](./ferc1-schedules.md) for the per-schedule breakdown.
    For unintegrated Form 1 schedules, use the raw DBF- or XBRL-derived Parquet files
    below. Only provide raw Form 1 data if a user **explicitly** requests it.
- **FERC Forms 2, 6, and 60**: None of this data has been integrated into PUDL.
    It is only available through the raw per-form Parquet files.
- **FERC Form 714**: Only the integrated PUDL tables span pre-2021 years.
    The legacy CSV files were not structured for general machine-readable extraction.
    Integrated Form 714 tables cover all electronic reporting years (2006–present).

### Raw per-form Parquet directories

```text
s3://pudl.catalyst.coop/nightly/<form>_<era>/datapackage.json
s3://pudl.catalyst.coop/nightly/<form>_<era>/<table_name>.parquet
```

| Form     | DBF-derived (legacy)                          | XBRL-derived (2021–present)                     |
| -------- | --------------------------------------------- | ----------------------------------------------- |
| Form 1   | `s3://pudl.catalyst.coop/nightly/ferc1_dbf/`  | `s3://pudl.catalyst.coop/nightly/ferc1_xbrl/`   |
| Form 2   | `s3://pudl.catalyst.coop/nightly/ferc2_dbf/`  | `s3://pudl.catalyst.coop/nightly/ferc2_xbrl/`   |
| Form 6   | `s3://pudl.catalyst.coop/nightly/ferc6_dbf/`  | `s3://pudl.catalyst.coop/nightly/ferc6_xbrl/`   |
| Form 60  | `s3://pudl.catalyst.coop/nightly/ferc60_dbf/` | `s3://pudl.catalyst.coop/nightly/ferc60_xbrl/`  |
| Form 714 | *(none — see above)*                          | `s3://pudl.catalyst.coop/nightly/ferc714_xbrl/` |

For example, the Form 1 XBRL table `identification_001_duration` lives at
`s3://pudl.catalyst.coop/nightly/ferc1_xbrl/identification_001_duration.parquet`, and
its descriptor is at `s3://pudl.catalyst.coop/nightly/ferc1_xbrl/datapackage.json`.

These are read the same way as any other PUDL Parquet table — see
[Loading PUDL Parquet tables](#loading-pudl-parquet-tables) below, substituting the
form/era directory for `nightly/`. Use the `datapackage` skill against each
directory's `datapackage.json` to discover table and column names before querying.

DBF-derived table names are the original (often cryptic) FERC identifiers, e.g.
`f1_adit_amrt_prop`. Hand-compiled schedule-to-table mappings are available for Forms
1 (Electricity) and 2 (Gas Pipelines):

- [FERC Form 1 Schedules and Tables](./ferc1-schedules.md)
- [FERC Form 2 Schedules and Tables](./ferc2-schedules.md)

Equivalent mappings do not yet exist for Forms 6 or 60.

### Listing tables in a raw per-form directory

Using DuckDB:

```sql
SET s3_url_style = 'path';
SET s3_access_key_id = '';
SET s3_secret_access_key = '';

SELECT file
FROM glob('s3://pudl.catalyst.coop/nightly/ferc1_xbrl/*.parquet');
```

Or query the descriptor with jq (see the `datapackage` skill for full querying patterns).
The remote filename inside every form/era directory is always `datapackage.json` — download
it and give the local copy a disambiguated name so you can tell descriptors apart once
you've fetched more than one:

```bash
curl -o ferc1_xbrl_datapackage.json \
    https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/ferc1_xbrl/datapackage.json
jq -r '.resources[].name' ferc1_xbrl_datapackage.json
```

---

## Loading PUDL Parquet tables

**Sample or aggregate by default rather than pulling a full table.** Some PUDL tables
are multiple gigabytes; loading one in full to answer a question that a `LIMIT`, a row
filter, a column selection, or an aggregate query would have answered just as well
wastes time and memory for no benefit. DuckDB's `LIMIT`/`WHERE`, polars'
`scan_parquet().select().filter().collect()` lazy pipeline, and pandas'
`columns=`/`filters=` arguments all push the selection down to the Parquet reader
itself, so only the requested data is ever transferred. Reach for whichever narrows the
read before reaching for a full load. You should estimate a table's size before a full,
unfiltered load, and only load the full table if the job genuinely needs every row.

**Summing or joining quantity columns?** Check each field's `unit` first — a matching
column name doesn't guarantee a matching unit, and mismatched-scale units (e.g. `Mcf` vs
`MMcf`) combine silently into a wrong-but-plausible number. See
[Using units safely when combining data](./metadata-and-querying.md#using-units-safely-when-combining-data).

### With pandas

**Pass `storage_options={"anon": True}`.** Without it, pandas/s3fs falls back to
anonymous access only when it finds no credentials at all — but if the user has any
AWS credentials configured, even invalid or expired ones, s3fs tries to sign requests
with them first and fails with a `403`/`ACCESS_DENIED` error instead of falling back.
Passing `anon=True` explicitly skips the credential lookup entirely, so this works the
same way regardless of what's in the user's environment.

```python
import datetime

import pandas as pd

table = "out_eia923__generation"

# Default: narrow to the columns (and, via `filters=`, the rows) you actually need --
# much faster for large tables, since the selection is pushed down to the reader.
# `filters=` compares against the column's actual type -- a date column needs a
# `datetime.date`, not a string, or pyarrow raises ArrowNotImplementedError.
df = pd.read_parquet(
    f"s3://pudl.catalyst.coop/nightly/{table}.parquet",
    columns=["plant_id_eia", "report_date", "net_generation_mwh"],
    filters=[("report_date", ">=", datetime.date(2020, 1, 1))],
    storage_options={"anon": True},
)

# Only when the task genuinely needs every column: drop `columns=`/`filters=`
df = pd.read_parquet(
    f"s3://pudl.catalyst.coop/nightly/{table}.parquet", storage_options={"anon": True}
)

# From local file (same columns=/filters= arguments apply)
df = pd.read_parquet(f"/path/to/pudl_parquet/{table}.parquet")
```

`s3fs` must be installed for S3 access. Install with `uv add s3fs` (preferred) or
`pip install s3fs` if `uv` is not available.

### With DuckDB (efficient for large tables or SQL-style queries)

Pure SQL (no Python required) — use `/query` to run these:

```sql
SET s3_url_style = 'path';
SET s3_access_key_id = '';
SET s3_secret_access_key = '';

SELECT plant_id_eia, report_date, net_generation_mwh
FROM read_parquet('s3://pudl.catalyst.coop/nightly/out_eia923__generation.parquet')
WHERE report_date >= '2020-01-01'
LIMIT 1000;
```

Or from Python:

```python
import duckdb

con = duckdb.connect()
con.execute("SET s3_url_style = 'path'")
con.execute("SET s3_access_key_id = ''")
con.execute("SET s3_secret_access_key = ''")
result = con.execute("""
    SELECT plant_id_eia, report_date, net_generation_mwh
    FROM read_parquet('s3://pudl.catalyst.coop/nightly/out_eia923__generation.parquet')
    WHERE report_date >= '2020-01-01'
    LIMIT 1000
""").df()  # .df() returns a pandas DataFrame; .pl() returns polars
```

DuckDB can scan Parquet files from S3 without downloading them. Useful for large
hourly tables (e.g., `out_ferc714__respondents_hourly`).

### With polars (memory-efficient alternative to pandas)

**Pass `storage_options` explicitly.** Unlike pandas/s3fs, polars does not fall back to
anonymous access on its own — with no AWS credentials or region configured (the common
case, since this bucket needs neither), it hangs trying an EC2 instance-metadata lookup
and then fails because it can't determine the bucket's region. Skip both problems with:

```python
import polars as pl

table = "out_eia923__generation"

lf = pl.scan_parquet(
    f"s3://pudl.catalyst.coop/nightly/{table}.parquet",
    storage_options={"aws_skip_signature": "true", "aws_region": "us-west-2"},
)
# Default: chain .select()/.filter() before .collect() so column and row pruning
# happen at the Parquet reader, not after the whole table is already in memory.
df = (
    lf.select(["plant_id_eia", "report_date", "net_generation_mwh"])
    .filter(pl.col("report_date") >= pl.date(2020, 1, 1))
    .collect()
)
```

Polars lazy evaluation (`scan_parquet`) is preferred since it pushes down column
selection and row filters to the Parquet reader.

---

## Listing all available tables

```sql
SET s3_url_style = 'path';
SET s3_access_key_id = '';
SET s3_secret_access_key = '';

-- Pure DuckDB SQL: list all Parquet tables in the nightly build
SELECT file
FROM glob('s3://pudl.catalyst.coop/nightly/*.parquet');
```

Or with the AWS CLI:

```bash
aws s3 ls --no-sign-request s3://pudl.catalyst.coop/nightly/ | grep '\.parquet'
```

Or query the descriptor with jq (see the `datapackage` skill for full querying patterns):

```bash
jq -r '.resources[].name' pudl_parquet_datapackage.json
```

---

## Raw input archives (Zenodo)

**Do not surface this to users unless they explicitly ask about data provenance or
want to trace a value to its original source file.** Most users should use the
processed PUDL outputs instead.

For agent workflows, prefer the cached S3 copy of the archive over the Zenodo website
or API. The cache has the same `datapackage.json` metadata and raw files, and it is the
normal place to inspect archive contents.

Raw inputs are cached on S3 as a mirror of PUDL's Zenodo archives:

```text
s3://pudl.catalyst.coop/zenodo/<dataset>/<concrete-doi-path>/datapackage.json
```

Where `<dataset>` is the PUDL short code for the data source (see
[Data Sources](./data-sources.md) for the full list) and `<concrete-doi-path>` is the
Zenodo **record DOI** with `/` replaced by `-`.

This distinction matters:

- The source docs page usually shows the **concept DOI**, which refers to the dataset
    lineage as a whole.
- The cached S3 path uses a **concrete DOI**, which refers to one specific archived
    version.

For example, for DOI `10.5281/zenodo.17091669`, the `<concrete-doi-path>` would be
`10.5281-zenodo.17091669`, giving:

```text
s3://pudl.catalyst.coop/zenodo/ferc1/10.5281-zenodo.17091669/datapackage.json
```

If the docs page only gives you a concept DOI, do **not** assume the S3 path uses that
same DOI. List the dataset prefix in S3 and use the concrete DOI directory that matches
the cached record you need.

To construct a human-readable DOI URL from a Zenodo record ID (e.g. `19367768`):

```text
https://doi.org/10.5281/zenodo.<record_id>
# Example: https://doi.org/10.5281/zenodo.19367768
```

Use `zenodo.org` itself mainly when a user wants a browser-friendly DOI landing page or
when a needed historical version is no longer present in the S3 cache.

---

## Useful links

- Data catalog / table browser: <https://data.catalyst.coop>
- PUDL data access documentation: <https://docs.catalyst.coop/pudl/en/nightly/data_access.html>
- PUDL Data Release Concept DOI (Zenodo): <https://doi.org/10.5281/zenodo.3653158>
- PUDL Software Concept DOI (Zenodo): <https://doi.org/10.5281/zenodo.3404014>
- AWS Open Data Registry: <https://registry.opendata.aws/catalyst-cooperative-pudl/>
