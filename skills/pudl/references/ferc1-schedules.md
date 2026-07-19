<!-- markdownlint-disable MD013 -->

# FERC Form 1 Schedules (Electric Utility)

FERC Form 1 is divided into numbered schedules (also called pages). The schedule number
appears at the bottom of each blank form page. Schedules are referred to by their page
number, e.g. "Schedule 301" or "Page 400a".

Account numbers referenced in the Description column (e.g. "Account 182.3",
"Accounts 221–224") correspond to entries in the
[FERC Electricity Accounts](./ferc-electricity-accounts.md).
Consult that reference to understand what a given account contains and whether it is
relevant to a user's query.

> **For agent use, query [`ferc1_schedules.json`](../assets/ferc1_schedules.json)**
> **directly — this file does not embed the full schedule table.**

---

## Querying the machine-readable index

Use [`ferc1_schedules.json`](../assets/ferc1_schedules.json) for all programmatic
lookups. `pudl_tables`, `xbrl_tables`, `dbf_tables`, and `ferc_accounts` are typed
arrays; `schedule` is the page key.

### jq examples

```bash
# Find schedules whose description mentions a specific account
jq '[.[] | select(.description | test("182\.3"))] | .[] | {schedule, title}' \
    assets/ferc1_schedules.json

# List all schedules that have PUDL integrated tables
jq '[.[] | select(.pudl_tables | length > 0)] | .[] | {schedule, title, pudl_tables}' \
    assets/ferc1_schedules.json

# Find schedules linked to a specific FERC account number
jq '[.[] | select(.ferc_accounts[] == "182.3")] | .[] | {schedule, title}' \
    assets/ferc1_schedules.json

# Get PUDL table names for a specific schedule
jq '.[] | select(.schedule == "204") | .pudl_tables[]' assets/ferc1_schedules.json
```

The four examples above cover single-file lookups and are all jq does well. For resolving
the account numbers a schedule references against their definitions (a join across two
files), see
[Cross-referencing FERC Form 1 and Form 2 schedules and accounts](../SKILL.md#cross-referencing-ferc-form-1-and-form-2-schedules-and-accounts)
in `SKILL.md`.

---

## Shape of the data

`ferc1_schedules.json` is a flat array of records like this one (illustrative only —
query the JSON for the full, current list of ~75 schedules):

```json
{
  "schedule": "204",
  "title": "Electric Plant in Service",
  "description": "Original cost of electric plant in service (Accounts 101-106) with beginning-of-year balances, additions, retirements, and end-of-year balances by prescribed account.",
  "pudl_tables": ["out_ferc1__yearly_plant_in_service_sched204"],
  "xbrl_tables": ["electric_plant_in_service_204_duration", "electric_plant_in_service_204_instant"],
  "dbf_tables": ["f1_plant", "f1_plant_in_srvce"],
  "ferc_accounts": ["101", "102", "103", "104", "105", "106"]
}
```

An empty `pudl_tables` array means that schedule has not yet been integrated into PUDL —
see below for how to fall back to the raw tables in that case.

## How to choose which tables to use

Use PUDL integrated tables (`out_ferc1__*`) first — they combine DBF and XBRL data,
apply entity resolution, and are the most analysis-ready. Fall back to the raw tables
only when:

- The schedule has not yet been integrated into PUDL (the PUDL column says
    "*(not yet integrated)*"), or
- The user explicitly asks for the raw data rather than the integrated PUDL data.

Raw tables come in two formats depending on the filing year:

- **XBRL (2021–present):** tables in `ferc1_xbrl.duckdb` / `ferc1_xbrl.sqlite`. Table
    names embed the schedule/page number just before the `_duration` or `_instant` suffix.
    Duration tables record changes over a period; instant tables record point-in-time
    balances. Many schedules have multiple sub-tables (e.g. one per section or account
    type).
- **DBF (1994–2020):** tables in `ferc1_dbf.sqlite`. Table names start with `f1_`.

Source (schedule titles): FERC Form 1 blank form (2025-07-31 edition),
"LIST OF SCHEDULES (Electric Utility)". The blank form HTML and older PDF versions can
be downloaded from links in the PUDL docs:
[FERC Form 1 additional documentation](https://docs.catalyst.coop/pudl/en/nightly/data_sources/ferc1.html#download-additional-documentation)

Source (DBF table names): Hand-compiled mapping published as the
[FERC Form 1 DBF data dictionary](https://docs.catalyst.coop/pudl/en/nightly/data_dictionaries/ferc1_db.html).

## Cross-schedule composite tables

These `out_ferc1__*` tables combine data from multiple schedules and are often more
useful than the per-schedule tables for broad financial or plant-level analysis:

| PUDL Table                                             | Schedules Combined | Description                                                                          |
| ------------------------------------------------------ | ------------------ | ------------------------------------------------------------------------------------ |
| `out_ferc1__yearly_all_plants`                         | 402, 406, 408, 410 | All generating plant types (steam, hydro, pumped storage, small plants) in one table |
| `out_ferc1__yearly_detailed_income_statements`         | 114, 336, 320, 300 | Income statement line items with account labels and hierarchy                        |
| `out_ferc1__yearly_detailed_balance_sheet_assets`      | 110, 200, 204, 219 | Balance sheet asset line items with account labels and hierarchy                     |
| `out_ferc1__yearly_detailed_balance_sheet_liabilities` | 110, 118           | Balance sheet liability line items with account labels and hierarchy                 |
| `out_ferc1__yearly_rate_base`                          | multiple           | Rate base calculation inputs drawn from several schedules                            |
