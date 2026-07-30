#!/usr/bin/env python3
"""Download and cache PUDL datapackage descriptors from the nightly S3 build.

Descriptors are updated nightly and are never bundled with the skill — they would
become stale immediately. This script downloads copies into skills/pudl/assets/cache/
for use in evals and offline testing.

A cached file younger than CACHE_TTL_SECONDS is reused as-is, with no network call —
safe to re-run freely (e.g. once per agent turn) without re-downloading every time.
Pass --force to bypass the cache and refetch regardless of age.

Usage:
    python scripts/fetch_descriptor.py                  # all descriptors, cache-aware
    python scripts/fetch_descriptor.py pudl_parquet_datapackage.json  # one file
    python scripts/fetch_descriptor.py --force           # bypass the cache

The cached files are gitignored.
"""

import argparse
import hashlib
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_NIGHTLY = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly"
_FERCEQR = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr"

# Maps each local cache filename to its full descriptor URL on S3. The core PUDL
# descriptor and FERC EQR keep their filename in the URL, but each raw per-form FERC
# directory (e.g. nightly/ferc1_xbrl/) publishes a same-named datapackage.json, so the
# local cache filename below is a disambiguated <form>_<era>_datapackage.json name and
# the URL points at the actual remote path.
_DESCRIPTOR_URLS: dict[str, str] = {
    "pudl_parquet_datapackage.json": f"{_NIGHTLY}/pudl_parquet_datapackage.json",
    "ferc1_dbf_datapackage.json": f"{_NIGHTLY}/ferc1_dbf/datapackage.json",
    "ferc1_xbrl_datapackage.json": f"{_NIGHTLY}/ferc1_xbrl/datapackage.json",
    "ferc2_dbf_datapackage.json": f"{_NIGHTLY}/ferc2_dbf/datapackage.json",
    "ferc2_xbrl_datapackage.json": f"{_NIGHTLY}/ferc2_xbrl/datapackage.json",
    "ferc6_dbf_datapackage.json": f"{_NIGHTLY}/ferc6_dbf/datapackage.json",
    "ferc6_xbrl_datapackage.json": f"{_NIGHTLY}/ferc6_xbrl/datapackage.json",
    "ferc60_dbf_datapackage.json": f"{_NIGHTLY}/ferc60_dbf/datapackage.json",
    "ferc60_xbrl_datapackage.json": f"{_NIGHTLY}/ferc60_xbrl/datapackage.json",
    "ferc714_xbrl_datapackage.json": f"{_NIGHTLY}/ferc714_xbrl/datapackage.json",
    "ferceqr_parquet_datapackage.json": f"{_FERCEQR}/ferceqr_parquet_datapackage.json",
}

DESCRIPTORS: list[str] = list(_DESCRIPTOR_URLS)

CACHE_DIR = Path(__file__).parent.parent / "assets" / "cache"

# S3 latency is occasionally spiky (observed multi-second time-to-first-byte, and
# rare full stalls). These descriptors are at most a few MB; a real transfer that's
# still stuck at zero bytes after a few seconds is stalled, not slow, so the timeout
# is kept short and attempts retried, rather than waiting out a long timeout once.
REQUEST_TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

# Descriptors are refreshed nightly upstream, so a cached copy is treated as fresh
# for up to a day — long enough that repeated calls within a session (or across a
# few) reuse the local file instead of re-downloading, short enough to stay close to
# upstream's own refresh cadence.
CACHE_TTL_SECONDS = 24 * 60 * 60


def fetch_one(filename: str, force: bool = False) -> tuple[str, int, str, bool]:
    """Fetch one descriptor, retrying transient failures.

    Returns (filename, bytes, sha256, was_cached). If a cached copy exists and is
    younger than CACHE_TTL_SECONDS, it's reused with no network call unless
    force=True.
    """
    out = CACHE_DIR / filename
    if not force and out.exists():
        age_seconds = time.time() - out.stat().st_mtime
        if age_seconds < CACHE_TTL_SECONDS:
            data = out.read_bytes()
            digest = hashlib.sha256(data).hexdigest()[:12]
            return filename, len(data), digest, True

    url = _DESCRIPTOR_URLS.get(filename, f"{_NIGHTLY}/{filename}")

    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                data = resp.read()
            out.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()[:12]
            return filename, len(data), digest, False
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise RuntimeError(
        f"Failed to fetch {url} after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILENAME",
        help="Descriptor filename(s) to fetch. Defaults to all.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the cache and refetch even if a fresh copy already exists.",
    )
    args = parser.parse_args()
    targets = args.files or DESCRIPTORS
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch concurrently: these are independent files on the same host, so a slow
    # or stalled request for one no longer blocks the rest — total wall time tracks
    # the slowest single file instead of the sum of all of them.
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        future_to_name = {
            pool.submit(fetch_one, name, args.force): name for name in targets
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                filename, size, digest, was_cached = future.result()
                status = "cached" if was_cached else "fetched"
                print(
                    f"{filename}  ({status}, {size:,} bytes, sha256:{digest})",
                    flush=True,
                )
            except RuntimeError as exc:
                print(f"FAILED: {exc}", flush=True)
                failures.append(name)

    if failures:
        print(
            f"Done, with {len(failures)} failure(s): {', '.join(failures)}", flush=True
        )
        raise SystemExit(1)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
