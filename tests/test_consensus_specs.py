"""Consensus spec fixtures (non-executable, spec-only vectors)."""

from __future__ import annotations

from tos_spec.consensus import blockdag_ordering as blockdag
from tos_spec.consensus import mining_pow as pow_spec


def _hex(byte: int) -> bytes:
    return bytes([byte]) * 32


def test_blockdag_tip_rules(vector_test_group) -> None:
    tips_valid = [_hex(1), _hex(2)]
    tips_invalid = []
    vector_test_group(
        "consensus/blockdag_ordering.json",
        {
            "name": "validate_tips_count_valid",
            "description": "tips count within limit",
            "runnable": False,
            "input": {"kind": "spec", "tips": [t.hex() for t in tips_valid]},
            "expected": {"success": blockdag.validate_tips_count(tips_valid)},
        },
    )
    vector_test_group(
        "consensus/blockdag_ordering.json",
        {
            "name": "validate_tips_count_invalid",
            "description": "tips count must be >= 1",
            "runnable": False,
            "input": {"kind": "spec", "tips": [t.hex() for t in tips_invalid]},
            "expected": {"success": blockdag.validate_tips_count(tips_invalid)},
        },
    )


def test_blockdag_best_tip(vector_test_group) -> None:
    scores = [
        blockdag.TipScore(tip_hash=bytes([1]) * 32, cumulative_difficulty=10),
        blockdag.TipScore(tip_hash=bytes([2]) * 32, cumulative_difficulty=12),
        blockdag.TipScore(tip_hash=bytes([3]) * 32, cumulative_difficulty=12),
    ]
    best = blockdag.select_best_tip(scores).tip_hash.hex()
    vector_test_group(
        "consensus/blockdag_ordering.json",
        {
            "name": "select_best_tip_tiebreaker",
            "description": "highest difficulty, tie by lowest hash",
            "runnable": False,
            "input": {
                "kind": "spec",
                "scores": [
                    {"tip_hash": s.tip_hash.hex(), "cumulative_difficulty": s.cumulative_difficulty}
                    for s in scores
                ],
            },
            "expected": {"best_tip": best},
        },
    )


def test_pow_rules(vector_test_group) -> None:
    diff = 1000
    target = pow_spec.target_from_difficulty(diff)
    vector_test_group(
        "consensus/mining_pow.json",
        {
            "name": "target_from_difficulty",
            "description": "target derived from difficulty",
            "runnable": False,
            "input": {"kind": "spec", "difficulty": diff},
            "expected": {"target": target},
        },
    )
    vector_test_group(
        "consensus/mining_pow.json",
        {
            "name": "randomx_key_block_height",
            "description": "RandomX key block height",
            "runnable": False,
            "input": {"kind": "spec", "height": 3500},
            "expected": {"key_block_height": pow_spec.randomx_key_block_height(3500)},
        },
    )
