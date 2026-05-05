# Datapackage Dev Maintainer Guide

This file is for repository maintainers only. It is not part of installed skill
content and should not be referenced from distributed skill docs.

## Scope

Use this guide when updating development fixtures, regeneration scripts, or test
inputs for the datapackage skill.

## Example corpus

Development fixtures live under `dev/skills/datapackage/assets/examples/`.
They provide parallel v1 and v2 datapackage descriptors across four storage
backends (CSV, Parquet, DuckDB, SQLite) so tests can validate equivalent
workflows across formats.

All fixture sets use the same weather-station dataset (5 stations, 30 daily
readings), which keeps backend and schema comparisons deterministic.

### v1 fixture layout

`dev/skills/datapackage/assets/examples/v1/`

| Directory  | Format  | Profile (package level) | Notable v1 patterns                                      |
| ---------- | ------- | ----------------------- | -------------------------------------------------------- |
| `csv/`     | CSV     | `tabular-data-package`  | Resources declare `"profile": "tabular-data-resource"`   |
| `parquet/` | Parquet | `data-package`          | Community pattern: `mediatype: application/parquet`      |
| `duckdb/`  | DuckDB  | `data-package`          | Community extension: `duckdb_table` key on each resource |
| `sqlite/`  | SQLite  | `data-package`          | Community extension: `sqlite_table` key on each resource |

### v2 fixture layout

`dev/skills/datapackage/assets/examples/v2/`

| Directory  | Format  | `$schema` declared | Notable v2 patterns                                         |
| ---------- | ------- | ------------------ | ----------------------------------------------------------- |
| `csv/`     | CSV     | yes                | `contributors[].roles` is an array; `version` field present |
| `parquet/` | Parquet | yes                | Same community Parquet pattern as v1                        |
| `duckdb/`  | DuckDB  | yes                | Same `duckdb_table` community extension as v1               |
| `sqlite/`  | SQLite  | yes                | Same `sqlite_table` community extension as v1               |

Each directory contains a `datapackage.json` descriptor and its backing data
file(s). The row-level data is intentionally identical across all fixture
directories; only descriptor structure and metadata conventions vary.

### v1 vs v2 descriptor differences to preserve

- **Version declaration**: v1 uses `"profile": "tabular-data-package"` or
    `"profile": "data-package"`; v2 uses
    `"$schema": "https://datapackage.org/profiles/2.0/datapackage.json"`.
- **Contributors**: v1 uses `"role": "author"` (string); v2 uses
    `"roles": ["author"]` (array).
- **`version` / `created` fields**: present in v2; omitted from v1.
- **Resource profile field**: v1 CSV resources use
    `"profile": "tabular-data-resource"`; v2 omits this field.

## Regeneration

When fixture generation logic changes, regenerate the example corpus:

```bash
pixi run python dev/skills/datapackage/scripts/generate_examples.py
pixi run prek run pretty-format-json --all-files
```

Then re-run datapackage tests:

```bash
pixi run test-datapackage
```

## Guardrails

- Keep distributed skill docs free of references to dev-only paths and scripts.
- If runtime agent guidance genuinely depends on an artifact, move that artifact
    into distributed `skills/datapackage/` content first.
