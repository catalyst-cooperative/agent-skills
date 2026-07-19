---
icon: lucide/database
---

# Using the PUDL Skill

The `pudl` skill gives your coding agent working knowledge of the
[Public Utility Data Liberation (PUDL)](https://docs.catalyst.coop/pudl) project's data
products — what tables exist, what their columns mean, which data-quality caveats
apply, and how to actually load the data. It's aimed at energy analysts and other data
users, not at people developing PUDL itself.

You don't need the `pudl` Python package installed, and you don't need a checkout of
the PUDL source repository. The skill works directly against PUDL's publicly
distributed Parquet files and their metadata.

## Installing

The skill is layered on top of the generic [`datapackage`](datapackage-skill.md) skill,
so install both:

```bash
npx skills add catalyst-cooperative/agent-skills --skill datapackage
npx skills add catalyst-cooperative/agent-skills --skill pudl
```

See the [main README](https://github.com/catalyst-cooperative/agent-skills#installing)
for other installation methods.

## What it can help with

- **Finding the right table.** Ask about a topic (coal plant retirements, hourly
    generation, utility financials) and the agent searches PUDL's live metadata rather
    than guessing table names.
- **Understanding a column.** Field descriptions, units, and any usage warnings baked
    into the metadata itself — including whether a column is safe to use as a join key
    or to sum across years.
- **Judging data quality and stability.** PUDL tables come in tiers (`out_*`, `core_*`,
    `_core_*`, and raw) with different stability guarantees; the skill knows which to
    recommend and when to warn you off a preliminary table.
- **FERC Form 1 and Form 2 lookups.** Resolving a schedule number ("Schedule 301"), a
    FERC account number, or a topic to the PUDL tables that cover it.
- **Loading data.** Working pandas, DuckDB, or polars code to read Parquet directly
    from PUDL's public S3 bucket (no credentials needed) or a local download, plus
    locations for the FERC historical DuckDB/SQLite databases and the FERC EQR dataset.
- **Pointing you at methodology.** For anything involving cleaning, imputation,
    allocation, or entity resolution, the agent looks at PUDL's own methodology
    write-ups before explaining implementation details.

## Example prompts

### Finding data on a topic

> "I'm trying to understand what data PUDL has on coal plant retirements. What tables
> would I look at, and are there any caveats I should know about?"

The agent searches the metadata for matching tables, explains what each one contains,
and surfaces any usage warnings before recommending one — preferring `out_*` tables
over lower-tier alternatives.

### Loading data

> "I want to load `out_eia923__yearly_generation` in a script. I don't have PUDL
> installed locally — can I get it from S3?"

The agent returns working pandas or DuckDB code reading straight from the public S3
bucket, with no PUDL package import required, and shows column projection for large
tables.

### Understanding a column

> "What does the `unit_id_pudl` column mean, and should I use it as a join key across
> PUDL versions?"

The agent looks up the field's description and warning text, and explains — in plain
language — why that particular ID isn't guaranteed to be stable long-term.

### FERC Form 1 lookups

> "Which FERC Form 1 schedule covers plant-in-service accounting, and which PUDL
> tables does it map to?"

The agent resolves the schedule by title or account number and reports the PUDL table
names it has been integrated into (or tells you plainly if it hasn't been integrated
yet).

## What it won't do

- Replace [PUDL's own data documentation](https://docs.catalyst.coop/pudl/en/nightly/data_access.html) —
    the skill is a starting point for exploration, not a substitute for reading the
    docs on a table you're about to build an analysis on.
- Run the PUDL ETL pipeline or require the `pudl` Python package — it only works with
    already-published data and metadata.
- Modify any data. It's a read-only exploration and loading aid.

## Learn more

- [PUDL data documentation](https://docs.catalyst.coop/pudl/en/nightly/data_access.html)
- [PUDL skill source](https://github.com/catalyst-cooperative/agent-skills/tree/main/skills/pudl)
- [Using the Datapackage Skill](datapackage-skill.md) — the generic layer this skill builds on
