"""Core tx fixtures (nonce + failed-tx semantics)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, MAX_NONCE_GAP, MAX_TRANSFER_COUNT
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
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_transfer_success(state_test) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=100_000, fee=100_000)
    state_test("transfer_success", state, tx)


def test_nonce_too_high(state_test) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=100, amount=100_000, fee=100_000)
    state_test("nonce_too_high", state, tx)


def test_insufficient_balance_execution_failure(state_test) -> None:
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=2_000_000, fee=100_000)
    state_test("insufficient_balance_execution_failure", state, tx)


def test_transfer_self(state_test) -> None:
    """Self-transfer (sender == recipient)."""
    state = _base_state()
    tx = _mk_tx(ALICE, ALICE, nonce=5, amount=100_000, fee=100_000)
    state_test("transfer_self", state, tx)


def test_transfer_empty_recipients(state_test) -> None:
    """Empty transfers list."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[],
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("transfer_empty_recipients", state, tx)


def test_transfer_max_count_exceeded(state_test) -> None:
    """More than MAX_TRANSFER_COUNT (500) recipients."""
    state = _base_state()
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=100_000_000, nonce=5
    )
    transfers = [
        TransferPayload(asset=_hash(0), destination=BOB, amount=1)
        for _ in range(MAX_TRANSFER_COUNT + 1)
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=transfers,
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("transfer_max_count_exceeded", state, tx)


def test_transfer_zero_amount(state_test) -> None:
    """Transfer with amount=0 (allowed by daemon — no-op transfer)."""
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=0, fee=100_000)
    state_test("transfer_zero_amount", state, tx)


def test_transfer_multiple_recipients(state_test) -> None:
    """Two valid transfers to different recipients."""
    from tos_spec.test_accounts import CAROL
    state = _base_state()
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    transfers = [
        TransferPayload(asset=_hash(0), destination=BOB, amount=100_000),
        TransferPayload(asset=_hash(0), destination=CAROL, amount=200_000),
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=transfers,
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("transfer_multiple_recipients", state, tx)


def test_nonce_too_low(state_test) -> None:
    """Nonce below account nonce."""
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=3, amount=100_000, fee=100_000)
    state_test("nonce_too_low", state, tx)


def test_nonce_gap_exceeded(state_test) -> None:
    """Nonce gap exceeds MAX_NONCE_GAP (64)."""
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5 + MAX_NONCE_GAP + 1, amount=100_000, fee=100_000)
    state_test("nonce_gap_exceeded", state, tx)
