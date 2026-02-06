"""TNS tx fixtures (register_name)."""

from __future__ import annotations

from tos_spec.config import MAX_NAME_LENGTH, MIN_NAME_LENGTH
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


def _mk_register_name(sender: bytes, nonce: int, name: str, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.REGISTER_NAME,
        payload={"name": name},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def test_register_name_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_register_name(sender, nonce=5, name="alice", fee=1_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_success", state, tx
    )


def test_register_name_too_short(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_register_name(sender, nonce=5, name="ab", fee=1_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_too_short", state, tx
    )


def test_register_name_too_long(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    long_name = "a" * (MAX_NAME_LENGTH + 1)
    tx = _mk_register_name(sender, nonce=5, name=long_name, fee=1_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_too_long", state, tx
    )


def test_register_name_min_length(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_register_name(sender, nonce=5, name="a" * MIN_NAME_LENGTH, fee=1_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_min_length", state, tx
    )
