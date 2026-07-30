# PUDL Dev Maintainer Guide

This file is for repository maintainers only. It is not part of installed skill
content and should not be referenced from distributed skill docs.

## Scope

Use this guide when updating the pudl skill's test fixtures or regenerating the
offline descriptor sample used by `dev/skills/pudl/tests/`.

## Test fixtures

Two kinds of fixture back the pudl test suite:

- **Static assets** — `skills/pudl/assets/ferc_electricity_accounts.json`,
    `ferc1_schedules.json`, and `ferc2_schedules.json` are the same files the
    installed skill ships and queries. Tests run the documented jq examples
    directly against them; no separate dev fixture is needed.
- **`dev/skills/pudl/assets/pudl_parquet_datapackage_sample.json`** — a small,
    offline stand-in for the live, nightly-refreshed
    `pudl_parquet_datapackage.json` descriptor (~4.4 MB, never checked into the
    repo since it would be stale within a day). It backs the tests for the
    live-descriptor jq examples in `metadata-and-querying.md` and
    `data-sources.md` — docstring/RST parsing, per-resource `sources`
    provenance, and the `unit_registry`.

## Regenerating the descriptor sample

The sample is extracted verbatim from a real descriptor by
`dev/skills/pudl/scripts/build_metadata_fixture.py` — field values are never
hand-invented, only the set of resources/sources/schema fields is narrowed.
Regenerate it whenever PUDL's upstream schema changes in a way the tests
depend on (a new field, a changed description, a `unit_registry` update):

```bash
pixi run python skills/pudl/scripts/fetch_descriptor.py pudl_parquet_datapackage.json
pixi run python dev/skills/pudl/scripts/build_metadata_fixture.py
pixi run prek run pretty-format-json --files dev/skills/pudl/assets/pudl_parquet_datapackage_sample.json
pixi run test-pudl
```

If a new documented example needs a resource, source, or field the sample
doesn't currently carry, add it to the `SOURCE_NAMES` list or `RESOURCE_FIELDS`
mapping in `build_metadata_fixture.py` — don't hand-edit the generated JSON.

## markitdown is deliberately not a pixi dependency

`test_markitdown_conversion.py` builds its own throwaway `uv`-managed venv rather than
using a pixi-installed `markitdown`. This isn't a stopgap — adding `markitdown[pdf]`
directly to this workspace's pixi environment currently fails to solve at all on
`osx-arm64` with Python ≥ 3.14: its transitive dependency chain
(`magika` → `onnxruntime`) has no wheel matching pixi's default macOS platform-tag
baseline for `cp314`, even though a plain `uv pip install "markitdown[pdf]"` on the
same machine resolves and runs it fine (`uv` resolves against the running machine;
pixi resolves against a portable baseline). If you try `pixi add markitdown` again
after an upstream release and it still fails, that's this same gap, not a fluke —
keep using the `uv`-venv pattern rather than fighting the pixi solver.

## Guardrails

- Keep distributed skill docs free of references to dev-only paths and scripts.
- If runtime agent guidance genuinely depends on an artifact, move that
    artifact into distributed `skills/pudl/` content first.
