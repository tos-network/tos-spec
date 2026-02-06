"""Account tx fixtures (multisig, agent_account)."""

from __future__ import annotations

from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig(byte: int) -> bytes:
    return bytes([byte]) * 64


def _base_state() -> ChainState:
    sender = _addr(1)
    state = ChainState(network_chain_id=0)
    state.accounts[sender] = AccountState(address=sender, balance=1_000_000, nonce=5)
    return state


def _mk_multisig(
    sender: bytes, nonce: int, threshold: int, participants: list[bytes], fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.MULTISIG,
        payload={"threshold": threshold, "participants": participants},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def _mk_agent_account(
    sender: bytes, nonce: int, payload: dict, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.AGENT_ACCOUNT,
        payload=payload,
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


# --- multisig specs ---


def test_multisig_setup(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    participants = [_addr(2), _addr(3), _addr(4)]
    tx = _mk_multisig(sender, nonce=5, threshold=2, participants=participants, fee=1_000)
    state_test_group(
        "transactions/account/multisig.json", "multisig_setup", state, tx
    )


def test_multisig_threshold_zero(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_multisig(sender, nonce=5, threshold=0, participants=[], fee=1_000)
    state_test_group(
        "transactions/account/multisig.json", "multisig_threshold_zero", state, tx
    )


def test_multisig_single_participant(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_multisig(sender, nonce=5, threshold=1, participants=[_addr(2)], fee=1_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_single_participant",
        state,
        tx,
    )


# --- agent_account specs ---


def test_agent_account_register(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    payload = {
        "variant": "register",
        "controller": _addr(2),
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(sender, nonce=5, payload=payload, fee=1_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register",
        state,
        tx,
    )


def test_agent_account_update_policy(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    payload = {
        "variant": "update_policy",
        "policy_hash": _hash(4),
    }
    tx = _mk_agent_account(sender, nonce=5, payload=payload, fee=1_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_update_policy",
        state,
        tx,
    )


def test_agent_account_rotate_controller(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    payload = {
        "variant": "rotate_controller",
        "new_controller": _addr(5),
    }
    tx = _mk_agent_account(sender, nonce=5, payload=payload, fee=1_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller",
        state,
        tx,
    )
