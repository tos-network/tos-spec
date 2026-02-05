# TOS Spec & Conformance Testing Architecture

This repository defines the **executable specification** and **conformance testing** flow for TOS.
The goal is to keep multiple client implementations behaviorally identical by making the spec
machine-readable, testable, and capable of producing deterministic fixtures.

## Goals
- **Executable spec**: a Python specification that defines canonical behavior.
- **Deterministic fixtures**: generated from the spec and consumed by all clients.
- **Cross-client consistency**: the same inputs must yield the same outputs.
- **Layered coverage**: wire format, transaction validation, and state transitions are all verified.
- **Scenario/expected comparison**: fixtures define scenarios and expected results; vectors are the runnable form consumed by Labu.

## Scenario/Expected Comparison Model

This repo defines the authoritative **scenario + expected** contracts. The runtime behavior is:

1. **Fixtures are the spec truth** (human-readable, canonical intent).
2. **Vectors are the runnable scenarios** (machine-executable JSON derived from fixtures).
3. **Simulators execute vectors** and assert expected results.
4. **Labu only orchestrates and aggregates results**; it does not interpret fixtures.

This mirrors the Ethereum Hive approach: simulator-owned assertions, harness-owned orchestration.

## Fixtures vs Vectors (Responsibilities)

**Fixtures** and **vectors** serve different purposes and are owned by different layers of the stack:

**Fixtures (spec-owned)**  
Location: `fixtures/`  
Purpose: authoring/semantic truth of the spec. Fixtures describe the expected behavior and
are generated/validated by the executable Python spec. They are not necessarily in a
directly executable format for clients.

**Vectors (harness-owned, client-consumable)**  
Location: `vectors/`  
Purpose: executable, client-consumable test inputs used by the multi-client conformance
harness (Labu). Vectors are derived from fixtures and should be stable artifacts used for
cross-client comparison.

**Conversion responsibility**  
The spec layer is responsible for converting fixtures → vectors. The conformance harness
only consumes vectors (it does not transform fixtures). Spec/test generators produce
fixtures/vectors; the harness only runs them.

**Conversion script**  
Use the provided tool to mirror fixtures into vectors (schema-preserving copy):

```bash
python tools/fixtures_to_vectors.py
```

This creates/updates `vectors/` from `fixtures/` according to the mapping in
`tools/fixtures_to_vectors.py`.

**Conformance usage (Labu)**  
The Labu orchestrator (`~/labu`) consumes `vectors/`. Example:

```bash
python tools/fixtures_to_vectors.py
cd ~/labu
./labu --sim tos/execution --client tos-rust,avatar-c --vectors ~/tos-spec/vectors
```

You can also use the helper script:

```bash
python tools/run_conformance.py --sim tos/execution --client tos-rust,avatar-c
```

## Deterministic Accounts (Test Identities)

To make signatures, addresses, and miner behavior reproducible across clients and simulators,
we use a fixed set of deterministic test accounts stored in `vectors/accounts.json`.

**Purpose**
- Provide canonical addresses and private keys for vectors/signatures.
- Ensure conformance and simulators use the same miner and test identities.
- Keep all scenario artifacts reproducible and portable.

**Source of truth**
- `vectors/accounts.json` is the authoritative list of test identities.
- Roles are fixed (e.g., `Miner`, `Alice`, `Bob`, ...).
- The same identities are used by:
  - vector generation/signing
  - conformance server (miner key)
  - simulators

**Usage**
- Vectors reference these addresses directly.
- The conformance server should read the miner key from this list (or via env pointing to it).
  - Environment: `LABU_ACCOUNTS_PATH` can point to `vectors/accounts.json`.

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
│   └── transactions/      # Legacy transaction fixtures (mirrored from tck/specs/transactions)
├── vectors/               # Client-consumable vectors for Labu
└── pyproject.toml
```

## Execution Model

### 1) Spec → Fixtures
- Specs are encoded as Python functions and data models.
- Pytest tests produce deterministic fixtures.
- Fixtures are stored as JSON and are versionable artifacts.

**Fixture formats by layer**
- Execution-layer fixtures: JSON (transactions, state transitions, wire-format, error matrices).
- Consensus-layer fixtures: YAML (block structure, PoW, blockdag ordering, fork-choice/validation).
- Crypto fixtures: YAML (hash/HMAC and related crypto vectors).
 - Legacy transaction fixtures: YAML (ported from `tck/specs/transactions/`; source directory removed after migration).

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

When the `tos_yaml` module is installed, Python YAML generators will prefer it over PyYAML.

## Design Principles
- **Spec is authoritative**: the executable spec defines correct behavior.
- **Fixtures are contracts**: all clients must match fixture expectations.
- **Deterministic outputs**: all generated data must be reproducible.
- **Small, composable units**: each spec module is testable in isolation.

## Extending
- Add new transaction types under `src/tos_spec/tx/`.
- Add tests under `tests/` and regenerate fixtures.
- Expand `encoding.py` and `state_transition.py` as coverage grows.
