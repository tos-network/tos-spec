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

**Reading this matrix:** L1 dominates as expected (382/382 conformance). L0 wire
format covers all 45 TX types plus 15 negative (malformed) wire tests. The
priority gaps are:
- L2: no executable block processing tests yet
- L3-L5: entirely unimplemented

## Matrix 2: Domain x Fixture Type

Which fixture types apply to each domain.

| Domain             | StateTest | BlockchainTest | TransactionTest | CodecTest | ContractTest | ConsensusTest | CryptoTest | RPCTest | EngineTest | FuzzCorpusTest |
|--------------------|-----------|----------------|-----------------|-----------|--------------|---------------|------------|---------|------------|----------------|
| Core (transfer)    | 28v       | planned        | 2v              | planned   | n/a          | n/a           | n/a        | planned | planned    | planned        |
| Burn               | 4v        | planned        | 1v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Multisig           | 7v        | planned        | 1v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Energy / Freeze    | 20v       | planned        | 4v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Energy / Delegate  | 20v       | planned        | 1v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Escrow             | 104v      | planned        | 9v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Arbitration        | 59v       | planned        | 10v             | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| KYC                | 18v       | planned        | 8v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Committee          | 42v       | planned        | 4v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Contracts          | 21v       | planned        | 2v              | planned   | planned      | n/a           | n/a        | planned | n/a        | planned        |
| Privacy (UNO)      | 7v        | planned        | 1v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Privacy (shield)   | 14v       | planned        | 2v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| TNS (names)        | 53v       | planned        | 2v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Referral           | 14v       | planned        | 2v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
| Account / Agent    | 36v       | planned        | 2v              | planned   | n/a          | n/a           | n/a        | planned | n/a        | planned        |
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

## Matrix 4: Transaction Type x Test Count

Detailed per-type coverage showing how many tests and vectors exist for each of the
43 transaction types.

| # | Transaction Type          | Handler Module | Tests | Vectors | Neg Tests | Wire Tests |
|---|---------------------------|----------------|-------|---------|-----------|------------|
| 1 | transfers                 | core           | 28    | 22      | 21        | 2          |
| 2 | burn                      | core           | 4     | 3       | 3         | 1          |
| 3 | multisig                  | account        | 7     | 6       | 4         | 1          |
| 4 | invoke_contract           | contracts      | 12    | 7       | 6         | 1          |
| 5 | deploy_contract           | contracts      | 9     | 6       | 6         | 1          |
| 6 | energy (freeze)           | energy         | 14    | 11      | 10        | 2          |
| 7 | energy (unfreeze)         | energy         | 6     | 6       | 5         | 1          |
| 8 | energy (delegate)         | energy         | 16    | 15      | 15        | 1          |
| 9 | energy (withdraw)         | energy         | 4     | 3       | 3         | 1          |
|10 | bind_referrer             | referral       | 4     | 4       | 2         | 1          |
|11 | batch_referral_reward     | referral       | 10    | 0\*     | 8         | 1          |
|12 | set_kyc                   | kyc            | 11    | 11      | 7         | 1          |
|13 | revoke_kyc                | kyc            | 6     | 6       | 5         | 1          |
|14 | renew_kyc                 | kyc            | 6     | 6       | 5         | 1          |
|15 | transfer_kyc              | kyc            | 7     | 7       | 6         | 1          |
|16 | appeal_kyc                | kyc            | 8     | 8       | 7         | 1          |
|17 | bootstrap_committee       | kyc            | 15    | 14      | 12        | 1          |
|18 | register_committee        | kyc            | 11    | 11      | 10        | 1          |
|19 | update_committee          | kyc            | 8     | 8       | 7         | 1          |
|20 | emergency_suspend         | kyc            | 8     | 7       | 6         | 1          |
|21 | agent_account             | account        | 29    | 28      | 18        | 1          |
|22 | uno_transfers             | privacy        | 7     | 2       | 4         | 1          |
|23 | shield_transfers          | privacy        | 9     | 2       | 7         | 1          |
|24 | unshield_transfers        | privacy        | 5     | 2       | 3         | 1          |
|25 | register_name             | tns            | 36    | 36      | 26        | 1          |
|26 | ephemeral_message         | tns            | 17    | 0\*     | 8         | 1          |
|27 | create_escrow             | escrow         | 25    | 12      | 18        | 1          |
|28 | deposit_escrow            | escrow         | 9     | 7       | 8         | 1          |
|29 | release_escrow            | escrow         | 9     | 9       | 8         | 1          |
|30 | refund_escrow             | escrow         | 13    | 9       | 9         | 1          |
|31 | challenge_escrow          | escrow         | 12    | 11      | 10        | 1          |
|32 | dispute_escrow            | escrow         | 10    | 10      | 7         | 1          |
|33 | appeal_escrow             | escrow         | 14    | 13      | 12        | 1          |
|34 | submit_verdict            | escrow         | 10    | 10      | 9         | 1          |
|35 | submit_verdict_by_juror   | escrow         | 2     | 0\*     | 1         | 1          |
|36 | commit_arbitration_open   | arbitration    | 3     | 1       | 1         | 1          |
|37 | commit_vote_request       | arbitration    | 3     | 1       | 1         | 1          |
|38 | commit_selection          | arbitration    | 3     | 1       | 1         | 1          |
|39 | commit_juror_vote         | arbitration    | 3     | 2       | 1         | 1          |
|40 | register_arbiter          | arbitration    | 14    | 13      | 9         | 1          |
|41 | update_arbiter            | arbitration    | 12    | 10      | 9         | 1          |
|42 | slash_arbiter             | arbitration    | 5     | 5       | 3         | 1          |
|43 | request_arbiter_exit      | arbitration    | 5     | 2       | 4         | 1          |
|44 | withdraw_arbiter_stake    | arbitration    | 7     | 5       | 6         | 1          |
|45 | cancel_arbiter_exit       | arbitration    | 4     | 2       | 3         | 1          |
|   | **Subtotal (per-type)**   |                |**460**|**354**  | **339**   | **45**     |
|   | fee_variants (cross-type) | -              | 20    | 6       | 18        | -          |
|   | consensus / models / misc | -              | 35    | 8       | -         | -          |
|   | wire_format (cross-type)  | -              | 45    | 0       | -         | 45         |
|   | **TOTAL**                 |                |**560**|**368**  | **357**   | **45**     |

`*` Vectors = 0 because the wire codec does not yet support this tx type;
tests exist at spec level but are marked `runnable: false` in vector output.

**Reading this matrix:** All 45 types have at least 2 tests with comprehensive
negative coverage. 560 pytest tests produce 699 total vectors; 368 are runnable
(passing conformance), 331 non-runnable (67 daemon-mismatch skips + codec gaps).
3 types lack runnable vectors pending codec support (batch_referral_reward,
ephemeral_message, submit_verdict_by_juror). Wire format coverage is complete
(45/45 types).

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

Aggregate coverage quality per handler module.

| Module      | Types | Tests | Vectors | Neg | Wire | Boundary | Fee Var | Depth Score |
|-------------|-------|-------|---------|-----|------|----------|---------|-------------|
| core        | 2     | 32    | 25      | 24  | 3    | YES      | YES     | 5/5         |
| energy      | 4     | 40    | 35      | 33  | 5    | YES      | YES     | 5/5         |
| escrow      | 9     | 104   | 81      | 82  | 9    | YES      | YES     | 5/5         |
| arbitration | 10    | 59    | 42      | 38  | 10   | YES      | YES     | 5/5         |
| kyc         | 8     | 80    | 78      | 65  | 8    | YES      | YES     | 5/5         |
| contracts   | 2     | 21    | 13      | 12  | 2    | YES      | YES     | 5/5         |
| privacy     | 3     | 21    | 6       | 14  | 3    | YES      | YES     | 5/5         |
| referral    | 2     | 14    | 4       | 10  | 2    | YES      | -       | 4/5         |
| tns         | 2     | 53    | 36      | 34  | 2    | YES      | YES     | 5/5         |
| account     | 2     | 36    | 34      | 22  | 2    | YES      | YES     | 5/5         |

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
