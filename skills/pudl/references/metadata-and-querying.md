# PUDL Datapackage Extensions

## Use this when

- Reading or querying `description` fields on a PUDL resource or field.
- Looking up a resource's provenance (source dataset, license, documentation link).
- Interpreting a field's `unit` value.
- Deciding whether something you're seeing in a PUDL descriptor is a PUDL-specific
    extension or standard Frictionless Data Package structure.

For the generic mechanics of locating a descriptor, querying it with jq or DuckDB, and
loading the data it describes, use the `datapackage` skill — this reference covers only
what PUDL adds on top of that standard.

---

## Descriptions: RST, docstrings, and structured sections

**PUDL descriptions are ReStructuredText (RST), not plain text or Markdown.** When
reading `description` fields, apply these rules:

- Sphinx inline roles like `:py:class:`, `:py:func:`, `:py:attr:` — extract the name
    inside the backticks (e.g. `` :py:func:`pudl.helpers.fix_eia_na` `` → `fix_eia_na`).
- `` :ref:`label` `` cross-references do not resolve to accessible URLs; treat them as
    internal documentation pointers only — do not attempt to construct a URL.
- Underlined headers (e.g. `Usage Warnings` followed by a line of `^^^^^^^^^^^^^^`) mark
    RST sections within the description body. See
    [Data Quality and Context](./data-quality-and-context.md) for what the `Usage Warnings`
    section means and how to surface it.

**Resource descriptions also follow a docstring convention**: every PUDL resource
description begins with a single-line summary, followed by a blank line, followed by a
longer body (identical to the Python docstring convention). The body is often a
structured RST field list (`Most-recent data:`, `Processing:`, `Source:`, `Primary key:`)
followed by RST sections such as `Usage Warnings` or `Additional Details`. Some
descriptions are hundreds of words long. **To decide whether a table is relevant without
loading the full description into context, read only the first line first** — if the
summary looks promising, then fetch the full description.

**With jq (local file):**

```bash
# List all resource names with just the first line of their description
jq -r '.resources[] | "\(.name): \(.description | split("\n")[0])"' "$PKG"

# Scan first-line summaries for a keyword (e.g. "generator")
jq -r '.resources[] | select(.description | split("\n")[0] | test("generator"; "i"))
     | "\(.name): \(.description | split("\n")[0])"' "$PKG"

# Once a table looks relevant, fetch the full description
jq -r '.resources[] | select(.name == "core_eia860__scd_generators") | .description' "$PKG"
```

**With DuckDB (local or remote):**

```sql
-- List resource names with just the first-line summary
SELECT
    r->>'$.name' AS name,
    split_part(r->>'$.description', chr(10), 1) AS summary
FROM (SELECT unnest(resources) AS r FROM read_json('pudl_parquet_datapackage.json', format='auto'));

-- Filter by keyword in the first-line summary only
SELECT
    r->>'$.name' AS name,
    split_part(r->>'$.description', chr(10), 1) AS summary
FROM (SELECT unnest(resources) AS r FROM read_json('pudl_parquet_datapackage.json', format='auto'))
WHERE summary ILIKE '%generator%';

-- Once a table looks relevant, fetch its full description
SELECT r->>'$.description' AS description
FROM (SELECT unnest(resources) AS r FROM read_json('pudl_parquet_datapackage.json', format='auto'))
WHERE r->>'$.name' = 'core_eia860__scd_generators';
```

---

## Per-resource provenance: `sources`

Each resource carries a `sources` array (a standard Frictionless field, but PUDL
populates it with dataset-specific provenance beyond the spec's minimal `name`/`title`):

```jsonc
{
  "name": "eia860",
  "title": "EIA Form 860 -- Annual Electric Generator Report",
  "concept_doi": "https://doi.org/10.5281/zenodo.4127026",
  "license_raw": { "name": "other-pd", "title": "U.S. Government Works", "path": "..." },
  "license_pudl": { "name": "CC-BY-4.0", "title": "Creative Commons Attribution 4.0", "path": "..." },
  "documentation": "https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia860.html",
}
```

- `concept_doi` — the Zenodo **concept DOI** for the raw source dataset's archive
    lineage (not a specific version). See
    [Data Quality and Context](./data-quality-and-context.md#raw-input-archives-zenodo)
    for how this relates to the concrete-DOI S3 archive path.
- `license_raw` vs `license_pudl` — the license the *original* agency published the data
    under, versus the license PUDL republishes it under (almost always CC-BY-4.0). Cite
    `license_pudl` when telling a user how they may use PUDL's output; mention
    `license_raw` only if they ask about the original source's terms.
- `documentation` — a direct link to that source's PUDL docs page. Prefer this over
    constructing a docs URL from the short code.

```bash
# Get provenance for every source dataset behind the current descriptor
jq -r '.resources[0].sources[] | "\(.name): \(.documentation)"' "$PKG"

# Find the license PUDL republishes a specific source under
jq '.resources[] | select(.name == "core_eia860__cooling_equipment") | .sources[0].license_pudl' "$PKG"
```

---

## Package-level unit registry: `unit_registry`

The top-level descriptor carries a `unit_registry` object defining non-SI units used in
`schema.fields[].unit` values, in [Pint](https://pint.readthedocs.io/) format:

```jsonc
{
  "format": "pint",
  "definitions": ["MMBtu = 1e6 * BTU = MMBTU", "Mcf = 1000 * cubic_foot", "USD = [currency]"]
}
```

If a field's `unit` (e.g. `MMBtu`, `Mcf`, `VAr`) isn't a familiar SI unit, look it up here
rather than guessing:

```bash
# Show all custom unit definitions
jq -r '.unit_registry.definitions[]' "$PKG"

# Find the definition for a specific unit
jq -r --arg u "MMBtu" '.unit_registry.definitions[] | select(startswith($u + " ="))' "$PKG"
```

---

## Other field-level extensions

Some schema fields carry a `geometry_format` key (e.g. on spatial/geometry columns) in
addition to the standard `name`/`type`/`description`/`constraints`/`unit`. Treat it, like
any other non-standard field, as informational metadata describing how to interpret the
column's values — not as an error or a sign of a malformed descriptor.
