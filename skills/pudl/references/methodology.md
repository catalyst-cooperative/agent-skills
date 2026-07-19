# PUDL Methodology Documentation

## Use this when

A user asks how PUDL processes, cleans, reconciles, or models a specific aspect of
the data — e.g., "how does PUDL match generators across years?", "how are missing
values filled in?", "how is ownership determined?".

**Workflow**: Read this index to find the relevant page URL, then fetch that page with
a web tool to get the full methodology description. Summarize the approach and direct
the user to the full page for details.

**Default behavior**: If a relevant methodology page exists, point the user to that
page and summarize it before diving into source code, implementation details, or
docstrings. Only move on to code-level explanation if the user asks for more detail
after seeing the methodology write-up, or if there is no methodology page for the
topic.

Index: <https://docs.catalyst.coop/pudl/en/nightly/methodology/index.html>

---

## Current methodology pages

### Entity Resolution

**URL**: <https://docs.catalyst.coop/pudl/en/nightly/methodology/entity_resolution.html>

**When relevant**: User asks how PUDL identifies the same plant, generator, or utility
across multiple forms or years; asks about "golden records", canonical IDs, or why
an entity has a particular name or attribute in PUDL when the source data differs.

**Summary**: PUDL attempts to identify canonical ("golden record") values for entities
that appear inconsistently across multiple forms, worksheets, and filing years. For
example, a power plant may be reported in EIA-860, EIA-923, and FERC Form 1 with
slightly different names, coordinates, or associated balancing authority areas. Entity
resolution harvests the most reliable values from all available sources and attaches
them to a stable PUDL identifier. This affects `plant_id_pudl`, `utility_id_pudl`,
and related entity tables.

---

### Timeseries Imputation

**URL**: <https://docs.catalyst.coop/pudl/en/nightly/methodology/timeseries_imputation.html>

**When relevant**: User asks how missing, anomalous, or flagged values are handled in
hourly or sub-hourly timeseries data (electricity demand, net generation, etc.); asks
about imputation flags, anomaly detection, or why a value looks unusual in an imputed
timeseries table like `out_ferc714__hourly_planning_area_demand`.

**Summary**: Energy systems timeseries data (especially hourly electricity demand and
net generation) frequently contains anomalous values due to reporting errors or data
gaps. PUDL uses heuristics developed by Tyler Ruggles to flag suspect values and
impute replacements using correlated timeseries with known seasonality and periodicity.
Flagged values are marked in the output tables so users can distinguish imputed from
reported values.

---

### SEC 10-K Ownership Data Extraction

**URL**: <https://docs.catalyst.coop/pudl/en/nightly/methodology/sec10k_modeling.html>

**When relevant**: User asks how utility holding company hierarchies are determined;
asks about ownership structure, parent companies, subsidiaries, or the
`out_sec10k__quarterly_filings` table and related outputs.

**Summary**: Utilities are often nested within complex holding company hierarchies that
obscure the true web of economic and political incentives. PUDL uses ML-assisted
extraction from SEC Form 10-K filings to reconstruct ownership relationships between
utilities and their parent/subsidiary companies. The output tables include
`out_sec10k__quarterly_filings` (filing metadata) and related ownership tables derived
from the extracted text.

---

## Keeping this index current

This file is maintained by hand. When new methodology pages are added to the PUDL docs,
add an entry here following the same pattern: URL, when-relevant trigger, and a 2–4
sentence summary. Run a quick `curl` or web fetch on the new page to draft the summary.
