"""Arbitration transaction specs."""

from __future__ import annotations

from copy import deepcopy

from ..config import (
    MAX_ARBITER_NAME_LEN,
    MAX_ARBITRATION_OPEN_BYTES,
    MAX_FEE_BPS,
    MAX_JUROR_VOTE_BYTES,
    MAX_SELECTION_COMMITMENT_BYTES,
    MAX_VOTE_REQUEST_BYTES,
    MIN_ARBITER_STAKE,
)
from ..errors import ErrorCode, SpecError
from ..types import (
    ArbiterAccount,
    ArbiterStatus,
    ArbitrationCommit,
    ChainState,
    Transaction,
    TransactionType,
)

_ARBITER_TYPES = frozenset({
    TransactionType.REGISTER_ARBITER,
    TransactionType.UPDATE_ARBITER,
    TransactionType.SLASH_ARBITER,
    TransactionType.REQUEST_ARBITER_EXIT,
    TransactionType.WITHDRAW_ARBITER_STAKE,
    TransactionType.CANCEL_ARBITER_EXIT,
})

_COMMIT_TYPES = frozenset({
    TransactionType.COMMIT_ARBITRATION_OPEN,
    TransactionType.COMMIT_VOTE_REQUEST,
    TransactionType.COMMIT_SELECTION_COMMITMENT,
    TransactionType.COMMIT_JUROR_VOTE,
})


def _to_bytes(v: object) -> bytes:
    if isinstance(v, bytes):
        return v
    if isinstance(v, (list, tuple)):
        return bytes(v)
    return bytes(32)


def verify(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbitration payload must be dict")

    tt = tx.tx_type
    if tt == TransactionType.REGISTER_ARBITER:
        _verify_register_arbiter(state, tx, p)
    elif tt == TransactionType.UPDATE_ARBITER:
        _verify_update_arbiter(state, tx, p)
    elif tt == TransactionType.SLASH_ARBITER:
        _verify_slash_arbiter(state, tx, p)
    elif tt == TransactionType.REQUEST_ARBITER_EXIT:
        _verify_request_exit(state, tx, p)
    elif tt == TransactionType.WITHDRAW_ARBITER_STAKE:
        _verify_withdraw_stake(state, tx, p)
    elif tt == TransactionType.CANCEL_ARBITER_EXIT:
        _verify_cancel_exit(state, tx, p)
    elif tt == TransactionType.COMMIT_ARBITRATION_OPEN:
        _verify_commit_arb_open(state, tx, p)
    elif tt == TransactionType.COMMIT_VOTE_REQUEST:
        _verify_commit_vote_request(state, tx, p)
    elif tt == TransactionType.COMMIT_SELECTION_COMMITMENT:
        _verify_commit_selection(state, tx, p)
    elif tt == TransactionType.COMMIT_JUROR_VOTE:
        _verify_commit_juror_vote(state, tx, p)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported arbitration tx type: {tt}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    p = tx.payload
    tt = tx.tx_type
    if tt == TransactionType.REGISTER_ARBITER:
        return _apply_register_arbiter(state, tx, p)
    elif tt == TransactionType.UPDATE_ARBITER:
        return _apply_update_arbiter(state, tx, p)
    elif tt == TransactionType.SLASH_ARBITER:
        return _apply_slash_arbiter(state, tx, p)
    elif tt == TransactionType.REQUEST_ARBITER_EXIT:
        return _apply_request_exit(state, tx, p)
    elif tt == TransactionType.WITHDRAW_ARBITER_STAKE:
        return _apply_withdraw_stake(state, tx, p)
    elif tt == TransactionType.CANCEL_ARBITER_EXIT:
        return _apply_cancel_exit(state, tx, p)
    elif tt in _COMMIT_TYPES:
        return _apply_commit(state, tx, p)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported arbitration tx type: {tt}")


# --- REGISTER_ARBITER ---

def _verify_register_arbiter(state: ChainState, tx: Transaction, p: dict) -> None:
    name = p.get("name", "")
    if not name or len(name) > MAX_ARBITER_NAME_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid arbiter name length")

    fee_bps = p.get("fee_basis_points", 0)
    if fee_bps < 0 or fee_bps > MAX_FEE_BPS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid fee basis points")

    stake = p.get("stake_amount", 0)
    if stake < MIN_ARBITER_STAKE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"stake too low (min {MIN_ARBITER_STAKE})")

    min_val = p.get("min_escrow_value", 0)
    max_val = p.get("max_escrow_value", 0)
    if min_val > max_val:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "min_escrow_value > max_escrow_value")

    if tx.source in state.arbiters:
        raise SpecError(ErrorCode.ACCOUNT_EXISTS, "arbiter already registered")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < stake:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for stake")


def _apply_register_arbiter(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    stake = p.get("stake_amount", 0)

    sender = ns.accounts[tx.source]
    sender.balance -= stake

    ns.arbiters[tx.source] = ArbiterAccount(
        public_key=tx.source,
        name=p.get("name", ""),
        status=ArbiterStatus.ACTIVE,
        expertise=list(p.get("expertise", [])),
        stake_amount=stake,
        fee_basis_points=p.get("fee_basis_points", 0),
        min_escrow_value=p.get("min_escrow_value", 0),
        max_escrow_value=p.get("max_escrow_value", 0),
        registered_at=ns.global_state.block_height,
    )
    return ns


# --- UPDATE_ARBITER ---

def _verify_update_arbiter(state: ChainState, tx: Transaction, p: dict) -> None:
    name = p.get("name")
    if name is not None and (not name or len(name) > MAX_ARBITER_NAME_LEN):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid arbiter name length")

    fee_bps = p.get("fee_basis_points")
    if fee_bps is not None and (fee_bps < 0 or fee_bps > MAX_FEE_BPS):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid fee basis points")

    if tx.source not in state.arbiters:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "arbiter not found")

    arbiter = state.arbiters[tx.source]
    if arbiter.status == ArbiterStatus.REMOVED:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter already removed")


def _apply_update_arbiter(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    arbiter = ns.arbiters[tx.source]

    name = p.get("name")
    if name is not None:
        arbiter.name = name

    fee_bps = p.get("fee_basis_points")
    if fee_bps is not None:
        arbiter.fee_basis_points = fee_bps

    min_val = p.get("min_escrow_value")
    if min_val is not None:
        arbiter.min_escrow_value = min_val

    max_val = p.get("max_escrow_value")
    if max_val is not None:
        arbiter.max_escrow_value = max_val

    add_stake = p.get("add_stake")
    if add_stake is not None and add_stake > 0:
        sender = ns.accounts[tx.source]
        if sender.balance < add_stake:
            raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for stake")
        sender.balance -= add_stake
        arbiter.stake_amount += add_stake

    deactivate = p.get("deactivate", False)
    if deactivate and arbiter.status == ArbiterStatus.ACTIVE:
        arbiter.status = ArbiterStatus.SUSPENDED

    return ns


# --- SLASH_ARBITER ---

def _verify_slash_arbiter(state: ChainState, tx: Transaction, p: dict) -> None:
    amount = p.get("amount", 0)
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "slash amount must be > 0")

    approvals = p.get("approvals", [])
    if not approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")

    reason_hash = _to_bytes(p.get("reason_hash"))
    if reason_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash must not be zero")


def _apply_slash_arbiter(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    arb_pk = _to_bytes(p.get("arbiter_pubkey"))
    amount = p.get("amount", 0)

    arbiter = ns.arbiters.get(arb_pk)
    if arbiter is not None:
        slash = min(amount, arbiter.stake_amount)
        arbiter.stake_amount -= slash
        arbiter.total_slashed += slash

    return ns


# --- REQUEST_ARBITER_EXIT ---

def _verify_request_exit(state: ChainState, tx: Transaction, p: dict) -> None:
    if tx.source not in state.arbiters:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "arbiter not found")
    arbiter = state.arbiters[tx.source]
    if arbiter.status != ArbiterStatus.ACTIVE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter must be active to request exit")
    if arbiter.active_cases > 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter has active cases")


def _apply_request_exit(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    ns.arbiters[tx.source].status = ArbiterStatus.EXITING
    return ns


# --- WITHDRAW_ARBITER_STAKE ---

def _verify_withdraw_stake(state: ChainState, tx: Transaction, p: dict) -> None:
    if tx.source not in state.arbiters:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "arbiter not found")
    arbiter = state.arbiters[tx.source]
    if arbiter.status != ArbiterStatus.EXITING:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter must be in exiting state")
    if arbiter.stake_amount <= 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "no stake to withdraw")


def _apply_withdraw_stake(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    arbiter = ns.arbiters[tx.source]
    stake = arbiter.stake_amount
    arbiter.stake_amount = 0
    arbiter.status = ArbiterStatus.REMOVED

    sender = ns.accounts.get(tx.source)
    if sender is not None:
        sender.balance += stake

    return ns


# --- CANCEL_ARBITER_EXIT ---

def _verify_cancel_exit(state: ChainState, tx: Transaction, p: dict) -> None:
    if tx.source not in state.arbiters:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "arbiter not found")
    arbiter = state.arbiters[tx.source]
    if arbiter.status != ArbiterStatus.EXITING:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter not in exiting state")


def _apply_cancel_exit(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    ns.arbiters[tx.source].status = ArbiterStatus.ACTIVE
    return ns


# --- COMMIT types ---

def _verify_commit_arb_open(state: ChainState, tx: Transaction, p: dict) -> None:
    payload_data = p.get("arbitration_open_payload", b"")
    if isinstance(payload_data, (list, tuple)):
        payload_data = bytes(payload_data)
    if len(payload_data) > MAX_ARBITRATION_OPEN_BYTES:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbitration_open_payload too large")


def _verify_commit_vote_request(state: ChainState, tx: Transaction, p: dict) -> None:
    payload_data = p.get("vote_request_payload", b"")
    if isinstance(payload_data, (list, tuple)):
        payload_data = bytes(payload_data)
    if len(payload_data) > MAX_VOTE_REQUEST_BYTES:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "vote_request_payload too large")


def _verify_commit_selection(state: ChainState, tx: Transaction, p: dict) -> None:
    payload_data = p.get("selection_commitment_payload", b"")
    if isinstance(payload_data, (list, tuple)):
        payload_data = bytes(payload_data)
    if len(payload_data) > MAX_SELECTION_COMMITMENT_BYTES:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "selection_commitment_payload too large")


def _verify_commit_juror_vote(state: ChainState, tx: Transaction, p: dict) -> None:
    payload_data = p.get("vote_payload", b"")
    if isinstance(payload_data, (list, tuple)):
        payload_data = bytes(payload_data)
    if len(payload_data) > MAX_JUROR_VOTE_BYTES:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "vote_payload too large")


def _apply_commit(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    tt = tx.tx_type

    if tt == TransactionType.COMMIT_ARBITRATION_OPEN:
        payload_hash = _to_bytes(p.get("arbitration_open_hash"))
        data = p.get("arbitration_open_payload", b"")
    elif tt == TransactionType.COMMIT_VOTE_REQUEST:
        payload_hash = _to_bytes(p.get("vote_request_hash"))
        data = p.get("vote_request_payload", b"")
    elif tt == TransactionType.COMMIT_SELECTION_COMMITMENT:
        payload_hash = _to_bytes(p.get("selection_commitment_id"))
        data = p.get("selection_commitment_payload", b"")
    elif tt == TransactionType.COMMIT_JUROR_VOTE:
        payload_hash = _to_bytes(p.get("vote_hash"))
        data = p.get("vote_payload", b"")
    else:
        return ns

    if isinstance(data, (list, tuple)):
        data = bytes(data)

    ns.arbitration_commits[payload_hash] = ArbitrationCommit(
        sender=tx.source, payload_hash=payload_hash, data=data
    )
    return ns
