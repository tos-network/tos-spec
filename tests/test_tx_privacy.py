"""Privacy tx fixtures (uno_transfers, shield_transfers, unshield_transfers)."""

from __future__ import annotations

from tos_spec.config import (
    CHAIN_ID_DEVNET,
    COIN_VALUE,
    MAX_TRANSFER_COUNT,
    MIN_SHIELD_TOS_AMOUNT,
)
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


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=1000 * COIN_VALUE, nonce=5
    )
    return state


def _mk_uno_transfer(
    sender: bytes, nonce: int, destination: bytes, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.UNO_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(0),
                    "destination": destination,
                    "commitment": _hash(10),
                    "sender_handle": _hash(11),
                    "receiver_handle": _hash(12),
                    "ct_validity_proof": bytes([0xAA]) * 160,
                }
            ]
        },
        fee=fee,
        fee_type=FeeType.UNO,
        nonce=nonce,
        source_commitments=[_hash(20)],
        range_proof=bytes([0xBB]) * 64,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_shield_transfer(
    sender: bytes, nonce: int, destination: bytes, amount: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.SHIELD_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(0),
                    "destination": destination,
                    "amount": amount,
                    "commitment": _hash(10),
                    "receiver_handle": _hash(12),
                    "proof": bytes([0xCC]) * 96,
                }
            ]
        },
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        source_commitments=[_hash(20)],
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_unshield_transfer(
    sender: bytes, nonce: int, destination: bytes, amount: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.UNSHIELD_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(0),
                    "destination": destination,
                    "amount": amount,
                    "commitment": _hash(10),
                    "sender_handle": _hash(11),
                    "ct_validity_proof": bytes([0xDD]) * 160,
                }
            ]
        },
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        source_commitments=[_hash(20)],
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- uno_transfers specs ---


def test_uno_transfer_success(state_test_group) -> None:
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_uno_transfer(ALICE, nonce=5, destination=BOB, fee=0)
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_success",
        state,
        tx,
    )


def test_uno_transfer_self(state_test_group) -> None:
    state = _base_state()
    tx = _mk_uno_transfer(ALICE, nonce=5, destination=ALICE, fee=0)
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_self",
        state,
        tx,
    )


# --- shield_transfers specs ---


def test_shield_transfer_success(state_test_group) -> None:
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        ALICE, nonce=5, destination=BOB, amount=MIN_SHIELD_TOS_AMOUNT, fee=100_000
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_success",
        state,
        tx,
    )


def test_shield_transfer_below_minimum(state_test_group) -> None:
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        ALICE, nonce=5, destination=BOB, amount=COIN_VALUE, fee=100_000
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_below_minimum",
        state,
        tx,
    )


# --- unshield_transfers specs ---


def test_unshield_transfer_success(state_test_group) -> None:
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_unshield_transfer(
        ALICE, nonce=5, destination=BOB, amount=5 * COIN_VALUE, fee=100_000
    )
    state_test_group(
        "transactions/privacy/unshield_transfers.json",
        "unshield_transfer_success",
        state,
        tx,
    )


def test_shield_transfer_zero_amount(state_test_group) -> None:
    """Shield 0 TOS."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        ALICE, nonce=5, destination=BOB, amount=0, fee=100_000
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_zero_amount",
        state,
        tx,
    )


def test_unshield_transfer_self(state_test_group) -> None:
    """Unshield to self."""
    state = _base_state()
    tx = _mk_unshield_transfer(
        ALICE, nonce=5, destination=ALICE, amount=5 * COIN_VALUE, fee=100_000
    )
    state_test_group(
        "transactions/privacy/unshield_transfers.json",
        "unshield_transfer_self",
        state,
        tx,
    )


def test_uno_transfer_insufficient_balance(state_test_group) -> None:
    """UNO transfer from account with zero balance."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    # Account with zero balance
    state.accounts[ALICE] = AccountState(address=ALICE, balance=0, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_uno_transfer(ALICE, nonce=5, destination=BOB, fee=0)
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_insufficient_balance",
        state,
        tx,
    )


def test_unshield_transfer_zero_amount(state_test_group) -> None:
    """Unshield with zero amount."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_unshield_transfer(
        ALICE, nonce=5, destination=BOB, amount=0, fee=100_000
    )
    state_test_group(
        "transactions/privacy/unshield_transfers.json",
        "unshield_transfer_zero_amount",
        state,
        tx,
    )


def test_shield_transfer_insufficient_balance(state_test_group) -> None:
    """Shield transfer exceeding sender balance."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    # Account with only 1 TOS, trying to shield 100 TOS (MIN_SHIELD_TOS_AMOUNT)
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=COIN_VALUE, nonce=5
    )
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        ALICE, nonce=5, destination=BOB, amount=MIN_SHIELD_TOS_AMOUNT, fee=100_000
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_insufficient_balance",
        state,
        tx,
    )


# --- boundary value tests ---


def test_shield_transfer_exact_minimum(state_test_group) -> None:
    """Shield exactly MIN_SHIELD_TOS_AMOUNT (100 TOS). Privacy stub returns INVALID_FORMAT."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        ALICE, nonce=5, destination=BOB, amount=MIN_SHIELD_TOS_AMOUNT, fee=100_000
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_exact_minimum",
        state,
        tx,
    )


def test_uno_transfer_zero_amount(state_test_group) -> None:
    """UNO transfer with zero-valued commitment."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.UNO_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(0),
                    "destination": BOB,
                    "commitment": bytes(32),  # zero commitment
                    "sender_handle": _hash(11),
                    "receiver_handle": _hash(12),
                    "ct_validity_proof": bytes([0xAA]) * 160,
                }
            ]
        },
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        source_commitments=[_hash(20)],
        range_proof=bytes([0xBB]) * 64,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_zero_amount",
        state,
        tx,
    )


# ===================================================================
# UNO transfer boundary tests
# ===================================================================


def test_uno_transfer_empty_list(state_test_group) -> None:
    """UNO transfer with empty transfers list.

    Rust: TransferCount error.
    """
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.UNO_TRANSFERS,
        payload={"transfers": []},
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        source_commitments=[_hash(20)],
        range_proof=bytes([0xBB]) * 64,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_empty_list",
        state,
        tx,
    )


def test_uno_transfer_max_count_exceeded(state_test_group) -> None:
    """UNO transfers exceeding MAX_TRANSFER_COUNT (500).

    Rust: TransferCount error.
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    transfers = [
        {
            "asset": _hash(0),
            "destination": BOB,
            "commitment": _hash(10),
            "sender_handle": _hash(11),
            "receiver_handle": _hash(12),
            "ct_validity_proof": bytes([0xAA]) * 160,
        }
        for _ in range(MAX_TRANSFER_COUNT + 1)
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.UNO_TRANSFERS,
        payload={"transfers": transfers},
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        source_commitments=[_hash(20)],
        range_proof=bytes([0xBB]) * 64,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_max_count_exceeded",
        state,
        tx,
    )


# ===================================================================
# Shield transfer boundary tests
# ===================================================================


def test_shield_transfer_empty_list(state_test_group) -> None:
    """Shield transfers with empty list.

    Rust: TransferCount error.
    """
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.SHIELD_TRANSFERS,
        payload={"transfers": []},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_empty_list",
        state,
        tx,
    )


def test_shield_transfer_max_count_exceeded(state_test_group) -> None:
    """Shield transfers exceeding MAX_TRANSFER_COUNT (500).

    Rust: TransferCount error.
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    transfers = [
        {
            "asset": _hash(0),
            "destination": BOB,
            "amount": MIN_SHIELD_TOS_AMOUNT,
            "commitment": _hash(10),
            "receiver_handle": _hash(12),
            "proof": bytes([0xCC]) * 96,
        }
        for _ in range(MAX_TRANSFER_COUNT + 1)
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.SHIELD_TRANSFERS,
        payload={"transfers": transfers},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_max_count_exceeded",
        state,
        tx,
    )


def test_shield_transfer_non_tos_asset(state_test_group) -> None:
    """Shield transfer with non-TOS asset.

    Rust: "Shield transfers only support TOS asset".
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.SHIELD_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(1),  # Non-TOS asset
                    "destination": BOB,
                    "amount": MIN_SHIELD_TOS_AMOUNT,
                    "commitment": _hash(10),
                    "receiver_handle": _hash(12),
                    "proof": bytes([0xCC]) * 96,
                }
            ]
        },
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_non_tos_asset",
        state,
        tx,
    )


# ===================================================================
# Unshield transfer boundary tests
# ===================================================================


def test_unshield_transfer_empty_list(state_test_group) -> None:
    """Unshield transfers with empty list.

    Rust: TransferCount error.
    """
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.UNSHIELD_TRANSFERS,
        payload={"transfers": []},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/unshield_transfers.json",
        "unshield_transfer_empty_list",
        state,
        tx,
    )


def test_unshield_transfer_max_count_exceeded(state_test_group) -> None:
    """Unshield transfers exceeding MAX_TRANSFER_COUNT (500).

    Rust: TransferCount error.
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    transfers = [
        {
            "asset": _hash(0),
            "destination": BOB,
            "amount": 5 * COIN_VALUE,
            "commitment": _hash(10),
            "sender_handle": _hash(11),
            "ct_validity_proof": bytes([0xDD]) * 160,
        }
        for _ in range(MAX_TRANSFER_COUNT + 1)
    ]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.UNSHIELD_TRANSFERS,
        payload={"transfers": transfers},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/unshield_transfers.json",
        "unshield_transfer_max_count_exceeded",
        state,
        tx,
    )


# ===================================================================
# UNO fee type tests
# ===================================================================


def test_uno_fee_type_invalid_tx(state_test_group) -> None:
    """UNO fee type on a non-UNO tx type.

    Rust: InvalidFormat.
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.SHIELD_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(0),
                    "destination": BOB,
                    "amount": MIN_SHIELD_TOS_AMOUNT,
                    "commitment": _hash(10),
                    "receiver_handle": _hash(12),
                    "proof": bytes([0xCC]) * 96,
                }
            ]
        },
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "uno_fee_type_invalid_tx",
        state,
        tx,
    )


def test_uno_fee_nonzero(state_test_group) -> None:
    """UNO fee type with non-zero fee value.

    Rust: InvalidFee(0, self.fee).
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.UNO_TRANSFERS,
        payload={
            "transfers": [
                {
                    "asset": _hash(0),
                    "destination": BOB,
                    "commitment": _hash(10),
                    "sender_handle": _hash(11),
                    "receiver_handle": _hash(12),
                    "ct_validity_proof": bytes([0xAA]) * 160,
                }
            ]
        },
        fee=1000,
        fee_type=FeeType.UNO,
        nonce=5,
        source_commitments=[_hash(20)],
        range_proof=bytes([0xBB]) * 64,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_fee_nonzero",
        state,
        tx,
    )
