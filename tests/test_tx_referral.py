"""Referral tx fixtures (bind_referrer)."""

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
    referrer = _addr(2)
    state = ChainState(network_chain_id=0)
    state.accounts[sender] = AccountState(address=sender, balance=1_000_000, nonce=5)
    state.accounts[referrer] = AccountState(address=referrer, balance=0, nonce=0)
    return state


def _mk_bind_referrer(sender: bytes, nonce: int, referrer: bytes, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.BIND_REFERRER,
        payload={"referrer": referrer},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def test_bind_referrer_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    referrer = _addr(2)
    tx = _mk_bind_referrer(sender, nonce=5, referrer=referrer, fee=1_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_success",
        state,
        tx,
    )


def test_bind_referrer_self(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_bind_referrer(sender, nonce=5, referrer=sender, fee=1_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_self",
        state,
        tx,
    )


def test_bind_referrer_not_found(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    unknown = _addr(99)
    tx = _mk_bind_referrer(sender, nonce=5, referrer=unknown, fee=1_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_not_found",
        state,
        tx,
    )
