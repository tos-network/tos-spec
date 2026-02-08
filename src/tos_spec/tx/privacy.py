"""Privacy transaction specs (UNO/Shield/Unshield).

Implements the verification rules from the Rust verify/mod.rs for:
- UNO transfers (encrypted-to-encrypted)
- Shield transfers (TOS -> UNO, plaintext to encrypted)
- Unshield transfers (UNO -> TOS, encrypted to plaintext)

ZKP proof verification is skipped (requires crypto libraries).
All structural / amount / limit validations are enforced.
"""

from __future__ import annotations

from copy import deepcopy

from ..config import (
    EXTRA_DATA_LIMIT_SIZE,
    EXTRA_DATA_LIMIT_SUM_SIZE,
    MAX_TRANSFER_COUNT,
    MIN_SHIELD_TOS_AMOUNT,
)
from ..errors import ErrorCode, SpecError
from ..types import AccountState, ChainState, Transaction, TransactionType

# TOS_ASSET is the zero hash (32 zero bytes)
TOS_ASSET = bytes(32)

U64_MAX = (1 << 64) - 1


def verify(state: ChainState, tx: Transaction) -> None:
    tt = tx.tx_type
    if tt == TransactionType.UNO_TRANSFERS:
        _verify_uno_transfers(state, tx)
    elif tt == TransactionType.SHIELD_TRANSFERS:
        _verify_shield_transfers(state, tx)
    elif tt == TransactionType.UNSHIELD_TRANSFERS:
        _verify_unshield_transfers(state, tx)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported privacy tx type: {tt}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    tt = tx.tx_type
    if tt == TransactionType.UNO_TRANSFERS:
        return _apply_uno_transfers(state, tx)
    elif tt == TransactionType.SHIELD_TRANSFERS:
        return _apply_shield_transfers(state, tx)
    elif tt == TransactionType.UNSHIELD_TRANSFERS:
        return _apply_unshield_transfers(state, tx)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported privacy tx type: {tt}")


# --- UNO transfers ---


def _verify_uno_transfers(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "uno payload must be dict")

    transfers = p.get("transfers", [])
    if not transfers or len(transfers) > MAX_TRANSFER_COUNT:
        raise SpecError(ErrorCode.INVALID_FORMAT, "invalid UNO transfer count")

    total_extra = 0
    for t in transfers:
        dest = t.get("destination")
        if dest == tx.source:
            raise SpecError(ErrorCode.SELF_OPERATION, "sender cannot be receiver")

        extra_data = t.get("extra_data")
        if extra_data is not None:
            if len(extra_data) > EXTRA_DATA_LIMIT_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
            total_extra += len(extra_data)

    if total_extra > EXTRA_DATA_LIMIT_SUM_SIZE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "total extra_data too large")


def _apply_uno_transfers(state: ChainState, tx: Transaction) -> ChainState:
    # UNO transfers operate on encrypted balances; in the spec we treat them
    # as a no-op on plaintext state (ZKP verification happens at the crypto layer).
    return deepcopy(state)


# --- Shield transfers (TOS -> UNO) ---


def _verify_shield_transfers(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "shield payload must be dict")

    transfers = p.get("transfers", [])
    if not transfers or len(transfers) > MAX_TRANSFER_COUNT:
        raise SpecError(ErrorCode.INVALID_FORMAT, "invalid shield transfer count")

    total_extra = 0
    total_amount = 0
    for t in transfers:
        amount = t.get("amount", 0)
        if amount <= 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "shield amount must be > 0")

        if amount < MIN_SHIELD_TOS_AMOUNT:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "shield amount below minimum")

        asset = t.get("asset")
        if asset != TOS_ASSET:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "shield transfers only support TOS asset")

        total_amount += amount
        if total_amount > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "shield total amount overflow")

        extra_data = t.get("extra_data")
        if extra_data is not None:
            if len(extra_data) > EXTRA_DATA_LIMIT_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
            total_extra += len(extra_data)

    if total_extra > EXTRA_DATA_LIMIT_SUM_SIZE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "total extra_data too large")

    # Balance check: sender must have enough TOS for all shield transfers + fee
    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < total_amount + tx.fee:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for shield")


def _apply_shield_transfers(state: ChainState, tx: Transaction) -> ChainState:
    ns = deepcopy(state)
    p = tx.payload
    transfers = p.get("transfers", [])

    sender = ns.accounts[tx.source]
    for t in transfers:
        amount = t.get("amount", 0)
        if sender.balance < amount:
            raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance")
        sender.balance -= amount

    return ns


# --- Unshield transfers (UNO -> TOS) ---


def _verify_unshield_transfers(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "unshield payload must be dict")

    transfers = p.get("transfers", [])
    if not transfers or len(transfers) > MAX_TRANSFER_COUNT:
        raise SpecError(ErrorCode.INVALID_FORMAT, "invalid unshield transfer count")

    total_extra = 0
    for t in transfers:
        amount = t.get("amount", 0)
        if amount <= 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "unshield amount must be > 0")

        extra_data = t.get("extra_data")
        if extra_data is not None:
            if len(extra_data) > EXTRA_DATA_LIMIT_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
            total_extra += len(extra_data)

    if total_extra > EXTRA_DATA_LIMIT_SUM_SIZE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "total extra_data too large")


def _apply_unshield_transfers(state: ChainState, tx: Transaction) -> ChainState:
    ns = deepcopy(state)
    p = tx.payload
    transfers = p.get("transfers", [])

    for t in transfers:
        amount = t.get("amount", 0)
        dest = t.get("destination")
        receiver = ns.accounts.get(dest)
        if receiver is None:
            receiver = AccountState(address=dest, balance=0, nonce=0)
            ns.accounts[dest] = receiver
        if receiver.balance + amount > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "receiver balance overflow")
        receiver.balance += amount

    return ns
