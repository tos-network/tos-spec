"""KYC tx fixtures."""

from __future__ import annotations

from tos_spec.config import (
    APPROVAL_EXPIRY_SECONDS,
    CHAIN_ID_DEVNET,
    EMERGENCY_SUSPEND_TIMEOUT,
    MAX_COMMITTEE_NAME_LEN,
    MIN_COMMITTEE_MEMBERS,
    VALID_KYC_LEVELS,
)
from tos_spec.test_accounts import ALICE, EVE
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)

_CURRENT_TIME = 1_700_000_000


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig(byte: int) -> bytes:
    # Use byte only in first position of each 32-byte scalar half to ensure
    # the value is a canonical Ristretto scalar (< curve order l).
    return bytes([byte]) + b"\x00" * 31 + bytes([byte]) + b"\x00" * 31


def _base_state() -> ChainState:
    sender = ALICE
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[sender] = AccountState(address=sender, balance=10_000_000, nonce=5)
    return state


def _approval(member_byte: int) -> dict:
    return {
        "member_pubkey": _addr(member_byte),
        "signature": _sig(member_byte),
        "timestamp": _CURRENT_TIME,
    }


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
    members = [
        {"public_key": _addr(20 + i), "name": f"rmember_{i}", "role": 0}
        for i in range(MIN_COMMITTEE_MEMBERS)
    ]
    payload = {
        "name": "RegionalCommittee",
        "region": 1,
        "members": members,
        "threshold": 2,
        "kyc_threshold": 2,
        "max_kyc_level": VALID_KYC_LEVELS[3],
        "parent_id": _hash(50),
        "approvals": [_approval(10), _approval(11)],
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
    payload = {
        "committee_id": _hash(50),
        "update": {
            "type": "add_member",
            "public_key": _addr(30),
            "name": "new_member",
            "role": 0,
        },
        "approvals": [_approval(10), _approval(11)],
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
    payload = {
        "account": target,
        "level": VALID_KYC_LEVELS[1],
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": [_approval(10)],
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
    payload = {
        "account": target,
        "level": 999,
        "verified_at": _CURRENT_TIME,
        "data_hash": _hash(40),
        "committee_id": _hash(50),
        "approvals": [_approval(10)],
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
    payload = {
        "account": target,
        "reason_hash": _hash(41),
        "committee_id": _hash(50),
        "approvals": [_approval(10)],
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
    payload = {
        "account": target,
        "source_committee_id": _hash(50),
        "source_approvals": [_approval(10)],
        "dest_committee_id": _hash(51),
        "dest_approvals": [_approval(20)],
        "new_data_hash": _hash(42),
        "transferred_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.TRANSFER_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/transfer_kyc.json", "transfer_kyc_success", state, tx
    )


# --- appeal_kyc specs ---


def test_appeal_kyc_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    payload = {
        "account": target,
        "original_committee_id": _hash(50),
        "parent_committee_id": _hash(51),
        "reason_hash": _hash(43),
        "documents_hash": _hash(44),
        "submitted_at": _CURRENT_TIME,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.APPEAL_KYC, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/appeal_kyc.json", "appeal_kyc_success", state, tx
    )


# --- emergency_suspend specs ---


def test_emergency_suspend_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    target = EVE
    state.accounts[target] = AccountState(address=target, balance=0, nonce=0)
    payload = {
        "account": target,
        "reason_hash": _hash(45),
        "committee_id": _hash(50),
        "approvals": [_approval(10), _approval(11)],
        "expires_at": _CURRENT_TIME + EMERGENCY_SUSPEND_TIMEOUT,
    }
    tx = _mk_kyc_tx(sender, nonce=5, tx_type=TransactionType.EMERGENCY_SUSPEND, payload=payload, fee=100_000)
    state_test_group(
        "transactions/kyc/emergency_suspend.json",
        "emergency_suspend_success",
        state,
        tx,
    )
