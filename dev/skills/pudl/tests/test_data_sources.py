"""Tests for the jq examples in references/data-sources.md.

Runs each documented query against the small offline descriptor fixture (see
../scripts/build_metadata_fixture.py) rather than the live nightly descriptor,
so these tests stay fast, deterministic, and network-free.

Run:  pixi run pytest dev/skills/pudl/tests/test_data_sources.py -v
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from .conftest import SAMPLE_DESCRIPTOR


def jq(expr: str, path: Path = SAMPLE_DESCRIPTOR) -> Any:
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


def test_find_source_by_title_keyword() -> None:
    """A case-insensitive title search finds the balancing-authority source."""
    matches = jq('[.sources[] | select(.title | test("balancing authority"; "i"))]')
    assert matches, "Expected a source with 'balancing authority' in its title"
    assert any(s["name"] == "eia930" for s in matches)


def test_find_source_by_keyword_list() -> None:
    """A keyword-list search finds sources tagged with a topic like 'emissions'."""
    matches = jq(
        r'[.sources[] | select(.keywords[]? | test("emissions"; "i")) | {name, title}]'
    )
    names = {m["name"] for m in matches}
    assert "epacems" in names


def test_get_short_code_for_source() -> None:
    """Resolve a source's short code from a title search (e.g. CEMS -> epacems)."""
    name = jq('.sources[] | select(.title | test("CEMS"; "i")) | .name')
    assert name == "epacems"


def test_get_docs_url_for_known_short_code() -> None:
    """documentation resolves to the source's PUDL docs page."""
    url = jq(
        '.sources[] | select(.name == "ferc1") | .documentation', SAMPLE_DESCRIPTOR
    )
    assert url.startswith("https://docs.catalyst.coop/pudl/")


def test_sources_with_no_docs_page() -> None:
    """mshamines has no documentation page yet, and is flagged correctly by a null check."""
    names = jq("[.sources[] | select(.documentation == null) | .name]")
    assert "mshamines" in names


def test_list_every_source_short_code_and_title() -> None:
    """Every source has both a short code and a human-readable title."""
    rows = jq(r'.sources[] | "\(.name)\t\(.title)"')
    assert rows
    for row in rows:
        name, _, title = row.partition("\t")
        assert name
        assert title


def test_pudl_source_is_not_an_external_dataset() -> None:
    """The 'pudl' source entry describes PUDL itself, not an ingested external dataset."""
    source = jq('.sources[] | select(.name == "pudl")')
    assert "Public Utility Data Liberation" in source["title"]
