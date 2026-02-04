# TOS Scenario/Expected Comparison Framework

## Goal
Define a deterministic, executable **scenario + expected** framework so that TOS clients
can be tested in a uniform, repeatable way across single-client and multi-client runs.

## Core Constraints
- **Fixtures are the spec truth**: human-authored canonical intent.
- **Vectors are runnable**: machine-executable JSON derived from fixtures.
- **Simulators own assertions**: they execute vectors and verify expected results.
- **Harness only orchestrates**: starts containers, aggregates logs/results.
- **Determinism**: same inputs produce the same outputs across clients.

## Directory Roles & Ownership
- `fixtures/` (spec-owned)
  - Source of truth for scenarios and expected behavior.
  - Written/validated by the executable spec.
- `vectors/` (harness-owned consumption)
  - Runnable scenarios derived from fixtures.
  - JSON is the primary format.
- `tools/`
  - Conversion pipeline `fixtures -> vectors`.
  - Validation/report tooling.
- `~/lab/simulators/tos/`
  - Execution engines that consume vectors and assert expected results.

## Vector Schema (JSON)

```json
{
  "name": "string",
  "description": "string",
  "pre_state": {
    "network_chain_id": 0,
    "global_state": {
      "total_supply": 0,
      "total_burned": 0,
      "total_energy": 0,
      "block_height": 0,
      "timestamp": 0
    },
    "accounts": [
      { "address": "...", "balance": 0, "nonce": 0, "frozen": 0, "energy": 0, "flags": 0, "data": "" }
    ]
  },
  "input": {
    "kind": "tx | block | rpc",
    "wire_hex": "...",
    "rpc": { "method": "...", "params": {} }
  },
  "expected": {
    "success": true,
    "error_code": 0,
    "state_digest": "hex32",
    "post_state": {
      "global_state": { },
      "accounts": [ ]
    }
  }
}
```

## Simulator Behavior
- **Single-client mode**:
  - Execute scenario against one client.
  - Compare `expected` directly (account-level, global state, error codes).
- **Multi-client mode**:
  - Execute scenario against all clients.
  - Verify each client matches `expected`.
  - Also check cross-client consistency.

## Execution Flow
1. Author/maintain fixtures in `fixtures/`.
2. Convert fixtures to vectors via `tools/fixtures_to_vectors.py`.
3. Simulators read vectors and execute against clients.
4. Expected results are asserted by simulators.
5. Harness aggregates logs and produces report output.

## Verification Strategy
- **Required assertions**:
  - `expected.success`
  - `expected.error_code`
- **Recommended assertions**:
  - `expected.post_state` (account-level, field-by-field)
  - `expected.global_state`
  - `expected.state_digest`
- **Optional assertions**:
  - Events, receipts, or additional protocol-specific outputs.

## State Digest
The state digest must be deterministic across implementations. A stable definition is required in
the spec. The digest should be derived from a canonical, ordered encoding of `post_state`.

## Notes
- Vectors are JSON-first to minimize ambiguity and maximize tooling support.
- Fixtures may remain JSON/YAML depending on layer needs, but conversion must always produce JSON vectors.
