"""Shared fixtures and constants for the pudl skill tests.

Paths point at the skill's distributed static assets (queried directly by
name, the way an agent would) and at the small offline descriptor fixture
built by ../scripts/build_metadata_fixture.py (for the live-descriptor
examples in metadata-and-querying.md and data-sources.md, which would
otherwise require a network fetch).
"""

from pathlib import Path

SKILL_ASSETS = (
    Path(__file__).parent.parent.parent.parent.parent / "skills" / "pudl" / "assets"
)
DEV_ASSETS = Path(__file__).parent.parent / "assets"

FERC_ELECTRICITY_ACCOUNTS = SKILL_ASSETS / "ferc_electricity_accounts.json"
FERC1_SCHEDULES = SKILL_ASSETS / "ferc1_schedules.json"
FERC2_SCHEDULES = SKILL_ASSETS / "ferc2_schedules.json"

# Small offline stand-in for pudl_parquet_datapackage.json (see build_metadata_fixture.py
# for how it was derived from a live descriptor).
SAMPLE_DESCRIPTOR = DEV_ASSETS / "pudl_parquet_datapackage_sample.json"

# Known-good values, verified against the current asset files, so tests don't
# hardcode brittle guesses about which accounts/schedules exist.
KNOWN_ACCOUNT = "182.3"  # "Other regulatory assets"
KNOWN_ACCOUNT_SCHEDULE = (
    "232"  # FERC1 and FERC2 schedule "Other Regulatory Assets", both reference 182.3
)
KNOWN_FERC1_SCHEDULE = "204"  # "Electric Plant in Service", accounts 101-106
KNOWN_FERC2_SCHEDULE = "204"  # "Gas Plant in Service"
