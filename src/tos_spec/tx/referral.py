"""Referral transaction specs (BindReferrer, BatchReferralReward)."""

from __future__ import annotations

from copy import deepcopy

from ..errors import ErrorCode, SpecError
from ..types import ChainState, Transaction, TransactionType


def verify(state: ChainState, tx: Transaction) -> None:
    if tx.tx_type == TransactionType.BIND_REFERRER:
        _verify_bind_referrer(state, tx)
    elif tx.tx_type == TransactionType.BATCH_REFERRAL_REWARD:
        _verify_batch_referral_reward(state, tx)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported referral tx type: {tx.tx_type}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    if tx.tx_type == TransactionType.BIND_REFERRER:
        return _apply_bind_referrer(state, tx)
    elif tx.tx_type == TransactionType.BATCH_REFERRAL_REWARD:
        return _apply_batch_referral_reward(state, tx)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported referral tx type: {tx.tx_type}")


def _verify_bind_referrer(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "bind_referrer payload must be dict")

    referrer = p.get("referrer")
    if referrer is None:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "referrer required")
    if isinstance(referrer, (list, tuple)):
        referrer = bytes(referrer)

    if referrer == tx.source:
        raise SpecError(ErrorCode.SELF_OPERATION, "cannot bind self as referrer")

    if tx.source in state.referrals:
        raise SpecError(ErrorCode.DELEGATION_EXISTS, "referrer already bound")


def _apply_bind_referrer(state: ChainState, tx: Transaction) -> ChainState:
    next_state = deepcopy(state)
    p = tx.payload
    referrer = p.get("referrer")
    if isinstance(referrer, (list, tuple)):
        referrer = bytes(referrer)
    next_state.referrals[tx.source] = referrer
    return next_state


def _verify_batch_referral_reward(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "batch_referral_reward payload must be dict")

    total_amount = p.get("total_amount", 0)
    if total_amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "total_amount must be > 0")

    ratios = p.get("ratios", [])
    levels = p.get("levels", 0)
    if len(ratios) != levels:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "ratios length must match levels")

    ratio_sum = sum(ratios)
    if ratio_sum > 10_000:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "ratios sum exceeds 10000 bps")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < total_amount:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for reward")


def _apply_batch_referral_reward(state: ChainState, tx: Transaction) -> ChainState:
    next_state = deepcopy(state)
    p = tx.payload
    total_amount = p.get("total_amount", 0)
    ratios = p.get("ratios", [])
    from_user = p.get("from_user")
    if isinstance(from_user, (list, tuple)):
        from_user = bytes(from_user)

    sender = next_state.accounts[tx.source]
    sender.balance -= total_amount

    current = from_user
    for ratio in ratios:
        if current is None or current not in next_state.referrals:
            break
        referrer_key = next_state.referrals[current]
        reward = (total_amount * ratio) // 10_000
        if reward <= 0:
            current = referrer_key
            continue
        referrer_acct = next_state.accounts.get(referrer_key)
        if referrer_acct is not None:
            referrer_acct.balance += reward
        current = referrer_key

    return next_state
