"""Hash algorithm assignments (from tck/specs/hash-algorithms.md)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from blake3 import blake3


HASH_SIZE = 32


@dataclass(frozen=True)
class HashAssignment:
    purpose: str
    algorithm: str
    output_size: int
    input_spec: str


ASSIGNMENTS = [
    HashAssignment("txid", "BLAKE3", 32, "serialized transaction bytes"),
    HashAssignment("block_hash", "BLAKE3", 32, "serialized block header bytes"),
    HashAssignment("signature_hash", "SHA3-512", 64, "pubkey || message || commitment_point"),
    HashAssignment("contract_address", "BLAKE3", 32, "0xff || deployer_pubkey || code_hash"),
    HashAssignment("node_identity", "SHA3-256", 32, "ed25519 public key bytes"),
]

ADDRESS_HRP_MAINNET = "tos"
ADDRESS_HRP_TESTNET = "tst"


def address_hrp(is_mainnet: bool) -> str:
    """Bech32 human-readable prefix (address encoding is not a hash)."""
    return ADDRESS_HRP_MAINNET if is_mainnet else ADDRESS_HRP_TESTNET


def blake3_hash(data: bytes) -> bytes:
    return blake3(data).digest()


def txid(serialized_tx: bytes) -> bytes:
    return blake3_hash(serialized_tx)


def block_hash(serialized_header: bytes) -> bytes:
    return blake3_hash(serialized_header)


def signature_hash(pubkey: bytes, message: bytes, commitment_point: bytes) -> bytes:
    hasher = hashlib.sha3_512()
    hasher.update(pubkey)
    hasher.update(message)
    hasher.update(commitment_point)
    return hasher.digest()


def compute_deterministic_contract_address(deployer_pubkey: bytes, bytecode: bytes) -> bytes:
    code_hash = blake3_hash(bytecode)
    data = b"\xff" + deployer_pubkey + code_hash
    return blake3_hash(data)


def node_identity_hash(pubkey: bytes) -> bytes:
    return hashlib.sha3_256(pubkey).digest()
