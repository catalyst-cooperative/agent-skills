"""Tests for the jq examples in references/ferc1-schedules.md.

Runs each documented query against the real, shipped ferc1_schedules.json and
checks it returns what the reference claims.

Run:  pixi run pytest dev/skills/pudl/tests/test_ferc1_schedules.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from .conftest import FERC1_SCHEDULES, KNOWN_ACCOUNT, KNOWN_FERC1_SCHEDULE


def jq(expr: str, path: Path) -> Any:
    """Run a jq expression and return the parsed output (list if multi-line)."""
    result = subprocess.run(
        ["jq", "-c", expr, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"jq exited {result.returncode}\nexpression: {expr!r}\nstderr: {result.stderr}"
    )
    lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    if len(lines) == 1:
        return json.loads(lines[0])
    return [json.loads(ln) for ln in lines]


def test_find_schedules_mentioning_account_in_description():
    r"""test("182\\.3") over description matches on a literal account number."""
    schedules = jq(
        r'[.[] | select(.description | test("182\\.3"))] | .[] | {schedule, title}',
        FERC1_SCHEDULES,
    )
    assert schedules, "Expected at least one schedule whose description mentions 182.3"


def test_schedules_with_pudl_tables():
    """select(.pudl_tables | length > 0) returns only integrated schedules."""
    schedules = jq(
        "[.[] | select(.pudl_tables | length > 0)] | .[] | {schedule, title, pudl_tables}",
        FERC1_SCHEDULES,
    )
    assert schedules, "Expected at least one Form 1 schedule with PUDL tables"
    for schedule in schedules:
        assert schedule["pudl_tables"], (
            f"Schedule {schedule['schedule']} has an empty pudl_tables list"
        )


def test_schedules_linked_to_account():
    """select(.ferc_accounts[] == ...) resolves the schedules that cite an account."""
    schedules = jq(
        f'[.[] | select(.ferc_accounts[] == "{KNOWN_ACCOUNT}")] | .[] | {{schedule, title}}',
        FERC1_SCHEDULES,
    )
    assert schedules, (
        f"Expected at least one schedule referencing account {KNOWN_ACCOUNT}"
    )


def test_pudl_table_names_for_schedule():
    """Get PUDL table names for a specific schedule."""
    tables = jq(
        f'.[] | select(.schedule == "{KNOWN_FERC1_SCHEDULE}") | .pudl_tables[]',
        FERC1_SCHEDULES,
    )
    if not isinstance(tables, list):
        tables = [tables]
    assert tables, f"Expected schedule {KNOWN_FERC1_SCHEDULE} to have PUDL tables"
    for table in tables:
        assert table.startswith("out_ferc1__"), f"Unexpected table name: {table}"


def test_shape_of_the_data():
    """Every record has the documented typed fields."""
    schedules = jq(".", FERC1_SCHEDULES)
    assert schedules, "ferc1_schedules.json should not be empty"
    expected_fields = {
        "schedule",
        "title",
        "description",
        "pudl_tables",
        "xbrl_tables",
        "dbf_tables",
        "ferc_accounts",
    }
    for schedule in schedules:
        assert set(schedule.keys()) == expected_fields, (
            f"Schedule {schedule.get('schedule')} has unexpected field set: {set(schedule.keys())}"
        )
        for array_field in (
            "pudl_tables",
            "xbrl_tables",
            "dbf_tables",
            "ferc_accounts",
        ):
            assert isinstance(schedule[array_field], list), (
                f"Schedule {schedule['schedule']}.{array_field} should be a list"
            )
