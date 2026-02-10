# TOS Conformance Test Matrix

This document provides a grid-based view of test coverage across all dimensions
defined in [VISION.md](VISION.md). Each matrix crosses two dimensions to reveal
coverage gaps and prioritization targets.

## Current Published Status (2026-02-10)

- `vectors/` contains **498** vectors in the `test_vectors` schema (execution + RPC suites), all **498** runnable.
- The published suite currently has **0** non-runnable vectors.
- Composition (execution): **263** tx execution vectors (`input.kind="tx"`) + **14** tx wire roundtrip vectors (`input.kind="tx_roundtrip"`) + **37** block vectors (`input.kind="block"`) + **100** chain-import vectors (`input.kind="chain"`).
- Composition (RPC): **84** RPC vectors (`input.rpc` present) consumed by the `tos/rpc` simulator.
- Covered transaction types: **11** distinct `tx_type` values in published vectors.
- Spec-only fixtures under `fixtures/{security,models,syscalls,consensus}/` are intentionally not published to `vectors/` yet.
- Codec corpus: `fixtures/wire_format.json` contains **14** golden wire-encoding vectors; these are published as tx wire roundtrip vectors under `wire_format_roundtrip`.

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
| Core (transfer)    | ++         | +++        | ++         | -          | -          | -          |
| Burn               | +          | ++         | ++         | -          | n/a        | -          |
| Multisig           | +          | +++        | ++         | -          | n/a        | -          |
| Energy / Freeze    | ++         | +++        | ++         | -          | n/a        | -          |
| Energy / Delegate  | +          | +++        | ++         | -          | n/a        | -          |
| Contracts          | +          | +++        | ++         | -          | n/a        | -          |
| Privacy (UNO)      | +          | +++        | ++         | -          | n/a        | -          |
| Privacy (shield)   | +          | +++        | ++         | -          | n/a        | -          |
| TNS (names)        | +          | +++        | ++         | -          | n/a        | -          |
| Account / Agent    | +          | +++        | ++         | -          | n/a        | -          |
| Block structure    | n/a        | n/a        | ++         | -          | -          | -          |
| DAG ordering       | n/a        | n/a        | ++         | -          | -          | -          |
| Finality           | n/a        | n/a        | ++         | -          | -          | -          |
| Mining / PoW       | n/a        | n/a        | ++         | -          | -          | -          |
| Block rewards      | n/a        | n/a        | ++         | -          | -          | -          |
| BLAKE3 / HMAC      | +          | n/a        | n/a        | n/a        | n/a        | n/a        |
| Ristretto255       | -          | n/a        | n/a        | n/a        | n/a        | n/a        |
| Fee model          | n/a        | ++         | ++         | -          | n/a        | n/a        |
| Energy model       | n/a        | ++         | ++         | -          | n/a        | n/a        |
| Account model      | n/a        | ++         | ++         | -          | n/a        | n/a        |

**Reading this matrix:** The published conformance suite is currently L1-heavy:
262/383 vectors are `tx` execution vectors. L0 wire-format coverage in published
vectors includes 14 tx wire roundtrip vectors (`wire_format_roundtrip`)
and 36 negative decode vectors (`wire_format_negative`). The
priority gaps are:
- L2: basic executable block processing tests (137 vectors: 37 `block` + 100 `chain`)
- L3: published via the RPC suite (84 vectors under `vectors/rpc/`)
- L4-L5: not published yet (P2P/interop vectors remain spec-only)
Note: L0 wire-format roundtrip is currently published for a small corpus; full tx-type codec coverage is not yet published.

## Matrix 2: Domain x Fixture Type

Published vectors include:
- Execution vectors (`input.kind` in `{tx, tx_roundtrip, block, chain}`).
- RPC vectors (`input.rpc` present), consumed by the `tos/rpc` simulator.

The table below lists the published `vectors/**` groups and vector counts.

| Group | Path Prefix | Vectors | Notes |
|------:|------------|--------:|-------|
| block | `execution/transactions/block/` | 37 | L2 block processing (multi-tx, atomic rejection) |
| blockchain | `execution/transactions/blockchain/` | 100 | L2 chain import (rewards + invalid tips) |
| tns | `execution/transactions/tns/` | 20 | L1 state transitions |
| energy | `execution/transactions/energy/` | 43 | L1 state transitions |
| account | `execution/transactions/account/` | 45 | L1 state transitions |
| contracts | `execution/transactions/contracts/` | 25 | L1 state transitions |
| privacy | `execution/transactions/privacy/` | 34 | L1 state transitions |
| core | `execution/transactions/core/` | 8 | L1 state transitions |
| root | `execution/transactions/*.json` | 99 | Includes `tx_core`, `fee_variants`, `wire_format_negative`, `wire_format_roundtrip` |
| template | `execution/transactions/template/` | 2 | Example vectors |
| rpc | `rpc/` | 84 | L3 JSON-RPC request/response conformance (`/json_rpc`) |

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
| Contracts          | YES        | YES        | YES      | -        | -        | -        | YES         | -          |
| Privacy (UNO)      | YES        | YES        | YES      | -        | -        | YES      | YES         | -          |
| Privacy (shield)   | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| TNS (names)        | YES        | YES        | YES      | -        | -        | YES      | YES         | -          |
| Account / Agent    | YES        | YES        | YES      | -        | -        | -        | YES         | -          |

**Reading this matrix:** Happy and error paths have broad coverage. Boundary testing
now covers all 10 domains listed above. Overflow testing covers 4 domains (Core, Burn,
Energy/Freeze, Energy/Delegate). Fee variant testing covers 8 domains. Auth/ACL testing
is intentionally out of scope in this trimmed core suite. The remaining gap is Fork
Param testing (not yet applicable).

## Matrix 4: Transaction Type Coverage (Published)

Per-type coverage is tracked from the published conformance suite under `vectors/`.
As of 2026-02-10:

- Total published vectors (execution suite): **414**
- Tx execution vectors: **263** (`input.kind="tx"`)
- L0 tx wire roundtrip vectors: **14** (`wire_format_roundtrip`)
- L0 negative wire-decoding vectors: **36** (`wire_format_negative`)
- L2 block vectors: **37** (`input.kind="block"`)
- L2 chain-import vectors: **100** (`input.kind="chain"`)
- Distinct `tx_type` values covered in published vectors: **11**

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
