"""Wire-format encoding utilities (minimal subset)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import EXTRA_DATA_LIMIT_SIZE, MAX_DELEGATEES, MAX_TRANSFER_COUNT
from .errors import ErrorCode, SpecError
from .types import (
    DelegationEntry,
    EnergyPayload,
    FeeType,
    FreezeDuration,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


TX_TYPE_IDS = {
    TransactionType.BURN: 0,
    TransactionType.TRANSFERS: 1,
    TransactionType.ENERGY: 5,
}


@dataclass
class Writer:
    buf: bytearray

    def write_u8(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(1, "big", signed=False))

    def write_u16(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(2, "big", signed=False))

    def write_u32(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(4, "big", signed=False))

    def write_u64(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(8, "big", signed=False))

    def write_bytes(self, b: bytes) -> None:
        self.buf.extend(b)

    def write_bool(self, v: bool) -> None:
        self.write_u8(1 if v else 0)


def _write_optional_bytes(w: Writer, value: Optional[bytes]) -> None:
    if value is None:
        w.write_u8(0)
        return
    w.write_u8(1)
    w.write_u32(len(value))
    w.write_bytes(value)


def _encode_transfers(w: Writer, transfers: list[TransferPayload]) -> None:
    if not transfers or len(transfers) > MAX_TRANSFER_COUNT:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid transfer count")

    w.write_u16(len(transfers))
    for t in transfers:
        if t.extra_data is not None and len(t.extra_data) > EXTRA_DATA_LIMIT_SIZE:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
        w.write_bytes(t.asset)
        w.write_bytes(t.destination)
        w.write_u64(t.amount)
        _write_optional_bytes(w, t.extra_data)

def _encode_freeze_duration(w: Writer, duration: FreezeDuration) -> None:
    w.write_u32(duration.days)


def _encode_energy(w: Writer, payload: EnergyPayload) -> None:
    if payload.variant == "freeze_tos":
        if payload.amount is None or payload.duration is None:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "freeze_tos missing fields")
        w.write_u8(0)
        w.write_u64(payload.amount)
        _encode_freeze_duration(w, payload.duration)
        return

    if payload.variant == "freeze_tos_delegate":
        if payload.delegatees is None or payload.duration is None:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "freeze_tos_delegate missing fields")
        if len(payload.delegatees) > MAX_DELEGATEES:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many delegatees")
        w.write_u8(1)
        w.write_u64(len(payload.delegatees))
        for entry in payload.delegatees:
            if not isinstance(entry, DelegationEntry):
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid delegation entry")
            w.write_bytes(entry.delegatee)
            w.write_u64(entry.amount)
        _encode_freeze_duration(w, payload.duration)
        return

    if payload.variant == "unfreeze_tos":
        if payload.amount is None or payload.from_delegation is None:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "unfreeze_tos missing fields")
        w.write_u8(2)
        w.write_u64(payload.amount)
        w.write_bool(payload.from_delegation)
        if payload.record_index is None:
            w.write_u8(0)
        else:
            w.write_u8(1)
            w.write_u32(payload.record_index)
        if payload.delegatee_address is None:
            w.write_u8(0)
        else:
            w.write_u8(1)
            w.write_bytes(payload.delegatee_address)
        return

    if payload.variant == "withdraw_unfrozen":
        w.write_u8(3)
        return

    raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown energy payload variant")


def encode_transaction(tx: Transaction) -> bytes:
    """Encode a transaction in wire format for supported types.

    Minimal subset for specs: Transfers and Burn.
    """
    if tx.version != TxVersion.T1:
        raise SpecError(ErrorCode.INVALID_VERSION, "unsupported tx version")

    if tx.tx_type not in TX_TYPE_IDS:
        raise SpecError(ErrorCode.INVALID_TYPE, "unsupported tx type")

    if tx.signature is None:
        raise SpecError(ErrorCode.INVALID_FORMAT, "missing signature")

    if tx.reference_hash is None or tx.reference_topoheight is None:
        raise SpecError(ErrorCode.INVALID_FORMAT, "missing reference")

    if len(tx.source) != 32:
        raise SpecError(ErrorCode.INVALID_FORMAT, "source must be 32 bytes")

    w = Writer(bytearray())
    w.write_u8(tx.version)
    w.write_u8(tx.chain_id)
    w.write_bytes(tx.source)

    w.write_u8(TX_TYPE_IDS[tx.tx_type])

    if tx.tx_type == TransactionType.TRANSFERS:
        if not isinstance(tx.payload, list):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "payload must be list")
        _encode_transfers(w, tx.payload)
    elif tx.tx_type == TransactionType.BURN:
        if not isinstance(tx.payload, int):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "payload must be int")
        w.write_u64(tx.payload)
    elif tx.tx_type == TransactionType.ENERGY:
        if not isinstance(tx.payload, EnergyPayload):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "payload must be EnergyPayload")
        _encode_energy(w, tx.payload)

    w.write_u64(tx.fee)
    if not isinstance(tx.fee_type, FeeType):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "fee_type invalid")
    w.write_u8(tx.fee_type)
    w.write_u64(tx.nonce)

    # UNO fields are excluded for this minimal subset
    # Reference
    w.write_bytes(tx.reference_hash)
    w.write_u64(tx.reference_topoheight)

    # Multisig omitted in minimal subset

    # Signature
    w.write_bytes(tx.signature)

    return bytes(w.buf)
