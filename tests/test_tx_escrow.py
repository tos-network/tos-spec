"""Escrow tx fixtures."""

from __future__ import annotations

import struct
import time

import tos_signer

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MIN_TIMEOUT_BLOCKS, MAX_BPS
from tos_spec.test_accounts import ALICE, BOB, CAROL
from tos_spec.types import (
    AccountState,
    ArbiterAccount,
    ArbiterStatus,
    ArbitrationConfig,
    ChainState,
    DisputeInfo,
    EscrowAccount,
    EscrowStatus,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig(byte: int) -> bytes:
    # Use byte only in first position of each 32-byte scalar half to ensure
    # the value is a canonical Ristretto scalar (< curve order l).
    return bytes([byte]) + b"\x00" * 31 + bytes([byte]) + b"\x00" * 31


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=100 * COIN_VALUE, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _funded_escrow(escrow_id: bytes, payer: bytes, payee: bytes, amount: int) -> EscrowAccount:
    """Create a funded escrow record for pre_state."""
    return EscrowAccount(
        id=escrow_id,
        task_id="test-task",
        payer=payer,
        payee=payee,
        amount=amount,
        total_amount=amount,
        status=EscrowStatus.FUNDED,
        asset=_hash(0),
        timeout_blocks=MIN_TIMEOUT_BLOCKS * 10,
        challenge_window=100,
        challenge_deposit_bps=500,
    )


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
        reference_hash=_hash(0),
        reference_topoheight=0,
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
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
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
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
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
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED
    payload = {
        "escrow_id": escrow_id,
        "amount": 5 * COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_success",
        state,
        tx,
    )


# --- release_escrow specs ---


def test_release_escrow_success(state_test_group) -> None:
    state = _base_state()
    # Payee (BOB) requests release in the optimistic release flow.
    sender = BOB
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.optimistic_release = True
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "amount": 5 * COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_success",
        state,
        tx,
    )


# --- refund_escrow specs ---


def test_refund_escrow_success(state_test_group) -> None:
    state = _base_state()
    # Payee (BOB) can initiate a refund before timeout.
    sender = BOB
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    payload = {
        "escrow_id": escrow_id,
        "amount": 5 * COIN_VALUE,
        "reason": "work not delivered",
    }
    tx = _mk_escrow_tx(sender, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
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
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single",
        arbiters=[CAROL],
        threshold=1,
        fee_amount=COIN_VALUE,
        allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "reason": "deliverable does not match specs",
        "deposit": COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
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
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single",
        arbiters=[CAROL],
        threshold=1,
        fee_amount=COIN_VALUE,
        allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "reason": "provider did not deliver",
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
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
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single",
        arbiters=[CAROL],
        threshold=1,
        fee_amount=COIN_VALUE,
        allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(
        initiator=ALICE,
        reason="provider did not deliver",
        disputed_at=1,
        deadline=1000,
    )
    escrow.dispute_id = _hash(61)
    escrow.dispute_round = 1
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "reason": "verdict was unfair",
        "appeal_deposit": 2 * COIN_VALUE,
        "appeal_mode": 1,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_success",
        state,
        tx,
    )


# --- submit_verdict specs ---


def _build_verdict_message(
    chain_id: int,
    escrow_id: bytes,
    dispute_id: bytes,
    round_num: int,
    outcome: int,
    payer_amount: int,
    payee_amount: int,
) -> bytes:
    """Build the TOS_VERDICT_V1 domain-separated message that arbiters sign."""
    msg = b"TOS_VERDICT_V1"
    msg += struct.pack("<Q", chain_id)
    msg += escrow_id
    msg += dispute_id
    msg += struct.pack("<I", round_num)
    msg += bytes([outcome])
    msg += struct.pack("<Q", payer_amount)
    msg += struct.pack("<Q", payee_amount)
    return msg


def test_submit_verdict_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    escrow_id = _hash(60)
    payer_amount = 3 * COIN_VALUE
    payee_amount = 7 * COIN_VALUE
    escrow = _funded_escrow(escrow_id, ALICE, BOB, payer_amount + payee_amount)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single",
        arbiters=[CAROL],
        threshold=1,
        fee_amount=COIN_VALUE,
        allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(
        initiator=ALICE,
        reason="provider did not deliver",
        disputed_at=1,
        deadline=1000,
    )
    state.escrows[escrow_id] = escrow
    # Register CAROL as an active arbiter with sufficient stake
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL,
        name="ArbiterCarol",
        status=ArbiterStatus.ACTIVE,
        stake_amount=1000 * COIN_VALUE,
    )
    # Build verdict message and sign with CAROL's key (seed=4)
    # outcome: Split=2 (both amounts non-zero)
    dispute_id = _hash(61)
    verdict_msg = _build_verdict_message(
        CHAIN_ID_DEVNET, escrow_id, dispute_id, 0, 2, payer_amount, payee_amount,
    )
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 0,
        "payer_amount": payer_amount,
        "payee_amount": payee_amount,
        "signatures": [
            {
                "arbiter_pubkey": CAROL,
                "signature": carol_sig,
                "timestamp": int(time.time()),
            }
        ],
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_success",
        state,
        tx,
    )
