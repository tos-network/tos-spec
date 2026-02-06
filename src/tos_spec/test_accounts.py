"""Test account helpers derived from tos_signer seed bytes.

Accounts are deterministically derived from seed bytes 1..10 via Ristretto
scalar multiplication. No external file dependency at import time.
"""

from __future__ import annotations

import time

import tos_signer

from .encoding import encode_signing_bytes
from .types import Transaction

# Derive public keys directly from seed bytes (1..10).
MINER = bytes(tos_signer.get_public_key(1))
ALICE = bytes(tos_signer.get_public_key(2))
BOB = bytes(tos_signer.get_public_key(3))
CAROL = bytes(tos_signer.get_public_key(4))
DAVE = bytes(tos_signer.get_public_key(5))
EVE = bytes(tos_signer.get_public_key(6))
FRANK = bytes(tos_signer.get_public_key(7))
GRACE = bytes(tos_signer.get_public_key(8))
HEIDI = bytes(tos_signer.get_public_key(9))
IVAN = bytes(tos_signer.get_public_key(10))

# Map address bytes -> seed_byte
SEED_MAP: dict[bytes, int] = {
    bytes(tos_signer.get_public_key(i)): i for i in range(1, 11)
}


def sign_transaction(tx: Transaction) -> bytes:
    """Sign a transaction using the test account's seed byte."""
    seed = SEED_MAP[tx.source]
    signing_bytes = encode_signing_bytes(tx, current_time=int(time.time()))
    return bytes(tos_signer.sign_data(signing_bytes, seed))
