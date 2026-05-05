# Metadata Querying

## Use this when

- Discovering which resources (tables) a dataset contains.
- Looking up what a resource or field means before loading data.
- Reading descriptions to understand data provenance, processing notes, and caveats.
- Searching for a column by name or topic across all resources.

In this skill, metadata discovery is **jq-first**. Prefer jq for descriptor metadata,
and only fall back to DuckDB or Python when jq cannot do the task cleanly (for
example: remote-only access without download, or complex transforms that would be
fragile in jq) and those tools are available.

---

## Spec reference

The Frictionless Data Package v2.0 specification and its JSON Schema are at
<https://datapackage.org/>. The JSON Schema itself (useful for validation) is at:
<https://datapackage.org/profiles/2.0/datapackage.json>

The spec is intentionally permissive: it defines a set of standard fields but allows
implementors to add non-standard keys anywhere — at the package, resource, or field
level. When you encounter unrecognized keys (like `unit`, `warning`, `bytes`, `hash`,
or source-specific metadata), treat them as informative extensions, not errors.

**Non-tabular resources**: not all resources have a `schema`. A resource may describe
an opaque file (PDF, ZIP, CSV without column metadata) and omit `schema.fields`
entirely. When `schema` is absent, the resource is still valid — just treat it as a
file reference rather than a queryable table.

**Integrity fields**: real-world descriptors often include `bytes` (file size in bytes)
and `hash` (checksum) on each resource. The `hash` value is usually in
`algorithm:hex` format (e.g. `"md5:abc123..."` or `"sha256:def456..."`); if no prefix
is present, assume MD5. For small files, use these to verify a download. For large
files (hundreds of MB or more), hashing is slow — check `bytes` first as a quick
sanity check, and only verify the hash if you suspect corruption.

```bash
# Find which resources have hashes
jq '.resources[] | select(.hash != null) | {name, bytes, hash}' "$PKG"

# Check hash of a downloaded file (macOS — strip any "md5:" prefix before comparing)
md5 stations.csv

# Check hash (Linux)
md5sum stations.csv
```

---

## Golden rule: never load the full datapackage.json into context

A `datapackage.json` can be megabytes with hundreds of resources and thousands of
fields. Always query it selectively — extract only the slice you need.

Use jq by default for descriptor metadata queries. If jq is unavailable or clearly
unsuitable for a specific metadata task, fallback to DuckDB or Python is acceptable.
Use DuckDB primarily for querying the data files referenced by resource `path`.

---

## Workflow

1. **Locate the descriptor** — find or download `datapackage.json` and note its base
    URL if remote (needed to resolve relative resource paths).
1. **Identify candidate resources** — search by name or description keyword.
1. **Read the resource description** — it contains source notes, primary key
    conventions, caveats, and processing history. Read it fully before presenting.
1. **Read column descriptions** for the specific columns the user needs.
1. **Confirm the data file path** — the `path` field is either a relative path
    (resolve against the descriptor's base directory or base URL) or an absolute URL.
1. **Load the data** *(only if the user asks)* — see
    [`storage-backends.md`](storage-backends.md).

---

## Step 1: Locate the descriptor

Check in this order:

1. **User-provided path** — the user may have a local file or know the URL.
1. **Alongside the data files** — `datapackage.json` is conventionally placed in the
    same directory as the data files it describes.
1. **Published URL** — dataset publishers often host the descriptor at a stable HTTPS
    URL. Check the dataset's README or documentation.

**Multiple descriptor files**: the spec requires the filename `datapackage.json`, but
in practice a directory may contain several descriptors (e.g.
`pudl_parquet_datapackage.json`, `ferc1_xbrl_datapackage.json`) associated with
different datasets. Treat each as a separate package.

**Remote descriptors and path resolution**: if you download a remote `datapackage.json`,
store its original base URL. Resource `path` values may be relative (e.g.
`my_table.parquet`) and must be resolved against that base URL, not the local download
directory. For example, if the descriptor was at
`https://example.com/data/datapackage.json` and a resource has `path: my_table.parquet`, the full data URL is `https://example.com/data/my_table.parquet`.

```bash
# Download and record the base URL
BASE_URL="https://example.com/data"
curl -O "$BASE_URL/datapackage.json"
PKG=datapackage.json

# Resolve a resource path to its full URL
jq -r '.resources[] | select(.name == "my_table") | .path' "$PKG"
# → "my_table.parquet"  (prepend $BASE_URL/ to get the full URL)
```

**Version checking**: before using a descriptor, verify it matches the data you have.
If the descriptor contains hash or byte-size information for resources, check them:

```bash
# Look for hash or bytes fields on resources (non-standard but common)
jq '.resources[] | {name, hash, bytes}' "$PKG"
```

Store the local path in `PKG` for reuse in queries below.

---

## Steps 2-5: Query the descriptor

Use **jq** by default for descriptor metadata queries so the workflow stays consistent
and easy to debug. If jq is unavailable or the query is impractical in jq, use
DuckDB or Python as a fallback.

---

## Steps 2–5: jq (local files only)

jq is the best default for selective querying of a local JSON file. It reads only what
you ask for and requires no additional setup. **jq cannot fetch over HTTPS** — if the
descriptor is remote, download it first with `curl -O <URL>`, then point jq at the
local file. If downloading is not feasible, DuckDB is a reasonable fallback.

### Step 2: Identify candidate resources

```bash
# Count total number of resources
jq '.resources | length' "$PKG"

# List all resource names
jq -r '.resources[].name' "$PKG"

# List resource names and their file formats
jq -r '.resources[] | "\(.name)\t\(.format // "unknown")"' "$PKG"

# Find resources whose name contains a keyword
jq -r '.resources[] | select(.name | test("generation"; "i")) | .name' "$PKG"

# Find resources whose description contains a keyword
jq '.resources[] | select(.description | test("capacity factor"; "i")) | {name, description: .description[:300]}' "$PKG"
```

### Step 3: Read resource and field descriptions

The spec is permissive — resources often carry extra non-spec fields beyond `name`,
`path`, `description`, and `schema`. Explore openly:

```bash
# Full description for one resource (includes processing notes, primary key, caveats)
jq -r '.resources[] | select(.name == "my_table") | .description' "$PKG"

# See all keys present on a resource (not just spec-defined ones)
jq '.resources[] | select(.name == "my_table") | keys' "$PKG"

# See all non-schema fields on a resource
jq '.resources[] | select(.name == "my_table") | del(.schema)' "$PKG"
```

Fields are also permissive — in addition to `name`, `description`, and `type`, a
field may carry extra metadata such as `unit`, `constraints`, `warning`, or
dataset-specific annotations. Always explore the full field object:

```bash
# Column names for a resource
jq -r '.resources[] | select(.name == "my_table") | .schema.fields[].name' "$PKG"

# All metadata for every field (not just name and description)
jq '.resources[] | select(.name == "my_table") | .schema.fields[]' "$PKG"

# Column names, descriptions, and units (unit may be absent on some fields)
jq '.resources[] | select(.name == "my_table") | .schema.fields[] | {name, description, unit}' "$PKG"

# Find fields that have a unit defined
jq '.resources[] | select(.name == "my_table") | .schema.fields[] | select(.unit != null) | {name, unit}' "$PKG"

# Find fields that carry a non-standard warning annotation
jq '.resources[] | select(.name == "my_table") | .schema.fields[] | select(.warning != null) | {name, warning}' "$PKG"

# See all keys used across all fields in a resource (reveals non-spec extensions)
jq '[.resources[] | select(.name == "my_table") | .schema.fields[] | keys[]] | unique' "$PKG"

# Find all resources that contain a specific column name
jq '.resources[] | {table: .name, fields: [.schema.fields[] | select(.name == "plant_id_eia")]} | select(.fields | length > 0)' "$PKG"
```

Package-level metadata follows the same pattern:

```bash
# See all top-level fields (excluding the potentially huge resources array)
jq 'del(.resources)' "$PKG"

# Or just the keys present at the top level
jq 'keys' "$PKG"
```

### Steps 4–5: Confirm the path, then load

```bash
# Data file path for a resource (may be a relative path or a URL)
jq -r '.resources[] | select(.name == "my_table") | .path' "$PKG"

# List resource names and their paths
jq -r '.resources[] | "\(.name)\t\(.path)"' "$PKG"
```

If the path is relative, prepend `$BASE_URL/` (recorded in Step 1). Then load —
see [`storage-backends.md`](storage-backends.md).

---

## Step 5 handoff: default to DuckDB for data queries

Once jq has identified the resource path, switch to DuckDB for the actual data query.
Keep these concerns separate:

- jq: default for descriptor metadata (`resources`, `schema`, descriptions, paths)
- DuckDB: default for table/file contents (and optional metadata fallback when needed)

```bash
# Step 4 in jq: get the resource path
REL_PATH=$(jq -r '.resources[] | select(.name == "my_table") | .path' "$PKG")

# Resolve local path (if relative) and query data with DuckDB
duckdb -c "SELECT * FROM read_parquet('$REL_PATH') LIMIT 10"
duckdb -c "SELECT * FROM read_csv('$REL_PATH') LIMIT 10"
```

For `.duckdb` and `.sqlite` resources, follow the attach-and-query patterns in
[`storage-backends.md`](storage-backends.md).
