#!/usr/bin/env python3
"""Check availability of datapackage URLs in the in-the-wild catalog.

Usage:
    pixi run python dev/tools/check_datapackage_catalog_urls.py

Exits non-zero if one or more URLs are unavailable.
"""

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG_PATH = (
    REPO_ROOT / "dev/skills/datapackage/assets/datapackage-in-the-wild.json"
)
DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_WORKERS = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help=f"Path to catalog JSON (default: {DEFAULT_CATALOG_PATH})",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"Per-request timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Concurrent worker count (default: {DEFAULT_WORKERS})",
    )
    return parser.parse_args()


def load_entries(catalog_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Catalog missing 'entries' list")
    return entries


def _request(url: str, method: str, timeout_seconds: int) -> tuple[int, str]:
    response = requests.request(
        method=method,
        url=url,
        allow_redirects=True,
        timeout=timeout_seconds,
        headers={
            "User-Agent": "agent-skills-datapackage-catalog-check/1.0",
            "Accept": "application/json,*/*;q=0.8",
        },
    )
    return response.status_code, response.url


def check_url(url: str, timeout_seconds: int) -> tuple[bool, str]:
    try:
        status, final_url = _request(url, "HEAD", timeout_seconds)
        if 200 <= status < 400:
            return True, f"HEAD {status}"
        if status not in {405, 501}:
            return False, f"HEAD {status} ({final_url})"
    except requests.RequestException as err:
        # Some hosts reject HEAD or have TLS/proxy quirks; retry with GET.
        head_error = str(err)
        try:
            status, final_url = _request(url, "GET", timeout_seconds)
            if 200 <= status < 400:
                return True, f"GET {status} (HEAD failed: {head_error})"
            return False, f"GET {status} ({final_url})"
        except requests.RequestException as get_err:
            return False, f"HEAD/GET failed: {head_error}; {get_err}"

    try:
        status, final_url = _request(url, "GET", timeout_seconds)
        if 200 <= status < 400:
            return True, f"GET {status}"
        return False, f"GET {status} ({final_url})"
    except requests.RequestException as err:
        return False, f"GET failed: {err}"


def main() -> int:
    args = parse_args()
    entries = load_entries(args.catalog)

    checks: list[tuple[str, str, str]] = []
    for entry in entries:
        entry_id = str(entry.get("id", "<missing-id>"))
        url = entry.get("datapackage_url")
        if not isinstance(url, str) or not url:
            checks.append((entry_id, "", "missing datapackage_url"))
            continue
        checks.append((entry_id, url, ""))

    failures: list[tuple[str, str, str]] = []
    successes = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_entry = {
            executor.submit(check_url, url, args.timeout_seconds): (entry_id, url)
            for entry_id, url, issue in checks
            if not issue
        }

        for entry_id, _, issue in checks:
            if issue:
                failures.append((entry_id, "", issue))

        for future in as_completed(future_to_entry):
            entry_id, url = future_to_entry[future]
            ok, detail = future.result()
            if ok:
                successes += 1
            else:
                failures.append((entry_id, url, detail))

    print(
        f"Checked {len(checks)} entries: {successes} reachable, {len(failures)} failing"
    )

    if failures:
        print("\nUnavailable datapackage descriptors:")
        for entry_id, url, detail in sorted(failures):
            if url:
                print(f"- {entry_id}: {url} -> {detail}")
            else:
                print(f"- {entry_id}: {detail}")
        return 1

    print("All datapackage URLs are reachable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
