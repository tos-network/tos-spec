# TOS Spec & Conformance Testing Architecture

This repository defines the **executable specification** and **conformance testing** flow for TOS.
The goal is to keep multiple client implementations behaviorally identical by making the spec
machine-readable, testable, and capable of producing deterministic fixtures.

## Goals
- **Executable spec**: a Python specification that defines canonical behavior.
- **Deterministic fixtures**: generated from the spec and consumed by all clients.
- **Cross-client consistency**: the same inputs must yield the same outputs.
- **Layered coverage**: wire format, transaction validation, and state transitions are all verified.

## Architecture Overview

```
             +------------------------------+
             |   Python Executable Spec     |
             |   (src/tos_spec/*)           |
             +---------------+--------------+
                             |
                             | generates
                             v
             +------------------------------+
             |   Fixtures / Vectors         |
             |   (fixtures/*.json)          |
             +---------------+--------------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+----------------+   +----------------+   +----------------+
| Client A       |   | Client B       |   | Client C       |
| (Rust)         |   | (C)            |   | (Go, etc.)     |
+----------------+   +----------------+   +----------------+
         |                   |                   |
         +-------------------+-------------------+
                             |
                             v
             +------------------------------+
             |   Result Comparison          |
             |   (conformance harness)      |
             +------------------------------+
```

## Repository Structure

```
.
├── src/tos_spec/          # Executable spec (Python)
│   ├── config.py          # Constants and limits
│   ├── errors.py          # Error codes and exceptions
│   ├── types.py           # Core data models
│   ├── state_transition.py# verify/apply logic
│   ├── encoding.py        # Wire-format encoding
│   └── tx/                # Per-transaction specs
├── tests/                 # Pytest-based spec tests
├── tools/                 # Fixture generation/consumption
├── fixtures/              # Generated vectors
└── pyproject.toml
```

## Execution Model

### 1) Spec → Fixtures
- Specs are encoded as Python functions and data models.
- Pytest tests produce deterministic fixtures.
- Fixtures are stored as JSON and are versionable artifacts.

### 2) Fixtures → Clients
- Clients consume fixtures, execute them, and compare outputs to expected results.
- Divergence indicates a bug in the client or in the spec.

### 3) Cross-Client Conformance
- A harness runs the same fixtures across multiple clients.
- Output mismatches are surfaced for triage and resolution.

## Key Components

### Wire Format
- Canonical encoding is defined in `encoding.py`.
- Fixtures include `expected_hex` to validate encoding.

### Nonce & Failed-Tx Semantics
- `state_transition.py` enforces:
  - pre-validation vs execution failure behavior
  - fee deduction and nonce progression
  - rollback on execution failure

### Transaction Modules
- `tx/` contains per-type verification and apply logic.
- Each module is responsible for its boundary rules and state changes.

## Running the Fixture Flow

Generate fixtures:
```
PYTHONPATH=src .venv/bin/python tools/fill.py
```

Consume fixtures locally:
```
PYTHONPATH=src .venv/bin/python tools/consume.py
```

## Optional Rust YAML Backend

For YAML generation that matches Rust serialization, build the optional Rust extension:
```
cd rust_py/tos_yaml
maturin develop
```

When the `tos_yaml` module is installed, `tools/gen_hash_vectors.py` will prefer it over PyYAML.

## Design Principles
- **Spec is authoritative**: the executable spec defines correct behavior.
- **Fixtures are contracts**: all clients must match fixture expectations.
- **Deterministic outputs**: all generated data must be reproducible.
- **Small, composable units**: each spec module is testable in isolation.

## Extending
- Add new transaction types under `src/tos_spec/tx/`.
- Add tests under `tests/` and regenerate fixtures.
- Expand `encoding.py` and `state_transition.py` as coverage grows.
