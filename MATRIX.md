# TOS Conformance Test Matrix

This document provides a grid-based view of test coverage across all dimensions
defined in [VISION.md](VISION.md). Each matrix crosses two dimensions to reveal
coverage gaps and prioritization targets.

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
| Core (transfer)    | +          | +++        | -          | -          | -          | -          |
| Burn               | -          | ++         | -          | -          | n/a        | -          |
| Multisig           | -          | ++         | -          | -          | n/a        | -          |
| Energy / Freeze    | +          | +++        | -          | -          | n/a        | -          |
| Energy / Delegate  | -          | +++        | -          | -          | n/a        | -          |
| Escrow             | -          | +++        | -          | -          | n/a        | -          |
| Arbitration        | -          | +++        | -          | -          | n/a        | -          |
| KYC                | -          | +++        | -          | -          | n/a        | -          |
| Committee          | -          | +++        | -          | -          | n/a        | -          |
| Contracts          | -          | +++        | -          | -          | n/a        | -          |
| Privacy (UNO)      | -          | +++        | -          | -          | n/a        | -          |
| Privacy (shield)   | -          | +++        | -          | -          | n/a        | -          |
| TNS (names)        | -          | +++        | -          | -          | n/a        | -          |
| Referral           | -          | +++        | -          | -          | n/a        | -          |
| Account / Agent    | -          | +++        | -          | -          | n/a        | -          |
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

**Reading this matrix:** The overwhelming concentration at L1 is expected at this
stage (109/109 conformance). The priority gaps are:
- L0: wire format coverage beyond transfer and energy freeze
- L2: no executable block processing tests yet
- L3-L5: entirely unimplemented

## Matrix 2: Domain x Fixture Type

Which fixture types apply to each domain.

| Domain             | StateTest | BlockchainTest | TransactionTest | CodecTest | ContractTest | ConsensusTest | CryptoTest | RPCTest | EngineTest | FuzzCorpusTest |
|--------------------|-----------|----------------|-----------------|-----------|--------------|---------------|------------|---------|------------|----------------|
| Core (transfer)    | 10v       | planned        | 1v              | planned   | n/a          | n/a           | n/a        | planned | planned    | planned        |
| Burn               | 4v        | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Multisig           | 4v        | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Energy / Freeze    | 10v       | planned        | 1v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Energy / Delegate  | 4v        | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Escrow             | 51v       | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Arbitration        | 38v       | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| KYC                | 15v       | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Committee          | 26v       | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Contracts          | 11v       | planned        | planned         | planned   | planned      | n/a           | n/a        | planned | n/a        | planned        |
| Privacy (UNO)      | 3v        | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Privacy (shield)   | 4v        | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| TNS (names)        | 10v       | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Referral           | 7v        | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Account / Agent    | 19v       | planned        | planned         | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Consensus          | n/a       | planned        | n/a             | n/a       | n/a          | 6v            | n/a        | n/a     | planned    | planned        |
| Cryptography       | n/a       | n/a            | n/a             | n/a       | n/a          | n/a           | partial    | n/a     | n/a        | planned        |
| Security           | n/a       | n/a            | n/a             | n/a       | n/a          | n/a           | n/a        | n/a     | n/a        | planned        |
| System Models      | n/a       | n/a            | n/a             | n/a       | n/a          | n/a           | n/a        | n/a     | n/a        | n/a            |

`Nv` = N vectors exist. `planned` = applicable but not yet implemented. `partial` = spec-level coverage exists.

## Matrix 3: Domain x Test Aspect

What aspects are tested for each domain. Aspects represent the testing perspective
(what question is being asked), orthogonal to layers and fixture types.

| Domain             | Happy Path | Error Path | Boundary | Overflow | Auth/ACL | Self-ref | Fee Variant | Fork Param |
|--------------------|------------|------------|----------|----------|----------|----------|-------------|------------|
| Core (transfer)    | YES        | YES        | YES      | -        | -        | YES      | -           | -          |
| Burn               | YES        | YES        | -        | -        | -        | n/a      | -           | -          |
| Multisig           | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| Energy / Freeze    | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| Energy / Delegate  | YES        | YES        | YES      | -        | -        | YES      | -           | -          |
| Escrow             | YES        | YES        | YES      | -        | YES      | YES      | -           | -          |
| Arbitration        | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| KYC                | YES        | YES        | YES      | -        | YES      | -        | -           | -          |
| Committee          | YES        | YES        | YES      | -        | YES      | -        | -           | -          |
| Contracts          | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| Privacy (UNO)      | YES        | YES        | -        | -        | -        | YES      | -           | -          |
| Privacy (shield)   | YES        | YES        | YES      | -        | -        | -        | -           | -          |
| TNS (names)        | YES        | YES        | YES      | -        | -        | YES      | -           | -          |
| Referral           | YES        | YES        | YES      | -        | -        | YES      | -           | -          |
| Account / Agent    | YES        | YES        | YES      | -        | -        | -        | -           | -          |

**Reading this matrix:** Happy and error paths have broad coverage. Boundary testing
now covers 13 of 15 domains. Auth/ACL testing covers 4 domains (KYC, Committee,
Escrow, Energy). The remaining empty columns (Overflow, Fee Variant, Fork Param)
represent systematic gaps that should be addressed next.

## Matrix 4: Transaction Type x Test Count

Detailed per-type coverage showing how many tests and vectors exist for each of the
43 transaction types.

| # | Transaction Type          | Handler Module | Tests | Vectors | Neg Tests | Wire Tests |
|---|---------------------------|----------------|-------|---------|-----------|------------|
| 1 | transfers                 | core           | 10    | 10      | 7         | 1          |
| 2 | burn                      | core           | 4     | 3       | 3         | 0          |
| 3 | multisig                  | account        | 4     | 4       | 2         | 0          |
| 4 | invoke_contract           | contracts      | 7     | 7       | 4         | 0          |
| 5 | deploy_contract           | contracts      | 4     | 3       | 3         | 0          |
| 6 | energy (freeze)           | energy         | 5     | 5       | 4         | 1          |
| 7 | energy (unfreeze)         | energy         | 3     | 3       | 2         | 0          |
| 8 | energy (delegate)         | energy         | 4     | 4       | 3         | 0          |
| 9 | energy (withdraw)         | energy         | 2     | 2       | 1         | 0          |
|10 | bind_referrer             | referral       | 3     | 3       | 2         | 0          |
|11 | batch_referral_reward     | referral       | 4     | 0\*     | 3         | 0          |
|12 | set_kyc                   | kyc            | 4     | 4       | 3         | 0          |
|13 | revoke_kyc                | kyc            | 4     | 4       | 3         | 0          |
|14 | renew_kyc                 | kyc            | 2     | 2       | 1         | 0          |
|15 | transfer_kyc              | kyc            | 5     | 5       | 4         | 0          |
|16 | appeal_kyc                | kyc            | 6     | 6       | 5         | 0          |
|17 | bootstrap_committee       | kyc            | 7     | 7       | 6         | 0          |
|18 | register_committee        | kyc            | 4     | 4       | 3         | 0          |
|19 | update_committee          | kyc            | 5     | 5       | 4         | 0          |
|20 | emergency_suspend         | kyc            | 4     | 4       | 3         | 0          |
|21 | agent_account             | account        | 15    | 15      | 12        | 0          |
|22 | uno_transfers             | privacy        | 3     | 3       | 2         | 0          |
|23 | shield_transfers          | privacy        | 4     | 4       | 3         | 0          |
|24 | unshield_transfers        | privacy        | 3     | 3       | 2         | 0          |
|25 | register_name             | tns            | 4     | 4       | 2         | 0          |
|26 | ephemeral_message         | tns            | 6     | 0\*     | 5         | 0          |
|27 | create_escrow             | escrow         | 6     | 6       | 5         | 0          |
|28 | deposit_escrow            | escrow         | 4     | 4       | 3         | 0          |
|29 | release_escrow            | escrow         | 7     | 7       | 6         | 0          |
|30 | refund_escrow             | escrow         | 6     | 6       | 5         | 0          |
|31 | challenge_escrow          | escrow         | 6     | 6       | 5         | 0          |
|32 | dispute_escrow            | escrow         | 7     | 7       | 6         | 0          |
|33 | appeal_escrow             | escrow         | 8     | 8       | 7         | 0          |
|34 | submit_verdict            | escrow         | 6     | 6       | 5         | 0          |
|35 | submit_verdict_by_juror   | escrow         | 2     | 0\*     | 1         | 0          |
|36 | commit_arbitration_open   | arbitration    | 2     | 2       | 1         | 0          |
|37 | commit_vote_request       | arbitration    | 2     | 2       | 1         | 0          |
|38 | commit_selection          | arbitration    | 2     | 2       | 1         | 0          |
|39 | commit_juror_vote         | arbitration    | 2     | 2       | 1         | 0          |
|40 | register_arbiter          | arbitration    | 8     | 8       | 7         | 0          |
|41 | update_arbiter            | arbitration    | 5     | 5       | 4         | 0          |
|42 | slash_arbiter             | arbitration    | 4     | 4       | 3         | 0          |
|43 | request_arbiter_exit      | arbitration    | 4     | 4       | 3         | 0          |
|44 | withdraw_arbiter_stake    | arbitration    | 4     | 4       | 3         | 0          |
|45 | cancel_arbiter_exit       | arbitration    | 3     | 3       | 2         | 0          |
|   | **TOTAL**                 |                |**215**|**199**  | **176**   | **2**      |

`*` Vectors = 0 because the wire codec does not yet support this tx type;
tests exist at spec level but are marked `runnable: false` in vector output.

**Reading this matrix:** All 45 types now have at least 2 tests with comprehensive
negative coverage. 215 tests total, 176 negative tests. 3 types lack runnable
vectors pending codec support (batch_referral_reward, ephemeral_message,
submit_verdict_by_juror). Wire format coverage remains minimal (2/45).

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
| P0       | Wire format all 43 tx types   | L0     | ~43          | Medium | High    |
| P0       | Negative wire format (invalid) | L0     | ~20          | Low    | High    |
| P1       | Boundary values per tx type   | L1     | ~86          | Medium | High    |
| P1       | Overflow arithmetic           | L1     | ~20          | Low    | High    |
| P1       | Insufficient balance variants | L1     | ~30          | Low    | Medium  |
| P1       | Wrong nonce / auth failures   | L1     | ~30          | Low    | Medium  |
| P2       | Fee type variations           | L1     | ~43          | Medium | Medium  |
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

Aggregate coverage quality per handler module.

| Module      | Types | Tests | Vectors | Neg | Wire | Boundary | Depth Score |
|-------------|-------|-------|---------|-----|------|----------|-------------|
| core        | 2     | 14    | 13      | 10  | 1    | 1        | 4/5         |
| energy      | 4     | 14    | 14      | 10  | 1    | 1        | 4/5         |
| escrow      | 9     | 52    | 50      | 43  | 0    | 1        | 3/5         |
| arbitration | 10    | 36    | 36      | 26  | 0    | 1        | 3/5         |
| kyc         | 8     | 41    | 41      | 32  | 0    | 1        | 3/5         |
| contracts   | 2     | 11    | 10      | 7   | 0    | 1        | 3/5         |
| privacy     | 3     | 10    | 10      | 7   | 0    | 1        | 3/5         |
| referral    | 2     | 7     | 3       | 5   | 0    | 1        | 3/5         |
| tns         | 2     | 10    | 4       | 7   | 0    | 1        | 3/5         |
| account     | 2     | 19    | 19      | 14  | 0    | 1        | 3/5         |

Depth score criteria (1 point each):
1. All types have at least 1 vector
2. All types have at least 1 negative test
3. At least 1 wire format test exists
4. At least 1 boundary value test exists
5. At least 1 fee variant test exists

## Summary: Coverage Heat Map

```
                     L0     L1     L2     L3     L4     L5
                   +------+------+------+------+------+------+
   Core tx         | LOW  | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Energy          | LOW  | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Escrow          | NONE | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Arbitration     | NONE | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   KYC/Committee   | NONE | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Contracts       | NONE | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Privacy         | NONE | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   TNS/Referral    | NONE | GOOD | NONE | NONE | NONE | NONE |
                   +------+------+------+------+------+------+
   Account/Agent   | NONE | GOOD | NONE | NONE | NONE | NONE |
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
