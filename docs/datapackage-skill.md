---
icon: lucide/package
---

# Using the Datapackage Skill

The `datapackage` skill gives your coding agent working knowledge of the
[Frictionless Data Package](https://datapackage.org/) standard — a widely used,
lightweight way of describing a collection of tabular data files (`datapackage.json`).
Unlike the `pudl` skill, it's completely generic: it works for any dataset that ships a
conforming descriptor, regardless of who published it or what the data is about.

If you work with datasets that come with a `datapackage.json` — or you're building
one — this skill is useful on its own. It's also the foundation the `pudl` skill layers
PUDL-specific knowledge on top of; see [Using the PUDL Skill](pudl-skill.md) if that's
what brought you here.

## Installing

```bash
npx skills add catalyst-cooperative/agent-skills -s datapackage
```

Querying metadata requires [`jq`](https://jqlang.org/) (>= 1.8). Loading data works with
whatever's already in your environment: pandas or polars if you have Python set up, or
DuckDB directly with no Python required at all (via the companion `attach-db` and
`query` skills from [duckdb/duckdb-skills](https://github.com/duckdb/duckdb-skills), for
pure-SQL workflows). Validating a package's structural integrity is optional and uses the
[`frictionless`](https://framework.frictionlessdata.io/) CLI if it's installed. See the
[main README](https://github.com/catalyst-cooperative/agent-skills#installing) for other
installation methods.

## What it can help with

- **Discovering what's in a dataset.** Lists resources (tables) and their descriptions
    by querying the descriptor selectively — never by loading the whole (potentially
    huge) file into context.
- **Understanding a column.** Field names, types, units, and any usage warnings a
    publisher embedded in the metadata.
- **Handling both spec versions.** Detects and correctly parses both Data Package v1
    (`profile`, singular `role`) and v2 (`$schema`, `roles` array) descriptors.
- **Joining tables safely.** Reads `schema.primaryKey`/`schema.foreignKeys` to find real
    join columns instead of guessing from similar-looking column names.
- **Loading data.** Working pandas, polars, or DuckDB code for CSV, Parquet, DuckDB, or
    SQLite files — whichever fits the format, size, and whether you want a Python
    dataframe or a SQL session — including figuring out the right table name inside a
    `.duckdb`/`.sqlite` file when no standard field says so.
- **Validating a package.** Uses the `frictionless` CLI (if installed) to check that
    the data actually matches what the descriptor claims — useful for diagnosing an
    unfamiliar descriptor found in the wild.

## Example prompts

=== "Discovering what's in a dataset"

    > "I've got a `datapackage.json` at `~/data/census/datapackage.json` — what tables
    > does this dataset contain, and what are they about?"

    The agent queries the descriptor selectively with `jq`, listing resource names and
    descriptions without ever loading the raw file into context.

=== "Understanding a column"

    > "What does the `population_estimate` column mean, and is there anything I should
    > watch out for before using it?"

    The agent reads the field's description and surfaces any usage warnings verbatim,
    explaining the practical implication before you build an analysis on top of it.

=== "Loading data"

    > "This dataset ships its tables as Parquet files. Can you load the `sales` table
    > into a dataframe?"

    The agent picks an appropriate tool (DuckDB, pandas, or polars, depending on the
    format and likely size) and returns working, copy-pasteable code.

=== "Joining tables safely"

    > "I need to combine the `orders` and `customers` tables — what's the right join
    > column?"

    The agent reads `schema.primaryKey`/`foreignKeys` from the descriptor to find the
    declared relationship rather than guessing from column names, and tells you plainly
    if the descriptor doesn't declare one.

## What it won't do

- Provide domain expertise about what the data actually means beyond what the
    descriptor itself documents — pair it with a domain-specific skill (like `pudl`)
    for that.
- Load or validate an entire dataset by default. Data loading and validation only
    happen when you ask for them, since remote or large files can be slow or costly.
- Read the descriptor *itself* with Python (`json.load`) — metadata queries always use
    `jq`, so the full `datapackage.json` never has to load into memory or context. This
    doesn't apply to the actual data: pandas and polars are fully supported, ordinary
    ways to load it once you know which resource you need.

## Learn more

- [Frictionless Data Package specification](https://datapackage.org/)
- [Skill source](https://github.com/catalyst-cooperative/agent-skills/tree/main/skills/datapackage)
- [Using the PUDL Skill](pudl-skill.md) — PUDL-specific knowledge layered on top
