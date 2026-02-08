"""L2 block processing fixtures (multi-tx atomic semantics)."""

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
    state.global_state.block_height = 1
    state.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _mk_transfer(sender: bytes, receiver: bytes, nonce: int, amount: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=amount)],
        fee=0,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_block_multi_tx_success(block_test_group) -> None:
    state = _base_state()
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=6, amount=20_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_multi_tx_success",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_nonce_gap(block_test_group) -> None:
    """Second tx is invalid after applying the first; entire block must be rejected."""
    state = _base_state()
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    # After tx1, sender nonce becomes 6; nonce=7 is NONCE_TOO_HIGH (strict).
    tx2 = _mk_transfer(ALICE, BOB, nonce=7, amount=20_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_nonce_too_high",
        state,
        [tx1, tx2],
    )

