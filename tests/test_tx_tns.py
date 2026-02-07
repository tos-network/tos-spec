"""TNS tx fixtures (register_name)."""

from __future__ import annotations

from tos_spec.config import (
    CHAIN_ID_DEVNET,
    COIN_VALUE,
    MAX_ENCRYPTED_SIZE,
    MAX_NAME_LENGTH,
    MAX_TTL,
    MIN_NAME_LENGTH,
    MIN_TTL,
)
from tos_spec.test_accounts import ALICE, BOB
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
    sender = ALICE
    tx = _mk_register_name(sender, nonce=5, name="alice", fee=10_000_000)
    state_test_group(
        "transactions/tns/register_name.json", "register_name_success", state, tx
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
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.EPHEMERAL_MESSAGE,
        payload={
            "sender_name_hash": sender_name_hash,
            "recipient_name_hash": recipient_name_hash,
            "ttl_blocks": ttl_blocks,
            "encrypted_content": encrypted_content,
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
    state = _base_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_hash(10),
        recipient_name_hash=_hash(11),
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


def test_ephemeral_message_ttl_too_low(state_test_group) -> None:
    """TTL below minimum."""
    state = _base_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_hash(10),
        recipient_name_hash=_hash(11),
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
    state = _base_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_hash(10),
        recipient_name_hash=_hash(11),
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
    state = _base_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_hash(10),
        recipient_name_hash=_hash(11),
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
    state = _base_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_hash(10),
        recipient_name_hash=_hash(11),
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
    state = _base_state()
    tx = _mk_ephemeral_message(
        ALICE, nonce=5,
        sender_name_hash=_hash(10),
        recipient_name_hash=_hash(10),
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
