---
name: datapackage
description: >
  Explore and query any dataset annotated with a Frictionless Data Package descriptor
  (datapackage.json). Use this skill whenever a user wants to discover what tables or
  resources a dataset contains, look up column names and descriptions, surface usage
  warnings embedded in metadata, or understand how to load data from Parquet files,
  DuckDB or SQLite databases, or CSV files described by a datapackage.json. Also use
  when the user has a datapackage.json and wants to know what's in it, how to query it
  efficiently, or how to connect its metadata to actual data files. Pairs well with
  dataset-specific skills (like `pudl`) that layer domain knowledge on top.
license: CC-BY-4.0
compatibility: |
  Required CLI tools: jq >= 1.7
  Optional CLI tools: frictionless >= 5.18 (with fastparquet for Parquet support)
  Required skills: duckdb-skills (install-duckdb, attach-db, query)
  Optional Python packages: marimo, pandas, polars, duckdb (for DataFrame work)
metadata:
  - author: Catalyst Cooperative
  - email: hello@catalyst.coop
  - last-updated: 2026-04-03
---

# Frictionless Data Package Guide

This skill covers any dataset described by a
[Frictionless Data Package](https://datapackage.org/) descriptor file
(`datapackage.json`). It is intentionally generic — it works for any conforming
datapackage, regardless of who published it or what the data contains.

For PUDL-specific knowledge (S3 bucket paths, table tier conventions, data source
context, usage warnings), also use the `pudl` skill on top of this one.

## What is a datapackage.json?

A `datapackage.json` is a JSON file that describes a collection of tabular data
resources. Each resource represents one table (or file) and includes:

- `name`: machine-readable identifier
- `description`: human-readable description, often including processing notes, primary
    keys, and usage warnings
- `path`: filename or URL of the actual data file
- `schema.fields`: list of columns, each with a `name` and `description`

The file can be large (hundreds of resources, megabytes of JSON). Always query it
selectively — never load it whole into context.

## Dependency check

Before querying metadata, verify `jq` is available:

```bash
command -v jq
```

If not found, tell the user how to install it:

- macOS: `brew install jq`
- Linux (apt): `sudo apt install jq`
- Linux (conda): `conda install jq`
- Windows: `winget install jqlang.jq`

For data loading and SQL queries, the `attach-db`, and `query` skills from
`duckdb-skills` must be installed. Install them from `duckdb/duckdb-skills`.

## Workflow overview

1. **Locate the descriptor** — find or download `datapackage.json` (see below).
1. **Query metadata selectively** — use jq or DuckDB to extract only what you need.
    See [Metadata Querying](./references/metadata-querying.md).
1. **Surface warnings** — always check for usage warnings before presenting a resource.
1. **Validate** *(optional)* — if the user wants to know whether the data actually
    matches the descriptor, or if you're diagnosing a suspicious package, use
    `frictionless validate`. See [Frictionless Validate](./references/frictionless-validate.md).
1. **Load the data** *(optional)* — only if the user explicitly wants to query or
    explore the actual data. Data files can be large and remote access can be slow or
    costly. Don't initiate data loading as a follow-on to a metadata lookup without
    confirming the user wants it. See [Storage Backends](./references/storage-backends.md).

## Reference index

- [Metadata Querying](./references/metadata-querying.md) — locate the descriptor,
    query it selectively with jq or DuckDB, surface usage warnings
- [Storage Backends](./references/storage-backends.md) — load data from Parquet,
    DuckDB, SQLite, or CSV files referenced by the descriptor
- [Frictionless Validate](./references/frictionless-validate.md) — use the `frictionless`
    CLI to validate packages, check data quality, infer schemas, and diagnose unfamiliar
    descriptors; read when the user wants to validate a descriptor, check if data matches
    its schema, or understand what the `frictionless` tool can tell them about a package

## Community patterns and recipes

The datapackage standard is permissive: publishers frequently add non-standard fields.
Two conventions are worth knowing immediately:

- **Custom fields** — non-standard keys added by publishers are common and valid.
    The `_` prefix convention marks system-generated or platform-specific keys (e.g.
    `_cache`, `_platformVersion`). Some publishers add custom keys without the prefix
    (e.g. PUDL adds `duckdb_table`, `sqlite_table` on database-backed resources). Treat
    unknown fields as informational metadata, not errors.
- **Compressed resources** — a resource with a `.gz` or `.zip` path may have an
    explicit `"compression": "gz"` field. The `bytes` and `hash` fields apply to the
    compressed file, not the uncompressed original.

For other patterns (catalogs, versioning, external foreign keys, translation support,
field relationships, etc.), fetch the relevant page on demand:

- v1 patterns: <https://specs.frictionlessdata.io/patterns/>
- v2 recipes: <https://datapackage.org/recipes/caching-of-resources/> (navigate via
    sidebar or next/previous links — no index page exists)

Both pages cover largely the same set of community conventions; consult whichever
matches the descriptor version you're working with.

## Companion skills

This skill delegates actual data querying to:

- **`/duckdb-skills:attach-db`** — attach a `.duckdb` or `.sqlite` database file and
    set up a persistent session for querying
- **`/duckdb-skills:query`** — run SQL or natural language queries against attached
    databases, ad-hoc files (Parquet, CSV, remote HTTPS/S3), and JSON files including
    `datapackage.json` itself (via DuckDB's `read_json`)

These skills must be installed. See `skills-lock.json` in the project root.

## Key constraints

- **Golden rule: never load the full datapackage.json into context.** It may be
    megabytes with hundreds of resources. Always query selectively.
- **Read the full description before presenting a resource.** Descriptions often
    contain important context: processing notes, primary key conventions, data
    provenance, or caveats about known limitations. Don't skip them.
- **Use `uv` to install Python packages** — prefer `uv add <package>` over
    `pip install <package>`. `uv` is faster and installs into a virtual environment
    rather than globally. Fall back to `pip` only if `uv` is not available
    (`command -v uv` returns nothing).
- **Do not use Python to query descriptor metadata.** Python is not the right tool here
    — it loads the full JSON into memory (violating the golden rule above), adds
    unnecessary dependencies, and can't easily handle remote descriptors. Use jq for
    metadata-only tasks; use DuckDB when you need to combine metadata queries with data
    queries. Python is only appropriate for loading data (via pandas or polars) after you
    already know which table and columns you need.

## Schema reference and version detection

Two versions of the Frictionless Data Package standard are in common use. Identify the
version from the top-level descriptor before parsing:

| Field present | Version                          | Example value                                             |
| ------------- | -------------------------------- | --------------------------------------------------------- |
| `"$schema"`   | v2.0                             | `"https://datapackage.org/profiles/2.0/datapackage.json"` |
| `"profile"`   | v1.0                             | `"tabular-data-package"` or `"data-package"`              |
| neither       | ambiguous (treat as v1 baseline) | —                                                         |

Key differences between versions that affect parsing:

- **Contributors** — v1 has `"role": "author"` (singular string); v2 has
    `"roles": ["author"]` (array). Both may appear in the wild.
- **Name pattern** — v1 enforces strictly lowercase `[-a-z0-9._/]`; v2 is unrestricted.
- **`version` field** — present in v2, absent in v1.

Bundled schemas:

- [`assets/datapackage-v1.schema.json`](./assets/datapackage-v1.schema.json) — v1.0
    (JSON Schema draft-04). Used by FERC XBRL packages and many older datasets.
- [`assets/datapackage-v2.schema.json`](./assets/datapackage-v2.schema.json) — v2.0
    (JSON Schema draft-07). The current standard. Canonical version always at:
    <https://datapackage.org/profiles/2.0/datapackage.json>

Read the appropriate schema when you need to understand which fields are valid in a
descriptor or validate one programmatically.
