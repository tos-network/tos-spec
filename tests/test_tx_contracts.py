"""Contract tx fixtures (deploy_contract, invoke_contract)."""

from __future__ import annotations

from tos_spec.config import COIN_VALUE
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig(byte: int) -> bytes:
    return bytes([byte]) * 64


def _base_state() -> ChainState:
    sender = _addr(1)
    state = ChainState(network_chain_id=0)
    state.accounts[sender] = AccountState(
        address=sender, balance=100 * COIN_VALUE, nonce=5
    )
    return state


def _mk_deploy_contract(
    sender: bytes, nonce: int, module: bytes, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.DEPLOY_CONTRACT,
        payload={"module": module},
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


def _mk_invoke_contract(
    sender: bytes, nonce: int, contract: bytes, entry_id: int, max_gas: int, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=0,
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
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )


# --- deploy_contract specs ---


def test_deploy_contract_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    # Minimal valid ELF module
    module = b"\x7FELF" + b"\x00" * 100
    tx = _mk_deploy_contract(sender, nonce=5, module=module, fee=1_000)
    state_test_group(
        "transactions/contracts/deploy_contract.json",
        "deploy_contract_success",
        state,
        tx,
    )


def test_deploy_contract_invalid_module(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    module = b"\x00" * 100  # Not an ELF
    tx = _mk_deploy_contract(sender, nonce=5, module=module, fee=1_000)
    state_test_group(
        "transactions/contracts/deploy_contract.json",
        "deploy_contract_invalid_module",
        state,
        tx,
    )


# --- invoke_contract specs ---


def test_invoke_contract_success(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    contract = _hash(80)
    tx = _mk_invoke_contract(
        sender, nonce=5, contract=contract, entry_id=0, max_gas=100_000, fee=1_000
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_success",
        state,
        tx,
    )


def test_invoke_contract_with_deposits(state_test_group) -> None:
    state = _base_state()
    sender = _addr(1)
    contract = _hash(80)
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=0,
        source=sender,
        tx_type=TransactionType.INVOKE_CONTRACT,
        payload={
            "contract": contract,
            "deposits": [{"asset": _hash(0), "amount": COIN_VALUE}],
            "entry_id": 1,
            "max_gas": 200_000,
            "parameters": [],
        },
        fee=1_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(9),
        reference_topoheight=100,
        signature=_sig(7),
    )
    state_test_group(
        "transactions/contracts/invoke_contract.json",
        "invoke_contract_with_deposits",
        state,
        tx,
    )
