"""Burn tx fixtures."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET
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


def _mk_burn(sender: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": amount},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_burn_success(state_test_group) -> None:
    state = _base_state()
    tx = _mk_burn(ALICE, nonce=5, amount=100_000, fee=100_000)
    state_test_group("transactions/core/burn.json", "burn_success", state, tx)


def test_burn_nonce_too_low(state_test_group) -> None:
    """Strict nonce: tx.nonce < sender.nonce."""
    state = _base_state()
    tx = _mk_burn(ALICE, nonce=4, amount=100_000, fee=100_000)
    state_test_group("transactions/core/burn.json", "burn_nonce_too_low", state, tx)


def test_burn_nonce_too_high_strict(state_test_group) -> None:
    """Strict nonce: tx.nonce > sender.nonce."""
    state = _base_state()
    tx = _mk_burn(ALICE, nonce=6, amount=100_000, fee=100_000)
    state_test_group(
        "transactions/core/burn.json", "burn_nonce_too_high_strict", state, tx
    )


def test_burn_insufficient_balance(state_test_group) -> None:
    state = _base_state()
    tx = _mk_burn(ALICE, nonce=5, amount=2_000_000, fee=100_000)
    state_test_group("transactions/core/burn.json", "burn_insufficient_balance", state, tx)


def test_burn_exact_balance(state_test_group) -> None:
    """Boundary: sender balance exactly equals burn amount + fee (should succeed)."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    fee = 100_000
    amount = 100_000
    state.accounts[ALICE] = AccountState(address=ALICE, balance=amount + fee, nonce=5)
    tx = _mk_burn(ALICE, nonce=5, amount=amount, fee=fee)
    state_test_group("transactions/core/burn.json", "burn_exact_balance", state, tx)


def test_burn_insufficient_balance_after_fee(state_test_group) -> None:
    """Boundary: can pay fee and amount individually, but not amount + fee."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    fee = 100_000
    amount = 100_000
    state.accounts[ALICE] = AccountState(address=ALICE, balance=amount + fee - 1, nonce=5)
    tx = _mk_burn(ALICE, nonce=5, amount=amount, fee=fee)
    state_test_group("transactions/core/burn.json", "burn_insufficient_balance_after_fee", state, tx)


def test_burn_invalid_amount(state_test_group) -> None:
    state = _base_state()
    tx = _mk_burn(ALICE, nonce=5, amount=0, fee=100_000)
    state_test_group("transactions/core/burn.json", "burn_invalid_amount", state, tx)


def test_burn_negative_amount(state_test_group) -> None:
    """Burn with negative amount."""
    state = _base_state()
    tx = _mk_burn(ALICE, nonce=5, amount=-1, fee=100_000)
    state_test_group("transactions/core/burn.json", "burn_negative_amount", state, tx)
