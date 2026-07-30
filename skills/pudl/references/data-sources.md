# PUDL Data Sources

Use this reference when looking up the short code for a raw input dataset, finding the
documentation page for a specific source, or resolving which datasets PUDL ingests.

> **For agent use, query the top-level `sources` array of the PUDL descriptor with jq.**

---

## Where this data lives

PUDL's `pudl_parquet_datapackage.json` descriptor carries a top-level `sources` array
listing every dataset PUDL ingests, each with source-level provenance, licensing, and a
docs link. Locate or fetch it the same way as any other PUDL metadata — see step 1 of
the workflow in `SKILL.md`, or run `python scripts/fetch_descriptor.py` for an offline
copy cached at `assets/cache/pudl_parquet_datapackage.json`. Querying this array
directly keeps this reference synced with PUDL's nightly build automatically, with no
separate file to keep up to date.

## The `sources` schema

`sources` itself is a standard Frictionless Data Package field — it also appears
per-resource (see
[PUDL Datapackage Extensions](./metadata-and-querying.md#per-resource-provenance-sources)).
The **rich schema PUDL populates it with** is the PUDL-specific part, layered on top of
the bare `name`/`title` the spec requires. Every record in the top-level array has:

| Field           | Meaning                                                                                                                                        |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`          | short code identifier (e.g. `eia860`) — the same short code used elsewhere in PUDL                                                             |
| `title`         | human-readable full name of the source                                                                                                         |
| `path`          | the source's homepage URL (not a data file)                                                                                                    |
| `description`   | one-sentence description of what the source contains                                                                                           |
| `email`         | contact email for the source agency, if known                                                                                                  |
| `keywords`      | list of search terms associated with the source                                                                                                |
| `concept_doi`   | Zenodo **concept DOI** for the raw input archive's lineage as a whole — see [Zenodo and DOI conventions](#zenodo-and-doi-conventions)          |
| `license_raw`   | the license the *original* agency published the data under                                                                                     |
| `license_pudl`  | the license PUDL republishes the data under (almost always CC-BY-4.0)                                                                          |
| `contributors`  | list of contributor/publisher records (usually just Catalyst Cooperative)                                                                      |
| `doi`           | DOI for this dataset within PUDL's own citation record                                                                                         |
| `documentation` | link to the source's PUDL docs page (`.html`); `null` if no docs page exists yet — **append `.md` to fetch the LLM-optimized version instead** |

**Example record** (`eia860`, `keywords` truncated for brevity):

```json
{
  "name": "eia860",
  "title": "EIA Form 860 -- Annual Electric Generator Report",
  "path": "https://www.eia.gov/electricity/data/eia860",
  "email": "infoelectric@eia.gov",
  "description": "US Energy Information Administration (EIA) Form 860 data for electric power plants with 1 megawatt or greater combined nameplate capacity.",
  "keywords": ["eia860", "generators", "capacity", "fuel", "..."],
  "concept_doi": "https://doi.org/10.5281/zenodo.4127026",
  "license_raw": { "name": "other-pd", "title": "U.S. Government Works", "path": "..." },
  "license_pudl": { "name": "CC-BY-4.0", "title": "Creative Commons Attribution 4.0", "path": "..." },
  "contributors": [{ "name": "catalyst-cooperative", "title": "Catalyst Cooperative", "roles": ["publisher"] }],
  "doi": "https://doi.org/10.5281/zenodo.20380530",
  "documentation": "https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia860.html"
}
```

There are currently 31 entries. Two are worth knowing about so they don't confuse a
keyword search or "list all sources" request: `pudl` refers to PUDL-derived data itself
(entity resolution and other PUDL-authored tables), not an external source it ingests;
`mshamines` (Mine Safety and Health Administration mines) doesn't yet have a
`documentation` page. Both are otherwise ordinary, queryable entries.

The **`name`** field is the short code used in:

- Cached raw-archive paths: `s3://pudl.catalyst.coop/zenodo/<name>/<concrete-doi>/`
- Table name prefixes (second component): e.g. `out_eia923__generation`
- FERC XBRL descriptor filenames: e.g. `ferc1_xbrl_datapackage.json`

---

## jq examples

```bash
PKG=assets/cache/pudl_parquet_datapackage.json

# Find a source by keyword in the title or keyword list
jq '[.sources[] | select(.title | test("balancing authority"; "i"))]' "$PKG"
jq '[.sources[] | select(.keywords[]? | test("emissions"; "i")) | {name, title}]' "$PKG"

# Get the short code for a specific source
jq '.sources[] | select(.title | test("CEMS"; "i")) | .name' "$PKG"

# Get the docs URL for a known short code
jq -r '.sources[] | select(.name == "ferc1") | .documentation' "$PKG"

# List all sources with no docs page yet
jq '[.sources[] | select(.documentation == null) | .name]' "$PKG"

# List every source's short code and title
jq -r '.sources[] | "\(.name)\t\(.title)"' "$PKG"
```

---

## Reading per-source documentation

Each source with a `documentation` link has a page describing:

- What the form collects and who files it
- Years and frequency of coverage
- Known data quality issues and gaps
- How PUDL processes and integrates it

**Always append `.md` to the `documentation` URL before fetching it yourself.** PUDL
publishes an LLM-optimized markdown mirror of every docs page (the `llms.txt`
convention), and agents don't discover it automatically unless told — the raw field
always points at the `.html` page. This `.html.md` URL is for *your* reading only —
if you share the link with the user, give them the plain `.html` URL from the field.
See [PUDL Datapackage Extensions: Per-resource provenance](./metadata-and-querying.md#per-resource-provenance-sources)
for exactly how that append works.

**Exception: fetch the raw `.html` page (not `.md`) for the "Download additional
documentation" links** — see
[Blank forms and filer instructions](#blank-forms-and-filer-instructions) below for why.

```bash
# Fetch a source's docs page (markdown version)
jq -r '.sources[] | select(.name == "eia923") | .documentation + ".md"' "$PKG" | xargs curl -s
```

Or use the `WebFetch` tool if available in your environment.

## Blank forms and filer instructions

Table and column descriptions in the descriptor summarize what data *contains*, but
they rarely explain what a filer was actually asked to report. For that, go to the
source: the blank form and filer instructions a respondent used to fill it out. These
define a code's exact scope, what a schedule line item is asking for, or how a term was
defined in a given filing year — context that's often impossible to infer from a column
name or description alone, and that changes as forms are revised over the years.

**Check for these whenever you're about to explain what something in the data means,**
not only when the user names the form and asks for it directly — most users won't know
these documents exist. If the source has a `documentation` page, look for a "Download
additional documentation" section on it before falling back to a description-only
answer.

### Finding them

Fetch the **raw `.html`** docs page for this section, not the `.md` mirror. The `.md`
mirror does list the same files, but as relative links that don't resolve to a working
URL; the `.html` page's links resolve to `https://docs.catalyst.coop/pudl/en/nightly/_downloads/<hash>/<filename>`,
which does work. This is the one place on the docs site where the `.md`-first rule
above should not be followed.

```bash
# Find the "Download additional documentation" section for a source
curl -s "$(jq -r '.sources[] | select(.name == "ferc1") | .documentation' "$PKG")" |
    grep -A50 'id="download-additional-documentation"'
```

Not every source has this section — most FERC forms and some EIA forms do; many
sources don't, and some (e.g. `ferc2` at the time of writing) don't have a
`documentation` page at all yet. If a source has neither, say so rather than guessing
at or constructing a URL; point the user to the source agency's own page instead (the
`path` field on that source's `sources` record).

Python's `urllib` returns `403 Forbidden` fetching from `docs.catalyst.coop` with its
default `User-Agent` string — override it with any other value. `curl` and `requests`
both work fine with their own defaults.

### Choosing an edition

Multiple editions accumulate over the years as a form is revised. **Prefer the newest
edition** — it's the most likely to describe current reporting practice — with one
twist: recent FERC forms are published as plain `.html`, while older editions (and most
EIA instructions) are PDFs. When a newer edition is easier to read (HTML) than an older
one (PDF), that's an extra reason to prefer it, not just its recency.

### Reading them

HTML editions are plain text — fetch and read them directly, same as any other web page.
PDFs and Word documents (`.docx`, occasionally used for cover memos or errata) need
converting to text first.
Download the file, then convert it with [markitdown](https://github.com/microsoft/markitdown)
(`uv pip install "markitdown[pdf,docx]"` if not already available — the base package
alone doesn't include PDF or docx support; add other extras the same way for other
formats you run into):

```bash
curl -s -o ferc1_blank_2019-12-31.pdf \
    "https://docs.catalyst.coop/pudl/en/nightly/_downloads/fd9ba713087c5c0be586ac51ba237731/ferc1_blank_2019-12-31.pdf"
markitdown ferc1_blank_2019-12-31.pdf > ferc1_blank_2019-12-31.md
```

These forms often run 50-100+ pages; skim the converted markdown or search it for the
schedule, line item, or term you need rather than reading it front to back.

### Zenodo and DOI conventions

When working with raw input archives, distinguish between the two DOI types:

- `concept_doi` — read directly from the `sources` record, no docs page needed — refers
    to the dataset's archive lineage as a whole.
- The S3 cache uses the **concrete DOI** for one specific archived version, which is a
    different value and can't be derived from `concept_doi` alone.

Give users `concept_doi` as a stable public citation link, then use the cached S3
archive (see
[Data Access](./data-access.md#raw-input-archives-zenodo)) for actual metadata lookup
or raw file access — list the dataset's S3 prefix and use whichever concrete-DOI
directory is present, since it may not match the concept DOI.

Prefer the cached S3 `datapackage.json` over the Zenodo website or API when you need to:

- inspect source metadata
- find file names and checksums
- look up licensing or provenance fields
- access the raw files themselves

The Zenodo website is mainly useful when a user wants to visit the source archive on the
web, cite it by DOI, or access a very old version that is no longer present in the S3
cache.
