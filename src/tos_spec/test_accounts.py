"""Test account helpers backed by accounts.json and tos_signer."""

from __future__ import annotations

import json
from pathlib import Path

import tos_signer

from .encoding import encode_signing_bytes
from .types import Transaction

_ACCOUNTS_PATH = Path(__file__).resolve().parent.parent.parent / "vectors" / "accounts.json"

_accounts = json.loads(_ACCOUNTS_PATH.read_text())["accounts"]

# Named constants — 32-byte compressed Ristretto public key (= address)
MINER = bytes.fromhex(_accounts[0]["address"])
ALICE = bytes.fromhex(_accounts[1]["address"])
BOB = bytes.fromhex(_accounts[2]["address"])
CAROL = bytes.fromhex(_accounts[3]["address"])
DAVE = bytes.fromhex(_accounts[4]["address"])
EVE = bytes.fromhex(_accounts[5]["address"])
FRANK = bytes.fromhex(_accounts[6]["address"])
GRACE = bytes.fromhex(_accounts[7]["address"])
HEIDI = bytes.fromhex(_accounts[8]["address"])
IVAN = bytes.fromhex(_accounts[9]["address"])

# Map address bytes -> seed_byte (the low byte of private_key)
SEED_MAP: dict[bytes, int] = {}
for _acct in _accounts:
    _pk_bytes = bytes.fromhex(_acct["private_key"])
    _addr = bytes.fromhex(_acct["address"])
    SEED_MAP[_addr] = _pk_bytes[0]


def sign_transaction(tx: Transaction) -> bytes:
    """Sign a transaction using the test account's seed byte."""
    seed = SEED_MAP[tx.source]
    signing_bytes = encode_signing_bytes(tx)
    return bytes(tos_signer.sign_data(signing_bytes, seed))
