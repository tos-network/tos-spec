"""Energy transaction specs (freeze/unfreeze/delegate/withdraw)."""

from __future__ import annotations

from copy import deepcopy

from ..config import (
    COIN_VALUE,
    MAX_DELEGATEES,
    MIN_FREEZE_TOS_AMOUNT,
    MIN_UNFREEZE_TOS_AMOUNT,
)
from ..errors import ErrorCode, SpecError
from ..types import (
    ChainState,
    DelegatedFreezeRecord,
    EnergyPayload,
    EnergyResource,
    FreezeRecord,
    PendingUnfreeze,
    Transaction,
)

U64_MAX = (1 << 64) - 1

MIN_FREEZE_DURATION_DAYS = 3
MAX_FREEZE_DURATION_DAYS = 365
MAX_FREEZE_RECORDS = 32
MAX_PENDING_UNFREEZES = 32
UNFREEZE_COOLDOWN_BLOCKS = 14 * 86400
BLOCKS_PER_DAY = 86400
BLOCKS_PER_DAY_DEVNET = 10


def _blocks_per_day(chain_id: int) -> int:
    if chain_id == 3:
        return BLOCKS_PER_DAY_DEVNET
    return BLOCKS_PER_DAY


def verify(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, EnergyPayload):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy payload must be EnergyPayload")

    variant = p.variant
    if variant == "freeze_tos":
        _verify_freeze_tos(state, tx, p)
    elif variant == "freeze_tos_delegate":
        _verify_freeze_delegate(state, tx, p)
    elif variant == "unfreeze_tos":
        _verify_unfreeze_tos(state, tx, p)
    elif variant == "withdraw_unfrozen":
        _verify_withdraw_unfrozen(state, tx, p)
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"unknown energy variant: {variant}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    p = tx.payload
    variant = p.variant
    if variant == "freeze_tos":
        return _apply_freeze_tos(state, tx, p)
    elif variant == "freeze_tos_delegate":
        return _apply_freeze_delegate(state, tx, p)
    elif variant == "unfreeze_tos":
        return _apply_unfreeze_tos(state, tx, p)
    elif variant == "withdraw_unfrozen":
        return _apply_withdraw_unfrozen(state, tx, p)
    raise SpecError(ErrorCode.INVALID_PAYLOAD, f"unknown energy variant: {variant}")


# --- freeze_tos ---

def _verify_freeze_tos(state: ChainState, tx: Transaction, p: EnergyPayload) -> None:
    if tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy transactions must have zero fee")

    amount = p.amount or 0
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "freeze amount must be > 0")
    if amount % COIN_VALUE != 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "freeze amount must be whole TOS")
    if amount < MIN_FREEZE_TOS_AMOUNT:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "freeze amount below minimum")

    if p.duration is None:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "duration required")
    days = p.duration.days
    if days < MIN_FREEZE_DURATION_DAYS or days > MAX_FREEZE_DURATION_DAYS:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"duration must be {MIN_FREEZE_DURATION_DAYS}-{MAX_FREEZE_DURATION_DAYS} days")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < amount:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for freeze")


def _apply_freeze_tos(state: ChainState, tx: Transaction, p: EnergyPayload) -> ChainState:
    ns = deepcopy(state)
    amount = p.amount or 0
    days = p.duration.days
    bpd = _blocks_per_day(ns.network_chain_id)
    height = ns.global_state.block_height

    sender = ns.accounts[tx.source]
    sender.balance -= amount

    if sender.frozen + amount > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "frozen balance overflow")
    sender.frozen += amount

    whole_tos = amount // COIN_VALUE
    energy_gained = whole_tos * (days * 2)

    if sender.energy + energy_gained > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "energy overflow")
    sender.energy += energy_gained

    er = ns.energy_resources.get(tx.source)
    if er is None:
        er = EnergyResource()
        ns.energy_resources[tx.source] = er

    total_records = len(er.freeze_records) + len(er.delegated_records)
    if total_records >= MAX_FREEZE_RECORDS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "maximum freeze records reached")

    er.freeze_records.append(FreezeRecord(
        amount=amount,
        energy_gained=energy_gained,
        freeze_height=height,
        unlock_height=height + days * bpd,
    ))

    if er.frozen_tos + amount > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "energy resource frozen_tos overflow")
    er.frozen_tos += amount

    if er.energy + energy_gained > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "energy resource energy overflow")
    er.energy += energy_gained

    if ns.global_state.total_energy + energy_gained > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "total energy overflow")
    ns.global_state.total_energy += energy_gained

    return ns


# --- freeze_tos_delegate ---

def _verify_freeze_delegate(state: ChainState, tx: Transaction, p: EnergyPayload) -> None:
    if tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy transactions must have zero fee")

    delegatees = p.delegatees or []
    if not delegatees:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "delegatees list empty")
    if len(delegatees) > MAX_DELEGATEES:
        raise SpecError(ErrorCode.INVALID_FORMAT, "too many delegatees")

    if p.duration is None:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "duration required")
    days = p.duration.days
    if days < MIN_FREEZE_DURATION_DAYS or days > MAX_FREEZE_DURATION_DAYS:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"duration must be {MIN_FREEZE_DURATION_DAYS}-{MAX_FREEZE_DURATION_DAYS} days")

    seen: set[bytes] = set()
    total = 0
    for entry in delegatees:
        if entry.delegatee == tx.source:
            raise SpecError(ErrorCode.SELF_OPERATION, "cannot delegate to self")
        if entry.delegatee in seen:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "duplicate delegatee")
        seen.add(entry.delegatee)

        if entry.amount <= 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "delegation amount must be > 0")
        if entry.amount % COIN_VALUE != 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "delegation amount must be whole TOS")
        if entry.amount < MIN_FREEZE_TOS_AMOUNT:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "delegation amount below minimum")

        if entry.delegatee not in state.accounts:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "delegatee not found")

        total += entry.amount

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.balance < total:
        raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for delegation")


def _apply_freeze_delegate(state: ChainState, tx: Transaction, p: EnergyPayload) -> ChainState:
    ns = deepcopy(state)
    delegatees = p.delegatees or []
    days = p.duration.days
    bpd = _blocks_per_day(ns.network_chain_id)
    height = ns.global_state.block_height

    sender = ns.accounts[tx.source]
    er = ns.energy_resources.get(tx.source)
    if er is None:
        er = EnergyResource()
        ns.energy_resources[tx.source] = er

    total_amount = 0
    total_energy = 0

    for entry in delegatees:
        amount = entry.amount
        whole_tos = amount // COIN_VALUE
        energy_gained = whole_tos * (days * 2)

        sender.balance -= amount
        sender.frozen += amount

        if total_amount + amount > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "delegation total amount overflow")
        total_amount += amount

        if total_energy + energy_gained > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "delegation total energy overflow")
        total_energy += energy_gained

        er.delegated_records.append(DelegatedFreezeRecord(
            delegatee=entry.delegatee,
            amount=amount,
            energy_gained=energy_gained,
            freeze_height=height,
            unlock_height=height + days * bpd,
        ))

        delegatee_acct = ns.accounts.get(entry.delegatee)
        if delegatee_acct is not None:
            if delegatee_acct.energy + energy_gained > U64_MAX:
                raise SpecError(ErrorCode.OVERFLOW, "delegatee energy overflow")
            delegatee_acct.energy += energy_gained

    if er.frozen_tos + total_amount > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "energy resource frozen_tos overflow")
    er.frozen_tos += total_amount

    if ns.global_state.total_energy + total_energy > U64_MAX:
        raise SpecError(ErrorCode.OVERFLOW, "total energy overflow")
    ns.global_state.total_energy += total_energy

    return ns


# --- unfreeze_tos ---

def _verify_unfreeze_tos(state: ChainState, tx: Transaction, p: EnergyPayload) -> None:
    if tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy transactions must have zero fee")

    amount = p.amount or 0
    if amount <= 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "unfreeze amount must be > 0")
    if amount % COIN_VALUE != 0:
        raise SpecError(ErrorCode.INVALID_AMOUNT, "unfreeze amount must be whole TOS")

    from_delegation = p.from_delegation or False
    if not from_delegation and p.delegatee_address is not None:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid delegatee_address usage")

    sender = state.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")
    if sender.frozen < amount:
        raise SpecError(ErrorCode.INSUFFICIENT_FROZEN, "insufficient frozen balance")

    er = state.energy_resources.get(tx.source)
    if er is not None and len(er.pending_unfreezes) >= MAX_PENDING_UNFREEZES:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "maximum pending unfreezes reached")


def _apply_unfreeze_tos(state: ChainState, tx: Transaction, p: EnergyPayload) -> ChainState:
    ns = deepcopy(state)
    amount = p.amount or 0
    from_delegation = p.from_delegation or False
    bpd = _blocks_per_day(ns.network_chain_id)
    height = ns.global_state.block_height
    cooldown = 14 * bpd

    sender = ns.accounts[tx.source]
    sender.frozen -= amount

    er = ns.energy_resources.get(tx.source)
    if er is None:
        er = EnergyResource()
        ns.energy_resources[tx.source] = er

    er.frozen_tos -= amount
    er.pending_unfreezes.append(PendingUnfreeze(
        amount=amount,
        from_delegation=from_delegation,
        expire_height=height + cooldown,
    ))

    return ns


# --- withdraw_unfrozen ---

def _verify_withdraw_unfrozen(state: ChainState, tx: Transaction, p: EnergyPayload) -> None:
    if tx.fee != 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "energy transactions must have zero fee")

    er = state.energy_resources.get(tx.source)
    if er is None or not er.pending_unfreezes:
        sender = state.accounts.get(tx.source)
        if sender is None or sender.frozen <= 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "no pending unfreezes")


def _apply_withdraw_unfrozen(state: ChainState, tx: Transaction, p: EnergyPayload) -> ChainState:
    ns = deepcopy(state)
    height = ns.global_state.block_height

    sender = ns.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")

    er = ns.energy_resources.get(tx.source)
    if er is not None:
        withdrawn = 0
        remaining = []
        for pending in er.pending_unfreezes:
            if pending.expire_height <= height:
                withdrawn += pending.amount
            else:
                remaining.append(pending)
        er.pending_unfreezes = remaining
        if sender.balance + withdrawn > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "balance overflow on withdraw")
        sender.balance += withdrawn
    else:
        withdrawn = sender.frozen
        sender.frozen = 0
        if sender.balance + withdrawn > U64_MAX:
            raise SpecError(ErrorCode.OVERFLOW, "balance overflow on withdraw")
        sender.balance += withdrawn

    return ns
