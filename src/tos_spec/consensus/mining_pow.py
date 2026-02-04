"""Mining and PoW spec (from tck/specs/mining-pow.md)."""

from __future__ import annotations

from dataclasses import dataclass


BLOCK_TIME_TARGET_MS = 15_000
DIFFICULTY_ADJUSTMENT_BLOCKS = 720
MIN_DIFFICULTY = 1
MAX_DIFFICULTY_INCREASE = 4.0
MAX_DIFFICULTY_DECREASE = 0.25

HALVING_INTERVAL = 2_100_000
COINBASE_MATURITY = 100
MAX_EXTRA_NONCE_HEX = 128

MAX_HASH = (1 << 256) - 1


def target_from_difficulty(difficulty: int) -> int:
    if difficulty <= 0:
        raise ValueError("difficulty must be positive")
    return MAX_HASH // difficulty


def is_valid_pow(hash_bytes: bytes, difficulty: int) -> bool:
    target = target_from_difficulty(difficulty)
    value = int.from_bytes(hash_bytes, "big")
    return value < target


def randomx_key_block_height(height: int) -> int:
    return (height // 2048) * 2048


def block_reward(height: int, coin_value: int) -> int:
    era = height // HALVING_INTERVAL
    initial_reward = 50 * coin_value
    return initial_reward >> era


def validate_extra_nonce_hex(extra_nonce_hex: str) -> None:
    if len(extra_nonce_hex) > MAX_EXTRA_NONCE_HEX:
        raise ValueError("extra_nonce hex too long")


def validate_difficulty_adjustment(prev: int, next_diff: int) -> None:
    if prev <= 0:
        raise ValueError("previous difficulty must be positive")
    max_inc = int(prev * MAX_DIFFICULTY_INCREASE)
    min_dec = max(1, int(prev * MAX_DIFFICULTY_DECREASE))
    if next_diff > max_inc or next_diff < min_dec:
        raise ValueError("difficulty change out of bounds")


@dataclass(frozen=True)
class StratumJob:
    job_id: str
    blob_hex: str
    target_hex: str
    height: int
