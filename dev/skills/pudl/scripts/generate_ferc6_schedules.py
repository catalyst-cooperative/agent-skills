#!/usr/bin/env python3
"""Generate ferc6_schedules.json from the blank FERC Form 6 HTML and database metadata.

FERC Form 6 is the Annual Report of Oil Pipeline Companies. It covers financial
statements, carrier property, operating revenues and expenses, and pipeline
statistics for oil pipeline companies regulated by FERC.

Data sources:
- HTML blank form: docs/data_sources/ferc6/ferc6_blank_2025-07-31.html
- XBRL datapackage: $PUDL_OUTPUT/ferc6_xbrl_datapackage.json
- DBF SQLite: $PUDL_OUTPUT/ferc6_dbf.sqlite (f6_s0_sched_info for schedule metadata)

Note: FERC Form 6 data is only extracted to SQLite/DuckDB in PUDL — it is NOT
transformed into PUDL output Parquet files. All pudl_tables arrays are empty.

Usage:
    python generate_ferc6_schedules.py

    You can also override the paths via environment variables:
    HTML_PATH, OUTPUT_PATH, XBRL_DATAPACKAGE_PATH
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup

# --- Paths -------------------------------------------------------------------

PUDL_REPO = os.environ.get("PUDL_REPO", "/Users/zane/code/catalyst/pudl")
PUDL_OUTPUT = os.environ.get("PUDL_OUTPUT", "/Users/zane/code/catalyst/pudl-output")
AGENT_SKILLS = os.environ.get("AGENT_SKILLS", "/Users/zane/code/catalyst/agent-skills")

HTML_PATH = os.environ.get(
    "HTML_PATH",
    str(Path(PUDL_REPO) / "docs/data_sources/ferc6/ferc6_blank_2025-07-31.html"),
)
XBRL_DATAPACKAGE_PATH = os.environ.get(
    "XBRL_DATAPACKAGE_PATH",
    str(Path(PUDL_OUTPUT) / "ferc6_xbrl_datapackage.json"),
)
OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH",
    str(Path(AGENT_SKILLS) / "skills/pudl/assets/ferc6_schedules.json"),
)

# --- DBF table → schedule mappings ------------------------------------------
# These were established by cross-referencing the f6_s0_sched_info metadata
# table in ferc6_dbf.sqlite against the table names. Tables with _s0_ prefix
# are internal metadata tables and are excluded.

DBF_TABLE_TO_SCHEDULE: dict[str, list[str]] = {
    "f6_ident_attsttn": ["1"],
    "f6_list_of_sched": ["2"],
    "f6_list_of_sched_add": ["2"],
    "f6_general_info": ["101"],
    "f6_cntrl_over_resp": ["102"],
    "f6_ctrl_by_resp": ["103"],
    "f6_principal_officers": ["104"],
    "f6_directors": ["105"],
    "f6_important_changes": ["108"],
    "f6_comp_bal_sheet": ["110"],
    "f6_income_stmnt": ["114"],
    "f6_cmpinc_hedge": ["116"],
    "f6_cmpinc_hedge_a": ["116"],
    "f6_approp_ret_inc": ["118"],
    "f6_unapprop_ret_inc": ["119"],
    "f6_stmnt_cash_flow": ["120"],
    "f6_note_fin_stmnt": ["122"],
    "f6_recv_affiliated": ["200"],
    "f6_invest_affil": ["202", "204"],  # appears in both schedules
    "f6_invest_affiliated": ["202"],
    "f6_invest_affil_a": ["204"],
    "f6_carrier_property": ["212"],
    "f6_undiv_joint_int_prop": ["214"],
    "f6_acc_depr_carrier": ["216"],
    "f6_depr_carrier_prop": ["216"],
    "f6_acc_depr_system": ["217"],
    "f6_depr_sys_prop": ["217"],
    "f6_amort_base": ["218"],
    "f6_noncarrier_prop": ["220"],
    "f6_other_defer_chrgs": ["221"],
    "f6_payables_affil": ["225"],
    "f6_long_term_debt": ["226"],
    "f6_analysis_inc_tax": ["230"],
    "f6_capital_stock": ["250"],
    "f6_cap_stk_chgs": ["252"],
    "f6_paid_in_cap": ["254"],
    "f6_300_op_revenues": ["300"],
    "f6_op_rev_accts": ["301"],
    "f6_op_rev_accts_a": ["301"],
    "f6_op_exp_accts": ["302"],
    "f6_pipeline_tax": ["305"],
    "f6_pipeline_tax_a": ["305"],
    "f6_inc_noncarrier": ["335"],
    "f6_int_div_inc": ["336"],
    "f6_misc_ret_inc": ["337"],
    "f6_pay_oth_emp": ["351"],
    "f6_stats_oper": ["600"],
    "f6_stats_oper_a": ["600"],
    "f6_miles_pipeline": ["602"],
    "f6_miles_pipe_a": ["602"],
    "f6_miles_pipe_b": ["602"],
    "f6_miles_pipe_c": ["602"],
    "f6_miles_pipe_d": ["602"],
    "f6_annual_cost_serv": ["700"],
}

# --- Schedule ordering -------------------------------------------------------
# Canonical ordering by schedule number (matches the form's "List of Schedules")

SCHEDULE_ORDER = [
    "1",
    "2",
    "101",
    "102",
    "103",
    "104",
    "105",
    "108",
    "110",
    "114",
    "116",
    "118",
    "119",
    "120",
    "122",
    "200",
    "202",
    "204",
    "212",
    "214",
    "216",
    "217",
    "218",
    "220",
    "221",
    "225",
    "226",
    "230",
    "250",
    "252",
    "254",
    "300",
    "301",
    "302",
    "305",
    "335",
    "336",
    "337",
    "351",
    "600",
    "602",
    "700",
]


def load_xbrl_tables(datapackage_path: str) -> dict[str, list[str]]:
    """Load XBRL table names from the datapackage JSON, grouped by schedule number.

    XBRL table names almost always contain the schedule number as the final
    numeric component before the _duration/_instant suffix (e.g.,
    ``carrier_property_212_duration`` → schedule 212).

    Returns a dict mapping schedule number (str) → list of table names.
    """
    with open(datapackage_path) as f:
        dp = json.load(f)

    schedule_tables: dict[str, list[str]] = defaultdict(list)
    for resource in dp.get("resources", []):
        name = resource["name"]
        # Extract trailing schedule number before _duration/_instant
        m = re.search(r"_(\d+[a-z]?)_(duration|instant)$", name)
        if m:
            sched = m.group(1).lstrip("0") or "0"
            # Normalize: remove leading zeros but keep '600a' as-is
            if sched.isdigit():
                sched = str(int(sched))
            schedule_tables[sched].append(name)

    return dict(schedule_tables)


def build_dbf_by_schedule() -> dict[str, list[str]]:
    """Invert DBF_TABLE_TO_SCHEDULE to get schedule → sorted list of DBF tables."""
    result: dict[str, list[str]] = defaultdict(list)
    for table, schedules in DBF_TABLE_TO_SCHEDULE.items():
        for sched in schedules:
            if table not in result[sched]:
                result[sched].append(table)
    for sched in result:
        result[sched] = sorted(set(result[sched]))
    return dict(result)


def extract_ferc_accounts(text: str) -> list[str]:
    """Extract FERC account numbers mentioned in schedule instructions.

    Handles patterns like:
    - "Account 600" → ["600"]
    - "Accounts 601-606" → ["601", "602", "603", "604", "605", "606"]
    - "(Account 70)" → ["70"]
    - "account 530" → ["530"]
    - "accounts 500, 510, and 520" → ["500", "510", "520"]
    """
    accounts: set[str] = set()

    # Ranges: "Accounts 601-606" or "accounts 300-390"
    for m in re.finditer(
        r"[Aa]ccounts?\s+(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", text
    ):
        try:
            start = int(float(m.group(1)))
            end = int(float(m.group(2)))
            # Only expand if range is reasonable (≤ 100 items)
            if end - start <= 100:
                for n in range(start, end + 1):
                    accounts.add(str(n))
            else:
                accounts.add(m.group(1))
                accounts.add(m.group(2))
        except ValueError:
            pass

    # Parenthetical: "(Account 70)" or "(account 610)"
    for m in re.finditer(r"\([Aa]ccounts?\s+(\d+(?:\.\d+)?)\)", text):
        accounts.add(m.group(1).rstrip(".0").rstrip("."))

    # Standalone: "Account 600" or "Accounts 601, 602"
    for m in re.finditer(
        r"[Aa]ccounts?\s+((?:\d+(?:\.\d+)?(?:,\s*(?:and\s+)?\d+(?:\.\d+)?)*|and\s+\d+(?:\.\d+)?))",
        text,
    ):
        for acct in re.findall(r"\d+(?:\.\d+)?", m.group(1)):
            accounts.add(acct.rstrip(".0").rstrip(".") if "." in acct else acct)

    return sorted(accounts, key=lambda x: (len(x), x))


def parse_html_form(html_path: str) -> dict[str, dict]:
    """Parse the blank FERC Form 6 HTML to extract per-schedule text.

    The HTML form contains a "List of Schedules" table of contents near the
    beginning (reference page 2), followed by the form pages themselves.
    Each schedule page has a header identifying the schedule number and title.

    Returns a dict mapping schedule number → {"title": str, "text": str}.
    """
    with open(html_path, encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Collect all text by page/section. The HTML uses page-break markers or
    # named anchors to separate schedules. We find anchors with schedule-number
    # names and collect the text between them.
    schedule_data: dict[str, dict] = {}

    # Strategy: find all named anchors, group body text between them
    # The form typically has anchors like <a name="page101"> or similar
    anchors = soup.find_all("a", {"name": True})

    # Build a flat list of (anchor_name, following_text) pairs
    sections = []
    for anchor in anchors:
        name_attr = anchor.get("name", "")
        name = name_attr if isinstance(name_attr, str) else ""
        # Collect text from this anchor to the next
        text_parts = []
        for sibling in anchor.find_all_next():
            if sibling.name == "a" and sibling.get("name"):
                break
            if sibling.string:
                text_parts.append(sibling.string.strip())
        text = " ".join(t for t in text_parts if t)
        sections.append((name, text))

    # Identify schedule-number anchors (e.g., "page101", "sched212", numbers)
    for anchor_name, text in sections:
        # Try to extract a schedule number from the anchor name
        m = re.search(r"(\d+)", anchor_name)
        if not m:
            continue
        sched_num = str(int(m.group(1)))
        if sched_num in SCHEDULE_ORDER and sched_num not in schedule_data:
            # Extract a title from the first heading in this section
            title_match = re.search(r"^([A-Z][A-Z\s\(\)/\-]+)", text)
            title = title_match.group(1).strip() if title_match else ""
            schedule_data[sched_num] = {"title": title, "text": text}

    return schedule_data


def build_schedules(
    html_path: str,
    xbrl_datapackage_path: str,
) -> list[dict]:
    """Build the complete list of schedule metadata dicts."""
    xbrl_by_schedule = load_xbrl_tables(xbrl_datapackage_path)
    dbf_by_schedule = build_dbf_by_schedule()
    html_data = parse_html_form(html_path)

    schedules = []
    for sched in SCHEDULE_ORDER:
        html_info = html_data.get(sched, {})
        text = html_info.get("text", "")
        accounts = extract_ferc_accounts(text) if text else []

        # XBRL tables: collect all tables for this schedule number
        # Also check for variant suffixes like "600a"
        xbrl_tables = sorted(
            xbrl_by_schedule.get(sched, []) + xbrl_by_schedule.get(sched + "a", [])
        )
        dbf_tables = dbf_by_schedule.get(sched, [])

        schedules.append(
            {
                "title": html_info.get("title", ""),
                "description": "",  # Fill in manually or use LLM
                "pudl_tables": [],  # FERC 6 is not transformed into PUDL Parquet
                "xbrl_tables": xbrl_tables,
                "dbf_tables": dbf_tables,
                "schedule": sched,
                "ferc_accounts": accounts,
            }
        )
    return schedules


def main() -> None:
    """Generate ferc6_schedules.json."""
    print(f"Reading HTML form: {HTML_PATH}")
    print(f"Reading XBRL datapackage: {XBRL_DATAPACKAGE_PATH}")

    schedules = build_schedules(HTML_PATH, XBRL_DATAPACKAGE_PATH)

    print(f"Writing {len(schedules)} schedules to: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, "w") as f:
        json.dump(schedules, f, indent=2)
    print("Done.")

    # Summary
    for s in schedules:
        print(
            f"  {s['schedule']:>4s}  xbrl={len(s['xbrl_tables'])}"
            f"  dbf={len(s['dbf_tables'])}"
            f"  accts={len(s['ferc_accounts'])}"
        )


if __name__ == "__main__":
    main()
