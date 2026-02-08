# TOS Conformance Test Matrix

This document provides a grid-based view of test coverage across all dimensions
defined in [VISION.md](VISION.md). Each matrix crosses two dimensions to reveal
coverage gaps and prioritization targets.

## Current Published Status (2026-02-08)

- `vectors/` contains **608** runnable execution vectors in the `test_vectors` schema.
- The published suite has **no** `runnable: false` vectors.
- Composition: **593** L1 state-transition vectors (`input.tx` present) + **15** L0 negative wire-decoding vectors.
- Covered transaction types: **42** distinct `tx_type` values in published vectors.
- Spec-only fixtures under `fixtures/{security,models,syscalls,api,consensus}/` are intentionally not published to `vectors/` yet.
- Codec corpus: `fixtures/wire_format.json` contains 45 golden wire-encoding vectors but is not published to `vectors/` yet.

Reproduce (local):

```bash
# terminal A
cd ~/tos
rm -rf /tmp/conformance_state
LABU_STATE_DIR=/tmp/conformance_state ./target/release/conformance

# terminal B
python3 ~/labu/tools/local_execution_runner.py --vectors ~/tos-spec/vectors
```

## Matrix 1: Domain x Layer

Which domains are tested at which layers. Each cell shows the current status.

```
Legend:  +++  strong coverage
        ++   moderate coverage
        +    minimal coverage
        -    no coverage
        n/a  not applicable to this domain
```

| Domain             | L0 Codec   | L1 State   | L2 Block   | L3 API     | L4 P2P     | L5 Interop |
|--------------------|------------|------------|------------|------------|------------|------------|
| Core (transfer)    | ++         | +++        | -          | -          | -          | -          |
| Burn               | +          | ++         | -          | -          | n/a        | -          |
| Multisig           | +          | +++        | -          | -          | n/a        | -          |
| Energy / Freeze    | ++         | +++        | -          | -          | n/a        | -          |
| Energy / Delegate  | +          | +++        | -          | -          | n/a        | -          |
| Escrow             | +          | +++        | -          | -          | n/a        | -          |
| Arbitration        | +          | +++        | -          | -          | n/a        | -          |
| KYC                | +          | +++        | -          | -          | n/a        | -          |
| Committee          | +          | +++        | -          | -          | n/a        | -          |
| Contracts          | +          | +++        | -          | -          | n/a        | -          |
| Privacy (UNO)      | +          | +++        | -          | -          | n/a        | -          |
| Privacy (shield)   | +          | +++        | -          | -          | n/a        | -          |
| TNS (names)        | +          | +++        | -          | -          | n/a        | -          |
| Referral           | +          | +++        | -          | -          | n/a        | -          |
| Account / Agent    | +          | +++        | -          | -          | n/a        | -          |
| Block structure    | n/a        | n/a        | ++         | -          | -          | -          |
| DAG ordering       | n/a        | n/a        | ++         | -          | -          | -          |
| Finality           | n/a        | n/a        | ++         | -          | -          | -          |
| Mining / PoW       | n/a        | n/a        | +          | -          | -          | -          |
| Block rewards      | n/a        | n/a        | ++         | -          | -          | -          |
| BLAKE3 / HMAC      | +          | n/a        | n/a        | n/a        | n/a        | n/a        |
| Ristretto255       | -          | n/a        | n/a        | n/a        | n/a        | n/a        |
| Fee model          | n/a        | +          | -          | -          | n/a        | n/a        |
| Energy model       | n/a        | +          | -          | -          | n/a        | n/a        |
| Account model      | n/a        | +          | -          | -          | n/a        | n/a        |

**Reading this matrix:** The published conformance suite is currently L1-heavy:
593/608 vectors are L1 state transitions. L0 wire-format coverage in published
vectors is currently negative-only (15 malformed `wire_hex` vectors). The
priority gaps are:
- L2: no executable block processing tests yet
- L3-L5: not published yet (API/P2P/interop vectors remain spec-only)

## Matrix 2: Domain x Fixture Type

Published conformance vectors are currently execution-only (`input.kind=tx`). The table below
lists the published `vectors/execution/transactions/**` groups and vector counts.

| Group | Path Prefix | Vectors | Notes |
|------:|------------|--------:|-------|
| escrow | `execution/transactions/escrow/` | 125 | L1 state transitions |
| kyc | `execution/transactions/kyc/` | 107 | L1 state transitions |
| arbitration | `execution/transactions/arbitration/` | 92 | L1 state transitions |
| tns | `execution/transactions/tns/` | 58 | L1 state transitions |
| energy | `execution/transactions/energy/` | 44 | L1 state transitions |
| account | `execution/transactions/account/` | 41 | L1 state transitions |
| contracts | `execution/transactions/contracts/` | 21 | L1 state transitions |
| privacy | `execution/transactions/privacy/` | 32 | L1 state transitions |
| referral | `execution/transactions/referral/` | 19 | L1 state transitions |
| core | `execution/transactions/core/` | 5 | L1 state transitions |
| root | `execution/transactions/*.json` | 62 | Includes `tx_core` (29), `fee_variants` (18), `wire_format_negative` (15) |
| template | `execution/transactions/template/` | 2 | Example vectors |

Spec-only fixture categories (`fixtures/{security,models,syscalls,api,consensus}/`) are omitted
from `vectors/` until a consumer exists for them.

## Matrix 3: Domain x Test Aspect

What aspects are tested for each domain. Aspects represent the testing perspective
(what question is being asked), orthogonal to layers and fixture types.

| Domain             | Happy Path | Error Path | Boundary | Overflow | Auth/ACL | Self-ref | Fee Variant | Fork Param |
|--------------------|------------|------------|----------|----------|----------|----------|-------------|------------|
| Core (transfer)    | YES        | YES        | YES      | YES      | -        | YES      | YES         | -          |
| Burn               | YES        | YES        | YES      | YES      | -        | n/a      | YES         | -          |
| Multisig           | YES        | YES        | YES      | -        | -        | -        | YES         | -          |
| Energy / Freeze    | YES        | YES        | YES      | YES      | -        | -        | YES         | -          |
| Energy / Delegate  | YES        | YES        | YES      | YES      | -        | YES      | -           | -          |
| Escrow             | YES        | YES        | YES      | YES      | YES      | YES      | YES         | -          |
| Arbitration        | YES        | YES        | YES      | YES      | -        | -        | YES         | -          |
| KYC                | YES        | YES        | YES      | -        | YES      | -        | YES         | -          |
| Committee          | YES        | YES        | YES      | -        | YES      | -        | -           | -          |
| Contracts          | YES        | YES        | YES      | -        | -        | -        | YES         | -          |
| Privacy (UNO)      | YES        | YES        | YES      | -        | -        | YES      | YES         | -          |
| Privacy (shield)   | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| TNS (names)        | YES        | YES        | YES      | -        | -        | YES      | YES         | -          |
| Referral           | YES        | YES        | YES      | -        | -        | YES      | -           | -          |
| Account / Agent    | YES        | YES        | YES      | -        | -        | -        | YES         | -          |

**Reading this matrix:** Happy and error paths have broad coverage. Boundary testing
now covers all 15 domains. Overflow testing covers 7 domains (Core, Burn, Energy/Freeze,
Energy/Delegate, Escrow, Arbitration). Fee variant testing covers 11 domains. Auth/ACL
testing covers 4 domains (KYC, Committee, Escrow, Energy). The remaining gap is Fork
Param testing (not yet applicable).

## Matrix 4: Transaction Type Coverage (Published)

Per-type coverage is tracked from the published conformance suite under `vectors/`.
As of 2026-02-08:

- Total published vectors: **608**
- L1 state-transition vectors: **593** (`input.tx` present)
- L0 negative wire-decoding vectors: **15** (`wire_format_negative`)
- Distinct `tx_type` values covered in published vectors: **42**

To list covered `tx_type` values from `vectors/`:

```bash
python3 - <<'PY'
import json
from pathlib import Path
tx_types=set()
for p in Path('vectors').rglob('*.json'):
    d=json.loads(p.read_text())
    for v in d.get('test_vectors', []):
        tx=(v.get('input') or {}).get('tx')
        if isinstance(tx, dict) and 'tx_type' in tx:
            tx_types.add(tx['tx_type'])
print(len(tx_types))
print('\\n'.join(sorted(tx_types)))
PY
```

## Matrix 5: Fixture Type x Verification Field

What fields each fixture type must verify.

| Field           | StateTest | BlockchainTest | TransactionTest | CodecTest | ContractTest | ConsensusTest | RPCTest | EngineTest |
|-----------------|-----------|----------------|-----------------|-----------|--------------|---------------|---------|------------|
| success         | Req       | -              | Req             | Req       | Req          | -             | Req     | Req        |
| error_code      | Req       | -              | Req             | Req       | Req          | -             | Req     | Req        |
| post_state      | Req       | Req            | -               | -         | -            | -             | -       | -          |
| state_digest    | Req       | Req            | -               | -         | -            | -             | -       | -          |
| logs_hash       | Req       | Rec            | -               | -         | -            | -             | -       | -          |
| receipts        | Rec       | -              | -               | -         | -            | -             | -       | -          |
| chain_head      | -         | Req            | -               | -         | -            | Req           | -       | -          |
| rejected_blocks | -         | Req            | -               | -         | -            | -             | -       | Req        |
| sender          | -         | -              | Req             | -         | -            | -             | -       | -          |
| decoded_value   | -         | -              | -               | Req       | -            | -             | -       | -          |
| valid           | -         | -              | -               | -         | Req          | -             | -       | -          |
| response_body   | -         | -              | -               | -         | -            | -             | Req     | Req        |
| ordering        | -         | -              | -               | -         | -            | Req           | -       | -          |

`Req` = Required. `Rec` = Recommended. `-` = not applicable.

## Matrix 6: Consumption Modality x Layer

How test vectors are consumed at each layer.

| Modality            | L0        | L1         | L2            | L3        | L4        | L5           |
|---------------------|-----------|------------|---------------|-----------|-----------|--------------|
| tos-t9n (parse)     | PRIMARY   | -          | -             | -         | -         | -            |
| tos-t8n (transition)| -         | PRIMARY    | -             | -         | -         | -            |
| Direct import       | -         | -          | PRIMARY       | -         | -         | -            |
| Engine API          | -         | -          | SECONDARY     | -         | -         | PRIMARY      |
| RPC call            | -         | -          | -             | PRIMARY   | -         | SECONDARY    |
| P2P sync            | -         | -          | SECONDARY     | -         | PRIMARY   | PRIMARY      |
| Devnet deployment   | -         | -          | -             | -         | SECONDARY | PRIMARY      |

`PRIMARY` = main consumption path. `SECONDARY` = additional validation modality.

## Matrix 7: Test Aspect x Priority

Prioritized backlog of test aspects to implement, ordered by impact and effort.

| Priority | Aspect                        | Layers | Est. Vectors | Effort | Impact  |
|----------|-------------------------------|--------|--------------|--------|---------|
| ~~P0~~   | ~~Wire format all 45 tx types~~ | L0   | 45 done      | -      | -       |
| ~~P0~~   | ~~Negative wire format (invalid)~~ | L0 | 15 done    | -      | -       |
| P1       | Boundary values per tx type   | L1     | ~86          | Medium | High    |
| ~~P1~~   | ~~Overflow arithmetic~~       | L1     | 10 done      | -      | -       |
| P1       | Insufficient balance variants | L1     | ~30          | Low    | Medium  |
| P1       | Wrong nonce / auth failures   | L1     | ~30          | Low    | Medium  |
| ~~P2~~   | ~~Fee type variations~~       | L1     | 20 done      | -      | -       |
| P2       | Multi-tx block execution      | L2     | ~20          | High   | High    |
| P2       | Block reward distribution     | L2     | ~10          | Medium | Medium  |
| P2       | DAG reorg vectors             | L2     | ~10          | High   | High    |
| P2       | Fork boundary transitions     | L1-L2  | ~10          | Medium | High    |
| P3       | RPC golden transcripts        | L3     | ~60          | Medium | Medium  |
| P3       | Engine API conformance        | L3     | ~20          | High   | Medium  |
| P3       | Crypto primitive vectors      | L0     | ~30          | Low    | Medium  |
| P4       | P2P protocol vectors          | L4     | ~30          | High   | Low     |
| P4       | Fault injection scenarios     | L4     | ~20          | High   | Medium  |
| P5       | Multi-client interop          | L5     | ~10          | High   | High    |
| P5       | Devnet / shadow network       | L5     | ~5           | High   | Medium  |

## Matrix 8: Handler Module x Coverage Depth

Aggregate coverage by handler module, computed from published vectors by mapping
each vector's `input.tx.tx_type` through the dispatcher in `src/tos_spec/state_transition.py`.
This view is intentionally **tx_type-based** (not path-based).

Fee types: `TOS=0`, `ENERGY=1`, `UNO=2`.

| Module      | Types Covered / Total | Vectors | Negative | Fee Types Seen | Notes |
|-------------|------------------------|--------:|---------:|----------------|-------|
| account     | 2 / 2                  | 42      | 28       | 0, 1           | multisig + agent_account |
| arbitration | 10 / 10                | 87      | 66       | 0              | commit_* and arbiter ops |
| contracts   | 2 / 2                  | 22      | 13       | 0, 1           | deploy + invoke |
| core        | 2 / 2                  | 43      | 32       | 0, 1, 2        | transfers + burn |
| energy      | 1 / 1                  | 47      | 38       | 0, 1, 2        | freeze/unfreeze/delegate share `tx_type=energy` |
| escrow      | 9 / 9                  | 130     | 109      | 0              | escrow lifecycle + verdict |
| kyc         | 9 / 9                  | 107     | 92       | 0              | committee + kyc |
| privacy     | 3 / 3                  | 37      | 23       | 0, 1, 2        | includes `uno_transfers` (tx-json-only) |
| referral    | 2 / 2                  | 19      | 15       | 0              | bind + batch reward |
| tns         | 2 / 2                  | 59      | 40       | 0, 1           | names + ephemeral messages |

This table covers the **593** published L1 vectors. The **15** L0 negative wire-decoding
vectors (`wire_format_negative`) are not included in handler-module stats.

## Summary: Coverage Heat Map

```
                     L0     L1     L2     L3     L4     L5
                   +------+------+------+------+------+------+
   Core tx         | OK   | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Energy          | OK   | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Escrow          | OK   | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Arbitration     | OK   | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   KYC/Committee   | OK   | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Contracts       | LOW  | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Privacy         | LOW  | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   TNS/Referral    | LOW  | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Account/Agent   | LOW  | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Consensus       | n/a  | n/a  | PART | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Crypto          | LOW  | n/a  | n/a  | n/a  | n/a  | n/a  |
                   +------+------+------+------+------+------+
   Security        | NONE | NONE | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+

Legend:  GOOD = broad coverage with success + error + boundary paths
        OK   = basic coverage, missing negative/boundary tests
        PART = partial (spec-level, not all executable)
        LOW  = 1-2 tests only
        NONE = no tests at this layer
```

## How to Use This Matrix

1. **Find gaps**: scan for `-`, `NONE`, or `0` cells to identify untested areas.
2. **Prioritize**: use Matrix 7 to determine implementation order.
3. **Track progress**: update cell values as new tests are added.
4. **Review coverage depth**: use Matrix 8 to identify modules that have many
   vectors but shallow coverage (only happy paths).
5. **Plan by fixture type**: use Matrix 2 to see which fixture types are needed
   for each domain and plan implementation of new fixture types accordingly.
