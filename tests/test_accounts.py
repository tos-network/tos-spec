"""Deterministic test account generation.

Derives all 10 test identities from seed bytes 1..10 using tos_signer,
and collects them for output to vectors/accounts.json.
"""

from __future__ import annotations

import tos_signer

NAMES = ["Miner", "Alice", "Bob", "Carol", "Dave",
         "Eve", "Frank", "Grace", "Heidi", "Ivan"]


def _derive_account(seed_byte: int, name: str) -> dict[str, str]:
    private_key = bytes([seed_byte] + [0] * 31).hex()
    public_key = bytes(tos_signer.get_public_key(seed_byte)).hex()
    return {
        "name": name,
        "private_key": private_key,
        "public_key": public_key,
        "address": public_key,
    }


def _all_accounts() -> list[dict[str, str]]:
    return [_derive_account(i + 1, name) for i, name in enumerate(NAMES)]


def test_accounts_deterministic(accounts_collector) -> None:
    """Verify that seed bytes 1..10 produce the expected test identities."""
    accounts = _all_accounts()

    assert len(accounts) == 10
    assert accounts[0]["name"] == "Miner"
    assert accounts[1]["name"] == "Alice"
    assert accounts[1]["address"] == "f05bc1df2831717c2992d85b57e0cf3d123fd6c254257de5f784be369747b249"
    assert accounts[2]["address"] == "c29d170ab8a5b42a3520878501a87a27f9b5653fca8b0c59fc2786cf26e37824"

    for acct in accounts:
        assert len(bytes.fromhex(acct["private_key"])) == 32
        assert len(bytes.fromhex(acct["public_key"])) == 32
        assert acct["public_key"] == acct["address"]

    accounts_collector(accounts)
