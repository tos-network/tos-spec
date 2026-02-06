"""Model spec fixtures (energy, fee, account, block_limits)."""

from __future__ import annotations

from tos_spec.account_model import (
    COIN_VALUE,
    MAXIMUM_SUPPLY,
    MAX_FREEZE_RECORDS,
    MAX_MULTISIG_PARTICIPANTS,
    MAX_PENDING_UNFREEZES,
    apply_balance_change,
    apply_nonce_increment,
    energy_from_freeze,
)
from tos_spec.config import (
    COIN_DECIMALS,
    EXTRA_DATA_LIMIT_SIZE,
    EXTRA_DATA_LIMIT_SUM_SIZE,
    MAX_DELEGATEES,
    MAX_DEPOSIT_PER_INVOKE_CALL,
    MAX_NONCE_GAP,
    MAX_TRANSFER_COUNT,
    MIN_FREEZE_TOS_AMOUNT,
    MIN_SHIELD_TOS_AMOUNT,
    MIN_UNFREEZE_TOS_AMOUNT,
)
from tos_spec.consensus.block_structure import (
    MAX_BLOCK_SIZE,
    MAX_TXS_PER_BLOCK,
    MAX_TRANSACTION_SIZE,
    TIPS_LIMIT,
)


# --- energy_system specs ---


def test_energy_from_1tos_7days(vector_test_group) -> None:
    vector_test_group(
        "models/energy_system.json",
        {
            "name": "energy_from_1tos_7days",
            "runnable": False,
            "input": {"amount": COIN_VALUE, "days": 7},
            "expected": {"energy": energy_from_freeze(COIN_VALUE, 7)},
        },
    )


def test_energy_from_10tos_30days(vector_test_group) -> None:
    vector_test_group(
        "models/energy_system.json",
        {
            "name": "energy_from_10tos_30days",
            "runnable": False,
            "input": {"amount": 10 * COIN_VALUE, "days": 30},
            "expected": {"energy": energy_from_freeze(10 * COIN_VALUE, 30)},
        },
    )


def test_energy_from_zero_amount(vector_test_group) -> None:
    vector_test_group(
        "models/energy_system.json",
        {
            "name": "energy_from_zero_amount",
            "runnable": False,
            "input": {"amount": 0, "days": 7},
            "expected": {"energy": energy_from_freeze(0, 7)},
        },
    )


def test_energy_from_sub_coin(vector_test_group) -> None:
    vector_test_group(
        "models/energy_system.json",
        {
            "name": "energy_from_sub_coin",
            "description": "Amount less than COIN_VALUE yields zero energy",
            "runnable": False,
            "input": {"amount": COIN_VALUE - 1, "days": 7},
            "expected": {"energy": energy_from_freeze(COIN_VALUE - 1, 7)},
        },
    )


# --- fee_model specs ---


def test_fee_model_constants(vector_test_group) -> None:
    vector_test_group(
        "models/fee_model.json",
        {
            "name": "fee_model_constants",
            "runnable": False,
            "input": {"kind": "spec"},
            "expected": {
                "max_transfer_count": MAX_TRANSFER_COUNT,
                "max_nonce_gap": MAX_NONCE_GAP,
                "extra_data_limit_size": EXTRA_DATA_LIMIT_SIZE,
                "extra_data_limit_sum_size": EXTRA_DATA_LIMIT_SUM_SIZE,
            },
        },
    )


# --- account_model specs ---


def test_account_model_constants(vector_test_group) -> None:
    vector_test_group(
        "models/account_model.json",
        {
            "name": "account_model_constants",
            "runnable": False,
            "input": {"kind": "spec"},
            "expected": {
                "coin_decimals": COIN_DECIMALS,
                "coin_value": COIN_VALUE,
                "maximum_supply": MAXIMUM_SUPPLY,
                "max_multisig_participants": MAX_MULTISIG_PARTICIPANTS,
                "max_freeze_records": MAX_FREEZE_RECORDS,
                "max_pending_unfreezes": MAX_PENDING_UNFREEZES,
            },
        },
    )


def test_balance_change_positive(vector_test_group) -> None:
    result = apply_balance_change(1_000, 500)
    vector_test_group(
        "models/account_model.json",
        {
            "name": "balance_change_positive",
            "runnable": False,
            "input": {"balance": 1_000, "delta": 500},
            "expected": {"new_balance": result},
        },
    )


def test_balance_change_negative_underflow(vector_test_group) -> None:
    try:
        apply_balance_change(100, -200)
        error = None
    except Exception as exc:
        error = str(exc)
    vector_test_group(
        "models/account_model.json",
        {
            "name": "balance_change_negative_underflow",
            "runnable": False,
            "input": {"balance": 100, "delta": -200},
            "expected": {"error": error},
        },
    )


def test_nonce_increment(vector_test_group) -> None:
    result = apply_nonce_increment(5)
    vector_test_group(
        "models/account_model.json",
        {
            "name": "nonce_increment",
            "runnable": False,
            "input": {"nonce": 5, "increment": 1},
            "expected": {"new_nonce": result},
        },
    )


# --- block_limits specs ---


def test_block_limits_constants(vector_test_group) -> None:
    vector_test_group(
        "models/block_limits.json",
        {
            "name": "block_limits_constants",
            "runnable": False,
            "input": {"kind": "spec"},
            "expected": {
                "tips_limit": TIPS_LIMIT,
                "max_block_size": MAX_BLOCK_SIZE,
                "max_txs_per_block": MAX_TXS_PER_BLOCK,
                "max_transaction_size": MAX_TRANSACTION_SIZE,
                "min_freeze_tos_amount": MIN_FREEZE_TOS_AMOUNT,
                "min_unfreeze_tos_amount": MIN_UNFREEZE_TOS_AMOUNT,
                "min_shield_tos_amount": MIN_SHIELD_TOS_AMOUNT,
                "max_delegatees": MAX_DELEGATEES,
                "max_deposit_per_invoke_call": MAX_DEPOSIT_PER_INVOKE_CALL,
            },
        },
    )
