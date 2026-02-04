"""Hash test vector generators (translated from Rust generators)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import blake3  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    blake3 = None

try:
    import sha3  # type: ignore  # provides keccak_256
except Exception:  # pragma: no cover - optional dependency
    sha3 = None

try:
    from Cryptodome.Hash import keccak as _keccak  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _keccak = None


@dataclass
class HashVector:
    name: str
    description: Optional[str]
    input_hex: str
    input_ascii: Optional[str]
    input_length: int
    expected_hex: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha512(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def _sha3_512(data: bytes) -> str:
    return hashlib.sha3_512(data).hexdigest()


def _keccak256(data: bytes) -> str:
    if sha3 is not None:
        h = sha3.keccak_256()
        h.update(data)
        return h.hexdigest()
    if _keccak is not None:
        h = _keccak.new(digest_bits=256)
        h.update(data)
        return h.hexdigest()
    raise RuntimeError("keccak256 requires pysha3 or pycryptodomex")


def _blake3(data: bytes) -> str:
    if blake3 is None:
        raise RuntimeError("blake3 requires blake3 dependency")
    return blake3.blake3(data).hexdigest()


def sha256_vectors() -> Dict[str, Any]:
    vectors: List[HashVector] = []

    vectors.append(
        HashVector(
            name="empty_string",
            description=None,
            input_hex="",
            input_ascii="",
            input_length=0,
            expected_hex=_sha256(b""),
        )
    )

    vectors.append(
        HashVector(
            name="abc",
            description=None,
            input_hex=b"abc".hex(),
            input_ascii="abc",
            input_length=3,
            expected_hex=_sha256(b"abc"),
        )
    )

    vectors.append(
        HashVector(
            name="hello_world",
            description=None,
            input_hex=b"Hello, world!".hex(),
            input_ascii="Hello, world!",
            input_length=13,
            expected_hex=_sha256(b"Hello, world!"),
        )
    )

    input_data = bytes([0x61] * 55)
    vectors.append(
        HashVector(
            name="55_bytes_a",
            description="Max single block input (55 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=55,
            expected_hex=_sha256(input_data),
        )
    )

    input_data = bytes([0x61] * 56)
    vectors.append(
        HashVector(
            name="56_bytes_a",
            description="Requires two blocks (56 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=56,
            expected_hex=_sha256(input_data),
        )
    )

    input_data = bytes([0x61] * 64)
    vectors.append(
        HashVector(
            name="64_bytes_a",
            description="Exactly one SHA256 block (64 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=64,
            expected_hex=_sha256(input_data),
        )
    )

    input_data = bytes([0x61] * 128)
    vectors.append(
        HashVector(
            name="128_bytes_a",
            description="Exactly two SHA256 blocks (128 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=128,
            expected_hex=_sha256(input_data),
        )
    )

    input_data = (
        b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
    )
    vectors.append(
        HashVector(
            name="nist_vector",
            description="NIST FIPS 180-4 test vector",
            input_hex=input_data.hex(),
            input_ascii=input_data.decode("utf-8"),
            input_length=len(input_data),
            expected_hex=_sha256(input_data),
        )
    )

    input_data = bytes(range(0, 256))
    vectors.append(
        HashVector(
            name="all_bytes",
            description="All byte values 0x00-0xFF",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=256,
            expected_hex=_sha256(input_data),
        )
    )

    return {
        "algorithm": "SHA256",
        "output_size": 32,
        "block_size": 64,
        "test_vectors": [v.__dict__ for v in vectors],
    }


def sha512_vectors() -> Dict[str, Any]:
    vectors: List[HashVector] = []

    vectors.append(
        HashVector(
            name="empty_string",
            description=None,
            input_hex="",
            input_ascii="",
            input_length=0,
            expected_hex=_sha512(b""),
        )
    )

    vectors.append(
        HashVector(
            name="abc",
            description=None,
            input_hex=b"abc".hex(),
            input_ascii="abc",
            input_length=3,
            expected_hex=_sha512(b"abc"),
        )
    )

    vectors.append(
        HashVector(
            name="hello_world",
            description=None,
            input_hex=b"Hello, world!".hex(),
            input_ascii="Hello, world!",
            input_length=13,
            expected_hex=_sha512(b"Hello, world!"),
        )
    )

    input_data = bytes([0x61] * 111)
    vectors.append(
        HashVector(
            name="111_bytes_a",
            description="Max single block input (111 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=111,
            expected_hex=_sha512(input_data),
        )
    )

    input_data = bytes([0x61] * 112)
    vectors.append(
        HashVector(
            name="112_bytes_a",
            description="Requires two blocks (112 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=112,
            expected_hex=_sha512(input_data),
        )
    )

    input_data = bytes([0x61] * 128)
    vectors.append(
        HashVector(
            name="128_bytes_a",
            description="Exactly one SHA512 block (128 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=128,
            expected_hex=_sha512(input_data),
        )
    )

    input_data = bytes([0x61] * 256)
    vectors.append(
        HashVector(
            name="256_bytes_a",
            description="Exactly two SHA512 blocks (256 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=256,
            expected_hex=_sha512(input_data),
        )
    )

    input_data = (
        b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno"
        b"ijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu"
    )
    vectors.append(
        HashVector(
            name="nist_vector",
            description="NIST FIPS 180-4 test vector",
            input_hex=input_data.hex(),
            input_ascii=input_data.decode("utf-8"),
            input_length=len(input_data),
            expected_hex=_sha512(input_data),
        )
    )

    input_data = bytes(range(0, 256))
    vectors.append(
        HashVector(
            name="all_bytes",
            description="All byte values 0x00-0xFF",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=256,
            expected_hex=_sha512(input_data),
        )
    )

    input_data = bytes([0x01] * 32)
    vectors.append(
        HashVector(
            name="ed25519_seed",
            description="32-byte seed for Ed25519 key expansion",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=32,
            expected_hex=_sha512(input_data),
        )
    )

    return {
        "algorithm": "SHA512",
        "output_size": 64,
        "block_size": 128,
        "test_vectors": [v.__dict__ for v in vectors],
    }


def sha3_512_vectors() -> Dict[str, Any]:
    vectors: List[HashVector] = []

    vectors.append(
        HashVector(
            name="empty_string",
            description=None,
            input_hex="",
            input_ascii="",
            input_length=0,
            expected_hex=_sha3_512(b""),
        )
    )

    vectors.append(
        HashVector(
            name="abc",
            description=None,
            input_hex=b"abc".hex(),
            input_ascii="abc",
            input_length=3,
            expected_hex=_sha3_512(b"abc"),
        )
    )

    vectors.append(
        HashVector(
            name="hello_world",
            description="Message used in TOS signature tests",
            input_hex=b"Hello, world!".hex(),
            input_ascii="Hello, world!",
            input_length=13,
            expected_hex=_sha3_512(b"Hello, world!"),
        )
    )

    input_data = bytes([0x61] * 71)
    vectors.append(
        HashVector(
            name="71_bytes_a",
            description="One byte less than SHA3-512 block size",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=71,
            expected_hex=_sha3_512(input_data),
        )
    )

    input_data = bytes([0x61] * 72)
    vectors.append(
        HashVector(
            name="72_bytes_a",
            description="Exactly one SHA3-512 block (72 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=72,
            expected_hex=_sha3_512(input_data),
        )
    )

    input_data = bytes([0x61] * 73)
    vectors.append(
        HashVector(
            name="73_bytes_a",
            description="One byte more than SHA3-512 block size",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=73,
            expected_hex=_sha3_512(input_data),
        )
    )

    input_data = bytes([0x61] * 144)
    vectors.append(
        HashVector(
            name="144_bytes_a",
            description="Exactly two SHA3-512 blocks (144 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=144,
            expected_hex=_sha3_512(input_data),
        )
    )

    input_data = bytes([0x00] * 32) + b"Hello, world!" + bytes([0x00] * 32)
    vectors.append(
        HashVector(
            name="tos_signature_hash",
            description=(
                "TOS hash_and_point_to_scalar style: pubkey(32) + message + point(32)"
            ),
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=len(input_data),
            expected_hex=_sha3_512(input_data),
        )
    )

    return {
        "algorithm": "SHA3-512",
        "output_size": 64,
        "block_size": 72,
        "test_vectors": [v.__dict__ for v in vectors],
    }


def keccak256_vectors() -> Dict[str, Any]:
    vectors: List[HashVector] = []

    vectors.append(
        HashVector(
            name="empty_string",
            description=None,
            input_hex="",
            input_ascii="",
            input_length=0,
            expected_hex=_keccak256(b""),
        )
    )

    vectors.append(
        HashVector(
            name="abc",
            description=None,
            input_hex=b"abc".hex(),
            input_ascii="abc",
            input_length=3,
            expected_hex=_keccak256(b"abc"),
        )
    )

    vectors.append(
        HashVector(
            name="hello_world",
            description=None,
            input_hex=b"Hello, world!".hex(),
            input_ascii="Hello, world!",
            input_length=13,
            expected_hex=_keccak256(b"Hello, world!"),
        )
    )

    input_data = bytes([0x04] * 64)
    vectors.append(
        HashVector(
            name="ethereum_pubkey",
            description="64-byte public key for Ethereum address derivation",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=64,
            expected_hex=_keccak256(input_data),
        )
    )

    input_data = bytes([0x61] * 135)
    vectors.append(
        HashVector(
            name="135_bytes_a",
            description="One byte less than Keccak256 block size",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=135,
            expected_hex=_keccak256(input_data),
        )
    )

    input_data = bytes([0x61] * 136)
    vectors.append(
        HashVector(
            name="136_bytes_a",
            description="Exactly one Keccak256 block (136 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=136,
            expected_hex=_keccak256(input_data),
        )
    )

    input_data = bytes([0x61] * 137)
    vectors.append(
        HashVector(
            name="137_bytes_a",
            description="One byte more than Keccak256 block size",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=137,
            expected_hex=_keccak256(input_data),
        )
    )

    input_data = bytes([0x61] * 272)
    vectors.append(
        HashVector(
            name="272_bytes_a",
            description="Exactly two Keccak256 blocks (272 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=272,
            expected_hex=_keccak256(input_data),
        )
    )

    input_data = bytes(range(0, 256))
    vectors.append(
        HashVector(
            name="all_bytes",
            description="All byte values 0x00-0xFF",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=256,
            expected_hex=_keccak256(input_data),
        )
    )

    input_data = bytes([0xFF] * 32)
    vectors.append(
        HashVector(
            name="pda_seed",
            description="32-byte seed for PDA derivation",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=32,
            expected_hex=_keccak256(input_data),
        )
    )

    return {
        "algorithm": "Keccak256",
        "output_size": 32,
        "block_size": 136,
        "test_vectors": [v.__dict__ for v in vectors],
    }


def blake3_vectors() -> Dict[str, Any]:
    vectors: List[HashVector] = []

    vectors.append(
        HashVector(
            name="empty_string",
            description=None,
            input_hex="",
            input_ascii="",
            input_length=0,
            expected_hex=_blake3(b""),
        )
    )

    vectors.append(
        HashVector(
            name="abc",
            description=None,
            input_hex=b"abc".hex(),
            input_ascii="abc",
            input_length=3,
            expected_hex=_blake3(b"abc"),
        )
    )

    vectors.append(
        HashVector(
            name="hello_world",
            description=None,
            input_hex=b"Hello, world!".hex(),
            input_ascii="Hello, world!",
            input_length=13,
            expected_hex=_blake3(b"Hello, world!"),
        )
    )

    input_data = bytes([0x61] * 63)
    vectors.append(
        HashVector(
            name="63_bytes_a",
            description="One byte less than BLAKE3 chunk size",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=63,
            expected_hex=_blake3(input_data),
        )
    )

    input_data = bytes([0x61] * 64)
    vectors.append(
        HashVector(
            name="64_bytes_a",
            description="Exactly one BLAKE3 chunk (64 bytes)",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=64,
            expected_hex=_blake3(input_data),
        )
    )

    input_data = bytes([0x61] * 65)
    vectors.append(
        HashVector(
            name="65_bytes_a",
            description="One byte more than BLAKE3 chunk size",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=65,
            expected_hex=_blake3(input_data),
        )
    )

    input_data = bytes([0x61] * 1024)
    vectors.append(
        HashVector(
            name="1024_bytes_a",
            description="1024 bytes spanning multiple chunks",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=1024,
            expected_hex=_blake3(input_data),
        )
    )

    input_data = bytes(range(0, 256))
    vectors.append(
        HashVector(
            name="all_bytes",
            description="All byte values 0x00-0xFF",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=256,
            expected_hex=_blake3(input_data),
        )
    )

    input_data = bytes([0x42] * 32)
    vectors.append(
        HashVector(
            name="tx_hash",
            description="32-byte transaction data hash",
            input_hex=input_data.hex(),
            input_ascii=None,
            input_length=32,
            expected_hex=_blake3(input_data),
        )
    )

    return {
        "algorithm": "BLAKE3",
        "output_size": 32,
        "block_size": 64,
        "test_vectors": [v.__dict__ for v in vectors],
    }
