"""Tests for the jq examples in references/ferc2-schedules.md.

Runs each documented query against the real, shipped ferc2_schedules.json and
checks it returns what the reference claims.

Run:  pixi run pytest dev/skills/pudl/tests/test_ferc2_schedules.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from .conftest import FERC2_SCHEDULES, KNOWN_ACCOUNT, KNOWN_FERC2_SCHEDULE


def jq(expr: str, path: Path) -> Any:
    """Run a jq expression and return the parsed output (list if multi-line)."""
    result = subprocess.run(
        ["jq", "-c", expr, str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"jq exited {result.returncode}\nexpression: {expr!r}\nstderr: {result.stderr}"
    )
    lines = [ln for ln in result.stdout.strip().splitlines() if ln]
    if len(lines) == 1:
        return json.loads(lines[0])
    return [json.loads(ln) for ln in lines]


def test_find_schedules_mentioning_topic():
    """test('storage') over description finds schedules about a topic."""
    schedules = jq(
        '[.[] | select(.description | test("storage"))] | .[] | {schedule, title}',
        FERC2_SCHEDULES,
    )
    assert schedules, (
        "Expected at least one schedule whose description mentions 'storage'"
    )


def test_schedules_linked_to_account():
    """select(.ferc_accounts[] == ...) resolves the schedules that cite an account."""
    schedules = jq(
        f'[.[] | select(.ferc_accounts[] == "{KNOWN_ACCOUNT}")] | .[] | {{schedule, title}}',
        FERC2_SCHEDULES,
    )
    assert schedules, (
        f"Expected at least one schedule referencing account {KNOWN_ACCOUNT}"
    )


def test_xbrl_table_names_for_schedule():
    """Get XBRL table names for a specific schedule."""
    tables = jq(
        f'.[] | select(.schedule == "{KNOWN_FERC2_SCHEDULE}") | .xbrl_tables[]',
        FERC2_SCHEDULES,
    )
    if not isinstance(tables, list):
        tables = [tables]
    assert tables, f"Expected schedule {KNOWN_FERC2_SCHEDULE} to have XBRL tables"


def test_shape_of_the_data():
    """Every record has the documented typed fields; pudl_tables/dbf_tables are empty."""
    schedules = jq(".", FERC2_SCHEDULES)
    assert schedules, "ferc2_schedules.json should not be empty"
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
        assert schedule["pudl_tables"] == [], (
            "Form 2 is not yet integrated into PUDL; pudl_tables should be empty "
            f"for schedule {schedule['schedule']}"
        )
