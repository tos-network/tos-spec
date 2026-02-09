"""TNS transaction specs (RegisterName)."""

from __future__ import annotations

import re
from copy import deepcopy

from ..config import (
    MAX_NAME_LENGTH,
    MIN_NAME_LENGTH,
    PHISHING_KEYWORDS,
    REGISTRATION_FEE,
    RESERVED_NAMES,
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


def verify(state: ChainState, tx: Transaction) -> None:
    if tx.tx_type == TransactionType.REGISTER_NAME:
        _verify_register_name(state, tx)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported tns tx type: {tx.tx_type}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    if tx.tx_type == TransactionType.REGISTER_NAME:
        return _apply_register_name(state, tx)
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
