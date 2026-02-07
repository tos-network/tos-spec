"""Account transaction specs (Multisig, AgentAccount)."""

from __future__ import annotations

from copy import deepcopy

from ..config import MAX_MULTISIG_PARTICIPANTS
from ..errors import ErrorCode, SpecError
from ..types import (
    AgentAccountMeta,
    ChainState,
    MultisigConfig,
    Transaction,
    TransactionType,
)


def verify(state: ChainState, tx: Transaction) -> None:
    if tx.tx_type == TransactionType.MULTISIG:
        _verify_multisig(state, tx)
    elif tx.tx_type == TransactionType.AGENT_ACCOUNT:
        _verify_agent_account(state, tx)
    else:
        raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported account tx type: {tx.tx_type}")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    if tx.tx_type == TransactionType.MULTISIG:
        return _apply_multisig(state, tx)
    elif tx.tx_type == TransactionType.AGENT_ACCOUNT:
        return _apply_agent_account(state, tx)
    raise SpecError(ErrorCode.INVALID_TYPE, f"unsupported account tx type: {tx.tx_type}")


# --- Multisig ---


def _verify_multisig(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "multisig payload must be dict")

    threshold = p.get("threshold", 0)
    participants = p.get("participants", [])

    if threshold == 0 and len(participants) == 0:
        if tx.source not in state.multisig_configs:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "multisig not configured")
        return

    if threshold <= 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "threshold must be > 0 for setup")

    if len(participants) == 0:
        raise SpecError(ErrorCode.INVALID_FORMAT, "participants must not be empty")

    if len(participants) > MAX_MULTISIG_PARTICIPANTS:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many multisig participants")

    seen: set[bytes] = set()
    for pk in participants:
        pk_bytes = bytes(pk) if not isinstance(pk, bytes) else pk
        if pk_bytes in seen:
            raise SpecError(ErrorCode.INVALID_SIGNATURE, "duplicate participant")
        seen.add(pk_bytes)

    if threshold > len(participants):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "threshold exceeds participant count")


def _apply_multisig(state: ChainState, tx: Transaction) -> ChainState:
    next_state = deepcopy(state)
    p = tx.payload
    threshold = p.get("threshold", 0)
    participants = p.get("participants", [])

    if threshold == 0 and len(participants) == 0:
        next_state.multisig_configs.pop(tx.source, None)
    else:
        participant_bytes = []
        for pk in participants:
            if isinstance(pk, bytes):
                participant_bytes.append(pk)
            else:
                participant_bytes.append(bytes(pk))
        next_state.multisig_configs[tx.source] = MultisigConfig(
            threshold=threshold, participants=participant_bytes
        )

    return next_state


# --- Agent Account ---


def _verify_agent_account(state: ChainState, tx: Transaction) -> None:
    p = tx.payload
    if not isinstance(p, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "agent_account payload must be dict")

    variant = p.get("variant", "")
    zero = bytes(32)

    if variant == "register":
        controller = p.get("controller", zero)
        if isinstance(controller, (list, tuple)):
            controller = bytes(controller)
        policy_hash = p.get("policy_hash", zero)
        if isinstance(policy_hash, (list, tuple)):
            policy_hash = bytes(policy_hash)
        if controller == zero:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "controller must not be zero")
        if controller == tx.source:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "controller must differ from owner")
        if policy_hash == zero:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "policy_hash must not be zero")
        if tx.source in state.agent_accounts:
            raise SpecError(ErrorCode.ACCOUNT_EXISTS, "agent account already registered")

    elif variant == "update_policy":
        policy_hash = p.get("policy_hash", zero)
        if isinstance(policy_hash, (list, tuple)):
            policy_hash = bytes(policy_hash)
        if policy_hash == zero:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "policy_hash must not be zero")
        if tx.source not in state.agent_accounts:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "agent account not registered")

    elif variant == "rotate_controller":
        new_controller = p.get("new_controller", zero)
        if isinstance(new_controller, (list, tuple)):
            new_controller = bytes(new_controller)
        if tx.source not in state.agent_accounts:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "agent account not registered")
        if new_controller == zero:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "new_controller must not be zero")
        if new_controller == tx.source:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "new_controller must differ from owner")
        meta = state.agent_accounts[tx.source]
        if new_controller == meta.controller:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "new_controller same as current")

    elif variant == "set_status":
        if tx.source not in state.agent_accounts:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "agent account not registered")
        status = p.get("status", 0)
        if status not in (0, 1):
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "invalid agent account parameter")

    elif variant == "set_energy_pool":
        if tx.source not in state.agent_accounts:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "agent account not registered")

    elif variant == "set_session_key_root":
        if tx.source not in state.agent_accounts:
            raise SpecError(ErrorCode.ACCOUNT_NOT_FOUND, "agent account not registered")

    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"unknown agent_account variant: {variant}")


def _apply_agent_account(state: ChainState, tx: Transaction) -> ChainState:
    next_state = deepcopy(state)
    p = tx.payload
    variant = p.get("variant", "")
    zero = bytes(32)

    if variant == "register":
        controller = p.get("controller", zero)
        if isinstance(controller, (list, tuple)):
            controller = bytes(controller)
        policy_hash = p.get("policy_hash", zero)
        if isinstance(policy_hash, (list, tuple)):
            policy_hash = bytes(policy_hash)
        energy_pool = p.get("energy_pool")
        if energy_pool is not None and isinstance(energy_pool, (list, tuple)):
            energy_pool = bytes(energy_pool)
        session_key_root = p.get("session_key_root")
        if session_key_root is not None and isinstance(session_key_root, (list, tuple)):
            session_key_root = bytes(session_key_root)

        next_state.agent_accounts[tx.source] = AgentAccountMeta(
            owner=tx.source,
            controller=controller,
            policy_hash=policy_hash,
            status=0,
            energy_pool=energy_pool,
            session_key_root=session_key_root,
        )

    elif variant == "update_policy":
        meta = next_state.agent_accounts[tx.source]
        policy_hash = p.get("policy_hash", zero)
        if isinstance(policy_hash, (list, tuple)):
            policy_hash = bytes(policy_hash)
        meta.policy_hash = policy_hash

    elif variant == "rotate_controller":
        meta = next_state.agent_accounts[tx.source]
        new_controller = p.get("new_controller", zero)
        if isinstance(new_controller, (list, tuple)):
            new_controller = bytes(new_controller)
        meta.controller = new_controller

    elif variant == "set_status":
        meta = next_state.agent_accounts[tx.source]
        meta.status = p.get("status", 0)

    elif variant == "set_energy_pool":
        meta = next_state.agent_accounts[tx.source]
        energy_pool = p.get("energy_pool")
        if energy_pool is not None and isinstance(energy_pool, (list, tuple)):
            energy_pool = bytes(energy_pool)
        meta.energy_pool = energy_pool

    elif variant == "set_session_key_root":
        meta = next_state.agent_accounts[tx.source]
        session_key_root = p.get("session_key_root")
        if session_key_root is not None and isinstance(session_key_root, (list, tuple)):
            session_key_root = bytes(session_key_root)
        meta.session_key_root = session_key_root

    return next_state
