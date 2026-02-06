"""Escrow transaction specs."""

from __future__ import annotations

from copy import deepcopy

from blake3 import blake3

from ..config import (
    MAX_BPS,
    MAX_REASON_LEN,
    MAX_TASK_ID_LEN,
    MAX_TIMEOUT_BLOCKS,
    MIN_APPEAL_DEPOSIT_BPS,
    MIN_TIMEOUT_BLOCKS,
)
from ..errors import ErrorCode, SpecError
from ..types import (
    ChainState,
    EscrowAccount,
    EscrowStatus,
    Transaction,
    TransactionType,
)

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


def _to_bytes(v: object) -> bytes:
    if isinstance(v, bytes):
        return v
    if isinstance(v, (list, tuple)):
        return bytes(v)
    return bytes(32)


def _escrow_id_from_tx(tx: Transaction) -> bytes:
    buf = bytearray()
    buf += tx.source
    buf += tx.nonce.to_bytes(8, "big")
    return blake3(buf).digest()


def verify(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "escrow payload must be dict")

    tt = tx.tx_type
    if tt == TransactionType.CREATE_ESCROW:
        _verify_create(state, tx, p)
    elif tt == TransactionType.DEPOSIT_ESCROW:
        _verify_deposit(state, tx, p)
    elif tt == TransactionType.RELEASE_ESCROW:
        _verify_release(state, tx, p)
    elif tt == TransactionType.REFUND_ESCROW:
        _verify_refund(state, tx, p)
    elif tt == TransactionType.CHALLENGE_ESCROW:
        _verify_challenge(state, tx, p)
    elif tt == TransactionType.DISPUTE_ESCROW:
        _verify_dispute(state, tx, p)
    elif tt == TransactionType.APPEAL_ESCROW:
        _verify_appeal(state, tx, p)
    elif tt == TransactionType.SUBMIT_VERDICT:
        _verify_submit_verdict(state, tx, p)
    elif tt == TransactionType.SUBMIT_VERDICT_BY_JUROR:
        _verify_submit_verdict(state, tx, p)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported escrow tx type: {tt}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    p = tx.payload
    tt = tx.tx_type
    if tt == TransactionType.CREATE_ESCROW:
        return _apply_create(state, tx, p)
    elif tt == TransactionType.DEPOSIT_ESCROW:
        return _apply_deposit(state, tx, p)
    elif tt == TransactionType.RELEASE_ESCROW:
        return _apply_release(state, tx, p)
    elif tt == TransactionType.REFUND_ESCROW:
        return _apply_refund(state, tx, p)
    elif tt == TransactionType.CHALLENGE_ESCROW:
        return _apply_challenge(state, tx, p)
    elif tt == TransactionType.DISPUTE_ESCROW:
        return _apply_dispute(state, tx, p)
    elif tt == TransactionType.APPEAL_ESCROW:
        return _apply_appeal(state, tx, p)
    elif tt in (TransactionType.SUBMIT_VERDICT, TransactionType.SUBMIT_VERDICT_BY_JUROR):
        return _apply_submit_verdict(state, tx, p)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported escrow tx type: {tt}")


# --- CREATE_ESCROW ---

def _verify_create(state: ChainState, tx: Transaction, p: dict) -> None:
    amount = p.get("amount", 0)
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "escrow amount must be > 0")

    task_id = p.get("task_id", "")
    if not task_id or len(task_id) > MAX_TASK_ID_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid task_id")

    timeout = p.get("timeout_blocks", 0)
    if timeout < MIN_TIMEOUT_BLOCKS or timeout > MAX_TIMEOUT_BLOCKS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "timeout_blocks out of range")

    challenge_window = p.get("challenge_window", 0)
    if challenge_window <= 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "challenge_window must be > 0")

    challenge_bps = p.get("challenge_deposit_bps", 0)
    if challenge_bps < 0 or challenge_bps > MAX_BPS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid challenge_deposit_bps")

    provider = _to_bytes(p.get("provider"))
    if provider == tx.source:
        raise SpecError(ErrorCode.SELF_OPERATION, "payer cannot be provider")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < amount:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance")


def _apply_create(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    amount = p.get("amount", 0)
    eid = _escrow_id_from_tx(tx)
    height = ns.global_state.block_height

    sender = ns.accounts[tx.source]
    sender.balance -= amount

    ns.escrows[eid] = EscrowAccount(
        id=eid,
        task_id=p.get("task_id", ""),
        payer=tx.source,
        payee=_to_bytes(p.get("provider")),
        amount=amount,
        total_amount=amount,
        asset=_to_bytes(p.get("asset")),
        status=EscrowStatus.CREATED,
        timeout_blocks=p.get("timeout_blocks", 0),
        challenge_window=p.get("challenge_window", 0),
        challenge_deposit_bps=p.get("challenge_deposit_bps", 0),
        optimistic_release=p.get("optimistic_release", False),
        created_at=height,
        updated_at=height,
        timeout_at=height + p.get("timeout_blocks", 0),
    )
    return ns


# --- DEPOSIT_ESCROW ---

def _verify_deposit(state: ChainState, tx: Transaction, p: dict) -> None:
    amount = p.get("amount", 0)
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "deposit amount must be > 0")

    eid = _to_bytes(p.get("escrow_id"))
    escrow = state.escrows.get(eid)
    if escrow is not None and escrow.status not in (EscrowStatus.CREATED, EscrowStatus.FUNDED):
        raise SpecError(ErrorCode.ESCROW_WRONG_STATE, "escrow not in depositable state")


def _apply_deposit(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    eid = _to_bytes(p.get("escrow_id"))
    amount = p.get("amount", 0)

    sender = ns.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < amount:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance")
    sender.balance -= amount

    escrow = ns.escrows.get(eid)
    if escrow is not None:
        escrow.amount += amount
        escrow.total_amount += amount
        escrow.status = EscrowStatus.FUNDED
        escrow.updated_at = ns.global_state.block_height

    return ns


# --- RELEASE_ESCROW ---

def _verify_release(state: ChainState, tx: Transaction, p: dict) -> None:
    amount = p.get("amount", 0)
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "release amount must be > 0")

    eid = _to_bytes(p.get("escrow_id"))
    escrow = state.escrows.get(eid)
    if escrow is not None:
        if escrow.status != EscrowStatus.FUNDED:
            raise SpecError(ErrorCode.ESCROW_WRONG_STATE, "escrow not funded")
        if amount > escrow.amount:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "release amount exceeds escrow balance")


def _apply_release(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    eid = _to_bytes(p.get("escrow_id"))
    amount = p.get("amount", 0)

    escrow = ns.escrows.get(eid)
    if escrow is not None:
        escrow.amount -= amount
        escrow.released_amount += amount
        if escrow.amount == 0:
            escrow.status = EscrowStatus.RELEASED
        else:
            escrow.status = EscrowStatus.PENDING_RELEASE
        escrow.updated_at = ns.global_state.block_height

        payee = ns.accounts.get(escrow.payee)
        if payee is not None:
            payee.balance += amount

    return ns


# --- REFUND_ESCROW ---

def _verify_refund(state: ChainState, tx: Transaction, p: dict) -> None:
    amount = p.get("amount", 0)
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "refund amount must be > 0")

    reason = p.get("reason")
    if reason is not None and len(reason) > MAX_REASON_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason too long")

    eid = _to_bytes(p.get("escrow_id"))
    escrow = state.escrows.get(eid)
    if escrow is not None:
        if amount > escrow.amount:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "refund amount exceeds escrow balance")


def _apply_refund(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    eid = _to_bytes(p.get("escrow_id"))
    amount = p.get("amount", 0)

    escrow = ns.escrows.get(eid)
    if escrow is not None:
        escrow.amount -= amount
        escrow.refunded_amount += amount
        if escrow.amount == 0:
            escrow.status = EscrowStatus.REFUNDED
        escrow.updated_at = ns.global_state.block_height

        payer = ns.accounts.get(escrow.payer)
        if payer is not None:
            payer.balance += amount

    return ns


# --- CHALLENGE_ESCROW ---

def _verify_challenge(state: ChainState, tx: Transaction, p: dict) -> None:
    reason = p.get("reason", "")
    if not reason or len(reason) > MAX_REASON_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid challenge reason")

    deposit = p.get("deposit", 0)
    if deposit <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "challenge deposit must be > 0")


def _apply_challenge(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    eid = _to_bytes(p.get("escrow_id"))
    deposit = p.get("deposit", 0)

    sender = ns.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < deposit:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for deposit")
    sender.balance -= deposit

    escrow = ns.escrows.get(eid)
    if escrow is not None:
        escrow.challenge_deposit += deposit
        escrow.status = EscrowStatus.CHALLENGED
        escrow.updated_at = ns.global_state.block_height

    return ns


# --- DISPUTE_ESCROW ---

def _verify_dispute(state: ChainState, tx: Transaction, p: dict) -> None:
    reason = p.get("reason", "")
    if not reason or len(reason) > MAX_REASON_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid dispute reason")


def _apply_dispute(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    eid = _to_bytes(p.get("escrow_id"))
    escrow = ns.escrows.get(eid)
    if escrow is not None:
        escrow.status = EscrowStatus.CHALLENGED
        escrow.updated_at = ns.global_state.block_height
    return ns


# --- APPEAL_ESCROW ---

def _verify_appeal(state: ChainState, tx: Transaction, p: dict) -> None:
    reason = p.get("reason", "")
    if not reason or len(reason) > MAX_REASON_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid appeal reason")

    appeal_deposit = p.get("appeal_deposit", 0)
    if appeal_deposit <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "appeal deposit must be > 0")


def _apply_appeal(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    appeal_deposit = p.get("appeal_deposit", 0)

    sender = ns.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < appeal_deposit:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for appeal")
    sender.balance -= appeal_deposit

    return ns


# --- SUBMIT_VERDICT / SUBMIT_VERDICT_BY_JUROR ---

def _verify_submit_verdict(state: ChainState, tx: Transaction, p: dict) -> None:
    payer_amount = p.get("payer_amount", 0)
    payee_amount = p.get("payee_amount", 0)
    if payer_amount < 0 or payee_amount < 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "verdict amounts must be >= 0")

    sigs = p.get("signatures", [])
    if not sigs:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "signatures required")


def _apply_submit_verdict(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    eid = _to_bytes(p.get("escrow_id"))
    payer_amount = p.get("payer_amount", 0)
    payee_amount = p.get("payee_amount", 0)

    escrow = ns.escrows.get(eid)
    if escrow is not None:
        if payer_amount > 0:
            payer = ns.accounts.get(escrow.payer)
            if payer is not None:
                payer.balance += payer_amount
        if payee_amount > 0:
            payee = ns.accounts.get(escrow.payee)
            if payee is not None:
                payee.balance += payee_amount
        escrow.amount = 0
        escrow.status = EscrowStatus.RESOLVED
        escrow.updated_at = ns.global_state.block_height

    return ns
