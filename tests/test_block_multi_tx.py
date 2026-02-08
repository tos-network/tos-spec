"""L2 block processing fixtures (multi-tx atomic semantics)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.test_accounts import ALICE, BOB, CAROL
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)
from tos_spec.config import EXTRA_DATA_LIMIT_SIZE


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


FEE_MIN = 100_000


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.global_state.block_height = 1
    state.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    return state


def _mk_transfer(
    sender: bytes, receiver: bytes, nonce: int, amount: int, *, fee: int = FEE_MIN
) -> Transaction:
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


def _mk_transfer_energy_fee(sender: bytes, receiver: bytes, nonce: int, amount: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=amount)],
        fee=0,
        fee_type=FeeType.ENERGY,
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


def test_block_reject_atomic_on_second_tx_nonce_too_low(block_test_group) -> None:
    """Second tx repeats nonce; entire block must be rejected."""
    state = _base_state()
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    # After tx1, sender nonce becomes 6; repeating nonce=5 is NONCE_TOO_LOW.
    tx2 = _mk_transfer(ALICE, BOB, nonce=5, amount=20_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_nonce_too_low",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_insufficient_balance(block_test_group) -> None:
    """Second tx becomes unaffordable after the first; entire block must be rejected."""
    state = _base_state()
    # After tx1, ALICE has exactly enough to pay tx2.fee but not (fee + amount).
    state.accounts[ALICE].balance = 350_000
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=150_000, fee=FEE_MIN)
    tx2 = _mk_transfer(ALICE, BOB, nonce=6, amount=1, fee=FEE_MIN)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_insufficient_balance",
        state,
        [tx1, tx2],
    )


def test_block_multi_sender_interleaved_success(block_test_group) -> None:
    """Two senders interleaved: strict nonce is tracked per-sender."""
    state = _base_state()
    state.accounts[BOB].balance = 500_000
    state.accounts[BOB].nonce = 1

    tx1 = _mk_transfer(ALICE, CAROL, nonce=5, amount=10_000)
    tx2 = _mk_transfer(BOB, CAROL, nonce=1, amount=20_000)
    tx3 = _mk_transfer(ALICE, CAROL, nonce=6, amount=30_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_multi_sender_interleaved_success",
        state,
        [tx1, tx2, tx3],
    )


def _mk_burn(sender: bytes, nonce: int, amount: int, *, fee: int = FEE_MIN) -> Transaction:
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


def test_block_burn_then_transfer_success(block_test_group) -> None:
    """Ensure per-block burned accounting and multi-tx ordering works."""
    state = _base_state()
    burn = _mk_burn(ALICE, nonce=5, amount=100_000, fee=FEE_MIN)
    xfer = _mk_transfer(ALICE, BOB, nonce=6, amount=200_000, fee=FEE_MIN)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_burn_then_transfer_success",
        state,
        [burn, xfer],
    )


def test_block_reject_sender_not_found(block_test_group) -> None:
    """Block is rejected if a sender is not present in pre_state."""
    state = _base_state()
    state.accounts.pop(BOB, None)  # remove bob so bob-as-sender is missing
    tx1 = _mk_transfer(BOB, ALICE, nonce=0, amount=1)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_sender_not_found",
        state,
        [tx1],
    )


def test_block_energy_fee_consumed_success(block_test_group) -> None:
    """ENERGY fee transfers consume 1 energy each on success."""
    state = _base_state()
    state.accounts[ALICE].energy = 2
    # ENERGY fee requires fee=0 and still requires balance for transfer amount.
    state.accounts[ALICE].balance = 1_000_000

    tx1 = _mk_transfer_energy_fee(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = _mk_transfer_energy_fee(ALICE, BOB, nonce=6, amount=10_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_energy_fee_consumed_success",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_insufficient_energy_fee(block_test_group) -> None:
    """Second ENERGY-fee tx fails due to insufficient energy; entire block is rejected."""
    state = _base_state()
    state.accounts[ALICE].energy = 1
    state.accounts[ALICE].balance = 1_000_000

    tx1 = _mk_transfer_energy_fee(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = _mk_transfer_energy_fee(ALICE, BOB, nonce=6, amount=10_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_insufficient_energy_fee",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_rolls_back_recipient_credit(block_test_group) -> None:
    """Recipient credit from tx1 must be rolled back if tx2 is invalid."""
    state = _base_state()
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=200_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=7, amount=1)  # nonce too high after tx1
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_rolls_back_recipient_credit",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_third_tx_sender_nonce_mismatch(block_test_group) -> None:
    """Failure on the 3rd tx must roll back earlier successful txs."""
    state = _base_state()
    state.accounts[BOB].balance = 500_000
    state.accounts[BOB].nonce = 0

    tx1 = _mk_transfer(ALICE, CAROL, nonce=5, amount=10_000)
    tx2 = _mk_transfer(BOB, CAROL, nonce=0, amount=20_000)
    tx3 = _mk_transfer(ALICE, CAROL, nonce=5, amount=30_000)  # repeats nonce, too low
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_third_tx_sender_nonce_mismatch",
        state,
        [tx1, tx2, tx3],
    )


def test_block_multi_sender_success_two_senders(block_test_group) -> None:
    """Two independent senders both succeed in the same block."""
    state = _base_state()
    state.accounts[BOB].balance = 1_000_000
    state.accounts[BOB].nonce = 0

    tx1 = _mk_transfer(ALICE, CAROL, nonce=5, amount=10_000)
    tx2 = _mk_transfer(BOB, CAROL, nonce=0, amount=20_000)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_multi_sender_success_two_senders",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_sender_nonce_too_high(block_test_group) -> None:
    """Second tx from a different sender has nonce too high; entire block rejected."""
    state = _base_state()
    state.accounts[BOB].balance = 1_000_000
    state.accounts[BOB].nonce = 0

    tx1 = _mk_transfer(ALICE, CAROL, nonce=5, amount=10_000)
    tx2 = _mk_transfer(BOB, CAROL, nonce=2, amount=20_000)  # strict nonce expects 0
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_sender_nonce_too_high",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_sender_insufficient_balance(block_test_group) -> None:
    """Second tx fails insufficient balance (amount+fee); entire block rejected."""
    state = _base_state()
    # Ensure fee is affordable but amount+fee is not.
    state.accounts[BOB].balance = FEE_MIN
    state.accounts[BOB].nonce = 0

    tx1 = _mk_transfer(ALICE, CAROL, nonce=5, amount=10_000)
    tx2 = _mk_transfer(BOB, CAROL, nonce=0, amount=1, fee=FEE_MIN)
    # BOB cannot afford amount(1) + fee(100k) when balance==fee (checks total spending).
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_sender_insufficient_balance",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_energy_fee_nonzero(block_test_group) -> None:
    """ENERGY fee must be zero; violation rejects block and rolls back tx1."""
    state = _base_state()
    # Ensure we hit the fee validation rather than failing earlier on energy.
    state.accounts[ALICE].energy = 2
    state.accounts[ALICE].balance = 1_000_000

    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000, fee=FEE_MIN)
    tx2 = _mk_transfer_energy_fee(ALICE, BOB, nonce=6, amount=10_000)
    tx2.fee = 1  # invalid for ENERGY fee type
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_energy_fee_nonzero",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_self_transfer(block_test_group) -> None:
    """Second tx is self-transfer; entire block is rejected and tx1 is rolled back."""
    state = _base_state()
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = _mk_transfer(ALICE, ALICE, nonce=6, amount=1)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_self_transfer",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_invalid_transfer_extra_data(block_test_group) -> None:
    """Second tx has extra_data larger than the per-transfer limit; entire block is rejected."""
    state = _base_state()
    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[
            TransferPayload(
                asset=_hash(0),
                destination=BOB,
                amount=1,
                extra_data=b"x" * (EXTRA_DATA_LIMIT_SIZE + 1),
            )
        ],
        fee=FEE_MIN,
        fee_type=FeeType.TOS,
        nonce=6,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_invalid_transfer_extra_data",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_receiver_balance_overflow(block_test_group) -> None:
    """Second tx overflows receiver balance (apply-time error); entire block is rejected."""
    U64_MAX = (1 << 64) - 1
    state = _base_state()
    # Make BOB overflow on receiving.
    state.accounts[BOB].balance = U64_MAX - 5
    # Ensure ALICE can cover amount+fee.
    state.accounts[ALICE].balance = 1_000_000

    tx1 = _mk_transfer(ALICE, CAROL, nonce=5, amount=10_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=6, amount=10, fee=FEE_MIN)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_receiver_balance_overflow",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_total_burned_overflow(block_test_group) -> None:
    """Second tx overflows total_burned (apply-time error); entire block is rejected."""
    U64_MAX = (1 << 64) - 1
    state = _base_state()
    state.global_state.total_burned = U64_MAX - 1
    state.accounts[ALICE].balance = 1_000_000

    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = _mk_burn(ALICE, nonce=6, amount=2, fee=FEE_MIN)
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_total_burned_overflow",
        state,
        [tx1, tx2],
    )


def test_block_reject_atomic_on_second_tx_burn_energy_fee(block_test_group) -> None:
    """Energy fee is invalid for burn; entire block is rejected and tx1 is rolled back."""
    state = _base_state()
    state.accounts[ALICE].balance = 1_000_000

    tx1 = _mk_transfer(ALICE, BOB, nonce=5, amount=10_000)
    tx2 = _mk_burn(ALICE, nonce=6, amount=1, fee=0)
    tx2.fee_type = FeeType.ENERGY
    block_test_group(
        "transactions/block/multi_tx.json",
        "block_reject_atomic_on_second_tx_burn_energy_fee",
        state,
        [tx1, tx2],
    )
