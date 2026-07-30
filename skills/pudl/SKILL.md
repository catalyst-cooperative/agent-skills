---
name: pudl
description: >
  Explore and understand PUDL energy data: discover which tables exist, look up column
  meanings and usage warnings, and load Parquet files from S3 or a local directory.
  No PUDL Python package required. Use this skill whenever a user asks what PUDL data
  contains, wants to understand a specific table or column, asks about data quality or
  limitations, needs help loading data into a notebook or script, or wants to know
  which table covers a topic like electricity generation, utility financials, fuel
  costs, power plant locations, emissions, capacity factors, FERC financial data, or
  EIA survey data. Also use when the user mentions PUDL, Catalyst Cooperative energy
  data, or any of the specific data sources PUDL ingests (EIA-860, EIA-861, EIA-923,
  FERC Form 1, FERC Form 714, FERC EQR, EPA CEMS, EPA CAMD, etc.).
license: CC-BY-4.0
compatibility: |
  Required skills: datapackage
  Optional Python packages: polars >= 1.0 (preferred for DataFrame work), pandas >= 2.0
    with s3fs (only needed if using pandas for S3 access), markitdown[pdf,docx] (to
    convert downloaded PDF/Word blank forms and instructions to text)
metadata:
  - author: Catalyst Cooperative
  - email: hello@catalyst.coop
  - last-updated: 2026-07-30
---

# PUDL Data Explorer Guide

This skill is for **data users** who want to explore, understand, and load PUDL's
public energy data products. It assumes no access to the PUDL Python package or source
repository — only the publicly distributed data files and their metadata.

PUDL's primary outputs are Apache Parquet files, described by a Frictionless Data
Package descriptor. For generic descriptor-querying patterns (jq), use
the `datapackage` skill — this skill provides PUDL-specific knowledge layered on top.

Beyond the main Parquet outputs, PUDL also distributes raw per-form FERC Parquet data
(covering Forms 1/2/6/60/714, each with its own `datapackage.json`) and the FERC EQR
(partitioned Parquet, separate from the main build). These have different access
patterns and are not covered by the main Frictionless descriptor — see
[Data Access](./references/data-access.md) for the full picture.

## Workflow overview

Every step below is inexpensive and should happen by default whenever it's relevant to
the question at hand, not only when the user asks for it by name.

1. **Locate the metadata** — the primary PUDL descriptor (Parquet outputs) is at:

    - S3: `s3://pudl.catalyst.coop/nightly/pudl_parquet_datapackage.json`
    - HTTPS: `https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/pudl_parquet_datapackage.json`

    Raw per-form FERC data has its own `datapackage.json` in each form/era directory,
    e.g. `s3://pudl.catalyst.coop/nightly/ferc1_xbrl/datapackage.json` and
    `s3://pudl.catalyst.coop/nightly/ferc1_dbf/datapackage.json` — see
    [Raw per-form Parquet directories](./references/data-access.md#raw-per-form-parquet-directories)
    for the full list.

    The FERC EQR (Electric Quarterly Reports) is distributed separately due to its
    size, and only one version is publicly available at a time:

    - S3: `s3://pudl.catalyst.coop/ferceqr/ferceqr_parquet_datapackage.json`
    - HTTPS: `https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr/ferceqr_parquet_datapackage.json`

    For offline or development use, download all descriptors locally with:

    ```bash
    python scripts/fetch_descriptor.py
    ```

    This populates `assets/cache/`. The script is cache-aware — a cached file
    younger than a day is reused with no network call, so it's safe to run this
    every time you need a descriptor rather than checking `assets/cache/` yourself
    first. Pass `--force` to bypass the cache and refetch regardless of age (e.g. if
    you suspect PUDL's schema changed today and need the very latest copy).

    Raw input archives (for provenance) live at
    `s3://pudl.catalyst.coop/zenodo/<dataset>/<concrete-doi>/datapackage.json`.
    Prefer the cached S3 archive over the Zenodo website or API for raw metadata and
    file access. The source docs page usually gives a concept DOI for the whole dataset
    lineage; the S3 path uses a concrete DOI for one specific archived version. See
    [Data Quality and Context](./references/data-quality-and-context.md) for details.

1. **Query metadata selectively** — use `/datapackage` skill patterns (jq)
    to find relevant tables, read descriptions, and surface warnings.

    For "does PUDL have data on X" questions, don't stop at a match you already
    recognized by reputation — run a broader keyword sweep across relevant
    description/code fields first (for FERC accounts, see
    [Cross-referencing FERC Form 1 and Form 2 schedules and accounts](#cross-referencing-ferc-form-1-and-form-2-schedules-and-accounts);
    the same habit applies to other sources' `core_*__codes_*` tables). Flag it if
    an answer came from recalled knowledge rather than the sweep.

1. **Consult primary-source forms and instructions when metadata alone doesn't fully
    explain something** — don't wait for the user to ask for these by name. See
    [Data Sources: Blank forms and filer instructions](./references/data-sources.md#blank-forms-and-filer-instructions).

1. **Check table tier** — see [Data Quality and Context](./references/data-quality-and-context.md).
    Prefer `out_*` tables; warn users about `_core_*` tables.

1. **Check keys before joining tables** — if the task combines a FERC-sourced table
    with an EIA-sourced table (or any two tables at all), check `schema.foreignKeys`
    on each first, and route utility/plant joins through `utility_id_pudl` /
    `plant_id_pudl`, not through name-string matching. See
    [PUDL Datapackage Extensions: Joining PUDL tables](./references/metadata-and-querying.md#joining-pudl-tables-use-declared-foreign-keys-and-pudls-id-crosswalks).

1. **Check methodology before implementation details** — if the user is asking how
    PUDL cleans, imputes, allocates, reconciles, estimates, or models data, read
    [Methodology](./references/methodology.md) first and fetch the relevant public
    methodology page (append `.md` to the URL for your own reading — but when pointing
    the user to it, give them the plain `.html` link) before looking at source code,
    docstrings, or implementation details. Summarize the public methodology page and
    point the user to it. Only dive into code-level implementation after the user has
    seen that write-up or if no methodology page exists for the topic.

1. **Load the data, efficiently** — Loading data doesn't have to mean downloading an
    entire table. `SELECT ... LIMIT` in DuckDB, `pl.scan_parquet()` with
    `.select()`/`.filter()` before `.collect()` in polars, and a `columns=` argument in
    pandas all push the selection down to the Parquet reader itself. Treat sampling and
    down-selecting as the normal way to explore a table, not an optimization reserved
    for when a file turns out to be huge. You should estimate a table's size before a
    full, unfiltered load, and only load the full table if the job genuinely needs every
    row; see [Data Access](./references/data-access.md) for the loading patterns
    themselves.

## Reference index

- [Data Sources](./references/data-sources.md) — how to query the PUDL descriptor's own
    `sources` array (31 datasets, with short codes, names, licensing, and per-source
    documentation links), and where to find and read each source's blank forms and
    filer instructions; read when a user asks about a specific source dataset
    (EIA-860, FERC Form 714, EPA CEMS, etc.) or needs documentation links, when
    resolving a raw-archive S3 path and you need the short code and have to
    distinguish between a concept-DOI and a concrete-DOI, or whenever interpreting what
    a column, code, or schedule actually means.
- [Data Access](./references/data-access.md) — S3 paths, loading patterns
    (pandas/DuckDB/polars/pure SQL), raw per-form FERC Parquet locations, and EQR access;
    read whenever generating data-loading code or explaining how to access any PUDL output
- [PUDL Datapackage Extensions](./references/metadata-and-querying.md) — PUDL-specific
    additions to the standard datapackage schema: RST/docstring-formatted descriptions,
    per-resource provenance fields, the package-level unit registry, and how to join
    tables across FERC/EIA ID systems via `utility_id_pudl`/`plant_id_pudl`; read
    before querying `description` or other non-standard fields on a PUDL descriptor,
    and before joining any two PUDL tables (for generic descriptor-querying mechanics,
    use the `datapackage` skill instead)
- [Data Quality and Context](./references/data-quality-and-context.md) — table tier
    naming conventions (`out_*` vs `core_*` vs raw), warning types, and what each tier
    means for analysis reliability; read when a user asks about data quality, when choosing
    between table tiers, or when surfacing warnings before providing loading code
- [Methodology](./references/methodology.md) — index of PUDL's data processing and
    modeling methodology pages (entity resolution, timeseries imputation, ownership
    extraction); read when a user asks *how* PUDL cleans, reconciles, imputes,
    allocates, estimates, or models data. Fetch the specific public methodology page,
    summarize it, and point the user there before diving into implementation details
    from code or docstrings
- [FERC Electricity Accounts](./references/ferc-electricity-accounts.md) —
    complete hierarchical chart of FERC electric utility accounts (balance sheet, electric
    plant, operating revenue, O&M expenses) with account numbers and descriptions; read
    when interpreting FERC Form 1 financial data or when a user asks what a specific
    account number means — prefer querying `ferc_electricity_accounts.json` over reading this
    file
- [FERC Form 1 Schedules](./references/ferc1-schedules.md) — all 75 Form 1 schedules
    with titles, descriptions, and table mappings; read when a user references a schedule
    by number or name (e.g. "Schedule 301", "Page 400a", "plant in service schedule") —
    prefer querying `ferc1_schedules.json` over reading this file
- [ferc1_schedules.json](./assets/ferc1_schedules.json) — **query this first** for any
    FERC Form 1 schedule or table lookup; use jq to find
    schedules by keyword, account number, or PUDL table name without loading the full
    markdown into context
- [FERC Form 2 Schedules](./references/ferc2-schedules.md) — all 77 Form 2 schedules
    with titles, descriptions, and XBRL table mappings (Form 2 is not yet integrated into
    PUDL); read when a user references a Form 2 schedule or asks about natural gas
    pipeline financial or operational data — prefer querying `ferc2_schedules.json` over
    reading this file
- [ferc2_schedules.json](./assets/ferc2_schedules.json) — **query this first** for any
    FERC Form 2 schedule or table lookup; use jq to find
    schedules by keyword, account number, or XBRL table name without loading the full
    markdown into context
- [ferc_electricity_accounts.json](./assets/ferc_electricity_accounts.json) — **query this first** for any
    FERC Form 1 (electric utility) account number lookup; use jq to resolve account
    definitions and cross-reference with Form 1 schedules via the `ferc_accounts` array

## PUDL-specific constraints

- **License**: All PUDL data is published under the
    [Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/)
    license. Users may freely use, share, and adapt the data with attribution to
    Catalyst Cooperative.

- **Citation**: When a user asks how to cite PUDL, provide this reference:

    > Selvans, Z., Gosnell, C., Sharpe, A., Schira, Z., Lamb, K., Belfer, E., Xia, D.,
    > & Mazaitis, K. *The Public Utility Data Liberation (PUDL) Project* [Data set].
    > Catalyst Cooperative. <https://doi.org/10.5281/zenodo.3653158>

    BibTeX:

    ```bibtex
    @misc{pudl,
      author       = {Selvans, Zane and Gosnell, Christina and Sharpe, Austen and
                      Schira, Zachary and Lamb, Katherine and Belfer, Ella and
                      Xia, Dazhong and Mazaitis, Kathryn},
      title        = {The Public Utility Data Liberation (PUDL) Project},
      publisher    = {Catalyst Cooperative},
      doi          = {10.5281/zenodo.3653158},
      url          = {https://doi.org/10.5281/zenodo.3653158},
    }
    ```

- The S3 bucket `s3://pudl.catalyst.coop` is **free and publicly accessible** — no
    AWS credentials needed, and any ambient credentials (even invalid ones) should be
    explicitly bypassed rather than assumed absent.

- **DuckDB, pandas, and polars each need explicit setup to query this bucket
    reliably** — see
    [Data Access: DuckDB and S3](./references/data-access.md#duckdb-and-s3-required-setup)
    (`s3_url_style` plus clearing S3 credential settings; applies through `/query` too)
    and the pandas/polars sections below it (`storage_options` for anonymous access)
    for why each is needed.

- The Parquet path for a **core PUDL output table** is
    `s3://pudl.catalyst.coop/nightly/<table_name>.parquet`. Raw per-form FERC tables
    use a different path — see
    [Raw per-form Parquet directories](./references/data-access.md#raw-per-form-parquet-directories).

- **Always surface usage warnings** from the descriptor before providing loading code.

- **Methodology-first rule**: if a public methodology page exists for the topic the
    user is asking about, use it before inspecting implementation details. Code-level
    explanations are a follow-up step, not the default first response.

- **Prefer `out_*` tables** for analyst work. If a user asks about a topic without
    specifying a table, search metadata for `out_` tables first.

- **Use `uv` to install Python packages** — prefer `uv add <package>` over
    `pip install <package>`. `uv` is faster and installs into a virtual environment
    rather than globally. Fall back to `pip` only if `uv` is not available
    (`command -v uv` returns nothing) — and if you do, install into a project-local
    virtual environment (create one with `python -m venv .venv` if none exists), not
    the system/global Python. **`pip install --user` is not a safe fallback either**
    — it still writes into the user's global user-site packages, shared across every
    other project on their machine, rather than scoping the change to this task. If
    the working directory already has its own environment manager (pixi, poetry, an
    existing venv or conda env), install through that instead of introducing a second
    one.

- **PUDL's datapackage descriptors extend the standard schema** in several PUDL-specific
    ways: RST-formatted, docstring-style descriptions, per-resource provenance metadata,
    and a package-level unit registry. Read
    [PUDL Datapackage Extensions](./references/metadata-and-querying.md) before writing
    jq queries against `description` or other non-standard fields — it covers only
    what's unique to PUDL; for generic descriptor-querying mechanics, use the
    `datapackage` skill.

- **Prefer joining PUDL tables on ID columns over name-string columns**
    (`utility_name_ferc1`, `utility_name_eia`, plant names, etc.) — same-named
    entities across FERC and EIA are not guaranteed to be the same company. Route
    joins through `utility_id_pudl` / `plant_id_pudl` via the `core_pudl__assn_*`
    crosswalk tables, checking `schema.foreignKeys` first. Name matching is a
    legitimate fallback when no ID crosswalk is available, but treat its results as
    unverified until spot-checked. See
    [PUDL Datapackage Extensions: Joining PUDL tables](./references/metadata-and-querying.md#joining-pudl-tables-use-declared-foreign-keys-and-pudls-id-crosswalks).

### Cross-referencing FERC Form 1 and Form 2 schedules and accounts

Both `ferc1_schedules.json` and `ferc2_schedules.json` share the same schema. Each
record has a `ferc_accounts` array with the account numbers that schedule references,
pre-extracted for direct lookup. Use `description` for topical keyword search; use
`ferc_accounts` for account-number cross-referencing.

**Quick lookup patterns (jq):**

```bash
# Find all Form 1 schedules that reference a specific account number
jq '[.[] | select(.ferc_accounts[] == "182.3")] | .[] | {schedule, title}' \
    assets/ferc1_schedules.json

# Find all Form 2 schedules that reference a specific account number
jq '[.[] | select(.ferc_accounts[] == "489.2")] | .[] | {schedule, title}' \
    assets/ferc2_schedules.json

# Get all account definitions for a specific Form 1 schedule
SCHED="232"
jq --arg s "$SCHED" '.[] | select(.schedule == $s) | .ferc_accounts[]' \
    assets/ferc1_schedules.json |
xargs -I{} jq --arg a {} '.[] | select(.account == $a)' assets/ferc_electricity_accounts.json
```

**Joining across both files (jq):** load the accounts file with `--slurpfile` and use
`INDEX()` to build an account-number lookup, then join it against each schedule's
`ferc_accounts` array:

```bash
# Find PUDL tables and account definitions for a Form 1 topic (e.g. "regulatory assets")
jq --slurpfile accounts assets/ferc_electricity_accounts.json '
  ($accounts[0] | INDEX(.account)) as $acct_lookup
  | .[]
  | select(.description | test("regulatory asset"; "i"))
  | .schedule as $sched | .title as $title | .pudl_tables as $tables
  | .ferc_accounts[]
  | {schedule: $sched, title: $title, pudl_tables: $tables,
     account: ., account_description: $acct_lookup[.].description}
' assets/ferc1_schedules.json

# Find Form 2 XBRL tables for a topic (e.g. "storage") — single file, no join needed
jq '[.[] | select(.description | test("storage"; "i"))] |
    .[] | {schedule, title, xbrl_tables}' assets/ferc2_schedules.json
```

## Delegation

| User intent                        | Hand off to    |
| ---------------------------------- | -------------- |
| Query datapackage.json metadata    | `/datapackage` |
| Run SQL or NL queries against data | `/query`       |
