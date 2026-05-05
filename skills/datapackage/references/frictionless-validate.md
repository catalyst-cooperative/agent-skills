# Using `frictionless validate` to Explore Data Packages

The `frictionless` CLI can validate packages and individual resources, confirm
structural conformance, surface data quality errors, and infer schemas from raw files.
It is especially useful when encountering an unfamiliar datapackage.json in the wild:
even a quick validation run tells you whether the data matches what the descriptor
claims.

## Dependency check

```bash
command -v frictionless
```

If not found, install with uv:

- `uv tool install frictionless` — installs the CLI into an isolated tool environment
- `uvx frictionless validate ...` — run once without installing (slower on first run)

Parquet support requires fastparquet as an extra dependency:

- `uv tool install frictionless --with fastparquet`

Without `fastparquet`, Parquet resources report an installation error and the run exits
non-zero. Note that fastparquet has a known limitation with `date32` columns (see
[Storage backend behavior](#storage-backend-behavior)); the recommended Parquet workflow
suppresses all row-level artefacts with `--skip-errors byte-count,type-error,primary-key`.

## Basic usage

```bash
# Validate an entire package
frictionless validate path/to/datapackage.json

# Validate a single data file directly (frictionless infers the schema)
frictionless validate path/to/data.csv

# Validate one named resource within a package (skip the rest)
frictionless validate --resource-name stations datapackage.json
```

Exit code is `0` on success, non-zero on any validation failure. The default output
is a human-readable table. Always use `--json` when processing output programmatically.

## Machine-readable output

```bash
frictionless validate --json datapackage.json
```

The JSON structure:

```jsonc
{
  "valid": true,
  "stats": { "tasks": 2, "errors": 0, "warnings": 0, "seconds": 0.025 },
  "tasks": [
    {
      "name": "stations",
      "type": "table",          // "table" if rows were read; "file" if only existence checked
      "valid": true,
      "place": "stations.csv",
      "labels": ["station_id", ...],
      "stats": {
        "errors": 0,
        "md5": "...",
        "sha256": "...",
        "bytes": 401,
        "fields": 7,
        "rows": 5
      },
      "errors": []
    }
  ]
}
```

Key fields to extract:

- `valid` (top-level) — overall pass/fail
- `tasks[].type` — `"table"` means rows were read and checked; `"file"` means only
    file-level integrity was checked (see storage backend notes below)
- `tasks[].stats.rows` — how many rows were validated
- `tasks[].errors[]` — each error has `type`, `message`, `rowNumber`, `fieldNumber`

### Extracting errors in jq

```bash
frictionless validate --json datapackage.json \
    | jq '.tasks[] | select(.valid == false) | {name, errors: [.errors[] | {row: .rowNumber, field: .fieldNumber, type: .type, msg: .message}]}'
```

## Controlling validation scope

### Validate only N rows (fast spot check on large files)

```bash
frictionless validate --limit-rows 1000 datapackage.json
```

`--limit-rows` caps how many rows are actually read and validated. Use this for a quick
sanity check on large datasets where full validation would be slow.

### Cap error output (don't drown in 10,000 identical errors)

```bash
frictionless validate --limit-errors 20 datapackage.json
```

Default is 1000. If the first N errors all say the same thing, you've already learned
what you need. Lower this to keep output readable.

### Schema inference sample size

```bash
frictionless validate --sample-size 200 datapackage.json
```

`--sample-size` controls how many rows frictionless reads to *infer* field types when
no schema is declared. It does **not** limit which rows are validated — if a schema is
present, all rows are validated regardless of `--sample-size`. Raise it when type
inference is getting fields wrong (usually a sign of sparse or late-appearing values).

### Parallel resource validation

```bash
frictionless validate --parallel datapackage.json
```

Useful for packages with many resources. Validates each resource in a separate process.

## Spec version handling

```bash
frictionless validate --standards v1 datapackage.json
frictionless validate --standards v2 datapackage.json
```

The `--standards` flag signals which version of the spec to apply. In practice,
frictionless's content validation (type checking, constraint checking, foreign keys) is
largely version-agnostic. The main effect is on how the descriptor itself is parsed —
for example, whether `"profile"` or `"$schema"` is expected as the version declaration.

When you encounter an unknown descriptor in the wild: try `--standards v1` if the
descriptor has a `"profile"` key; `--standards v2` if it has `"$schema"`. If neither
is present, try both and compare.

## Adding extra checks

```bash
# Check for duplicate rows (not run by default)
frictionless validate --checks duplicate-row datapackage.json

# Check exact table dimensions
frictionless validate --checks "table-dimensions:numRows=5" stations.csv

# Combine: duplicate-row check plus dimension check
frictionless validate --checks "duplicate-row table-dimensions:numRows=150" datapackage.json
```

## Filtering error types

```bash
# Only surface type errors and constraint violations (ignore everything else)
frictionless validate --pick-errors "type-error,constraint-error" datapackage.json

# Descriptor-only validation for Parquet (suppress all fastparquet row-level artefacts)
frictionless validate --skip-errors byte-count,type-error,primary-key datapackage.json
```

Common error type codes:

| Code               | What it means                                              |
| ------------------ | ---------------------------------------------------------- |
| `type-error`       | Cell value doesn't match the declared field type           |
| `constraint-error` | Constraint violation (e.g. `minimum`, `pattern`)           |
| `unique-error`     | Unique constraint violated on a field                      |
| `primary-key`      | Primary key uniqueness violated                            |
| `foreign-key`      | Foreign key reference not found in the referenced resource |
| `blank-row`        | Row with all empty cells                                   |
| `duplicate-row`    | Identical row found earlier (only with `--checks`)         |
| `byte-count`       | File size doesn't match `bytes` in descriptor              |
| `hash-count`       | File hash doesn't match `hash` in descriptor               |
| `row-count`        | Row count doesn't match declared `rows` field              |
| `field-count`      | Number of fields doesn't match declared count              |

## Attaching an external schema

```bash
# Validate a raw file against a separately stored schema
frictionless validate --schema path/to/schema.json data.csv
```

The schema must be a Frictionless Table Schema JSON file (the value of the `"schema"`
key in a resource descriptor). Useful when you have a schema from a descriptor but want
to validate a standalone file, or when you want to test a schema against a new data
file before publishing.

## Inferring schemas from raw files

When you encounter a data file with no descriptor, use `describe` to infer a schema:

```bash
# Infer schema from a CSV file
frictionless describe --json data.csv
```

The output is a full resource descriptor with inferred field types. This is useful for:

- Bootstrapping a new descriptor from existing data
- Cross-checking that inferred types match what the publisher declared in their descriptor
- Quickly understanding the structure of an undescribed file

```bash
# Increase sample size for better inference on sparse data
frictionless describe --sample-size 500 --json data.csv
```

## Storage backend behavior

Not all backends are equal. The `type` field in JSON output reveals what frictionless
actually checked:

| Backend | Recommended flags                                 | `type` in output | Row-level validation   | Integrity check (bytes/hash) |
| ------- | ------------------------------------------------- | ---------------- | ---------------------- | ---------------------------- |
| CSV     | *(none)*                                          | `table`          | Yes — all rows         | Yes                          |
| Parquet | `--skip-errors byte-count,type-error,primary-key` | `table`          | No — errors suppressed | No (fastparquet limitation)  |
| SQLite  | *(none)*                                          | `file`           | No — existence only    | Yes (file-level)             |
| DuckDB  | *(none)*                                          | `file`           | No — existence only    | Yes (file-level)             |

When you see `"type": "file"` in the output, frictionless confirmed the file exists and
checked file-level integrity, but did **not** read or validate any rows or field types.
To validate the tabular content of SQLite and DuckDB resources, use DuckDB SQL queries
directly (see `storage-backends.md`).

**Parquet: use descriptor-only validation.** fastparquet (frictionless's Parquet backend)
has two problems that prevent meaningful row-level validation:

1. `type-error` / `primary-key` cascade — fastparquet misreads `date32` columns,
    returning raw nanosecond epoch integers instead of calendar dates. frictionless
    cannot validate these integers against `"type": "date"` fields, and the resulting
    null-parse cascade causes every `(id, null)` pair to look like a primary-key
    violation.
1. `byte-count` — fastparquet doesn't expose the raw file byte count that frictionless
    needs for the `bytes` integrity check.

Note: `--limit-rows 0` does **not** help — fastparquet loads the entire file into memory
when it opens it, so frictionless receives all rows regardless of the limit.

The correct approach is to run frictionless in descriptor-only mode by suppressing all
three row-level artefacts:

```bash
frictionless validate --skip-errors byte-count,type-error,primary-key datapackage.json
```

**This is not a Parquet format problem.** The Parquet files correctly encode date columns
as `INT32` with a `DATE` logical type annotation. Every conforming Parquet reader
(pyarrow, polars, DuckDB) handles this correctly. To validate Parquet data content, use
DuckDB or polars directly (see `storage-backends.md`).

## Diagnosing an unknown descriptor

When encountering an unfamiliar `datapackage.json` for the first time, this sequence
gives a useful picture with minimal cost:

```bash
# 1. Quick structural check — does frictionless understand the descriptor?
frictionless validate --limit-rows 0 --json datapackage.json

# 2. Spot-check the first 100 rows of each resource
frictionless validate --limit-rows 100 --limit-errors 20 --json datapackage.json

# 3. Full validation (potentially slow on large datasets)
frictionless validate --parallel --limit-errors 50 --json datapackage.json \
    | jq '.tasks[] | select(.valid == false) | {name, error_count: .stats.errors}'
```

Step 1 (`--limit-rows 0`) effectively validates the descriptor structure and checks
file accessibility without reading any data rows — fast even for remote or large files.

## Working with remote descriptors

frictionless can validate remote packages directly:

```bash
frictionless validate https://example.com/path/to/datapackage.json
```

For large remote packages, always use `--limit-rows` to avoid downloading and
validating the entire dataset:

```bash
frictionless validate --limit-rows 50 --json \
    https://s3.amazonaws.com/bucket/datapackage.json
```
