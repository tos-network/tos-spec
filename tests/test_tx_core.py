"""Core tx fixtures (nonce + failed-tx semantics)."""

from __future__ import annotations

from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _base_state() -> ChainState:
    sender = _addr(1)
    receiver = _addr(2)
    state = ChainState(network_chain_id=0)
    state.accounts[sender] = AccountState(address=sender, balance=1_000_000, nonce=5)
    state.accounts[receiver] = AccountState(address=receiver, balance=0, nonce=0)
    return state


def _mk_tx(sender: bytes, receiver: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=amount)],
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_hash(7),
    )


def test_transfer_success(state_test) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    tx = _mk_tx(sender, receiver, nonce=5, amount=100_000, fee=1_000)
    state_test("transfer_success", state, tx)


def test_nonce_too_high(state_test) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    tx = _mk_tx(sender, receiver, nonce=100, amount=100_000, fee=1_000)
    state_test("nonce_too_high", state, tx)


def test_insufficient_balance_execution_failure(state_test) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    tx = _mk_tx(sender, receiver, nonce=5, amount=2_000_000, fee=1_000)
    state_test("insufficient_balance_execution_failure", state, tx)
