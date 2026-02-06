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

## Template

See `tests/test_template_example.py` for a runnable, minimal template.

## Template Rules (Must Follow)
- **File name**: `tests/<module>/test_<thing>.py`
- **Fixture output**: always use `state_test_group` with a stable JSON path.
- **Case naming**: `snake_case` with clear behavior.
- **One behavior per test**: do not mix multiple failures in one case.
- **No randomness**: if needed, use fixed seeds or fixed values.

## Fixture Path Conventions
- Transactions: `transactions/<group>/<name>.json`
- Consensus/Models/Security: `consensus/<name>.json`, `models/<name>.json`, `security/<name>.json`
- Syscalls: `syscalls/<name>.json`
- API: `api/<name>.json`

## Output Flow
1. Write tests in `tests/`.
2. Generate fixtures:
   `PYTHONPATH=~/tos-spec/src:~/tos-spec .venv/bin/python -m pytest -q ~/tos-spec --output ~/tos-spec/fixtures`
3. Generate vectors:
   `.venv/bin/python tools/fixtures_to_vectors.py --fixtures fixtures --vectors vectors/execution`

## Non-goals
- No direct YAML → pytest translation.
- No external dependencies during test execution.
