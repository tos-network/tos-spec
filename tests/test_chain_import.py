"""L2 chain import fixtures (block rewards + basic block-structure errors)."""

from __future__ import annotations

from copy import deepcopy

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.errors import ErrorCode
from tos_spec.state_digest import compute_state_digest
from tos_spec.test_accounts import MINER
from tos_spec.types import AccountState, ChainState, GlobalState
from tools.fixtures_io import state_to_json


# Keep this aligned with tos/daemon/src/config.rs + tos/daemon/src/core/hard_fork.rs.
MAXIMUM_SUPPLY = 184_000_000 * 100_000_000
EMISSION_SPEED_FACTOR = 20
MILLIS_PER_SECOND = 1000
BLOCK_TIME_TARGET_MS = 1000  # TIP-1: unified to 1s in hard_fork.rs
DEV_FEE_THRESHOLD_5PCT = 15_768_000


def get_block_reward(past_emitted_supply: int) -> int:
    if past_emitted_supply >= MAXIMUM_SUPPLY:
        return 0
    base_reward = (MAXIMUM_SUPPLY - past_emitted_supply) >> EMISSION_SPEED_FACTOR
    return (base_reward * BLOCK_TIME_TARGET_MS) // MILLIS_PER_SECOND // 180


def get_dev_fee_percent(height: int) -> int:
    return 5 if height >= DEV_FEE_THRESHOLD_5PCT else 10


def apply_empty_block_with_rewards(state: ChainState, *, height: int, emitted_supply: int) -> tuple[ChainState, int]:
    """Apply an empty block's reward distribution to the exported state surface."""
    next_state = deepcopy(state)
    reward = get_block_reward(emitted_supply)
    dev_fee = (reward * get_dev_fee_percent(height)) // 100
    miner_reward = reward - dev_fee

    miner = next_state.accounts.get(MINER)
    if miner is None:
        miner = AccountState(address=MINER, balance=0, nonce=0)
        next_state.accounts[MINER] = miner
    miner.balance += int(miner_reward)
    next_state.global_state.block_height += 1
    return next_state, reward


def _base_state(include_miner: bool) -> ChainState:
    s = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    s.global_state = GlobalState(total_supply=0, total_burned=0, total_energy=0, block_height=0, timestamp=0)
    if include_miner:
        s.accounts[MINER] = AccountState(address=MINER, balance=0, nonce=0)
    return s


def test_chain_reward_empty_block(vector_test_group) -> None:
    """Import 1 empty block and validate miner reward (dev fee applied)."""
    pre = _base_state(include_miner=True)
    post, reward = apply_empty_block_with_rewards(pre, height=1, emitted_supply=0)
    _ = reward  # left for future multi-block reward vectors

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    vector_test_group(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_reward_empty_block",
            "description": "Import one empty block; miner gets block_reward minus dev fee (10% at height 1).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {
                        "id": "b1",
                        "parents": ["genesis"],
                        "txs": [],
                    }
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
        },
    )


def test_chain_invalid_tips_count_zero(vector_test_group) -> None:
    """Block with zero tips is rejected (requires at least one parent/tip)."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)
    vector_test_group(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_tips_count_zero",
            "description": "Reject a non-genesis block with zero parents/tips.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {
                        "id": "bad",
                        "parents": [],
                        "height": 1,
                        "txs": [],
                    }
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_COUNT),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
        },
    )


def test_chain_invalid_tip_not_found(vector_test_group) -> None:
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)
    vector_test_group(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_tip_not_found",
            "description": "Reject a block referencing a missing parent hash.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {
                        "id": "bad",
                        "parents": ["11" * 32],
                        "height": 1,
                        "txs": [],
                    }
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_NOT_FOUND),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
        },
    )


def test_chain_non_tip_parent_allowed(vector_test_group) -> None:
    """Document current behavior: blocks may reference a non-tip parent (DAG fanout)."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)
    vector_test_group(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_non_tip_parent_allowed",
            "description": "Import a block that references a non-tip parent (fork from an earlier block).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    # b1 is no longer a tip (b2 is).
                    {"id": "bad", "parents": ["b1"], "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": "",
                "post_state": None,
            },
        },
    )


def test_chain_invalid_block_height(vector_test_group) -> None:
    """Reject a block with an explicit height that does not match its parents."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)
    vector_test_group(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_block_height",
            "description": "Reject a block whose declared height does not match its parents.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {
                        "id": "bad",
                        "parents": ["genesis"],
                        "height": 2,
                        "txs": [],
                    }
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_BLOCK_HEIGHT),
                "state_digest": "",
                "post_state": None,
            },
        },
    )


def test_chain_invalid_tips_count_over_limit(vector_test_group) -> None:
    """Create 4 parent blocks, then attempt to build a block with 4 tips (limit is 3)."""
    pre = _base_state(include_miner=False)  # keep export surface minimal; only checking error_code
    pre_json = state_to_json(pre)
    vector_test_group(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_tips_count_over_limit",
            "description": "Reject a block with >3 tips (parents).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    {"id": "b3", "parents": ["b2"], "txs": []},
                    {"id": "b4", "parents": ["b3"], "txs": []},
                    # Fails here.
                    {"id": "bad", "parents": ["b1", "b2", "b3", "b4"], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_COUNT),
                "state_digest": "",
                "post_state": None,
            },
        },
    )
