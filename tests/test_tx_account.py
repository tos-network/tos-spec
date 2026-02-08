"""Account tx fixtures (multisig, agent_account)."""

from __future__ import annotations

from tos_spec.config import CHAIN_ID_DEVNET, MAX_MULTISIG_PARTICIPANTS
from tos_spec.test_accounts import ALICE, BOB, CAROL, DAVE
from tos_spec.types import (
    AccountState,
    AgentAccountMeta,
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
    return state


def _mk_multisig(
    sender: bytes, nonce: int, threshold: int, participants: list[bytes], fee: int
) -> Transaction:
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


def _mk_agent_account(
    sender: bytes, nonce: int, payload: dict, fee: int
) -> Transaction:
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


# --- multisig specs ---


def test_multisig_setup(state_test_group) -> None:
    state = _base_state()
    participants = [BOB, bytes([3]) * 32, bytes([4]) * 32]
    tx = _mk_multisig(ALICE, nonce=5, threshold=2, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json", "multisig_setup", state, tx
    )


def test_multisig_insufficient_fee(state_test_group) -> None:
    """multisig with balance below fee must fail: INSUFFICIENT_FEE (pre-check)."""
    state = _base_state()
    state.accounts[ALICE].balance = 99_999
    participants = [BOB, bytes([3]) * 32, bytes([4]) * 32]
    tx = _mk_multisig(ALICE, nonce=5, threshold=2, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_insufficient_fee",
        state,
        tx,
    )


def test_multisig_exact_balance_for_fee(state_test_group) -> None:
    """Sender balance equals fee (boundary: exact fee coverage)."""
    state = _base_state()
    state.accounts[ALICE].balance = 100_000
    participants = [BOB, bytes([3]) * 32, bytes([4]) * 32]
    tx = _mk_multisig(ALICE, nonce=5, threshold=2, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_exact_balance_for_fee",
        state,
        tx,
    )


def test_multisig_threshold_zero(state_test_group) -> None:
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=5, threshold=0, participants=[], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json", "multisig_threshold_zero", state, tx
    )


def test_multisig_single_participant(state_test_group) -> None:
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=5, threshold=1, participants=[BOB], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_single_participant",
        state,
        tx,
    )


def test_multisig_nonce_too_low(state_test_group) -> None:
    """Multisig with nonce below sender.nonce must fail."""
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=4, threshold=1, participants=[BOB], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_nonce_too_low",
        state,
        tx,
    )


def test_multisig_nonce_too_high_strict(state_test_group) -> None:
    """Multisig with nonce above sender.nonce must fail (strict nonce)."""
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=6, threshold=1, participants=[BOB], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_nonce_too_high_strict",
        state,
        tx,
    )


# --- agent_account specs ---


def test_agent_account_register(state_test_group) -> None:
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register",
        state,
        tx,
    )


def test_agent_account_register_insufficient_fee(state_test_group) -> None:
    """agent_account.register with balance below fee must fail: INSUFFICIENT_FEE (pre-check)."""
    state = _base_state()
    state.accounts[ALICE].balance = 99_999
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_insufficient_fee",
        state,
        tx,
    )


def test_agent_account_register_exact_balance_for_fee(state_test_group) -> None:
    """Sender balance equals fee (boundary: exact fee coverage)."""
    state = _base_state()
    state.accounts[ALICE].balance = 100_000
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_exact_balance_for_fee",
        state,
        tx,
    )


def test_agent_account_register_nonce_too_low(state_test_group) -> None:
    """Agent account register with nonce below sender.nonce must fail."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=4, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_nonce_too_low",
        state,
        tx,
    )


def test_agent_account_register_nonce_too_high_strict(state_test_group) -> None:
    """Agent account register with nonce above sender.nonce must fail (strict nonce)."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=6, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_nonce_too_high_strict",
        state,
        tx,
    )


def test_agent_account_update_policy(state_test_group) -> None:
    state = _base_state()
    payload = {
        "variant": "update_policy",
        "policy_hash": _hash(4),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_update_policy",
        state,
        tx,
    )


def test_agent_account_rotate_controller(state_test_group) -> None:
    state = _base_state()
    payload = {
        "variant": "rotate_controller",
        "new_controller": bytes([5]) * 32,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller",
        state,
        tx,
    )


# --- multisig boundary tests ---


def test_multisig_duplicate_participants(state_test_group) -> None:
    """Duplicate keys in participant list."""
    state = _base_state()
    participants = [BOB, BOB, CAROL]
    tx = _mk_multisig(ALICE, nonce=5, threshold=2, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_duplicate_participants",
        state,
        tx,
    )


# --- agent_account negative tests ---


def test_agent_account_register_zero_controller(state_test_group) -> None:
    """Register agent account with zero controller should fail."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": bytes(32),  # zero controller
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_zero_controller",
        state,
        tx,
    )


def test_agent_account_register_self_controller(state_test_group) -> None:
    """Register agent account with controller == owner should fail."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": ALICE,  # same as source
        "policy_hash": _hash(3),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_self_controller",
        state,
        tx,
    )


def test_agent_account_register_zero_policy_hash(state_test_group) -> None:
    """Register agent account with zero policy_hash should fail."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": bytes(32),  # zero hash
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_zero_policy_hash",
        state,
        tx,
    )


def test_agent_account_register_already_registered(state_test_group) -> None:
    """Register agent account when already registered should fail."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "register",
        "controller": CAROL,
        "policy_hash": _hash(4),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_already_registered",
        state,
        tx,
    )


def test_agent_account_update_policy_not_registered(state_test_group) -> None:
    """Update policy when not registered should fail."""
    state = _base_state()
    # No agent_accounts entry for ALICE
    payload = {
        "variant": "update_policy",
        "policy_hash": _hash(4),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_update_policy_not_registered",
        state,
        tx,
    )


def test_agent_account_update_policy_zero_hash(state_test_group) -> None:
    """Update policy with zero hash should fail."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "update_policy",
        "policy_hash": bytes(32),  # zero hash
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_update_policy_zero_hash",
        state,
        tx,
    )


def test_agent_account_rotate_controller_not_registered(state_test_group) -> None:
    """Rotate controller when not registered should fail."""
    state = _base_state()
    # No agent_accounts entry for ALICE
    payload = {
        "variant": "rotate_controller",
        "new_controller": bytes([5]) * 32,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller_not_registered",
        state,
        tx,
    )


def test_agent_account_rotate_controller_to_self(state_test_group) -> None:
    """Rotate controller to owner (self) should fail."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "rotate_controller",
        "new_controller": ALICE,  # same as owner
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller_to_self",
        state,
        tx,
    )


def test_agent_account_rotate_controller_zero(state_test_group) -> None:
    """Rotate controller to zero key should fail."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "rotate_controller",
        "new_controller": bytes(32),  # zero key
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller_zero",
        state,
        tx,
    )


def test_agent_account_set_status_not_registered(state_test_group) -> None:
    """Set status when not registered should fail."""
    state = _base_state()
    # No agent_accounts entry for ALICE
    payload = {
        "variant": "set_status",
        "status": 1,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_status_not_registered",
        state,
        tx,
    )


def test_agent_account_set_status_invalid(state_test_group) -> None:
    """Set status to invalid value should fail."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "set_status",
        "status": 99,  # invalid
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_status_invalid",
        state,
        tx,
    )


def test_agent_account_unknown_variant(state_test_group) -> None:
    """Unknown variant should fail."""
    state = _base_state()
    payload = {
        "variant": "nonexistent_variant",
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_unknown_variant",
        state,
        tx,
    )


# --- multisig boundary value tests ---


def test_multisig_threshold_exceeds_participants(state_test_group) -> None:
    """Multisig with threshold > len(participants) must fail."""
    state = _base_state()
    participants = [BOB, CAROL]
    tx = _mk_multisig(ALICE, nonce=5, threshold=5, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_threshold_exceeds_participants",
        state,
        tx,
    )


def test_multisig_max_participants(state_test_group) -> None:
    """Multisig with exactly MAX_MULTISIG_PARTICIPANTS (255) must succeed."""
    state = _base_state()
    # Generate 255 distinct participant keys
    participants = [bytes([i]) + bytes(31) for i in range(MAX_MULTISIG_PARTICIPANTS)]
    tx = _mk_multisig(ALICE, nonce=5, threshold=1, participants=participants, fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_max_participants",
        state,
        tx,
    )


def test_multisig_zero_participants_nonzero_threshold(state_test_group) -> None:
    """Multisig with threshold=1 but empty participants list must fail."""
    state = _base_state()
    tx = _mk_multisig(ALICE, nonce=5, threshold=1, participants=[], fee=100_000)
    state_test_group(
        "transactions/account/multisig.json",
        "multisig_zero_participants_nonzero_threshold",
        state,
        tx,
    )


# --- agent_account: rotate_controller same-as-current ---


def test_agent_account_rotate_controller_same_as_current(state_test_group) -> None:
    """Rotate controller to the same current controller should fail."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "rotate_controller",
        "new_controller": BOB,  # same as current controller
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller_same_as_current",
        state,
        tx,
    )


# --- agent_account: set_status success ---


def test_agent_account_set_status_zero(state_test_group) -> None:
    """Set status to 0 (active) should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=1,
    )
    payload = {
        "variant": "set_status",
        "status": 0,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_status_zero",
        state,
        tx,
    )


def test_agent_account_set_status_one(state_test_group) -> None:
    """Set status to 1 (disabled) should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "set_status",
        "status": 1,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_status_one",
        state,
        tx,
    )


def test_agent_account_set_status_two(state_test_group) -> None:
    """Set status to 2 should fail (valid values are 0 and 1 only)."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "set_status",
        "status": 2,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_status_two",
        state,
        tx,
    )


# --- agent_account: set_energy_pool ---


def test_agent_account_set_energy_pool_success(state_test_group) -> None:
    """Set energy pool to owner address should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "set_energy_pool",
        "energy_pool": ALICE,  # owner
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_energy_pool_success",
        state,
        tx,
    )


def test_agent_account_set_energy_pool_clear(state_test_group) -> None:
    """Clear energy pool (set to None) should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
        energy_pool=ALICE,
    )
    payload = {
        "variant": "set_energy_pool",
        "energy_pool": None,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_energy_pool_clear",
        state,
        tx,
    )


def test_agent_account_set_energy_pool_not_registered(state_test_group) -> None:
    """Set energy pool when not registered should fail."""
    state = _base_state()
    # No agent_accounts entry for ALICE
    payload = {
        "variant": "set_energy_pool",
        "energy_pool": ALICE,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_energy_pool_not_registered",
        state,
        tx,
    )


# --- agent_account: set_session_key_root ---


def test_agent_account_set_session_key_root_success(state_test_group) -> None:
    """Set session key root to a non-zero hash should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "set_session_key_root",
        "session_key_root": _hash(9),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_session_key_root_success",
        state,
        tx,
    )


def test_agent_account_set_session_key_root_clear(state_test_group) -> None:
    """Clear session key root (set to None) should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
        session_key_root=_hash(9),
    )
    payload = {
        "variant": "set_session_key_root",
        "session_key_root": None,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_session_key_root_clear",
        state,
        tx,
    )


def test_agent_account_set_session_key_root_not_registered(state_test_group) -> None:
    """Set session key root when not registered should fail."""
    state = _base_state()
    # No agent_accounts entry for ALICE
    payload = {
        "variant": "set_session_key_root",
        "session_key_root": _hash(9),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_set_session_key_root_not_registered",
        state,
        tx,
    )


# --- agent_account: register with energy_pool and session_key_root ---


def test_agent_account_register_with_energy_pool(state_test_group) -> None:
    """Register agent account with energy_pool set to owner."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
        "energy_pool": ALICE,
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_with_energy_pool",
        state,
        tx,
    )


def test_agent_account_register_with_session_key_root(state_test_group) -> None:
    """Register agent account with session_key_root set."""
    state = _base_state()
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(3),
        "session_key_root": _hash(9),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_register_with_session_key_root",
        state,
        tx,
    )


# --- agent_account: update_policy success ---


def test_agent_account_update_policy_success(state_test_group) -> None:
    """Update policy with non-zero hash when registered should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "update_policy",
        "policy_hash": _hash(4),
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_update_policy_success",
        state,
        tx,
    )


# --- agent_account: rotate_controller success ---


def test_agent_account_rotate_controller_success(state_test_group) -> None:
    """Rotate controller to a new valid controller should succeed."""
    state = _base_state()
    state.agent_accounts[ALICE] = AgentAccountMeta(
        owner=ALICE,
        controller=BOB,
        policy_hash=_hash(3),
        status=0,
    )
    payload = {
        "variant": "rotate_controller",
        "new_controller": DAVE,  # new controller
    }
    tx = _mk_agent_account(ALICE, nonce=5, payload=payload, fee=100_000)
    state_test_group(
        "transactions/account/agent_account.json",
        "agent_account_rotate_controller_success",
        state,
        tx,
    )
