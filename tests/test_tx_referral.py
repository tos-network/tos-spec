"""Referral tx fixtures (bind_referrer)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, MAX_BPS
from tos_spec.test_accounts import ALICE, BOB, CAROL
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=1_000_000, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    return state


def _mk_bind_referrer(sender: bytes, nonce: int, referrer: bytes, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.BIND_REFERRER,
        payload={"referrer": referrer},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_bind_referrer_success(state_test_group) -> None:
    state = _base_state()
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=BOB, fee=100_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_success",
        state,
        tx,
    )


def test_bind_referrer_self(state_test_group) -> None:
    state = _base_state()
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=ALICE, fee=100_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_self",
        state,
        tx,
    )


def test_bind_referrer_not_found(state_test_group) -> None:
    state = _base_state()
    unknown = bytes([99]) * 32
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=unknown, fee=100_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_not_found",
        state,
        tx,
    )


# --- batch_referral_reward specs ---


def _mk_batch_referral_reward(
    sender: bytes, nonce: int, total_amount: int, levels: int,
    ratios: list[int], from_user: bytes, fee: int,
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.BATCH_REFERRAL_REWARD,
        payload={
            # Rust payload requires an asset; native TOS is the zero-hash.
            "asset": bytes(32),
            "total_amount": total_amount,
            "levels": levels,
            "ratios": ratios,
            "from_user": from_user,
        },
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_batch_referral_reward_success(state_test_group) -> None:
    """Valid batch reward with levels and ratios."""
    state = _base_state()
    # Set up referral chain: BOB -> CAROL (BOB's referrer is CAROL)
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.referrals[BOB] = CAROL
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=1,
        ratios=[5000], from_user=BOB, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_success",
        state,
        tx,
    )


def test_batch_referral_reward_zero_amount(state_test_group) -> None:
    """Total amount = 0."""
    state = _base_state()
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=0, levels=1,
        ratios=[5000], from_user=BOB, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_zero_amount",
        state,
        tx,
    )


def test_batch_referral_reward_empty_levels(state_test_group) -> None:
    """Empty ratios list with levels=0."""
    state = _base_state()
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=0,
        ratios=[], from_user=BOB, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_empty_levels",
        state,
        tx,
    )


def test_batch_referral_reward_ratio_exceeds_max(state_test_group) -> None:
    """Sum of ratios > 10000 BPS."""
    state = _base_state()
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=2,
        ratios=[6000, 5000], from_user=BOB, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_ratio_exceeds_max",
        state,
        tx,
    )


def test_batch_referral_reward_levels_mismatch(state_test_group) -> None:
    """ratios.len != levels."""
    state = _base_state()
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=3,
        ratios=[5000, 3000], from_user=BOB, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_levels_mismatch",
        state,
        tx,
    )


# --- boundary value tests ---


def test_batch_referral_reward_max_ratio(state_test_group) -> None:
    """Batch referral reward with ratio exactly at MAX_BPS (10000) must succeed."""
    state = _base_state()
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.referrals[BOB] = CAROL
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=1,
        ratios=[MAX_BPS], from_user=BOB, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_max_ratio",
        state,
        tx,
    )


# ===================================================================
# Referral boundary tests
# ===================================================================


def test_bind_referrer_already_bound(state_test_group) -> None:
    """Bind referrer when sender already has a referrer.

    Rust: state check for existing referral.
    """
    state = _base_state()
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.referrals[ALICE] = BOB  # Already bound
    tx = _mk_bind_referrer(ALICE, nonce=5, referrer=CAROL, fee=100_000)
    state_test_group(
        "transactions/referral/bind_referrer.json",
        "bind_referrer_already_bound",
        state,
        tx,
    )


def test_batch_referral_reward_sender_not_from_user(state_test_group) -> None:
    """BatchReferralReward sender must be from_user.

    Rust: "BatchReferralReward sender must be the from_user".
    """
    state = _base_state()
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.referrals[BOB] = CAROL
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=1,
        ratios=[5000], from_user=BOB, fee=100_000,  # from_user != sender
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_sender_not_from_user",
        state,
        tx,
    )


def test_batch_referral_reward_sender_is_from_user(state_test_group) -> None:
    """BatchReferralReward where sender == from_user (success case)."""
    state = _base_state()
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.referrals[ALICE] = CAROL
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=1,
        ratios=[5000], from_user=ALICE, fee=100_000,  # from_user == sender
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_sender_is_from_user",
        state,
        tx,
    )


def test_batch_referral_reward_insufficient_balance(state_test_group) -> None:
    """Batch referral reward exceeds sender balance."""
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=50_000, nonce=5)
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    state.referrals[ALICE] = CAROL
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=1,
        ratios=[5000], from_user=ALICE, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_insufficient_balance",
        state,
        tx,
    )


def test_batch_referral_reward_zero_levels(state_test_group) -> None:
    """Batch referral reward with levels=0 and empty ratios.

    Should fail because total_amount > 0 but levels = 0 != len(ratios=0).
    Actually len([]) == 0 so ratios match, but total_amount > 0 is valid.
    This is a degenerate case where nobody gets rewards.
    """
    state = _base_state()
    tx = _mk_batch_referral_reward(
        ALICE, nonce=5, total_amount=100_000, levels=0,
        ratios=[], from_user=ALICE, fee=100_000,
    )
    state_test_group(
        "transactions/referral/batch_referral_reward.json",
        "batch_referral_reward_zero_levels",
        state,
        tx,
    )
