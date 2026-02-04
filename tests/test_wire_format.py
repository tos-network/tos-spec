"""Wire-format vectors (minimal subset)."""

from __future__ import annotations

from tos_spec.encoding import encode_transaction
from tos_spec.types import (
    EnergyPayload,
    FeeType,
    FreezeDuration,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def test_transfer_wire_vector(wire_vector) -> None:
    sender = _addr(1)
    receiver = _addr(2)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=100_000)],
        fee=1_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_hash(7),
    )

    encoded = encode_transaction(tx)
    wire_vector(
        "transfer_basic",
        {
            "tx": {
                "version": int(tx.version),
                "chain_id": tx.chain_id,
                "source": tx.source.hex(),
                "tx_type": tx.tx_type.value,
                "nonce": tx.nonce,
                "fee": tx.fee,
                "fee_type": int(tx.fee_type),
                "payload": [
                    {
                        "asset": tx.payload[0].asset.hex(),
                        "destination": tx.payload[0].destination.hex(),
                        "amount": tx.payload[0].amount,
                        "extra_data": None,
                    }
                ],
                "reference_hash": tx.reference_hash.hex(),
                "reference_topoheight": tx.reference_topoheight,
                "signature": tx.signature.hex(),
            },
            "expected_hex": encoded.hex(),
        },
    )


def test_energy_freeze_wire_vector(wire_vector) -> None:
    sender = _addr(3)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos",
            amount=100_000_000,
            duration=FreezeDuration(days=7),
        ),
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=1,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_hash(7),
    )

    encoded = encode_transaction(tx)
    wire_vector(
        "energy_freeze_basic",
        {
            "tx": {
                "version": int(tx.version),
                "chain_id": tx.chain_id,
                "source": tx.source.hex(),
                "tx_type": tx.tx_type.value,
                "nonce": tx.nonce,
                "fee": tx.fee,
                "fee_type": int(tx.fee_type),
                "payload": {
                    "variant": "freeze_tos",
                    "amount": 100_000_000,
                    "duration_days": 7,
                },
                "reference_hash": tx.reference_hash.hex(),
                "reference_topoheight": tx.reference_topoheight,
                "signature": tx.signature.hex(),
            },
            "expected_hex": encoded.hex(),
        },
    )
