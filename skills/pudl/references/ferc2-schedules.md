<!-- markdownlint-disable MD013 -->

# FERC Form 2 Schedules (Natural Gas Company)

FERC Form 2 is the Annual Report of Natural Gas Companies filed with FERC by major
interstate natural gas pipelines. It is divided into numbered schedules (also called
pages). The schedule number appears at the bottom of each blank form page. Schedules are
referred to by their page number, e.g. "Schedule 300" or "Page 508".

Account numbers referenced in the Description column (e.g. "Account 182.3",
"Accounts 221–224") correspond to the FERC Uniform System of Accounts for Natural Gas
Companies; there is no separate accounts reference file for gas companies in this skill.

> **For agent use, query [`ferc2_schedules.json`](../assets/ferc2_schedules.json)**
> **directly — this file does not embed the full schedule table.**

---

## Querying the machine-readable index

Use [`ferc2_schedules.json`](../assets/ferc2_schedules.json) for all programmatic
lookups. `xbrl_tables` and `ferc_accounts` are typed arrays; `schedule` is the page key.
`pudl_tables` and `dbf_tables` are present but currently empty (Form 2 is not yet
integrated into PUDL).

### jq examples

```bash
# Find schedules whose description mentions a topic
jq '[.[] | select(.description | test("storage"))] | .[] | {schedule, title}' \
    assets/ferc2_schedules.json

# Find schedules linked to a specific FERC account number
jq '[.[] | select(.ferc_accounts[] == "489.2")] | .[] | {schedule, title}' \
    assets/ferc2_schedules.json

# Get XBRL table names for a specific schedule
jq '.[] | select(.schedule == "300") | .xbrl_tables[]' assets/ferc2_schedules.json
```

These three examples cover every lookup this file supports. For joining this JSON with
`ferc1_schedules.json` or `ferc_electricity_accounts.json` in one query, see
[Cross-referencing FERC Form 1 and Form 2 schedules and accounts](../SKILL.md#cross-referencing-ferc-form-1-and-form-2-schedules-and-accounts)
in `SKILL.md` for that pattern.

---

## About FERC Form 2 data

None of FERC Form 2 has yet been integrated into the main PUDL data pipeline. The raw
XBRL-derived data (2021–present) is available in `ferc2_xbrl.duckdb` and
`ferc2_xbrl.sqlite`. There is no equivalent DBF-era database for Form 2 yet.

Raw tables come in two formats within the XBRL database:

- **Duration tables** (`_duration` suffix): record values that apply over a time period
    (e.g. income, expenses, changes in plant balance).
- **Instant tables** (`_instant` suffix): record point-in-time balances (e.g. balance
    sheet accounts, end-of-year plant totals).

Many schedules are split across multiple sub-tables in the XBRL database, one per
section, account type, or monthly period.

Source (schedule titles and descriptions): FERC Form 2 blank form (2025-07-31 edition).
`ferc2` doesn't have a PUDL docs page yet (its `documentation` field is `null` — see
[Data Sources](./data-sources.md#the-sources-schema)), so its blank form and filer
instructions aren't linked from `docs.catalyst.coop` the way FERC Form 1's are. Get them
from the source agency's own page instead — the `path` field on the `ferc2` `sources`
record. See
[Data Sources: Blank forms and filer instructions](./data-sources.md#blank-forms-and-filer-instructions)
for the general pattern for sources that do have a docs page.

---

## Shape of the data

`ferc2_schedules.json` is a flat array of records like this one (illustrative only —
query the JSON for the full, current list of ~77 schedules):

```json
{
  "schedule": "204",
  "title": "Gas Plant in Service",
  "description": "Original cost of classified gas plant in service by account, with additions and retirements during the year.",
  "pudl_tables": [],
  "xbrl_tables": ["gas_plant_in_services_204_duration", "gas_plant_in_services_204_instant"],
  "dbf_tables": ["f2_204_gas_plant_in_srv"],
  "ferc_accounts": ["101", "102", "103", "106"]
}
```
