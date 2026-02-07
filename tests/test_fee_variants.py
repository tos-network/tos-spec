"""Fee variant fixtures — test fee_type/fee validation across tx types."""

from __future__ import annotations

import tos_signer
from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE
from tos_spec.test_accounts import ALICE, BOB
from tos_spec.types import (
    AccountState,
    ChainState,
    EnergyPayload,
    EnergyResource,
    FeeType,
    FreezeRecord,
    FreezeDuration,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _hash(n: int) -> bytes:
    return bytes([n]) + bytes(31)


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=10 * COIN_VALUE, nonce=5
    )
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


# ===================================================================
# Group 1: Wrong fee_type tests
# ===================================================================


def test_transfer_energy_fee_zero(state_test_group) -> None:
    """TRANSFERS with FeeType.ENERGY and fee=0 — should succeed.

    Daemon computes energy cost from wire size. Sender needs enough
    frozen TOS to have sufficient energy for the transaction.
    """
    state = _base_state()
    # Give ALICE frozen TOS so she has energy for the tx
    state.accounts[ALICE].frozen = 100 * COIN_VALUE
    state.energy_resources[ALICE] = EnergyResource(
        frozen_tos=100 * COIN_VALUE, energy=1_000_000,
        freeze_records=[FreezeRecord(
            amount=100 * COIN_VALUE, energy_gained=1_000_000,
            freeze_height=0, unlock_height=99999,
        )],
    )
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=100_000)],
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "transfer_energy_fee_zero",
        state,
        tx,
    )


def test_transfer_energy_fee_nonzero(state_test_group) -> None:
    """TRANSFERS with FeeType.ENERGY and fee=100_000 — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=100_000)],
        fee=100_000,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "transfer_energy_fee_nonzero",
        state,
        tx,
    )


def test_burn_energy_fee(state_test_group) -> None:
    """BURN with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD (energy fee only for transfers)."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": 100_000},
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "burn_energy_fee",
        state,
        tx,
    )


def test_burn_uno_fee(state_test_group) -> None:
    """BURN with FeeType.UNO — should FAIL: INVALID_PAYLOAD (uno fee only for uno_transfers)."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": 100_000},
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "burn_uno_fee",
        state,
        tx,
    )


def test_freeze_energy_fee(state_test_group) -> None:
    """ENERGY (freeze) with FeeType.ENERGY and fee=0 — should FAIL: energy fee only for transfers."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos",
            amount=COIN_VALUE,
            duration=FreezeDuration(days=7),
        ),
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "freeze_energy_fee",
        state,
        tx,
    )


def test_freeze_uno_fee(state_test_group) -> None:
    """ENERGY (freeze) with FeeType.UNO — should FAIL: uno fee only for uno_transfers."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos",
            amount=COIN_VALUE,
            duration=FreezeDuration(days=7),
        ),
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "freeze_uno_fee",
        state,
        tx,
    )


def test_escrow_energy_fee(state_test_group) -> None:
    """CREATE_ESCROW with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.CREATE_ESCROW,
        payload={
            "task_id": "test-task",
            "payee": BOB,
            "amount": COIN_VALUE,
            "asset": _hash(0),
            "timeout_blocks": 100,
        },
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "escrow_energy_fee",
        state,
        tx,
    )


def test_escrow_uno_fee(state_test_group) -> None:
    """CREATE_ESCROW with FeeType.UNO — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.CREATE_ESCROW,
        payload={
            "task_id": "test-task",
            "payee": BOB,
            "amount": COIN_VALUE,
            "asset": _hash(0),
            "timeout_blocks": 100,
        },
        fee=0,
        fee_type=FeeType.UNO,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "escrow_uno_fee",
        state,
        tx,
    )


def test_arbitration_energy_fee(state_test_group) -> None:
    """REGISTER_ARBITER with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.REGISTER_ARBITER,
        payload={
            "name": "arbiter-test",
            "expertise": [1],
            "fee_basis_points": 500,
            "min_escrow_value": COIN_VALUE,
            "max_escrow_value": 100 * COIN_VALUE,
        },
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "arbitration_energy_fee",
        state,
        tx,
    )


def test_kyc_energy_fee(state_test_group) -> None:
    """SET_KYC with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.SET_KYC,
        payload={
            "target": BOB,
            "level": 7,
            "data_hash": _hash(1),
        },
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "kyc_energy_fee",
        state,
        tx,
    )


def test_contract_energy_fee(state_test_group) -> None:
    """DEPLOY_CONTRACT with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.DEPLOY_CONTRACT,
        payload={"module": b"\x7FELF" + b"\x00" * 100},
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "contract_energy_fee",
        state,
        tx,
    )


def test_tns_energy_fee(state_test_group) -> None:
    """REGISTER_NAME with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.REGISTER_NAME,
        payload={"name": "alice"},
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "tns_energy_fee",
        state,
        tx,
    )


def test_multisig_energy_fee(state_test_group) -> None:
    """MULTISIG with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.MULTISIG,
        payload={"threshold": 2, "participants": [BOB]},
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "multisig_energy_fee",
        state,
        tx,
    )


def test_agent_account_energy_fee(state_test_group) -> None:
    """AGENT_ACCOUNT with FeeType.ENERGY — should FAIL: INVALID_PAYLOAD."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.AGENT_ACCOUNT,
        payload={
            "variant": "create",
            "controller": BOB,
            "policy_hash": _hash(1),
        },
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "agent_account_energy_fee",
        state,
        tx,
    )


# ===================================================================
# Group 2: Negative and insufficient fee tests
# ===================================================================


def test_transfer_negative_fee(state_test_group) -> None:
    """Transfer with fee=-1 — should FAIL: INVALID_AMOUNT."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=100_000)],
        fee=-1,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "transfer_negative_fee",
        state,
        tx,
    )


def test_transfer_insufficient_fee(state_test_group) -> None:
    """Transfer with fee > sender.balance — should FAIL: INSUFFICIENT_FEE."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=100_000)],
        fee=20 * COIN_VALUE,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "transfer_insufficient_fee",
        state,
        tx,
    )


def test_burn_negative_fee(state_test_group) -> None:
    """Burn with fee=-1 — should FAIL: INVALID_AMOUNT."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": 100_000},
        fee=-1,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "burn_negative_fee",
        state,
        tx,
    )


def test_freeze_insufficient_fee(state_test_group) -> None:
    """ENERGY (freeze) with fee > sender.balance — should FAIL: INSUFFICIENT_FEE."""
    state = _base_state()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos",
            amount=COIN_VALUE,
            duration=FreezeDuration(days=7),
        ),
        fee=20 * COIN_VALUE,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "freeze_insufficient_fee",
        state,
        tx,
    )


# ===================================================================
# Group 3: UNO fee tests
# ===================================================================


def test_uno_transfer_tos_fee(state_test_group) -> None:
    """UNO_TRANSFERS with FeeType.TOS — should succeed (TOS fee always allowed)."""
    state = _base_state()
    _vp = lambda: bytes(tos_signer.random_valid_point())
    _ct = lambda: bytes(tos_signer.make_dummy_ct_validity_proof())
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
                    "commitment": _vp(),
                    "sender_handle": _vp(),
                    "receiver_handle": _vp(),
                    "ct_validity_proof": _ct(),
                }
            ]
        },
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        source_commitments=[],
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "uno_transfer_tos_fee",
        state,
        tx,
    )


def test_uno_transfer_uno_fee_nonzero(state_test_group) -> None:
    """UNO_TRANSFERS with FeeType.UNO and fee=100 — should FAIL: uno fee must be zero."""
    state = _base_state()
    _vp = lambda: bytes(tos_signer.random_valid_point())
    _ct = lambda: bytes(tos_signer.make_dummy_ct_validity_proof())
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
                    "commitment": _vp(),
                    "sender_handle": _vp(),
                    "receiver_handle": _vp(),
                    "ct_validity_proof": _ct(),
                }
            ]
        },
        fee=100,
        fee_type=FeeType.UNO,
        nonce=5,
        source_commitments=[],
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/fee_variants.json",
        "uno_transfer_uno_fee_nonzero",
        state,
        tx,
    )
