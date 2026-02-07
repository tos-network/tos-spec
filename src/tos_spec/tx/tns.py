"""TNS transaction specs (RegisterName, EphemeralMessage)."""

from __future__ import annotations

import re
from copy import deepcopy

from ..config import (
    BASE_MESSAGE_FEE,
    MAX_ENCRYPTED_SIZE,
    MAX_NAME_LENGTH,
    MAX_TTL,
    MIN_NAME_LENGTH,
    MIN_TTL,
    PHISHING_KEYWORDS,
    REGISTRATION_FEE,
    RESERVED_NAMES,
    TTL_ONE_DAY,
)
from ..errors import ErrorCode, SpecError
from ..types import ChainState, TnsRecord, Transaction, TransactionType

_VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
_CONSECUTIVE_SEPARATORS_RE = re.compile(r"[._-]{2}")


def _is_confusing_name(name: str) -> bool:
    """Check if a name is potentially confusing (phishing risk).

    Mirrors Rust's is_confusing_name logic:
    1. Looks like an address prefix (tos1, tst1, 0x)
    2. Pure numeric (easily confused with ID)
    3. Contains phishing keywords
    """
    if name.startswith("tos1") or name.startswith("tst1") or name.startswith("0x"):
        return True
    if name.isdigit():
        return True
    for keyword in PHISHING_KEYWORDS:
        if keyword in name:
            return True
    return False


def _calculate_message_fee(ttl_blocks: int) -> int:
    """Calculate the fee for an ephemeral message based on TTL.

    Mirrors Rust's calculate_message_fee logic:
    - TTL <= 100 blocks: 1x base fee
    - TTL <= 28,800 blocks: 2x base fee
    - TTL > 28,800 blocks: 3x base fee
    """
    if ttl_blocks <= MIN_TTL:
        return BASE_MESSAGE_FEE
    elif ttl_blocks <= TTL_ONE_DAY:
        return BASE_MESSAGE_FEE * 2
    else:
        return BASE_MESSAGE_FEE * 3


def verify(state: ChainState, tx: Transaction) -> None:
    if tx.tx_type == TransactionType.REGISTER_NAME:
        _verify_register_name(state, tx)
    elif tx.tx_type == TransactionType.EPHEMERAL_MESSAGE:
        _verify_ephemeral_message(state, tx)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported tns tx type: {tx.tx_type}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    if tx.tx_type == TransactionType.REGISTER_NAME:
        return _apply_register_name(state, tx)
    elif tx.tx_type == TransactionType.EPHEMERAL_MESSAGE:
        return _apply_ephemeral_message(state, tx)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported tns tx type: {tx.tx_type}")


def _verify_register_name(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "register_name payload must be dict")

    name = p.get("name", "")
    if not isinstance(name, str):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "name must be string")

    if len(name) < MIN_NAME_LENGTH:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"name too short (min {MIN_NAME_LENGTH})")

    if len(name) > MAX_NAME_LENGTH:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"name too long (max {MAX_NAME_LENGTH})")

    normalized = name.lower()

    if not normalized[0].isalpha():
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "name must start with a letter")

    if normalized[-1] in (".", "-", "_"):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "name cannot end with separator")

    if not _VALID_NAME_RE.match(normalized):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "name contains invalid characters")

    if _CONSECUTIVE_SEPARATORS_RE.search(normalized):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "name has consecutive separators")

    # Reserved name check (matches Rust is_reserved_name)
    if normalized in RESERVED_NAMES:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"reserved name: {normalized}")

    # Confusing name check (matches Rust is_confusing_name)
    if _is_confusing_name(normalized):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"confusing name: {normalized}")

    # Fee check: minimum registration fee required
    if tx.fee < REGISTRATION_FEE:
        raise SpecError(
            ErrorCode.INSUFFICIENT_FEE,
            f"registration fee too low (required {REGISTRATION_FEE}, got {tx.fee})",
        )

    if normalized in state.tns_names:
        raise SpecError(ErrorCode.DOMAIN_EXISTS, "name already registered")

    if tx.source in state.tns_by_owner:
        raise SpecError(ErrorCode.DOMAIN_EXISTS, "account already has a name")


def _apply_register_name(state: ChainState, tx: Transaction) -> ChainState:
    next_state = deepcopy(state)
    p = tx.payload
    name = p.get("name", "").lower()
    height = next_state.global_state.block_height

    next_state.tns_names[name] = TnsRecord(
        name=name, owner=tx.source, registered_at=height
    )
    next_state.tns_by_owner[tx.source] = name

    return next_state


def _verify_ephemeral_message(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "ephemeral_message payload must be dict")

    sender_name_hash = p.get("sender_name_hash")
    recipient_name_hash = p.get("recipient_name_hash")

    if sender_name_hash is None or recipient_name_hash is None:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "name hashes required")

    if sender_name_hash == recipient_name_hash:
        raise SpecError(ErrorCode.SELF_OPERATION, "cannot send message to self")

    ttl = p.get("ttl_blocks", 0)
    if ttl < MIN_TTL or ttl > MAX_TTL:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"ttl must be {MIN_TTL}-{MAX_TTL}")

    content = p.get("encrypted_content", b"")
    if isinstance(content, (list, tuple)):
        content = bytes(content)
    if not content:
        raise SpecError(ErrorCode.INVALID_FORMAT, "message content empty")
    if len(content) > MAX_ENCRYPTED_SIZE:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"message too large (max {MAX_ENCRYPTED_SIZE})")

    # Fee check: minimum message fee based on TTL tier
    required_fee = _calculate_message_fee(ttl)
    if tx.fee < required_fee:
        raise SpecError(
            ErrorCode.INSUFFICIENT_FEE,
            f"message fee too low (required {required_fee}, got {tx.fee})",
        )


def _apply_ephemeral_message(state: ChainState, tx: Transaction) -> ChainState:
    return deepcopy(state)
