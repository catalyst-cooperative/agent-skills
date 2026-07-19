#!/usr/bin/env python3
"""Download and cache PUDL datapackage descriptors from the nightly S3 build.

Descriptors are updated nightly and are never bundled with the skill — they would
become stale immediately. This script downloads fresh copies into
skills/pudl/assets/cache/ for use in evals and offline testing.

Usage:
    python scripts/fetch_descriptor.py           # download all descriptors
    python scripts/fetch_descriptor.py pudl_parquet_datapackage.json  # one file

The cached files are gitignored. Re-run to refresh them.
"""

import argparse
import hashlib
import urllib.request
from pathlib import Path

_NIGHTLY = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly"
_FERCEQR = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/ferceqr"

# Maps each descriptor filename to its S3 base URL.
# Most descriptors live under /nightly; FERC EQR has its own path.
_DESCRIPTOR_URLS: dict[str, str] = {
    "pudl_parquet_datapackage.json": _NIGHTLY,
    "ferc1_xbrl_datapackage.json": _NIGHTLY,
    "ferc2_xbrl_datapackage.json": _NIGHTLY,
    "ferc6_xbrl_datapackage.json": _NIGHTLY,
    "ferc60_xbrl_datapackage.json": _NIGHTLY,
    "ferc714_xbrl_datapackage.json": _NIGHTLY,
    "ferceqr_parquet_datapackage.json": _FERCEQR,
}

DESCRIPTORS = list(_DESCRIPTOR_URLS)

CACHE_DIR = Path(__file__).parent.parent / "assets" / "cache"


def fetch_one(filename: str) -> None:
    base = _DESCRIPTOR_URLS.get(filename, _NIGHTLY)
    url = f"{base}/{filename}"
    out = CACHE_DIR / filename
    print(f"Fetching {url} ...")
    with urllib.request.urlopen(url) as resp:  # noqa: S310
        data = resp.read()
    out.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()[:12]
    print(f"  → {out.name}  ({len(data):,} bytes, sha256:{digest})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILENAME",
        help="Descriptor filename(s) to fetch. Defaults to all.",
    )
    args = parser.parse_args()
    targets = args.files or DESCRIPTORS
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for filename in targets:
        fetch_one(filename)
    print("Done.")


if __name__ == "__main__":
    main()
