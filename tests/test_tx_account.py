"""Account tx fixtures (multisig, agent_account)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.test_accounts import ALICE, BOB, CAROL
from tos_spec.types import (
    AccountState,
    AgentAccountMeta,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=5)
    return state


def _mk_multisig(
    sender: bytes, nonce: int, threshold: int, participants: list[bytes], fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.MULTISIG,
        payload={"threshold": threshold, "participants": participants},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_agent_account(
    sender: bytes, nonce: int, payload: dict, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.AGENT_ACCOUNT,
        payload=payload,
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- multisig specs ---


def test_multisig_setup(state_test_group) -> None:
    state = _base_state()
    participants = [BOB, bytes([3]) * 32, bytes([4]) * 32]
    tx = _mk_multisig(ALICE, nonce=5, threshold=2, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json", "multisig_setup", state, tx
    )


def test_multisig_threshold_zero(state_test_group) -> None:
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=5, threshold=0, participants=[], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json", "multisig_threshold_zero", state, tx
    )


def test_multisig_single_participant(state_test_group) -> None:
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=5, threshold=1, participants=[BOB], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_single_participant",
        state,
        tx,
    )


# --- agent_account specs ---


def test_agent_account_register(state_test_group) -> None:
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register",
        state,
        tx,
    )


def test_agent_account_update_policy(state_test_group) -> None:
    state = _base_state()
    payload = {
        "variant": "update_policy",
        "policy_hash": _hash(4),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_update_policy",
        state,
        tx,
    )


def test_agent_account_rotate_controller(state_test_group) -> None:
    state = _base_state()
    payload = {
        "variant": "rotate_controller",
        "new_controller": bytes([5]) * 32,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller",
        state,
        tx,
    )


# --- multisig boundary tests ---


def test_multisig_duplicate_participants(state_test_group) -> None:
    """Duplicate keys in participant list."""
    state = _base_state()
    participants = [BOB, BOB, CAROL]
    tx = _mk_multisig(ALICE, nonce=5, threshold=2, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_duplicate_participants",
        state,
        tx,
    )
