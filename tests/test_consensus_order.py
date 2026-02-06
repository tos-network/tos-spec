"""Consensus ordering fixtures (finality, transaction_ordering)."""

from __future__ import annotations

from tos_spec.consensus.blockdag_ordering import (
    STABLE_LIMIT,
    PRUNE_SAFETY_LIMIT,
    TipScore,
    height_from_parents,
    is_stable,
    select_best_tip,
    validate_tips_count,
    validate_tips_difficulty,
)
from tos_spec.consensus.mining_pow import (
    BLOCK_TIME_TARGET_MS,
    COINBASE_MATURITY,
    HALVING_INTERVAL,
    block_reward,
    randomx_key_block_height,
    target_from_difficulty,
)
from tos_spec.config import COIN_VALUE


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


# --- finality specs ---


def test_finality_stable_check(vector_test_group) -> None:
    current = 1000
    block_topo = 970
    result = is_stable(current, block_topo)
    vector_test_group(
        "consensus/finality.json",
        {
            "name": "stable_check_true",
            "runnable": False,
            "input": {"current_topoheight": current, "block_topoheight": block_topo},
            "expected": {"is_stable": result},
        },
    )


def test_finality_unstable_check(vector_test_group) -> None:
    current = 1000
    block_topo = 990
    result = is_stable(current, block_topo)
    vector_test_group(
        "consensus/finality.json",
        {
            "name": "stable_check_false",
            "runnable": False,
            "input": {"current_topoheight": current, "block_topoheight": block_topo},
            "expected": {"is_stable": result},
        },
    )


def test_finality_constants(vector_test_group) -> None:
    vector_test_group(
        "consensus/finality.json",
        {
            "name": "finality_constants",
            "runnable": False,
            "input": {"kind": "spec"},
            "expected": {
                "stable_limit": STABLE_LIMIT,
                "prune_safety_limit": PRUNE_SAFETY_LIMIT,
                "block_time_target_ms": BLOCK_TIME_TARGET_MS,
                "coinbase_maturity": COINBASE_MATURITY,
            },
        },
    )


def test_finality_height_from_parents(vector_test_group) -> None:
    parents = [10, 12, 11]
    result = height_from_parents(parents)
    vector_test_group(
        "consensus/finality.json",
        {
            "name": "height_from_parents",
            "runnable": False,
            "input": {"parent_heights": parents},
            "expected": {"height": result},
        },
    )


def test_finality_block_reward(vector_test_group) -> None:
    height = 100
    reward = block_reward(height, COIN_VALUE)
    vector_test_group(
        "consensus/finality.json",
        {
            "name": "block_reward_era0",
            "runnable": False,
            "input": {"height": height, "coin_value": COIN_VALUE},
            "expected": {"reward": reward},
        },
    )


def test_finality_block_reward_halved(vector_test_group) -> None:
    height = HALVING_INTERVAL + 100
    reward = block_reward(height, COIN_VALUE)
    vector_test_group(
        "consensus/finality.json",
        {
            "name": "block_reward_era1",
            "runnable": False,
            "input": {"height": height, "coin_value": COIN_VALUE},
            "expected": {"reward": reward},
        },
    )


# --- transaction_ordering specs ---


def test_ordering_tips_validation(vector_test_group) -> None:
    tips_valid = [_hash(1), _hash(2)]
    tips_empty = []
    vector_test_group(
        "consensus/transaction_ordering.json",
        {
            "name": "tips_count_valid",
            "runnable": False,
            "input": {"tips": [t.hex() for t in tips_valid]},
            "expected": {"valid": validate_tips_count(tips_valid)},
        },
    )
    vector_test_group(
        "consensus/transaction_ordering.json",
        {
            "name": "tips_count_empty",
            "runnable": False,
            "input": {"tips": []},
            "expected": {"valid": validate_tips_count(tips_empty)},
        },
    )


def test_ordering_best_tip_selection(vector_test_group) -> None:
    scores = [
        TipScore(tip_hash=_hash(1), cumulative_difficulty=100),
        TipScore(tip_hash=_hash(2), cumulative_difficulty=120),
        TipScore(tip_hash=_hash(3), cumulative_difficulty=120),
    ]
    best = select_best_tip(scores)
    vector_test_group(
        "consensus/transaction_ordering.json",
        {
            "name": "best_tip_tiebreaker",
            "runnable": False,
            "input": {
                "scores": [
                    {"tip_hash": s.tip_hash.hex(), "cumulative_difficulty": s.cumulative_difficulty}
                    for s in scores
                ],
            },
            "expected": {"best_tip": best.tip_hash.hex()},
        },
    )


def test_ordering_tips_difficulty(vector_test_group) -> None:
    best_diff = 1000
    tip_diffs = [920, 950]  # 920 >= 1000 * 0.91 = 910
    result = validate_tips_difficulty(best_diff, tip_diffs)
    vector_test_group(
        "consensus/transaction_ordering.json",
        {
            "name": "tips_difficulty_valid",
            "runnable": False,
            "input": {"best_difficulty": best_diff, "tip_difficulties": tip_diffs},
            "expected": {"valid": result},
        },
    )


def test_ordering_randomx_key_block(vector_test_group) -> None:
    height = 5000
    key_height = randomx_key_block_height(height)
    vector_test_group(
        "consensus/transaction_ordering.json",
        {
            "name": "randomx_key_block",
            "runnable": False,
            "input": {"height": height},
            "expected": {"key_block_height": key_height},
        },
    )


def test_ordering_target_from_difficulty(vector_test_group) -> None:
    diff = 1000
    target = target_from_difficulty(diff)
    vector_test_group(
        "consensus/transaction_ordering.json",
        {
            "name": "target_from_difficulty",
            "runnable": False,
            "input": {"difficulty": diff},
            "expected": {"target": target},
        },
    )
