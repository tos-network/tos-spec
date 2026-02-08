"""Escrow tx fixtures."""

from __future__ import annotations

import struct

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

# Fixed timestamp to keep fixtures deterministic across regenerations.
_NOW = 1700000000


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


def test_create_escrow_insufficient_fee(state_test_group) -> None:
    """Fee pre-check: sender balance below fee must fail (INSUFFICIENT_FEE)."""
    state = _base_state()
    sender = ALICE
    state.accounts[ALICE].balance = 99_999
    payload = {
        "task_id": "task_insufficient_fee",
        "provider": BOB,
        "amount": 1,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_insufficient_fee",
        state,
        tx,
    )


def test_create_escrow_nonce_too_low(state_test_group) -> None:
    """Create escrow with nonce below sender.nonce must fail."""
    state = _base_state()
    sender = ALICE
    payload = {
        "task_id": "task_nonce_low",
        "provider": BOB,
        "amount": 10 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(sender, nonce=4, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_nonce_too_low",
        state,
        tx,
    )


def test_create_escrow_nonce_too_high_strict(state_test_group) -> None:
    """Create escrow with nonce above sender.nonce must fail (strict nonce)."""
    state = _base_state()
    sender = ALICE
    payload = {
        "task_id": "task_nonce_high",
        "provider": BOB,
        "amount": 10 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(sender, nonce=6, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_nonce_too_high_strict",
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


def test_deposit_escrow_insufficient_fee(state_test_group) -> None:
    """Fee pre-check: sender balance below fee must fail (INSUFFICIENT_FEE)."""
    state = _base_state()
    sender = ALICE
    state.accounts[ALICE].balance = 99_999
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED
    payload = {
        "escrow_id": escrow_id,
        "amount": 1,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_insufficient_fee",
        state,
        tx,
    )


def test_deposit_escrow_nonce_too_low(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED
    payload = {
        "escrow_id": escrow_id,
        "amount": 5 * COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=4, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_nonce_too_low",
        state,
        tx,
    )


def test_deposit_escrow_nonce_too_high_strict(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED
    payload = {
        "escrow_id": escrow_id,
        "amount": 5 * COIN_VALUE,
    }
    tx = _mk_escrow_tx(sender, nonce=6, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_nonce_too_high_strict",
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


def test_release_escrow_insufficient_fee(state_test_group) -> None:
    """Fee pre-check: sender balance below fee must fail (INSUFFICIENT_FEE)."""
    state = _base_state()
    sender = BOB
    state.accounts[BOB] = AccountState(address=BOB, balance=99_999, nonce=0)
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
        "release_escrow_insufficient_fee",
        state,
        tx,
    )


def test_release_escrow_nonce_too_low(state_test_group) -> None:
    state = _base_state()
    sender = BOB
    # Make sender nonce > tx nonce, without using negative tx nonce.
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=1)
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
        "release_escrow_nonce_too_low",
        state,
        tx,
    )


def test_release_escrow_nonce_too_high_strict(state_test_group) -> None:
    state = _base_state()
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
    tx = _mk_escrow_tx(sender, nonce=1, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_nonce_too_high_strict",
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


def test_refund_escrow_insufficient_fee(state_test_group) -> None:
    """Fee pre-check: sender balance below fee must fail (INSUFFICIENT_FEE)."""
    state = _base_state()
    sender = BOB
    state.accounts[BOB] = AccountState(address=BOB, balance=99_999, nonce=0)
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
        "refund_escrow_insufficient_fee",
        state,
        tx,
    )


def test_refund_escrow_nonce_too_low(state_test_group) -> None:
    state = _base_state()
    sender = BOB
    # Make sender nonce > tx nonce, without using negative tx nonce.
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=1)
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
        "refund_escrow_nonce_too_low",
        state,
        tx,
    )


def test_refund_escrow_nonce_too_high_strict(state_test_group) -> None:
    state = _base_state()
    sender = BOB
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    payload = {
        "escrow_id": escrow_id,
        "amount": 5 * COIN_VALUE,
        "reason": "work not delivered",
    }
    tx = _mk_escrow_tx(sender, nonce=1, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_nonce_too_high_strict",
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


def test_challenge_escrow_insufficient_fee(state_test_group) -> None:
    """Fee pre-check: sender balance below fee must fail (INSUFFICIENT_FEE)."""
    state = _base_state()
    sender = ALICE
    state.accounts[ALICE].balance = 99_999
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
        "deposit": 1,
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_insufficient_fee",
        state,
        tx,
    )


def test_challenge_escrow_nonce_too_low(state_test_group) -> None:
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
    tx = _mk_escrow_tx(sender, nonce=4, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_nonce_too_low",
        state,
        tx,
    )


def test_challenge_escrow_nonce_too_high_strict(state_test_group) -> None:
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
    tx = _mk_escrow_tx(sender, nonce=6, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_nonce_too_high_strict",
        state,
        tx,
    )


def test_challenge_escrow_insufficient_balance_for_deposit(state_test_group) -> None:
    """Challenge should fail if payer cannot cover the challenge deposit."""
    state = _base_state()
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

    deposit = COIN_VALUE
    # Enough to pay fee, but not enough to cover deposit.
    state.accounts[ALICE].balance = deposit - 1

    payload = {
        "escrow_id": escrow_id,
        "reason": "deliverable does not match specs",
        "deposit": deposit,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_insufficient_balance_for_deposit",
        state,
        tx,
    )


def test_challenge_escrow_exact_balance_for_deposit(state_test_group) -> None:
    """Boundary: payer balance exactly equals deposit + fee (should succeed)."""
    state = _base_state()
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

    fee = 100_000
    deposit = COIN_VALUE
    state.accounts[ALICE].balance = deposit + fee

    payload = {
        "escrow_id": escrow_id,
        "reason": "deliverable does not match specs",
        "deposit": deposit,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_exact_balance_for_deposit",
        state,
        tx,
    )


def test_challenge_escrow_insufficient_balance_after_fee_for_deposit(state_test_group) -> None:
    """Boundary: can pay fee, but cannot pay deposit + fee."""
    state = _base_state()
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

    fee = 100_000
    deposit = COIN_VALUE
    state.accounts[ALICE].balance = deposit + fee - 1

    payload = {
        "escrow_id": escrow_id,
        "reason": "deliverable does not match specs",
        "deposit": deposit,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_insufficient_balance_after_fee_for_deposit",
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


def test_dispute_escrow_insufficient_fee(state_test_group) -> None:
    """dispute_escrow with balance below fee must fail: INSUFFICIENT_FEE (pre-check)."""
    state = _base_state()
    sender = ALICE
    state.accounts[sender].balance = 99_999
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
        "dispute_escrow_insufficient_fee",
        state,
        tx,
    )


def test_dispute_escrow_nonce_too_low(state_test_group) -> None:
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
    tx = _mk_escrow_tx(sender, nonce=4, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_nonce_too_low",
        state,
        tx,
    )


def test_dispute_escrow_nonce_too_high_strict(state_test_group) -> None:
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
    tx = _mk_escrow_tx(sender, nonce=6, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_nonce_too_high_strict",
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


def test_appeal_escrow_insufficient_fee(state_test_group) -> None:
    """Fee pre-check: sender balance below fee must fail (INSUFFICIENT_FEE)."""
    state = _base_state()
    sender = ALICE
    state.accounts[ALICE].balance = 99_999
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
        "appeal_escrow_insufficient_fee",
        state,
        tx,
    )


def test_appeal_escrow_nonce_too_low(state_test_group) -> None:
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
    tx = _mk_escrow_tx(sender, nonce=4, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_nonce_too_low",
        state,
        tx,
    )


def test_appeal_escrow_nonce_too_high_strict(state_test_group) -> None:
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
    tx = _mk_escrow_tx(sender, nonce=6, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_nonce_too_high_strict",
        state,
        tx,
    )


def test_appeal_escrow_insufficient_balance_for_deposit(state_test_group) -> None:
    """Appeal should fail if appellant cannot cover the appeal deposit."""
    state = _base_state()
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

    appeal_deposit = 2 * COIN_VALUE
    # Enough to pay fee, but not enough to cover appeal deposit.
    state.accounts[ALICE].balance = appeal_deposit - 1

    payload = {
        "escrow_id": escrow_id,
        "reason": "verdict was unfair",
        "appeal_deposit": appeal_deposit,
        "appeal_mode": 1,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_insufficient_balance_for_deposit",
        state,
        tx,
    )


def test_appeal_escrow_exact_balance_for_deposit(state_test_group) -> None:
    """Boundary: appellant balance exactly equals appeal_deposit + fee (should succeed)."""
    state = _base_state()
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

    fee = 100_000
    appeal_deposit = 2 * COIN_VALUE
    state.accounts[ALICE].balance = appeal_deposit + fee

    payload = {
        "escrow_id": escrow_id,
        "reason": "verdict was unfair",
        "appeal_deposit": appeal_deposit,
        "appeal_mode": 1,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_exact_balance_for_deposit",
        state,
        tx,
    )


def test_appeal_escrow_insufficient_balance_after_fee_for_deposit(state_test_group) -> None:
    """Boundary: can pay fee, but cannot pay appeal_deposit + fee."""
    state = _base_state()
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

    fee = 100_000
    appeal_deposit = 2 * COIN_VALUE
    state.accounts[ALICE].balance = appeal_deposit + fee - 1

    payload = {
        "escrow_id": escrow_id,
        "reason": "verdict was unfair",
        "appeal_deposit": appeal_deposit,
        "appeal_mode": 1,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_insufficient_balance_after_fee_for_deposit",
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
                "timestamp": _NOW,
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


def test_submit_verdict_insufficient_fee(state_test_group) -> None:
    """submit_verdict with balance below fee must fail: INSUFFICIENT_FEE (pre-check)."""
    state = _base_state()
    sender = ALICE
    state.accounts[sender].balance = 99_999
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
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL,
        name="ArbiterCarol",
        status=ArbiterStatus.ACTIVE,
        stake_amount=1000 * COIN_VALUE,
    )
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
                "timestamp": _NOW,
            }
        ],
    }
    tx = _mk_escrow_tx(sender, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_insufficient_fee",
        state,
        tx,
    )


def test_submit_verdict_nonce_too_low(state_test_group) -> None:
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
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL,
        name="ArbiterCarol",
        status=ArbiterStatus.ACTIVE,
        stake_amount=1000 * COIN_VALUE,
    )
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
                "timestamp": _NOW,
            }
        ],
    }
    tx = _mk_escrow_tx(sender, nonce=4, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_nonce_too_low",
        state,
        tx,
    )


def test_submit_verdict_nonce_too_high_strict(state_test_group) -> None:
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
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL,
        name="ArbiterCarol",
        status=ArbiterStatus.ACTIVE,
        stake_amount=1000 * COIN_VALUE,
    )
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
                "timestamp": _NOW,
            }
        ],
    }
    tx = _mk_escrow_tx(sender, nonce=6, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_nonce_too_high_strict",
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


def test_create_escrow_exact_balance(state_test_group) -> None:
    """Boundary: sender balance exactly equals amount + fee (should succeed)."""
    state = _base_state()
    fee = 100_000
    amount = 5 * COIN_VALUE
    state.accounts[ALICE].balance = amount + fee
    payload = {
        "task_id": "task_exact_balance",
        "provider": BOB,
        "amount": amount,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_exact_balance",
        state,
        tx,
    )


def test_create_escrow_insufficient_balance_after_fee(state_test_group) -> None:
    """Boundary: can pay fee, but cannot pay amount + fee."""
    state = _base_state()
    fee = 100_000
    amount = 5 * COIN_VALUE
    state.accounts[ALICE].balance = amount + fee - 1
    payload = {
        "task_id": "task_exact_minus_one",
        "provider": BOB,
        "amount": amount,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_insufficient_balance_after_fee",
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


def test_deposit_escrow_insufficient_balance(state_test_group) -> None:
    """Deposit should fail if sender balance is less than deposit amount."""
    state = _base_state()
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED

    # Enough to pay fee, but not enough to cover the deposit amount.
    state.accounts[ALICE].balance = (5 * COIN_VALUE) - 1

    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_insufficient_balance",
        state,
        tx,
    )


def test_deposit_escrow_exact_balance(state_test_group) -> None:
    """Boundary: sender balance exactly equals deposit amount + fee (should succeed)."""
    state = _base_state()
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED

    fee = 100_000
    amount = 5 * COIN_VALUE
    state.accounts[ALICE].balance = amount + fee

    payload = {"escrow_id": escrow_id, "amount": amount}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_exact_balance",
        state,
        tx,
    )


def test_deposit_escrow_insufficient_balance_after_fee(state_test_group) -> None:
    """Boundary: can pay fee, but cannot pay deposit amount + fee."""
    state = _base_state()
    escrow_id = _hash(60)
    state.escrows[escrow_id] = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    state.escrows[escrow_id].status = EscrowStatus.CREATED

    fee = 100_000
    amount = 5 * COIN_VALUE
    state.accounts[ALICE].balance = amount + fee - 1

    payload = {"escrow_id": escrow_id, "amount": amount}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=fee)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_insufficient_balance_after_fee",
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
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
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
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
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
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
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
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
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
    """Create escrow with task_id at the max wire-encodable length (255 bytes, should pass)."""
    state = _base_state()
    payload = {
        # Wire format uses u8 length prefix for strings, so 255 is the true max.
        "task_id": "t" * 255,
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
    escrow = _funded_escrow(escrow_id, ALICE, BOB, U64_MAX - 100)
    escrow.status = EscrowStatus.CREATED
    state.escrows[escrow_id] = escrow
    payload = {
        "escrow_id": escrow_id,
        "amount": 200,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
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
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
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
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_balance_overflow",
        state,
        tx,
    )


# ===================================================================
# Additional validation tests aligned with Rust escrow.rs
# ===================================================================


# --- create_escrow: challenge_deposit_bps > MAX_BPS ---


def test_create_escrow_bps_over_max(state_test_group) -> None:
    """challenge_deposit_bps exceeding MAX_BPS (10_000) must be rejected."""
    state = _base_state()
    payload = {
        "task_id": "task_bps",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": MAX_BPS + 1,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_bps_over_max",
        state,
        tx,
    )


# --- create_escrow: arbitration config validation ---


def test_create_escrow_arb_mode_none_with_config(state_test_group) -> None:
    """Arbitration mode 'none' is invalid when arbitration_config is present."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_none",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "none",
            "arbiters": [CAROL],
            "threshold": 1,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_arb_mode_none_with_config",
        state,
        tx,
    )


def test_create_escrow_single_mode_wrong_arbiter_count(state_test_group) -> None:
    """Single mode requires exactly 1 arbiter."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_single_wrong",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "single",
            "arbiters": [CAROL, DAVE],
            "threshold": 1,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_single_mode_wrong_arbiter_count",
        state,
        tx,
    )


def test_create_escrow_single_mode_wrong_threshold(state_test_group) -> None:
    """Single mode requires threshold=1 when specified."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_single_thresh",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "single",
            "arbiters": [CAROL],
            "threshold": 2,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_single_mode_wrong_threshold",
        state,
        tx,
    )


def test_create_escrow_committee_no_arbiters(state_test_group) -> None:
    """Committee mode requires at least one arbiter."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_committee_empty",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "committee",
            "arbiters": [],
            "threshold": 1,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_committee_no_arbiters",
        state,
        tx,
    )


def test_create_escrow_committee_zero_threshold(state_test_group) -> None:
    """Committee mode threshold cannot be zero."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_committee_zero_thresh",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "committee",
            "arbiters": [CAROL, DAVE],
            "threshold": 0,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_committee_zero_threshold",
        state,
        tx,
    )


def test_create_escrow_committee_threshold_exceeds_arbiters(state_test_group) -> None:
    """Committee mode threshold exceeds arbiter count."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_committee_high_thresh",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "committee",
            "arbiters": [CAROL],
            "threshold": 3,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_committee_threshold_exceeds_arbiters",
        state,
        tx,
    )


def test_create_escrow_dao_no_arbiters(state_test_group) -> None:
    """DaoGovernance mode requires at least one arbiter."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_dao_empty",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "dao-governance",
            "arbiters": [],
            "threshold": 1,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_dao_no_arbiters",
        state,
        tx,
    )


def test_create_escrow_dao_threshold_exceeds_arbiters(state_test_group) -> None:
    """DaoGovernance mode threshold exceeds arbiter count."""
    state = _base_state()
    payload = {
        "task_id": "task_arb_dao_high_thresh",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "dao-governance",
            "arbiters": [CAROL],
            "threshold": 3,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_dao_threshold_exceeds_arbiters",
        state,
        tx,
    )


def test_create_escrow_optimistic_release_without_arbitration(state_test_group) -> None:
    """optimistic_release=True requires arbitration_config to be present."""
    state = _base_state()
    payload = {
        "task_id": "task_optimistic_no_arb",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": True,
        # No arbitration_config
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_optimistic_release_without_arbitration",
        state,
        tx,
    )


def test_create_escrow_valid_with_arbitration(state_test_group) -> None:
    """Create escrow with valid arbitration_config (happy path)."""
    state = _base_state()
    payload = {
        "task_id": "task_with_arb",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": True,
        "arbitration_config": {
            "mode": "single",
            "arbiters": [CAROL],
            "threshold": 1,
            "fee_amount": COIN_VALUE,
            "allow_appeal": False,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_valid_with_arbitration",
        state,
        tx,
    )


# --- challenge_escrow: additional neg tests ---


def test_challenge_escrow_reason_too_long(state_test_group) -> None:
    """Challenge reason exceeding MAX_REASON_LEN must be rejected."""
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
    payload = {"escrow_id": escrow_id, "reason": "x" * (MAX_REASON_LEN + 1), "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_reason_too_long",
        state,
        tx,
    )


def test_challenge_escrow_optimistic_not_enabled(state_test_group) -> None:
    """Challenge requires optimistic_release=True on the escrow."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = False  # Not enabled
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "bad work", "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_optimistic_not_enabled",
        state,
        tx,
    )


def test_challenge_escrow_no_arbitration_config(state_test_group) -> None:
    """Challenge requires arbitration_config to handle disputes."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    # No arbitration_config
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "bad work", "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_no_arbitration_config",
        state,
        tx,
    )


def test_challenge_escrow_window_expired(state_test_group) -> None:
    """Challenge after the challenge window has expired must be rejected."""
    state = _base_state()
    # Set block height beyond the window
    state.global_state.block_height = 200
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.challenge_window = 100  # Window ends at block 101
    escrow.pending_release_amount = 5 * COIN_VALUE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "late challenge", "deposit": COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_window_expired",
        state,
        tx,
    )


def test_challenge_escrow_deposit_too_low(state_test_group) -> None:
    """Challenge deposit below required bps-based minimum must be rejected.

    With pending_release_amount=10 COIN, challenge_deposit_bps=500 (5%),
    required = 10 * 500 / 10000 = 0.5 COIN. Providing less than that fails.
    """
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 10 * COIN_VALUE
    escrow.challenge_deposit_bps = 500  # 5%
    state.escrows[escrow_id] = escrow
    # Required: 10 * COIN_VALUE * 500 / 10000 = 0.5 COIN_VALUE
    # Provide only 1 atomic unit (far below required)
    payload = {"escrow_id": escrow_id, "reason": "underdeposit", "deposit": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_deposit_too_low",
        state,
        tx,
    )


def test_challenge_escrow_deposit_exact_minimum(state_test_group) -> None:
    """Challenge deposit at exactly the bps-based minimum should succeed."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.optimistic_release = True
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.release_requested_at = 1
    escrow.pending_release_amount = 10 * COIN_VALUE
    escrow.challenge_deposit_bps = 500  # 5%
    state.escrows[escrow_id] = escrow
    # Required: 10 * COIN_VALUE * 500 / 10000 = COIN_VALUE / 2
    required = (10 * COIN_VALUE * 500) // MAX_BPS
    payload = {"escrow_id": escrow_id, "reason": "exact deposit", "deposit": required}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CHALLENGE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/challenge_escrow.json",
        "challenge_escrow_deposit_exact_minimum",
        state,
        tx,
    )


# --- dispute_escrow: additional neg tests ---


def test_dispute_escrow_reason_too_long(state_test_group) -> None:
    """Dispute reason exceeding MAX_REASON_LEN must be rejected."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "x" * (MAX_REASON_LEN + 1)}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_reason_too_long",
        state,
        tx,
    )


def test_dispute_escrow_from_pending_release(state_test_group) -> None:
    """Dispute allowed from PendingRelease state (happy path)."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "dispute from pending release"}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_from_pending_release",
        state,
        tx,
    )


def test_dispute_escrow_payee_can_dispute(state_test_group) -> None:
    """Payee can also initiate a dispute (happy path)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "payee disputes"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.DISPUTE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/dispute_escrow.json",
        "dispute_escrow_payee_can_dispute",
        state,
        tx,
    )


# --- appeal_escrow: additional neg tests ---


def test_appeal_escrow_reason_too_long(state_test_group) -> None:
    """Appeal reason exceeding MAX_REASON_LEN must be rejected."""
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
    payload = {"escrow_id": escrow_id, "reason": "x" * (MAX_REASON_LEN + 1), "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_reason_too_long",
        state,
        tx,
    )


def test_appeal_escrow_duplicate_appeal(state_test_group) -> None:
    """Cannot appeal if an appeal already exists."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    # Mark that an appeal already exists
    escrow.appeal = {"appellant": ALICE, "reason": "first appeal"}
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "second appeal", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_duplicate_appeal",
        state,
        tx,
    )


def test_appeal_escrow_window_expired(state_test_group) -> None:
    """Appeal after timeout_at has been reached must be rejected."""
    state = _base_state()
    # Set block height past the timeout
    state.global_state.block_height = 100
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 50  # Already expired
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "late appeal", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_window_expired",
        state,
        tx,
    )


def test_appeal_escrow_deposit_too_low(state_test_group) -> None:
    """Appeal deposit below MIN_APPEAL_DEPOSIT_BPS-based minimum must be rejected.

    With total_amount=100 COIN, MIN_APPEAL_DEPOSIT_BPS=500 (5%),
    required = 100 * 500 / 10000 = 5 COIN. Providing only 1 fails.
    """
    from tos_spec.config import MIN_APPEAL_DEPOSIT_BPS as APPEAL_BPS
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 100 * COIN_VALUE)
    escrow.total_amount = 100 * COIN_VALUE
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    # Required: 100 * COIN_VALUE * 500 / 10000 = 5 * COIN_VALUE
    payload = {"escrow_id": escrow_id, "reason": "underpaid appeal", "appeal_deposit": 1, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_deposit_too_low",
        state,
        tx,
    )


def test_appeal_escrow_deposit_exact_minimum(state_test_group) -> None:
    """Appeal deposit at exactly the bps-based minimum should succeed."""
    from tos_spec.config import MIN_APPEAL_DEPOSIT_BPS as APPEAL_BPS
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 100 * COIN_VALUE)
    escrow.total_amount = 100 * COIN_VALUE
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=True,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    required = (100 * COIN_VALUE * APPEAL_BPS) // MAX_BPS  # 5 * COIN_VALUE
    payload = {"escrow_id": escrow_id, "reason": "exact appeal", "appeal_deposit": required, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_deposit_exact_minimum",
        state,
        tx,
    )


def test_appeal_escrow_no_arbitration_config(state_test_group) -> None:
    """Appeal rejected when arbitration_config is missing."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.timeout_at = 99999
    # No arbitration_config
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "reason": "no arb config", "appeal_deposit": 2 * COIN_VALUE, "appeal_mode": 1}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.APPEAL_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/appeal_escrow.json",
        "appeal_escrow_no_arbitration_config",
        state,
        tx,
    )


# --- refund_escrow: authorization and state tests ---


def test_refund_escrow_payer_before_timeout(state_test_group) -> None:
    """Payer (non-payee) cannot refund before timeout."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.created_at = 1
    escrow.timeout_blocks = 1000
    # Block height is far before timeout
    state.global_state.block_height = 5
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "too early"}
    # ALICE is the payer, not payee -- should fail because timeout not reached
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_payer_before_timeout",
        state,
        tx,
    )


def test_refund_escrow_payee_from_pending_release(state_test_group) -> None:
    """Payee can refund from PendingRelease state (before timeout)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    escrow.created_at = 1
    escrow.timeout_blocks = 1000
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "payee refund from pending release"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_payee_from_pending_release",
        state,
        tx,
    )


def test_refund_escrow_refunded_state(state_test_group) -> None:
    """Cannot refund an already-refunded escrow (terminal state)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.REFUNDED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "double refund"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_refunded_state",
        state,
        tx,
    )


def test_refund_escrow_released_state(state_test_group) -> None:
    """Cannot refund a released escrow (terminal state)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RELEASED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "refund after release"}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_released_state",
        state,
        tx,
    )


def test_refund_escrow_payer_after_timeout(state_test_group) -> None:
    """Payer can refund after timeout from funded state."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.created_at = 1
    escrow.timeout_blocks = 100
    # Block height past timeout
    state.global_state.block_height = 200
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE, "reason": "timeout refund"}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.REFUND_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/refund_escrow.json",
        "refund_escrow_payer_after_timeout",
        state,
        tx,
    )


# --- submit_verdict: additional neg tests ---


def test_submit_verdict_no_arbitration_config(state_test_group) -> None:
    """Verdict requires arbitration config."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    # No arbitration_config
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
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_no_arbitration_config",
        state,
        tx,
    )


def test_submit_verdict_dispute_id_mismatch(state_test_group) -> None:
    """Verdict dispute_id must match escrow's dispute_id if set."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    # Set a specific dispute_id on the escrow
    escrow.dispute_id = _hash(61)
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    # Use a different dispute_id in the verdict payload
    wrong_dispute_id = _hash(99)
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, escrow_id, wrong_dispute_id, 0, 2, 5 * COIN_VALUE, 5 * COIN_VALUE)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": wrong_dispute_id,
        "round": 0,
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_dispute_id_mismatch",
        state,
        tx,
    )


def test_submit_verdict_first_round_nonzero(state_test_group) -> None:
    """First verdict round must be 0 when no prior dispute_round exists."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    # No dispute_round set (None) -- first verdict must use round=0
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    dispute_id = _hash(61)
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, escrow_id, dispute_id, 1, 2, 5 * COIN_VALUE, 5 * COIN_VALUE)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 1,  # Wrong: should be 0
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_first_round_nonzero",
        state,
        tx,
    )


def test_submit_verdict_round_not_incrementing(state_test_group) -> None:
    """Verdict round must be greater than current dispute_round."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    escrow.arbitration_config = ArbitrationConfig(
        mode="single", arbiters=[CAROL], threshold=1, fee_amount=COIN_VALUE, allow_appeal=False,
    )
    escrow.dispute = DisputeInfo(initiator=ALICE, reason="dispute", disputed_at=1, deadline=1000)
    escrow.dispute_round = 2  # Already at round 2
    state.escrows[escrow_id] = escrow
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.arbiters[CAROL] = ArbiterAccount(
        public_key=CAROL, name="ArbiterCarol", status=ArbiterStatus.ACTIVE, stake_amount=1000 * COIN_VALUE,
    )
    dispute_id = _hash(61)
    verdict_msg = _build_verdict_message(CHAIN_ID_DEVNET, escrow_id, dispute_id, 2, 2, 5 * COIN_VALUE, 5 * COIN_VALUE)
    carol_sig = bytes(tos_signer.sign_data(verdict_msg, 4))
    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 2,  # Wrong: must be > 2
        "payer_amount": 5 * COIN_VALUE,
        "payee_amount": 5 * COIN_VALUE,
        "signatures": [{"arbiter_pubkey": CAROL, "signature": carol_sig, "timestamp": _NOW}],
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.SUBMIT_VERDICT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/submit_verdict.json",
        "submit_verdict_round_not_incrementing",
        state,
        tx,
    )


# --- deposit_escrow: additional state tests ---


def test_deposit_escrow_challenged_state(state_test_group) -> None:
    """Cannot deposit to a challenged escrow."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CHALLENGED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_challenged_state",
        state,
        tx,
    )


def test_deposit_escrow_pending_release_state(state_test_group) -> None:
    """Cannot deposit to a pending_release escrow."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.PENDING_RELEASE
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_pending_release_state",
        state,
        tx,
    )


def test_deposit_escrow_refunded_state(state_test_group) -> None:
    """Cannot deposit to a refunded escrow."""
    state = _base_state()
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.REFUNDED
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.DEPOSIT_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/deposit_escrow.json",
        "deposit_escrow_refunded_state",
        state,
        tx,
    )


# --- release_escrow: additional state tests ---


def test_release_escrow_resolved_state(state_test_group) -> None:
    """Cannot release from a resolved escrow."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.RESOLVED
    escrow.optimistic_release = True
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_resolved_state",
        state,
        tx,
    )


def test_release_escrow_created_state(state_test_group) -> None:
    """Cannot release from a created (not yet funded) escrow."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    escrow_id = _hash(60)
    escrow = _funded_escrow(escrow_id, ALICE, BOB, 10 * COIN_VALUE)
    escrow.status = EscrowStatus.CREATED
    escrow.optimistic_release = True
    state.escrows[escrow_id] = escrow
    payload = {"escrow_id": escrow_id, "amount": 5 * COIN_VALUE}
    tx = _mk_escrow_tx(BOB, nonce=0, tx_type=TransactionType.RELEASE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/release_escrow.json",
        "release_escrow_created_state",
        state,
        tx,
    )


# --- create_escrow: committee mode valid happy path ---


def test_create_escrow_committee_valid(state_test_group) -> None:
    """Create escrow with valid committee arbitration config."""
    state = _base_state()
    payload = {
        "task_id": "task_committee",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": {
            "mode": "committee",
            "arbiters": [CAROL, DAVE],
            "threshold": 2,
            "fee_amount": COIN_VALUE,
            "allow_appeal": True,
        },
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_committee_valid",
        state,
        tx,
    )


# --- create_escrow: timeout boundary exact minimum ---


def test_create_escrow_timeout_exact_min(state_test_group) -> None:
    """Create escrow with timeout_blocks at exactly MIN_TIMEOUT_BLOCKS (should pass)."""
    state = _base_state()
    payload = {
        "task_id": "task_min_timeout",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_timeout_exact_min",
        state,
        tx,
    )


# --- create_escrow: bps boundary at MAX_BPS ---


def test_create_escrow_bps_at_max(state_test_group) -> None:
    """Create escrow with challenge_deposit_bps at exactly MAX_BPS (should pass)."""
    state = _base_state()
    payload = {
        "task_id": "task_bps_max",
        "provider": BOB,
        "amount": 5 * COIN_VALUE,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS * 10,
        "challenge_window": 100,
        "challenge_deposit_bps": MAX_BPS,
        "optimistic_release": False,
    }
    tx = _mk_escrow_tx(ALICE, nonce=5, tx_type=TransactionType.CREATE_ESCROW, payload=payload, fee=100_000)
    state_test_group(
        "transactions/escrow/create_escrow.json",
        "create_escrow_bps_at_max",
        state,
        tx,
    )
