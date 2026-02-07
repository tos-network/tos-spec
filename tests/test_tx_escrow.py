"""Escrow tx fixtures."""

from __future__ import annotations

import struct
import time

import tos_signer

from tos_spec.config import (
    CHAIN_ID_DEVNET,
    COIN_VALUE,
    MAX_REASON_LEN,
    MAX_TASK_ID_LEN,
    MAX_TIMEOUT_BLOCKS,
    MIN_TIMEOUT_BLOCKS,
    MAX_BPS,
)
from tos_spec.test_accounts import ALICE, BOB, CAROL, DAVE
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


# ===================================================================
# Negative / boundary / authorization tests
# ===================================================================


# --- create_escrow neg tests ---


def test_create_escrow_self_provider(state_test_group) -> None:
    """Payer cannot also be the provider (self-operation)."""
    state = _base_state()
    payload = {
        "task_id": "task_self",
        "provider": ALICE,
        "amount": 10 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_self_provider",
        state,
        tx,
    )


def test_create_escrow_insufficient_balance(state_test_group) -> None:
    """Sender does not have enough balance for escrow amount."""
    state = _base_state()
    payload = {
        "task_id": "task_big",
        "provider": BOB,
        "amount": 200 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_insufficient_balance",
        state,
        tx,
    )


def test_create_escrow_timeout_too_low(state_test_group) -> None:
    """Timeout below MIN_TIMEOUT_BLOCKS."""
    state = _base_state()
    payload = {
        "task_id": "task_low_timeout",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": 1,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_timeout_too_low",
        state,
        tx,
    )


def test_create_escrow_empty_task_id(state_test_group) -> None:
    """Task ID must not be empty."""
    state = _base_state()
    payload = {
        "task_id": "",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_empty_task_id",
        state,
        tx,
    )


def test_create_escrow_zero_challenge_window(state_test_group) -> None:
    """Challenge window must be > 0."""
    state = _base_state()
    payload = {
        "task_id": "task_no_window",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 0,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_zero_challenge_window",
        state,
        tx,
    )


# --- deposit_escrow neg tests ---


def test_deposit_escrow_zero_amount(state_test_group) -> None:
    """Deposit amount must be > 0."""
    state = _base_state()
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED
    payload = {"escrow_id": escrow_id, "amount": 0}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_zero_amount",
        state,
        tx,
    )


def test_deposit_escrow_not_found(state_test_group) -> None:
    """Deposit to nonexistent escrow."""
    state = _base_state()
    payload = {"escrow_id": _hash(99), "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_not_found",
        state,
        tx,
    )


def test_deposit_escrow_wrong_state(state_test_group) -> None:
    """Cannot deposit to a released escrow."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RELEASED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_wrong_state",
        state,
        tx,
    )


# --- release_escrow neg tests ---


def test_release_escrow_zero_amount(state_test_group) -> None:
    """Release amount must be > 0."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.optimistic_release = True
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 0}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_zero_amount",
        state,
        tx,
    )


def test_release_escrow_not_payee(state_test_group) -> None:
    """Only the payee can request release."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.optimistic_release = True
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    # ALICE is the payer, not the payee -- should be rejected
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_not_payee",
        state,
        tx,
    )


def test_release_escrow_not_funded(state_test_group) -> None:
    """Cannot release from a non-funded escrow."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.optimistic_release = True
    escrow.status = EscrowStatus.CHALLENGED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_not_funded",
        state,
        tx,
    )


def test_release_escrow_exceeds_balance(state_test_group) -> None:
    """Release amount exceeds escrow balance."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 5 * COIN_VALUE)
    escrow.optimistic_release = True
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 10 * COIN_VALUE}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_exceeds_balance",
        state,
        tx,
    )


def test_release_escrow_optimistic_not_enabled(state_test_group) -> None:
    """Release requires optimistic_release flag."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.optimistic_release = False
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_optimistic_not_enabled",
        state,
        tx,
    )


def test_release_escrow_not_found(state_test_group) -> None:
    """Release on nonexistent escrow."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    payload = {"escrow_id": _hash(99), "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_not_found",
        state,
        tx,
    )


# --- refund_escrow neg tests ---


def test_refund_escrow_zero_amount(state_test_group) -> None:
    """Refund amount must be > 0."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    payload = {"escrow_id": escrow_id, "amount": 0, "reason": "test"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_zero_amount",
        state,
        tx,
    )


def test_refund_escrow_exceeds_balance(state_test_group) -> None:
    """Refund amount exceeds escrow balance."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 5 * COIN_VALUE)
    payload = {"escrow_id": escrow_id, "amount": 10 * COIN_VALUE, "reason": "too much"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_exceeds_balance",
        state,
        tx,
    )


def test_refund_escrow_reason_too_long(state_test_group) -> None:
    """Reason field exceeds MAX_REASON_LEN."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "x" * (MAX_REASON_LEN + 1)}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_reason_too_long",
        state,
        tx,
    )


def test_refund_escrow_not_found(state_test_group) -> None:
    """Refund on nonexistent escrow."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    payload = {"escrow_id": _hash(99), "amount": 5 * COIN_VALUE, "reason": "no escrow"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_not_found",
        state,
        tx,
    )


def test_refund_escrow_terminal_state(state_test_group) -> None:
    """Cannot refund an already-resolved escrow."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "late refund"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_terminal_state",
        state,
        tx,
    )


# --- challenge_escrow neg tests ---


def test_challenge_escrow_empty_reason(state_test_group) -> None:
    """Challenge reason must not be empty."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "", "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_empty_reason",
        state,
        tx,
    )


def test_challenge_escrow_zero_deposit(state_test_group) -> None:
    """Challenge deposit must be > 0."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "bad work", "deposit": 0}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_zero_deposit",
        state,
        tx,
    )


def test_challenge_escrow_not_payer(state_test_group) -> None:
    """Only the payer (client) can challenge."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=10 * COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "challenge by payee", "deposit": COIN_VALUE}
    # BOB is the payee, not the payer
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_not_payer",
        state,
        tx,
    )


def test_challenge_escrow_wrong_state(state_test_group) -> None:
    """Challenge requires PENDING_RELEASE state."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    # Escrow is FUNDED, not PENDING_RELEASE
    escrow.status = EscrowStatus.FUNDED
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "premature challenge", "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_wrong_state",
        state,
        tx,
    )


def test_challenge_escrow_not_found(state_test_group) -> None:
    """Challenge on nonexistent escrow."""
    state = _base_state()
    payload = {"escrow_id": _hash(99), "reason": "no escrow", "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_not_found",
        state,
        tx,
    )


# --- dispute_escrow neg tests ---


def test_dispute_escrow_empty_reason(state_test_group) -> None:
    """Dispute reason must not be empty."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": ""}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_empty_reason",
        state,
        tx,
    )


def test_dispute_escrow_unauthorized(state_test_group) -> None:
    """Only payer or payee can initiate dispute."""
    state = _base_state()
    state.accounts[DAVE] = AccountState(address=DAVE, balance=10 * COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "third party dispute"}
    tx = _mk_escrow_tx(DAVE, nonce=0, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_unauthorized",
        state,
        tx,
    )


def test_dispute_escrow_wrong_state(state_test_group) -> None:
    """Cannot dispute a resolved escrow."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "dispute resolved escrow"}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_wrong_state",
        state,
        tx,
    )


def test_dispute_escrow_already_exists(state_test_group) -> None:
    """Cannot dispute if a dispute already exists."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(
        initiator=ALICE, reason="existing dispute", disputed_at=1, deadline=1000,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "second dispute"}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_already_exists",
        state,
        tx,
    )


def test_dispute_escrow_no_arbitration(state_test_group) -> None:
    """Cannot dispute without arbitration config."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    # No arbitration_config set
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "no arbitration configured"}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_no_arbitration",
        state,
        tx,
    )


def test_dispute_escrow_not_found(state_test_group) -> None:
    """Dispute on nonexistent escrow."""
    state = _base_state()
    payload = {"escrow_id": _hash(99), "reason": "no escrow"}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_not_found",
        state,
        tx,
    )


# --- appeal_escrow neg tests ---


def test_appeal_escrow_zero_deposit(state_test_group) -> None:
    """Appeal deposit must be > 0."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "unfair", "appeal_deposit": 0, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_zero_deposit",
        state,
        tx,
    )


def test_appeal_escrow_empty_reason(state_test_group) -> None:
    """Appeal reason must not be empty."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_empty_reason",
        state,
        tx,
    )


def test_appeal_escrow_not_allowed(state_test_group) -> None:
    """Appeal rejected when allow_appeal is false."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "unfair", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_not_allowed",
        state,
        tx,
    )


def test_appeal_escrow_wrong_state(state_test_group) -> None:
    """Appeal requires RESOLVED state."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.FUNDED  # Not RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "unfair", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_wrong_state",
        state,
        tx,
    )


def test_appeal_escrow_unauthorized(state_test_group) -> None:
    """Only payer or payee can appeal."""
    state = _base_state()
    state.accounts[DAVE] = AccountState(address=DAVE, balance=10 * COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "third party appeal", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(DAVE, nonce=0, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_unauthorized",
        state,
        tx,
    )


def test_appeal_escrow_no_dispute(state_test_group) -> None:
    """Appeal requires a prior dispute record."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    # No dispute set
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "unfair verdict", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_no_dispute",
        state,
        tx,
    )


def test_appeal_escrow_not_found(state_test_group) -> None:
    """Appeal on nonexistent escrow."""
    state = _base_state()
    payload = {"escrow_id": _hash(99), "reason": "no escrow", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_not_found",
        state,
        tx,
    )


# --- submit_verdict neg tests ---


def test_submit_verdict_no_signatures(state_test_group) -> None:
    """Verdict must have at least one signature."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": _hash(61),
        "round": 0,
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_no_signatures",
        state,
        tx,
    )


def test_submit_verdict_wrong_state(state_test_group) -> None:
    """Verdict requires CHALLENGED state."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.FUNDED  # Not CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    dispute_id = _hash(61)
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, escrow_id, dispute_id, 0, 2, 5 * COIN_VALUE, 5 * COIN_VALUE)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 0,
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": int(time.time())}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_wrong_state",
        state,
        tx,
    )


def test_submit_verdict_amounts_mismatch(state_test_group) -> None:
    """Verdict payer_amount + payee_amount must equal escrow amount."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    dispute_id = _hash(61)
    # Amounts sum to 8 COIN_VALUE, but escrow has 10 COIN_VALUE
    payer_amount = 3 * COIN_VALUE
    payee_amount = 5 * COIN_VALUE
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, escrow_id, dispute_id, 0, 2, payer_amount, payee_amount)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 0,
        "payer_amount": payer_amount,
        "payee_amount": payee_amount,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": int(time.time())}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_amounts_mismatch",
        state,
        tx,
    )


def test_submit_verdict_no_dispute(state_test_group) -> None:
    """Verdict requires a dispute record."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    # No dispute set
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    dispute_id = _hash(61)
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, escrow_id, dispute_id, 0, 2, 5 * COIN_VALUE, 5 * COIN_VALUE)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 0,
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": int(time.time())}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_no_dispute",
        state,
        tx,
    )


def test_submit_verdict_not_found(state_test_group) -> None:
    """Verdict on nonexistent escrow."""
    state = _base_state()
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    dispute_id = _hash(61)
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, _hash(99), dispute_id, 0, 2, 5 * COIN_VALUE, 5 * COIN_VALUE)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": _hash(99),
        "dispute_id": dispute_id,
        "round": 0,
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": int(time.time())}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_not_found",
        state,
        tx,
    )


# ===================================================================
# Additional boundary tests
# ===================================================================


def test_create_escrow_timeout_max(state_test_group) -> None:
    """Create escrow with timeout_blocks at MAX_TIMEOUT_BLOCKS boundary (should pass)."""
    state = _base_state()
    payload = {
        "task_id": "task_max_timeout",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MAX_TIMEOUT_BLOCKS,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_timeout_max",
        state,
        tx,
    )


def test_create_escrow_timeout_over_max(state_test_group) -> None:
    """Create escrow with timeout_blocks exceeding MAX_TIMEOUT_BLOCKS."""
    state = _base_state()
    payload = {
        "task_id": "task_over_timeout",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MAX_TIMEOUT_BLOCKS + 1,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_timeout_over_max",
        state,
        tx,
    )


def test_create_escrow_task_id_max_length(state_test_group) -> None:
    """Create escrow with task_id at exactly MAX_TASK_ID_LEN (256 chars, should pass)."""
    state = _base_state()
    payload = {
        "task_id": "t" * MAX_TASK_ID_LEN,
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_task_id_max_length",
        state,
        tx,
    )


def test_create_escrow_task_id_too_long(state_test_group) -> None:
    """Create escrow with task_id exceeding MAX_TASK_ID_LEN (257 chars)."""
    state = _base_state()
    payload = {
        "task_id": "t" * (MAX_TASK_ID_LEN + 1),
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_task_id_too_long",
        state,
        tx,
    )


def test_deposit_escrow_amount_overflow(state_test_group) -> None:
    """Deposit amount so large that escrow balance would overflow u64.

    Pre-state escrow has amount near u64 max; depositing more overflows.
    """
    U64_MAX = (1 << 64) - 1
    state = _base_state()
    state.accounts[ALICE] = AccountState(address=ALICE, balance=U64_MAX, nonce=5)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, U64_MAX - 1)
    escrow.status = EscrowStatus.CREATED
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "amount": U64_MAX,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=0)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_amount_overflow",
        state,
        tx,
    )


def test_refund_escrow_amount_exceeds_balance(state_test_group) -> None:
    """Refund amount exceeds escrow balance (duplicate coverage check)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 3 * COIN_VALUE)
    payload = {"escrow_id": escrow_id, "amount": 10 * COIN_VALUE, "reason": "over-refund"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_amount_exceeds_balance_boundary",
        state,
        tx,
    )


# ===================================================================
# U64 overflow tests (apply-phase)
# ===================================================================

U64_MAX = (1 << 64) - 1


def test_deposit_escrow_amount_u64_overflow(state_test_group) -> None:
    """Deposit causes escrow.amount to overflow u64 max."""
    state = _base_state()
    state.accounts[ALICE] = AccountState(address=ALICE, balance=U64_MAX, nonce=5)
    escrow_id = _hash(61)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, U64_MAX - 100)
    escrow.status = EscrowStatus.CREATED
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "amount": 200,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=0)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_amount_u64_overflow",
        state,
        tx,
    )


def test_refund_escrow_balance_overflow(state_test_group) -> None:
    """Refund causes payer.balance to overflow u64 max."""
    state = _base_state()
    # Payer (ALICE) has balance near U64_MAX
    state.accounts[ALICE] = AccountState(address=ALICE, balance=U64_MAX - 50, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(62)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 200)
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "amount": 200,
        "reason": "refund overflow test",
    }
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=0)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_balance_overflow",
        state,
        tx,
    )
