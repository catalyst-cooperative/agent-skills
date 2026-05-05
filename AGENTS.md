# AGENTS.md

> Canonical source note: `AGENTS.md` is the single source of truth for repository-level agent guidance. `CLAUDE.md` is a symlink to this file (not a separate guidance document).

## Project Overview

This repository contains shareable agent skills — reusable, installable prompts that give agents specialized knowledge and workflows.
Skills live under `skills/`, each providing distributed agent-facing guidance and assets.
Development-only tests, generators, and other validation artifacts live under `dev/skills/`.

## Distribution Boundary

Everything under `skills/<skill_name>/` is shipped with installed skills, including `SKILL.md`, `references/`, `assets/`, and (when present) `scripts/`.
Do not mention repository-internal dev paths, test suites, or example-generation scripts in distributed skill content (for example, anything under `dev/skills/`).
If guidance needs those artifacts at runtime, move the required artifacts into the distributed skill first.

Use `ALL_CAPS.md` only for repository standards or canonical interface files such
as `AGENTS.md`, `README.md`, and `SKILL.md`. Use kebab-case for other markdown
documents.

## Repository Layout

```
agent-skills/
├── skills/
│   ├── datapackage/     # Generic Frictionless Data Package exploration skill
│   │   ├── SKILL.md           # Skill descriptor (YAML front matter) + usage guide
│   │   ├── assets/            # Distributed JSON schemas and skill assets
│   │   ├── references/        # frictionless-validate.md, metadata-querying.md, storage-backends.md
│   │   ├── scripts/           # utility scripts (Python or shell) for use at runtime by agents
│   │   └── evals/             # Skill evaluation cases
│   ├── pudl/            # PUDL data-user skill (read tables, explore metadata)
│   └── pudl-dev/        # PUDL developer skill (ETL, schema, CI, dbt, pytest)
├── docs/                # Zensical documentation site source (markdown)
├── .github/workflows/   # CI: test-datapackage.yml, docs.yml
├── pyproject.toml       # Pixi workspace: dependencies, tasks, tool config
├── skills-lock.json     # Pinned external skill versions and hashes
└── .pre-commit-config.yaml
```

External skills (from `skills-lock.json`) are installed into `.agents/skills/`, which is git-ignored. Install them with `pixi run install-skills`.

## Environment

This repository uses **pixi** for dependency and environment management.
All commands must be run through pixi.

```bash
pixi run <command>          # run any command in the pixi environment
pixi run test-datapackage   # run the datapackage test suite
pixi run install-skills     # install vendored external skills into .agents/
```

Never use `pip install` or `conda install` directly. Add new dependencies with
`pixi add <package>` and commit the updated `pyproject.toml` and `pixi.lock`.

## Linting and Formatting

Call the underlying tools directly — not through `prek`. Pre-commit hooks exist as a safety net for humans at commit time; they are slow, require files to be staged, and run across the entire repository.
Direct invocation is faster, targets only the files you changed, and works on new files without staging them first.

**Determine which files to check from `git status`, not from memory.**
Any file may be modified by a formatter, a merge, or another tool after you last ran a check:

```bash
git status --short   # modified, staged, and new untracked files
```

Run the appropriate tool for every file type that appears in the output.

### Python

```bash
pixi run ruff check --fix path/to/file.py   # lint and auto-fix
pixi run ruff format path/to/file.py        # format
pixi run ty check                           # type checking (always whole project)
```

This repository targets modern Python only; do not add `from __future__ import annotations`.

### JSON

```bash
pixi run prek run pretty-format-json --files path/to/file.json
```

JSON is the exception: the `pretty-format-json` hook uses non-obvious args (`--autofix --indent=4 --no-sort-keys`) so routing through prek is simpler than replicating them.
Python code that writes JSON must use `indent=4` and the default `ensure_ascii=True` — do **not** pass `ensure_ascii=False`.

### YAML

```bash
pixi run prettier --write path/to/file.yaml   # format
pixi run actionlint path/to/workflow.yml      # GitHub Actions files only
```

### Markdown

```bash
pixi run mdformat path/to/file.md          # format
pixi run markdownlint-cli2 path/to/file.md # lint
```

`mdformat` is configured with `wrap = "no"` — it does not add hard line breaks.
Do not add hard line breaks manually in markdown files.

### TOML

```bash
pixi run taplo format path/to/file.toml
```

## Reference/Test Synchronization

Reference markdown examples are executable specifications for agent behavior.
When you update a documented workflow, keep its corresponding tests in sync so
guidance remains reliable.

When editing a documented workflow snippet:

1. Update the snippet in `skills/<skill>/references/`.
1. Update the relevant tests in `dev/skills/<skill>/tests/`.
1. Run the relevant skill test suite.

Tests should validate the documented workflow pattern (API shape, operation,
and result form), not incidental fixture details unless those details are
explicitly part of the instructions.

## Datapackage Skill Rules

Datapackage repository-maintainer notes (example corpus layout, regeneration
workflow, and other dev-only context) are documented in
`dev/skills/datapackage/datapackage-dev-guide.md`.

### Editing code examples in reference files

Every code block in `skills/datapackage/references/` is covered by a test in `dev/skills/datapackage/tests/`.
After editing any code example in a reference file, run the full test suite to confirm the example still works:

```bash
pixi run test-datapackage
```

The mapping from reference file to test file is:

| Reference file                           | Test file                 |
| ---------------------------------------- | ------------------------- |
| `frictionless-validate.md`               | `test_frictionless.py`    |
| `metadata-querying.md` (jq patterns)     | `test_metadata_jq.py`     |
| `metadata-querying.md` (DuckDB patterns) | `test_metadata_duckdb.py` |
| `storage-backends.md`                    | `test_backends.py`        |

### Adding new examples to reference files

When you add a new code example to any reference file, add a corresponding test to the appropriate test file that runs the pattern against the example data.
Check `dev/skills/datapackage/tests/conftest.py` for shared constants (row counts, column names, path roots) before adding new helpers.

### Editing `generate_examples.py`

After modifying `dev/skills/datapackage/scripts/generate_examples.py`, regenerate all example datasets and verify nothing regressed:

```bash
python dev/skills/datapackage/scripts/generate_examples.py
pixi run test-datapackage
pixi run prek run pretty-format-json --all-files  # reformat generated descriptors
```

## Skill Authoring Guidelines

Each skill directory follows this layout:

```
skills/<name>/
├── SKILL.md       # Required: YAML front matter descriptor + usage guide
├── assets/        # Schemas, cached data, and distributed skill assets
├── references/    # Long-form reference docs (markdown)
├── scripts/       # Utility scripts (Python or shell)
└── evals/         # Evaluation cases for measuring skill quality

dev/skills/<name>/
├── assets/examples/ # Generated example datasets and fixtures
├── scripts/         # Dev-only utility scripts (Python or shell)
└── tests/           # pytest suite verifying reference code examples
```

- Reference documents in `references/` are the authoritative source for patterns.
    Test files exist solely to validate those patterns; keep them in sync.
- Files marked `linguist-generated=true` in `.gitattributes` are generated outputs — never hand-edit them.
    Regenerate them using the script that produced them.
    When it is not obvious which script to run, check `.gitattributes` first to confirm a file is generated, then trace the `linguist-generated` path back to its generator script.
- When adding a test suite to a skill, add a corresponding GitHub Actions workflow under `.github/workflows/` with a `paths` filter scoped to that skill's directory.
- External skills are managed through `skills-lock.json`, not added to the repo directly.
    They land in `.agents/skills/` (git-ignored) after `pixi run install-skills`.

## Additional Guidelines

- **Explicit dependencies**: Every tool or runtime invoked directly must be listed as an explicit dependency in `pyproject.toml`.
    Do not rely on transitive dependencies — they are an implementation detail of another package and can disappear without warning if that package changes.
    Add missing dependencies with `pixi add <package>`.
- **File size limit**: The `check-added-large-files` hook rejects files over 800 KB.
    The generated DuckDB example files are ~780 KB — avoid making them larger.
- **Typos**: The `typos` checker excludes `skills/*/assets/` because upstream data may contain canonical misspellings.
    Do not add spurious typo suppressions elsewhere.
- **Line endings**: LF only. The `mixed-line-ending` hook enforces this; do not commit CRLF line endings.
- **Shell scripts**: Write POSIX-compatible shell. The `shellcheck` hook validates all shell scripts.
- **Python type checking**: `ty` runs as a pre-commit hook locally but is skipped in CI (`ci: skip: [ty-check]` in `.pre-commit-config.yaml`).
    Always run it locally before committing Python changes.
- **Documentation**: The `docs/` site is built with Zensical and deployed by CI on push to `main`.
    Edit source files in `docs/` (markdown); never commit the `site/` build output.
