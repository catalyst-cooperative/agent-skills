"""Shared constants for the datapackage skill tests.

All dataset dimensions, column names, and resource names are derived directly
from the generator module (scripts/generate_examples.py) so that they cannot
drift out of sync with the actual example data.  If you change the data model
(add a column, change a field type, add a station) you only need to edit the
generator; these constants update automatically.
"""

import datetime
import sys
from pathlib import Path

# Pytest runs these tests from the repository context where this path injection
# is valid, but static analyzers may still report unresolved-import warnings.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from generate_examples import (
    READINGS_RESOURCE_BASE,
    SAMPLE_PERIODS,
    STATIONS,
    STATIONS_RESOURCE_BASE,
    Reading,
    Station,
)

# Root of the generated example packages
EXAMPLES = Path(__file__).parent.parent / "assets" / "examples"

# ── Dataset dimensions ────────────────────────────────────────────────────────
STATION_COUNT: int = len(STATIONS)
READING_COUNT = STATION_COUNT * SAMPLE_PERIODS

# ── Descriptor structure ──────────────────────────────────────────────────────
RESOURCE_NAMES = [STATIONS_RESOURCE_BASE["name"], READINGS_RESOURCE_BASE["name"]]

# Column names in definition order (Pydantic preserves field order)
STATION_COLUMNS: list[str] = list(Station.model_fields.keys())
READING_COLUMNS: list[str] = list(Reading.model_fields.keys())

# Columns that should carry a proper date type in typed backends (Parquet, DuckDB, SQLite)
DATE_COLUMNS = {
    STATIONS_RESOURCE_BASE["name"]: [
        name
        for name, f in Station.model_fields.items()
        if f.annotation is datetime.date
    ],
    READINGS_RESOURCE_BASE["name"]: [
        name
        for name, f in Reading.model_fields.items()
        if f.annotation is datetime.date
    ],
}
