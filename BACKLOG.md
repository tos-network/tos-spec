# YAML Fixture Priority Backlog

Prioritized checklist of all **64** YAML fixture files under `fixtures/`,
ordered by implementation priority for converting into executable Python spec tests.

> **Note:** The 36 crypto test-vector YAMLs (cross-client function equality checks)
> live in `rust_generators/crypto/` and are managed separately from this backlog.

## Priority Criteria

1. **Dependency chain** — foundational modules first (others build on them)
2. **Existing spec coverage** — types with encoding already done but verify/apply missing are cheaper
3. **Testability** — transaction types producing state transitions are most valuable for conformance
4. **Complexity** — simpler items first to build momentum; crypto/privacy last

---

## Tier 1: Core Transactions (encoding + partial spec exist)

These have `encoding.py` support and `state_transition.py` dispatch. Closest to done.

- [ ] `transactions/core/burn.yaml` — `tx/core.py` — Partial (test exists)
- [ ] `transactions/energy/freeze_tos.yaml` — `tx/energy.py` — Stub
- [ ] `transactions/energy/freeze_delegate.yaml` — `tx/energy.py` — Stub
- [ ] `transactions/energy/unfreeze_tos.yaml` — `tx/energy.py` — Stub
- [ ] `transactions/energy/withdraw_unfrozen.yaml` — `tx/energy.py` — Stub
- [ ] `models/energy_system.yaml` — `account_model.py` — Partial
- [ ] `models/fee_model.yaml` — fee logic in `state_transition.py` — Partial
- [ ] `models/account_model.yaml` — `account_model.py` — Partial
- [ ] `models/block_limits.yaml` — `config.py` — Constants only

## Tier 2: Account Management

- [ ] `transactions/account/multisig.yaml` — new `tx/account.py` — Not started
- [ ] `transactions/account/agent_account.yaml` — new `tx/account.py` — Not started
- [ ] `transactions/referral/bind_referrer.yaml` — new `tx/referral.py` — Not started
- [ ] `transactions/tns/register_name.yaml` — new `tx/tns.py` — Not started

## Tier 3: KYC & Committee

- [ ] `transactions/kyc/bootstrap_committee.yaml` — new `tx/kyc.py` — Not started
- [ ] `transactions/kyc/register_committee.yaml` — `tx/kyc.py` — Not started
- [ ] `transactions/kyc/update_committee.yaml` — `tx/kyc.py` — Not started
- [ ] `transactions/kyc/set_kyc.yaml` — `tx/kyc.py` — Not started
- [ ] `transactions/kyc/revoke_kyc.yaml` — `tx/kyc.py` — Not started
- [ ] `transactions/kyc/transfer_kyc.yaml` — `tx/kyc.py` — Not started
- [ ] `transactions/kyc/appeal_kyc.yaml` — `tx/kyc.py` — Not started
- [ ] `transactions/kyc/emergency_suspend.yaml` — `tx/kyc.py` — Not started

## Tier 4: Escrow

- [ ] `transactions/escrow/create_escrow.yaml` — new `tx/escrow.py` — Not started
- [ ] `transactions/escrow/deposit_escrow.yaml` — `tx/escrow.py` — Not started
- [ ] `transactions/escrow/release_escrow.yaml` — `tx/escrow.py` — Not started
- [ ] `transactions/escrow/refund_escrow.yaml` — `tx/escrow.py` — Not started
- [ ] `transactions/escrow/challenge_escrow.yaml` — `tx/escrow.py` — Not started
- [ ] `transactions/escrow/dispute_escrow.yaml` — `tx/escrow.py` — Not started
- [ ] `transactions/escrow/appeal_escrow.yaml` — `tx/escrow.py` — Not started
- [ ] `transactions/escrow/submit_verdict.yaml` — `tx/escrow.py` — Not started

## Tier 5: Arbitration

- [ ] `transactions/arbitration/register_arbiter.yaml` — new `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/update_arbiter.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/request_arbiter_exit.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/withdraw_arbiter_stake.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/cancel_arbiter_exit.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/slash_arbiter.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/commit_arbitration_open.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/commit_vote_request.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/commit_selection_commitment.yaml` — `tx/arbitration.py` — Not started
- [ ] `transactions/arbitration/commit_juror_vote.yaml` — `tx/arbitration.py` — Not started

## Tier 6: Contracts

- [ ] `transactions/contracts/deploy_contract.yaml` — new `tx/contracts.py` — Not started
- [ ] `transactions/contracts/invoke_contract.yaml` — `tx/contracts.py` — Not started

## Tier 7: Privacy (requires crypto libraries)

- [ ] `transactions/privacy/uno_transfers.yaml` — `tx/privacy.py` — Stub
- [ ] `transactions/privacy/shield_transfers.yaml` — `tx/privacy.py` — Stub
- [ ] `transactions/privacy/unshield_transfers.yaml` — `tx/privacy.py` — Stub

## Tier 8: Consensus

- [ ] `consensus/block_validation.yaml` — `consensus/block_structure.py` — Partial
- [ ] `consensus/fork_choice.yaml` — `consensus/blockdag_ordering.py` — Partial
- [ ] `consensus/finality.yaml` — new `consensus/finality.py` — Not started
- [ ] `consensus/transaction_ordering.yaml` — new `consensus/mempool.py` — Not started

## Tier 9: Documentation-Only (no Python spec needed)

These are purely descriptive — no executable test data.
Keep as-is for conformance documentation; no Python spec conversion required.

### Security conformance docs

- [ ] `security/access_control.yaml` — doc only
- [ ] `security/dos_protection.yaml` — doc only
- [ ] `security/overflow.yaml` — doc only
- [ ] `security/reentrancy.yaml` — doc only

### Syscall interface docs

- [ ] `syscalls/balance_get.yaml` — doc only
- [ ] `syscalls/balance_transfer.yaml` — doc only
- [ ] `syscalls/call.yaml` — doc only
- [ ] `syscalls/code.yaml` — doc only
- [ ] `syscalls/crypto.yaml` — doc only
- [ ] `syscalls/environment.yaml` — doc only
- [ ] `syscalls/events.yaml` — doc only
- [ ] `syscalls/memory.yaml` — doc only
- [ ] `syscalls/nft.yaml` — doc only
- [ ] `syscalls/storage.yaml` — doc only

### API schema docs

- [ ] `api/rpc_methods.yaml` — doc only
- [ ] `api/websocket.yaml` — doc only

---

## Summary

| Tier | Category | Count | Dependencies |
|------|----------|------:|--------------|
| 1 | Core Transactions + Models | 9 | None — encoding exists |
| 2 | Account Management | 4 | Tier 1 account_model |
| 3 | KYC & Committee | 8 | Tier 1 |
| 4 | Escrow | 8 | Tier 3 (KYC gating) |
| 5 | Arbitration | 10 | Tier 4 (escrow disputes) |
| 6 | Contracts | 2 | Tier 1 |
| 7 | Privacy | 3 | External crypto libs |
| 8 | Consensus | 4 | Tier 1 block model |
| 9 | Documentation-Only | 16 | N/A |
| | **Total** | **64** | |

> 36 crypto test-vector YAMLs tracked separately in `rust_generators/crypto/`.

## Implementation Notes

- Follow the `Policy.md` pattern: write `tests/test_<thing>.py` → generate fixtures → convert to vectors
- Tier 1 is highest priority: encoding already exists, `account_model.py` has data structures, `config.py` has constants
- Tiers 1–6 are pure Python logic (no external crypto libraries needed)
- Tier 7 (Privacy) requires external Python crypto libraries
- Tier 9 files are documentation — no Python spec conversion needed
- Crypto test vectors (36 files) live in `rust_generators/crypto/` — managed by Rust generators, not this backlog
