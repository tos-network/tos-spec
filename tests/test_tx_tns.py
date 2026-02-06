"""TNS tx fixtures (register_name)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, MAX_NAME_LENGTH, MIN_NAME_LENGTH
from tos_spec.test_accounts import ALICE
from tos_spec.types import (
    AccountState,
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


def _mk_register_name(sender: bytes, nonce: int, name: str, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.REGISTER_NAME,
        payload={"name": name},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_register_name_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="alice", fee=100_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_success", state, tx
    )


def test_register_name_too_short(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="ab", fee=100_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_too_short", state, tx
    )


def test_register_name_too_long(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    long_name = "a" * (MAX_NAME_LENGTH + 1)
    tx = _mk_register_name(sender, nonce=5, name=long_name, fee=100_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_too_long", state, tx
    )


def test_register_name_min_length(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="a" * MIN_NAME_LENGTH, fee=100_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_min_length", state, tx
    )
