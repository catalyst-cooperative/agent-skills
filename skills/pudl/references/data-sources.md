# PUDL Data Sources

Use this reference when looking up the short code for a raw input dataset, finding the
documentation page for a specific source, or resolving which datasets PUDL ingests.

> **For agent use, query [`data_sources.json`](../assets/data_sources.json)**
> **with jq — this file does not embed the full source table.**

---

## Querying the machine-readable index

Use [`data_sources.json`](../assets/data_sources.json) for all programmatic lookups.
Fields: `short_code`, `full_name`, `docs_url`.

The **short code** is the identifier used in:

- Cached raw-archive paths: `s3://pudl.catalyst.coop/zenodo/<short_code>/<concrete-doi>/`
- Table name prefixes (second component): e.g. `out_eia923__generation`
- FERC XBRL descriptor filenames: e.g. `ferc1_xbrl_datapackage.json`

### jq examples

```bash
# Find a source by keyword in the full name
jq '[.[] | select(.full_name | test("balancing authority"; "i"))]' assets/data_sources.json

# Get the short code for a specific source
jq '.[] | select(.full_name | test("CEMS"; "i")) | .short_code' assets/data_sources.json

# Get the docs URL for a known short code
jq '.[] | select(.short_code == "ferc1") | .docs_url' assets/data_sources.json

# List all sources with no docs page yet
jq '[.[] | select(.docs_url == null) | .short_code]' assets/data_sources.json
```

These four jq examples cover every lookup this file supports.

---

## Refreshing this list

The authoritative source of available datasets is the S3 listing. Run this to see the
current dataset codes:

```bash
aws s3 ls --no-sign-request s3://pudl.catalyst.coop/zenodo/ | awk '{print $2}' | tr -d '/'
```

When a new short code appears there that isn't in `data_sources.json`, add a record to
the JSON asset directly — there is no separate generated table to keep in sync.

---

## Reading per-source documentation

Each source with a docs URL has a page describing:

- What the form collects and who files it
- Years and frequency of coverage
- Known data quality issues and gaps
- How PUDL processes and integrates it

The docs index is at:
<https://docs.catalyst.coop/pudl/en/nightly/data_sources/index.html.md>

Fetch a source page when the user asks about a specific data source and the JSON sidecar
does not provide enough context:

```bash
curl -s "$(jq -r '.[] | select(.short_code == "eia923") | .docs_url' assets/data_sources.json)"
```

Or use the `WebFetch` tool if available in your environment.

### Zenodo and DOI conventions

When working with raw input archives, distinguish between the two DOI types:

- The docs page usually lists a **concept DOI** for the dataset lineage as a whole.
- The S3 cache uses the **concrete DOI** for one specific archived version.

Agents should usually use the docs page to understand the source and give users a
stable public link, then use the cached S3 archive for actual metadata lookup or raw
file access.

Prefer the cached S3 `datapackage.json` over the Zenodo website or API when you need to:

- inspect source metadata
- find file names and checksums
- look up licensing or provenance fields
- access the raw files themselves

The Zenodo website is mainly useful when a user wants to visit the source archive on the
web, cite it by DOI, or access a very old version that is no longer present in the S3
cache.

---

## Shape of the data

`data_sources.json` is a flat array of records like these two (illustrative only — query
the JSON for the full, current list of ~29 sources):

```json
[
  {
    "short_code": "eia860",
    "full_name": "EIA Form 860 – Annual Electric Generator Report",
    "docs_url": "https://docs.catalyst.coop/pudl/en/nightly/data_sources/eia860.html.md"
  },
  {
    "short_code": "ferc2",
    "full_name": "FERC Form 2 – Annual Report of Major Natural Gas Companies",
    "docs_url": null
  }
]
```

A `null` `docs_url` means that source has no dedicated documentation page yet.
