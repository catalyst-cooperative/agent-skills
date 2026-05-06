---
icon: lucide/book-open
---

# Clanker Skills

This repository contains shareable [agent skills](https://agentskills.io) developed by [Catalyst Cooperative](https://catalyst.coop).
Skills selectively provide context to coding agents, giving them specialized knowledge and workflows.
This repository is aimed at the PUDL maintainers who are developing these skills for use by the public.
To install one of the skills below your system, use [`npx skills`](https://www.npmjs.com/package/skills).
For example:

```bash
npx skills add catalyst-cooperative/agent-skills --skill <skill-name>
```

Many other agent skills can be found on [skills.sh](https://skills.sh/)

## Available skills

### datapackage

Explore and query any dataset described by a [Frictionless Data Package](https://datapackage.org/) descriptor (`datapackage.json`).
Covers schema inspection, validation, metadata querying with `jq` and DuckDB, and reading data from CSV, Parquet, DuckDB, and SQLite backends.

Useful for any agent working with tabular datasets that follow the Frictionless spec — not just PUDL.

### pudl

Guides your agent through [PUDL](https://github.com/catalyst-cooperative/pudl) metadata for interactive exploration.
Can be used to query and load the referenced data into dataframes in a Jupyter or Marimo note.
Covers discovering which tables exist, understanding column meanings and caveats, and loading data from S3 or a local PUDL download.
For human-readable PUDL data documentation, see the [PUDL Data Documentation](https://docs.catalyst.coop/pudl/en/latest/data/index.html).

Aimed at energy analysts and data users who want to work with PUDL open data products.

### pudl-dev

!!! warning

    The `pudl-dev` skill is half-baked should not be considered ready for widespread use.

Guidance for agents being used by contributors to the PUDL open source project.
Covers the contributor workflow, local ETL and Dagster development, schema and metadata changes, dbt models, and validation.

Aimed at PUDL core contributors working on code and data pipeline changes.

## Installing skills for development

A number of repository level skills intended for use in development in this repo are specified in `skills-lock.json`.
They can be installed into `.agents/skills/` using:

```bash
pixi run install-skills
```

Agent harnesses that support the skills spec (Claude Code, Gemini CLI, etc.) will pick them up automatically from that directory.
Claude should pick them up from the symlink at `.claude/skills` which points at `.agents/skills`.

## Agent sandbox

The repository includes a containerized development sandbox that lets coding agents run with full, unrestricted access — safely isolated from your host system.
See the [Agent Sandbox](agent-sandbox.md) page for setup instructions.
