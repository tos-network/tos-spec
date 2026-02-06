"""State transition entrypoints for TOS Python specs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Optional

from .config import MAX_NONCE_GAP
from .errors import ErrorCode, SpecError
from .types import ChainState, FeeType, Transaction, TransactionType
from .tx import account as tx_account
from .tx import arbitration as tx_arbitration
from .tx import contracts as tx_contracts
from .tx import core as tx_core
from .tx import energy as tx_energy
from .tx import escrow as tx_escrow
from .tx import kyc as tx_kyc
from .tx import privacy as tx_privacy
from .tx import referral as tx_referral
from .tx import tns as tx_tns

_PRIVACY_TYPES = frozenset({
    TransactionType.UNO_TRANSFERS,
    TransactionType.SHIELD_TRANSFERS,
    TransactionType.UNSHIELD_TRANSFERS,
})

_ACCOUNT_TYPES = frozenset({
    TransactionType.MULTISIG,
    TransactionType.AGENT_ACCOUNT,
})

_ARBITRATION_TYPES = frozenset({
    TransactionType.REGISTER_ARBITER,
    TransactionType.UPDATE_ARBITER,
    TransactionType.SLASH_ARBITER,
    TransactionType.REQUEST_ARBITER_EXIT,
    TransactionType.WITHDRAW_ARBITER_STAKE,
    TransactionType.CANCEL_ARBITER_EXIT,
    TransactionType.COMMIT_ARBITRATION_OPEN,
    TransactionType.COMMIT_VOTE_REQUEST,
    TransactionType.COMMIT_SELECTION_COMMITMENT,
    TransactionType.COMMIT_JUROR_VOTE,
})

_ESCROW_TYPES = frozenset({
    TransactionType.CREATE_ESCROW,
    TransactionType.DEPOSIT_ESCROW,
    TransactionType.RELEASE_ESCROW,
    TransactionType.REFUND_ESCROW,
    TransactionType.CHALLENGE_ESCROW,
    TransactionType.DISPUTE_ESCROW,
    TransactionType.APPEAL_ESCROW,
    TransactionType.SUBMIT_VERDICT,
    TransactionType.SUBMIT_VERDICT_BY_JUROR,
})

_REFERRAL_TYPES = frozenset({
    TransactionType.BIND_REFERRER,
    TransactionType.BATCH_REFERRAL_REWARD,
})

_TNS_TYPES = frozenset({
    TransactionType.REGISTER_NAME,
    TransactionType.EPHEMERAL_MESSAGE,
})

_CONTRACT_TYPES = frozenset({
    TransactionType.DEPLOY_CONTRACT,
    TransactionType.INVOKE_CONTRACT,
})

_KYC_TYPES = frozenset({
    TransactionType.SET_KYC,
    TransactionType.REVOKE_KYC,
    TransactionType.RENEW_KYC,
    TransactionType.TRANSFER_KYC,
    TransactionType.APPEAL_KYC,
    TransactionType.BOOTSTRAP_COMMITTEE,
    TransactionType.REGISTER_COMMITTEE,
    TransactionType.UPDATE_COMMITTEE,
    TransactionType.EMERGENCY_SUSPEND,
})


class TransitionResult:
    """Thin wrapper for verify/apply results."""

    def __init__(self, ok: bool, error: Optional[SpecError] = None):
        self.ok = ok
        self.error = error

    @classmethod
    def success(cls) -> "TransitionResult":
        return cls(True, None)

    @classmethod
    def failure(cls, error: SpecError) -> "TransitionResult":
        return cls(False, error)


def _dispatch_verify(state: ChainState, tx: Transaction) -> None:
    tt = tx.tx_type
    if tt in (TransactionType.TRANSFERS, TransactionType.BURN):
        return tx_core.verify(state, tx)
    if tt == TransactionType.ENERGY:
        return tx_energy.verify(state, tx)
    if tt in _PRIVACY_TYPES:
        return tx_privacy.verify(state, tx)
    if tt in _ACCOUNT_TYPES:
        return tx_account.verify(state, tx)
    if tt in _ARBITRATION_TYPES:
        return tx_arbitration.verify(state, tx)
    if tt in _CONTRACT_TYPES:
        return tx_contracts.verify(state, tx)
    if tt in _ESCROW_TYPES:
        return tx_escrow.verify(state, tx)
    if tt in _REFERRAL_TYPES:
        return tx_referral.verify(state, tx)
    if tt in _TNS_TYPES:
        return tx_tns.verify(state, tx)
    if tt in _KYC_TYPES:
        return tx_kyc.verify(state, tx)

    raise SpecError(ErrorCode.NOT_IMPLEMENTED, f"verify not implemented for {tx.tx_type}")


def _dispatch_apply(state: ChainState, tx: Transaction) -> ChainState:
    tt = tx.tx_type
    if tt in (TransactionType.TRANSFERS, TransactionType.BURN):
        return tx_core.apply(state, tx)
    if tt == TransactionType.ENERGY:
        return tx_energy.apply(state, tx)
    if tt in _PRIVACY_TYPES:
        return tx_privacy.apply(state, tx)
    if tt in _ACCOUNT_TYPES:
        return tx_account.apply(state, tx)
    if tt in _ARBITRATION_TYPES:
        return tx_arbitration.apply(state, tx)
    if tt in _CONTRACT_TYPES:
        return tx_contracts.apply(state, tx)
    if tt in _ESCROW_TYPES:
        return tx_escrow.apply(state, tx)
    if tt in _REFERRAL_TYPES:
        return tx_referral.apply(state, tx)
    if tt in _TNS_TYPES:
        return tx_tns.apply(state, tx)
    if tt in _KYC_TYPES:
        return tx_kyc.apply(state, tx)

    raise SpecError(ErrorCode.NOT_IMPLEMENTED, f"apply not implemented for {tx.tx_type}")


def _verify_common(state: ChainState, tx: Transaction) -> None:
    if tx.chain_id != state.network_chain_id:
        raise SpecError(ErrorCode.INVALID_VERSION, "chain_id mismatch")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")

    # Fee rules
    if tx.fee < 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "fee negative")

    if tx.fee_type == FeeType.ENERGY and tx.tx_type != TransactionType.TRANSFERS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy fee only for transfers")

    if tx.fee_type == FeeType.ENERGY and tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy fee must be zero")

    if tx.fee_type == FeeType.UNO and tx.tx_type != TransactionType.UNO_TRANSFERS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "uno fee only for uno transfers")

    if tx.fee_type == FeeType.UNO and tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "uno fee must be zero")

    # Nonce range rules (verification phase)
    if tx.nonce < sender.nonce:
        raise SpecError(ErrorCode.NONCE_TOO_LOW, "nonce too low")

    if tx.nonce > sender.nonce + MAX_NONCE_GAP:
        raise SpecError(ErrorCode.NONCE_TOO_HIGH, "nonce too high")

    # Fee availability check (pre-validation)
    if sender.balance < tx.fee:
        raise SpecError(ErrorCode.INSUFFICIENT_FEE, "insufficient fee")


def verify_tx(state: ChainState, tx: Transaction) -> TransitionResult:
    """Stateless + stateful verification for a single tx."""
    try:
        _verify_common(state, tx)
        _dispatch_verify(state, tx)
        return TransitionResult.success()
    except SpecError as exc:
        return TransitionResult.failure(exc)


def _require_strict_nonce(sender_nonce: int, tx_nonce: int) -> None:
    if tx_nonce < sender_nonce:
        raise SpecError(ErrorCode.NONCE_TOO_LOW, "nonce too low")
    if tx_nonce > sender_nonce:
        raise SpecError(ErrorCode.NONCE_TOO_HIGH, "nonce too high")


def apply_tx(state: ChainState, tx: Transaction) -> tuple[ChainState, TransitionResult]:
    """Apply tx to state after verification.

    Failed-tx semantics:
    - Pre-validation failure: no fee, no nonce
    - Execution failure: fee deducted, nonce advanced, payload effects rolled back
    """
    # Pre-validation
    try:
        _verify_common(state, tx)
        # Strict nonce validation happens before execution.
        sender = state.accounts[tx.source]
        _require_strict_nonce(sender.nonce, tx.nonce)
        _dispatch_verify(state, tx)
    except SpecError as exc:
        return state, TransitionResult.failure(exc)

    working = deepcopy(state)
    sender = working.accounts[tx.source]

    # Deduct fee + advance nonce
    sender.balance -= tx.fee
    sender.nonce += 1

    checkpoint = deepcopy(working)

    try:
        working = _dispatch_apply(working, tx)
        return working, TransitionResult.success()
    except SpecError as exc:
        # Roll back payload effects, keep fee + nonce
        return checkpoint, TransitionResult.failure(exc)


def apply_block(state: ChainState, txs: list[Transaction]) -> tuple[ChainState, TransitionResult]:
    """Apply a block worth of transactions in order."""
    working = state
    for tx in txs:
        working, result = apply_tx(working, tx)
        if not result.ok:
            return working, result
    working = replace(
        working,
        global_state=replace(
            working.global_state, block_height=working.global_state.block_height + 1
        ),
    )
    return working, TransitionResult.success()
