# Spec Tests Policy

This document defines how we write executable specs in `tests/` and how fixtures are generated.

## Goals
- Use Python spec code as the only source of truth.
- Generate deterministic `fixtures/**/*.json` via pytest.
- Keep YAML specs as documentation only; do not execute them.

## Baseline Requirements
- Executable: tests must run in a pure Python environment with no external daemon.
- Deterministic: identical inputs always produce identical outputs.
- Minimal: each case isolates a single behavior or error branch.
- Traceable: case names must be stable and human-readable.
- Canonical output: `pre_state`, `input`, `expected` must be present.
- Error codes: use the canonical `ErrorCode` names from the spec.

## Authoring Guidelines
- Organize tests by module under `tests/`.
- Use `state_test_group(rel_path, name, pre_state, tx)` to write to the desired fixture file.
- Cover success path, main error branches, and boundary values.
- Reuse common builders from `tests/helpers.py` where possible.

## Output Flow
1. Write tests in `tests/`.
2. Generate fixtures:
   `PYTHONPATH=~/tos-spec/src:~/tos-spec .venv/bin/python -m pytest -q ~/tos-spec --output ~/tos-spec/fixtures`
3. Generate vectors:
   `.venv/bin/python tools/fixtures_to_vectors.py --fixtures fixtures --vectors vectors/execution`

## Non-goals
- No direct YAML → pytest translation.
- No external dependencies during test execution.
