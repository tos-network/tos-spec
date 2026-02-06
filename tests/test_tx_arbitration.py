"""Arbitration tx fixtures."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MIN_ARBITER_STAKE
from tos_spec.test_accounts import ALICE
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
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=10_000 * COIN_VALUE, nonce=5
    )
    return state


def _mk_arb_tx(
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
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- register_arbiter specs ---


def test_register_arbiter_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "name": "ArbiterAlice",
        "expertise": [1, 2, 3],
        "stake_amount": MIN_ARBITER_STAKE,
        "min_escrow_value": COIN_VALUE,
        "max_escrow_value": 1000 * COIN_VALUE,
        "fee_basis_points": 250,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/register_arbiter.json",
        "register_arbiter_success",
        state,
        tx,
    )


def test_register_arbiter_low_stake(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "name": "LowStake",
        "expertise": [1],
        "stake_amount": COIN_VALUE,
        "min_escrow_value": COIN_VALUE,
        "max_escrow_value": 10 * COIN_VALUE,
        "fee_basis_points": 100,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/register_arbiter.json",
        "register_arbiter_low_stake",
        state,
        tx,
    )


# --- update_arbiter specs ---


def test_update_arbiter_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "name": "ArbiterAliceUpdated",
        "fee_basis_points": 300,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/update_arbiter.json",
        "update_arbiter_success",
        state,
        tx,
    )


# --- request_arbiter_exit specs ---


def test_request_arbiter_exit(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {}
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.REQUEST_ARBITER_EXIT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/request_arbiter_exit.json",
        "request_arbiter_exit",
        state,
        tx,
    )


# --- withdraw_arbiter_stake specs ---


def test_withdraw_arbiter_stake_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {"amount": MIN_ARBITER_STAKE}
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.WITHDRAW_ARBITER_STAKE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/withdraw_arbiter_stake.json",
        "withdraw_arbiter_stake_success",
        state,
        tx,
    )


# --- cancel_arbiter_exit specs ---


def test_cancel_arbiter_exit(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {}
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.CANCEL_ARBITER_EXIT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/cancel_arbiter_exit.json",
        "cancel_arbiter_exit",
        state,
        tx,
    )


# --- slash_arbiter specs ---


def test_slash_arbiter_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "committee_id": _hash(50),
        "arbiter_pubkey": _addr(30),
        "amount": COIN_VALUE * 10,
        "reason_hash": _hash(70),
        "approvals": [
            {
                "member_pubkey": _addr(10),
                "signature": _sig(10),
                "timestamp": 1_700_000_000,
            },
            {
                "member_pubkey": _addr(11),
                "signature": _sig(11),
                "timestamp": 1_700_000_000,
            },
        ],
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.SLASH_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/slash_arbiter.json",
        "slash_arbiter_success",
        state,
        tx,
    )


# --- commit_arbitration_open specs ---


def test_commit_arbitration_open(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "escrow_id": _hash(60),
        "dispute_id": _hash(61),
        "round": 1,
        "request_id": _hash(62),
        "arbitration_open_hash": _hash(63),
        "opener_signature": _sig(30),
        "arbitration_open_payload": b"\x00" * 64,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_ARBITRATION_OPEN, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_arbitration_open.json",
        "commit_arbitration_open",
        state,
        tx,
    )


# --- commit_vote_request specs ---


def test_commit_vote_request(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "request_id": _hash(62),
        "vote_request_hash": _hash(64),
        "coordinator_signature": _sig(31),
        "vote_request_payload": b"\x01" * 32,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_VOTE_REQUEST, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_vote_request.json",
        "commit_vote_request",
        state,
        tx,
    )


# --- commit_selection_commitment specs ---


def test_commit_selection_commitment(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "request_id": _hash(62),
        "selection_commitment_id": _hash(65),
        "selection_commitment_payload": b"\x02" * 32,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_SELECTION_COMMITMENT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_selection_commitment.json",
        "commit_selection_commitment",
        state,
        tx,
    )


# --- commit_juror_vote specs ---


def test_commit_juror_vote(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "request_id": _hash(62),
        "juror_pubkey": _addr(35),
        "vote_hash": _hash(66),
        "juror_signature": _sig(35),
        "vote_payload": b"\x03" * 16,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_JUROR_VOTE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_juror_vote.json",
        "commit_juror_vote",
        state,
        tx,
    )
