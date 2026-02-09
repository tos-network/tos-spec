"""Convert Python Transaction objects to the Rust serde JSON expected by `tos_codec`.

Scope: core tx types currently supported in `~/tos`:
Transfers, Burn, MultiSig, InvokeContract, DeployContract, Energy, AgentAccount,
UNO/Shield/Unshield transfers, RegisterName.
"""

from __future__ import annotations

import json
from typing import Any

from .types import EnergyPayload, FeeType, MultiSig, Transaction, TransactionType, TransferPayload


SERDE_VARIANT_MAP: dict[str, str] = {
    # Rust TransactionType uses `#[serde(rename_all = "snake_case")]`
    "transfers": "transfers",
    "burn": "burn",
    "multisig": "multi_sig",
    "invoke_contract": "invoke_contract",
    "deploy_contract": "deploy_contract",
    "energy": "energy",
    "agent_account": "agent_account",
    "uno_transfers": "uno_transfers",
    "shield_transfers": "shield_transfers",
    "unshield_transfers": "unshield_transfers",
    "register_name": "register_name",
}

FEE_TYPE_SERDE: dict[int, str] = {
    int(FeeType.TOS): "TOS",
    int(FeeType.ENERGY): "Energy",
    int(FeeType.UNO): "UNO",
}

ENERGY_VARIANT_MAP: dict[str, str] = {
    "freeze_tos": "FreezeTos",
    "freeze_tos_delegate": "FreezeTosDelegate",
    "unfreeze_tos": "UnfreezeTos",
    "withdraw_unfrozen": "WithdrawUnfrozen",
}

AGENT_VARIANT_MAP: dict[str, str] = {
    "register": "Register",
    "update_policy": "UpdatePolicy",
    "rotate_controller": "RotateController",
    "set_status": "SetStatus",
    "set_energy_pool": "SetEnergyPool",
    "set_session_key_root": "SetSessionKeyRoot",
    "add_session_key": "AddSessionKey",
    "revoke_session_key": "RevokeSessionKey",
}

# 32-byte values represented as `[u8; 32]` in serde JSON.
PUBKEY_FIELDS: set[str] = {
    "source",
    "destination",
    "controller",
    "new_controller",
    "delegatee",
    "energy_pool",
}

# 32-byte values represented as hex strings in serde JSON.
HASH_FIELDS: set[str] = {
    "asset",
    "contract",
    "policy_hash",
    "reference_hash",
}

# 64-byte values represented as hex strings in serde JSON.
SIGNATURE_FIELDS: set[str] = {
    "signature",
}

# `Vec<u8>` fields represented as `[]u8` in serde JSON.
VEC_U8_FIELDS: set[str] = {
    "extra_data",
    "module",
    "args",
    "commitment",
    "sender_handle",
    "receiver_handle",
    "proof",
    "ct_validity_proof",
}


def _bytes_to_pubkey(b: bytes) -> list[int]:
    if len(b) != 32:
        # Keep behavior simple: still serialize as bytes -> vec<u8>.
        return list(b)
    return list(b)


def _bytes_to_hash(b: bytes) -> str:
    return b.hex()


def _bytes_to_signature(b: bytes) -> str:
    return b.hex()


def _bytes_to_vec_u8(b: bytes) -> list[int]:
    return list(b)


def _convert_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        vb = bytes(value)
        if key in PUBKEY_FIELDS:
            return _bytes_to_pubkey(vb)
        if key in HASH_FIELDS:
            return _bytes_to_hash(vb)
        if key in SIGNATURE_FIELDS:
            return _bytes_to_signature(vb)
        if key in VEC_U8_FIELDS:
            return _bytes_to_vec_u8(vb)
        # Default: treat 32-byte blobs as pubkeys, else Vec<u8>.
        if len(vb) == 32:
            return _bytes_to_pubkey(vb)
        return _bytes_to_vec_u8(vb)
    if isinstance(value, dict):
        return _convert_dict(value)
    if isinstance(value, list):
        return [_convert_value(key, item) for item in value]
    return value


def _convert_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        out[k] = _convert_value(k, v)
    return out


def _convert_transfers(payload: list[TransferPayload]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in payload:
        out.append(
            {
                "asset": _bytes_to_hash(p.asset),
                "destination": _bytes_to_pubkey(p.destination),
                "amount": p.amount,
                "extra_data": _bytes_to_vec_u8(p.extra_data) if p.extra_data else None,
            }
        )
    return out


def _convert_energy(payload: EnergyPayload) -> dict[str, Any]:
    variant = ENERGY_VARIANT_MAP.get(payload.variant)
    if variant is None:
        raise ValueError(f"Unknown energy variant: {payload.variant}")
    inner: dict[str, Any] = {}
    if payload.amount is not None:
        inner["amount"] = payload.amount
    if payload.duration is not None:
        inner["duration_days"] = payload.duration.days
    if payload.delegatees is not None:
        inner["delegatees"] = [
            {"delegatee": _bytes_to_pubkey(d.delegatee), "amount": d.amount} for d in payload.delegatees
        ]
    if payload.from_delegation is not None:
        inner["from_delegation"] = payload.from_delegation
    if payload.record_index is not None:
        inner["record_index"] = payload.record_index
    if payload.delegatee_address is not None:
        inner["delegatee_address"] = _bytes_to_pubkey(payload.delegatee_address)
    if not inner:
        return variant
    return {variant: inner}


def _convert_agent_account(payload: dict[str, Any]) -> dict[str, Any]:
    variant_key = payload.get("variant", "")
    variant = AGENT_VARIANT_MAP.get(variant_key)
    if variant is None:
        raise ValueError(f"Unknown agent_account variant: {variant_key}")
    inner: dict[str, Any] = {}
    for k, v in payload.items():
        if k == "variant":
            continue
        inner[k] = _convert_value(k, v)
    if not inner:
        return variant
    return {variant: inner}


def _convert_multisig_payload(payload: dict[str, Any]) -> dict[str, Any]:
    threshold = payload["threshold"]
    participants = payload.get("participants", [])
    out = []
    for p in participants:
        if isinstance(p, str):
            out.append(_bytes_to_pubkey(bytes.fromhex(p)))
        else:
            out.append(_bytes_to_pubkey(bytes(p) if not isinstance(p, bytes) else p))
    return {"threshold": threshold, "participants": out}


def _convert_invoke_contract(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in payload.items():
        out[k] = _convert_value(k, v)
    return out


def _convert_deploy_contract(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in payload.items():
        out[k] = _convert_value(k, v)
    return out


def _build_data(tx: Transaction) -> dict[str, Any]:
    variant = SERDE_VARIANT_MAP.get(tx.tx_type.value)
    if variant is None:
        raise ValueError(f"Unknown tx_type: {tx.tx_type}")

    payload = tx.payload
    if tx.tx_type == TransactionType.TRANSFERS:
        return {variant: _convert_transfers(payload)}
    if tx.tx_type == TransactionType.BURN:
        return {variant: _convert_dict(payload) if isinstance(payload, dict) else payload}
    if tx.tx_type == TransactionType.ENERGY and isinstance(payload, EnergyPayload):
        return {variant: _convert_energy(payload)}
    if tx.tx_type == TransactionType.MULTISIG:
        return {variant: _convert_multisig_payload(payload)}
    if tx.tx_type == TransactionType.AGENT_ACCOUNT:
        return {variant: _convert_agent_account(payload)}
    if tx.tx_type == TransactionType.INVOKE_CONTRACT and isinstance(payload, dict):
        return {variant: _convert_invoke_contract(payload)}
    if tx.tx_type == TransactionType.DEPLOY_CONTRACT and isinstance(payload, dict):
        return {variant: _convert_deploy_contract(payload)}

    if isinstance(payload, dict):
        return {variant: _convert_dict(payload)}
    if isinstance(payload, list):
        return {variant: [_convert_dict(item) if isinstance(item, dict) else item for item in payload]}
    return {variant: payload}


def _convert_multisig(multisig: MultiSig | None) -> Any:
    if multisig is None:
        return None
    return {
        "signatures": [
            {"id": sig.signer_id, "signature": _bytes_to_signature(sig.signature)}
            for sig in multisig.signatures
        ]
    }


def tx_to_serde_json(tx: Transaction) -> str:
    obj: dict[str, Any] = {
        "version": int(tx.version),
        "chain_id": tx.chain_id,
        "source": _bytes_to_pubkey(tx.source),
        "data": _build_data(tx),
        "fee": tx.fee,
        "fee_type": FEE_TYPE_SERDE[int(tx.fee_type)],
        "nonce": tx.nonce,
        # Privacy-related fields are not modeled here (they are not needed for the core corpus).
        "source_commitments": [],
        "range_proof": None,
        "reference": {
            "hash": _bytes_to_hash(tx.reference_hash) if tx.reference_hash else "0" * 64,
            "topoheight": tx.reference_topoheight if tx.reference_topoheight is not None else 0,
        },
        "multisig": _convert_multisig(tx.multisig),
        "signature": _bytes_to_signature(tx.signature) if tx.signature else "0" * 128,
    }
    return json.dumps(obj)

