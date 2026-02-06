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

- [x] `transactions/core/burn.yaml` — `tx/core.py` — test_tx_burn.py
- [x] `transactions/energy/freeze_tos.yaml` — `tx/energy.py` — test_tx_energy.py
- [x] `transactions/energy/freeze_delegate.yaml` — `tx/energy.py` — test_tx_energy.py
- [x] `transactions/energy/unfreeze_tos.yaml` — `tx/energy.py` — test_tx_energy.py
- [x] `transactions/energy/withdraw_unfrozen.yaml` — `tx/energy.py` — test_tx_energy.py
- [x] `models/energy_system.yaml` — `account_model.py` — test_models.py
- [x] `models/fee_model.yaml` — fee logic in `state_transition.py` — test_models.py
- [x] `models/account_model.yaml` — `account_model.py` — test_models.py
- [x] `models/block_limits.yaml` — `config.py` — test_models.py

## Tier 2: Account Management

- [x] `transactions/account/multisig.yaml` — test_tx_account.py
- [x] `transactions/account/agent_account.yaml` — test_tx_account.py
- [x] `transactions/referral/bind_referrer.yaml` — test_tx_referral.py
- [x] `transactions/tns/register_name.yaml` — test_tx_tns.py

## Tier 3: KYC & Committee

- [x] `transactions/kyc/bootstrap_committee.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/register_committee.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/update_committee.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/set_kyc.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/revoke_kyc.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/transfer_kyc.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/appeal_kyc.yaml` — test_tx_kyc.py
- [x] `transactions/kyc/emergency_suspend.yaml` — test_tx_kyc.py

## Tier 4: Escrow

- [x] `transactions/escrow/create_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/deposit_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/release_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/refund_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/challenge_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/dispute_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/appeal_escrow.yaml` — test_tx_escrow.py
- [x] `transactions/escrow/submit_verdict.yaml` — test_tx_escrow.py

## Tier 5: Arbitration

- [x] `transactions/arbitration/register_arbiter.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/update_arbiter.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/request_arbiter_exit.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/withdraw_arbiter_stake.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/cancel_arbiter_exit.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/slash_arbiter.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/commit_arbitration_open.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/commit_vote_request.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/commit_selection_commitment.yaml` — test_tx_arbitration.py
- [x] `transactions/arbitration/commit_juror_vote.yaml` — test_tx_arbitration.py

## Tier 6: Contracts

- [x] `transactions/contracts/deploy_contract.yaml` — test_tx_contracts.py
- [x] `transactions/contracts/invoke_contract.yaml` — test_tx_contracts.py

## Tier 7: Privacy (requires crypto libraries)

- [x] `transactions/privacy/uno_transfers.yaml` — test_tx_privacy.py
- [x] `transactions/privacy/shield_transfers.yaml` — test_tx_privacy.py
- [x] `transactions/privacy/unshield_transfers.yaml` — test_tx_privacy.py

## Tier 8: Consensus

- [x] `consensus/block_validation.yaml` — test_consensus_block.py
- [x] `consensus/fork_choice.yaml` — test_consensus_block.py
- [x] `consensus/finality.yaml` — test_consensus_order.py
- [x] `consensus/transaction_ordering.yaml` — test_consensus_order.py

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
