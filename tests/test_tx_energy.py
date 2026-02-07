"""Energy tx fixtures."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MAX_DELEGATEES, MIN_FREEZE_TOS_AMOUNT, MIN_UNFREEZE_TOS_AMOUNT
from tos_spec.test_accounts import ALICE, BOB, CAROL
from tos_spec.types import (
    AccountState,
    ChainState,
    DelegationEntry,
    EnergyPayload,
    EnergyResource,
    FeeType,
    FreezeRecord,
    FreezeDuration,
    PendingUnfreeze,
    Transaction,
    TransactionType,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _base_state() -> ChainState:
    sender = ALICE
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[sender] = AccountState(
        address=sender, balance=100 * COIN_VALUE, nonce=5, frozen=10 * COIN_VALUE
    )
    state.energy_resources[sender] = EnergyResource(
        frozen_tos=10 * COIN_VALUE,
        energy=0,
        freeze_records=[
            FreezeRecord(
                amount=10 * COIN_VALUE,
                energy_gained=0,
                freeze_height=0,
                unlock_height=99999,
            )
        ],
    )
    return state


def _mk_freeze_tos(
    sender: bytes, nonce: int, amount: int, days: int, fee: int
) -> Transaction:
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


def _mk_freeze_delegate(
    sender: bytes,
    nonce: int,
    delegatees: list[DelegationEntry],
    days: int,
    fee: int,
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


def _mk_unfreeze_tos(
    sender: bytes,
    nonce: int,
    amount: int,
    from_delegation: bool,
    fee: int,
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="unfreeze_tos",
            amount=amount,
            from_delegation=from_delegation,
        ),
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_withdraw_unfrozen(sender: bytes, nonce: int, fee: int) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(variant="withdraw_unfrozen"),
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- freeze_tos specs ---


def test_freeze_tos_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_freeze_tos(sender, nonce=5, amount=MIN_FREEZE_TOS_AMOUNT, days=7, fee=0)
    state_test_group("transactions/energy/freeze_tos.json", "freeze_tos_success", state, tx)


def test_freeze_tos_insufficient_balance(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_freeze_tos(sender, nonce=5, amount=200 * COIN_VALUE, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json",
        "freeze_tos_insufficient_balance",
        state,
        tx,
    )


def test_freeze_tos_zero_amount(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_freeze_tos(sender, nonce=5, amount=0, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_tos_zero_amount", state, tx
    )


# --- freeze_delegate specs ---


def test_freeze_delegate_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    delegatee = BOB
    state.accounts[delegatee] = AccountState(address=delegatee, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=delegatee, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(sender, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_success",
        state,
        tx,
    )


def test_freeze_delegate_self(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    entries = [DelegationEntry(delegatee=sender, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(sender, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_self",
        state,
        tx,
    )


def test_freeze_delegate_empty(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_freeze_delegate(sender, nonce=5, delegatees=[], days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_empty",
        state,
        tx,
    )


# --- unfreeze_tos specs ---


def test_unfreeze_tos_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    # Override unlock_height to 0 so the record is unlockable at topoheight=0
    state.energy_resources[sender].freeze_records[0].unlock_height = 0
    tx = _mk_unfreeze_tos(
        sender, nonce=5, amount=MIN_UNFREEZE_TOS_AMOUNT, from_delegation=False, fee=0
    )
    state_test_group(
        "transactions/energy/unfreeze_tos.json", "unfreeze_tos_success", state, tx
    )


def test_unfreeze_tos_insufficient_frozen(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    # Override unlock_height to 0 so the record is unlockable at topoheight=0
    state.energy_resources[sender].freeze_records[0].unlock_height = 0
    tx = _mk_unfreeze_tos(
        sender, nonce=5, amount=50 * COIN_VALUE, from_delegation=False, fee=0
    )
    state_test_group(
        "transactions/energy/unfreeze_tos.json",
        "unfreeze_tos_insufficient_frozen",
        state,
        tx,
    )


def test_unfreeze_tos_zero_amount(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_unfreeze_tos(sender, nonce=5, amount=0, from_delegation=False, fee=0)
    state_test_group(
        "transactions/energy/unfreeze_tos.json",
        "unfreeze_tos_zero_amount",
        state,
        tx,
    )


# --- withdraw_unfrozen specs ---


def test_withdraw_unfrozen_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    # Add pending unfreezes that are already expired (expire_height=0)
    state.energy_resources[sender].pending_unfreezes = [
        PendingUnfreeze(amount=5 * COIN_VALUE, expire_height=0),
    ]
    tx = _mk_withdraw_unfrozen(sender, nonce=5, fee=0)
    state_test_group(
        "transactions/energy/withdraw_unfrozen.json",
        "withdraw_unfrozen_success",
        state,
        tx,
    )


def test_withdraw_unfrozen_nothing_pending(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    state.accounts[sender].frozen = 0
    # Clear energy_resource to match frozen=0 (no frozen records, no pending unfreezes)
    state.energy_resources[sender] = EnergyResource(
        frozen_tos=0, energy=0, freeze_records=[], pending_unfreezes=[],
    )
    tx = _mk_withdraw_unfrozen(sender, nonce=5, fee=0)
    state_test_group(
        "transactions/energy/withdraw_unfrozen.json",
        "withdraw_unfrozen_nothing_pending",
        state,
        tx,
    )


# --- freeze_tos boundary tests ---


def test_freeze_duration_too_short(state_test_group) -> None:
    """Duration below minimum (3 days)."""
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=COIN_VALUE, days=2, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_duration_too_short", state, tx
    )


def test_freeze_duration_too_long(state_test_group) -> None:
    """Duration above maximum (365 days)."""
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=COIN_VALUE, days=366, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_duration_too_long", state, tx
    )


# --- freeze_delegate boundary tests ---


def test_freeze_delegate_max_delegatees_exceeded(state_test_group) -> None:
    """501 delegatees (max=500)."""
    state = _base_state()
    sender = ALICE
    state.accounts[sender] = AccountState(
        address=sender, balance=1000 * COIN_VALUE, nonce=5, frozen=10 * COIN_VALUE
    )
    # Create distinct delegatee accounts
    delegatees = []
    for i in range(MAX_DELEGATEES + 1):
        addr = bytes([i % 256, (i >> 8) % 256]) + bytes(30)
        state.accounts[addr] = AccountState(address=addr, balance=0, nonce=0)
        delegatees.append(DelegationEntry(delegatee=addr, amount=COIN_VALUE))
    tx = _mk_freeze_delegate(sender, nonce=5, delegatees=delegatees, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_max_delegatees_exceeded",
        state,
        tx,
    )


# ===================================================================
# Additional boundary tests
# ===================================================================


def test_freeze_below_minimum(state_test_group) -> None:
    """Freeze with amount < MIN_FREEZE_TOS_AMOUNT (half a TOS).

    Amount 50_000_000 is below minimum 1 TOS and also not a whole TOS.
    """
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=MIN_FREEZE_TOS_AMOUNT // 2, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_below_minimum", state, tx
    )


def test_freeze_non_whole_tos(state_test_group) -> None:
    """Freeze with amount that is not a multiple of COIN_VALUE.

    Amount 150_000_000 (1.5 TOS) is above minimum but not a whole TOS.
    """
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=COIN_VALUE + COIN_VALUE // 2, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_non_whole_tos", state, tx
    )


def test_freeze_max_records_exceeded(state_test_group) -> None:
    """33 freeze records (max=32).

    Pre-state has 32 existing freeze records; adding one more should fail.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE
    state.accounts[sender] = AccountState(
        address=sender, balance=100 * COIN_VALUE, nonce=5, frozen=32 * COIN_VALUE
    )
    # Pre-populate 32 freeze records (the maximum)
    records = [
        FreezeRecord(
            amount=COIN_VALUE,
            energy_gained=14,
            freeze_height=0,
            unlock_height=99999,
        )
        for _ in range(32)
    ]
    state.energy_resources[sender] = EnergyResource(
        frozen_tos=32 * COIN_VALUE,
        energy=32 * 14,
        freeze_records=records,
    )
    tx = _mk_freeze_tos(sender, nonce=5, amount=COIN_VALUE, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_max_records_exceeded", state, tx
    )


def test_unfreeze_amount_zero(state_test_group) -> None:
    """Unfreeze with amount=0 should be rejected.

    This is an alias test; the existing test_unfreeze_tos_zero_amount covers
    this case but uses the state_test_group fixture under the standard path.
    """
    state = _base_state()
    tx = _mk_unfreeze_tos(ALICE, nonce=5, amount=0, from_delegation=False, fee=0)
    state_test_group(
        "transactions/energy/unfreeze_tos.json",
        "unfreeze_amount_zero",
        state,
        tx,
    )


def test_delegate_self(state_test_group) -> None:
    """Delegate to self (sender == delegatee) should be rejected.

    This is tested via freeze_delegate_self; here we confirm the error
    under the standard freeze_delegate path.
    """
    state = _base_state()
    entries = [DelegationEntry(delegatee=ALICE, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "delegate_self",
        state,
        tx,
    )
