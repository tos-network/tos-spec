"""Contract transaction specs (DeployContract, InvokeContract)."""

from __future__ import annotations

from copy import deepcopy

from blake3 import blake3

from ..config import COIN_VALUE, MAX_DEPOSIT_PER_INVOKE_CALL
from ..errors import ErrorCode, SpecError
from ..types import ChainState, ContractState, Transaction, TransactionType


def verify(state: ChainState, tx: Transaction) -> None:
    if tx.tx_type == TransactionType.DEPLOY_CONTRACT:
        _verify_deploy(state, tx)
    elif tx.tx_type == TransactionType.INVOKE_CONTRACT:
        _verify_invoke(state, tx)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported contract tx type: {tx.tx_type}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    if tx.tx_type == TransactionType.DEPLOY_CONTRACT:
        return _apply_deploy(state, tx)
    elif tx.tx_type == TransactionType.INVOKE_CONTRACT:
        return _apply_invoke(state, tx)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported contract tx type: {tx.tx_type}")


def _verify_deploy(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "deploy_contract payload must be dict")

    module = p.get("module", b"")
    if isinstance(module, (list, tuple)):
        module = bytes(module)
    if not module:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "module must not be empty")


def _apply_deploy(state: ChainState, tx: Transaction) -> ChainState:
    ns = deepcopy(state)
    p = tx.payload
    module = p.get("module", b"")
    if isinstance(module, (list, tuple)):
        module = bytes(module)

    # Deduct deployment cost (1 COIN_VALUE)
    sender = ns.accounts.get(tx.source)
    if sender is not None:
        sender.balance -= COIN_VALUE

    module_hash = blake3(module).digest()
    ns.contracts[module_hash] = ContractState(
        deployer=tx.source, module_hash=module_hash
    )
    return ns


def _verify_invoke(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invoke_contract payload must be dict")

    max_gas = p.get("max_gas", 0)
    if max_gas <= 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "max_gas must be > 0")

    deposits = p.get("deposits", [])
    if len(deposits) > MAX_DEPOSIT_PER_INVOKE_CALL:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many deposits")

    for d in deposits:
        if not isinstance(d, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "deposit must be dict")
        amount = d.get("amount", 0)
        if amount <= 0:
            raise SpecError(ErrorCode.INVALID_AMOUNT, "deposit amount must be > 0")


def _apply_invoke(state: ChainState, tx: Transaction) -> ChainState:
    ns = deepcopy(state)
    p = tx.payload
    deposits = p.get("deposits", [])

    sender = ns.accounts.get(tx.source)
    if sender is None:
        raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "sender not found")

    for d in deposits:
        amount = d.get("amount", 0)
        if sender.balance < amount:
            raise SpecError(ErrorCode.INSUFFICIENT_BALANCE, "insufficient balance for deposit")
        sender.balance -= amount

    return ns
