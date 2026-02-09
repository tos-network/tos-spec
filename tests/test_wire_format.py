"""Wire-format vectors for the core transaction types implemented in `~/tos`."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MIN_SHIELD_TOS_AMOUNT
from tos_spec.encoding import encode_transaction
from tos_spec.test_accounts import ALICE, BOB
from tos_spec.types import (
    DelegationEntry,
    EnergyPayload,
    FeeType,
    FreezeDuration,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig() -> bytes:
    return bytes(64)


def _tx(source: bytes, tx_type: TransactionType, payload: object, **kwargs) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=source,
        tx_type=tx_type,
        payload=payload,
        fee=kwargs.get("fee", 100_000),
        fee_type=kwargs.get("fee_type", FeeType.TOS),
        nonce=kwargs.get("nonce", 1),
        reference_hash=kwargs.get("reference_hash", _hash(0)),
        reference_topoheight=kwargs.get("reference_topoheight", 0),
        signature=kwargs.get("signature", _sig()),
        source_commitments=kwargs.get("source_commitments", []),
        range_proof=kwargs.get("range_proof", None),
        multisig=kwargs.get("multisig", None),
    )


def _vec(wire_vector, name: str, tx: Transaction, encoded: bytes, payload_json: object) -> None:
    wire_vector(
        name,
        {
            "tx": {
                "version": int(tx.version),
                "chain_id": tx.chain_id,
                "source": tx.source.hex(),
                "tx_type": tx.tx_type.value,
                "nonce": tx.nonce,
                "fee": tx.fee,
                "fee_type": int(tx.fee_type),
                "payload": payload_json,
                "reference_hash": tx.reference_hash.hex() if tx.reference_hash else None,
                "reference_topoheight": tx.reference_topoheight,
                "signature": tx.signature.hex() if tx.signature else None,
            },
            "expected_hex": encoded.hex(),
        },
    )


def test_transfers_wire_vector(wire_vector) -> None:
    payload = [TransferPayload(asset=_hash(0), destination=BOB, amount=10 * COIN_VALUE)]
    tx = _tx(ALICE, TransactionType.TRANSFERS, payload)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "transfers_basic",
        tx,
        encoded,
        [
            {
                "asset": _hash(0).hex(),
                "destination": BOB.hex(),
                "amount": 10 * COIN_VALUE,
                "extra_data": None,
            }
        ],
    )


def test_burn_wire_vector(wire_vector) -> None:
    payload = {"asset": _hash(0), "amount": 123}
    tx = _tx(ALICE, TransactionType.BURN, payload)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "burn_basic",
        tx,
        encoded,
        {"asset": _hash(0).hex(), "amount": 123},
    )


def test_multisig_wire_vector(wire_vector) -> None:
    payload = {"threshold": 2, "participants": [ALICE, BOB]}
    tx = _tx(ALICE, TransactionType.MULTISIG, payload)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "multisig_basic",
        tx,
        encoded,
        {"threshold": 2, "participants": [ALICE.hex(), BOB.hex()]},
    )


def test_deploy_contract_wire_vector(wire_vector) -> None:
    module = b"\x7FELF" + b"\x00" * 16
    payload = {"module": module}
    tx = _tx(ALICE, TransactionType.DEPLOY_CONTRACT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "deploy_contract_basic", tx, encoded, {"module": module.hex()})


def test_invoke_contract_wire_vector(wire_vector) -> None:
    payload = {"contract": _hash(9), "deposits": [], "entry_id": 0, "max_gas": 0, "parameters": []}
    tx = _tx(ALICE, TransactionType.INVOKE_CONTRACT, payload)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "invoke_contract_basic",
        tx,
        encoded,
        {"contract": _hash(9).hex(), "deposits": [], "entry_id": 0, "max_gas": 0, "parameters": []},
    )


def test_energy_freeze_wire_vector(wire_vector) -> None:
    payload = EnergyPayload(variant="freeze_tos", amount=COIN_VALUE, duration=FreezeDuration(days=7))
    tx = _tx(ALICE, TransactionType.ENERGY, payload, fee=0)
    encoded = encode_transaction(tx, current_time=1700000000)
    _vec(
        wire_vector,
        "energy_freeze_tos_basic",
        tx,
        encoded,
        {"variant": "freeze_tos", "amount": COIN_VALUE, "duration_days": 7},
    )


def test_agent_account_register_wire_vector(wire_vector) -> None:
    payload = {"variant": "register", "controller": BOB, "policy_hash": _hash(1)}
    tx = _tx(ALICE, TransactionType.AGENT_ACCOUNT, payload)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "agent_account_register_basic",
        tx,
        encoded,
        {"variant": "register", "controller": BOB.hex(), "policy_hash": _hash(1).hex()},
    )


def test_shield_transfers_wire_vector(wire_vector) -> None:
    transfer = {
        "asset": _hash(0),
        "destination": BOB,
        "amount": MIN_SHIELD_TOS_AMOUNT,
        "extra_data": None,
        "commitment": bytes(32),
        "receiver_handle": bytes(32),
        "proof": bytes(96),
    }
    payload = {"transfers": [transfer]}
    tx = _tx(ALICE, TransactionType.SHIELD_TRANSFERS, payload, fee_type=FeeType.TOS)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "shield_transfers_basic",
        tx,
        encoded,
        {
            "transfers": [
                {
                    "asset": _hash(0).hex(),
                    "destination": BOB.hex(),
                    "amount": MIN_SHIELD_TOS_AMOUNT,
                    "extra_data": None,
                    "commitment": bytes(32).hex(),
                    "receiver_handle": bytes(32).hex(),
                    "proof": bytes(96).hex(),
                }
            ]
        },
    )


def test_unshield_transfers_wire_vector(wire_vector) -> None:
    transfer = {
        "asset": _hash(0),
        "destination": BOB,
        "amount": 10 * COIN_VALUE,
        "extra_data": None,
        "commitment": bytes(32),
        "sender_handle": bytes(32),
        "ct_validity_proof": bytes(160),
    }
    payload = {"transfers": [transfer]}
    tx = _tx(ALICE, TransactionType.UNSHIELD_TRANSFERS, payload, fee_type=FeeType.TOS)
    encoded = encode_transaction(tx)
    _vec(
        wire_vector,
        "unshield_transfers_basic",
        tx,
        encoded,
        {
            "transfers": [
                {
                    "asset": _hash(0).hex(),
                    "destination": BOB.hex(),
                    "amount": 10 * COIN_VALUE,
                    "extra_data": None,
                    "commitment": bytes(32).hex(),
                    "sender_handle": bytes(32).hex(),
                    "ct_validity_proof": bytes(160).hex(),
                }
            ]
        },
    )


def test_register_name_wire_vector(wire_vector) -> None:
    payload = {"name": "alice"}
    tx = _tx(ALICE, TransactionType.REGISTER_NAME, payload, fee=10_000_000)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "register_name_basic", tx, encoded, {"name": "alice"})
