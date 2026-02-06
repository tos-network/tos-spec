"""Core tx fixtures (nonce + failed-tx semantics)."""

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
    state.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _mk_tx(sender: bytes, receiver: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=amount)],
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=bytes(64),
    )


def test_transfer_success(state_test) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=100_000, fee=1_000)
    state_test("transfer_success", state, tx)


def test_nonce_too_high(state_test) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=100, amount=100_000, fee=1_000)
    state_test("nonce_too_high", state, tx)


def test_insufficient_balance_execution_failure(state_test) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=2_000_000, fee=1_000)
    state_test("insufficient_balance_execution_failure", state, tx)
