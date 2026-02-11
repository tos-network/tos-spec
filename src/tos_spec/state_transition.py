"""State transition entrypoints for TOS Python specs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Optional

from .config import MAX_NONCE_GAP
from .errors import ErrorCode, SpecError
from .types import ChainState, FeeType, Transaction, TransactionType
from .tx import account as tx_account
from .tx import contracts as tx_contracts
from .tx import core as tx_core
from .tx import energy as tx_energy
from .tx import privacy as tx_privacy
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

_TNS_TYPES = frozenset({
    TransactionType.REGISTER_NAME,
})

_CONTRACT_TYPES = frozenset({
    TransactionType.DEPLOY_CONTRACT,
    TransactionType.INVOKE_CONTRACT,
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
    if tt in _CONTRACT_TYPES:
        return tx_contracts.verify(state, tx)
    if tt in _TNS_TYPES:
        return tx_tns.verify(state, tx)

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
    if tt in _CONTRACT_TYPES:
        return tx_contracts.apply(state, tx)
    if tt in _TNS_TYPES:
        return tx_tns.apply(state, tx)

    raise SpecError(ErrorCode.NOT_IMPLEMENTED, f"apply not implemented for {tx.tx_type}")


def _verify_common(state: ChainState, tx: Transaction) -> None:
    if tx.chain_id != state.network_chain_id:
        raise SpecError(ErrorCode.INVALID_TYPE, "chain_id mismatch")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")

    # Fee rules
    if tx.fee < 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "fee negative")

    # Matches `~/tos`: a subset of TOS-fee transactions reject `fee=0` (minimum fee surface).
    # Note: this is intentionally a narrow rule derived from current daemon behavior and vectors.
    _TOS_MIN_FEE_REQUIRED = {
        TransactionType.TRANSFERS,
        TransactionType.BURN,
        TransactionType.MULTISIG,
        TransactionType.DEPLOY_CONTRACT,
        TransactionType.AGENT_ACCOUNT,
    }
    if tx.fee_type == FeeType.TOS and tx.tx_type in _TOS_MIN_FEE_REQUIRED and tx.fee == 0:
        raise SpecError(ErrorCode.INSUFFICIENT_FEE, "fee too low")

    # Matches `~/tos`: Energy fee type is valid for transfer-type transactions (including privacy transfers).
    _ENERGY_FEE_ALLOWED = {
        TransactionType.TRANSFERS,
        TransactionType.UNO_TRANSFERS,
        TransactionType.SHIELD_TRANSFERS,
        TransactionType.UNSHIELD_TRANSFERS,
    }
    if tx.fee_type == FeeType.ENERGY and tx.tx_type not in _ENERGY_FEE_ALLOWED:
        raise SpecError(ErrorCode.INVALID_FORMAT, "energy fee only for transfer-type transactions")

    if tx.fee_type == FeeType.ENERGY and tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy fee must be zero")

    # Energy transactions must have zero fee regardless of fee_type
    if tx.tx_type == TransactionType.ENERGY and tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy transactions must have zero fee")

    if tx.fee_type == FeeType.UNO and tx.tx_type != TransactionType.UNO_TRANSFERS:
        raise SpecError(ErrorCode.INVALID_FORMAT, "uno fee only for uno transfers")

    if tx.fee_type == FeeType.UNO and tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_FORMAT, "uno fee must be zero")

    # Nonce range rules (verification phase)
    if tx.nonce < sender.nonce:
        raise SpecError(ErrorCode.NONCE_TOO_LOW, "nonce too low")

    if tx.nonce > sender.nonce + MAX_NONCE_GAP:
        raise SpecError(ErrorCode.NONCE_TOO_HIGH, "nonce too high")



def _check_fee_availability(state: ChainState, tx: Transaction) -> None:
    """Check sender has enough balance to cover the fee.

    Called after type-specific validation so that protocol violations
    (overflow, payload errors) take precedence over fee insufficiency.
    """
    sender = state.accounts.get(tx.source)
    if sender is None:
        return

    # TOS fee
    if tx.fee_type == FeeType.TOS:
        if sender.balance < tx.fee:
            raise SpecError(ErrorCode.INSUFFICIENT_FEE, "insufficient fee")
        return

    # UNO fee is always zero (validation above enforces that).
    if tx.fee_type == FeeType.UNO:
        return

    # Energy fee: 1 energy per transfer-type transaction with at least 1 output.
    if tx.fee_type == FeeType.ENERGY:
        output_count = 0
        if tx.tx_type == TransactionType.TRANSFERS and isinstance(tx.payload, list):
            output_count = len(tx.payload)
        elif tx.tx_type in _PRIVACY_TYPES and isinstance(tx.payload, dict):
            output_count = len(tx.payload.get("transfers", []) or [])
        energy_cost = 1 if output_count > 0 else 0
        # Energy is modeled both on AccountState and (optionally) EnergyResource.
        # When an EnergyResource exists, treat it as authoritative (matches daemon export).
        er = state.energy_resources.get(tx.source)
        energy_available = er.energy if er is not None else sender.energy
        if energy_available < energy_cost:
            raise SpecError(ErrorCode.INSUFFICIENT_ENERGY, "insufficient energy for fee")
        return

    raise SpecError(ErrorCode.INVALID_FORMAT, "unknown fee type")


def verify_tx(state: ChainState, tx: Transaction) -> TransitionResult:
    """Stateless + stateful verification for a single tx."""
    try:
        _verify_common(state, tx)
        _check_fee_availability(state, tx)
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
    - Pre-validation failure: no fee, no nonce, state unchanged
    - Execution failure: no fee, no nonce, state unchanged
    """
    # Pre-validation
    try:
        _verify_common(state, tx)
        # Strict nonce validation happens before execution.
        sender = state.accounts[tx.source]
        _require_strict_nonce(sender.nonce, tx.nonce)
        _check_fee_availability(state, tx)
        _dispatch_verify(state, tx)
    except SpecError as exc:
        return state, TransitionResult.failure(exc)

    working = deepcopy(state)
    sender = working.accounts[tx.source]

    try:
        working = _dispatch_apply(working, tx)
    except SpecError as exc:
        # Execution failure: state unchanged (no fee deducted)
        return state, TransitionResult.failure(exc)

    # Success: deduct fee + advance nonce
    sender = working.accounts[tx.source]
    sender.balance -= tx.fee
    sender.nonce += 1

    # Energy fee is consumed on success.
    if tx.fee_type == FeeType.ENERGY:
        output_count = 0
        if tx.tx_type == TransactionType.TRANSFERS and isinstance(tx.payload, list):
            output_count = len(tx.payload)
        elif tx.tx_type in _PRIVACY_TYPES and isinstance(tx.payload, dict):
            output_count = len(tx.payload.get("transfers", []) or [])
        energy_cost = 1 if output_count > 0 else 0
        if energy_cost:
            er = working.energy_resources.get(tx.source)
            if er is not None:
                er.energy -= energy_cost
                sender.energy = er.energy
            else:
                sender.energy -= energy_cost
    return working, TransitionResult.success()


def apply_block(state: ChainState, txs: list[Transaction]) -> tuple[ChainState, TransitionResult]:
    """Apply a block worth of transactions in order (block-atomic semantics).

    If any transaction fails, the entire block is rejected and the state is
    unchanged. This matches block acceptance rules (an invalid TX makes the
    whole block invalid).
    """
    working = state
    for tx in txs:
        working, result = apply_tx(working, tx)
        if not result.ok:
            return state, result

    working = replace(
        working,
        global_state=replace(
            working.global_state, block_height=working.global_state.block_height + 1
        ),
    )
    return working, TransitionResult.success()
