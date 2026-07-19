# Prompt for compiling FERC schedule, table, and account metadata

We need to compile metadata describing the relationships between FERC form schedules
(also referred to as "pages"), DBF and XBRL derived database tables, the FERC uniform
system of accounts, and the instructions for filling out each schedule. This metadata
will be used to populate the knowledge base of the PUDL agent skill, which will allow it
to answer questions about what data is available in PUDL, where it comes from, and how
the different pieces of data relate to each other.

The final output of this process will be a JSON file called fercN_schedules.json where
"N" is the FERC form number (1, 2, 6, 60, or 714). You can see an example of this type
of output in ferc1_schedules.json, which is already part of the pudl skill's knowledge
base. Each element of the JSON file should have the following format, where the title,
description, list of associated PUDL tables, list of associated XBRL tables, list of
associated DBF tables, schedule number, and list of associated FERC accounts are all
filled in with the relevant information for that schedule:

```json
{
  "title": "Electric Plant in Service",
  "description": "Original cost of electric plant in service (Accounts 101-106) with beginning-of-year balances, additions, retirements, and end-of-year balances by prescribed account.",
  "pudl_tables": [
    "out_ferc1__yearly_plant_in_service_sched204"
  ],
  "xbrl_tables": [
    "electric_plant_in_service_204_duration",
    "electric_plant_in_service_204_instant"
  ],
  "dbf_tables": [
    "f1_plant",
    "f1_plant_in_srvce"
  ],
  "schedule": "204",
  "ferc_accounts": [
    "101",
    "102",
    "103",
    "104",
    "105",
    "106"
  ]
}
```

You have several sources of information to draw on to compile this metadata.

- **`$PUDL_OUTPUT/fercN_xbrl_datapackage.json`** contains the metadata about the
    XBRL-derived DuckDB database, including the list of tables (called resources in the
    nomenclature of the datapackage specification). Unfortunately, the table descriptions
    in the datapackage metadata are not informative, so we need to use another source to
    generate those descriptions.

- **`$PUDL_REPO/docs/data_sources/fercN/fercN_blank_*.{html,pdf}`** contains HTML and
    PDF versions of the blank FERC Forms. These forms contain the instructions for filling
    out each schedule, and the instructions often give us important context about the data
    that is being collected in each schedule. This is the best source for generating
    informative descriptions of each schedule. The instructions and other parts of the
    schedule itself also often explicitly reference the FERC accounts that are associated
    with the schedule, which is helpful for compiling the list of associated FERC accounts
    for each schedule. Any FERC Account that is mentioned in the instructions or elsewhere
    on the schedule should be included in the list of associated FERC accounts for that
    schedule. Sometimes the FERC Account is not explicitly mentioned, but the
    instructions will say something like "report the data for each account in the electric
    plant in service group (Accounts 101-106)", in which case we should include all of
    those accounts in the list of associated FERC accounts for that schedule. Sometimes
    the FERC Account is just mentioned parenthetically like (801.5). In that case we
    should still include it in the list of associated FERC accounts for that schedule. You
    can find the blank forms in the PUDL documentation locally at paths like this: Note
    that there are often several different versions of the blank forms. Each filename
    contains a date. The date indicates when that version of the form was supposed to be
    valid until. You should use the most recent version of the form, which will have the
    latest date in its filename. If necessary we will return to the older versions of the
    form to clarify any questions about the instructions, but the most recent version of
    the form should be our primary source of information. The HTML version of the form is
    easier to work with, so prefer that over the PDF if it's available. Use beautiful soup
    to parse the HTML and extract the relevant information. The HTML forms all contain a
    table of contents near the beginning of the document, which contains a list of all the
    schedules and links to where they are in the document. This is a good place to start
    when trying to find the instructions for each schedule. It's on Page 2 in a section
    entitled "List of Schedules"

- **`$PUDL_OUTPUT/fercN_xbrl.duckdb`** is the database file containing FERC data derived
    from the raw XBRL data. This data is more recent -- dating from 2021 to the present.
    You can attach to and query the database to help understand the relationships between
    tables and the schedules and accounts they relate to. The XBRL database table names
    almost always contain the number of the, schedule the table is derived from. For many
    schedules there will be two tables, one with the suffix "\_duration" and one with the
    suffix "\_instant".

- **`$PUDL_OUTPUT/fercN_dbf.sqlite`** is the database file containing older FERC data
    derived from the raw DBF data. This data comes from 2020 and earlier. You can attach to
    and query the database to help understand the relationships between tables and
    schedules and the accounts they relate to. The table names in the DBF derived database
    are much shorter and less informative on their own (though they do still sometimes
    contain the schedule number, as in the case of Form 2). However, there are also some
    tables that contain metadata and structural information about the database. For example,
    in `ferc6_dbf.sqlite` the `f6_s0_sched_info` table contains columns `schedule_title`
    and `pg_num` and `pg_num` is the schedule number (schedules are often referred to as
    "pages" colloquially). Tables that contain `_s0_` in their name are likely to contain
    metadata and structural information about the database.

When filling in the metadata JSON template for each schedule, do not make educated
guesses about the list of associated PUDL tables, XBRL tables, DBF tables, and FERC
accounts. Only include tables and accounts that you can confirm are associated with the
schedule based on the information in the sources described above. It's better to have an
incomplete list than an inaccurate one, because we can always add to the list later as
we learn more.

When filling in the "description" field for each schedule, use the instructions and
other information on the schedule itself to write a meaningful description of what data
is being collected in the schedule. The description should be more informative than just
the title of the schedule. It should give a clear summary of what data is being
collected in the schedule, and any important context that is necessary to understand the
data. The description should be written in complete sentences and should be suitable for
either human consumption, or as context for an agent that is responding to a user query
about what data is available in PUDL, or related to a topic the user is asking about.

Given the above context, now attempt to compile the metadata for FERC Form 6, and place
it in `skills/pudl/assets/ferc6_schedules.json`.

## Prior attempt at FERC 2

Earlier we compiled the ferc1_schedules.json asset for the pudl skill based on
information sourced from:

- the ferc1_xbrl.duckdb database,
- the ferc1_xbrl_datapackage.json datapackage descriptor,
- a copy of the blank FERC Form 1 in HTML format,
- a hand-compiled mapping between the list of schedules and the DBF derived database tables.

Now we want to do something similar for FERC Form 2. We lack the hand compiled mapping
for the DBF derived database tables, but we do have the XBRL-derived DuckDB database,
the associated datapackage descriptor, and the HTML version of the blank form.

Look in $PUDL_OUTPUT to find ferc2_xbrl_datapackage.json and ferc2_xbrl.duckdb
Look at $PUDL_REPO/docs/data_sources/ferc2/ferc2_blank_2025-07-31.html for the blank Form 2

Near the beginning of the HTML document you will find a table of contents with one
column entitled "Reference Page No. (b)" -- this is the schedule / page number. The
column with the header "Title of Schedule (a)" contains the title of the schedule. The
Reference Page No. column contains internal links to each of the listed schedules within
the (very long) document. Following the link you should be able to find a instructions
for how to fill out the form, and other information from which you can summarize a
longer more informative description of the schedule.

You can obtain the list of all available FERC 2 XBRL database tables by attaching to the
ferc2_xbrl.duckdb database and listing all tables. Most of them will have the schedule
as part of their name. For many schedules there will be both an_instant and \_duration
table. In some cases one schedule will be split across a number of different tables.

Using all of this information, compile a ferc2_schedules.json asset using the same
format that we used in ferc1_schedules.json. Because none of FERC Form 2 has been
integrated into PUDL, the pudl_tables element for all schedules will be empty for now,
and we will need to do some kind of entity resolution process to identify the correct
dbf_tables to associate with each schedule, but having the schedule ID, the title, a
meaningful description, and the list of xbrl_tables will still be a good start.

## FERC Form 6 extraction — results summary (2026-04-05)

**Output**: `skills/pudl/assets/ferc6_schedules.json` — 42 schedules covering all
FERC Form 6 pages. A reusable generation script was saved to
`skills/pudl/scripts/generate_ferc6_schedules.py`.

### Sources used

- **HTML blank form**: `docs/data_sources/ferc6/ferc6_blank_2025-07-31.html` —
    primary source for descriptions and FERC account numbers
- **XBRL datapackage**: `$PUDL_OUTPUT/ferc6_xbrl_datapackage.json` — 206 XBRL
    resources mapped to schedules by the number embedded in each table name
- **DBF SQLite**: `$PUDL_OUTPUT/ferc6_dbf.sqlite` — `f6_s0_sched_info` confirmed
    the 42 canonical schedules; table names were used to map DBF tables to schedules

### Key findings

- **No PUDL output tables** — FERC 6 is only extracted to SQLite/DuckDB, not
    transformed into Parquet. All `pudl_tables` arrays are empty.
- **XBRL naming quirk** — The `statistics_of_operations` tables use a `600a` suffix
    for operator-level sub-tables (distinct from the main `600` schedule tables).
- **Shared DBF tables** — `f6_invest_affil` appears in both schedule 202
    (Investments in Affiliated Companies) and schedule 204 (Investments in Common
    Stocks of Affiliated Companies), because it covers both schedules.
- **Schedule 302** (Operating Expense Accounts) has the most FERC accounts (21),
    covering the full range of pipeline operating expense accounts (300–610).
- **Schedule 120** (Statement of Cash Flows) has 18 XBRL tables — the most of any
    schedule — due to many sub-tables for different cash flow categories.

### Script saved

The script used to generate the
[`ferc6_schedules.json`](skills/pudl/assets/ferc6_schedules.json) file was saved to
[`generate_ferc6_schedules.py`](skills/pudl/scripts/generate_ferc6_schedules.py) and
documents all the DBF→schedule mappings, the XBRL grouping logic, and the FERC account
extraction patterns. It can serve as a template for FERC 2, 60, and 714 extractions.
