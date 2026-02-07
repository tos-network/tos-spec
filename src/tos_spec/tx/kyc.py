"""KYC and committee transaction specs."""

from __future__ import annotations

import time
from copy import deepcopy

from blake3 import blake3

from ..config import (
    APPROVAL_EXPIRY_SECONDS,
    APPROVAL_FUTURE_TOLERANCE_SECONDS,
    CHAIN_ID_DEVNET,
    EMERGENCY_SUSPEND_MIN_APPROVALS,
    EMERGENCY_SUSPEND_TIMEOUT,
    MAX_APPROVALS,
    MAX_COMMITTEE_MEMBERS,
    MAX_COMMITTEE_NAME_LEN,
    MAX_MEMBER_NAME_LEN,
    MIN_COMMITTEE_MEMBERS,
    VALID_KYC_LEVELS,
)
from ..errors import ErrorCode, SpecError
from ..types import (
    ChainState,
    Committee,
    CommitteeMember,
    KycData,
    KycStatus,
    Transaction,
    TransactionType,
)

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


def verify(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "kyc payload must be dict")

    tt = tx.tx_type
    if tt == TransactionType.SET_KYC:
        _verify_set_kyc(state, tx, p)
    elif tt == TransactionType.REVOKE_KYC:
        _verify_revoke_kyc(state, tx, p)
    elif tt == TransactionType.RENEW_KYC:
        _verify_renew_kyc(state, tx, p)
    elif tt == TransactionType.TRANSFER_KYC:
        _verify_transfer_kyc(state, tx, p)
    elif tt == TransactionType.APPEAL_KYC:
        _verify_appeal_kyc(state, tx, p)
    elif tt == TransactionType.BOOTSTRAP_COMMITTEE:
        _verify_bootstrap_committee(state, tx, p)
    elif tt == TransactionType.REGISTER_COMMITTEE:
        _verify_register_committee(state, tx, p)
    elif tt == TransactionType.UPDATE_COMMITTEE:
        _verify_update_committee(state, tx, p)
    elif tt == TransactionType.EMERGENCY_SUSPEND:
        _verify_emergency_suspend(state, tx, p)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported kyc tx type: {tx.tx_type}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    p = tx.payload
    tt = tx.tx_type
    if tt == TransactionType.SET_KYC:
        return _apply_set_kyc(state, tx, p)
    elif tt == TransactionType.REVOKE_KYC:
        return _apply_revoke_kyc(state, tx, p)
    elif tt == TransactionType.RENEW_KYC:
        return _apply_renew_kyc(state, tx, p)
    elif tt == TransactionType.TRANSFER_KYC:
        return _apply_transfer_kyc(state, tx, p)
    elif tt == TransactionType.APPEAL_KYC:
        return _apply_appeal_kyc(state, tx, p)
    elif tt == TransactionType.BOOTSTRAP_COMMITTEE:
        return _apply_bootstrap_committee(state, tx, p)
    elif tt == TransactionType.REGISTER_COMMITTEE:
        return _apply_register_committee(state, tx, p)
    elif tt == TransactionType.UPDATE_COMMITTEE:
        return _apply_update_committee(state, tx, p)
    elif tt == TransactionType.EMERGENCY_SUSPEND:
        return _apply_emergency_suspend(state, tx, p)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported kyc tx type: {tx.tx_type}")


# --- helpers ---

def _to_bytes(v: object) -> bytes:
    if isinstance(v, bytes):
        return v
    if isinstance(v, (list, tuple)):
        return bytes(v)
    return bytes(32)


def _level_to_tier(level: int) -> int:
    """Convert KYC level bitmask to tier number (0-8)."""
    _tier_map = {0: 0, 7: 1, 31: 2, 63: 3, 255: 4, 2047: 5, 8191: 6, 16383: 7, 32767: 8}
    return _tier_map.get(level, 0)


def _validate_approvals(approvals: list) -> None:
    if len(approvals) > MAX_APPROVALS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"too many approvals (max {MAX_APPROVALS})")
    seen: set[bytes] = set()
    for a in approvals:
        pk = _to_bytes(a.get("member_pubkey"))
        if pk in seen:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "duplicate approver")
        seen.add(pk)


def _committee_id(name: str, members: list[dict]) -> bytes:
    buf = bytearray()
    buf += name.encode("utf-8")
    for m in members:
        buf += _to_bytes(m.get("public_key"))
    return blake3(buf).digest()


def _bootstrap_address_for_chain(chain_id: int) -> bytes | None:
    """Return the bootstrap address (public key) for the given chain.

    On devnet the bootstrap address is MINER (seed 1).
    Returns None for unknown chains (skip authorization check).
    """
    try:
        import tos_signer
    except ImportError:
        return None
    if chain_id == CHAIN_ID_DEVNET:
        return bytes(tos_signer.get_public_key(1))
    return None


# --- SET_KYC ---

def _verify_set_kyc(state: ChainState, tx: Transaction, p: dict) -> None:
    level = p.get("level", -1)
    if level not in VALID_KYC_LEVELS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"invalid KYC level: {level}")

    approvals = p.get("approvals", [])
    if not approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
    _validate_approvals(approvals)

    data_hash = _to_bytes(p.get("data_hash"))
    if data_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "data_hash must not be zero")

    # Committee max_kyc_level check
    committee_id = _to_bytes(p.get("committee_id"))
    committee = state.committees.get(committee_id)
    if committee is not None and level > committee.max_kyc_level:
        raise SpecError(
            ErrorCode.INVALID_PAYLOAD,
            f"level {level} exceeds committee max_kyc_level {committee.max_kyc_level}",
        )

    # Compute required threshold from committee
    tier = _level_to_tier(level)
    kyc_threshold = committee.kyc_threshold if committee is not None else 1
    required = kyc_threshold + 1 if tier >= 5 else kyc_threshold
    if len(approvals) < required:
        raise SpecError(
            ErrorCode.INVALID_PAYLOAD,
            f"tier {tier} requires at least {required} approvals",
        )


def _apply_set_kyc(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    account = _to_bytes(p.get("account"))
    ns.kyc_data[account] = KycData(
        level=p.get("level", 0),
        status=KycStatus.ACTIVE,
        verified_at=p.get("verified_at", 0),
        data_hash=_to_bytes(p.get("data_hash")),
    )
    return ns


# --- REVOKE_KYC ---

def _verify_revoke_kyc(state: ChainState, tx: Transaction, p: dict) -> None:
    approvals = p.get("approvals", [])
    if not approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
    _validate_approvals(approvals)

    reason_hash = _to_bytes(p.get("reason_hash"))
    if reason_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash must not be zero")

    # State check: KYC record must exist
    account = _to_bytes(p.get("account"))
    if account not in state.kyc_data:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "kyc record not found")


def _apply_revoke_kyc(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    account = _to_bytes(p.get("account"))
    existing = ns.kyc_data.get(account)
    if existing is not None:
        existing.status = KycStatus.REVOKED
    else:
        ns.kyc_data[account] = KycData(level=0, status=KycStatus.REVOKED)
    return ns


# --- RENEW_KYC ---

def _verify_renew_kyc(state: ChainState, tx: Transaction, p: dict) -> None:
    approvals = p.get("approvals", [])
    if not approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
    _validate_approvals(approvals)

    data_hash = _to_bytes(p.get("data_hash"))
    if data_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "data_hash must not be zero")

    # State check: KYC record must exist for renewal
    account = _to_bytes(p.get("account"))
    if account not in state.kyc_data:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "kyc record not found")


def _apply_renew_kyc(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    account = _to_bytes(p.get("account"))
    existing = ns.kyc_data.get(account)
    if existing is not None:
        existing.status = KycStatus.ACTIVE
        existing.verified_at = p.get("verified_at", 0)
        existing.data_hash = _to_bytes(p.get("data_hash"))
    return ns


# --- TRANSFER_KYC ---

def _verify_transfer_kyc(state: ChainState, tx: Transaction, p: dict) -> None:
    src_id = _to_bytes(p.get("source_committee_id"))
    dst_id = _to_bytes(p.get("dest_committee_id"))
    if src_id == dst_id:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "source and dest committee must differ")

    src_approvals = p.get("source_approvals", [])
    dst_approvals = p.get("dest_approvals", [])

    # Combined approval count must not exceed 2 * MAX_APPROVALS
    combined_count = len(src_approvals) + len(dst_approvals)
    if combined_count > MAX_APPROVALS * 2:
        raise SpecError(
            ErrorCode.INVALID_PAYLOAD,
            f"combined approval count {combined_count} exceeds max {MAX_APPROVALS * 2}",
        )

    if not src_approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "source_approvals required")
    if not dst_approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "dest_approvals required")
    _validate_approvals(src_approvals + dst_approvals)

    new_data_hash = _to_bytes(p.get("new_data_hash"))
    if new_data_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "new_data_hash must not be zero")

    # Cross-committee duplicate check: same member cannot approve for both
    src_pks = {_to_bytes(a.get("member_pubkey")) for a in src_approvals}
    for a in dst_approvals:
        pk = _to_bytes(a.get("member_pubkey"))
        if pk in src_pks:
            raise SpecError(
                ErrorCode.INVALID_PAYLOAD,
                "same member cannot approve for both source and dest",
            )

    # State check: KYC record must exist for transfer
    account = _to_bytes(p.get("account"))
    if account not in state.kyc_data:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "kyc record not found")


def _apply_transfer_kyc(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    account = _to_bytes(p.get("account"))
    existing = ns.kyc_data.get(account)
    if existing is not None:
        existing.data_hash = _to_bytes(p.get("new_data_hash"))
        existing.verified_at = p.get("transferred_at", 0)
    return ns


# --- APPEAL_KYC ---

def _verify_appeal_kyc(state: ChainState, tx: Transaction, p: dict) -> None:
    orig = _to_bytes(p.get("original_committee_id"))
    parent = _to_bytes(p.get("parent_committee_id"))
    if orig == parent:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "original and parent committee must differ")

    reason_hash = _to_bytes(p.get("reason_hash"))
    if reason_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash must not be zero")

    docs_hash = _to_bytes(p.get("documents_hash"))
    if docs_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "documents_hash must not be zero")

    # submitted_at must be within 1-hour window of current time
    submitted_at = p.get("submitted_at", 0)
    now = int(time.time())
    if submitted_at > now + APPROVAL_FUTURE_TOLERANCE_SECONDS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "submitted_at too far in the future")
    if submitted_at < now - APPROVAL_FUTURE_TOLERANCE_SECONDS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "submitted_at too far in the past")

    # State check: KYC record must exist
    account = _to_bytes(p.get("account"))
    kyc = state.kyc_data.get(account)
    if kyc is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "kyc record not found")

    # State check: KYC status must be REVOKED or SUSPENDED to appeal
    if kyc.status not in (KycStatus.REVOKED, KycStatus.SUSPENDED):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "can only appeal revoked or suspended KYC")


def _apply_appeal_kyc(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    return deepcopy(state)


# --- BOOTSTRAP_COMMITTEE ---

def _verify_bootstrap_committee(state: ChainState, tx: Transaction, p: dict) -> None:
    # Authorization: only the bootstrap address can create the global committee
    bootstrap_addr = _bootstrap_address_for_chain(state.network_chain_id)
    if bootstrap_addr is not None and tx.source != bootstrap_addr:
        raise SpecError(ErrorCode.UNAUTHORIZED, "only bootstrap address can create global committee")

    # State check: cannot bootstrap if a committee already exists
    if state.committees:
        raise SpecError(ErrorCode.ACCOUNT_EXISTS, "global committee already bootstrapped")

    name = p.get("name", "")
    if not name or len(name) > MAX_COMMITTEE_NAME_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid committee name length")

    members = p.get("members", [])
    if len(members) < MIN_COMMITTEE_MEMBERS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"need at least {MIN_COMMITTEE_MEMBERS} members")
    if len(members) > MAX_COMMITTEE_MEMBERS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"max {MAX_COMMITTEE_MEMBERS} members")

    seen: set[bytes] = set()
    for m in members:
        mn = m.get("name", "")
        if len(mn) > MAX_MEMBER_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name too long")
        pk = _to_bytes(m.get("public_key"))
        if pk in seen:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "duplicate member public key")
        seen.add(pk)

    threshold = p.get("threshold", 0)
    kyc_threshold = p.get("kyc_threshold", 0)
    approver_count = len(members)

    if threshold <= 0 or threshold > approver_count:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid threshold")
    if threshold > MAX_APPROVALS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "threshold exceeds max approvals")
    if kyc_threshold <= 0 or kyc_threshold > approver_count:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid kyc_threshold")
    if kyc_threshold > MAX_APPROVALS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "kyc_threshold exceeds max approvals")

    max_kyc_level = p.get("max_kyc_level", -1)
    if max_kyc_level not in VALID_KYC_LEVELS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid max_kyc_level")


def _apply_bootstrap_committee(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    name = p.get("name", "")
    members_raw = p.get("members", [])

    cid = _committee_id(name, members_raw)
    members = [
        CommitteeMember(
            public_key=_to_bytes(m.get("public_key")),
            name=m.get("name", ""),
            role=m.get("role", 0),
        )
        for m in members_raw
    ]
    ns.committees[cid] = Committee(
        id=cid,
        name=name,
        members=members,
        threshold=p.get("threshold", 0),
        kyc_threshold=p.get("kyc_threshold", 0),
        max_kyc_level=p.get("max_kyc_level", 0),
    )
    return ns


# --- REGISTER_COMMITTEE ---

def _verify_register_committee(state: ChainState, tx: Transaction, p: dict) -> None:
    approvals = p.get("approvals", [])
    if not approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
    _validate_approvals(approvals)

    name = p.get("name", "")
    if not name or len(name) > MAX_COMMITTEE_NAME_LEN:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid committee name length")

    members = p.get("members", [])
    if len(members) < MIN_COMMITTEE_MEMBERS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"need at least {MIN_COMMITTEE_MEMBERS} members")
    if len(members) > MAX_COMMITTEE_MEMBERS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"max {MAX_COMMITTEE_MEMBERS} members")

    seen: set[bytes] = set()
    for m in members:
        mn = m.get("name", "")
        if len(mn) > MAX_MEMBER_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name too long")
        pk = _to_bytes(m.get("public_key"))
        if pk in seen:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "duplicate member public key")
        seen.add(pk)

    threshold = p.get("threshold", 0)
    kyc_threshold = p.get("kyc_threshold", 0)
    approver_count = len(members)

    if threshold <= 0 or threshold > approver_count:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid threshold")
    if threshold > MAX_APPROVALS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "threshold exceeds max approvals")
    if kyc_threshold <= 0 or kyc_threshold > approver_count:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid kyc_threshold")
    if kyc_threshold > MAX_APPROVALS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "kyc_threshold exceeds max approvals")

    max_kyc_level = p.get("max_kyc_level", -1)
    if max_kyc_level not in VALID_KYC_LEVELS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid max_kyc_level")


def _apply_register_committee(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    name = p.get("name", "")
    members_raw = p.get("members", [])

    cid = _committee_id(name, members_raw)
    members = [
        CommitteeMember(
            public_key=_to_bytes(m.get("public_key")),
            name=m.get("name", ""),
            role=m.get("role", 0),
        )
        for m in members_raw
    ]
    ns.committees[cid] = Committee(
        id=cid,
        name=name,
        members=members,
        threshold=p.get("threshold", 0),
        kyc_threshold=p.get("kyc_threshold", 0),
        max_kyc_level=p.get("max_kyc_level", 0),
    )
    return ns


# --- UPDATE_COMMITTEE ---

def _verify_update_committee(state: ChainState, tx: Transaction, p: dict) -> None:
    approvals = p.get("approvals", [])
    if not approvals:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
    _validate_approvals(approvals)

    # State check: committee must exist
    committee_id = _to_bytes(p.get("committee_id"))
    if committee_id not in state.committees:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "committee not found")

    update = p.get("update", {})
    if not isinstance(update, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "update must be dict")

    update_type = update.get("type", "")
    if update_type == "add_member":
        mn = update.get("name", "")
        if mn and len(mn) > MAX_MEMBER_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name too long")
    elif update_type == "update_threshold":
        new_threshold = update.get("new_threshold", 0)
        if new_threshold <= 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "threshold must be > 0")
    elif update_type == "update_kyc_threshold":
        new_kyc_threshold = update.get("new_kyc_threshold", 0)
        if new_kyc_threshold <= 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "kyc_threshold must be > 0")
    elif update_type == "update_name":
        new_name = update.get("new_name", "")
        if not new_name or len(new_name) > MAX_COMMITTEE_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid committee name length")


def _apply_update_committee(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    committee_id = _to_bytes(p.get("committee_id"))
    committee = ns.committees.get(committee_id)
    if committee is None:
        return ns

    update = p.get("update", {})
    update_type = update.get("type", "")

    if update_type == "add_member":
        committee.members.append(CommitteeMember(
            public_key=_to_bytes(update.get("public_key")),
            name=update.get("name", ""),
            role=update.get("role", 0),
        ))
    elif update_type == "remove_member":
        pk = _to_bytes(update.get("member_pubkey"))
        committee.members = [m for m in committee.members if m.public_key != pk]
    elif update_type == "update_threshold":
        committee.threshold = update.get("new_threshold", committee.threshold)
    elif update_type == "update_kyc_threshold":
        committee.kyc_threshold = update.get("new_kyc_threshold", committee.kyc_threshold)
    elif update_type == "update_name":
        committee.name = update.get("new_name", committee.name)

    return ns


# --- EMERGENCY_SUSPEND ---

def _verify_emergency_suspend(state: ChainState, tx: Transaction, p: dict) -> None:
    approvals = p.get("approvals", [])
    if len(approvals) < EMERGENCY_SUSPEND_MIN_APPROVALS:
        raise SpecError(
            ErrorCode.INVALID_PAYLOAD,
            f"need at least {EMERGENCY_SUSPEND_MIN_APPROVALS} approvals",
        )
    _validate_approvals(approvals)

    reason_hash = _to_bytes(p.get("reason_hash"))
    if reason_hash == bytes(32):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash must not be zero")

    # State check: target account KYC record must exist
    account = _to_bytes(p.get("account"))
    if account not in state.kyc_data:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "kyc record not found")


def _apply_emergency_suspend(state: ChainState, tx: Transaction, p: dict) -> ChainState:
    ns = deepcopy(state)
    account = _to_bytes(p.get("account"))
    existing = ns.kyc_data.get(account)
    if existing is not None:
        existing.status = KycStatus.SUSPENDED
    else:
        ns.kyc_data[account] = KycData(level=0, status=KycStatus.SUSPENDED)
    return ns
