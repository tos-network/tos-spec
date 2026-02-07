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
    """33 freeze records — daemon does not enforce max records limit.

    Pre-state has 32 existing freeze records; adding one more succeeds
    because the daemon does not check freeze record count at verify time.
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


def test_delegate_max_delegatees_exceeded(state_test_group) -> None:
    """501 delegatees (max=500) should be rejected.

    Rust: "Too many delegatees (max 500)"
    """
    state = _base_state()
    # Create 501 unique delegatees
    delegatees = []
    for i in range(MAX_DELEGATEES + 1):
        addr = bytes([i % 256]) + bytes([(i >> 8) % 256]) + bytes(30)
        state.accounts[addr] = AccountState(address=addr, balance=0, nonce=0)
        delegatees.append(DelegationEntry(delegatee=addr, amount=COIN_VALUE))
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=delegatees, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "delegate_max_delegatees_exceeded",
        state,
        tx,
    )


# ===================================================================
# Overflow tests (u64 boundary)
# ===================================================================

U64_MAX = (1 << 64) - 1


def test_freeze_frozen_overflow(state_test_group) -> None:
    """Freezing TOS when sender.frozen is near U64_MAX should overflow.

    Pre-state: sender.frozen = U64_MAX - COIN_VALUE + 1.
    Freeze amount = COIN_VALUE (1 TOS).
    frozen + amount = U64_MAX + 1 > U64_MAX => OVERFLOW.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE
    frozen_val = U64_MAX - COIN_VALUE + 1
    state.accounts[sender] = AccountState(
        address=sender, balance=10 * COIN_VALUE, nonce=5, frozen=frozen_val,
    )
    state.energy_resources[sender] = EnergyResource(
        frozen_tos=frozen_val, energy=0,
        freeze_records=[
            FreezeRecord(
                amount=frozen_val, energy_gained=0,
                freeze_height=0, unlock_height=99999,
            )
        ],
    )
    tx = _mk_freeze_tos(sender, nonce=5, amount=COIN_VALUE, days=3, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_frozen_overflow", state, tx
    )


def test_freeze_energy_overflow(state_test_group) -> None:
    """Freezing TOS when sender.energy is near U64_MAX should overflow.

    Freeze 1 TOS for 3 days => energy_gained = 1 * (3 * 2) = 6.
    Pre-state: sender.energy = U64_MAX - 5.
    energy + 6 = U64_MAX + 1 > U64_MAX => OVERFLOW.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE
    state.accounts[sender] = AccountState(
        address=sender, balance=10 * COIN_VALUE, nonce=5,
        frozen=0, energy=U64_MAX - 5,
    )
    state.energy_resources[sender] = EnergyResource(
        frozen_tos=0, energy=U64_MAX - 5,
    )
    state.global_state.total_energy = U64_MAX - 5
    tx = _mk_freeze_tos(sender, nonce=5, amount=COIN_VALUE, days=3, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_energy_overflow", state, tx
    )


def test_delegate_energy_overflow(state_test_group) -> None:
    """Delegation where delegatee.energy would overflow.

    Delegate 1 TOS for 3 days => energy_gained = 6.
    Pre-state: delegatee (BOB) energy = U64_MAX - 5.
    delegatee.energy + 6 = U64_MAX + 1 > U64_MAX => OVERFLOW.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE
    delegatee = BOB
    state.accounts[sender] = AccountState(
        address=sender, balance=10 * COIN_VALUE, nonce=5, frozen=0,
    )
    state.accounts[delegatee] = AccountState(
        address=delegatee, balance=0, nonce=0, energy=U64_MAX - 5,
    )
    state.global_state.total_energy = U64_MAX - 5
    entries = [DelegationEntry(delegatee=delegatee, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(sender, nonce=5, delegatees=entries, days=3, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "delegate_energy_overflow",
        state,
        tx,
    )


def test_withdraw_balance_overflow(state_test_group) -> None:
    """Withdrawing unfrozen TOS when sender.balance is near U64_MAX.

    Pre-state: sender.balance = U64_MAX - COIN_VALUE + 1,
    pending unfreeze amount = COIN_VALUE.
    balance + withdrawn = U64_MAX + 1 > U64_MAX => OVERFLOW.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE
    balance_val = U64_MAX - COIN_VALUE + 1
    state.accounts[sender] = AccountState(
        address=sender, balance=balance_val, nonce=5, frozen=COIN_VALUE,
    )
    state.energy_resources[sender] = EnergyResource(
        frozen_tos=COIN_VALUE, energy=0,
        pending_unfreezes=[
            PendingUnfreeze(amount=COIN_VALUE, expire_height=0),
        ],
    )
    tx = _mk_withdraw_unfrozen(sender, nonce=5, fee=0)
    state_test_group(
        "transactions/energy/withdraw_unfrozen.json",
        "withdraw_balance_overflow",
        state,
        tx,
    )


# ===================================================================
# Energy fee=0 validation tests
# Rust: "Energy transactions must have zero fee"
# ===================================================================


def test_freeze_tos_nonzero_fee(state_test_group) -> None:
    """Freeze with fee != 0 should be rejected."""
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=COIN_VALUE, days=7, fee=100)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_tos_nonzero_fee", state, tx
    )


def test_freeze_delegate_nonzero_fee(state_test_group) -> None:
    """Delegate with fee != 0 should be rejected."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=BOB, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=100)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_nonzero_fee",
        state,
        tx,
    )


def test_unfreeze_tos_nonzero_fee(state_test_group) -> None:
    """Unfreeze with fee != 0 should be rejected."""
    state = _base_state()
    state.energy_resources[ALICE].freeze_records[0].unlock_height = 0
    tx = _mk_unfreeze_tos(ALICE, nonce=5, amount=COIN_VALUE, from_delegation=False, fee=100)
    state_test_group(
        "transactions/energy/unfreeze_tos.json",
        "unfreeze_tos_nonzero_fee",
        state,
        tx,
    )


def test_withdraw_unfrozen_nonzero_fee(state_test_group) -> None:
    """Withdraw with fee != 0 should be rejected."""
    state = _base_state()
    state.energy_resources[ALICE].pending_unfreezes = [
        PendingUnfreeze(amount=COIN_VALUE, expire_height=0),
    ]
    tx = _mk_withdraw_unfrozen(ALICE, nonce=5, fee=100)
    state_test_group(
        "transactions/energy/withdraw_unfrozen.json",
        "withdraw_unfrozen_nonzero_fee",
        state,
        tx,
    )


# ===================================================================
# Delegate validation tests
# ===================================================================


def test_freeze_delegate_duplicate_delegatees(state_test_group) -> None:
    """Duplicate delegatee addresses should be rejected.

    Rust: "Duplicate delegatee in list".
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [
        DelegationEntry(delegatee=BOB, amount=COIN_VALUE),
        DelegationEntry(delegatee=BOB, amount=COIN_VALUE),
    ]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_duplicate_delegatees",
        state,
        tx,
    )


def test_freeze_delegate_not_found(state_test_group) -> None:
    """Delegatee account does not exist.

    Rust: "Delegatee account does not exist".
    """
    state = _base_state()
    unknown = bytes([99]) * 32
    entries = [DelegationEntry(delegatee=unknown, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_not_found",
        state,
        tx,
    )


def test_freeze_delegate_zero_amount(state_test_group) -> None:
    """Delegation amount = 0 per entry.

    Rust: "Delegation amount must be greater than zero".
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=BOB, amount=0)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_zero_amount",
        state,
        tx,
    )


def test_freeze_delegate_non_whole_tos(state_test_group) -> None:
    """Delegation amount not a multiple of COIN_VALUE.

    Rust: "Delegation amount must be a whole number of TOS".
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=BOB, amount=COIN_VALUE + COIN_VALUE // 2)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_non_whole_tos",
        state,
        tx,
    )


def test_freeze_delegate_below_minimum(state_test_group) -> None:
    """Delegation amount below MIN_FREEZE_TOS_AMOUNT.

    Rust: "Delegation amount must be at least 1 TOS".
    """
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=BOB, amount=MIN_FREEZE_TOS_AMOUNT // 2)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_below_minimum",
        state,
        tx,
    )


def test_freeze_delegate_insufficient_balance(state_test_group) -> None:
    """Total delegation amount exceeds sender balance.

    Rust: InsufficientFunds.
    """
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    sender = ALICE
    state.accounts[sender] = AccountState(
        address=sender, balance=COIN_VALUE, nonce=5
    )
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    state.accounts[CAROL] = AccountState(address=CAROL, balance=0, nonce=0)
    entries = [
        DelegationEntry(delegatee=BOB, amount=COIN_VALUE),
        DelegationEntry(delegatee=CAROL, amount=COIN_VALUE),
    ]
    tx = _mk_freeze_delegate(sender, nonce=5, delegatees=entries, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_insufficient_balance",
        state,
        tx,
    )


def test_freeze_delegate_duration_too_short(state_test_group) -> None:
    """Delegation duration below minimum (2 days < 3)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=BOB, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=2, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_duration_too_short",
        state,
        tx,
    )


def test_freeze_delegate_duration_too_long(state_test_group) -> None:
    """Delegation duration above maximum (366 days > 365)."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=0, nonce=0)
    entries = [DelegationEntry(delegatee=BOB, amount=COIN_VALUE)]
    tx = _mk_freeze_delegate(ALICE, nonce=5, delegatees=entries, days=366, fee=0)
    state_test_group(
        "transactions/energy/freeze_delegate.json",
        "freeze_delegate_duration_too_long",
        state,
        tx,
    )


# ===================================================================
# Unfreeze boundary tests
# ===================================================================


def test_unfreeze_non_whole_tos(state_test_group) -> None:
    """Unfreeze amount not a multiple of COIN_VALUE.

    Rust: "Unfreeze amount must be a whole number of TOS".
    """
    state = _base_state()
    state.energy_resources[ALICE].freeze_records[0].unlock_height = 0
    tx = _mk_unfreeze_tos(
        ALICE, nonce=5, amount=COIN_VALUE + COIN_VALUE // 2,
        from_delegation=False, fee=0,
    )
    state_test_group(
        "transactions/energy/unfreeze_tos.json",
        "unfreeze_non_whole_tos",
        state,
        tx,
    )


# ===================================================================
# Freeze exact boundary (MIN/MAX) tests
# ===================================================================


def test_freeze_duration_exact_min(state_test_group) -> None:
    """Freeze with exactly MIN_FREEZE_DURATION_DAYS (3). Should succeed."""
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=COIN_VALUE, days=3, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_duration_exact_min", state, tx
    )


def test_freeze_duration_exact_max(state_test_group) -> None:
    """Freeze with exactly MAX_FREEZE_DURATION_DAYS (365). Should succeed."""
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=COIN_VALUE, days=365, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_duration_exact_max", state, tx
    )


def test_freeze_exact_minimum_amount(state_test_group) -> None:
    """Freeze with exactly MIN_FREEZE_TOS_AMOUNT (1 TOS). Should succeed."""
    state = _base_state()
    tx = _mk_freeze_tos(ALICE, nonce=5, amount=MIN_FREEZE_TOS_AMOUNT, days=7, fee=0)
    state_test_group(
        "transactions/energy/freeze_tos.json", "freeze_exact_minimum_amount", state, tx
    )
