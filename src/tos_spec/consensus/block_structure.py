"""Block structure spec (from tck/specs/block-structure.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from blake3 import blake3


TIPS_LIMIT = 3
MAX_BLOCK_SIZE = 1_310_720
MAX_TXS_PER_BLOCK = 10_000
MAX_TRANSACTION_SIZE = 1_048_576
EXTRA_NONCE_SIZE = 32
HEADER_WORK_SIZE = 73
BLOCK_WORK_SIZE = 112
MAX_TIPS = TIPS_LIMIT
MIN_HEADER_SIZE = 91


def max_header_size() -> int:
    # 90 fixed + tips + txs + miner + vrf flag + vrf data (max)
    fixed = 90
    tips = MAX_TIPS * 32
    txs = 2 + MAX_TXS_PER_BLOCK * 32
    vrf = 1 + 161
    return fixed + tips + txs + vrf


@dataclass
class BlockVrfData:
    public_key: bytes
    output: bytes
    proof: bytes
    binding_signature: bytes


@dataclass
class BlockHeader:
    version: int
    tips: List[bytes]
    timestamp: int
    height: int
    nonce: int
    extra_nonce: bytes
    miner: bytes
    txs_hashes: List[bytes]
    vrf: Optional[BlockVrfData] = None


def serialize_header(header: BlockHeader) -> bytes:
    if len(header.extra_nonce) != EXTRA_NONCE_SIZE:
        raise ValueError("extra_nonce must be 32 bytes")
    if len(header.tips) > TIPS_LIMIT:
        raise ValueError("tips exceed TIPS_LIMIT")
    if len(header.miner) != 32:
        raise ValueError("miner must be 32 bytes")
    for tip in header.tips:
        if len(tip) != 32:
            raise ValueError("tip hash must be 32 bytes")
    for tx in header.txs_hashes:
        if len(tx) != 32:
            raise ValueError("tx hash must be 32 bytes")

    out = bytearray()
    out.append(header.version & 0xFF)
    out.extend(header.height.to_bytes(8, "big"))
    out.extend(header.timestamp.to_bytes(8, "big"))
    out.extend(header.nonce.to_bytes(8, "big"))
    out.extend(header.extra_nonce)
    out.append(len(header.tips) & 0xFF)
    for tip in header.tips:
        out.extend(tip)
    out.extend(len(header.txs_hashes).to_bytes(2, "big"))
    for tx in header.txs_hashes:
        out.extend(tx)
    out.extend(header.miner)
    out.append(1 if header.vrf is not None else 0)
    if header.vrf is not None:
        out.extend(header.vrf.public_key)
        out.extend(header.vrf.output)
        out.extend(header.vrf.proof)
        out.extend(header.vrf.binding_signature)
    return bytes(out)


def block_hash(serialized_header: bytes) -> bytes:
    return blake3(serialized_header).digest()


def tips_hash(tips: List[bytes]) -> bytes:
    data = b"".join(tips)
    return blake3(data).digest()


def txs_hash(txs_hashes: List[bytes]) -> bytes:
    data = b"".join(txs_hashes)
    return blake3(data).digest()


def work_hash(version: int, height: int, tips: List[bytes], txs_hashes: List[bytes]) -> bytes:
    data = bytearray()
    data.append(version & 0xFF)
    data.extend(height.to_bytes(8, "big"))
    data.extend(tips_hash(tips))
    data.extend(txs_hash(txs_hashes))
    return blake3(bytes(data)).digest()


def pow_hash_input(
    work_hash_bytes: bytes,
    timestamp: int,
    nonce: int,
    extra_nonce: bytes,
    miner: bytes,
) -> bytes:
    data = bytearray()
    data.extend(work_hash_bytes)
    data.extend(timestamp.to_bytes(8, "big"))
    data.extend(nonce.to_bytes(8, "big"))
    data.extend(extra_nonce)
    data.extend(miner)
    return bytes(data)


def header_size(header: BlockHeader) -> int:
    """Compute serialized header size."""
    size = 1 + 8 + 8 + 8 + EXTRA_NONCE_SIZE
    size += 1 + len(header.tips) * 32
    size += 2 + len(header.txs_hashes) * 32
    size += 32  # miner
    size += 1  # vrf flag
    if header.vrf is not None:
        size += 32 + 64 + 32 + 64
    return size


def validate_limits(header: BlockHeader) -> None:
    if not (1 <= len(header.tips) <= TIPS_LIMIT):
        raise ValueError("tips count out of range")
    if len(header.txs_hashes) > MAX_TXS_PER_BLOCK:
        raise ValueError("txs exceed MAX_TXS_PER_BLOCK")
    size = header_size(header)
    if size < MIN_HEADER_SIZE or size > max_header_size():
        raise ValueError("header size out of bounds")


def validate_timestamp(timestamp_ms: int, parent_timestamps: List[int], now_ms: int) -> None:
    if parent_timestamps and timestamp_ms <= max(parent_timestamps):
        raise ValueError("timestamp must be greater than parents")
    if timestamp_ms > now_ms + 60_000:
        raise ValueError("timestamp too far in future")


def validate_unique_txs(txs_hashes: List[bytes]) -> None:
    if len(set(txs_hashes)) != len(txs_hashes):
        raise ValueError("duplicate transaction hashes")
