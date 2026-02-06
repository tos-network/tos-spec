"""KYC tx fixtures."""

from __future__ import annotations

import struct
import time

import blake3
import tos_signer

from tos_spec.config import (
    APPROVAL_EXPIRY_SECONDS,
    CHAIN_ID_DEVNET,
    EMERGENCY_SUSPEND_TIMEOUT,
    MAX_COMMITTEE_NAME_LEN,
    MIN_COMMITTEE_MEMBERS,
    VALID_KYC_LEVELS,
)
from tos_spec.test_accounts import (
    ALICE,
    BOB,
    CAROL,
    DAVE,
    EVE,
    FRANK,
    GRACE,
    HEIDI,
    IVAN,
    SEED_MAP,
)
from tos_spec.types import (
    AccountState,
    ChainState,
    Committee,
    CommitteeMember,
    FeeType,
    KycData,
    KycStatus,
    Transaction,
    TransactionType,
    TxVersion,
)

_CURRENT_TIME = int(time.time())


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig(byte: int) -> bytes:
    return bytes([byte]) + b"\x00" * 31 + bytes([byte]) + b"\x00" * 31


def _base_state() -> ChainState:
    sender = ALICE
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    return state


# --- Domain-separated approval message builders (match Rust exactly) ---


def _build_set_kyc_msg(
    committee_id: bytes, account: bytes, level: int,
    data_hash: bytes, verified_at: int, timestamp: int,
) -> bytes:
    msg = b"TOS_KYC_SET"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += committee_id
    msg += account
    msg += struct.pack("<H", level)
    msg += data_hash
    msg += struct.pack("<Q", verified_at)
    msg += struct.pack("<Q", timestamp)
    return msg


def _build_revoke_kyc_msg(
    committee_id: bytes, account: bytes, reason_hash: bytes, timestamp: int,
) -> bytes:
    msg = b"TOS_KYC_REVOKE"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += committee_id
    msg += account
    msg += reason_hash
    msg += struct.pack("<Q", timestamp)
    return msg


def _build_emergency_suspend_msg(
    committee_id: bytes, account: bytes, reason_hash: bytes,
    expires_at: int, timestamp: int,
) -> bytes:
    msg = b"TOS_KYC_EMERGENCY"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += committee_id
    msg += account
    msg += reason_hash
    msg += struct.pack("<Q", expires_at)
    msg += struct.pack("<Q", timestamp)
    return msg


def _build_transfer_src_msg(
    source_committee: bytes, dest_committee: bytes, account: bytes,
    current_level: int, new_data_hash: bytes, transferred_at: int,
    timestamp: int,
) -> bytes:
    msg = b"TOS_KYC_TRANSFER_SRC"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += source_committee
    msg += dest_committee
    msg += account
    msg += struct.pack("<H", current_level)
    msg += new_data_hash
    msg += struct.pack("<Q", transferred_at)
    msg += struct.pack("<Q", timestamp)
    return msg


def _build_transfer_dst_msg(
    source_committee: bytes, dest_committee: bytes, account: bytes,
    current_level: int, new_data_hash: bytes, transferred_at: int,
    timestamp: int,
) -> bytes:
    msg = b"TOS_KYC_TRANSFER_DST"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += source_committee
    msg += dest_committee
    msg += account
    msg += struct.pack("<H", current_level)
    msg += new_data_hash
    msg += struct.pack("<Q", transferred_at)
    msg += struct.pack("<Q", timestamp)
    return msg


def _build_register_committee_msg(
    parent_id: bytes, name: str, region: int, config_hash: bytes,
    timestamp: int,
) -> bytes:
    msg = b"TOS_COMMITTEE_REG"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += parent_id
    msg += name.encode("utf-8")
    msg += bytes([region])
    msg += config_hash
    msg += struct.pack("<Q", timestamp)
    return msg


def _build_update_committee_msg(
    committee_id: bytes, update_type: int, update_data_hash: bytes,
    timestamp: int,
) -> bytes:
    msg = b"TOS_COMMITTEE_UPD"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += committee_id
    msg += bytes([update_type])
    msg += update_data_hash
    msg += struct.pack("<Q", timestamp)
    return msg


# --- Config hash helpers (match Rust Writer serialization + blake3) ---


def _compute_register_config_hash(
    members: list[tuple[bytes, str | None, int]],
    threshold: int, kyc_threshold: int, max_kyc_level: int,
) -> bytes:
    """Compute blake3 hash of committee config matching Rust compute_register_config_hash."""
    sorted_members = sorted(members, key=lambda m: m[0])
    buf = bytearray()
    buf += struct.pack(">H", len(sorted_members))
    for pubkey, name, role in sorted_members:
        buf += pubkey
        if name is not None:
            buf += b"\x01"
            name_bytes = name.encode("utf-8")
            buf += bytes([len(name_bytes)])
            buf += name_bytes
        else:
            buf += b"\x00"
        buf += bytes([role])
    buf += bytes([threshold])
    buf += bytes([kyc_threshold])
    buf += struct.pack(">H", max_kyc_level)
    return blake3.blake3(bytes(buf)).digest()


def _compute_add_member_data_hash(pubkey: bytes, name: str | None, role: int) -> bytes:
    """Compute blake3 hash of AddMember update data matching Rust serialization."""
    buf = bytearray()
    buf += bytes([0])  # CommitteeUpdateType::AddMember = 0
    buf += pubkey  # CompressedPublicKey (32 bytes)
    if name is not None:
        buf += b"\x01"
        name_bytes = name.encode("utf-8")
        buf += bytes([len(name_bytes)])
        buf += name_bytes
    else:
        buf += b"\x00"
    buf += bytes([role])
    return blake3.blake3(bytes(buf)).digest()


# --- Signed approval helper ---


def _sign_approval(signer: bytes, message: bytes, timestamp: int) -> dict:
    """Create a cryptographically signed approval using a real test account key."""
    seed = SEED_MAP[signer]
    sig = bytes(tos_signer.sign_data(message, seed))
    return {
        "member_pubkey": signer,
        "signature": sig,
        "timestamp": timestamp,
    }


# --- Committee definitions using real test account keys ---


def _global_committee() -> Committee:
    """Global committee using CAROL, DAVE, FRANK as members."""
    return Committee(
        id=_hash(50),
        name="GlobalCommittee",
        region=255,  # KycRegion::Global
        members=[
            CommitteeMember(public_key=CAROL, name="member_0", role=0),
            CommitteeMember(public_key=DAVE, name="member_1", role=0),
            CommitteeMember(public_key=FRANK, name="member_2", role=0),
        ],
        threshold=2,
        kyc_threshold=2,
        max_kyc_level=VALID_KYC_LEVELS[4],
    )


def _regional_committee() -> Committee:
    """Regional committee using GRACE, HEIDI, IVAN as members."""
    return Committee(
        id=_hash(51),
        name="RegionalCommittee",
        region=1,  # KycRegion::AsiaPacific
        members=[
            CommitteeMember(public_key=GRACE, name="rmember_0", role=0),
            CommitteeMember(public_key=HEIDI, name="rmember_1", role=0),
            CommitteeMember(public_key=IVAN, name="rmember_2", role=0),
        ],
        threshold=2,
        kyc_threshold=2,
        max_kyc_level=VALID_KYC_LEVELS[3],
        parent_id=_hash(50),  # child of global committee
    )


def _mk_kyc_tx(
    sender: bytes, nonce: int, tx_type: TransactionType, payload: dict, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=tx_type,
        payload=payload,
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- bootstrap_committee specs ---


def test_bootstrap_committee_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "GlobalCommittee",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_success",
        state,
        tx,
    )


# --- register_committee specs ---


def test_register_committee_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    new_threshold = 2
    new_kyc_threshold = 2
    new_max_level = VALID_KYC_LEVELS[3]

    config_hash = _compute_register_config_hash(
        new_members, new_threshold, new_kyc_threshold, new_max_level,
    )

    ts = _CURRENT_TIME
    msg = _build_register_committee_msg(
        _hash(50), "RegionalCommittee", 1, config_hash, ts,
    )
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    members_payload = [
        {"public_key": pk, "name": name, "role": role}
        for pk, name, role in new_members
    ]
    payload = {
        "name": "RegionalCommittee",
        "region": 1,
        "members": members_payload,
        "threshold": new_threshold,
        "kyc_threshold": new_kyc_threshold,
        "max_kyc_level": new_max_level,
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_success",
        state,
        tx,
    )


# --- update_committee specs ---


def test_update_committee_add_member(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()

    new_member_pubkey = BOB
    new_member_name = "new_member"
    # Use Observer role (3) — adding an approver (Chair=0) would require
    # threshold >= ceil(2/3 * 4) = 3, but current threshold is 2.
    new_member_role = 3  # Observer

    update_data_hash = _compute_add_member_data_hash(
        new_member_pubkey, new_member_name, new_member_role,
    )

    ts = _CURRENT_TIME
    update_type = 0  # AddMember
    msg = _build_update_committee_msg(_hash(50), update_type, update_data_hash, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "add_member",
            "public_key": new_member_pubkey,
            "name": new_member_name,
            "role": new_member_role,
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_add_member",
        state,
        tx,
    )


# --- set_kyc specs ---


def test_set_kyc_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()

    level = VALID_KYC_LEVELS[1]
    verified_at = _CURRENT_TIME
    committee_id = _hash(50)
    data_hash = _hash(40)
    ts = _CURRENT_TIME

    msg = _build_set_kyc_msg(committee_id, target, level, data_hash, verified_at, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "account": target,
        "level": level,
        "verified_at": verified_at,
        "data_hash": data_hash,
        "committee_id": committee_id,
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_success", state, tx
    )


def test_set_kyc_invalid_level(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    payload = {
        "account": target,
        "level": 999,
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(4),
                "timestamp": _CURRENT_TIME,
            }
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_invalid_level", state, tx
    )


# --- revoke_kyc specs ---


def test_revoke_kyc_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    committee_id = _hash(50)
    reason_hash = _hash(41)
    ts = _CURRENT_TIME

    msg = _build_revoke_kyc_msg(committee_id, target, reason_hash, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "account": target,
        "reason_hash": reason_hash,
        "committee_id": committee_id,
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REVOKE_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/revoke_kyc.json", "revoke_kyc_success", state, tx
    )


# --- transfer_kyc specs ---


def test_transfer_kyc_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()

    current_level = VALID_KYC_LEVELS[1]
    state.kyc_data[target] = KycData(
        level=current_level,
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    source_committee = _hash(50)
    dest_committee = _hash(51)
    new_data_hash = _hash(42)
    transferred_at = _CURRENT_TIME
    ts = _CURRENT_TIME

    src_msg = _build_transfer_src_msg(
        source_committee, dest_committee, target, current_level,
        new_data_hash, transferred_at, ts,
    )
    source_approvals = [
        _sign_approval(CAROL, src_msg, ts),
        _sign_approval(DAVE, src_msg, ts),
    ]

    dst_msg = _build_transfer_dst_msg(
        source_committee, dest_committee, target, current_level,
        new_data_hash, transferred_at, ts,
    )
    dest_approvals = [
        _sign_approval(GRACE, dst_msg, ts),
        _sign_approval(HEIDI, dst_msg, ts),
    ]

    payload = {
        "account": target,
        "source_committee_id": source_committee,
        "source_approvals": source_approvals,
        "dest_committee_id": dest_committee,
        "dest_approvals": dest_approvals,
        "new_data_hash": new_data_hash,
        "transferred_at": transferred_at,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_success", state, tx
    )


# --- appeal_kyc specs ---


def test_appeal_kyc_success(state_test_group) -> None:
    state = _base_state()
    # The sender MUST be the account whose KYC is being appealed
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    # KYC was originally verified by the regional committee
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.REVOKED,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(51),
    )
    # Appeal goes from regional (original) to global (parent)
    payload = {
        "account": target,
        "original_committee_id": _hash(51),
        "parent_committee_id": _hash(50),
        "reason_hash": _hash(43),
        "documents_hash": _hash(44),
        "submitted_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(target, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_success", state, tx
    )


# --- emergency_suspend specs ---


def test_emergency_suspend_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    committee_id = _hash(50)
    reason_hash = _hash(45)
    expires_at = _CURRENT_TIME + EMERGENCY_SUSPEND_TIMEOUT
    ts = _CURRENT_TIME

    msg = _build_emergency_suspend_msg(
        committee_id, target, reason_hash, expires_at, ts,
    )
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "account": target,
        "reason_hash": reason_hash,
        "committee_id": committee_id,
        "approvals": approvals,
        "expires_at": expires_at,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.EMERGENCY_SUSPEND, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/emergency_suspend.json",
        "emergency_suspend_success",
        state,
        tx,
    )
