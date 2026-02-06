"""Escrow tx fixtures."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MIN_TIMEOUT_BLOCKS, MAX_BPS
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


def _sig(byte: int) -> bytes:
    return bytes([byte]) * 64


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=100 * COIN_VALUE, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _mk_escrow_tx(
    sender: bytes, nonce: int, tx_type: TransactionType, payload: dict, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=tx_type,
        payload=payload,
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=bytes(64),
    )


# --- create_escrow specs ---


def test_create_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "task_id": "task_001",
        "provider": BOB,
        "amount": 10 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_success",
        state,
        tx,
    )


def test_create_escrow_zero_amount(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "task_id": "task_002",
        "provider": BOB,
        "amount": 0,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_zero_amount",
        state,
        tx,
    )


# --- deposit_escrow specs ---


def test_deposit_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "amount": 5 * COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_success",
        state,
        tx,
    )


# --- release_escrow specs ---


def test_release_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "amount": 5 * COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_success",
        state,
        tx,
    )


# --- refund_escrow specs ---


def test_refund_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "amount": 5 * COIN_VALUE,
        "reason": "work not delivered",
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_success",
        state,
        tx,
    )


# --- challenge_escrow specs ---


def test_challenge_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "reason": "deliverable does not match specs",
        "deposit": COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_success",
        state,
        tx,
    )


# --- dispute_escrow specs ---


def test_dispute_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "reason": "provider did not deliver",
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_success",
        state,
        tx,
    )


# --- appeal_escrow specs ---


def test_appeal_escrow_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "reason": "verdict was unfair",
        "appeal_deposit": 2 * COIN_VALUE,
        "appeal_mode": 1,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_success",
        state,
        tx,
    )


# --- submit_verdict specs ---


def test_submit_verdict_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "dispute_id": _hash(61),
        "round": 1,
        "payer_amount": 3 * COIN_VALUE,
        "payee_amount": 7 * COIN_VALUE,
        "signatures": [
            {
                "arbiter_pubkey": bytes([30]) * 32,
                "signature": _sig(30),
                "timestamp": 1_700_000_000,
            }
        ],
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=1_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_success",
        state,
        tx,
    )
