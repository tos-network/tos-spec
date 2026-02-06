"""Consensus block validation fixtures."""

from __future__ import annotations

from tos_spec.consensus.block_structure import (
    EXTRA_NONCE_SIZE,
    MAX_BLOCK_SIZE,
    MAX_TXS_PER_BLOCK,
    MIN_HEADER_SIZE,
    TIPS_LIMIT,
    BlockHeader,
    header_size,
    max_header_size,
    validate_limits,
    validate_timestamp,
    validate_unique_txs,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _mk_header(tips_count: int = 1, txs_count: int = 0) -> BlockHeader:
    return BlockHeader(
        version=1,
        tips=[_hash(i + 1) for i in range(tips_count)],
        timestamp=1_700_000_000_000,
        height=100,
        nonce=42,
        extra_nonce=bytes(EXTRA_NONCE_SIZE),
        miner=_hash(0xAA),
        txs_hashes=[_hash(0x80 + i) for i in range(txs_count)],
    )


# --- block_validation specs ---


def test_block_tips_within_limit(vector_test_group) -> None:
    header = _mk_header(tips_count=2)
    valid = True
    try:
        validate_limits(header)
    except ValueError:
        valid = False
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "tips_within_limit",
            "runnable": False,
            "input": {"tips_count": 2},
            "expected": {"valid": valid},
        },
    )


def test_block_tips_exceed_limit(vector_test_group) -> None:
    valid = True
    try:
        header = _mk_header(tips_count=TIPS_LIMIT + 1)
        validate_limits(header)
    except ValueError:
        valid = False
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "tips_exceed_limit",
            "runnable": False,
            "input": {"tips_count": TIPS_LIMIT + 1},
            "expected": {"valid": valid},
        },
    )


def test_block_tips_zero(vector_test_group) -> None:
    valid = True
    try:
        header = _mk_header(tips_count=0)
        validate_limits(header)
    except ValueError:
        valid = False
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "tips_zero",
            "runnable": False,
            "input": {"tips_count": 0},
            "expected": {"valid": valid},
        },
    )


def test_block_header_size_constants(vector_test_group) -> None:
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "header_size_constants",
            "runnable": False,
            "input": {"kind": "spec"},
            "expected": {
                "tips_limit": TIPS_LIMIT,
                "max_block_size": MAX_BLOCK_SIZE,
                "max_txs_per_block": MAX_TXS_PER_BLOCK,
                "min_header_size": MIN_HEADER_SIZE,
                "max_header_size": max_header_size(),
            },
        },
    )


def test_block_timestamp_valid(vector_test_group) -> None:
    now_ms = 1_700_000_060_000
    parent_ts = [1_700_000_000_000]
    ts = 1_700_000_030_000
    valid = True
    try:
        validate_timestamp(ts, parent_ts, now_ms)
    except ValueError:
        valid = False
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "timestamp_valid",
            "runnable": False,
            "input": {"timestamp_ms": ts, "parent_timestamps": parent_ts, "now_ms": now_ms},
            "expected": {"valid": valid},
        },
    )


def test_block_timestamp_too_old(vector_test_group) -> None:
    now_ms = 1_700_000_060_000
    parent_ts = [1_700_000_050_000]
    ts = 1_700_000_040_000  # Before parent
    valid = True
    try:
        validate_timestamp(ts, parent_ts, now_ms)
    except ValueError:
        valid = False
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "timestamp_too_old",
            "runnable": False,
            "input": {"timestamp_ms": ts, "parent_timestamps": parent_ts, "now_ms": now_ms},
            "expected": {"valid": valid},
        },
    )


def test_block_duplicate_txs(vector_test_group) -> None:
    txs = [_hash(1), _hash(1)]  # Duplicate
    valid = True
    try:
        validate_unique_txs(txs)
    except ValueError:
        valid = False
    vector_test_group(
        "consensus/block_validation.json",
        {
            "name": "duplicate_txs",
            "runnable": False,
            "input": {"txs_hashes": [t.hex() for t in txs]},
            "expected": {"valid": valid},
        },
    )


# --- fork_choice specs ---


def test_fork_choice_header_size(vector_test_group) -> None:
    header = _mk_header(tips_count=2, txs_count=3)
    size = header_size(header)
    vector_test_group(
        "consensus/fork_choice.json",
        {
            "name": "header_size_2tips_3txs",
            "runnable": False,
            "input": {"tips_count": 2, "txs_count": 3},
            "expected": {"header_size": size},
        },
    )
