"""Tests for SKILL.md's "Cross-referencing FERC Form 1 and Form 2 schedules and
accounts" section — the jq patterns for joining ferc1/ferc2_schedules.json against
ferc_electricity_accounts.json.

Run:  pixi run pytest dev/skills/pudl/tests/test_cross_reference.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from .conftest import (
    FERC1_SCHEDULES,
    FERC2_SCHEDULES,
    FERC_ELECTRICITY_ACCOUNTS,
    KNOWN_ACCOUNT,
)


def run_shell(command: str) -> str:
    """Run a documented shell one-liner (may include a pipeline) and return stdout."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, cwd=Path.cwd()
    )
    assert result.returncode == 0, (
        f"Command exited {result.returncode}\ncommand: {command}\nstderr: {result.stderr}"
    )
    return result.stdout


def jq(expr: str, path: Path) -> Any:
    result = subprocess.run(
        ["jq", "-c", expr, str(path)], capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"jq exited {result.returncode}\nstderr: {result.stderr}"
    )
    lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    if len(lines) == 1:
        return json.loads(lines[0])
    return [json.loads(ln) for ln in lines]


def test_find_ferc1_schedules_by_account():
    """Find all Form 1 schedules that reference a specific account number."""
    result = jq(
        f'[.[] | select(.ferc_accounts[] == "{KNOWN_ACCOUNT}")] | .[] | {{schedule, title}}',
        FERC1_SCHEDULES,
    )
    assert result, f"Expected at least one FERC1 schedule referencing {KNOWN_ACCOUNT}"


def test_find_ferc2_schedules_by_account():
    """Find all Form 2 schedules that reference a specific account number."""
    result = jq(
        '[.[] | select(.ferc_accounts[] == "489.2")] | .[] | {schedule, title}',
        FERC2_SCHEDULES,
    )
    assert result, "Expected at least one FERC2 schedule referencing account 489.2"


def test_account_definitions_for_schedule(tmp_path):
    """Get all account definitions for a specific Form 1 schedule, via xargs join."""
    sched = "232"
    accounts_path = FERC_ELECTRICITY_ACCOUNTS
    schedules_path = FERC1_SCHEDULES
    command = (
        f"jq --arg s '{sched}' '.[] | select(.schedule == $s) | .ferc_accounts[]' "
        f"'{schedules_path}' | "
        f"xargs -I{{}} jq -c --arg a {{}} '.[] | select(.account == $a)' '{accounts_path}'"
    )
    stdout = run_shell(command)
    lines = [ln for ln in stdout.strip().splitlines() if ln]
    assert lines, f"Expected account definitions for FERC1 schedule {sched}"
    accounts = [json.loads(ln) for ln in lines]
    for account in accounts:
        assert account["account"]
        assert account["description"]


def test_slurpfile_index_join_for_ferc1_topic():
    """--slurpfile + INDEX() join: resolve account descriptions for a topical keyword search."""
    command = (
        f"jq -c --slurpfile accounts '{FERC_ELECTRICITY_ACCOUNTS}' '\n"
        "  ($accounts[0] | INDEX(.account)) as $acct_lookup\n"
        "  | .[]\n"
        '  | select(.description | test("regulatory asset"; "i"))\n'
        "  | .schedule as $sched | .title as $title | .pudl_tables as $tables\n"
        "  | .ferc_accounts[]\n"
        "  | {schedule: $sched, title: $title, pudl_tables: $tables,\n"
        "     account: ., account_description: $acct_lookup[.].description}\n"
        f"' '{FERC1_SCHEDULES}'"
    )
    stdout = run_shell(command)
    lines = [ln for ln in stdout.strip().splitlines() if ln]
    assert lines, "Expected at least one row for the 'regulatory asset' topic search"
    rows = [json.loads(ln) for ln in lines]
    for row in rows:
        assert row["schedule"]
        assert row["account"]
        assert row["account_description"], (
            f"account {row['account']} on schedule {row['schedule']} "
            "did not resolve to a description via the INDEX() lookup"
        )


def test_ferc2_topic_search_needs_no_join():
    """Single-file Form 2 topic search (no account join required)."""
    result = jq(
        '[.[] | select(.description | test("storage"; "i"))] | .[] | {schedule, title, xbrl_tables}',
        FERC2_SCHEDULES,
    )
    assert result, "Expected at least one Form 2 schedule matching 'storage'"
