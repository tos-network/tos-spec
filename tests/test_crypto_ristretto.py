"""L0 Ristretto255 vectors (deterministic, spec-only)."""

from __future__ import annotations

from typing import Callable, Any

import tos_signer


def _hex(b: bytes) -> str:
    return bytes(b).hex()


def test_ristretto_vectors(
    vector_test_group: Callable[[str, dict[str, Any]], None],
) -> None:
    rel_path = "crypto/ristretto255.json"

    # Deterministic seed-based public key
    seed = 1
    pk = tos_signer.get_public_key(seed)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_public_key_seed_1",
            "description": "Public key derived from seed byte 1 (compressed Ristretto255).",
            "runnable": False,
            "input": {"kind": "ristretto255", "op": "public_key_from_seed", "seed": seed},
            "expected": {"public_key": _hex(pk)},
        },
    )

    # Additional seed-based public keys
    for seed in (2, 255):
        pk_seed = tos_signer.get_public_key(seed)
        vector_test_group(
            rel_path,
            {
                "name": f"ristretto_public_key_seed_{seed}",
                "description": f"Public key derived from seed byte {seed} (compressed Ristretto255).",
                "runnable": False,
                "input": {
                    "kind": "ristretto255",
                    "op": "public_key_from_seed",
                    "seed": seed,
                },
                "expected": {"public_key": _hex(pk_seed)},
            },
        )

    # Public key from raw private key bytes
    priv = bytes(range(1, 33))
    pk_priv = tos_signer.get_public_key_from_private(priv)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_public_key_private_1_32",
            "description": "Public key derived from raw 32-byte private key.",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "public_key_from_private",
                "private_key": _hex(priv),
            },
            "expected": {"public_key": _hex(pk_priv)},
        },
    )

    # Public key from zero private key bytes
    priv_zero = bytes([0] * 32)
    pk_priv_zero = tos_signer.get_public_key_from_private(priv_zero)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_public_key_private_zero",
            "description": "Public key derived from raw 32-byte private key (all zeros).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "public_key_from_private",
                "private_key": _hex(priv_zero),
            },
            "expected": {"public_key": _hex(pk_priv_zero)},
        },
    )

    # Public key from high private key bytes (all 0xFF)
    priv_ff = bytes([0xFF] * 32)
    pk_priv_ff = tos_signer.get_public_key_from_private(priv_ff)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_public_key_private_ff",
            "description": "Public key derived from raw 32-byte private key (all 0xFF).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "public_key_from_private",
                "private_key": _hex(priv_ff),
            },
            "expected": {"public_key": _hex(pk_priv_ff)},
        },
    )

    # Deterministic signature over fixed message (seed-based)
    message = b"tos-ristretto-test"
    sig = tos_signer.sign_data(message, seed)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_sign_seed_1",
            "description": "Schnorr signature over fixed message (seed byte 1).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "sign_data",
                "seed": seed,
                "message": _hex(message),
            },
            "expected": {
                "public_key": _hex(pk),
                "signature": _hex(sig),
            },
        },
    )

    # Signature over long message (seed-based)
    long_msg = b"tos-ristretto-long-message-" * 16
    sig_long = tos_signer.sign_data(long_msg, seed)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_sign_seed_1_long",
            "description": "Schnorr signature over long message (seed byte 1).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "sign_data",
                "seed": seed,
                "message": _hex(long_msg),
            },
            "expected": {
                "public_key": _hex(pk),
                "signature": _hex(sig_long),
            },
        },
    )

    # Signature over empty message (seed-based)
    empty_msg = b""
    sig_empty = tos_signer.sign_data(empty_msg, seed)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_sign_seed_1_empty",
            "description": "Schnorr signature over empty message (seed byte 1).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "sign_data",
                "seed": seed,
                "message": _hex(empty_msg),
            },
            "expected": {
                "public_key": _hex(pk),
                "signature": _hex(sig_empty),
            },
        },
    )

    # Deterministic signature over fixed message (raw private key)
    sig_priv = tos_signer.sign_with_key(message, priv)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_sign_private_1_32",
            "description": "Schnorr signature over fixed message (raw private key).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "sign_with_private",
                "private_key": _hex(priv),
                "message": _hex(message),
            },
            "expected": {
                "public_key": _hex(pk_priv),
                "signature": _hex(sig_priv),
            },
        },
    )

    # Deterministic signature over fixed message (raw private key, all 0xFF)
    sig_priv_ff = tos_signer.sign_with_key(message, priv_ff)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_sign_private_ff",
            "description": "Schnorr signature over fixed message (raw private key all 0xFF).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "sign_with_private",
                "private_key": _hex(priv_ff),
                "message": _hex(message),
            },
            "expected": {
                "public_key": _hex(pk_priv_ff),
                "signature": _hex(sig_priv_ff),
            },
        },
    )

    # Deterministic valid compressed point
    point = tos_signer.random_valid_point()
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_random_valid_point",
            "description": "Deterministic valid compressed Ristretto255 point (32 bytes).",
            "runnable": False,
            "input": {"kind": "ristretto255", "op": "random_valid_point"},
            "expected": {"point": _hex(point)},
        },
    )

    # Deterministic dummy CT validity proof (wire-valid bytes)
    proof = tos_signer.make_dummy_ct_validity_proof()
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_dummy_ct_validity_proof",
            "description": "Deterministic wire-valid ciphertext validity proof bytes.",
            "runnable": False,
            "input": {"kind": "ristretto255", "op": "dummy_ct_validity_proof"},
            "expected": {"proof": _hex(proof), "length": len(proof)},
        },
    )

    # Deterministic shield crypto tuple (commitment, handle, proof)
    commit, handle, proof_shield = tos_signer.make_shield_crypto(2, 100000)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_shield_crypto_seed2_amount_100k",
            "description": "Shield transfer crypto tuple (seed 2, amount 100000).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "shield_crypto",
                "seed": 2,
                "amount": 100000,
            },
            "expected": {
                "commitment": _hex(commit),
                "receiver_handle": _hex(handle),
                "proof": _hex(proof_shield),
            },
        },
    )

    commit2, handle2, proof_shield2 = tos_signer.make_shield_crypto(9, 500000000)
    vector_test_group(
        rel_path,
        {
            "name": "ristretto_shield_crypto_seed9_amount_500m",
            "description": "Shield transfer crypto tuple (seed 9, amount 500000000).",
            "runnable": False,
            "input": {
                "kind": "ristretto255",
                "op": "shield_crypto",
                "seed": 9,
                "amount": 500000000,
            },
            "expected": {
                "commitment": _hex(commit2),
                "receiver_handle": _hex(handle2),
                "proof": _hex(proof_shield2),
            },
        },
    )
