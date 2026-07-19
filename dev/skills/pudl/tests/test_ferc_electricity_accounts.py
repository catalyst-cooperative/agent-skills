"""Tests for the jq examples in references/ferc-electricity-accounts.md.

Runs each documented query against the real, shipped ferc_electricity_accounts.json
and checks it returns what the reference claims. A failing test names the jq
expression that broke so an agent can find and fix the stale example.

Run:  pixi run pytest dev/skills/pudl/tests/test_ferc_electricity_accounts.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from .conftest import FERC_ELECTRICITY_ACCOUNTS, KNOWN_ACCOUNT


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


def test_lookup_specific_account():
    """Look up a specific account by number."""
    account = jq(
        f'.[] | select(.account == "{KNOWN_ACCOUNT}")', FERC_ELECTRICITY_ACCOUNTS
    )
    assert account["account"] == KNOWN_ACCOUNT
    assert isinstance(account["description"], str) and account["description"]


def test_find_accounts_in_numeric_range():
    """Numeric-range test('^18[0-9]') matches only 18x-prefixed accounts."""
    accounts = jq(
        '[.[] | select(.account | test("^18[0-9]"))] | .[] | {account, description}',
        FERC_ELECTRICITY_ACCOUNTS,
    )
    assert accounts, "Expected at least one account in the 180-189 range"
    for account in accounts:
        assert account["account"].startswith("18"), (
            f"Account {account['account']} does not start with '18'"
        )


def test_om_transmission_expense_accounts():
    """chart == 'om_expenses' and section == '2. Transmission Expenses' filters correctly."""
    accounts = jq(
        '[.[] | select(.chart == "om_expenses" and .section == "2. Transmission Expenses")] |'
        " .[] | {account, description, operation_type}",
        FERC_ELECTRICITY_ACCOUNTS,
    )
    assert accounts, "Expected at least one O&M transmission expense account"
    for account in accounts:
        assert isinstance(account["account"], str)


def test_major_only_accounts():
    """select(.major_only) returns only accounts flagged major_only == true."""
    all_accounts = jq(".", FERC_ELECTRICITY_ACCOUNTS)
    expected = {a["account"] for a in all_accounts if a["major_only"]}
    result = jq("[.[] | select(.major_only)] | .[].account", FERC_ELECTRICITY_ACCOUNTS)
    assert set(result) == expected
    assert expected, "Expected at least one major_only account"


def test_shape_of_the_data():
    """Every record has the documented fields, with the documented types."""
    accounts = jq(".", FERC_ELECTRICITY_ACCOUNTS)
    assert accounts, "ferc_electricity_accounts.json should not be empty"
    expected_fields = {
        "account",
        "description",
        "chart",
        "section",
        "group",
        "operation_type",
        "major_only",
        "nonmajor_only",
        "reserved",
    }
    for account in accounts:
        assert set(account.keys()) == expected_fields, (
            f"Account {account.get('account')} has unexpected field set: {set(account.keys())}"
        )
        assert isinstance(account["major_only"], bool)
        assert isinstance(account["nonmajor_only"], bool)
        assert isinstance(account["reserved"], bool)
