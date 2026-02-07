"""TNS transaction specs (RegisterName, EphemeralMessage)."""

from __future__ import annotations

import re
from copy import deepcopy

from ..config import MAX_ENCRYPTED_SIZE, MAX_NAME_LENGTH, MAX_TTL, MIN_NAME_LENGTH, MIN_TTL
from ..errors import ErrorCode, SpecError
from ..types import ChainState, TnsRecord, Transaction, TransactionType

_VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9._-]*$")
_CONSECUTIVE_SEPARATORS_RE = re.compile(r"[._-]{2}")


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
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"ttl must be {MIN_TTL}-{MAX_TTL}")

    content = p.get("encrypted_content", b"")
    if isinstance(content, (list, tuple)):
        content = bytes(content)
    if not content:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "message content empty")
    if len(content) > MAX_ENCRYPTED_SIZE:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"message too large (max {MAX_ENCRYPTED_SIZE})")


def _apply_ephemeral_message(state: ChainState, tx: Transaction) -> ChainState:
    return deepcopy(state)
