"""L2 chain import fixtures (block rewards + basic block-structure errors)."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from tos_spec.config import CHAIN_ID_DEVNET
from tos_spec.encoding import encode_transaction
from tos_spec.errors import ErrorCode
from tos_spec.state_digest import compute_state_digest
from tos_spec.state_transition import apply_block
from tos_spec.test_accounts import ALICE, BOB, MINER, sign_transaction
from tos_spec.types import (
    AccountState,
    ChainState,
    DelegationEntry,
    EnergyPayload,
    FreezeDuration,
    FeeType,
    GlobalState,
    MultisigConfig,
    Transaction,
    TransactionType,
    TransferPayload,
    AgentAccountMeta,
    TxVersion,
)
from tools.fixtures_io import state_to_json
from tools.fixtures_io import tx_to_json


_DAEMON_EXPECTED = json.loads(
    (Path(__file__).parent / "data" / "chain_import_daemon_expected.json").read_text()
)


def _apply_daemon_expected(vector: dict) -> dict:
    name = vector.get("name")
    override = _DAEMON_EXPECTED.get(name) if name else None
    if not override:
        return vector
    updated = deepcopy(vector)
    updated["expected"] = {
        "success": override["success"],
        "error_code": int(override["error_code"]),
        "state_digest": override["state_digest"],
        "post_state": override["post_state"],
    }
    updated.pop("runnable", None)
    return updated


def _vector_test_group(vector_test_group):
    def _inner(path, data):
        return vector_test_group(path, _apply_daemon_expected(data))

    return _inner


# Keep this aligned with tos/daemon/src/config.rs + tos/daemon/src/core/hard_fork.rs.
MAXIMUM_SUPPLY = 184_000_000 * 100_000_000
EMISSION_SPEED_FACTOR = 20
MILLIS_PER_SECOND = 1000
BLOCK_TIME_TARGET_MS = 1000  # TIP-1: unified to 1s in hard_fork.rs
DEV_FEE_THRESHOLD_5PCT = 15_768_000
SIDE_BLOCK_REWARD_PERCENT = 30  # daemon/src/config.rs


def get_block_reward(past_emitted_supply: int) -> int:
    if past_emitted_supply >= MAXIMUM_SUPPLY:
        return 0
    base_reward = (MAXIMUM_SUPPLY - past_emitted_supply) >> EMISSION_SPEED_FACTOR
    return (base_reward * BLOCK_TIME_TARGET_MS) // MILLIS_PER_SECOND // 180


def get_dev_fee_percent(height: int) -> int:
    return 5 if height >= DEV_FEE_THRESHOLD_5PCT else 10


def apply_empty_block_with_rewards(
    state: ChainState,
    *,
    height: int,
    emitted_supply: int,
    side_reward_percent: int | None = None,
) -> tuple[ChainState, int]:
    """Apply an empty block's reward distribution to the exported state surface."""
    next_state = deepcopy(state)
    # Match daemon: apply dev fee to the pre-divide "base_reward" amount, then divide.
    # This matters across multiple blocks because the right-shift changes base_reward.
    if emitted_supply >= MAXIMUM_SUPPLY:
        reward = 0
        miner_reward = 0
    else:
        base_reward = (MAXIMUM_SUPPLY - emitted_supply) >> EMISSION_SPEED_FACTOR
        reward = (base_reward * BLOCK_TIME_TARGET_MS) // MILLIS_PER_SECOND // 180
        dev_fee_base = (base_reward * get_dev_fee_percent(height)) // 100
        miner_base = base_reward - dev_fee_base
        miner_reward = (miner_base * BLOCK_TIME_TARGET_MS) // MILLIS_PER_SECOND // 180

    # Side blocks get a reduced reward percentage (applies to both total emission and miner share).
    if side_reward_percent is not None:
        reward = (reward * side_reward_percent) // 100
        miner_reward = (miner_reward * side_reward_percent) // 100

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


def _tx_state() -> ChainState:
    s = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    s.global_state = GlobalState(total_supply=0, total_burned=0, total_energy=0, block_height=0, timestamp=0)
    s.accounts[MINER] = AccountState(address=MINER, balance=0, nonce=0)
    s.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=0)
    s.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return s


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _mk_transfer(sender: bytes, receiver: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=amount)],
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_burn(sender: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.BURN,
        payload={"asset": _hash(0), "amount": amount},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_multisig(sender: bytes, nonce: int, threshold: int, participants: list[bytes], fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.MULTISIG,
        payload={"threshold": threshold, "participants": participants},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_agent_account(sender: bytes, nonce: int, payload: dict, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.AGENT_ACCOUNT,
        payload=payload,
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_energy_freeze(sender: bytes, nonce: int, amount: int, days: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos",
            amount=amount,
            duration=FreezeDuration(days=days),
        ),
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_energy_delegate(
    sender: bytes, nonce: int, delegatees: list[DelegationEntry], days: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos_delegate",
            delegatees=delegatees,
            duration=FreezeDuration(days=days),
        ),
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_deploy_contract(sender: bytes, nonce: int, module: bytes, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.DEPLOY_CONTRACT,
        payload={"module": module},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_invoke_contract(sender: bytes, nonce: int, contract: bytes, entry_id: int, max_gas: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.INVOKE_CONTRACT,
        payload={
            "contract": contract,
            "deposits": [],
            "entry_id": entry_id,
            "max_gas": max_gas,
            "parameters": [],
        },
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_register_name(sender: bytes, nonce: int, name: str, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.REGISTER_NAME,
        payload={"name": name},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_uno_empty(sender: bytes, nonce: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.UNO_TRANSFERS,
        payload={"transfers": []},
        fee=fee,
        fee_type=FeeType.UNO,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_shield_empty(sender: bytes, nonce: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.SHIELD_TRANSFERS,
        payload={"transfers": []},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_unshield_empty(sender: bytes, nonce: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.UNSHIELD_TRANSFERS,
        payload={"transfers": []},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_transfer_energy_fee(sender: bytes, receiver: bytes, nonce: int, amount: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=amount)],
        fee=fee,
        fee_type=FeeType.ENERGY,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _tx_entry(tx: Transaction) -> dict:
    tx.signature = sign_transaction(tx)
    tx_json = tx_to_json(tx)
    wire_hex = encode_transaction(tx).hex()
    return {"wire_hex": wire_hex, "tx": tx_json}


def _tx_entry_with_signature(tx: Transaction, *, sign: bool) -> dict:
    if sign:
        tx.signature = sign_transaction(tx)
    else:
        tx.signature = bytes(64)
    tx_json = tx_to_json(tx)
    wire_hex = encode_transaction(tx).hex()
    return {"wire_hex": wire_hex, "tx": tx_json}


def _tx_entry_allow_invalid(tx: Transaction) -> dict:
    """Best-effort wire encoding for intentionally invalid payloads."""
    tx.signature = bytes(64)
    tx_json = tx_to_json(tx)
    try:
        wire_hex = encode_transaction(tx).hex()
    except Exception:
        wire_hex = ""
    return {"wire_hex": wire_hex, "tx": tx_json}


def apply_block_with_rewards(
    state: ChainState,
    txs: list[Transaction],
    *,
    height: int,
    emitted_supply: int,
    side_reward_percent: int | None = None,
) -> tuple[ChainState, int]:
    """Apply a tx block then reward the miner (without double-advancing height)."""
    next_state, result = apply_block(state, txs)
    if not result.ok:
        raise AssertionError(f"block txs failed: {result.error}")

    if emitted_supply >= MAXIMUM_SUPPLY:
        reward = 0
        miner_reward = 0
    else:
        base_reward = (MAXIMUM_SUPPLY - emitted_supply) >> EMISSION_SPEED_FACTOR
        reward = (base_reward * BLOCK_TIME_TARGET_MS) // MILLIS_PER_SECOND // 180
        dev_fee_base = (base_reward * get_dev_fee_percent(height)) // 100
        miner_base = base_reward - dev_fee_base
        miner_reward = (miner_base * BLOCK_TIME_TARGET_MS) // MILLIS_PER_SECOND // 180

    if side_reward_percent is not None:
        reward = (reward * side_reward_percent) // 100
        miner_reward = (miner_reward * side_reward_percent) // 100

    miner = next_state.accounts.get(MINER)
    if miner is None:
        miner = AccountState(address=MINER, balance=0, nonce=0)
        next_state.accounts[MINER] = miner
    miner.balance += int(miner_reward)
    return next_state, reward


def test_chain_reward_empty_block(vector_test_group) -> None:
    """Import 1 empty block and validate miner reward (dev fee applied)."""
    pre = _base_state(include_miner=True)
    post, reward = apply_empty_block_with_rewards(pre, height=1, emitted_supply=0)
    _ = reward  # left for future multi-block reward vectors

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
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


def test_chain_reward_two_empty_blocks(vector_test_group) -> None:
    """Import 2 empty blocks and validate cumulative miner reward."""
    pre = _base_state(include_miner=True)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_reward_two_empty_blocks",
            "description": "Import two empty blocks; miner rewards accumulate (dev fee 10% at these heights).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
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


def test_chain_explicit_height_two_blocks(vector_test_group) -> None:
    """Import 2 empty blocks with explicit heights."""
    pre = _base_state(include_miner=True)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_explicit_height_two_blocks",
            "description": "Import two empty blocks with explicit height fields (1 then 2).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
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


def test_chain_invalid_reachability_ancestor_parent(vector_test_group) -> None:
    """Reject a block whose parents are not mutually reachable (one is ancestor of the other)."""
    pre = _base_state(include_miner=True)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_reachability_ancestor_parent",
            "description": "Reject a block that references parents where one is an ancestor of the other.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    # b1 is an ancestor of b2: should violate reachability rules.
                    {"id": "bad", "parents": ["b1", "b2"], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_REACHABILITY),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
        },
    )


def test_chain_invalid_timestamp_too_old(vector_test_group) -> None:
    """Reject a block whose timestamp is less than its parent."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    # Expected post-state is after importing b1 only.
    post, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=0)
    _ = r1
    post_json = state_to_json(post)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_timestamp_too_old",
            "description": "Reject a block with timestamp_ms less than its parent timestamp.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    # Let daemon choose a valid timestamp >= genesis/now.
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    # Force timestamp < parent.
                    {"id": "bad", "parents": ["b1"], "timestamp_ms": 0, "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.TIMESTAMP_TOO_OLD),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
        },
    )


def test_chain_invalid_timestamp_too_new(vector_test_group) -> None:
    """Reject a block whose timestamp is far in the future."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    # Expected post-state is after importing b1 only.
    post, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=0)
    _ = r1
    post_json = state_to_json(post)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_timestamp_too_new",
            "description": "Reject a block with timestamp_ms far in the future.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    # Let daemon choose a valid timestamp >= genesis/now.
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    # Guaranteed to be > system_time + allowed drift.
                    {"id": "bad", "parents": ["b1"], "timestamp_ms": 18446744073709551615, "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.TIMESTAMP_TOO_NEW),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
        },
    )


def test_chain_fork_then_merge_rewards(vector_test_group) -> None:
    """Import a small fork then merge; rewards should accumulate for each imported block."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (height 2)
    emitted += r2
    # In a fork at the same height, one competing block becomes a side block with reduced reward.
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (height 2, fork from b1; side block)
    emitted += r3
    post, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # merge (height 3)
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_fork_then_merge_rewards",
            "description": "Import a fork (b2 and b3) then a merge (b4 with two parents); miner reward accumulates for all imported blocks.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": []},
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


def test_chain_two_side_blocks_same_height_rewards(vector_test_group) -> None:
    """Import 3 competing blocks at the same height then merge; side blocks get reduced rewards."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side #1 => 30%)
    emitted += r3
    # Ordering nuance: the DAG can order the merge before all side blocks are ordered.
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b5 (merge)
    emitted += r4
    post, r5 = apply_empty_block_with_rewards(
        s4,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2,
    )  # b4 (side #2 => 15%)
    emitted += r5
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_two_side_blocks_same_height_rewards",
            "description": "Import b2/b3/b4 all at height 2 from b1 then merge with b5; side blocks receive reduced rewards (30% then 15%).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b5", "parents": ["b2", "b3", "b4"], "height": 3, "txs": []},
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
    _vector_test_group(vector_test_group)(
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


def test_chain_three_side_blocks_same_height_rewards(vector_test_group) -> None:
    """Import 4 competing blocks at the same height then merge; side rewards decay per side-block count."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side #1 => 30%)
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b5 (merge)
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(
        s4,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2,
    )  # b4 (side #2 => 15%)
    emitted += r5
    post, r6 = apply_empty_block_with_rewards(
        s5,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 4,
    )  # b6 (side #3 => 7%)
    emitted += r6
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_three_side_blocks_same_height_rewards",
            "description": "Import b2/b3/b4/b6 at height 2 then merge; side blocks receive 30%, 15%, then 7% rewards.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b5", "parents": ["b2", "b3", "b4"], "height": 3, "txs": []},
                    {"id": "b6", "parents": ["b1"], "height": 2, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_invalid_tip_not_found(vector_test_group) -> None:
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)
    _vector_test_group(vector_test_group)(
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
    _vector_test_group(vector_test_group)(
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
    _vector_test_group(vector_test_group)(
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
    _vector_test_group(vector_test_group)(
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


def test_chain_fork_longer_branch_then_merge_rewards(vector_test_group) -> None:
    """Import a fork where one branch extends; rewards accrue for all blocks including side block."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side)
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 (extends b3)
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(s4, height=4, emitted_supply=emitted)  # b5 (extends b4)
    emitted += r5
    post, r6 = apply_empty_block_with_rewards(s5, height=5, emitted_supply=emitted)  # b6 (merge)
    emitted += r6
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_fork_longer_branch_then_merge_rewards",
            "description": "Import a fork that grows longer before merge; miner rewards accrue for each block including side block b3.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b3"], "height": 3, "txs": []},
                    {"id": "b5", "parents": ["b4"], "height": 4, "txs": []},
                    {"id": "b6", "parents": ["b2", "b5"], "height": 5, "txs": []},
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


def test_chain_blocks_with_txs_success(vector_test_group) -> None:
    """Import two blocks with transfers; balances, nonces, and rewards accumulate."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx1 = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=1, amount=200_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_block_with_rewards(pre, [tx1], height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_block_with_rewards(s1, [tx2], height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_blocks_with_txs_success",
            "description": "Import two blocks containing transfers; tx effects and miner rewards are reflected in post-state.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(tx1)]},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(tx2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_four_side_blocks_same_height_rewards(vector_test_group) -> None:
    """Import 5 competing blocks at the same height; side rewards decay to the minimum."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side #1 => 30%)
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(
        s3,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2,
    )  # b4 (side #2 => 15%)
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(
        s4,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 4,
    )  # b5 (side #3 => 7%)
    emitted += r5
    post, r6 = apply_empty_block_with_rewards(
        s5,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 6,
    )  # b6 (side #4 => 5%)
    emitted += r6
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_four_side_blocks_same_height_rewards",
            "description": "Import five blocks at height 2; side blocks receive 30%, 15%, 7%, then 5% rewards.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b5", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b6", "parents": ["b1"], "height": 2, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_reject_atomic_on_second_tx(vector_test_group) -> None:
    """Reject a block where the second tx has a nonce gap; block is atomic."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx1 = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=2, amount=1, fee=100_000)  # nonce gap (expected 1)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_reject_atomic_on_second_tx",
            "description": "Import a block with two txs where the second has nonce too high; entire block is rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx1), _tx_entry(tx2)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.NONCE_TOO_HIGH),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_blocks_with_txs_invalid_second_block(vector_test_group) -> None:
    """Import a valid tx block then reject a second block with a nonce gap."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx1 = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=1, amount=200_000, fee=100_000)
    tx_bad = _mk_transfer(ALICE, BOB, nonce=3, amount=1, fee=100_000)  # nonce gap (expected 2)

    emitted = 0
    post, r1 = apply_block_with_rewards(pre, [tx1], height=1, emitted_supply=emitted)
    emitted += r1
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_blocks_with_txs_invalid_second_block",
            "description": "Import one valid tx block then reject second block with nonce-too-high tx; state reflects only block1.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(tx1)]},
                    {"id": "bad", "parents": ["b1"], "txs": [_tx_entry(tx2), _tx_entry(tx_bad)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.NONCE_TOO_HIGH),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_burn_then_tx_insufficient_balance_rejected(vector_test_group) -> None:
    """Burn then transfer in same block; transfer fails so entire block is rejected and burn does not apply."""
    pre = _tx_state()
    pre.accounts[ALICE].balance = 250_000
    pre_json = state_to_json(pre)

    burn = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    # After burn+fee, balance would be 50_000; this transfer would fail.
    xfer = _mk_transfer(ALICE, BOB, nonce=1, amount=60_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_burn_then_tx_insufficient_balance_rejected",
            "description": "Burn then transfer in the same block; transfer fails, so block is rejected and burn is rolled back.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(burn), _tx_entry(xfer)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INSUFFICIENT_BALANCE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_merge_before_parent_invalid_order(vector_test_group) -> None:
    """Reject a merge that references a parent id not yet imported."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_merge_before_parent_invalid_order",
            "description": "Merge references b2 before b2 is imported; should be INVALID_TIPS_NOT_FOUND.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "bad", "parents": ["b1", "b2"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_NOT_FOUND),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_invalid_reachability_three_tips(vector_test_group) -> None:
    """Reject a block whose tips include an ancestor of another tip (3 tips case)."""
    pre = _base_state(include_miner=True)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    post, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    _ = emitted

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_reachability_three_tips",
            "description": "Reject a block whose tips include an ancestor (b1) and its descendant (b2).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    {"id": "bad", "parents": ["b1", "b2", "genesis"], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_REACHABILITY),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
        },
    )


def test_chain_burn_accumulates_across_blocks(vector_test_group) -> None:
    """Burns across blocks should accumulate in total_burned while rewards still apply."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn1 = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    burn2 = _mk_burn(ALICE, nonce=1, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_block_with_rewards(pre, [burn1], height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_block_with_rewards(s1, [burn2], height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_burn_accumulates_across_blocks",
            "description": "Import two blocks with burn txs; total_burned accumulates while miner rewards apply.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(burn1)]},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(burn2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_side_block_rewards_then_burn(vector_test_group) -> None:
    """Side-block rewards + burn in a later block should combine correctly."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side)
    emitted += r3

    burn = _mk_burn(ALICE, nonce=0, amount=75_000, fee=100_000)
    post, r4 = apply_block_with_rewards(s3, [burn], height=3, emitted_supply=emitted)  # b4
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_side_block_rewards_then_burn",
            "description": "Import fork with a side block, then a burn tx; rewards + total_burned reflect all.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    {"id": "b3", "parents": ["b1"], "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "txs": [_tx_entry(burn)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_invalid_reachability_four_tips(vector_test_group) -> None:
    """Reject a block whose tips include multiple ancestor/descendant pairs."""
    pre = _base_state(include_miner=True)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    post, r3 = apply_empty_block_with_rewards(s2, height=3, emitted_supply=emitted)  # b3
    emitted += r3
    _ = emitted

    pre_json = state_to_json(pre)
    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_reachability_four_tips",
            "description": "Reject a block whose tips include ancestors (b1/b2) and descendant (b3).",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    {"id": "b3", "parents": ["b2"], "txs": []},
                    {"id": "bad", "parents": ["b1", "b2", "b3", "genesis"], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_REACHABILITY),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_merge_order_variation_same_result(vector_test_group) -> None:
    """Same DAG, different input order: merge should still succeed."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    post, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 (merge)
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_merge_order_variation_same_result",
            "description": "Import same fork/merge DAG but provide b3 before b2; merge still succeeds.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": []},
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


def test_chain_three_tips_allowed(vector_test_group) -> None:
    """A block with exactly 3 tips should be accepted."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    post, r4 = apply_empty_block_with_rewards(
        s3, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2
    )  # b4
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_three_tips_allowed",
            "description": "Import three tips at the same height (limit is 3); should succeed.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_tips_count_over_limit_after_merge(vector_test_group) -> None:
    """Reject a block that tries to reference 4 tips after a merge."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_tips_count_over_limit_after_merge",
            "description": "Reject a block with 4 tips (limit is 3) after multiple branches.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    {"id": "b3", "parents": ["b1"], "txs": []},
                    {"id": "b4", "parents": ["b1"], "txs": []},
                    {"id": "bad", "parents": ["b2", "b3", "b4", "b1"], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_COUNT),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_cross_block_receive_then_spend(vector_test_group) -> None:
    """Receive in block 1, spend in block 2: should succeed with correct balances."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx1 = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx2 = _mk_transfer(BOB, ALICE, nonce=0, amount=50_000, fee=0)

    emitted = 0
    s1, r1 = apply_block_with_rewards(pre, [tx1], height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_block_with_rewards(s1, [tx2], height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_cross_block_receive_then_spend",
            "description": "Receive in block 1, spend in block 2; balances and nonces update correctly.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(tx1)]},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(tx2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_cross_branch_receive_then_spend_after_merge(vector_test_group) -> None:
    """Receive on one branch, then spend after merge on a new block."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx1 = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)  # in b2
    tx2 = _mk_transfer(BOB, ALICE, nonce=0, amount=50_000, fee=0)   # in merge block

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [tx1], height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    post, r4 = apply_block_with_rewards(s3, [tx2], height=3, emitted_supply=emitted)  # b4 merge
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_cross_branch_receive_then_spend_after_merge",
            "description": "Receive on branch block, then spend after merge; balances should reflect both.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": [_tx_entry(tx1)]},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": [_tx_entry(tx2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_merge_three_parents_unordered(vector_test_group) -> None:
    """Merge three tips in an unsorted parent list; should still succeed."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(
        s3, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2
    )  # b4
    emitted += r4
    post, r5 = apply_empty_block_with_rewards(s4, height=3, emitted_supply=emitted)  # b5 (merge)
    emitted += r5
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_merge_three_parents_unordered",
            "description": "Merge with three parents in unsorted order; should still import successfully.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b5", "parents": ["b4", "b2", "b3"], "height": 3, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_randomized_order_same_dag(vector_test_group) -> None:
    """Provide a valid DAG in a shuffled order; should succeed."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4
    emitted += r4
    post, r5 = apply_empty_block_with_rewards(s4, height=4, emitted_supply=emitted)  # b5
    emitted += r5
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_randomized_order_same_dag",
            "description": "Blocks are provided in a shuffled but dependency-valid order; should still succeed.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": []},
                    {"id": "b5", "parents": ["b4"], "height": 4, "txs": []},
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


def test_chain_multi_block_burn_then_transfer(vector_test_group) -> None:
    """Burn in block 1 then transfer in block 2; verify cumulative effects."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    xfer = _mk_transfer(ALICE, BOB, nonce=1, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_block_with_rewards(pre, [burn], height=1, emitted_supply=emitted)
    emitted += r1
    post, r2 = apply_block_with_rewards(s1, [xfer], height=2, emitted_supply=emitted)
    emitted += r2
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_multi_block_burn_then_transfer",
            "description": "Burn in block 1 then transfer in block 2; total_burned and balances reflect both.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(burn)]},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(xfer)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_invalid_merge_height(vector_test_group) -> None:
    """Reject a merge block with an explicit height that doesn't match its tips."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    post, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side)
    emitted += r3
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_merge_height",
            "description": "Reject a merge block whose declared height is lower than expected for its tips.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    # Correct height should be 3 for tips b2/b3; force an invalid height.
                    {"id": "bad", "parents": ["b2", "b3"], "height": 2, "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_BLOCK_HEIGHT),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_invalid_tip_not_found_after_fork(vector_test_group) -> None:
    """Reject a block that references a missing parent after a fork."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    post, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (fork at height 2)
    emitted += r3
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_invalid_tip_not_found_after_fork",
            "description": "Reject a block that references a missing parent hash after a fork is present.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": []},
                    {"id": "b3", "parents": ["b1"], "txs": []},
                    {"id": "bad", "parents": ["b2", "ff" * 32], "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_NOT_FOUND),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_randomized_order_with_side_blocks_same_result(vector_test_group) -> None:
    """Provide a shuffled DAG with multiple side blocks and a merge; should succeed."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side #1)
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(
        s3,
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2,
    )  # b4 (side #2)
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(s4, height=3, emitted_supply=emitted)  # b5 (merge)
    emitted += r5
    post, r6 = apply_empty_block_with_rewards(s5, height=4, emitted_supply=emitted)  # b6
    emitted += r6
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_randomized_order_with_side_blocks_same_result",
            "description": "Provide a shuffled DAG with two side blocks and a merge; final state should match.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b5", "parents": ["b2", "b3", "b4"], "height": 3, "txs": []},
                    {"id": "b6", "parents": ["b5"], "height": 4, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_randomized_order_with_txs_same_result(vector_test_group) -> None:
    """Shuffle a forked DAG with txs on each branch; should succeed and merge states."""
    pre = _tx_state()
    pre.accounts[BOB].balance = 500_000
    pre_json = state_to_json(pre)

    tx_a = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx_b = _mk_transfer(BOB, ALICE, nonce=0, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [tx_a], height=2, emitted_supply=emitted)  # b2 (main)
    emitted += r2
    s3, r3 = apply_block_with_rewards(
        s2,
        [tx_b],
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 (side)
    emitted += r3
    post, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 (merge)
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_randomized_order_with_txs_same_result",
            "description": "Forked DAG with txs on each branch, shuffled order; merge should apply both txs.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": [_tx_entry(tx_b)]},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": [_tx_entry(tx_a)]},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_multi_block_burn_transfer_mix(vector_test_group) -> None:
    """Mix burn and transfer over multiple blocks; verify cumulative totals."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn1 = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    xfer = _mk_transfer(ALICE, BOB, nonce=1, amount=200_000, fee=100_000)
    burn2 = _mk_burn(ALICE, nonce=2, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_block_with_rewards(pre, [burn1], height=1, emitted_supply=emitted)
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [xfer], height=2, emitted_supply=emitted)
    emitted += r2
    post, r3 = apply_block_with_rewards(s2, [burn2], height=3, emitted_supply=emitted)
    emitted += r3
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_multi_block_burn_transfer_mix",
            "description": "Burn, transfer, then burn across three blocks; total_burned and balances reflect all ops.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(burn1)]},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(xfer)]},
                    {"id": "b3", "parents": ["b2"], "txs": [_tx_entry(burn2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_random_order_two_merges_variant_a(vector_test_group) -> None:
    """Same DAG as variant B but with a different block ordering; final state should match."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 merge
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(s4, height=4, emitted_supply=emitted)  # b5
    emitted += r5
    s6, r6 = apply_empty_block_with_rewards(
        s5, height=4, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2
    )  # b6 (side at height 4)
    emitted += r6
    post, r7 = apply_empty_block_with_rewards(s6, height=5, emitted_supply=emitted)  # b7 merge
    emitted += r7
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_random_order_two_merges_variant_a",
            "description": "Two merges with side blocks; ordering A should still result in the same final state.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": []},
                    {"id": "b6", "parents": ["b4"], "height": 4, "txs": []},
                    {"id": "b5", "parents": ["b4"], "height": 4, "txs": []},
                    {"id": "b7", "parents": ["b5", "b6"], "height": 5, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_random_order_two_merges_variant_b(vector_test_group) -> None:
    """Same DAG as variant A but with a different block ordering; final state should match."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 merge
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(s4, height=4, emitted_supply=emitted)  # b5
    emitted += r5
    s6, r6 = apply_empty_block_with_rewards(
        s5, height=4, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2
    )  # b6 (side at height 4)
    emitted += r6
    post, r7 = apply_empty_block_with_rewards(s6, height=5, emitted_supply=emitted)  # b7 merge
    emitted += r7
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_random_order_two_merges_variant_b",
            "description": "Two merges with side blocks; ordering B should still result in the same final state.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b4", "parents": ["b3", "b2"], "height": 3, "txs": []},
                    {"id": "b5", "parents": ["b4"], "height": 4, "txs": []},
                    {"id": "b6", "parents": ["b4"], "height": 4, "txs": []},
                    {"id": "b7", "parents": ["b6", "b5"], "height": 5, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_multi_block_burn_transfer_mix_extended(vector_test_group) -> None:
    """Mix burn/transfer/empty across multiple blocks; verify cumulative totals."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn1 = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    xfer1 = _mk_transfer(ALICE, BOB, nonce=1, amount=200_000, fee=100_000)
    burn2 = _mk_burn(ALICE, nonce=2, amount=50_000, fee=100_000)
    xfer2 = _mk_transfer(ALICE, BOB, nonce=3, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_block_with_rewards(pre, [burn1], height=1, emitted_supply=emitted)
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [xfer1], height=2, emitted_supply=emitted)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(s2, height=3, emitted_supply=emitted)
    emitted += r3
    s4, r4 = apply_block_with_rewards(s3, [burn2], height=4, emitted_supply=emitted)
    emitted += r4
    post, r5 = apply_block_with_rewards(s4, [xfer2], height=5, emitted_supply=emitted)
    emitted += r5
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_multi_block_burn_transfer_mix_extended",
            "description": "Burn/transfer/empty/burn/transfer across five blocks; totals accumulate with rewards.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": [_tx_entry(burn1)]},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(xfer1)]},
                    {"id": "b3", "parents": ["b2"], "txs": []},
                    {"id": "b4", "parents": ["b3"], "txs": [_tx_entry(burn2)]},
                    {"id": "b5", "parents": ["b4"], "txs": [_tx_entry(xfer2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_rewards_burn_across_blocks_with_merge(vector_test_group) -> None:
    """Burn across blocks on main + side branches, then merge; rewards and burns accumulate."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn_main = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    burn_side = _mk_burn(ALICE, nonce=1, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [burn_main], height=2, emitted_supply=emitted)  # b2 main
    emitted += r2
    s3, r3 = apply_block_with_rewards(
        s2,
        [burn_side],
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 side
    emitted += r3
    post, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 merge
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_rewards_burn_across_blocks_with_merge",
            "description": "Main and side branches both burn, then merge; rewards and total_burned accumulate.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(burn_main)]},
                    {"id": "b3", "parents": ["b1"], "txs": [_tx_entry(burn_side)]},
                    {"id": "b4", "parents": ["b2", "b3"], "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_random_order_complex_dag_stable(vector_test_group) -> None:
    """Import a deeper DAG with two merges in a shuffled order; should succeed."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(
        s3, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT // 2
    )  # b4
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(s4, height=3, emitted_supply=emitted)  # b5 merge
    emitted += r5
    s6, r6 = apply_empty_block_with_rewards(s5, height=4, emitted_supply=emitted)  # b6
    emitted += r6
    s7, r7 = apply_empty_block_with_rewards(s6, height=5, emitted_supply=emitted)  # b7 merge
    emitted += r7
    post, r8 = apply_empty_block_with_rewards(s7, height=6, emitted_supply=emitted)  # b8
    emitted += r8
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_random_order_complex_dag_stable",
            "description": "Deeper DAG with two merges in shuffled order should converge to the same state.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b5", "parents": ["b2", "b3"], "height": 3, "txs": []},
                    {"id": "b4", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b6", "parents": ["b5"], "height": 4, "txs": []},
                    {"id": "b7", "parents": ["b4", "b6"], "height": 5, "txs": []},
                    {"id": "b8", "parents": ["b7"], "height": 6, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_multi_branch_txs_merge(vector_test_group) -> None:
    """Apply transfers on two branches then merge; both tx effects should be visible."""
    pre = _tx_state()
    pre.accounts[BOB].balance = 500_000
    pre_json = state_to_json(pre)

    tx_a = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx_b = _mk_transfer(BOB, ALICE, nonce=0, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [tx_a], height=2, emitted_supply=emitted)  # b2 main
    emitted += r2
    s3, r3 = apply_block_with_rewards(
        s2,
        [tx_b],
        height=2,
        emitted_supply=emitted,
        side_reward_percent=SIDE_BLOCK_REWARD_PERCENT,
    )  # b3 side
    emitted += r3
    post, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 merge
    emitted += r4
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_multi_branch_txs_merge",
            "description": "Two branches include transfers; after merge both effects should be reflected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": [_tx_entry(tx_a)]},
                    {"id": "b3", "parents": ["b1"], "height": 2, "txs": [_tx_entry(tx_b)]},
                    {"id": "b4", "parents": ["b2", "b3"], "height": 3, "txs": []},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_tips_over_limit_with_reachability_noise(vector_test_group) -> None:
    """Construct a block with >3 tips and a non-reachable tip to confirm error handling."""
    pre = _base_state(include_miner=True)
    pre_json = state_to_json(pre)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_empty_block_with_rewards(s1, height=2, emitted_supply=emitted)  # b2
    emitted += r2
    post, r3 = apply_empty_block_with_rewards(s2, height=3, emitted_supply=emitted)  # b3
    emitted += r3
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_tips_over_limit_with_reachability_noise",
            "description": "Reject a block with 4 tips where one tip is also non-reachable.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "height": 1, "txs": []},
                    {"id": "b2", "parents": ["b1"], "height": 2, "txs": []},
                    {"id": "b3", "parents": ["b2"], "height": 3, "txs": []},
                    {"id": "bad", "parents": ["b1", "b2", "b3", "ff" * 32], "height": 4, "txs": []},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TIPS_COUNT),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_cross_block_dependency_after_merge(vector_test_group) -> None:
    """Receive funds on one branch, merge, then spend on the merged chain."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    receive = _mk_transfer(ALICE, BOB, nonce=0, amount=200_000, fee=100_000)
    spend = _mk_transfer(BOB, ALICE, nonce=0, amount=50_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [receive], height=2, emitted_supply=emitted)  # b2 (branch A)
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(
        s2, height=2, emitted_supply=emitted, side_reward_percent=SIDE_BLOCK_REWARD_PERCENT
    )  # b3 (branch B)
    emitted += r3
    s4, r4 = apply_empty_block_with_rewards(s3, height=3, emitted_supply=emitted)  # b4 merge
    emitted += r4
    post, r5 = apply_block_with_rewards(s4, [spend], height=4, emitted_supply=emitted)  # b5 spend
    emitted += r5
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_cross_block_dependency_after_merge",
            "description": "Receive on one branch, merge, then spend on the merged chain.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(receive)]},
                    {"id": "b3", "parents": ["b1"], "txs": []},
                    {"id": "b4", "parents": ["b2", "b3"], "txs": []},
                    {"id": "b5", "parents": ["b4"], "txs": [_tx_entry(spend)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_mixed_empty_tx_burn(vector_test_group) -> None:
    """Interleave empty blocks with burn and transfer blocks across a deeper chain."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn1 = _mk_burn(ALICE, nonce=0, amount=100_000, fee=100_000)
    xfer = _mk_transfer(ALICE, BOB, nonce=1, amount=50_000, fee=100_000)
    burn2 = _mk_burn(ALICE, nonce=2, amount=25_000, fee=100_000)

    emitted = 0
    s1, r1 = apply_empty_block_with_rewards(pre, height=1, emitted_supply=emitted)  # b1 empty
    emitted += r1
    s2, r2 = apply_block_with_rewards(s1, [burn1], height=2, emitted_supply=emitted)  # b2 burn
    emitted += r2
    s3, r3 = apply_empty_block_with_rewards(s2, height=3, emitted_supply=emitted)  # b3 empty
    emitted += r3
    s4, r4 = apply_block_with_rewards(s3, [xfer], height=4, emitted_supply=emitted)  # b4 transfer
    emitted += r4
    s5, r5 = apply_empty_block_with_rewards(s4, height=5, emitted_supply=emitted)  # b5 empty
    emitted += r5
    post, r6 = apply_block_with_rewards(s5, [burn2], height=6, emitted_supply=emitted)  # b6 burn
    emitted += r6
    _ = emitted

    post_json = state_to_json(post)
    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_mixed_empty_tx_burn",
            "description": "Empty blocks interleaved with burn and transfer blocks; totals accumulate with rewards.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "b1", "parents": ["genesis"], "txs": []},
                    {"id": "b2", "parents": ["b1"], "txs": [_tx_entry(burn1)]},
                    {"id": "b3", "parents": ["b2"], "txs": []},
                    {"id": "b4", "parents": ["b3"], "txs": [_tx_entry(xfer)]},
                    {"id": "b5", "parents": ["b4"], "txs": []},
                    {"id": "b6", "parents": ["b5"], "txs": [_tx_entry(burn2)]},
                ],
            },
            "expected": {
                "success": True,
                "error_code": int(ErrorCode.SUCCESS),
                "state_digest": compute_state_digest(post_json),
                "post_state": post_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_invalid_signature_rejected(vector_test_group) -> None:
    """Reject a tx block with an invalid signature."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx_bad_sig = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_invalid_signature_rejected",
            "description": "Import a block with a transfer that has an invalid signature; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_with_signature(tx_bad_sig, sign=False)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_SIGNATURE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_insufficient_fee_rejected(vector_test_group) -> None:
    """Reject a tx block with fee below minimum."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx_fee_zero = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=0)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_insufficient_fee_rejected",
            "description": "Import a block with a fee-too-low transfer; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_fee_zero)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INSUFFICIENT_FEE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_account_not_found_rejected(vector_test_group) -> None:
    """Reject a tx block where the sender is not in pre-state."""
    pre = _tx_state()
    pre.accounts.pop(ALICE, None)
    pre_json = state_to_json(pre)

    tx_missing = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_account_not_found_rejected",
            "description": "Import a block whose sender does not exist; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_missing)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.ACCOUNT_NOT_FOUND),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_nonce_too_low_rejected(vector_test_group) -> None:
    """Reject a tx block with a nonce that is too low."""
    pre = _tx_state()
    pre.accounts[ALICE].nonce = 1
    pre_json = state_to_json(pre)

    tx_nonce_low = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_nonce_too_low_rejected",
            "description": "Import a block with a transfer whose nonce is below expected; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_nonce_low)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.NONCE_TOO_LOW),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_nonce_too_high_rejected(vector_test_group) -> None:
    """Reject a tx block with a nonce that is too high."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx_nonce_high = _mk_transfer(ALICE, BOB, nonce=5, amount=100_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_nonce_too_high_rejected",
            "description": "Import a block with a transfer whose nonce is above expected; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_nonce_high)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.NONCE_TOO_HIGH),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_insufficient_balance_rejected(vector_test_group) -> None:
    """Reject a tx block when sender lacks funds for amount + fee."""
    pre = _tx_state()
    pre.accounts[ALICE].balance = 150_000
    pre_json = state_to_json(pre)

    tx_insufficient = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_insufficient_balance_rejected",
            "description": "Import a block where sender lacks funds for amount+fee; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_insufficient)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INSUFFICIENT_BALANCE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_receiver_overflow_rejected(vector_test_group) -> None:
    """Reject a tx block where receiver balance would overflow."""
    pre = _tx_state()
    pre.accounts[BOB].balance = 18_446_744_073_709_551_610
    pre_json = state_to_json(pre)

    tx_overflow = _mk_transfer(ALICE, BOB, nonce=0, amount=10, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_receiver_overflow_rejected",
            "description": "Import a block where receiver balance would overflow; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_overflow)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.OVERFLOW),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_chain_id_mismatch_rejected(vector_test_group) -> None:
    """Reject a tx block where the tx chain_id is wrong."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx_bad_chain = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx_bad_chain.chain_id = 1

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_chain_id_mismatch_rejected",
            "description": "Import a block with a tx for the wrong chain_id; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_bad_chain)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_TYPE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_transfer_zero_amount_rejected(vector_test_group) -> None:
    """Reject a tx block with a zero-amount transfer."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx_zero = _mk_transfer(ALICE, BOB, nonce=0, amount=0, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_transfer_zero_amount_rejected",
            "description": "Import a block with a zero-amount transfer; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx_zero)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_AMOUNT),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_burn_zero_amount_rejected(vector_test_group) -> None:
    """Reject a tx block with a zero-amount burn."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn_zero = _mk_burn(ALICE, nonce=0, amount=0, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_burn_zero_amount_rejected",
            "description": "Import a block with a zero-amount burn; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(burn_zero)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_AMOUNT),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_burn_exceeds_balance_rejected(vector_test_group) -> None:
    """Reject a tx block with a burn exceeding balance + fee."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    burn_too_much = _mk_burn(ALICE, nonce=0, amount=900_000, fee=200_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_burn_exceeds_balance_rejected",
            "description": "Import a block with a burn exceeding balance+fee; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(burn_too_much)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INSUFFICIENT_BALANCE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_txs_duplicate_nonce_rejected(vector_test_group) -> None:
    """Reject a tx block with duplicate nonce from the same sender."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx1 = _mk_transfer(ALICE, BOB, nonce=0, amount=100_000, fee=100_000)
    tx2 = _mk_transfer(ALICE, BOB, nonce=0, amount=50_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_txs_duplicate_nonce_rejected",
            "description": "Import a block with duplicate nonce from same sender; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [
                    {"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx1), _tx_entry(tx2)]},
                ],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.NONCE_DUPLICATE),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_multisig_invalid_threshold_rejected(vector_test_group) -> None:
    """Reject a multisig config with threshold=0."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_multisig(ALICE, nonce=0, threshold=0, participants=[], fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_multisig_invalid_threshold_rejected",
            "description": "Import a block with invalid multisig threshold; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.MULTISIG_THRESHOLD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_agent_account_invalid_controller_rejected(vector_test_group) -> None:
    """Reject agent_account register with zero controller."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    payload = {"variant": "register", "controller": bytes(32), "policy_hash": _hash(3)}
    tx = _mk_agent_account(ALICE, nonce=0, payload=payload, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_agent_account_invalid_controller_rejected",
            "description": "Import a block with agent_account register using zero controller; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_energy_freeze_fee_nonzero_rejected(vector_test_group) -> None:
    """Reject energy freeze with non-zero fee."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_energy_freeze(ALICE, nonce=0, amount=100_000_000, days=3, fee=1)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_energy_freeze_fee_nonzero_rejected",
            "description": "Import a block with energy freeze that has fee != 0; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_energy_delegate_self_rejected(vector_test_group) -> None:
    """Reject energy delegation to self."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    delegatees = [DelegationEntry(delegatee=ALICE, amount=100_000_000)]
    tx = _mk_energy_delegate(ALICE, nonce=0, delegatees=delegatees, days=3, fee=0)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_energy_delegate_self_rejected",
            "description": "Import a block with energy delegation to self; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.SELF_OPERATION),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_contract_deploy_empty_module_rejected(vector_test_group) -> None:
    """Reject deploy_contract with empty module."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_deploy_contract(ALICE, nonce=0, module=b"", fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_contract_deploy_empty_module_rejected",
            "description": "Import a block with deploy_contract empty module; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_FORMAT),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_contract_invoke_missing_rejected(vector_test_group) -> None:
    """Reject invoke_contract when contract does not exist."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_invoke_contract(ALICE, nonce=0, contract=_hash(7), entry_id=0, max_gas=1_000_000, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_contract_invoke_missing_rejected",
            "description": "Import a block with invoke_contract for missing contract; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.CONTRACT_NOT_FOUND),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_uno_empty_transfers_rejected(vector_test_group) -> None:
    """Reject UNO transfer with empty transfers list."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_uno_empty(ALICE, nonce=0, fee=0)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_uno_empty_transfers_rejected",
            "description": "Import a block with UNO transfers empty list; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_shield_empty_transfers_rejected(vector_test_group) -> None:
    """Reject shield transfer with empty transfers list."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_shield_empty(ALICE, nonce=0, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_shield_empty_transfers_rejected",
            "description": "Import a block with shield transfers empty list; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_unshield_empty_transfers_rejected(vector_test_group) -> None:
    """Reject unshield transfer with empty transfers list."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_unshield_empty(ALICE, nonce=0, fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_unshield_empty_transfers_rejected",
            "description": "Import a block with unshield transfers empty list; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_register_name_too_short_rejected(vector_test_group) -> None:
    """Reject name registration that is too short."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_register_name(ALICE, nonce=0, name="ab", fee=100_000)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_register_name_too_short_rejected",
            "description": "Import a block with too-short name registration; block should be rejected.",
            "pre_state": pre_json,
            "input": {
                "kind": "chain",
                "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry_allow_invalid(tx)]}],
            },
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )


def test_chain_block_with_transfer_energy_fee_rejected(vector_test_group) -> None:
    """Reject transfers using Energy fee type."""
    pre = _tx_state()
    pre_json = state_to_json(pre)

    tx = _mk_transfer_energy_fee(ALICE, BOB, nonce=0, amount=100_000, fee=1)

    _vector_test_group(vector_test_group)(
        "transactions/blockchain/chain_import.json",
        {
            "name": "chain_block_with_transfer_energy_fee_rejected",
            "description": "Import a block with transfers using Energy fee type; block should be rejected.",
            "pre_state": pre_json,
            "input": {"kind": "chain", "blocks": [{"id": "bad", "parents": ["genesis"], "txs": [_tx_entry(tx)]}]},
            "expected": {
                "success": False,
                "error_code": int(ErrorCode.INVALID_PAYLOAD),
                "state_digest": compute_state_digest(pre_json),
                "post_state": pre_json,
            },
            "runnable": False,
        },
    )
