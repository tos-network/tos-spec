"""Template example for executable spec tests."""

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


def _sig(byte: int) -> bytes:
    return bytes([byte]) * 64


def _base_state() -> ChainState:
    sender = _addr(1)
    receiver = _addr(2)
    state = ChainState(network_chain_id=0)
    state.accounts[sender] = AccountState(address=sender, balance=1_000_000, nonce=1)
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
        signature=_sig(7),
    )


def test_template_transfer_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    tx = _mk_tx(sender, receiver, nonce=1, amount=10_000, fee=1_000)
    state_test_group(
        "transactions/template/example.json",
        "template_transfer_success",
        state,
        tx,
    )


def test_template_transfer_insufficient_balance(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    tx = _mk_tx(sender, receiver, nonce=1, amount=10_000_000, fee=1_000)
    state_test_group(
        "transactions/template/example.json",
        "template_transfer_insufficient_balance",
        state,
        tx,
    )
