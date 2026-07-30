"""Tests for skills/pudl/scripts/fetch_descriptor.py.

Exactly one test in this module makes a real network call — downloading the
smallest of the eleven descriptors (ferc714_xbrl_datapackage.json, ~65 KB) from the
real S3 bucket, via a module-scoped fixture, so the suite verifies the script
actually works against the real service it's built for. Compare
dev/tools/check_datapackage_catalog_urls.py, which similarly makes live requests in
CI rather than mocking them.

Every other test reuses that one download's bytes locally — cache-hit/TTL/--force
behavior is about *whether* fetch_one() calls the network, which is verified by
patching urllib.request.urlopen to fail (or count calls) rather than by making
further live S3 round trips. An earlier version of this suite made one live call per
test (6 total) and took ~80s with occasional stalls from the same S3 latency spikes
the retry logic exists to survive; sharing one real download avoids re-introducing
that flakiness into the test suite itself.

Run:  pixi run pytest dev/skills/pudl/tests/test_fetch_descriptor.py -v
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

# fetch_descriptor.py is a distributed skill script, not a dev-only one, so it lives
# under skills/pudl/scripts/ rather than dev/skills/pudl/scripts/. Pytest runs these
# tests from the repository context where this path injection is valid, but static
# analyzers may still report unresolved-import warnings.
sys.path.insert(
    0,
    str(
        Path(__file__).parent.parent.parent.parent.parent
        / "skills"
        / "pudl"
        / "scripts"
    ),
)

from typing import Self

import fetch_descriptor

SMALLEST_DESCRIPTOR = "ferc714_xbrl_datapackage.json"


class _FakeResponse:
    """Minimal stand-in for the object urllib.request.urlopen()'s context manager yields."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


def test_ferceqr_uses_its_own_base_url() -> None:
    """Static routing check, no network: FERC EQR is hosted under a separate S3 prefix."""
    assert fetch_descriptor._DESCRIPTOR_URLS[
        "ferceqr_parquet_datapackage.json"
    ].startswith(fetch_descriptor._FERCEQR)


def test_other_descriptors_use_the_nightly_base_url() -> None:
    """Static routing check, no network: every non-EQR descriptor is under /nightly."""
    for name in fetch_descriptor.DESCRIPTORS:
        if name == "ferceqr_parquet_datapackage.json":
            continue
        assert fetch_descriptor._DESCRIPTOR_URLS[name].startswith(
            fetch_descriptor._NIGHTLY
        )


def test_raw_ferc_form_descriptors_point_at_their_own_subdirectory() -> None:
    """Static routing check, no network: each raw per-form FERC descriptor (e.g.
    ferc1_xbrl_datapackage.json) is cached under a disambiguated local filename but
    fetched from the shared remote name `datapackage.json` inside that form/era's own
    S3 subdirectory, since every such subdirectory publishes a same-named descriptor."""
    url = fetch_descriptor._DESCRIPTOR_URLS["ferc1_xbrl_datapackage.json"]
    assert url == f"{fetch_descriptor._NIGHTLY}/ferc1_xbrl/datapackage.json"


@pytest.fixture(scope="module")
def real_fetch_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[tuple[str, int, str, bool], bytes]:
    """The one live S3 call this whole module makes, shared by every test below."""
    cache_dir = tmp_path_factory.mktemp("real_fetch_once")
    original_cache_dir = fetch_descriptor.CACHE_DIR
    fetch_descriptor.CACHE_DIR = cache_dir
    try:
        result = fetch_descriptor.fetch_one(SMALLEST_DESCRIPTOR)
    finally:
        fetch_descriptor.CACHE_DIR = original_cache_dir
    data = (cache_dir / SMALLEST_DESCRIPTOR).read_bytes()
    return result, data


def test_fetch_one_downloads_the_real_smallest_descriptor(
    real_fetch_result: tuple[tuple[str, int, str, bool], bytes],
) -> None:
    (filename, size, digest, was_cached), data = real_fetch_result

    assert filename == SMALLEST_DESCRIPTOR
    assert was_cached is False  # nothing was cached yet for this fresh tmp dir
    assert len(data) == size
    assert hashlib.sha256(data).hexdigest()[:12] == digest
    # It should be the real descriptor, not an error page or placeholder.
    descriptor = json.loads(data)
    assert "resources" in descriptor


@pytest.fixture
def prepopulated_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    real_fetch_result: tuple[tuple[str, int, str, bool], bytes],
) -> Path:
    """A tmp cache dir seeded with the one real download's bytes — no network needed
    to set up a "cache already has this file" starting state for the tests below."""
    _result, data = real_fetch_result
    monkeypatch.setattr(fetch_descriptor, "CACHE_DIR", tmp_path)
    (tmp_path / SMALLEST_DESCRIPTOR).write_bytes(data)
    return tmp_path


def test_fetch_one_reuses_a_fresh_cache_without_a_network_call(
    prepopulated_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("fetch_one() hit the network despite a fresh cache entry")

    monkeypatch.setattr(fetch_descriptor.urllib.request, "urlopen", _fail_if_called)

    filename, _size, _digest, was_cached = fetch_descriptor.fetch_one(
        SMALLEST_DESCRIPTOR
    )

    assert filename == SMALLEST_DESCRIPTOR
    assert was_cached is True


def test_force_bypasses_a_fresh_cache(
    prepopulated_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    real_fetch_result: tuple[tuple[str, int, str, bool], bytes],
) -> None:
    _result, data = real_fetch_result
    calls: list[str] = []

    def _fake_urlopen(url: str, timeout: float | None = None) -> _FakeResponse:
        calls.append(url)
        return _FakeResponse(data)

    monkeypatch.setattr(fetch_descriptor.urllib.request, "urlopen", _fake_urlopen)

    _filename, _size, _digest, was_cached = fetch_descriptor.fetch_one(
        SMALLEST_DESCRIPTOR, force=True
    )

    assert was_cached is False  # --force refetched despite the cache being fresh
    assert len(calls) == 1


def test_stale_cache_is_refetched(
    prepopulated_cache: Path,
    monkeypatch: pytest.MonkeyPatch,
    real_fetch_result: tuple[tuple[str, int, str, bool], bytes],
) -> None:
    _result, data = real_fetch_result
    calls: list[str] = []

    def _fake_urlopen(url: str, timeout: float | None = None) -> _FakeResponse:
        calls.append(url)
        return _FakeResponse(data)

    monkeypatch.setattr(fetch_descriptor.urllib.request, "urlopen", _fake_urlopen)
    # A negative TTL means any cached file, however new, already counts as stale —
    # avoids sleeping in the test to simulate real time passing.
    monkeypatch.setattr(fetch_descriptor, "CACHE_TTL_SECONDS", -1)

    _filename, _size, _digest, was_cached = fetch_descriptor.fetch_one(
        SMALLEST_DESCRIPTOR
    )

    assert was_cached is False
    assert len(calls) == 1
