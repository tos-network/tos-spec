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
    MAX_APPROVALS,
    MAX_COMMITTEE_MEMBERS,
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
    MINER,
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
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER  # Devnet bootstrap address holder (seed 1)
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
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


# --- renew_kyc specs ---


def _build_renew_kyc_msg(
    committee_id: bytes, account: bytes, data_hash: bytes,
    verified_at: int, timestamp: int,
) -> bytes:
    msg = b"TOS_KYC_RENEW"
    msg += struct.pack("<Q", CHAIN_ID_DEVNET)
    msg += committee_id
    msg += account
    msg += data_hash
    msg += struct.pack("<Q", verified_at)
    msg += struct.pack("<Q", timestamp)
    return msg


def test_renew_kyc_success(state_test_group) -> None:
    """Valid renewal with data_hash and approvals."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 10000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    committee_id = _hash(50)
    new_data_hash = _hash(41)
    verified_at = _CURRENT_TIME
    ts = _CURRENT_TIME

    msg = _build_renew_kyc_msg(committee_id, target, new_data_hash, verified_at, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "account": target,
        "data_hash": new_data_hash,
        "verified_at": verified_at,
        "committee_id": committee_id,
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.RENEW_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/renew_kyc.json", "renew_kyc_success", state, tx
    )


def test_renew_kyc_no_kyc_record(state_test_group) -> None:
    """Renew KYC for address with no existing KYC record."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    # No kyc_data entry for target

    committee_id = _hash(50)
    new_data_hash = _hash(41)
    verified_at = _CURRENT_TIME
    ts = _CURRENT_TIME

    msg = _build_renew_kyc_msg(committee_id, target, new_data_hash, verified_at, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "account": target,
        "data_hash": new_data_hash,
        "verified_at": verified_at,
        "committee_id": committee_id,
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.RENEW_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/renew_kyc.json", "renew_kyc_no_kyc_record", state, tx
    )


# --- revoke_kyc negative tests ---


def test_revoke_kyc_no_kyc_record(state_test_group) -> None:
    """Revoke KYC for address with no existing KYC record."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    # No kyc_data entry for target

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
        "transactions/kyc/revoke_kyc.json", "revoke_kyc_no_kyc_record", state, tx
    )


def test_revoke_kyc_zero_reason_hash(state_test_group) -> None:
    """Revoke KYC with zero reason_hash should fail."""
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

    payload = {
        "account": target,
        "reason_hash": bytes(32),  # zero hash
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": DAVE, "signature": _sig(5), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REVOKE_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/revoke_kyc.json", "revoke_kyc_zero_reason_hash", state, tx
    )


def test_revoke_kyc_no_approvals(state_test_group) -> None:
    """Revoke KYC with empty approvals should fail."""
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

    payload = {
        "account": target,
        "reason_hash": _hash(41),
        "committee_id": _hash(50),
        "approvals": [],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REVOKE_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/revoke_kyc.json", "revoke_kyc_no_approvals", state, tx
    )


# --- transfer_kyc negative tests ---


def test_transfer_kyc_no_kyc_record(state_test_group) -> None:
    """Transfer KYC for address with no existing KYC record."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    # No kyc_data entry for target

    source_committee = _hash(50)
    dest_committee = _hash(51)
    new_data_hash = _hash(42)
    transferred_at = _CURRENT_TIME
    ts = _CURRENT_TIME

    src_msg = _build_transfer_src_msg(
        source_committee, dest_committee, target, VALID_KYC_LEVELS[1],
        new_data_hash, transferred_at, ts,
    )
    source_approvals = [
        _sign_approval(CAROL, src_msg, ts),
        _sign_approval(DAVE, src_msg, ts),
    ]

    dst_msg = _build_transfer_dst_msg(
        source_committee, dest_committee, target, VALID_KYC_LEVELS[1],
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
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_no_kyc_record", state, tx
    )


def test_transfer_kyc_same_committee(state_test_group) -> None:
    """Transfer KYC where source and dest committee are the same should fail."""
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

    payload = {
        "account": target,
        "source_committee_id": _hash(50),
        "source_approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
        "dest_committee_id": _hash(50),  # same as source
        "dest_approvals": [
            {"member_pubkey": DAVE, "signature": _sig(5), "timestamp": _CURRENT_TIME},
        ],
        "new_data_hash": _hash(42),
        "transferred_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_same_committee", state, tx
    )


def test_transfer_kyc_zero_data_hash(state_test_group) -> None:
    """Transfer KYC with zero new_data_hash should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "source_committee_id": _hash(50),
        "source_approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
        "dest_committee_id": _hash(51),
        "dest_approvals": [
            {"member_pubkey": GRACE, "signature": _sig(8), "timestamp": _CURRENT_TIME},
        ],
        "new_data_hash": bytes(32),  # zero hash
        "transferred_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_zero_data_hash", state, tx
    )


def test_transfer_kyc_no_source_approvals(state_test_group) -> None:
    """Transfer KYC with empty source approvals should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "source_committee_id": _hash(50),
        "source_approvals": [],  # empty
        "dest_committee_id": _hash(51),
        "dest_approvals": [
            {"member_pubkey": GRACE, "signature": _sig(8), "timestamp": _CURRENT_TIME},
        ],
        "new_data_hash": _hash(42),
        "transferred_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_no_source_approvals", state, tx
    )


# --- appeal_kyc negative tests ---


def test_appeal_kyc_no_kyc_record(state_test_group) -> None:
    """Appeal KYC for address with no existing KYC record."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    # No kyc_data entry for target

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
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_no_kyc_record", state, tx
    )


def test_appeal_kyc_not_revoked(state_test_group) -> None:
    """Appeal KYC when status is ACTIVE (not revoked/suspended) should fail."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,  # Not revoked
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(51),
    )

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
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_not_revoked", state, tx
    )


def test_appeal_kyc_same_committee(state_test_group) -> None:
    """Appeal KYC where original and parent committee are the same should fail."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.REVOKED,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "original_committee_id": _hash(50),
        "parent_committee_id": _hash(50),  # same as original
        "reason_hash": _hash(43),
        "documents_hash": _hash(44),
        "submitted_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(target, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_same_committee", state, tx
    )


def test_appeal_kyc_zero_reason_hash(state_test_group) -> None:
    """Appeal KYC with zero reason_hash should fail."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.REVOKED,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(51),
    )

    payload = {
        "account": target,
        "original_committee_id": _hash(51),
        "parent_committee_id": _hash(50),
        "reason_hash": bytes(32),  # zero hash
        "documents_hash": _hash(44),
        "submitted_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(target, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_zero_reason_hash", state, tx
    )


def test_appeal_kyc_zero_documents_hash(state_test_group) -> None:
    """Appeal KYC with zero documents_hash should fail."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.REVOKED,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(51),
    )

    payload = {
        "account": target,
        "original_committee_id": _hash(51),
        "parent_committee_id": _hash(50),
        "reason_hash": _hash(43),
        "documents_hash": bytes(32),  # zero hash
        "submitted_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(target, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_zero_documents_hash", state, tx
    )


# --- set_kyc negative tests ---


def test_set_kyc_zero_data_hash(state_test_group) -> None:
    """Set KYC with zero data_hash should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()

    payload = {
        "account": target,
        "level": VALID_KYC_LEVELS[1],
        "verified_at": _CURRENT_TIME,
        "data_hash": bytes(32),  # zero hash
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": DAVE, "signature": _sig(5), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_zero_data_hash", state, tx
    )


def test_set_kyc_no_approvals(state_test_group) -> None:
    """Set KYC with empty approvals should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()

    payload = {
        "account": target,
        "level": VALID_KYC_LEVELS[1],
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": [],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_no_approvals", state, tx
    )


# --- bootstrap_committee negative tests ---


def test_bootstrap_committee_not_bootstrap_address(state_test_group) -> None:
    """Bootstrap committee from non-bootstrap address should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE  # Not the bootstrap address (MINER on devnet)
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
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
        "bootstrap_committee_not_bootstrap_address",
        state,
        tx,
    )


def test_bootstrap_committee_empty_name(state_test_group) -> None:
    """Bootstrap committee with empty name should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "",  # empty name
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_empty_name",
        state,
        tx,
    )


def test_bootstrap_committee_too_few_members(state_test_group) -> None:
    """Bootstrap committee with fewer members than minimum should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10), "name": "member_0", "role": 0},
        {"public_key": _addr(11), "name": "member_1", "role": 0},
    ]  # Only 2, below MIN_COMMITTEE_MEMBERS=3
    payload = {
        "name": "SmallCommittee",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_too_few_members",
        state,
        tx,
    )


def test_bootstrap_committee_duplicate_member(state_test_group) -> None:
    """Bootstrap committee with duplicate member keys should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10), "name": "member_0", "role": 0},
        {"public_key": _addr(10), "name": "member_1", "role": 0},  # duplicate
        {"public_key": _addr(12), "name": "member_2", "role": 0},
    ]
    payload = {
        "name": "DupCommittee",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_duplicate_member",
        state,
        tx,
    )


def test_bootstrap_committee_invalid_threshold(state_test_group) -> None:
    """Bootstrap committee with threshold=0 should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "ZeroThreshold",
        "members": members,
        "threshold": 0,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_invalid_threshold",
        state,
        tx,
    )


def test_bootstrap_committee_invalid_kyc_level(state_test_group) -> None:
    """Bootstrap committee with invalid max_kyc_level should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "BadLevel",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": 999,  # invalid level
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_invalid_kyc_level",
        state,
        tx,
    )


# --- register_committee negative tests ---


def test_register_committee_no_approvals(state_test_group) -> None:
    """Register committee with no approvals should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    members_payload = [
        {"public_key": pk, "name": name, "role": role}
        for pk, name, role in new_members
    ]
    payload = {
        "name": "RegionalCommittee",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": [],  # empty
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_no_approvals",
        state,
        tx,
    )


def test_register_committee_empty_name(state_test_group) -> None:
    """Register committee with empty name should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "", 1, config_hash, ts,
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
        "name": "",  # empty name
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_empty_name",
        state,
        tx,
    )


def test_register_committee_too_few_members(state_test_group) -> None:
    """Register committee with fewer members than minimum should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    # Only 2 members (below MIN_COMMITTEE_MEMBERS=3)
    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "SmallRegional", 1, config_hash, ts,
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
        "name": "SmallRegional",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_too_few_members",
        state,
        tx,
    )


# --- update_committee negative tests ---


def test_update_committee_no_approvals(state_test_group) -> None:
    """Update committee with no approvals should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "update_name",
            "new_name": "NewName",
        },
        "approvals": [],  # empty
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_no_approvals",
        state,
        tx,
    )


def test_update_committee_not_found(state_test_group) -> None:
    """Update committee that does not exist in state."""
    state = _base_state()
    sender = ALICE
    # No committee in state
    ts = _CURRENT_TIME

    msg = _build_update_committee_msg(_hash(99), 0, _hash(60), ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(99),  # does not exist
        "update": {
            "type": "add_member",
            "public_key": BOB,
            "name": "new_member",
            "role": 3,
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_not_found",
        state,
        tx,
    )


def test_update_committee_threshold_zero(state_test_group) -> None:
    """Update committee threshold to zero should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    msg = _build_update_committee_msg(_hash(50), 2, _hash(60), ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "update_threshold",
            "new_threshold": 0,
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_threshold_zero",
        state,
        tx,
    )


def test_update_committee_empty_name(state_test_group) -> None:
    """Update committee name to empty should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    msg = _build_update_committee_msg(_hash(50), 4, _hash(60), ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "update_name",
            "new_name": "",
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_empty_name",
        state,
        tx,
    )


# --- emergency_suspend negative tests ---


def test_emergency_suspend_no_kyc_record(state_test_group) -> None:
    """Emergency suspend for address with no existing KYC record."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    # No kyc_data entry for target

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
        "emergency_suspend_no_kyc_record",
        state,
        tx,
    )


def test_emergency_suspend_zero_reason_hash(state_test_group) -> None:
    """Emergency suspend with zero reason_hash should fail."""
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

    payload = {
        "account": target,
        "reason_hash": bytes(32),  # zero hash
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": DAVE, "signature": _sig(5), "timestamp": _CURRENT_TIME},
        ],
        "expires_at": _CURRENT_TIME + EMERGENCY_SUSPEND_TIMEOUT,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.EMERGENCY_SUSPEND, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/emergency_suspend.json",
        "emergency_suspend_zero_reason_hash",
        state,
        tx,
    )


def test_emergency_suspend_insufficient_approvals(state_test_group) -> None:
    """Emergency suspend with only 1 approval should fail (needs 2)."""
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
        # Only 1 approval, but EMERGENCY_SUSPEND_MIN_APPROVALS = 2
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
        "emergency_suspend_insufficient_approvals",
        state,
        tx,
    )


# --- boundary value tests ---


def test_bootstrap_committee_max_members(state_test_group) -> None:
    """Bootstrap committee with exactly MAX_COMMITTEE_MEMBERS (21) must succeed."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    # Use valid Ristretto keys (daemon decompresses member public keys)
    members = [
        {"public_key": bytes(tos_signer.get_public_key(10 + i)), "name": f"member_{i}", "role": 0}
        for i in range(MAX_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "MaxMembersCommittee",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_max_members",
        state,
        tx,
    )


def test_bootstrap_committee_too_many_members(state_test_group) -> None:
    """Bootstrap committee with MAX_COMMITTEE_MEMBERS + 1 must fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MAX_COMMITTEE_MEMBERS + 1)
    ]
    payload = {
        "name": "TooManyCommittee",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_too_many_members",
        state,
        tx,
    )


def test_bootstrap_committee_max_name_length(state_test_group) -> None:
    """Bootstrap committee with name exactly at MAX_COMMITTEE_NAME_LEN (128) must succeed."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "A" * MAX_COMMITTEE_NAME_LEN,
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_max_name_length",
        state,
        tx,
    )


def test_bootstrap_committee_name_too_long(state_test_group) -> None:
    """Bootstrap committee with name exceeding MAX_COMMITTEE_NAME_LEN must fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "A" * (MAX_COMMITTEE_NAME_LEN + 1),
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_name_too_long",
        state,
        tx,
    )


def test_emergency_suspend_max_approvals(state_test_group) -> None:
    """Emergency suspend with exactly MAX_APPROVALS (15) must succeed."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)

    # Use valid Ristretto keys for committee members (seed bytes 20..34)
    member_seeds = list(range(20, 20 + MAX_APPROVALS))
    member_keys = [bytes(tos_signer.get_public_key(s)) for s in member_seeds]
    committee_members = [
        CommitteeMember(public_key=member_keys[i], name=f"mem_{i}", role=0)
        for i in range(MAX_APPROVALS)
    ]
    state.committees[_hash(50)] = Committee(
        id=_hash(50),
        name="LargeCommittee",
        members=committee_members,
        threshold=2,
        kyc_threshold=2,
        max_kyc_level=VALID_KYC_LEVELS[4],
    )
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
    # Use real cryptographic signatures from valid Ristretto keys
    approvals = [
        {
            "member_pubkey": member_keys[i],
            "signature": bytes(tos_signer.sign_data(msg, member_seeds[i])),
            "timestamp": ts,
        }
        for i in range(MAX_APPROVALS)
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
        "emergency_suspend_max_approvals",
        state,
        tx,
    )


def test_register_committee_duplicate_member(state_test_group) -> None:
    """Register committee with duplicate public key in members list must fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    # Use duplicate key: GRACE appears twice
    new_members = [
        (GRACE, "rmember_0", 0),
        (GRACE, "rmember_1", 0),  # duplicate
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "DupMemberRegional", 1, config_hash, ts,
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
        "name": "DupMemberRegional",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_duplicate_member",
        state,
        tx,
    )


# --- set_kyc: tier5+ requires 2 approvals ---


def test_set_kyc_tier5_needs_2_approvals(state_test_group) -> None:
    """Set KYC at tier 5 (level 2047) with only 1 approval should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    gc = _global_committee()
    gc.max_kyc_level = VALID_KYC_LEVELS[8]  # 32767 to allow tier 5
    state.committees[_hash(50)] = gc

    level = 2047  # Tier 5
    verified_at = _CURRENT_TIME
    committee_id = _hash(50)
    data_hash = _hash(40)
    ts = _CURRENT_TIME

    msg = _build_set_kyc_msg(committee_id, target, level, data_hash, verified_at, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        # Only 1 approval, but tier 5 requires 2
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
        "transactions/kyc/set_kyc.json", "set_kyc_tier5_needs_2_approvals", state, tx
    )


def test_set_kyc_tier5_with_3_approvals(state_test_group) -> None:
    """Set KYC at tier 5 (level 2047) with 3 approvals should succeed.

    Tier 5+ requires kyc_threshold + 1 approvals (3 for kyc_threshold=2).
    """
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    gc = _global_committee()
    gc.max_kyc_level = VALID_KYC_LEVELS[8]  # 32767 to allow tier 5+
    state.committees[_hash(50)] = gc

    level = 2047  # Tier 5
    verified_at = _CURRENT_TIME
    committee_id = _hash(50)
    data_hash = _hash(40)
    ts = _CURRENT_TIME

    msg = _build_set_kyc_msg(committee_id, target, level, data_hash, verified_at, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
        _sign_approval(FRANK, msg, ts),
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
        "transactions/kyc/set_kyc.json", "set_kyc_tier5_with_3_approvals", state, tx
    )


def test_set_kyc_tier6_needs_3_approvals(state_test_group) -> None:
    """Set KYC at tier 6 (level 8191) with only 1 approval should fail (needs kyc_threshold+1=3)."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    gc = _global_committee()
    gc.max_kyc_level = VALID_KYC_LEVELS[8]  # 32767 to allow tier 6
    state.committees[_hash(50)] = gc

    level = 8191  # Tier 6
    payload = {
        "account": target,
        "level": level,
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_tier6_needs_3_approvals", state, tx
    )


# --- set_kyc: duplicate approvers ---


def test_set_kyc_duplicate_approver(state_test_group) -> None:
    """Set KYC with duplicate approver public key should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()

    payload = {
        "account": target,
        "level": VALID_KYC_LEVELS[1],
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_duplicate_approver", state, tx
    )


# --- set_kyc: too many approvals ---


def test_set_kyc_too_many_approvals(state_test_group) -> None:
    """Set KYC with more than MAX_APPROVALS should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()

    approvals = [
        {"member_pubkey": _addr(100 + i), "signature": _sig(100 + i), "timestamp": _CURRENT_TIME}
        for i in range(MAX_APPROVALS + 1)
    ]
    payload = {
        "account": target,
        "level": VALID_KYC_LEVELS[1],
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.SET_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/set_kyc.json", "set_kyc_too_many_approvals", state, tx
    )


# --- renew_kyc negative tests ---


def test_renew_kyc_zero_data_hash(state_test_group) -> None:
    """Renew KYC with zero data_hash should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 10000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "data_hash": bytes(32),  # zero hash
        "verified_at": _CURRENT_TIME,
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": DAVE, "signature": _sig(5), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.RENEW_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/renew_kyc.json", "renew_kyc_zero_data_hash", state, tx
    )


def test_renew_kyc_no_approvals(state_test_group) -> None:
    """Renew KYC with empty approvals should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 10000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "data_hash": _hash(41),
        "verified_at": _CURRENT_TIME,
        "committee_id": _hash(50),
        "approvals": [],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.RENEW_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/renew_kyc.json", "renew_kyc_no_approvals", state, tx
    )


def test_renew_kyc_duplicate_approver(state_test_group) -> None:
    """Renew KYC with duplicate approver should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 10000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "data_hash": _hash(41),
        "verified_at": _CURRENT_TIME,
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.RENEW_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/renew_kyc.json", "renew_kyc_duplicate_approver", state, tx
    )


def test_renew_kyc_too_many_approvals(state_test_group) -> None:
    """Renew KYC with more than MAX_APPROVALS should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 10000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    approvals = [
        {"member_pubkey": _addr(100 + i), "signature": _sig(100 + i), "timestamp": _CURRENT_TIME}
        for i in range(MAX_APPROVALS + 1)
    ]
    payload = {
        "account": target,
        "data_hash": _hash(41),
        "verified_at": _CURRENT_TIME,
        "committee_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.RENEW_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/renew_kyc.json", "renew_kyc_too_many_approvals", state, tx
    )


# --- transfer_kyc: additional negative tests ---


def test_transfer_kyc_no_dest_approvals(state_test_group) -> None:
    """Transfer KYC with empty dest approvals should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "source_committee_id": _hash(50),
        "source_approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
        "dest_committee_id": _hash(51),
        "dest_approvals": [],  # empty
        "new_data_hash": _hash(42),
        "transferred_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_no_dest_approvals", state, tx
    )


def test_transfer_kyc_cross_committee_duplicate(state_test_group) -> None:
    """Transfer KYC with same member approving for both committees should fail."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.ACTIVE,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(50),
    )

    payload = {
        "account": target,
        "source_committee_id": _hash(50),
        "source_approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
        "dest_committee_id": _hash(51),
        "dest_approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
        "new_data_hash": _hash(42),
        "transferred_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_cross_committee_duplicate", state, tx
    )


# --- appeal_kyc: timestamp bounds ---


def test_appeal_kyc_submitted_at_far_future(state_test_group) -> None:
    """Appeal KYC with submitted_at far in the future should fail (encoding check)."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.REVOKED,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(51),
    )

    payload = {
        "account": target,
        "original_committee_id": _hash(51),
        "parent_committee_id": _hash(50),
        "reason_hash": _hash(43),
        "documents_hash": _hash(44),
        "submitted_at": _CURRENT_TIME + 7200,  # 2 hours in the future (too far)
    }
    tx = _mk_kyc_tx(target, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_submitted_at_far_future", state, tx
    )


def test_appeal_kyc_submitted_at_far_past(state_test_group) -> None:
    """Appeal KYC with submitted_at far in the past should fail (encoding check)."""
    state = _base_state()
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=10_000_000, nonce=5)
    state.committees[_hash(50)] = _global_committee()
    state.committees[_hash(51)] = _regional_committee()
    state.kyc_data[target] = KycData(
        level=VALID_KYC_LEVELS[1],
        status=KycStatus.REVOKED,
        verified_at=_CURRENT_TIME - 1000,
        data_hash=_hash(40),
        committee_id=_hash(51),
    )

    payload = {
        "account": target,
        "original_committee_id": _hash(51),
        "parent_committee_id": _hash(50),
        "reason_hash": _hash(43),
        "documents_hash": _hash(44),
        "submitted_at": _CURRENT_TIME - 7200,  # 2 hours in the past (too far)
    }
    tx = _mk_kyc_tx(target, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_submitted_at_far_past", state, tx
    )


# --- revoke_kyc: additional negative tests ---


def test_revoke_kyc_duplicate_approver(state_test_group) -> None:
    """Revoke KYC with duplicate approver should fail."""
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

    payload = {
        "account": target,
        "reason_hash": _hash(41),
        "committee_id": _hash(50),
        "approvals": [
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
            {"member_pubkey": CAROL, "signature": _sig(4), "timestamp": _CURRENT_TIME},
        ],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REVOKE_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/revoke_kyc.json", "revoke_kyc_duplicate_approver", state, tx
    )


def test_revoke_kyc_too_many_approvals(state_test_group) -> None:
    """Revoke KYC with more than MAX_APPROVALS should fail."""
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

    approvals = [
        {"member_pubkey": _addr(100 + i), "signature": _sig(100 + i), "timestamp": _CURRENT_TIME}
        for i in range(MAX_APPROVALS + 1)
    ]
    payload = {
        "account": target,
        "reason_hash": _hash(41),
        "committee_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REVOKE_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/revoke_kyc.json", "revoke_kyc_too_many_approvals", state, tx
    )


# --- emergency_suspend: additional negative tests ---


def test_emergency_suspend_too_many_approvals(state_test_group) -> None:
    """Emergency suspend with more than MAX_APPROVALS should fail."""
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

    approvals = [
        {"member_pubkey": _addr(100 + i), "signature": _sig(100 + i), "timestamp": _CURRENT_TIME}
        for i in range(MAX_APPROVALS + 1)
    ]
    payload = {
        "account": target,
        "reason_hash": _hash(45),
        "committee_id": _hash(50),
        "approvals": approvals,
        "expires_at": _CURRENT_TIME + EMERGENCY_SUSPEND_TIMEOUT,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.EMERGENCY_SUSPEND, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/emergency_suspend.json",
        "emergency_suspend_too_many_approvals",
        state,
        tx,
    )


def test_emergency_suspend_duplicate_approver(state_test_group) -> None:
    """Emergency suspend with duplicate approver should fail."""
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
        _sign_approval(CAROL, msg, ts),  # duplicate
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
        "emergency_suspend_duplicate_approver",
        state,
        tx,
    )


def test_emergency_suspend_no_approvals(state_test_group) -> None:
    """Emergency suspend with empty approvals should fail (needs 2)."""
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

    payload = {
        "account": target,
        "reason_hash": _hash(45),
        "committee_id": _hash(50),
        "approvals": [],
        "expires_at": _CURRENT_TIME + EMERGENCY_SUSPEND_TIMEOUT,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.EMERGENCY_SUSPEND, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/emergency_suspend.json",
        "emergency_suspend_no_approvals",
        state,
        tx,
    )


# --- bootstrap_committee: additional validation tests ---


def test_bootstrap_committee_kyc_threshold_zero(state_test_group) -> None:
    """Bootstrap committee with kyc_threshold=0 should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "KycThreshZero",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 0,  # invalid
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_kyc_threshold_zero",
        state,
        tx,
    )


def test_bootstrap_committee_threshold_exceeds_members(state_test_group) -> None:
    """Bootstrap committee with threshold > member count should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "ThreshExceedsMembers",
        "members": members,
        "threshold": MIN_COMMITTEE_MEMBERS + 1,  # exceeds member count
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_threshold_exceeds_members",
        state,
        tx,
    )


def test_bootstrap_committee_kyc_threshold_exceeds_members(state_test_group) -> None:
    """Bootstrap committee with kyc_threshold > member count should fail."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10 + i), "name": f"member_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "KycThreshExceeds",
        "members": members,
        "threshold": 2,
        "kyc_threshold": MIN_COMMITTEE_MEMBERS + 1,  # exceeds member count
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_kyc_threshold_exceeds_members",
        state,
        tx,
    )


def test_bootstrap_committee_member_name_too_long(state_test_group) -> None:
    """Bootstrap committee with a member name exceeding MAX_MEMBER_NAME_LEN should fail."""
    from tos_spec.config import MAX_MEMBER_NAME_LEN as MMLEN
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = MINER
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    members = [
        {"public_key": _addr(10), "name": "B" * (MMLEN + 1), "role": 0},
        {"public_key": _addr(11), "name": "member_1", "role": 0},
        {"public_key": _addr(12), "name": "member_2", "role": 0},
    ]
    payload = {
        "name": "MemberNameLong",
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[4],
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.BOOTSTRAP_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/bootstrap_committee.json",
        "bootstrap_committee_member_name_too_long",
        state,
        tx,
    )


# --- register_committee: additional validation tests ---


def test_register_committee_name_too_long(state_test_group) -> None:
    """Register committee with name exceeding MAX_COMMITTEE_NAME_LEN should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    long_name = "A" * (MAX_COMMITTEE_NAME_LEN + 1)
    msg = _build_register_committee_msg(
        _hash(50), long_name, 1, config_hash, ts,
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
        "name": long_name,
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_name_too_long",
        state,
        tx,
    )


def test_register_committee_too_many_members(state_test_group) -> None:
    """Register committee with more than MAX_COMMITTEE_MEMBERS should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (_addr(100 + i), f"rmember_{i}", 0)
        for i in range(MAX_COMMITTEE_MEMBERS + 1)
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "TooManyRegional", 1, config_hash, ts,
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
        "name": "TooManyRegional",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_too_many_members",
        state,
        tx,
    )


def test_register_committee_invalid_kyc_level(state_test_group) -> None:
    """Register committee with invalid max_kyc_level should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "BadLevelRegional", 1, config_hash, ts,
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
        "name": "BadLevelRegional",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": 999,  # invalid level
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_invalid_kyc_level",
        state,
        tx,
    )


def test_register_committee_threshold_zero(state_test_group) -> None:
    """Register committee with threshold=0 should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "ThreshZero", 1, config_hash, ts,
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
        "name": "ThreshZero",
        "region": 1,
        "members": members_payload,
        "threshold": 0,  # invalid
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_threshold_zero",
        state,
        tx,
    )


def test_register_committee_kyc_threshold_zero(state_test_group) -> None:
    """Register committee with kyc_threshold=0 should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (GRACE, "rmember_0", 0),
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "KycThreshZero", 1, config_hash, ts,
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
        "name": "KycThreshZero",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 0,  # invalid
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_kyc_threshold_zero",
        state,
        tx,
    )


def test_register_committee_member_name_too_long(state_test_group) -> None:
    """Register committee with member name exceeding MAX_MEMBER_NAME_LEN should fail."""
    from tos_spec.config import MAX_MEMBER_NAME_LEN as MMLEN
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    new_members = [
        (GRACE, "B" * (MMLEN + 1), 0),  # name too long
        (HEIDI, "rmember_1", 0),
        (IVAN, "rmember_2", 0),
    ]
    config_hash = _compute_register_config_hash(
        new_members, 2, 2, VALID_KYC_LEVELS[3],
    )
    msg = _build_register_committee_msg(
        _hash(50), "LongMemberName", 1, config_hash, ts,
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
        "name": "LongMemberName",
        "region": 1,
        "members": members_payload,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/register_committee.json",
        "register_committee_member_name_too_long",
        state,
        tx,
    )


# --- update_committee: additional validation tests ---


def test_update_committee_kyc_threshold_zero(state_test_group) -> None:
    """Update committee kyc_threshold to zero should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    msg = _build_update_committee_msg(_hash(50), 3, _hash(60), ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "update_kyc_threshold",
            "new_kyc_threshold": 0,
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_kyc_threshold_zero",
        state,
        tx,
    )


def test_update_committee_name_too_long(state_test_group) -> None:
    """Update committee name to a string exceeding MAX_COMMITTEE_NAME_LEN should fail."""
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()
    ts = _CURRENT_TIME

    msg = _build_update_committee_msg(_hash(50), 4, _hash(60), ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "update_name",
            "new_name": "A" * (MAX_COMMITTEE_NAME_LEN + 1),
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_name_too_long",
        state,
        tx,
    )


def test_update_committee_add_member_name_too_long(state_test_group) -> None:
    """Update committee add_member with name exceeding MAX_MEMBER_NAME_LEN should fail."""
    from tos_spec.config import MAX_MEMBER_NAME_LEN as MMLEN
    state = _base_state()
    sender = ALICE
    state.committees[_hash(50)] = _global_committee()

    long_name = "B" * (MMLEN + 1)
    update_data_hash = _compute_add_member_data_hash(
        BOB, long_name, 3,
    )

    ts = _CURRENT_TIME
    msg = _build_update_committee_msg(_hash(50), 0, update_data_hash, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
    ]

    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "add_member",
            "public_key": BOB,
            "name": long_name,
            "role": 3,
        },
        "approvals": approvals,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_COMMITTEE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/update_committee.json",
        "update_committee_add_member_name_too_long",
        state,
        tx,
    )


# --- set_kyc: all valid levels ---


def test_set_kyc_level_zero(state_test_group) -> None:
    """Set KYC at level 0 (tier 0) should succeed."""
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    state.committees[_hash(50)] = _global_committee()

    level = 0
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
        "transactions/kyc/set_kyc.json", "set_kyc_level_zero", state, tx
    )


def test_set_kyc_max_level(state_test_group) -> None:
    """Set KYC at max level 32767 (tier 8) with 3 approvals should succeed.

    Tier 5+ requires kyc_threshold + 1 approvals (3 for kyc_threshold=2).
    """
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    gc = _global_committee()
    gc.max_kyc_level = VALID_KYC_LEVELS[8]  # 32767 to allow tier 8
    state.committees[_hash(50)] = gc

    level = 32767  # Tier 8
    verified_at = _CURRENT_TIME
    committee_id = _hash(50)
    data_hash = _hash(40)
    ts = _CURRENT_TIME

    msg = _build_set_kyc_msg(committee_id, target, level, data_hash, verified_at, ts)
    approvals = [
        _sign_approval(CAROL, msg, ts),
        _sign_approval(DAVE, msg, ts),
        _sign_approval(FRANK, msg, ts),
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
        "transactions/kyc/set_kyc.json", "set_kyc_max_level", state, tx
    )


