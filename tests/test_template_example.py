"""Template example for executable spec tests."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.test_accounts import ALICE, BOB
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=1)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _mk_tx(sender: bytes, receiver: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=bytes([0]) * 32, destination=receiver, amount=amount)],
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_template_transfer_success(state_test_group) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=1, amount=10_000, fee=100_000)
    state_test_group(
        "transactions/template/example.json",
        "template_transfer_success",
        state,
        tx,
    )


def test_template_transfer_insufficient_balance(state_test_group) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=1, amount=10_000_000, fee=100_000)
    state_test_group(
        "transactions/template/example.json",
        "template_transfer_insufficient_balance",
        state,
        tx,
    )
