"""Core transaction specs (Transfers/Burn)."""

from __future__ import annotations

from copy import deepcopy

from ..config import EXTRA_DATA_LIMIT_SIZE, EXTRA_DATA_LIMIT_SUM_SIZE, MAX_TRANSFER_COUNT
from ..errors import ErrorCode, SpecError
from ..types import AccountState, ChainState, Transaction, TransactionType, TransferPayload

U64_MAX = (1 << 64) - 1


def verify(state: ChainState, tx: Transaction) -> None:
    if tx.tx_type == TransactionType.BURN:
        if not isinstance(tx.payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "burn payload must be dict")
        amount = int(tx.payload.get("amount", 0))
        if amount <= 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "burn amount invalid")
        if amount > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "burn amount exceeds u64 max")
        # Rust: fee.checked_add(amount) -> Err → InvalidFormat (wire deserialization)
        if tx.fee + amount > U64_MAX:
            raise SpecError(ErrorCode.INVALID_FORMAT, "burn amount plus fee overflow")
        return

    if tx.tx_type != TransactionType.TRANSFERS:
        raise SpecError(ErrorCode.INVALID_TYPE, "unsupported core tx type")

    if not isinstance(tx.payload, list) or not tx.payload:
        raise SpecError(ErrorCode.INVALID_FORMAT, "transfers list empty")

    if len(tx.payload) > MAX_TRANSFER_COUNT:
        raise SpecError(ErrorCode.INVALID_FORMAT, "too many transfers")

    total_extra = 0
    total_amount = 0
    for t in tx.payload:
        if not isinstance(t, TransferPayload):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid transfer payload")
        if t.destination == tx.source:
            raise SpecError(ErrorCode.SELF_OPERATION, "sender cannot be receiver")
        if t.amount < 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "transfer amount invalid")
        total_amount += t.amount
        if total_amount > U64_MAX:
            raise SpecError(ErrorCode.INSUFFICIENT_FEE, "total transfer amount overflow")
        if t.extra_data is not None:
            if len(t.extra_data) > EXTRA_DATA_LIMIT_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
            total_extra += len(t.extra_data)

    if total_extra > EXTRA_DATA_LIMIT_SUM_SIZE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "total extra_data too large")

    # Check amount + fee overflow (matches Rust checked_add on spending + fee)
    if total_amount + tx.fee > U64_MAX:
        raise SpecError(ErrorCode.INSUFFICIENT_FEE, "total amount plus fee overflow")

    # Check sender can afford total transfers + fee (Rust: verify_spending)
    sender = state.accounts.get(tx.source)
    if sender is not None and sender.balance < total_amount + tx.fee:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for transfers")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    next_state = deepcopy(state)
    if tx.tx_type == TransactionType.BURN:
        sender = next_state.accounts.get(tx.source)
        if sender is None:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
        amount = int(tx.payload.get("amount", 0))
        if sender.balance < amount:
            raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance")
        sender.balance -= amount
        if next_state.global_state.total_burned + amount > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "total_burned overflow")
        next_state.global_state.total_burned += amount
        return next_state

    if tx.tx_type != TransactionType.TRANSFERS:
        raise SpecError(ErrorCode.INVALID_TYPE, "unsupported core tx type")

    sender = next_state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")

    for t in tx.payload:
        if sender.balance < t.amount:
            raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance")
        sender.balance -= t.amount
        receiver = next_state.accounts.get(t.destination)
        if receiver is None:
            receiver = AccountState(address=t.destination, balance=0, nonce=0)
            next_state.accounts[t.destination] = receiver
        if receiver.balance + t.amount > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "receiver balance overflow")
        receiver.balance += t.amount

    return next_state
