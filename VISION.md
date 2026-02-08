# TOS Conformance Testing Vision

This document defines the long-term testing strategy for TOS. It describes the
principles behind the conformance testing framework, the layered testing architecture,
current coverage, and the roadmap for expanding test coverage across all system layers.

## Testing Philosophy

TOS conformance testing is built on five principles:

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
   Fork parameterization uses one of two data models:
   - **Per-fork expansion**: a single test definition generates one vector per
     applicable fork, each with its own expected output. The vector's `fork` field
     identifies which protocol rules apply.
   - **Multi-fork map**: a single vector contains an `expected_by_fork` map keyed
     by fork name, allowing compact representation when only the expected output
     differs.
   Both height-based and timestamp-based fork activations are supported. Transition
   schedule tests use synthetic fork configurations (e.g., "activate fork X at
   block 5") to stress fork-boundary logic independently of the mainnet schedule.

5. **Fill is not conformance.** Generating (filling) test vectors from the spec is a
   necessary step, but it does not prove client correctness. A client is only
   conformant when it independently consumes the published vectors and produces
   matching outputs. Filling and consumption are separate checkpoints — passing one
   does not imply passing the other.

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

- Published execution vectors currently cover 42 distinct tx types across 11 handler modules
  (more are defined in the spec but are not yet published to `vectors/`).
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

**Consumption modalities.** The same BlockchainTest fixtures are consumed through
multiple independent execution paths, each exercising different client codepaths:

- **Direct import**: blocks are fed sequentially via the client's block import API
- **Engine API**: blocks are delivered through the block production interface
- **Sync**: the client syncs a pre-built chain from a peer, validating as it goes

A client that passes direct import but fails sync consumption has a real bug. All
three modalities must agree on the final state.

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

**Devnet and shadow network testing.** Beyond deterministic vector consumption, L5
includes deploying multiple clients on a shared test network (devnet) to validate
behavior under realistic conditions — real block times, real P2P propagation, and
real resource contention. Shadow networks replay mainnet traffic against new client
versions to detect regressions before release.

## Fixture Types

Test fixtures are categorized by what they verify. Each type maps to a specific
layer in the testing pyramid.

| Fixture Type      | Layer | Description                              | Status     |
|-------------------|-------|------------------------------------------|------------|
| StateTest         | L1    | Single transaction execution             | Active     |
| BlockchainTest    | L2    | Multi-block chain import with reorgs     | Planned    |
| TransactionTest   | L0    | Wire format validity (no execution)      | Partial    |
| CodecTest         | L0    | Raw encoding/decoding round-trip         | Planned    |
| ContractTest      | L0    | Bytecode container validity              | Planned    |
| ConsensusTest     | L2    | DAG ordering, mining, finality           | Partial    |
| CryptoTest        | L0    | Hash algorithms, HMAC, signatures        | Partial    |
| RPCTest           | L3    | RPC query method conformance             | Planned    |
| EngineTest        | L3    | Block production API conformance         | Planned    |
| FuzzCorpusTest    | L0-L1 | Minimized cases from differential fuzzing| Planned    |

**Fixture type definitions:**

- **StateTest**: provides a pre-state, a single transaction, and the expected
  post-state or error code. The primary fixture type for L1 conformance.
- **BlockchainTest**: imports a sequence of blocks (possibly including invalid
  blocks) into a chain, then verifies the final post-state, the canonical chain
  head, and correct rejection of invalid blocks. Covers multi-block state
  accumulation, reorgs, and fork-choice rule validation.
- **TransactionTest**: provides a transaction in its wire-encoded form. The client
  must parse it, validate structure, and derive the sender. No state transition is
  executed. Tests wire format compliance and signature recovery.
- **CodecTest**: provides raw byte sequences and their expected decoded values (or
  expected parse errors). Tests encoding/decoding round-trips for all field types,
  blocks, receipts, and messages — independent of transaction semantics.
- **ContractTest**: provides contract bytecode and expected validation results
  (valid/invalid with specific error). Tests container format parsing and bytecode
  validation rules before execution.
- **FuzzCorpusTest**: minimized inputs from differential fuzzing that triggered
  disagreements between implementations. Promoted into the stable vector suite as
  regression tests with deterministic seeds.

## Current Coverage

As of **2026-02-08**:

- Published conformance suite: `vectors/` contains **649 runnable** execution vectors in the `test_vectors` schema.
- Runner status: `python3 ~/labu/tools/local_execution_runner.py --vectors ~/tos-spec/vectors` reports `all ok` against the `tos` conformance server.
- Composition: **627** L1 state-transition vectors (`input.tx` present) + **15** L0 negative wire-decoding vectors (malformed `wire_hex` rejected by decode) + **7** L2 block vectors (`input.kind="block"`).
- Covered transaction types: **42** distinct `tx_type` values in published vectors.
- Note: `uno_transfers` vectors are currently **tx-json-only** (`input.wire_hex=""`) until wire/proof generation and encrypted pre-state are represented in the exported conformance surface.
- Spec-only: fixtures under `fixtures/{security,models,syscalls,api,consensus}/` are not published to `vectors/` yet.
- Codec corpus: `fixtures/wire_format.json` contains golden wire hex vectors (45 entries) but is not published to `vectors/` yet. The corpus is mirrored into `~/tos/common/tests/wire_format.json` (with `wire_format_negative.json`) and validated by Rust internal tests: `cargo test -p tos_common --test spec_wire_format_vectors`.

### Published Vector Groups

Counts below are for the published conformance suite under `vectors/execution/transactions/`.

| Group | Vectors |
|------:|--------:|
| escrow | 137 |
| kyc | 107 |
| arbitration | 97 |
| block | 7 |
| (root) | 64 |
| tns | 61 |
| energy | 46 |
| account | 43 |
| contracts | 24 |
| privacy | 34 |
| referral | 20 |
| core | 7 |
| template | 2 |

### By Layer (Published)

| Layer | Current Vectors | Target | Coverage |
|-------|-----------------|--------|----------|
| L0    | 15 (wire negative) | ~50 | Partial  |
| L1    | 627 (tx state transition) | ~200 | Good |
| L2    | 7 | ~50 | Partial |
| L3    | 0 | ~80 | None |
| L4    | 0 | ~30 | None |
| L5    | 0 | ~10 | None |

## Coverage Gap Analysis

### Layer 0 — Pure Computation

**Current (published)**: 15 negative wire-format vectors (malformed `wire_hex` rejected by decode).

**Current (fixtures only)**: `fixtures/wire_format.json` contains 45 golden wire-encoding vectors
(`expected_hex`) but is not published to `vectors/` yet. It is currently consumed via Rust internal tests (see `~/tos/common/tests/`).

**Gaps**:
- CodecTest fixtures: raw encoding/decoding round-trip for all field types
- Positive wire format tests for all tx types (encode and/or decode acceptance)
- BLAKE3 hash test vectors (cross-implementation)
- HMAC test vectors
- Ristretto255 point encoding/decoding vectors
- Key derivation vectors
- Transaction ID computation vectors

### Layer 1 — Single Transaction State Transition

**Current (published)**: 627 L1 state-transition vectors (`input.tx` present) covering 42 distinct `tx_type` values.
All published vectors pass in the Rust daemon conformance runner (overall 649/649 including L0 negatives and L2 blocks).

**Gaps**:
- Multiple tests per transaction type (currently ~1 per type on average)
- Boundary value tests (minimum amounts, maximum counts, zero values)
- More negative cases (insufficient balance, wrong nonce, unauthorized signer)
- Interaction tests (e.g., freeze then transfer, delegate then unfreeze)
- Fee type variations (energy fee vs direct fee per transaction type)
- Protocol version parameterization (same tx tested under different rule sets)
- Fork boundary vectors (last block before upgrade, first block after)

### Layer 2 — Block Processing

**Current (published)**: 7 block-processing vectors (multi-tx execution + atomic rejection + multi-sender ordering).

**Current (fixtures only)**: consensus/model fixtures exist under `fixtures/consensus/` but are not published to `vectors/` yet.

**Gaps**:
- BlockchainTest fixtures: multi-block chain import with reorgs and invalid blocks
- Block reward calculation and distribution vectors
- DAG reordering vectors (multiple parents, competing tips)
- Finality vectors (stable vs unstable blocks across sequences)
- Invalid block rejection vectors (must appear in `rejected_blocks` list)
- Fork transition vectors (rule change at specific block height or timestamp)
- Consumption via all modalities (direct import, Engine API, sync)

### Layer 3 — API Boundary

**Current (published)**: no API vectors yet.

**Current (fixtures only)**: API/syscall fixtures exist under `fixtures/api/` and `fixtures/syscalls/` but are not published to `vectors/` yet.

**Gaps**:
- Executable RPC conformance tests (currently spec-only, not runnable)
- Golden request/response transcripts per RPC method
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

Each test vector specifies what the client must verify. Verification requirements
vary by fixture type and layer.

### StateTest (L1) Verification

| Field          | Requirement | Description                                    |
|----------------|-------------|------------------------------------------------|
| success        | Required    | Transaction succeeded or failed                |
| error_code     | Required    | Specific error code on failure                 |
| post_state     | Required    | Full post-state (balances, nonces, storage)    |
| state_digest   | Required    | BLAKE3 hash over canonical post-state          |
| logs_hash      | Required    | BLAKE3 hash over emitted log entries           |
| receipts       | Recommended | Per-transaction receipt (gas used, status)     |

### BlockchainTest (L2) Verification

| Field          | Requirement | Description                                    |
|----------------|-------------|------------------------------------------------|
| chain_head     | Required    | Hash of the canonical chain tip after import   |
| post_state     | Required    | Full post-state after all blocks               |
| state_digest   | Required    | BLAKE3 hash over canonical post-state          |
| rejected_blocks| Required    | List of block hashes that must be rejected     |
| logs_hash      | Recommended | Cumulative log commitment across all blocks    |

### Canonicalization

The `state_digest` and `logs_hash` fields depend on deterministic canonicalization.
Independent implementations must produce identical digests for equivalent state.

**State digest canonicalization rules:**
- Accounts are sorted by address (lexicographic byte order)
- Within each account: fields are serialized in fixed order (balance, nonce,
  code_hash, storage_root)
- Storage entries are sorted by key (lexicographic byte order)
- All integers use fixed-width little-endian encoding
- The BLAKE3 hash is computed over the concatenated canonical byte sequence

**Logs hash canonicalization rules:**
- Logs are ordered by emission sequence (block order, then transaction order,
  then log index within transaction)
- Each log entry is serialized as: address || topics_count || topic_0 || ... || data
- The BLAKE3 hash is computed over the concatenated log byte sequence

These rules are specified so that two implementations that agree on semantics will
always agree on the digest. Ambiguity in encoding order or integer width would
cause false negatives in conformance checks.

## Separation of Responsibilities

The testing infrastructure is divided into four components with strict boundaries.
No component should duplicate the responsibilities of another.

| Component        | Owns                                      | Must Not                          |
|------------------|-------------------------------------------|-----------------------------------|
| Spec / Generator | Semantics, expected results, fixture fill | Interpret client-specific formats  |
| Fixtures/Vectors | Immutable test artifacts (JSON)           | Be hand-edited after generation    |
| Harness (Labu)   | Scheduling, orchestration, IO, reporting  | Encode protocol logic or semantics |
| Simulator        | Protocol-specific client driving          | Contain assertion logic            |

**Spec / Generator.** The Python executable spec defines canonical behavior. It
produces fixtures and vectors. It may invoke client `t8n` tools during filling to
cross-check expected outputs, but it is the sole authority on what the expected
output should be.

**Fixtures and Vectors.** Generated artifacts that are committed to the repository.
They are reproducible from the spec and must never be hand-edited. Changes flow
through the spec, not through fixture files.

**Harness (Labu).** The orchestration layer that launches clients, feeds them
vectors, collects outputs, and compares against expected results. It must remain a
thin shell — it does not interpret transaction semantics, compute state digests, or
validate block structure. If the harness needs protocol knowledge, that logic
belongs in a simulator adapter.

**Simulator adapters.** Thin, protocol-specific drivers that translate between the
harness's generic interface and a specific client consumption path (RPC, Engine API,
direct import, P2P sync). Each adapter exercises a different client codepath. The
adapter is responsible for driving the client, not for deciding correctness —
assertion logic stays in the harness's comparison step.

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

### Artifact Immutability Rules

The testing pipeline distinguishes between **source artifacts** (author-edited) and
**generated artifacts** (machine-produced). This separation is strictly enforced.

| Artifact       | Location     | Editable? | Regenerated By                    |
|----------------|-------------|-----------|-----------------------------------|
| Test specs     | `tests/`     | Yes       | Authors (human-edited)            |
| Spec modules   | `src/`       | Yes       | Authors (human-edited)            |
| Fixtures       | `fixtures/`  | No        | `pytest --output fixtures`        |
| Vectors        | `vectors/`   | No        | `fixtures_to_vectors.py`          |

**Rule: edit fillers, never edit fixtures.** To change a test's expected output,
modify the test spec under `tests/` or the spec module under `src/`, then
regenerate fixtures and vectors. Direct edits to `fixtures/` or `vectors/` are
rejected by CI.

### Fill Reproducibility

Fixture generation must be deterministic and reproducible. The fill process is
pinned by:

- **Python version**: specified in `pyproject.toml` (`requires-python`)
- **Dependency versions**: locked via `requirements.txt` or equivalent
- **Rust extension versions**: `tos_codec`, `tos_signer` built from pinned commits
- **Fork configuration**: the set of protocol versions and activation heights
  used during filling is recorded in the fixture metadata

A `make fill` target regenerates all fixtures and vectors from source. If the
output differs from the committed artifacts, the CI build fails — indicating
either an uncommitted spec change or a toolchain version mismatch.

### Outdated Fixture Detection

When the spec changes, affected fixtures may become stale. The CI pipeline detects
this by regenerating fixtures and comparing against the committed versions. A
mismatch triggers a build failure with a clear message identifying which fixtures
need updating.

### Large Vector Storage

As the vector suite grows, individual files or the total repository size may exceed
practical limits for Git. The storage strategy scales in stages:

1. **Default**: vectors committed directly (current, suitable for < 100 MB total)
2. **Git LFS**: large vector files tracked via LFS when individual files exceed
   1 MB or total vectors exceed 100 MB
3. **Split repository**: vectors published as versioned release artifacts in a
   dedicated repository, consumed by the harness via download

### Transition Tool Interface

The Python spec computes expected outputs directly. For client implementations, TOS
defines a standardized **transition tool (`t8n`) interface** — a versioned CLI
specification that each client must implement. This interface enables both fixture
filling and standalone vector consumption.

**`tos-t8n` — state transition tool:**

```
tos-t8n --state.fork <fork-name>       # protocol version (e.g., "genesis", "v2")
        --state.chainid <chain-id>     # network chain ID
        --state.reward <block-reward>  # block reward override (-1 to disable)
        --input.pre <path|stdin>       # pre-state (JSON: account → balance/nonce/code/storage)
        --input.txs <path|stdin>       # transactions (JSON array)
        --input.env <path|stdin>       # block environment (height, timestamp, coinbase, etc.)
        --output.post <path|stdout>    # post-state allocation
        --output.result <path|stdout>  # execution result (receipts, logs, gas used, errors)
        --output.body <path|stdout>    # wire-encoded transaction bodies
        --trace                        # emit per-step execution trace (optional)
        --trace.dir <path>             # directory for trace output files
```

When a path argument is `stdin` or `stdout`, the tool reads from or writes to the
corresponding stream. This enables piped workflows without temporary files.

**Result schema.** The `result` output includes per-transaction receipts with gas
used, log entries, error codes (if failed), and the cumulative state digest. This
enables verification beyond pass/fail — clients can be compared on intermediate
execution details.

**`tos-t9n` — transaction validation tool:**

```
tos-t9n --state.fork <fork-name>
        --input.txs <path|stdin>       # wire-encoded transactions
        --output.result <path|stdout>  # per-tx: valid/invalid, sender, error
```

The `t9n` tool performs parse-and-validate only — no state transition. It checks
wire format validity, recovers the sender address, and reports structural errors.
This corresponds to TransactionTest fixtures and isolates parsing bugs from
execution bugs.

**Purposes:**

1. **Filling.** The spec framework can invoke any client's `t8n` tool to independently
   verify that the Python spec and the client agree on expected outputs. Discrepancies
   discovered during filling indicate spec or client bugs before vectors are published.

2. **Standalone testing.** Client developers can run individual vectors through their
   `t8n` tool without needing the full Labu harness, enabling fast local iteration.

3. **Differential comparison.** Multiple clients' `t8n` tools are invoked on the same
   inputs and their outputs compared. Any disagreement is investigated and resolved
   before vectors are published.

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

**Corpus management.** Fuzz-discovered inputs follow a promotion pipeline:

1. **Discovery**: the fuzzer flags an input that causes output disagreement.
2. **Minimization**: the input is reduced to the smallest case that still triggers
   the disagreement, using deterministic seed replay for reproducibility.
3. **Triage**: the disagreement is classified as one of:
   - *Spec bug* — the Python spec produces incorrect output.
   - *Client bug* — the client implementation deviates from the spec.
   - *Underspecified check* — the vector's expected output is too weak to detect the
     real difference (e.g., only checking success/error without post-state).
   Resolution requires traces, cross-client majority comparison, or spec amendment.
4. **Promotion**: the minimized, triaged case is committed as a FuzzCorpusTest
   fixture with a deterministic seed, becoming a permanent regression test.

Fuzzing is a continuous process, not a one-time pass. The corpus grows over time
and is versioned alongside hand-written vectors.
