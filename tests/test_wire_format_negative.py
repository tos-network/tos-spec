"""Negative wire format tests: malformed bytes that fail at deserialization.

These tests produce vectors with invalid wire_hex that the conformance daemon
should reject with INVALID_FORMAT (error_code 256 / 0x0100).  They exercise
the L0 codec layer without touching state transition logic.
"""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.test_accounts import ALICE, sign_transaction
from tos_spec.types import (
    FeeType,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _hash(b: int) -> bytes:
    return bytes([b]) * 32


def _valid_burn_hex() -> tuple[str, int]:
    """Encode a valid BURN tx and return (hex, total_byte_length).

    The BURN payload is fixed-size (asset:32 + amount:8 = 40 bytes),
    making it ideal as a baseline for mutation tests.
    """
    import tos_codec
    from tos_spec.codec_adapter import tx_to_serde_json

    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": 1000},
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=0,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    tx.signature = sign_transaction(tx)
    hex_str = tos_codec.encode_tx(tx_to_serde_json(tx))
    return hex_str, len(bytes.fromhex(hex_str))


def _mutate(hex_str: str, offset: int, new_byte: int) -> str:
    raw = bytearray(bytes.fromhex(hex_str))
    raw[offset] = new_byte
    return raw.hex()


def _truncate(hex_str: str, byte_length: int) -> str:
    raw = bytes.fromhex(hex_str)
    return raw[:byte_length].hex()


def _append(hex_str: str, extra: bytes) -> str:
    raw = bytes.fromhex(hex_str)
    return (raw + extra).hex()


# Byte offsets for a standard (non-UNO, non-multisig) transaction:
#   [0]      version      (1 byte)
#   [1]      chain_id     (1 byte)
#   [2..34]  source       (32 bytes, CompressedPublicKey)
#   [34]     tx_type      (1 byte, discriminant)
#   [35..]   payload      (variable, BURN = 40 bytes: asset:32 + amount:8)
#   For BURN: offset 75 = fee start (8 bytes)
#             offset 83 = fee_type (1 byte)
#             offset 84 = nonce (8 bytes)
#   Then reference + has_multisig + signature

OFF_VERSION = 0
OFF_CHAIN_ID = 1
OFF_TX_TYPE = 34
# BURN-specific:
OFF_BURN_FEE_TYPE = 83


def _vec(name: str, description: str, wire_hex: str) -> dict:
    """Build a negative wire format vector entry."""
    return {
        "name": name,
        "description": description,
        "pre_state": None,
        "input": {"kind": "tx", "wire_hex": wire_hex},
        "expected": {
            "success": False,
            "error_code": 256,
            "state_digest": "",
            "post_state": None,
        },
    }


FIXTURE_PATH = "transactions/wire_format_negative.json"


# --- Truncation tests ---


def test_wire_single_byte(vector_test_group) -> None:
    """Single byte is too short for any valid transaction."""
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_single_byte",
        "1 byte input cannot form a valid transaction",
        "00",
    ))


def test_wire_truncated_header(vector_test_group) -> None:
    """10 bytes is too short to contain version+chain_id+source."""
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_truncated_header",
        "10 bytes is shorter than the minimum header",
        "01" + "00" * 9,
    ))


def test_wire_truncated_mid_payload(vector_test_group) -> None:
    """Valid header but payload cut short."""
    valid, total = _valid_burn_hex()
    wire = _truncate(valid, 50)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_truncated_mid_payload",
        "Transaction truncated in the middle of the payload",
        wire,
    ))


def test_wire_truncated_before_signature(vector_test_group) -> None:
    """All fields present except signature is incomplete."""
    valid, total = _valid_burn_hex()
    wire = _truncate(valid, total - 32)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_truncated_before_signature",
        "Transaction missing the last 32 bytes of signature",
        wire,
    ))


# --- Invalid field value tests ---


def test_wire_invalid_version(vector_test_group) -> None:
    """Version byte 0xFF is not a supported transaction version."""
    valid, _ = _valid_burn_hex()
    wire = _mutate(valid, OFF_VERSION, 0xFF)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_invalid_version",
        "Version 0xFF is unsupported",
        wire,
    ))


def test_wire_version_zero(vector_test_group) -> None:
    """Version byte 0x00 is not valid (T1 = 0x01)."""
    valid, _ = _valid_burn_hex()
    wire = _mutate(valid, OFF_VERSION, 0x00)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_version_zero",
        "Version 0x00 is not a valid transaction version",
        wire,
    ))


def test_wire_invalid_tx_type(vector_test_group) -> None:
    """TX type discriminant 6 does not exist."""
    valid, _ = _valid_burn_hex()
    wire = _mutate(valid, OFF_TX_TYPE, 6)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_invalid_tx_type",
        "Transaction type discriminant 6 is not assigned",
        wire,
    ))


def test_wire_tx_type_high(vector_test_group) -> None:
    """TX type discriminant 0xFF is way out of range."""
    valid, _ = _valid_burn_hex()
    wire = _mutate(valid, OFF_TX_TYPE, 0xFF)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_tx_type_high",
        "Transaction type discriminant 255 is invalid",
        wire,
    ))


def test_wire_invalid_fee_type(vector_test_group) -> None:
    """Fee type 5 is not a valid FeeType variant (only 0, 1, 2)."""
    valid, _ = _valid_burn_hex()
    wire = _mutate(valid, OFF_BURN_FEE_TYPE, 5)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_invalid_fee_type",
        "Fee type 5 is not a valid enum variant",
        wire,
    ))


# --- Structural tests ---


def test_wire_extra_trailing_bytes(vector_test_group) -> None:
    """Valid transaction with extra trailing garbage bytes."""
    valid, _ = _valid_burn_hex()
    wire = _append(valid, b"\xde\xad\xbe\xef" * 4)
    v = _vec(
        "wire_extra_trailing_bytes",
        "Trailing bytes after a complete transaction are rejected",
        wire,
    )
    vector_test_group(FIXTURE_PATH, v)


def test_wire_all_zeros(vector_test_group) -> None:
    """A buffer of all zeros is invalid (version=0, no valid structure)."""
    wire = "00" * 100
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_all_zeros",
        "100 bytes of zeros is not a valid transaction",
        wire,
    ))


def test_wire_all_ones(vector_test_group) -> None:
    """A buffer of all 0xFF bytes is invalid."""
    wire = "ff" * 100
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_all_ones",
        "100 bytes of 0xFF is not a valid transaction",
        wire,
    ))


# --- Transfer-specific malformed tests ---


def _valid_transfer_hex() -> tuple[str, int]:
    """Encode a valid single-transfer tx."""
    import tos_codec
    from tos_spec.codec_adapter import tx_to_serde_json
    from tos_spec.test_accounts import BOB

    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=BOB, amount=1000)],
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=0,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    tx.signature = sign_transaction(tx)
    hex_str = tos_codec.encode_tx(tx_to_serde_json(tx))
    return hex_str, len(bytes.fromhex(hex_str))


def test_wire_transfer_zero_count(vector_test_group) -> None:
    """Transfer with count=0 is rejected at wire level."""
    valid, _ = _valid_transfer_hex()
    # Transfer payload starts at offset 35 with a 2-byte count (u16 BE)
    # Set count to 0x0000
    wire = _mutate(_mutate(valid, 35, 0x00), 36, 0x00)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_transfer_zero_count",
        "Transfer with 0 recipients is invalid at wire level",
        wire,
    ))


def test_wire_transfer_count_overflow(vector_test_group) -> None:
    """Transfer with count > MAX_TRANSFER_COUNT (500) in wire bytes."""
    valid, _ = _valid_transfer_hex()
    # Set count to 0x01F5 = 501 (but rest of payload only has 1 transfer)
    # This will fail because the deserializer tries to read 501 entries
    wire = _mutate(_mutate(valid, 35, 0x01), 36, 0xF5)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_transfer_count_overflow",
        "Transfer count 501 exceeds MAX_TRANSFER_COUNT (500)",
        wire,
    ))


def test_wire_transfer_count_mismatch(vector_test_group) -> None:
    """Transfer claims 5 entries but only has data for 1."""
    valid, _ = _valid_transfer_hex()
    # Set count to 5, but only 1 transfer's worth of data follows
    wire = _mutate(_mutate(valid, 35, 0x00), 36, 0x05)
    vector_test_group(FIXTURE_PATH, _vec(
        "wire_transfer_count_mismatch",
        "Transfer count says 5 but data only contains 1 entry",
        wire,
    ))
