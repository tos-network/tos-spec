"""Core tx fixtures (nonce + failed-tx semantics)."""

from __future__ import annotations

from tos_spec.config import (
    CHAIN_ID_DEVNET,
    CHAIN_ID_TESTNET,
    MAX_NONCE_GAP,
    MAX_TRANSFER_COUNT,
)
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


def test_transfer_exact_balance(state_test) -> None:
    """Sender balance equals (sum(outputs) + fee)."""
    state = _base_state()
    amount = 900_000
    fee = 100_000
    state.accounts[ALICE].balance = amount + fee
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=amount, fee=fee)
    state_test("transfer_exact_balance", state, tx)


def test_transfer_insufficient_balance_after_fee(state_test) -> None:
    """Sender balance covers outputs but not (outputs + fee)."""
    state = _base_state()
    amount = 900_000
    fee = 100_000
    state.accounts[ALICE].balance = amount + fee - 1
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=amount, fee=fee)
    state_test("transfer_insufficient_balance_after_fee", state, tx)


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


def test_transfer_creates_new_account(state_test) -> None:
    """Transfer creates a new receiver account if it does not exist."""
    from tos_spec.test_accounts import DAVE

    state = _base_state()
    # DAVE is not in pre-state.
    tx = _mk_tx(ALICE, DAVE, nonce=5, amount=100_000, fee=100_000)
    state_test("transfer_creates_new_account", state, tx)


def test_transfer_sender_missing(state_test) -> None:
    """Sender account missing should fail validation."""
    state = _base_state()
    state.accounts.pop(ALICE, None)
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=100_000, fee=100_000)
    state_test("transfer_sender_missing", state, tx)


def test_transfer_fee_zero_allowed(state_test) -> None:
    """Transfers allow fee=0 (no min-fee requirement)."""
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=100_000, fee=0)
    state_test("transfer_fee_zero_allowed", state, tx)


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


def test_nonce_too_high_strict(state_test) -> None:
    """Strict nonce: tx.nonce > sender.nonce (apply_tx enforces strict equality)."""
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=6, amount=100_000, fee=100_000)
    state_test("nonce_too_high_strict", state, tx)


# ===================================================================
# Overflow / boundary tests
# ===================================================================

U64_MAX = (1 << 64) - 1


def test_transfer_amount_overflow(state_test) -> None:
    """Sum of multiple transfer amounts overflows u64.

    Two transfers each near u64_max / 2 will overflow when summed.
    """
    state = _base_state()
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=U64_MAX, nonce=5
    )
    half = (U64_MAX // 2) + 1
    transfers = [
        TransferPayload(asset=_hash(0), destination=BOB, amount=half),
        TransferPayload(asset=_hash(0), destination=BOB, amount=half),
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=transfers,
        fee=0,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("transfer_amount_overflow", state, tx)


def test_transfer_amount_plus_fee_overflow(state_test) -> None:
    """Transfer amount + fee overflows u64.

    A single transfer near u64_max combined with a non-zero fee will overflow.
    """
    state = _base_state()
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=U64_MAX, nonce=5
    )
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=U64_MAX)],
        fee=1,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("transfer_amount_plus_fee_overflow", state, tx)


def test_burn_zero_amount(state_test) -> None:
    """Burn with amount=0 should be rejected."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"amount": 0, "asset": _hash(0)},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("burn_zero_amount", state, tx)


def test_burn_amount_exceeds_balance(state_test) -> None:
    """Burn amount exceeds sender balance."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"amount": 2_000_000, "asset": _hash(0)},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("burn_amount_exceeds_balance", state, tx)


# ===================================================================
# U64 overflow tests (apply-phase)
# ===================================================================


def test_transfer_receiver_balance_overflow(state_test) -> None:
    """Transfer causes receiver.balance to overflow u64 max."""
    state = _base_state()
    state.accounts[ALICE] = AccountState(address=ALICE, balance=U64_MAX, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=U64_MAX - 50, nonce=0)
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=100, fee=100_000)
    state_test("transfer_receiver_balance_overflow", state, tx)


def test_burn_total_burned_overflow(state_test) -> None:
    """Burn causes global_state.total_burned to overflow u64 max."""
    state = _base_state()
    state.accounts[ALICE] = AccountState(address=ALICE, balance=U64_MAX, nonce=5)
    state.global_state.total_burned = U64_MAX - 50
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"amount": 100, "asset": _hash(0)},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("burn_total_burned_overflow", state, tx)


# ===================================================================
# Chain ID validation tests
# ===================================================================


def test_chain_id_mismatch(state_test) -> None:
    """Transaction chain_id does not match network chain_id.

    Rust: VerificationError::InvalidChainId.
    """
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_TESTNET,  # Wrong: state uses DEVNET
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=100_000)],
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("chain_id_mismatch", state, tx)


# ===================================================================
# Nonce boundary tests
# ===================================================================


def test_nonce_exact_match(state_test) -> None:
    """Nonce exactly matches sender nonce (happy path)."""
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5, amount=100_000, fee=100_000)
    state_test("nonce_exact_match", state, tx)


def test_nonce_gap_max(state_test) -> None:
    """Nonce at exactly MAX_NONCE_GAP (64) above sender nonce.

    nonce = 5 + 64 = 69. Should be rejected (strict nonce in apply_tx).
    """
    state = _base_state()
    tx = _mk_tx(ALICE, BOB, nonce=5 + MAX_NONCE_GAP, amount=100_000, fee=100_000)
    state_test("nonce_gap_max", state, tx)


# ===================================================================
# Fee validation tests
# ===================================================================


def test_insufficient_fee(state_test) -> None:
    """Sender balance is less than the fee.

    Rust: InsufficientFunds. Python: INSUFFICIENT_FEE pre-check.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=50, nonce=0)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_tx(ALICE, BOB, nonce=0, amount=10, fee=100)
    state_test("insufficient_fee", state, tx)


def test_fee_exact_balance(state_test) -> None:
    """Sender has exactly enough for amount + fee (boundary success)."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=200_000, nonce=0)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_tx(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    state_test("fee_exact_balance", state, tx)


def test_fee_exceeds_balance_after_amount(state_test) -> None:
    """Sender can pay amount but not amount + fee."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=150_000, nonce=0)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_tx(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    state_test("fee_exceeds_balance_after_amount", state, tx)


# ===================================================================
# Sender not found
# ===================================================================


def test_sender_not_found(state_test) -> None:
    """Sender address not in state."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    # ALICE not added to state
    tx = _mk_tx(ALICE, BOB, nonce=0, amount=100, fee=100)
    state_test("sender_not_found", state, tx)


# ===================================================================
# Burn boundary tests
# ===================================================================


def test_burn_amount_plus_fee_overflow(state_test) -> None:
    """Burn amount + fee overflows u64.

    Rust: fee.checked_add(amount) fails -> InvalidFormat.
    """
    state = _base_state()
    state.accounts[ALICE] = AccountState(address=ALICE, balance=U64_MAX, nonce=5)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"amount": U64_MAX, "asset": _hash(0)},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("burn_amount_plus_fee_overflow", state, tx)


def test_burn_success(state_test) -> None:
    """Successful burn with sufficient balance."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"amount": 100_000, "asset": _hash(0)},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("burn_success", state, tx)


# ===================================================================
# Energy fee type tests
# ===================================================================


def test_energy_fee_type_nonzero_fee(state_test) -> None:
    """Energy fee type with non-zero fee value.

    Rust: InvalidFee(0, self.fee).
    """
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=100)],
        fee=1000,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("energy_fee_type_nonzero_fee", state, tx)


def test_energy_fee_type_invalid_tx(state_test) -> None:
    """Energy fee type on a non-transfer tx (burn).

    Rust: InvalidFormat.
    """
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"amount": 100_000, "asset": _hash(0)},
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("energy_fee_type_invalid_tx", state, tx)


def test_transfer_max_count_exact(state_test) -> None:
    """Exactly MAX_TRANSFER_COUNT (500) recipients: should succeed."""
    state = _base_state()
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=1_000_000_000, nonce=5
    )
    transfers = [
        TransferPayload(asset=_hash(0), destination=BOB, amount=1)
        for _ in range(MAX_TRANSFER_COUNT)
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=transfers,
        fee=3_000_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test("transfer_max_count_exact", state, tx)
