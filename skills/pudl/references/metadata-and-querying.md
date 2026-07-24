# PUDL Datapackage Extensions

## Use this when

- Reading or querying `description` fields on a PUDL resource or field.
- Looking up a resource's provenance (source dataset, license, documentation link).
- Interpreting a field's `unit` value.
- Deciding whether something you're seeing in a PUDL descriptor is a PUDL-specific
    extension or standard Frictionless Data Package structure.

For the generic mechanics of locating a descriptor, querying it with jq, and loading the
data it describes, use the `datapackage` skill — this reference covers only what PUDL
adds on top of that standard.

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

```bash
# List all resource names with just the first line of their description
jq -r '.resources[] | "\(.name): \(.description | split("\n")[0])"' "$PKG"

# Scan first-line summaries for a keyword (e.g. "generator")
jq -r '.resources[] | select(.description | split("\n")[0] | test("generator"; "i"))
     | "\(.name): \(.description | split("\n")[0])"' "$PKG"

# Once a table looks relevant, fetch the full description
jq -r '.resources[] | select(.name == "core_eia860__scd_generators") | .description' "$PKG"
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
    constructing a docs URL from the short code. **Append `.md` only when *you* are
    fetching the page** resulting in a path ending in `.html.md` (PUDL publishes an
    LLM-optimized markdown mirror of every docs page). Examples:

    ```text
    field value:        https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html
    fetch this (mirror): https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html.md   ✓
    not this:            https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.md        ✗ 404s
    ```

    If you share this link with the user, give them the plain `.html` URL from
    the field — the `.html.md` version is for your own reading, not theirs.

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

To look up what an unfamiliar `unit` value (e.g. `MMBtu`, `Mcf`, `VAr`) means:

```bash
# Show all custom unit definitions
jq -r '.unit_registry.definitions[]' "$PKG"

# Find the definition for a specific unit
jq -r --arg u "MMBtu" '.unit_registry.definitions[] | select(startswith($u + " ="))' "$PKG"
```

**Most `unit` values need no lookup at all.** Things like `MW`, `MWh`, `foot`, `acre`,
`gallon / minute`, and `percent` are units [Pint](https://pint.readthedocs.io/) already
understands out of the box from a plain `pint.UnitRegistry()` — `unit_registry` exists
only for the smaller set of non-standard abbreviations Pint doesn't know natively:
`MMBtu`, `Mcf`, `MMcf`, `TBtu`, `VAr`, `MVAr`, and the currency unit `USD` (Pint has no
built-in notion of currency at all). Notably, the oil-and-gas convention of doubling the
prefix letter for "million" (`MM` in `MMcf`, `MMBtu`) is **not** the same as SI's single
`M` for "mega" — a real source of confusion if you guess a conversion instead of
resolving it against the registry.

### Using units safely when combining data

Two fields can look combinable — same rough topic, plausible-looking column names — and
still be in different units. Before summing, averaging, or joining quantity columns
drawn from more than one field or resource, check each one's `unit`. Don't assume a
matching or similar-looking column name implies a matching unit.

Load all of `unit_registry.definitions` into your Pint registry unconditionally, every
time — don't try to first judge whether a given field's unit "looks standard enough" to
skip it. The definitions are few, defining them is essentially free, and none of them
collide with anything Pint already knows: there's no upside to guessing which fields
need the lookup when you can just always have it available.

**Worked failure mode**: `unit_registry` defines both `Mcf` (thousand cubic feet) and
`MMcf` (million cubic feet) for natural gas volumes — a 1,000x difference. Add a
quantity reported in `Mcf` to one reported in `MMcf` without converting first, and the
total is silently off by a factor of 1,000 — no error, no warning, just a wrong number
that still looks plausible.

```bash
# Check the unit for every field you're about to combine, on every resource involved
jq '.resources[] | select(.name == "TABLE_A") | .schema.fields[] | select(.name == "FIELD_A") | {name, unit}' "$PKG"
jq '.resources[] | select(.name == "TABLE_B") | .schema.fields[] | select(.name == "FIELD_B") | {name, unit}' "$PKG"
```

If the two `unit` values differ, convert onto a common basis before combining. Build the
Pint registry once, up front, from the default registry plus all of
`unit_registry.definitions` (as above), then let Pint track the conversion:

```python
import pint

ureg = pint.UnitRegistry()  # already parses MW, foot, gallon / minute, percent, ...
for definition in descriptor["unit_registry"]["definitions"]:
    ureg.define(definition)  # adds MMBtu, Mcf, MMcf, TBtu, VAr, MVAr, USD on top

gas_a = 1_200 * ureg.Mcf  # table A reports in Mcf
gas_b = 1.5 * ureg.MMcf  # table B reports in MMcf

# Wrong: adding raw magnitudes treats 1.5 (MMcf) as if it were 1.5 Mcf
wrong_total = gas_a.magnitude + gas_b.magnitude  # 1_201.5 -- silently ~1,000x too low

# Right: convert onto a common unit first, then combine
right_total = gas_a + gas_b.to(ureg.Mcf)  # 2_700 Mcf
```

---

---

## Joining PUDL tables: use declared foreign keys, and PUDL's ID crosswalks

**Before joining two PUDL resources, check `schema.foreignKeys` on each — don't join
on matching column names, and never join on a name/label field when an ID field is
available.** This is the general `datapackage` skill rule (see its
[Metadata Querying: Joining resources](../../datapackage/references/metadata-querying.md#joining-resources-primary-keys-and-foreign-keys)),
and it applies with extra force in PUDL because the same real-world entity (a
utility, a plant) is reported under **different ID systems by different source
agencies** — FERC assigns its own utility IDs, EIA assigns its own, and they don't
match.

```bash
# Check a table's declared primary key and foreign keys before joining
jq '.resources[] | select(.name == "out_ferc1__yearly_income_statements_sched114") | {primaryKey: .schema.primaryKey, foreignKeys: .schema.foreignKeys}' "$PKG"
```

PUDL resolves the multi-agency-ID problem with a **crosswalk hub**:
`utility_id_pudl` (and `plant_id_pudl` for plants) is PUDL's own surrogate ID, and
`core_pudl__assn_*` tables declare the links from each source system's ID to it —
for example `out_ferc1__yearly_income_statements_sched114.utility_id_ferc1` has a
declared foreign key to `core_pudl__assn_ferc1_pudl_utilities.utility_id_ferc1`,
and `core_pudl__assn_eia_pudl_utilities.utility_id_pudl` links to the same
`core_pudl__entity_utilities_pudl` hub. To join a FERC-sourced table to an
EIA-sourced table, route through `utility_id_pudl`, not through utility name
strings:

```
out_ferc1__...(utility_id_ferc1)
  → core_pudl__assn_ferc1_pudl_utilities (utility_id_ferc1 → utility_id_pudl)
  → core_pudl__assn_eia_pudl_utilities (utility_id_pudl → utility_id_eia)
  → core_eia861__... (utility_id_eia)
```

**Declared `foreignKeys` coverage varies by table and can change over time** — a
table may carry a `utility_id_eia` or `plant_id_eia` column with no `foreignKeys`
entry pointing it at the corresponding crosswalk table, even though it's the same
key. Don't take an undeclared link as evidence no relationship exists: check for it
with jq first, but if it's absent, still prefer joining on the shared `utility_id_*`
/ `plant_id_*` column over a name column — the ID system is the reliable part even
when the formal declaration is missing — and treat the result as unverified until
you spot-check it (e.g. confirm a handful of joined rows resolve to the entity you
expect).

**Worked failure mode**: searching a table by utility *name* (e.g.
`utility_name_eia ILIKE '%tri-state%'`) can return an entirely unrelated company —
"Tri-State Electric Member Corp," a Georgia/Tennessee/North Carolina cooperative,
is a false-positive match for a search meant to find Colorado's "Tri-State
Generation and Transmission Association." Going through the ID crosswalk
(`utility_id_ferc1` → `utility_id_pudl` → `utility_id_eia`) instead of name
matching returns the correct entity and would have caught the mismatch immediately,
since the crosswalked EIA ID and the name-matched EIA ID are different numbers.

## Other field-level extensions

Some schema fields carry a `geometry_format` key (e.g. on spatial/geometry columns) in
addition to the standard `name`/`type`/`description`/`constraints`/`unit`. Treat it, like
any other non-standard field, as informational metadata describing how to interpret the
column's values — not as an error or a sign of a malformed descriptor.
