"""Privacy tx fixtures (uno_transfers, shield_transfers, unshield_transfers)."""

from __future__ import annotations

from tos_spec.config import COIN_VALUE, MIN_SHIELD_TOS_AMOUNT
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
    sender = _addr(1)
    state = ChainState(network_chain_id=0)
    state.accounts[sender] = AccountState(
        address=sender, balance=1000 * COIN_VALUE, nonce=5
    )
    return state


def _mk_uno_transfer(
    sender: bytes, nonce: int, destination: bytes, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
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
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def _mk_shield_transfer(
    sender: bytes, nonce: int, destination: bytes, amount: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
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
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def _mk_unshield_transfer(
    sender: bytes, nonce: int, destination: bytes, amount: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
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
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


# --- uno_transfers specs ---


def test_uno_transfer_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    state.accounts[receiver] = AccountState(address=receiver, balance=0, nonce=0)
    tx = _mk_uno_transfer(sender, nonce=5, destination=receiver, fee=0)
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_success",
        state,
        tx,
    )


def test_uno_transfer_self(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    tx = _mk_uno_transfer(sender, nonce=5, destination=sender, fee=0)
    state_test_group(
        "transactions/privacy/uno_transfers.json",
        "uno_transfer_self",
        state,
        tx,
    )


# --- shield_transfers specs ---


def test_shield_transfer_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    state.accounts[receiver] = AccountState(address=receiver, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        sender, nonce=5, destination=receiver, amount=MIN_SHIELD_TOS_AMOUNT, fee=1_000
    )
    state_test_group(
        "transactions/privacy/shield_transfers.json",
        "shield_transfer_success",
        state,
        tx,
    )


def test_shield_transfer_below_minimum(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    receiver = _addr(2)
    state.accounts[receiver] = AccountState(address=receiver, balance=0, nonce=0)
    tx = _mk_shield_transfer(
        sender, nonce=5, destination=receiver, amount=COIN_VALUE, fee=1_000
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
    sender = _addr(1)
    receiver = _addr(2)
    state.accounts[receiver] = AccountState(address=receiver, balance=0, nonce=0)
    tx = _mk_unshield_transfer(
        sender, nonce=5, destination=receiver, amount=5 * COIN_VALUE, fee=1_000
    )
    state_test_group(
        "transactions/privacy/unshield_transfers.json",
        "unshield_transfer_success",
        state,
        tx,
    )
