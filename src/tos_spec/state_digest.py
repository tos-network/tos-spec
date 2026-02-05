"""Canonical state digest implementation (v1)."""
from __future__ import annotations

from typing import Any

from blake3 import blake3


def _hex_to_bytes(value: str | None) -> bytes:
    if value is None:
        return b""
    if not isinstance(value, str):
        raise TypeError("hex value must be string")
    v = value[2:] if value.startswith(("0x", "0X")) else value
    if v == "":
        return b""
    return bytes.fromhex(v)


def _u64_be(value: int) -> bytes:
    if value < 0:
        raise ValueError("u64 must be non-negative")
    return int(value).to_bytes(8, "big", signed=False)


def compute_state_digest(post_state: dict[str, Any]) -> str:
    """Compute state digest v1 from post_state.

    Fields are encoded in canonical order and hashed with BLAKE3-256.
    """
    gs = post_state.get("global_state", {}) if isinstance(post_state, dict) else {}
    buf = bytearray()
    for field in ("total_supply", "total_burned", "total_energy", "block_height", "timestamp"):
        buf += _u64_be(int(gs.get(field, 0)))

    accounts = post_state.get("accounts", []) if isinstance(post_state, dict) else []
    sortable = []
    for acc in accounts:
        addr_hex = acc.get("address", "")
        addr = _hex_to_bytes(addr_hex)
        if len(addr) != 32:
            raise ValueError(f"address must be 32 bytes, got {len(addr)}")
        sortable.append((addr, acc))
    sortable.sort(key=lambda x: x[0])

    for addr, acc in sortable:
        buf += addr
        for field in ("balance", "nonce", "frozen", "energy", "flags"):
            buf += _u64_be(int(acc.get(field, 0)))
        data = _hex_to_bytes(acc.get("data", ""))
        buf += _u64_be(len(data))
        buf += data

    return blake3(buf).hexdigest()
