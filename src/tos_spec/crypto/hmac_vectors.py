"""HMAC test vector generators (translated from Rust generators)."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class HmacVector:
    name: str
    description: Optional[str]
    key_hex: str
    key_length: int
    message_hex: str
    message_ascii: Optional[str]
    message_length: int
    expected_hex: str


def _hmac_sha256(key: bytes, message: bytes) -> str:
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _hmac_sha512(key: bytes, message: bytes) -> str:
    return hmac.new(key, message, hashlib.sha512).hexdigest()


def hmac_sha256_vectors() -> Dict[str, Any]:
    vectors: List[HmacVector] = []

    key = bytes.fromhex("0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b")
    message = b"Hi There"
    vectors.append(
        HmacVector(
            name="rfc4231_test1",
            description="RFC 4231 Test Case 1",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii="Hi There",
            message_length=len(message),
            expected_hex=_hmac_sha256(key, message),
        )
    )

    key = b"Jefe"
    message = b"what do ya want for nothing?"
    vectors.append(
        HmacVector(
            name="rfc4231_test2",
            description="RFC 4231 Test Case 2",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii="what do ya want for nothing?",
            message_length=len(message),
            expected_hex=_hmac_sha256(key, message),
        )
    )

    key = bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    message = bytes.fromhex(
        "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
    )
    vectors.append(
        HmacVector(
            name="rfc4231_test3",
            description="RFC 4231 Test Case 3",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii=None,
            message_length=len(message),
            expected_hex=_hmac_sha256(key, message),
        )
    )

    key = bytes([0x01] * 32)
    message = b""
    vectors.append(
        HmacVector(
            name="empty_message",
            description="32-byte key, empty message",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex="",
            message_ascii="",
            message_length=0,
            expected_hex=_hmac_sha256(key, message),
        )
    )

    key = bytes([0xAA] * 128)
    message = b"Test with a key longer than block size"
    vectors.append(
        HmacVector(
            name="long_key",
            description="Key longer than block size (128 bytes)",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii=message.decode("utf-8"),
            message_length=len(message),
            expected_hex=_hmac_sha256(key, message),
        )
    )

    key = bytes([0x42] * 32)
    message = b"m/44'/501'/0'/0'"
    vectors.append(
        HmacVector(
            name="bip32_path",
            description="HD wallet path derivation style",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii=message.decode("utf-8"),
            message_length=len(message),
            expected_hex=_hmac_sha256(key, message),
        )
    )

    return {
        "algorithm": "HMAC-SHA256",
        "output_size": 32,
        "test_vectors": [v.__dict__ for v in vectors],
    }


def hmac_sha512_vectors() -> Dict[str, Any]:
    vectors: List[HmacVector] = []

    key = bytes.fromhex("0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b")
    message = b"Hi There"
    vectors.append(
        HmacVector(
            name="rfc4231_test1",
            description="RFC 4231 Test Case 1",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii="Hi There",
            message_length=len(message),
            expected_hex=_hmac_sha512(key, message),
        )
    )

    key = b"Jefe"
    message = b"what do ya want for nothing?"
    vectors.append(
        HmacVector(
            name="rfc4231_test2",
            description="RFC 4231 Test Case 2",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii="what do ya want for nothing?",
            message_length=len(message),
            expected_hex=_hmac_sha512(key, message),
        )
    )

    key = bytes([0x01] * 64)
    message = b""
    vectors.append(
        HmacVector(
            name="empty_message",
            description="64-byte key, empty message",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex="",
            message_ascii="",
            message_length=0,
            expected_hex=_hmac_sha512(key, message),
        )
    )

    key = bytes([0xAA] * 256)
    message = b"Test with a key longer than block size"
    vectors.append(
        HmacVector(
            name="long_key",
            description="Key longer than block size (256 bytes)",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii=message.decode("utf-8"),
            message_length=len(message),
            expected_hex=_hmac_sha512(key, message),
        )
    )

    key = b"mnemonic"
    message = (
        b"abandon abandon abandon abandon abandon abandon abandon abandon "
        b"abandon abandon abandon about"
    )
    vectors.append(
        HmacVector(
            name="bip39_mnemonic",
            description="BIP39 mnemonic to seed derivation style",
            key_hex=key.hex(),
            key_length=len(key),
            message_hex=message.hex(),
            message_ascii=message.decode("utf-8"),
            message_length=len(message),
            expected_hex=_hmac_sha512(key, message),
        )
    )

    return {
        "algorithm": "HMAC-SHA512",
        "output_size": 64,
        "test_vectors": [v.__dict__ for v in vectors],
    }
