"""Burn tx fixtures."""

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


def _mk_burn(sender: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": amount},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def test_burn_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_burn(sender, nonce=5, amount=100_000, fee=1_000)
    state_test_group("transactions/core/burn.json", "burn_success", state, tx)


def test_burn_insufficient_balance(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_burn(sender, nonce=5, amount=2_000_000, fee=1_000)
    state_test_group("transactions/core/burn.json", "burn_insufficient_balance", state, tx)


def test_burn_invalid_amount(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_burn(sender, nonce=5, amount=0, fee=1_000)
    state_test_group("transactions/core/burn.json", "burn_invalid_amount", state, tx)
