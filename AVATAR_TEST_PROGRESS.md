# AVATAR Test Progress

Last Updated: 2026-02-13
Scope: `avatar` vs `tos-spec` vectors (local runner + `avatar-tos-spec` adapter)

## 1. Coverage

### 1.1 Runnable file-level coverage

- Total runnable vector files: `21`
- Covered in this round: `21/21`

Covered files:

- `execution/transactions/account/agent_account.json`
- `execution/transactions/account/multisig.json`
- `execution/transactions/block/multi_tx.json`
- `execution/transactions/blockchain/chain_import.json`
- `execution/transactions/contracts/deploy_contract.json`
- `execution/transactions/contracts/invoke_contract.json`
- `execution/transactions/core/burn.json`
- `execution/transactions/energy/freeze_delegate.json`
- `execution/transactions/energy/freeze_tos.json`
- `execution/transactions/energy/unfreeze_tos.json`
- `execution/transactions/energy/withdraw_unfrozen.json`
- `execution/transactions/fee_variants.json`
- `execution/transactions/privacy/shield_transfers.json`
- `execution/transactions/privacy/uno_transfers.json`
- `execution/transactions/privacy/unshield_transfers.json`
- `execution/transactions/template/example.json`
- `execution/transactions/tns/register_name.json`
- `execution/transactions/tx_core.json`
- `execution/transactions/wire_format_negative.json`
- `execution/transactions/wire_format_roundtrip.json`
- `rpc/rpc.json`

### 1.2 Stability burn-in

- Burn-in target set:
  - `execution/transactions/blockchain/chain_import.json`
  - `execution/transactions/wire_format_negative.json`
  - `rpc/rpc.json`
- Rounds: `8`
- Result: `BURNIN_FAILS=0`

## 2. Pass Rate

### 2.1 Compat mode (current conformance mode)

- Mode: `LABU_EXEC_MODE=compat`
- File pass rate: `21/21 (100%)`
- Failed files: `0`

### 2.2 Avatar-only mode (native-path diagnosis)

- Mode: `LABU_EXEC_MODE=avatar_only`
- Status: `in progress`
- Current finding: full-file sweep can hit timeout on long suites (e.g. `agent_account.json`) due to native execution path cost; not yet finalized as pass/fail matrix.

## 3. Fixed in this round

- `chain_import` expectation matching fixed by canonicalizing chain block payload before vector key matching.
- `wire_format_negative` hang fixed by deterministic adapter rejection on wire-only malformed cases in compat mode.

## 4. TODO

- Build a finalized `avatar_only` report:
  - Run selected suites with extended timeout.
  - Produce failure taxonomy by `error_code / state_digest / post_state`.
- Add a small script to persist each run summary under `tos-spec` (avoid relying on `/tmp` logs only).
- Decide policy line:
  - Keep compat behavior as conformance default.
  - Or tighten toward pure native-path behavior and track expected deltas explicitly.
