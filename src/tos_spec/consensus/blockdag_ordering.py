"""BlockDAG ordering spec (from tck/specs/blockdag-ordering.md)."""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Dict, Iterable, List


STABLE_LIMIT = 24
PRUNE_SAFETY_LIMIT = STABLE_LIMIT * 10
TIPS_LIMIT = 3
TIP_DIFFICULTY_THRESHOLD = 0.91


@dataclass(frozen=True)
class TipScore:
    tip_hash: bytes
    cumulative_difficulty: int


def sort_ascending_by_cumulative_difficulty(scores: Iterable[TipScore]) -> List[TipScore]:
    return sorted(scores, key=lambda s: s.cumulative_difficulty)


def select_best_tip(candidates: Iterable[TipScore]) -> TipScore:
    candidates = list(candidates)
    if not candidates:
        raise ValueError("no candidates")
    best_diff = max(c.cumulative_difficulty for c in candidates)
    best = [c for c in candidates if c.cumulative_difficulty == best_diff]
    return min(best, key=lambda s: s.tip_hash)


def validate_tips_count(tips: List[bytes]) -> bool:
    return 1 <= len(tips) <= TIPS_LIMIT


def validate_tip_difficulty(best: int, tip: int) -> bool:
    return tip >= int(best * TIP_DIFFICULTY_THRESHOLD)


def validate_tips_difficulty(best: int, tips: Iterable[int]) -> bool:
    return all(validate_tip_difficulty(best, tip) for tip in tips)


def is_stable(current_topoheight: int, block_topoheight: int) -> bool:
    return current_topoheight - block_topoheight >= STABLE_LIMIT


def topoheight_sequence(base_topoheight: int, skipped: int, count: int) -> List[int]:
    return [base_topoheight + skipped + i for i in range(count)]


def height_from_parents(parent_heights: Iterable[int]) -> int:
    return max(parent_heights) + 1


def ensure_non_reachability(ancestor_map: Dict[bytes, List[bytes]], tips: List[bytes]) -> bool:
    tip_set = set(tips)
    for tip in tips:
        for ancestor in ancestor_map.get(tip, []):
            if ancestor in tip_set:
                return False
    return True


def generate_full_order(
    start_hash: bytes,
    get_tips: callable,
    get_cumulative_difficulty: callable,
) -> List[bytes]:
    """Deterministic ordering from a target block.

    The algorithm walks tips, sorting by cumulative difficulty ascending,
    and produces a stack-based traversal order.
    """
    processed: set[bytes] = set()
    stack = deque([start_hash])
    order: List[bytes] = []

    while stack:
        current = stack.popleft()
        if current in processed:
            continue
        processed.add(current)
        order.append(current)
        tips = get_tips(current)
        scores = [TipScore(t, get_cumulative_difficulty(t)) for t in tips]
        for score in sort_ascending_by_cumulative_difficulty(scores):
            stack.append(score.tip_hash)
    return order
