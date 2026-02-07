"""Contract tx fixtures (deploy_contract, invoke_contract)."""

from __future__ import annotations

from blake3 import blake3

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MAX_DEPOSIT_PER_INVOKE_CALL
from tos_spec.test_accounts import ALICE, BOB
from tos_spec.types import (
    AccountState,
    ChainState,
    ContractState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


# Minimal valid ELF module (ELF magic + padding)
_HELLO_ELF = b"\x7FELF" + b"\x00" * 100


def _compute_contract_address(deployer: bytes, bytecode: bytes) -> bytes:
    """Compute deterministic contract address matching Rust daemon.

    address = blake3(0xff || deployer || blake3(bytecode))
    """
    code_hash = blake3(bytecode).digest()
    data = b"\xff" + deployer + code_hash
    return blake3(data).digest()


def _base_state() -> ChainState:
    sender = ALICE
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[sender] = AccountState(
        address=sender, balance=100 * COIN_VALUE, nonce=5
    )
    return state


def _base_state_with_contract() -> tuple[ChainState, bytes]:
    """Create base state with a pre-deployed contract. Returns (state, contract_hash)."""
    state = _base_state()
    contract_hash = _compute_contract_address(ALICE, _HELLO_ELF)
    state.contracts[contract_hash] = ContractState(
        deployer=ALICE, module_hash=blake3(_HELLO_ELF).digest(), module=_HELLO_ELF
    )
    return state, contract_hash


def _mk_deploy_contract(
    sender: bytes, nonce: int, module: bytes, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.DEPLOY_CONTRACT,
        payload={"module": module},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


def _mk_invoke_contract(
    sender: bytes, nonce: int, contract: bytes, entry_id: int, max_gas: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.INVOKE_CONTRACT,
        payload={
            "contract": contract,
            "deposits": [],
            "entry_id": entry_id,
            "max_gas": max_gas,
            "parameters": [],
        },
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- deploy_contract specs ---


def test_deploy_contract_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    # Minimal valid ELF module
    module = _HELLO_ELF
    tx = _mk_deploy_contract(sender, nonce=5, module=module, fee=100_000)
    state_test_group(
        "transactions/contracts/deploy_contract.json",
        "deploy_contract_success",
        state,
        tx,
    )


def test_deploy_contract_invalid_module(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    module = b"\x00" * 100  # Not an ELF
    tx = _mk_deploy_contract(sender, nonce=5, module=module, fee=100_000)
    state_test_group(
        "transactions/contracts/deploy_contract.json",
        "deploy_contract_invalid_module",
        state,
        tx,
    )


# --- invoke_contract specs ---


def test_invoke_contract_success(state_test_group) -> None:
    state, contract_hash = _base_state_with_contract()
    sender = ALICE
    tx = _mk_invoke_contract(
        sender, nonce=5, contract=contract_hash, entry_id=0, max_gas=100_000, fee=100_000
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_success",
        state,
        tx,
    )


def test_invoke_contract_with_deposits(state_test_group) -> None:
    state, contract_hash = _base_state_with_contract()
    sender = ALICE
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.INVOKE_CONTRACT,
        payload={
            "contract": contract_hash,
            "deposits": [{"asset": _hash(0), "amount": COIN_VALUE}],
            "entry_id": 1,
            "max_gas": 200_000,
            "parameters": [],
        },
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_with_deposits",
        state,
        tx,
    )


def test_invoke_contract_zero_gas(state_test_group) -> None:
    """Invoke with max_gas=0."""
    state, contract_hash = _base_state_with_contract()
    sender = ALICE
    tx = _mk_invoke_contract(
        sender, nonce=5, contract=contract_hash, entry_id=0, max_gas=0, fee=100_000
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_zero_gas",
        state,
        tx,
    )


def test_deploy_contract_empty_code(state_test_group) -> None:
    """Deploy with empty bytecode."""
    state = _base_state()
    sender = ALICE
    tx = _mk_deploy_contract(sender, nonce=5, module=b"", fee=100_000)
    state_test_group(
        "transactions/contracts/deploy_contract.json",
        "deploy_contract_empty_code",
        state,
        tx,
    )


# ===================================================================
# Negative / boundary / authorization tests
# ===================================================================


# --- invoke_contract neg tests ---


def test_invoke_contract_not_found(state_test_group) -> None:
    """Invoke a contract that does not exist."""
    state = _base_state()
    fake_contract = _hash(99)
    tx = _mk_invoke_contract(
        ALICE, nonce=5, contract=fake_contract, entry_id=0, max_gas=100_000, fee=100_000
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_not_found",
        state,
        tx,
    )


def test_invoke_contract_insufficient_balance_for_gas(state_test_group) -> None:
    """Sender cannot afford max_gas + fee."""
    state, contract_hash = _base_state_with_contract()
    # Set balance to barely cover fee but not gas
    state.accounts[ALICE].balance = 200_000
    tx = _mk_invoke_contract(
        ALICE, nonce=5, contract=contract_hash, entry_id=0, max_gas=500_000, fee=100_000
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_insufficient_balance_for_gas",
        state,
        tx,
    )


def test_invoke_contract_too_many_deposits(state_test_group) -> None:
    """Exceed MAX_DEPOSIT_PER_INVOKE_CALL."""
    state, contract_hash = _base_state_with_contract()
    deposits = [{"asset": _hash(i % 256), "amount": 1} for i in range(MAX_DEPOSIT_PER_INVOKE_CALL + 1)]
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.INVOKE_CONTRACT,
        payload={
            "contract": contract_hash,
            "deposits": deposits,
            "entry_id": 0,
            "max_gas": 100_000,
            "parameters": [],
        },
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_too_many_deposits",
        state,
        tx,
    )


def test_invoke_contract_zero_deposit_amount(state_test_group) -> None:
    """Deposit amount in invoke must be > 0."""
    state, contract_hash = _base_state_with_contract()
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=ALICE,
        tx_type=TransactionType.INVOKE_CONTRACT,
        payload={
            "contract": contract_hash,
            "deposits": [{"asset": _hash(0), "amount": 0}],
            "entry_id": 0,
            "max_gas": 100_000,
            "parameters": [],
        },
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_zero_deposit_amount",
        state,
        tx,
    )


# --- deploy_contract neg tests ---


def test_deploy_contract_short_module(state_test_group) -> None:
    """Module too short to contain ELF magic."""
    state = _base_state()
    tx = _mk_deploy_contract(ALICE, nonce=5, module=b"\x7fEL", fee=100_000)
    state_test_group(
        "transactions/contracts/deploy_contract.json",
        "deploy_contract_short_module",
        state,
        tx,
    )
