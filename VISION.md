# TOS Conformance Testing Vision

This document defines the long-term testing strategy for TOS. It describes the
principles behind the conformance testing framework, the layered testing architecture,
current coverage, and the roadmap for expanding test coverage across all system layers.

## Testing Philosophy

TOS conformance testing is built on four principles:

1. **Deterministic and offline.** Every test vector is self-contained. Given a pre-state
   and a set of inputs, any correct client must arrive at the same post-state. No network
   access, no randomness, no timing dependencies.

2. **Client-agnostic.** The specification is written in Python as an executable reference.
   It produces test vectors that any implementation — in any language — can consume.
   The spec is the single source of truth.

3. **Layered verification.** Testing is organized into layers of increasing complexity,
   from pure computation up through network-level interoperability. Each layer builds
   on the correctness guarantees of the layers below it.

4. **Fork-aware.** Test vectors are parameterized by protocol version. The same
   transaction may produce different results under different protocol rules. Tests
   explicitly cover fork boundaries — the last block before an upgrade and the first
   block after — to verify that clients activate new rules at the correct height.

The core question every test answers:

> Given this pre-state and these inputs, do you arrive at this post-state?

## Testing Pyramid

Tests are organized into six layers. Lower layers are faster, more numerous, and
provide the foundation for higher layers.

```
                    +---------------------------+
                    |  L5: Cross-Client Interop |
                    +---------------------------+
                   /                             \
              +-----------------------------------+
              |    L4: Network Protocol (P2P)     |
              +-----------------------------------+
             /                                     \
        +-------------------------------------------+
        |      L3: API Boundary (RPC / WS)          |
        +-------------------------------------------+
       /                                             \
  +-------------------------------------------------+
  |     L2: Block Processing (multi-tx, rewards)    |
  +-------------------------------------------------+
  |     L1: Single Transaction State Transition     |
  +-------------------------------------------------+
  |     L0: Pure Computation (codec, crypto)        |
  +-------------------------------------------------+
```

### Layer 0 — Pure Computation

Stateless functions with no blockchain context. Tests verify that serialization,
hashing, and cryptographic primitives produce correct outputs.

- Wire format encoding and decoding
- BLAKE3 hashing, HMAC computation
- Ristretto255 key derivation and signature verification
- RandomX proof-of-work verification
- Transaction ID computation

### Layer 1 — Single Transaction State Transition

The current primary focus. Each test provides a pre-state (account balances, energy
resources, domain data), a single transaction, and the expected post-state or error code.

- 43 transaction types across 11 handler modules
- Covers success paths, error paths, and edge cases
- Verifies balance changes, nonce advancement, state digest

### Layer 2 — Block Processing

Multiple transactions within a block, block reward distribution, and DAG ordering.
Tests at this layer verify behavior that only emerges from multi-transaction execution.

- Transaction ordering within a block
- Cumulative fee and reward calculation
- DAG parent selection and fork choice
- Finality computation across block sequences
- Coinbase reward distribution and halving schedule

### Layer 3 — API Boundary

API conformance is split into two categories with distinct testing requirements.

**Query APIs** (read-only). Tests verify that clients expose the same query interface
with identical response formats.

- JSON-RPC method signatures and return types
- WebSocket subscription behavior
- Error code and error message consistency
- Pagination and filtering behavior

**Block production APIs** (write path). Tests verify the interface through which
miners and block producers submit new blocks and the client validates them.

- Block submission and validation responses
- Transaction pool submission and status reporting
- Block template construction (transaction selection, reward calculation)
- Rejection of invalid blocks with correct error codes

### Layer 4 — Network Protocol

Peer-to-peer message exchange, block propagation, and chain synchronization. Tests at
this layer require simulated network environments.

- Block announcement and relay
- Transaction pool synchronization
- Peer discovery and handshake
- Chain sync from genesis or checkpoint

**Fault injection and chaos testing.** Beyond correct-path protocol tests, this layer
includes adversarial scenarios that verify client resilience:

- Network partitions (split-brain, asymmetric connectivity)
- Message reordering, duplication, and corruption
- Peer disconnection during sync
- Resource exhaustion (connection flooding, oversized messages)
- Clock skew between peers

### Layer 5 — Cross-Client Interoperability

End-to-end multi-client testing using the Labu orchestration harness. Multiple client
implementations process the same chain and must arrive at identical state.

- Multi-client block production and validation
- State root agreement after N blocks
- Graceful handling of invalid blocks from peers
- Client restart and state recovery

## Fixture Types

Test fixtures are categorized by what they verify. Each type maps to a specific
layer in the testing pyramid.

| Fixture Type      | Layer | Description                              | Status     |
|-------------------|-------|------------------------------------------|------------|
| StateTest         | L1    | Single transaction execution             | Active     |
| BlockTest         | L2    | Multi-transaction block processing       | Planned    |
| TransactionTest   | L0    | Wire format validity (no execution)      | Partial    |
| CodecTest         | L0    | Raw encoding/decoding round-trip         | Planned    |
| ConsensusTest     | L2    | DAG ordering, mining, finality           | Partial    |
| CryptoTest        | L0    | Hash algorithms, HMAC, signatures        | Partial    |
| RPCTest           | L3    | RPC query method conformance             | Planned    |
| EngineTest        | L3    | Block production API conformance         | Planned    |

## Current Coverage

As of the latest run: **105 pytest tests, 71 conformance vectors**.

### By Domain

| Domain                    | Tests | Vectors | Notes                            |
|---------------------------|-------|---------|----------------------------------|
| Core (transfers, burn)    | 3     | 2       | Basic value transfer             |
| Energy (freeze/delegate)  | 11    | 4       | Freeze, unfreeze, delegate       |
| Escrow                    | 9     | 8       | Full escrow lifecycle            |
| Arbitration               | 11    | 10      | Arbiter management, commit flow  |
| KYC / Committee           | 9     | 8       | KYC issuance, committee ops      |
| Contracts                 | 4     | 2       | Deploy and invoke                |
| Privacy                   | 5     | 3       | Shield, unshield, UNO            |
| Referral                  | 3     | 1       | Bind referrer                    |
| Name Service (TNS)        | 4     | 1       | Register name                    |
| Account                   | 6     | 2       | Address registration             |
| Wire Format               | 2     | --      | Encoding round-trip              |
| Consensus                 | 22    | 6       | Block structure, ordering, PoW   |
| Models                    | 10    | --      | Constants, balance, energy       |
| Security                  | --    | 4       | Overflow, DoS, access, reentrancy|
| RPC                       | --    | 2       | Method listing, WebSocket        |
| State Models              | --    | 4       | Account, fee, energy, block      |
| Template                  | 2     | --      | Example for new test authors     |

### By Layer

| Layer | Current Vectors | Target | Coverage |
|-------|-----------------|--------|----------|
| L0    | 2 (wire format) | ~50    | Minimal  |
| L1    | 44 (tx)         | ~200   | Good     |
| L2    | 6 (consensus)   | ~50    | Partial  |
| L3    | 2 (RPC)         | ~80    | Minimal  |
| L4    | 0               | ~30    | None     |
| L5    | 0               | ~10    | None     |

## Coverage Gap Analysis

### Layer 0 — Pure Computation

**Current**: 2 wire format tests (transfer, energy freeze).

**Gaps**:
- CodecTest fixtures: raw encoding/decoding round-trip for all field types
- Wire format tests for all 43 transaction types
- Negative wire format tests (truncated, oversized, invalid type codes)
- BLAKE3 hash test vectors (cross-implementation)
- HMAC test vectors
- Ristretto255 point encoding/decoding vectors
- Key derivation vectors
- Transaction ID computation vectors

### Layer 1 — Single Transaction State Transition

**Current**: 44 transaction vectors covering all 43 types. 76/76 conformance pass rate.

**Gaps**:
- Multiple tests per transaction type (currently ~1 per type on average)
- Boundary value tests (minimum amounts, maximum counts, zero values)
- More negative cases (insufficient balance, wrong nonce, unauthorized signer)
- Interaction tests (e.g., freeze then transfer, delegate then unfreeze)
- Fee type variations (energy fee vs direct fee per transaction type)
- Protocol version parameterization (same tx tested under different rule sets)
- Fork boundary vectors (last block before upgrade, first block after)

### Layer 2 — Block Processing

**Current**: 6 consensus vectors covering block structure, ordering, and PoW rules.

**Gaps**:
- Multi-transaction block execution (ordering effects, cumulative state)
- Block reward calculation and distribution vectors
- DAG reordering vectors (multiple parents, competing tips)
- Finality vectors (stable vs unstable blocks across sequences)
- Invalid block rejection vectors

### Layer 3 — API Boundary

**Current**: 2 vectors (RPC method listing, WebSocket). Specs defined in YAML only.

**Gaps**:
- Executable RPC conformance tests (currently spec-only, not runnable)
- Per-method request/response validation
- Error response format conformance
- Query methods (get_balance, get_transaction, get_block)
- Domain query methods (get_escrow, get_energy, get_name)
- EngineTest fixtures for block production API (submit block, get template)
- Block production API error codes (invalid block, duplicate submission)

### Layer 4 — Network Protocol

**Current**: No vectors.

**Gaps**:
- P2P handshake protocol vectors
- Block propagation timing and ordering
- Transaction relay behavior
- Peer scoring and ban rules
- Chain sync protocol (header-first, state sync)
- Fault injection vectors (partition, message corruption, clock skew)
- Resource exhaustion scenarios (connection flooding, oversized messages)

### Layer 5 — Cross-Client Interoperability

**Current**: No vectors. Labu harness is operational but requires a second client.

**Gaps**:
- Multi-client block production agreement
- State root comparison after shared chain segment
- Handling of client-specific edge cases
- Restart and recovery conformance

## Test Subject Areas

Tests are organized by domain to ensure comprehensive coverage within each
functional area of TOS.

### Transactions
- **Core**: transfers (single, batch), burn, multisig
- **Energy**: freeze, unfreeze, delegate, undelegate, withdraw
- **Escrow**: create, deposit, release, refund, challenge, dispute, appeal, verdict
- **Arbitration**: register/update/slash arbiter, commit open/vote/selection/juror, exit
- **KYC**: set, revoke, renew, transfer, appeal
- **Governance**: bootstrap committee, register/update committee, emergency suspend
- **Contracts**: deploy, invoke (with gas metering)
- **Privacy**: UNO transfers, shield, unshield
- **Identity**: register name, agent account, ephemeral message
- **Referral**: bind referrer, batch reward

### Consensus
- Block structure and header validation
- BlockDAG tip management and fork choice
- Transaction ordering within blocks
- Finality computation (stable height, confirmation depth)
- Mining and proof-of-work (RandomX key blocks, difficulty adjustment)
- Block reward schedule and halving

### Cryptography
- BLAKE3 hashing (message digest, keyed hash)
- HMAC computation
- Ristretto255 scalar and point operations
- Signature generation and verification
- Key derivation

### Security
- Integer overflow and underflow protection
- Denial-of-service resistance (resource limits, gas metering)
- Access control enforcement (signer authorization, committee membership)
- Reentrancy protection in contract execution

### System Models
- Account model (balance, nonce, account type)
- Fee model (direct fee, energy fee, UNO fee)
- Energy model (frozen TOS to energy weight conversion)
- Block limits (transaction count, block size)

## Verification Strategy

Each test vector specifies what the client must verify. The strictness levels allow
incremental adoption by new client implementations.

| Level       | Fields Checked          | Purpose                          |
|-------------|-------------------------|----------------------------------|
| Required    | success, error_code     | Basic correctness                |
| Recommended | post_state, state_digest| Full state transition validation |
| Optional    | events, receipts        | Observability and debugging      |

**Required** fields must match exactly. A conformant client must return the correct
success/failure status and, on failure, the correct error code.

**Recommended** fields verify that the full post-state (account balances, nonces,
energy resources, domain data) matches the expected output. The state digest provides
a single BLAKE3 hash over the canonical post-state for fast comparison.

**Optional** fields verify event emission and receipt generation. These are useful
for client debugging but are not required for conformance.

## Workflow

The end-to-end flow from spec change to conformance verification:

```
  Spec change (Python)
       |
       v
  pytest generates fixtures (JSON)
       |
       v
  fixtures_to_vectors.py produces vectors
       |
       v
  Labu orchestrator consumes vectors
       |
       v
  Client simulator executes and reports
       |
       v
  Pass/fail per vector, aggregate report
```

Each step is deterministic and reproducible. Fixtures and vectors are committed to
the repository so that conformance can be verified without re-running the spec.

### Transition Tool Interface

The Python spec computes expected outputs directly. For client implementations, TOS
defines a standardized **transition tool (`t8n`) interface** — a CLI command that each
client exposes to execute a single state transition in isolation:

```
tos-t8n --input.pre <pre-state> --input.txs <transactions> --input.env <env>
        --output.post <post-state> --output.result <result>
```

This interface serves two purposes:

1. **Filling.** The spec framework can invoke any client's `t8n` tool to independently
   verify that the Python spec and the client agree on expected outputs. Discrepancies
   discovered during filling indicate spec or client bugs before vectors are published.

2. **Standalone testing.** Client developers can run individual vectors through their
   `t8n` tool without needing the full Labu harness, enabling fast local iteration.

## Differential Fuzzing

Hand-written test vectors cover known scenarios. Differential fuzzing covers the
unknown by generating random inputs and comparing outputs across implementations.

**Approach.** A fuzzer generates random but structurally valid transactions and
pre-states, then feeds them to two or more `t8n` implementations (the Python spec
and one or more client transition tools). Any output disagreement is a bug in at
least one implementation.

**Scope.** Fuzzing is most effective at layers 0-1:

- **L0 (codec):** Random byte sequences tested against all wire format decoders.
  Any decoder that accepts input another rejects (or vice versa) indicates a
  conformance gap.
- **L1 (state transition):** Random transactions with valid structure but arbitrary
  field values. Catches edge cases in balance arithmetic, nonce handling, and
  authorization logic that hand-written tests miss.

**Integration.** Fuzzing is a continuous process, not a one-time pass. Inputs that
trigger disagreements are minimized and added to the vector suite as regression tests.
