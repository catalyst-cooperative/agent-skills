# Data Quality and Context

## Use this when

- Explaining what a data source is (EIA-923, FERC Form 1, etc.)
- Interpreting table naming conventions and what they imply about data quality.
- Understanding what kinds of warnings appear in metadata and why they matter.
- Pointing a user to the right public documentation or data catalog.

---

## Table and asset naming conventions

PUDL asset names follow this pattern (double underscore separates source from the rest):

```text
{layer}_{source}__{asset_type}_{asset_name}
```

### Layers

| Prefix   | Layer        | What it contains                                                                                                      |
| -------- | ------------ | --------------------------------------------------------------------------------------------------------------------- |
| `raw_`   | Raw          | Direct extractions from source files — pickle files, not analyst-facing                                               |
| `core_`  | Core         | Cleaned, normalized, well-modeled building blocks with logical primary keys and tidy structure                        |
| `out_`   | Output       | Wide, analyst-ready tables — joined foreign keys, decoded codes, **start here for analysis**                          |
| `_core_` | Intermediate | Private processing steps, not intended for users; may appear in outputs temporarily but can be removed without notice |

`source` is the dataset short code (e.g. `eia860`, `ferc1`, `epacems`). In the output
layer it is optional, since some assets combine multiple sources. Use `pudl` as the
source when an asset was derived by PUDL contributors (e.g. entity-resolution tables).
For the full list of source codes see [Data Sources](./data-sources.md).

### Asset types (core layer)

The `asset_type` component describes the data model role of the table:

| Type                            | Meaning                                                          | Example                                 |
| ------------------------------- | ---------------------------------------------------------------- | --------------------------------------- |
| `assn`                          | Association — links entities across datasets                     | `core_pudl__assn_plants_eia`            |
| `changelog`                     | Tracks first-reported change in entity attributes over time      | `core_eia860m__changelog_generators`    |
| `codes`                         | Categorical code lookup table (from source data dictionaries)    | `core_eia__codes_balancing_authorities` |
| `entity`                        | Static entity attributes (e.g. plant location, boiler ownership) | `core_eia__entity_boilers`              |
| `scd`                           | Slowly changing dimension — attributes that rarely change        | `core_eia860__scd_generators`           |
| `yearly` / `monthly` / `hourly` | Time-series measurements at the stated frequency                 | `core_ferc1__yearly_plant_in_service`   |

In the output layer, `asset_type` often describes reporting frequency and is optional.
Examples: `out_eia923__monthly_generation`, `out_ferc714__hourly_planning_area_demand`.

---

## Usage warnings — what they mean and why they matter

Many tables carry explicit usage warnings in their metadata descriptions. These are not
generic disclaimers — they document **known, specific limitations** that affect
real analyses. The warning section of a resource description starts with the header
"Usage Warnings".

### Common warning types

#### Unstable IDs

> "WARNING: This ID is not guaranteed to be static long term as the input data and
> algorithm may evolve over time."

Applies to `unit_id_pudl` and other algorithmically assigned identifiers. Don't use
these as durable foreign keys across PUDL versions.

#### Temporary tables

> "Published only temporarily and may be removed without notice."

Applies to all `_core_*` tables. These are intermediate products that haven't been
harvested into the main normalized tables yet.

#### Not yet harvested / duplicate data

> "This table has not been harvested with other EIA 923 or 860 data. The same variables
> present in this table may show up in other `_core_*` tables in other years."

Means the same phenomenon is recorded in multiple tables — joining them naively would
double-count.

#### Methodology caveats

Some `out_*` tables contain derived or imputed values. The description will say
"derived from" or reference a methodology doc. Point users to
<https://docs.catalyst.coop/methodology> for details.

### How to surface warnings to users

Always quote the relevant warning text verbatim — don't paraphrase it. Explain the
practical implication in plain language. For example:

> The metadata for `out_eia923__generation` notes that `unit_id_pudl` is not stable
> across PUDL versions. This means if you're joining data across different PUDL
> releases — or building a pipeline that updates over time — you shouldn't use this
> column as a join key without checking whether it changed.

---

## Data sources overview

PUDL integrates 31 public datasets from U.S. government agencies and research
organizations (a couple are PUDL-derived rather than external sources — see
[Data Sources](./data-sources.md) for details). For the full list of dataset short
codes, full names, and per-source documentation links, see
[Data Sources](./data-sources.md).

The most commonly accessed sources:

| Short code | Description                                                               |
| ---------- | ------------------------------------------------------------------------- |
| `eia860`   | Annual electric generator report — plant and generator characteristics    |
| `eia861`   | Annual electric power industry report — utility sales, customers, revenue |
| `eia923`   | Power plant operations report — fuel consumption, generation, heat rates  |
| `eia930`   | Hourly and daily balancing authority operations                           |
| `ferc1`    | Annual report of major electric utilities — financial statements          |
| `ferc714`  | Annual electric balancing authority area and planning area report         |
| `ferceqr`  | Electric Quarterly Report — bulk power market contracts                   |
| `epacems`  | Hourly continuous emissions monitoring — SO₂, NOₓ, CO₂, heat input        |

---

## Public documentation links

Use these when you need to explain source data or point users to authoritative
methodology docs. **Do not reference internal `docs/` or `src/` paths** — they are
only available to people with the source repository.

| Resource                           | URL                                                                                |
| ---------------------------------- | ---------------------------------------------------------------------------------- |
| PUDL documentation home            | <https://docs.catalyst.coop/pudl/>                                                 |
| Data access guide                  | <https://docs.catalyst.coop/pudl/en/nightly/data_access.html>                      |
| Data dictionary (tables + columns) | <https://docs.catalyst.coop/pudl/en/nightly/data_dictionaries/pudl_db.html>        |
| Usage warnings reference           | <https://docs.catalyst.coop/pudl/en/nightly/data_dictionaries/usage_warnings.html> |
| Methodology docs                   | <https://docs.catalyst.coop/pudl/en/nightly/methodology/index.html>                |
| **Data sources index**             | <https://docs.catalyst.coop/pudl/en/nightly/data_sources/index.html>               |
| Web data viewer (preview tables)   | <https://data.catalyst.coop>                                                       |
| GitHub issues / discussions        | <https://github.com/catalyst-cooperative/pudl>                                     |

---

## Raw input archives (Zenodo)

PUDL processes data from US government agencies and republishes it. All raw input
datasets are archived on Zenodo (CERN's research data management platform) and mirrored
to S3. These archives exist for two reasons:

1. **Reproducibility** — every PUDL release is built from a specific, citable Zenodo
    archive. The DOI in the release metadata tells you exactly which raw data was used.
1. **Independent fallback** — if a government agency removes or changes data on its
    public website, the Zenodo archive remains permanently accessible.

For agents, Zenodo is mainly a provenance and permanence layer. It is usually **not**
the best place to explore raw metadata or access raw files. Prefer the cached S3 copy of
the same archive and its `datapackage.json`.

Most users should work with the processed PUDL outputs rather than the raw archives.
Raw data is appropriate when:

- Tracing a specific value back to its original government form
- Verifying that a transformation is correct
- Accessing years or fields that PUDL has not yet processed

### How to think about Zenodo vs. the S3 cache

- Use the **docs page** for a high-level description of the source and a public DOI link.
- Use the **cached S3 archive** for actual metadata and file access.
- Use the **Zenodo website or API** only when a user wants to visit the archive in a
    browser, cite the archive by DOI, or retrieve a version that has already been purged
    from the S3 cache.

In practice, agents should rarely fetch data or metadata from `zenodo.org` itself.

### Archive locations

Zenodo canonical home: <https://zenodo.org/communities/catalyst-cooperative/>

S3 mirror: `s3://pudl.catalyst.coop/zenodo/<dataset>/<concrete-doi>/datapackage.json`

The S3 path uses the **concrete Zenodo record DOI** with the internal `/` replaced by
`-`:

| Dataset      | Short code | Example path                              |
| ------------ | ---------- | ----------------------------------------- |
| FERC Form 1  | `ferc1`    | `zenodo/ferc1/10.5281-zenodo.XXXXXXX/`    |
| EIA Form 923 | `eia923`   | `zenodo/eia923/10.5281-zenodo.XXXXXXX/`   |
| EPA CEMS     | `epacems`  | `zenodo/epacems/10.5281-zenodo.XXXXXXX/`  |
| PHMSA Gas    | `phmsagas` | `zenodo/phmsagas/10.5281-zenodo.XXXXXXX/` |
| FERC CID     | `ferccid`  | `zenodo/ferccid/10.5281-zenodo.XXXXXXX/`  |

The DOI shown on a dataset's docs page is usually the **concept DOI**, which identifies
the whole lineage of versions for that dataset. The actual cached S3 path uses a
**concrete DOI** for one specific version. For example, a docs page might list the
concept DOI `10.5281/zenodo.18248545`, while the corresponding cached S3 directory uses
the concrete DOI `10.5281-zenodo.18793102`.

Each directory contains a `datapackage.json` (non-tabular — resources have `bytes` and
`hash` for integrity checking but no `schema`). Multiple DOI versions may coexist on
S3; the nightly build uses whichever version is referenced in the current `zenodo_doi`
config. See [Data Access](./data-access.md#raw-input-archives-zenodo) for shell
commands to browse and fetch these.

---

## When data seems wrong

If a value looks suspicious, guide the user through this sequence:

1. Check the column description in the metadata for any caveats about the value.
1. Check the table description for usage warnings.
1. Check whether the table is `_core_*` (preliminary, may have known issues).
1. Look up the source form at the agency's website to compare raw values.
1. Search open PUDL GitHub issues for the symptom.
1. For methodology questions (imputation, entity resolution), see <https://docs.catalyst.coop/pudl/en/nightly/methodology/index.html>
1. If you think you've found a data bug, report it at <https://github.com/catalyst-cooperative/pudl/issues/new?template=data_bug_report.yml>
