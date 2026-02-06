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
Use the provided tool to convert pytest-generated JSON fixtures into vectors:

```bash
python tools/fixtures_to_vectors.py
```

This creates/updates `vectors/` from JSON fixtures under `fixtures/` according to the mapping in
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
├── rust_py/               # Optional Rust PyO3 extensions
│   ├── tos_signer/        # Cryptographic signing & tx encoding
│   └── tos_yaml/          # YAML serialization backend
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
- Execution-layer fixtures: JSON (pytest-generated transactions, state transitions, wire-format).
- YAML specs are documentation only; pytest generates JSON fixtures from executable tests.
- YAML specs are mirrored into JSON as non-runnable `test_vectors` for unified consumption.

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

See `Policy.md` for the spec test policy and authoring guidelines.

## Dependencies

This repo expects a local virtualenv in `.venv` and a working pytest stack.
Key Python packages: `pytest`, `blake3`, `pyyaml`, `pycryptodomex`.

Quick setup (from repo root):
```
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
pip install pytest
```

Make targets (optional):
```
make venv
make install
make fixtures
make vectors
make consume
```

Generate fixtures (pytest → fixtures):
```
PYTHONPATH=~/tos-spec/src:~/tos-spec .venv/bin/python -m pytest -q --output ~/tos-spec/fixtures
```

Pytest can emit multiple fixture files (e.g., `tx_core.json`, `transactions/core/burn.json`)
depending on which test modules are enabled.

Convert fixtures → vectors:
```
PYTHONPATH=~/tos-spec/src:~/tos-spec .venv/bin/python tools/fixtures_to_vectors.py
```

Consume fixtures locally (spec runner):
```
PYTHONPATH=~/tos-spec/src:~/tos-spec .venv/bin/python tools/consume.py
```

## Rust Extensions (`rust_py/`)

The repository includes optional Rust-based PyO3 extensions under `rust_py/`.
Each extension is built with [maturin](https://github.com/PyO3/maturin) and installed
into the virtualenv as an editable package.

Prerequisites: a working Rust toolchain and `maturin` (`pip install maturin`).

### tos_yaml — YAML serialization backend

For YAML generation that matches Rust serialization order, build the extension:

```bash
cd rust_py/tos_yaml && maturin develop --release
```

When installed, Python YAML generators will prefer it over PyYAML.

**API**

| Function | Description |
|----------|-------------|
| `dump_yaml(json_str: str) -> str` | Convert a JSON string to YAML. |

### tos_signer — cryptographic signing and transaction encoding

Provides Ristretto-based key derivation, signing, and transaction serialization.
Used by the test harness (`test_accounts.sign_transaction`) and available for
direct use when building transactions from Python.

```bash
cd rust_py/tos_signer && maturin develop --release
```

All functions return `list[int]`; wrap with `bytes()` to get a `bytes` object
(e.g. `sig = bytes(tos_signer.sign_data(data, seed))`).

**Key management**

| Function | Description |
|----------|-------------|
| `get_public_key(seed_byte: int) -> list[int]` | Derive 32-byte compressed public key from a single seed byte (0-255). |
| `get_public_key_from_private(private_key: bytes) -> list[int]` | Derive 32-byte compressed public key from a raw 32-byte private key. |

**Signing**

| Function | Description |
|----------|-------------|
| `sign_data(data: bytes, seed_byte: int) -> list[int]` | Sign arbitrary data using a seed-byte keypair. Returns 64-byte signature. |
| `sign_with_key(data: bytes, private_key: bytes) -> list[int]` | Sign arbitrary data using a raw 32-byte private key. Returns 64-byte signature. |

**Transaction frame assembly**

| Function | Description |
|----------|-------------|
| `build_signing_bytes(version, chain_id, source, tx_type_id, encoded_payload, fee, fee_type, nonce, ref_hash, ref_topo) -> list[int]` | Assemble the unsigned transaction frame for signing. Byte layout: `[version:1][chain_id:1][source:32][tx_type_id:1][payload:var][fee:8][fee_type:1][nonce:8][ref_hash:32][ref_topo:8]`. Output is byte-identical to `encoding.encode_signing_bytes()`. |

**Payload encoding**

| Function | Description |
|----------|-------------|
| `encode_transfer_payload(transfers: list[tuple]) -> list[int]` | Encode transfer payload. Each tuple: `(asset: bytes, destination: bytes, amount: int)` or `(asset, destination, amount, extra_data: Optional[bytes])`. Format: `[count:u16][asset:32][dest:32][amount:u64][optional_extra]...` |
| `encode_burn_payload(asset: bytes, amount: int) -> list[int]` | Encode burn payload. Format: `[asset:32][amount:u64]`. |

**All-in-one convenience**

| Function | Description |
|----------|-------------|
| `sign_transfer(seed_byte, chain_id, nonce, fee, fee_type, ref_hash, ref_topo, transfers) -> list[int]` | Build a transfer transaction and sign it in one call. Returns 64-byte signature. Uses version=T1 and tx_type_id=1 (Transfers) internally. |

**Example: sign a transfer**

```python
import tos_signer

asset = b"\x00" * 32          # TOS native asset
dest  = b"\x01" * 32          # recipient address
ref_h = b"\x09" * 32          # reference block hash

# One-step: build + sign
sig = bytes(tos_signer.sign_transfer(
    seed_byte=1, chain_id=3, nonce=0, fee=1000, fee_type=0,
    ref_hash=ref_h, ref_topo=100,
    transfers=[(asset, dest, 500_000)],
))

# Or step-by-step:
payload = bytes(tos_signer.encode_transfer_payload([
    (asset, dest, 500_000, b"memo"),
]))
frame = bytes(tos_signer.build_signing_bytes(
    version=1, chain_id=3,
    source=bytes(tos_signer.get_public_key(1)),
    tx_type_id=1, encoded_payload=payload,
    fee=1000, fee_type=0, nonce=0,
    ref_hash=ref_h, ref_topo=100,
))
sig = bytes(tos_signer.sign_data(frame, seed_byte=1))
```

## Design Principles
- **Spec is authoritative**: the executable spec defines correct behavior.
- **Fixtures are contracts**: all clients must match fixture expectations.
- **Deterministic outputs**: all generated data must be reproducible.
- **Small, composable units**: each spec module is testable in isolation.

## Extending
- Add new transaction types under `src/tos_spec/tx/`.
- Add tests under `tests/` and regenerate fixtures.
- Expand `encoding.py` and `state_transition.py` as coverage grows.
