# FERC Uniform System of Accounts — Electric Utility Account Listing

**Authoritative source**: 18 C.F.R. Part 101 — *Uniform System of Accounts Prescribed
for Public Utilities and Licensees Subject to the Provisions of the Federal Power Act*
[18 C.F.R. Part 101 on eCFR](https://www.ecfr.gov/current/title-18/chapter-I/subchapter-C/part-101)

> **Do not load the eCFR URL into context in its entirety — it is a very large page.**
> If you need the full regulatory text, download it and cache it locally, then search
> selectively. The account listing below (compiled from the NARUC summary publication)
> covers account numbers and short descriptions; consult the CFR for the full
> definitional text of any individual account.

Accounts marked **(Major only)** apply only to Major utilities; those marked
**(Nonmajor only)** apply only to non-Major utilities; unmarked accounts apply to both.

---

> **For agent use, query [`ferc_electricity_accounts.json`](../assets/ferc_electricity_accounts.json)**
> **directly — this file does not embed the full account listing.**

---

## Querying the machine-readable index

Use [`ferc_electricity_accounts.json`](../assets/ferc_electricity_accounts.json) for all programmatic lookups.
Fields: `account`, `description`, `chart`, `section`, `group`, `operation_type`,
`major_only`, `nonmajor_only`, `reserved`.

### jq examples

```bash
# Look up a specific account
jq '.[] | select(.account == "182.3")' assets/ferc_electricity_accounts.json

# Find all accounts in a numeric range
jq '[.[] | select(.account | test("^18[0-9]"))] | .[] | {account, description}' \
    assets/ferc_electricity_accounts.json

# List all O&M transmission expense accounts
jq '[.[] | select(.chart == "om_expenses" and .section == "2. Transmission Expenses")] |
    .[] | {account, description, operation_type}' assets/ferc_electricity_accounts.json

# Find all Major-only accounts
jq '[.[] | select(.major_only)] | .[].account' assets/ferc_electricity_accounts.json
```

The four examples above cover single-file lookups and are all jq does well. For joining
accounts with the Form 1/Form 2 schedules that reference them (something jq handles
awkwardly across two files), see
[Cross-referencing FERC Form 1 and Form 2 schedules and accounts](../SKILL.md#cross-referencing-ferc-form-1-and-form-2-schedules-and-accounts)
in `SKILL.md`.

---

## Shape of the data

`ferc_electricity_accounts.json` is a flat array of records like these two (illustrative
only — query the JSON for the full, current account listing):

```json
[
  {
    "account": "101",
    "description": "Electric plant in service",
    "chart": "balance_sheet",
    "section": "Assets and Other Debits",
    "group": "Utility Plant",
    "operation_type": null,
    "major_only": true,
    "nonmajor_only": false,
    "reserved": false
  },
  {
    "account": "930.2",
    "description": "Miscellaneous general expenses",
    "chart": "om_expenses",
    "section": "8. Administrative and General Expenses",
    "group": null,
    "operation_type": "Operation",
    "major_only": false,
    "nonmajor_only": false,
    "reserved": false
  }
]
```
