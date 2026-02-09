"""TNS tx fixtures (register_name only)."""

from __future__ import annotations

from tos_spec.config import (
    CHAIN_ID_DEVNET,
    COIN_VALUE,
    MAX_NAME_LENGTH,
    MIN_NAME_LENGTH,
    REGISTRATION_FEE,
)
from tos_spec.test_accounts import ALICE, BOB
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    TnsRecord,
    Transaction,
    TransactionType,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=COIN_VALUE, nonce=5)
    return state


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


def test_register_name_success(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE)
    state_test_group("transactions/tns/register_name.json", "register_name_success", state, tx)


def test_register_name_nonce_too_low(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=4, name="alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_nonce_too_low",
        state,
        tx,
    )


def test_register_name_nonce_too_high_strict(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=6, name="alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_nonce_too_high_strict",
        state,
        tx,
    )


def test_register_name_too_short(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="ab", fee=REGISTRATION_FEE)
    state_test_group("transactions/tns/register_name.json", "register_name_too_short", state, tx)


def test_register_name_too_long(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="a" * (MAX_NAME_LENGTH + 1), fee=REGISTRATION_FEE)
    state_test_group("transactions/tns/register_name.json", "register_name_too_long", state, tx)


def test_register_name_min_length(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="a" * MIN_NAME_LENGTH, fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_min_length",
        state,
        tx,
    )


def test_register_name_exact_max_length(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="a" * MAX_NAME_LENGTH, fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_exact_max_length",
        state,
        tx,
    )


def test_register_name_invalid_starts_with_digit(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="1alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_starts_with_digit",
        state,
        tx,
    )


def test_register_name_invalid_ends_with_separator(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice.", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_ends_with_dot",
        state,
        tx,
    )


def test_register_name_consecutive_separators(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="a..b", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_consecutive_dots",
        state,
        tx,
    )


def test_register_name_invalid_char_at_symbol(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice@tos", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_at_symbol",
        state,
        tx,
    )


def test_register_name_reserved_admin(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="admin", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_reserved_admin",
        state,
        tx,
    )


def test_register_name_confusing_tos1_prefix(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="tos1abcdef", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_tos1_prefix",
        state,
        tx,
    )


def test_register_name_confusing_phishing_keyword(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="official_support", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_phishing_support",
        state,
        tx,
    )


def test_register_name_insufficient_fee(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE - 1)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_insufficient_fee",
        state,
        tx,
    )


def test_register_name_fee_zero(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=0)
    state_test_group("transactions/tns/register_name.json", "register_name_fee_zero", state, tx)


def test_register_name_insufficient_balance_for_fee(state_test_group) -> None:
    state = _base_state()
    state.accounts[ALICE].balance = REGISTRATION_FEE - 1
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_insufficient_balance_for_fee",
        state,
        tx,
    )


def test_register_name_duplicate(state_test_group) -> None:
    state = _base_state()
    state.tns_names["alice"] = TnsRecord(name="alice", owner=BOB, registered_at=1)
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE)
    state_test_group("transactions/tns/register_name.json", "register_name_duplicate", state, tx)


def test_register_name_account_already_has_name(state_test_group) -> None:
    state = _base_state()
    state.tns_names["existingname"] = TnsRecord(name="existingname", owner=ALICE, registered_at=1)
    state.tns_by_owner[ALICE] = "existingname"
    tx = _mk_register_name(ALICE, nonce=5, name="newname", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_account_already_has_name",
        state,
        tx,
    )


def test_register_name_with_separators(state_test_group) -> None:
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="a.b-c_d", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_mixed_separators",
        state,
        tx,
    )

