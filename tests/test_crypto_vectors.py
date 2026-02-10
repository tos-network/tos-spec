"""L0 crypto vectors (hash + HMAC)."""

from __future__ import annotations

import pytest

from tos_spec.crypto.hash_vectors import blake3_vectors
from tos_spec.crypto.hmac_vectors import hmac_sha256_vectors, hmac_sha512_vectors


def _emit_hash_vectors(vector_test_group, rel_path: str, algorithm: str, payload: dict) -> None:
    for item in payload.get("test_vectors", []):
        vector_test_group(
            rel_path,
            {
                "name": f"{algorithm.lower()}_{item['name']}",
                "description": item.get("description") or "",
                "input": {
                    "kind": "hash",
                    "algorithm": algorithm,
                    "input_hex": item["input_hex"],
                    "input_ascii": item.get("input_ascii"),
                    "input_length": item["input_length"],
                },
                "expected": {"digest_hex": item["expected_hex"]},
            },
        )


def _emit_hmac_vectors(vector_test_group, rel_path: str, algorithm: str, payload: dict) -> None:
    for item in payload.get("test_vectors", []):
        vector_test_group(
            rel_path,
            {
                "name": f"{algorithm.lower()}_{item['name']}",
                "description": item.get("description") or "",
                "input": {
                    "kind": "hmac",
                    "algorithm": algorithm,
                    "key_hex": item["key_hex"],
                    "key_length": item["key_length"],
                    "message_hex": item["message_hex"],
                    "message_ascii": item.get("message_ascii"),
                    "message_length": item["message_length"],
                },
                "expected": {"mac_hex": item["expected_hex"]},
            },
        )


def test_crypto_blake3_vectors(vector_test_group) -> None:
    pytest.importorskip("blake3")
    _emit_hash_vectors(
        vector_test_group,
        "crypto/blake3.json",
        "BLAKE3",
        blake3_vectors(),
    )


def test_crypto_hmac_sha256_vectors(vector_test_group) -> None:
    _emit_hmac_vectors(
        vector_test_group,
        "crypto/hmac_sha256.json",
        "HMAC-SHA256",
        hmac_sha256_vectors(),
    )


def test_crypto_hmac_sha512_vectors(vector_test_group) -> None:
    _emit_hmac_vectors(
        vector_test_group,
        "crypto/hmac_sha512.json",
        "HMAC-SHA512",
        hmac_sha512_vectors(),
    )
