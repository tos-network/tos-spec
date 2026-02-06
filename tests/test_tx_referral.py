"""Referral tx fixtures (bind_referrer)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.test_accounts import ALICE, BOB
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
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _mk_bind_referrer(sender: bytes, nonce: int, referrer: bytes, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.BIND_REFERRER,
        payload={"referrer": referrer},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=bytes(64),
    )


def test_bind_referrer_success(state_test_group) -> None:
    state = _base_state()
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=BOB, fee=1_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_success",
        state,
        tx,
    )


def test_bind_referrer_self(state_test_group) -> None:
    state = _base_state()
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=ALICE, fee=1_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_self",
        state,
        tx,
    )


def test_bind_referrer_not_found(state_test_group) -> None:
    state = _base_state()
    unknown = bytes([99]) * 32
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=unknown, fee=1_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_not_found",
        state,
        tx,
    )
