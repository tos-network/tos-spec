"""TNS tx fixtures (register_name)."""

from __future__ import annotations

from tos_spec.config import (
    BASE_MESSAGE_FEE,
    CHAIN_ID_DEVNET,
    COIN_VALUE,
    MAX_ENCRYPTED_SIZE,
    MAX_NAME_LENGTH,
    MAX_TTL,
    MIN_NAME_LENGTH,
    MIN_TTL,
    REGISTRATION_FEE,
    TTL_ONE_DAY,
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


# Ristretto255 basepoint (valid compressed Ristretto point for receiver_handle)
_RISTRETTO_BASEPOINT = bytes.fromhex(
    "e2f2ae0a6abc4e71a884a961c500515f58e30b6aa582dd8db6a65945e08d2d76"
)


def _name_hash(name: str) -> bytes:
    """Compute blake3 hash of a TNS name (matches daemon's blake3_hash)."""
    import blake3
    return bytes.fromhex(blake3.blake3(name.encode()).hexdigest())


_SENDER_NAME = "alice"
_RECIPIENT_NAME = "bob.wallet"
_SENDER_NAME_HASH = _name_hash(_SENDER_NAME)
_RECIPIENT_NAME_HASH = _name_hash(_RECIPIENT_NAME)


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(address=ALICE, balance=COIN_VALUE, nonce=5)
    return state


def _msg_state() -> ChainState:
    """Base state with TNS names registered for ephemeral message tests."""
    state = _base_state()
    state.accounts[BOB] = AccountState(address=BOB, balance=COIN_VALUE, nonce=0)
    state.tns_names[_SENDER_NAME] = TnsRecord(
        name=_SENDER_NAME, owner=ALICE, registered_at=1
    )
    state.tns_by_owner[ALICE] = _SENDER_NAME
    state.tns_names[_RECIPIENT_NAME] = TnsRecord(
        name=_RECIPIENT_NAME, owner=BOB, registered_at=1
    )
    state.tns_by_owner[BOB] = _RECIPIENT_NAME
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
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="alice", fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_success", state, tx
    )


def test_register_name_nonce_too_low(state_test_group) -> None:
    """Strict nonce: tx.nonce < sender.nonce."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=4, name="alice", fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_nonce_too_low", state, tx
    )


def test_register_name_nonce_too_high_strict(state_test_group) -> None:
    """Strict nonce: tx.nonce > sender.nonce."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=6, name="alice", fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_nonce_too_high_strict",
        state,
        tx,
    )


def test_register_name_too_short(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="ab", fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_too_short", state, tx
    )


def test_register_name_too_long(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    long_name = "a" * (MAX_NAME_LENGTH + 1)
    tx = _mk_register_name(sender, nonce=5, name=long_name, fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_too_long", state, tx
    )


def test_register_name_min_length(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="a" * MIN_NAME_LENGTH, fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_min_length", state, tx
    )


# --- ephemeral_message specs ---


def _mk_ephemeral_message(
    sender: bytes, nonce: int, sender_name_hash: bytes, recipient_name_hash: bytes,
    ttl_blocks: int, encrypted_content: bytes, fee: int,
    receiver_handle: bytes | None = None,
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.EPHEMERAL_MESSAGE,
        payload={
            "sender_name_hash": sender_name_hash,
            "recipient_name_hash": recipient_name_hash,
            "message_nonce": nonce,
            "ttl_blocks": ttl_blocks,
            "encrypted_content": encrypted_content,
            "receiver_handle": receiver_handle or _RISTRETTO_BASEPOINT,
        },
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def test_ephemeral_message_success(state_test_group) -> None:
    """Valid ephemeral message with TTL and content."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * 100,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_success",
        state,
        tx,
    )


def test_ephemeral_message_nonce_too_low(state_test_group) -> None:
    """Strict nonce: tx.nonce < sender.nonce."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=4,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * 100,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_nonce_too_low",
        state,
        tx,
    )


def test_ephemeral_message_nonce_too_high_strict(state_test_group) -> None:
    """Strict nonce: tx.nonce > sender.nonce."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=6,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * 100,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_nonce_too_high_strict",
        state,
        tx,
    )


def test_ephemeral_message_ttl_too_low(state_test_group) -> None:
    """TTL below minimum."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL - 1,
        encrypted_content=bytes([0xAA]) * 100,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_ttl_too_low",
        state,
        tx,
    )


def test_ephemeral_message_ttl_too_high(state_test_group) -> None:
    """TTL above maximum."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MAX_TTL + 1,
        encrypted_content=bytes([0xAA]) * 100,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_ttl_too_high",
        state,
        tx,
    )


def test_ephemeral_message_content_too_long(state_test_group) -> None:
    """Content exceeds MAX_ENCRYPTED_SIZE (188 bytes)."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * (MAX_ENCRYPTED_SIZE + 1),
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_content_too_long",
        state,
        tx,
    )


def test_ephemeral_message_empty_content(state_test_group) -> None:
    """Empty content."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=b"",
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_empty_content",
        state,
        tx,
    )


def test_ephemeral_message_self_send(state_test_group) -> None:
    """Sender and recipient are the same name hash."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_SENDER_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * 100,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_self_send",
        state,
        tx,
    )


# --- boundary value tests ---


def test_register_name_exact_max_length(state_test_group) -> None:
    """Register name exactly at MAX_NAME_LENGTH (64) must succeed."""
    state = _base_state()
    sender = ALICE
    # Build a valid name: start with letter, then fill with lowercase alphanums
    name = "a" * MAX_NAME_LENGTH
    tx = _mk_register_name(sender, nonce=5, name=name, fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_exact_max_length",
        state,
        tx,
    )


def test_ephemeral_message_ttl_exact_min(state_test_group) -> None:
    """Ephemeral message with ttl exactly at MIN_TTL (100) must succeed."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xBB]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_ttl_exact_min",
        state,
        tx,
    )


def test_ephemeral_message_ttl_exact_max(state_test_group) -> None:
    """Ephemeral message with ttl exactly at MAX_TTL (86400) must succeed."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MAX_TTL,
        encrypted_content=bytes([0xBB]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_ttl_exact_max",
        state,
        tx,
    )


def test_ephemeral_message_content_exact_max(state_test_group) -> None:
    """Ephemeral message with content exactly at MAX_ENCRYPTED_SIZE (188 bytes) must succeed."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xCC]) * MAX_ENCRYPTED_SIZE,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_content_exact_max",
        state,
        tx,
    )


# ===================================================================
# TNS name character validation tests (from Rust verify_register_name_format)
# ===================================================================


def test_register_name_starts_with_digit(state_test_group) -> None:
    """Name starting with digit must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="1alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_starts_with_digit",
        state,
        tx,
    )


def test_register_name_starts_with_dot(state_test_group) -> None:
    """Name starting with dot must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name=".alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_starts_with_dot",
        state,
        tx,
    )


def test_register_name_starts_with_underscore(state_test_group) -> None:
    """Name starting with underscore must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="_alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_starts_with_underscore",
        state,
        tx,
    )


def test_register_name_starts_with_hyphen(state_test_group) -> None:
    """Name starting with hyphen must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="-alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_starts_with_hyphen",
        state,
        tx,
    )


def test_register_name_ends_with_dot(state_test_group) -> None:
    """Name ending with dot must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice.", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_ends_with_dot",
        state,
        tx,
    )


def test_register_name_ends_with_hyphen(state_test_group) -> None:
    """Name ending with hyphen must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice-", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_ends_with_hyphen",
        state,
        tx,
    )


def test_register_name_ends_with_underscore(state_test_group) -> None:
    """Name ending with underscore must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice_", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_ends_with_underscore",
        state,
        tx,
    )


def test_register_name_consecutive_dots(state_test_group) -> None:
    """Name with consecutive dots must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice..bob", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_consecutive_dots",
        state,
        tx,
    )


def test_register_name_consecutive_mixed_separators(state_test_group) -> None:
    """Name with consecutive mixed separators must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice.-bob", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_consecutive_mixed_separators",
        state,
        tx,
    )


def test_register_name_at_symbol(state_test_group) -> None:
    """Name with @ symbol must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice@bob", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_at_symbol",
        state,
        tx,
    )


def test_register_name_space(state_test_group) -> None:
    """Name with space must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice bob", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_space",
        state,
        tx,
    )


def test_register_name_uppercase(state_test_group) -> None:
    """Name with uppercase is normalized to lowercase and should succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="Alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_uppercase",
        state,
        tx,
    )


# ===================================================================
# TNS reserved name tests (from Rust is_reserved_name)
# ===================================================================


def test_register_name_reserved_admin(state_test_group) -> None:
    """Reserved name 'admin' must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="admin", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_reserved_admin",
        state,
        tx,
    )


def test_register_name_reserved_system(state_test_group) -> None:
    """Reserved name 'system' must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="system", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_reserved_system",
        state,
        tx,
    )


def test_register_name_reserved_validator(state_test_group) -> None:
    """Reserved name 'validator' must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="validator", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_reserved_validator",
        state,
        tx,
    )


def test_register_name_reserved_wallet(state_test_group) -> None:
    """Reserved name 'wallet' must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="wallet", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_reserved_wallet",
        state,
        tx,
    )


def test_register_name_reserved_tos(state_test_group) -> None:
    """Reserved name 'tos' must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="tos", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_reserved_tos",
        state,
        tx,
    )


# ===================================================================
# TNS confusing name tests (from Rust is_confusing_name)
# ===================================================================


def test_register_name_confusing_tos1_prefix(state_test_group) -> None:
    """Name starting with 'tos1' (address prefix) must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="tos1alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_tos1_prefix",
        state,
        tx,
    )


def test_register_name_confusing_tst1_prefix(state_test_group) -> None:
    """Name starting with 'tst1' (testnet prefix) must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="tst1alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_tst1_prefix",
        state,
        tx,
    )


def test_register_name_confusing_phishing_official(state_test_group) -> None:
    """Name containing 'official' (phishing keyword) must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice.official", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_phishing_official",
        state,
        tx,
    )


def test_register_name_confusing_phishing_verified(state_test_group) -> None:
    """Name containing 'verified' (phishing keyword) must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="verified.alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_phishing_verified",
        state,
        tx,
    )


def test_register_name_confusing_phishing_support(state_test_group) -> None:
    """Name containing 'support' must fail (both reserved and confusing)."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="support", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_confusing_phishing_support",
        state,
        tx,
    )


# ===================================================================
# TNS fee validation tests (from Rust verify_register_name_fee)
# ===================================================================


def test_register_name_insufficient_fee(state_test_group) -> None:
    """Registration fee below REGISTRATION_FEE must fail."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE - 1)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_insufficient_fee",
        state,
        tx,
    )


def test_register_name_exact_fee(state_test_group) -> None:
    """Registration fee exactly at REGISTRATION_FEE must succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_exact_fee",
        state,
        tx,
    )


# ===================================================================
# TNS duplicate registration tests (from Rust stateful checks)
# ===================================================================


def test_register_name_duplicate(state_test_group) -> None:
    """Registering an already taken name must fail."""
    from tos_spec.types import TnsRecord
    state = _base_state()
    state.tns_names["alice"] = TnsRecord(name="alice", owner=BOB, registered_at=1)
    tx = _mk_register_name(ALICE, nonce=5, name="alice", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_duplicate",
        state,
        tx,
    )


def test_register_name_account_already_has_name(state_test_group) -> None:
    """Sender already has a registered name must fail."""
    state = _base_state()
    state.tns_names["existingname"] = TnsRecord(name="existingname", owner=ALICE)
    state.tns_by_owner[ALICE] = "existingname"
    tx = _mk_register_name(ALICE, nonce=5, name="newname", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_account_already_has_name",
        state,
        tx,
    )


# ===================================================================
# TNS valid name with separators (from Rust test_valid_name_*)
# ===================================================================


def test_register_name_with_dot(state_test_group) -> None:
    """Name with valid dot separator must succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="john.doe", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_with_dot",
        state,
        tx,
    )


def test_register_name_with_hyphen(state_test_group) -> None:
    """Name with valid hyphen separator must succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="alice-wang", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_with_hyphen",
        state,
        tx,
    )


def test_register_name_with_underscore(state_test_group) -> None:
    """Name with valid underscore separator must succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="user_name", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_with_underscore",
        state,
        tx,
    )


def test_register_name_with_digits(state_test_group) -> None:
    """Name with digits after initial letter must succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="bob123", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_with_digits",
        state,
        tx,
    )


def test_register_name_mixed_separators(state_test_group) -> None:
    """Name with mixed (non-consecutive) separators must succeed."""
    state = _base_state()
    tx = _mk_register_name(ALICE, nonce=5, name="a.b-c_d", fee=REGISTRATION_FEE)
    state_test_group(
        "transactions/tns/register_name.json",
        "register_name_mixed_separators",
        state,
        tx,
    )


# ===================================================================
# Ephemeral message fee tier tests (from Rust verify_ephemeral_message_fee)
# ===================================================================


def test_ephemeral_message_fee_tier1(state_test_group) -> None:
    """TTL at minimum (100 blocks): tier 1 fee = BASE_MESSAGE_FEE."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier1",
        state,
        tx,
    )


def test_ephemeral_message_fee_tier1_insufficient(state_test_group) -> None:
    """TTL at minimum but fee below BASE_MESSAGE_FEE must fail."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL,
        encrypted_content=bytes([0xAA]) * 50,
        fee=BASE_MESSAGE_FEE - 1,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier1_insufficient",
        state,
        tx,
    )


def test_ephemeral_message_fee_tier2(state_test_group) -> None:
    """TTL just above tier 1 boundary (101 blocks): tier 2 fee = 2x BASE_MESSAGE_FEE."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL + 1,
        encrypted_content=bytes([0xAA]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier2",
        state,
        tx,
    )


def test_ephemeral_message_fee_tier2_insufficient(state_test_group) -> None:
    """TTL 101 but fee below 2x BASE_MESSAGE_FEE must fail."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MIN_TTL + 1,
        encrypted_content=bytes([0xAA]) * 50,
        fee=BASE_MESSAGE_FEE * 2 - 1,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier2_insufficient",
        state,
        tx,
    )


def test_ephemeral_message_fee_tier2_boundary(state_test_group) -> None:
    """TTL at TTL_ONE_DAY (28800 blocks): still tier 2 fee."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=TTL_ONE_DAY,
        encrypted_content=bytes([0xAA]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier2_boundary",
        state,
        tx,
    )


def test_ephemeral_message_fee_tier3(state_test_group) -> None:
    """TTL just above TTL_ONE_DAY (28801 blocks): tier 3 fee = 3x BASE_MESSAGE_FEE."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=TTL_ONE_DAY + 1,
        encrypted_content=bytes([0xAA]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier3",
        state,
        tx,
    )


def test_ephemeral_message_fee_tier3_insufficient(state_test_group) -> None:
    """TTL 28801 but fee below 3x BASE_MESSAGE_FEE must fail."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=TTL_ONE_DAY + 1,
        encrypted_content=bytes([0xAA]) * 50,
        fee=BASE_MESSAGE_FEE * 3 - 1,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_tier3_insufficient",
        state,
        tx,
    )


def test_ephemeral_message_fee_max_ttl(state_test_group) -> None:
    """TTL at MAX_TTL (86400 blocks): tier 3 fee."""
    state = _msg_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_SENDER_NAME_HASH,
        recipient_name_hash=_RECIPIENT_NAME_HASH,
        ttl_blocks=MAX_TTL,
        encrypted_content=bytes([0xAA]) * 50,
        fee=100_000,
    )
    state_test_group(
        "transactions/tns/ephemeral_message.json",
        "ephemeral_message_fee_max_ttl",
        state,
        tx,
    )
