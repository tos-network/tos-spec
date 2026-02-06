"""Adapter to convert Python Transaction objects to Rust serde JSON format.

This module bridges the Python Transaction dataclass representation to the
JSON format expected by tos_common's serde deserialization, enabling
byte-identical wire encoding via the tos_codec extension.
"""

from __future__ import annotations

import json
from typing import Any

from .types import (
    DelegationEntry,
    EnergyPayload,
    FeeType,
    FreezeDuration,
    MultiSig,
    Transaction,
    TransactionType,
    TransferPayload,
)

# Maps Python TransactionType enum values to Rust serde variant names.
# TransactionType uses #[serde(rename_all = "snake_case")] so most map directly.
SERDE_VARIANT_MAP: dict[str, str] = {
    "transfers": "transfers",
    "burn": "burn",
    "multisig": "multi_sig",
    "invoke_contract": "invoke_contract",
    "deploy_contract": "deploy_contract",
    "energy": "energy",
    "bind_referrer": "bind_referrer",
    "batch_referral_reward": "batch_referral_reward",
    "set_kyc": "set_kyc",
    "revoke_kyc": "revoke_kyc",
    "renew_kyc": "renew_kyc",
    "transfer_kyc": "transfer_kyc",
    "appeal_kyc": "appeal_kyc",
    "bootstrap_committee": "bootstrap_committee",
    "register_committee": "register_committee",
    "update_committee": "update_committee",
    "emergency_suspend": "emergency_suspend",
    "agent_account": "agent_account",
    "uno_transfers": "uno_transfers",
    "shield_transfers": "shield_transfers",
    "unshield_transfers": "unshield_transfers",
    "register_name": "register_name",
    "ephemeral_message": "ephemeral_message",
    "create_escrow": "create_escrow",
    "deposit_escrow": "deposit_escrow",
    "release_escrow": "release_escrow",
    "refund_escrow": "refund_escrow",
    "challenge_escrow": "challenge_escrow",
    "dispute_escrow": "dispute_escrow",
    "appeal_escrow": "appeal_escrow",
    "submit_verdict": "submit_verdict",
    "submit_verdict_by_juror": "submit_verdict_by_juror",
    "commit_arbitration_open": "commit_arbitration_open",
    "commit_vote_request": "commit_vote_request",
    "commit_selection_commitment": "commit_selection_commitment",
    "commit_juror_vote": "commit_juror_vote",
    "register_arbiter": "register_arbiter",
    "update_arbiter": "update_arbiter",
    "slash_arbiter": "slash_arbiter",
    "request_arbiter_exit": "request_arbiter_exit",
    "withdraw_arbiter_stake": "withdraw_arbiter_stake",
    "cancel_arbiter_exit": "cancel_arbiter_exit",
}

# Field names that hold CompressedPublicKey values (32-byte keys serialized
# as arrays of u8 ints in serde JSON).
PUBKEY_FIELDS: set[str] = {
    "source",
    "destination",
    "provider",
    "controller",
    "new_controller",
    "referrer",
    "delegatee",
    "buyer",
    "seller",
    "arbiter",
    "issuer",
    "subject",
    "target",
    "from_user",
    "from_issuer",
    "to_issuer",
    "arbiter_pubkey",
    "member_pubkey",
    "juror_pubkey",
    "proposer",
    "account",
    "public_key",
    "energy_pool",
}

# Field names that hold Hash values (32-byte hashes serialized as hex strings).
HASH_FIELDS: set[str] = {
    "asset",
    "contract",
    "escrow_id",
    "dispute_id",
    "request_id",
    "committee_id",
    "source_committee_id",
    "dest_committee_id",
    "original_committee_id",
    "parent_committee_id",
    "parent_id",
    "reason_hash",
    "data_hash",
    "new_data_hash",
    "documents_hash",
    "policy_hash",
    "session_key_root",
    "evidence_hash",
    "new_evidence_hash",
    "completion_proof",
    "arbitration_open_hash",
    "vote_request_hash",
    "selection_commitment_id",
    "vote_hash",
    "sender_name_hash",
    "recipient_name_hash",
}

# Field names that hold Signature values (64 bytes, serialized as hex strings).
SIGNATURE_FIELDS: set[str] = {
    "signature",
    "opener_signature",
    "coordinator_signature",
    "juror_signature",
}

# Field names that hold Vec<u8> data (serialized as arrays of u8 ints).
VEC_U8_FIELDS: set[str] = {
    "extra_data",
    "module",
    "metadata",
    "encrypted_content",
    "receiver_handle",
    "commitment",
    "sender_handle",
    "proof",
    "ct_validity_proof",
    "arbitration_open_payload",
    "vote_request_payload",
    "selection_commitment_payload",
    "vote_payload",
}

# Maps Python FeeType int values to Rust serde string representations.
FEE_TYPE_SERDE: dict[int, str] = {
    FeeType.TOS: "TOS",
    FeeType.ENERGY: "Energy",
    FeeType.UNO: "UNO",
}

# Maps Python EnergyPayload variant names to Rust serde enum variant names.
# EnergyPayload has no rename_all, so PascalCase is used.
ENERGY_VARIANT_MAP: dict[str, str] = {
    "freeze_tos": "FreezeTos",
    "freeze_tos_delegate": "FreezeTosDelegate",
    "unfreeze_tos": "UnfreezeTos",
    "withdraw_unfrozen": "WithdrawUnfrozen",
}

# Maps Python AgentAccount variant names to Rust serde enum variant names.
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

# MemberRole: no rename_all, PascalCase variants
_MEMBER_ROLE_MAP: dict[int, str] = {
    0: "Chair",
    1: "ViceChair",
    2: "Member",
    3: "Observer",
}

# MemberStatus: no rename_all, PascalCase variants
_MEMBER_STATUS_MAP: dict[int, str] = {
    0: "Active",
    1: "Suspended",
    2: "Removed",
}

# KycRegion: no rename_all, PascalCase variants
_KYC_REGION_MAP: dict[int, str] = {
    0: "Unspecified",
    1: "AsiaPacific",
    2: "Europe",
    3: "NorthAmerica",
    4: "LatinAmerica",
    5: "MiddleEast",
    6: "Africa",
    7: "Oceania",
    255: "Global",
}

# AppealMode: rename_all = "snake_case"
_APPEAL_MODE_MAP: dict[int, str] = {
    0: "committee",
    1: "dao_governance",
}

# ArbitrationMode: rename_all = "kebab-case"
_ARBITRATION_MODE_MAP: dict[int, str] = {
    0: "none",
    1: "single",
    2: "committee",
    3: "dao-governance",
}

# ExpertiseDomain: rename_all = "kebab-case"
# serde kebab-case splits on each uppercase boundary: AIAgent -> a-i-agent
_EXPERTISE_DOMAIN_MAP: dict[int, str] = {
    0: "general",
    1: "a-i-agent",
    2: "smart-contract",
    3: "payment",
    4: "de-fi",
    5: "governance",
    6: "identity",
    7: "data",
    8: "security",
    9: "gaming",
    10: "data-service",
    11: "digital-asset",
    12: "cross-chain",
    13: "nft",
}

# ArbiterStatus: rename_all = "kebab-case"
_ARBITER_STATUS_MAP: dict[int, str] = {
    0: "active",
    1: "suspended",
    2: "exiting",
    3: "removed",
}

# Maps field names to their enum conversion maps.
# When a field name is found in a payload dict and its value is an int,
# it gets converted to the corresponding serde string.
_ENUM_FIELD_MAP: dict[str, dict[int, str]] = {
    "role": _MEMBER_ROLE_MAP,
    "new_role": _MEMBER_ROLE_MAP,
    "appeal_mode": _APPEAL_MODE_MAP,
    "mode": _ARBITRATION_MODE_MAP,
    "region": _KYC_REGION_MAP,
    "status": _ARBITER_STATUS_MAP,
    "new_status": _MEMBER_STATUS_MAP,
}


def _bytes_to_pubkey(b: bytes) -> list[int]:
    """Convert 32-byte public key to array of u8 ints for serde."""
    return list(b)


def _bytes_to_hash(b: bytes) -> str:
    """Convert 32-byte hash to hex string for serde."""
    return b.hex()


def _bytes_to_signature(b: bytes) -> str:
    """Convert 64-byte signature to hex string for serde."""
    return b.hex()


def _bytes_to_vec_u8(b: bytes) -> list[int]:
    """Convert bytes to array of u8 ints for serde."""
    return list(b)


def _convert_value(key: str, value: Any) -> Any:
    """Convert a single value based on its field name."""
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = bytes(value)
        if key in PUBKEY_FIELDS:
            return _bytes_to_pubkey(value)
        if key in HASH_FIELDS:
            return _bytes_to_hash(value)
        if key in SIGNATURE_FIELDS:
            return _bytes_to_signature(value)
        if key in VEC_U8_FIELDS:
            return _bytes_to_vec_u8(value)
        # Default: treat unknown bytes as pubkey (32 bytes) or vec_u8
        if len(value) == 32:
            return _bytes_to_pubkey(value)
        return _bytes_to_vec_u8(value)
    # Convert enum int fields to serde string variants
    if isinstance(value, int) and key in _ENUM_FIELD_MAP:
        enum_map = _ENUM_FIELD_MAP[key]
        if value in enum_map:
            return enum_map[value]
    return value


def _convert_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively convert a dict payload, handling bytes fields appropriately."""
    result: dict[str, Any] = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = _convert_dict(value)
        elif isinstance(value, list):
            result[key] = [_convert_list_item(key, item) for item in value]
        else:
            result[key] = _convert_value(key, value)
    return result


def _convert_list_item(parent_key: str, item: Any) -> Any:
    """Convert an item in a list payload."""
    if isinstance(item, dict):
        return _convert_dict(item)
    if isinstance(item, (bytes, bytearray)):
        return _convert_value(parent_key, bytes(item))
    if isinstance(item, str) and parent_key in PUBKEY_FIELDS:
        return _bytes_to_pubkey(bytes.fromhex(item))
    return item


def _convert_transfers(transfers: list[TransferPayload]) -> list[dict[str, Any]]:
    """Convert TransferPayload list to serde format."""
    result = []
    for t in transfers:
        entry: dict[str, Any] = {
            "asset": _bytes_to_hash(t.asset),
            "destination": _bytes_to_pubkey(t.destination),
            "amount": t.amount,
            "extra_data": _bytes_to_vec_u8(t.extra_data) if t.extra_data is not None else None,
        }
        result.append(entry)
    return result


def _convert_energy(payload: EnergyPayload) -> Any:
    """Convert EnergyPayload to serde format (externally-tagged enum, PascalCase)."""
    variant = ENERGY_VARIANT_MAP.get(payload.variant)
    if variant is None:
        raise ValueError(f"Unknown energy variant: {payload.variant}")

    if payload.variant == "freeze_tos":
        inner: dict[str, Any] = {
            "amount": payload.amount,
            "duration": {"days": payload.duration.days},
        }
    elif payload.variant == "freeze_tos_delegate":
        inner = {
            "delegatees": [
                {
                    "delegatee": _bytes_to_pubkey(d.delegatee),
                    "amount": d.amount,
                }
                for d in (payload.delegatees or [])
            ],
            "duration": {"days": payload.duration.days},
        }
    elif payload.variant == "unfreeze_tos":
        inner = {
            "amount": payload.amount,
            "from_delegation": payload.from_delegation,
            "record_index": payload.record_index,
            "delegatee_address": _bytes_to_pubkey(payload.delegatee_address)
            if payload.delegatee_address is not None
            else None,
        }
    elif payload.variant == "withdraw_unfrozen":
        return variant
    else:
        raise ValueError(f"Unknown energy variant: {payload.variant}")

    return {variant: inner}


def _convert_agent_account(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert agent_account payload to serde format (externally-tagged, PascalCase)."""
    variant_key = payload["variant"]
    variant = AGENT_VARIANT_MAP.get(variant_key)
    if variant is None:
        raise ValueError(f"Unknown agent_account variant: {variant_key}")

    inner = {}
    for key, value in payload.items():
        if key == "variant":
            continue
        if isinstance(value, dict):
            inner[key] = _convert_dict(value)
        elif isinstance(value, list):
            inner[key] = [_convert_list_item(key, item) for item in value]
        else:
            inner[key] = _convert_value(key, value)

    return {variant: inner}


def _convert_multisig_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Convert multisig payload to serde format."""
    result: dict[str, Any] = {"threshold": payload["threshold"]}
    participants = payload.get("participants", [])
    converted = []
    for p in participants:
        if isinstance(p, str):
            converted.append(_bytes_to_pubkey(bytes.fromhex(p)))
        else:
            converted.append(_bytes_to_pubkey(p))
    result["participants"] = converted
    return result


def _convert_committee_update(update: dict[str, Any]) -> Any:
    """Convert committee update data to serde format (externally-tagged enum, PascalCase)."""
    update_type = update["type"]
    variant_map = {
        "add_member": "AddMember",
        "remove_member": "RemoveMember",
        "update_member_role": "UpdateMemberRole",
        "update_member_status": "UpdateMemberStatus",
        "update_threshold": "UpdateThreshold",
        "update_kyc_threshold": "UpdateKycThreshold",
        "update_name": "UpdateName",
        "suspend_committee": "SuspendCommittee",
        "activate_committee": "ActivateCommittee",
    }
    variant = variant_map.get(update_type)
    if variant is None:
        raise ValueError(f"Unknown committee update type: {update_type}")

    inner: dict[str, Any] = {}
    for key, value in update.items():
        if key == "type":
            continue
        inner[key] = _convert_value(key, value)

    if not inner:
        return variant
    return {variant: inner}


def _convert_expertise_list(expertise: list[Any]) -> list[str]:
    """Convert a list of ExpertiseDomain int values to serde strings."""
    return [_EXPERTISE_DOMAIN_MAP.get(e, str(e)) if isinstance(e, int) else e for e in expertise]


def _build_data(tx: Transaction) -> dict[str, Any]:
    """Build the serde 'data' field (externally-tagged TransactionType enum)."""
    variant = SERDE_VARIANT_MAP.get(tx.tx_type.value)
    if variant is None:
        raise ValueError(f"Unknown tx_type: {tx.tx_type}")

    payload = tx.payload

    if tx.tx_type == TransactionType.TRANSFERS:
        return {variant: _convert_transfers(payload)}

    if tx.tx_type == TransactionType.BURN:
        return {variant: _convert_dict(payload) if isinstance(payload, dict) else payload}

    if tx.tx_type == TransactionType.ENERGY:
        if isinstance(payload, EnergyPayload):
            return {variant: _convert_energy(payload)}
        return {variant: payload}

    if tx.tx_type == TransactionType.MULTISIG:
        return {variant: _convert_multisig_payload(payload)}

    if tx.tx_type == TransactionType.AGENT_ACCOUNT:
        return {variant: _convert_agent_account(payload)}

    if tx.tx_type in (
        TransactionType.REQUEST_ARBITER_EXIT,
        TransactionType.CANCEL_ARBITER_EXIT,
    ):
        return {variant: None}

    if tx.tx_type == TransactionType.UPDATE_COMMITTEE:
        if isinstance(payload, dict):
            result: dict[str, Any] = {}
            for key, value in payload.items():
                if key == "update" and isinstance(value, dict) and "type" in value:
                    result[key] = _convert_committee_update(value)
                elif isinstance(value, list):
                    result[key] = [
                        _convert_dict(item) if isinstance(item, dict) else _convert_value(key, item)
                        for item in value
                    ]
                elif isinstance(value, dict):
                    result[key] = _convert_dict(value)
                else:
                    result[key] = _convert_value(key, value)
            return {variant: result}

    if tx.tx_type in (TransactionType.REGISTER_ARBITER, TransactionType.UPDATE_ARBITER):
        if isinstance(payload, dict):
            result = {}
            for key, value in payload.items():
                if key == "expertise" and isinstance(value, list):
                    result[key] = _convert_expertise_list(value)
                elif isinstance(value, dict):
                    result[key] = _convert_dict(value)
                elif isinstance(value, list):
                    result[key] = [
                        _convert_dict(item) if isinstance(item, dict) else _convert_value(key, item)
                        for item in value
                    ]
                else:
                    result[key] = _convert_value(key, value)
            return {variant: result}

    # Generic dict payload
    if isinstance(payload, dict):
        return {variant: _convert_dict(payload)}

    # List payloads (uno_transfers, shield_transfers, etc.)
    if isinstance(payload, list):
        return {variant: [_convert_dict(item) if isinstance(item, dict) else item for item in payload]}

    return {variant: payload}


def _convert_multisig(multisig: MultiSig | None) -> Any:
    """Convert MultiSig to serde format."""
    if multisig is None:
        return None
    return {
        "signatures": [
            {
                "id": sig.signer_id,
                "signature": _bytes_to_signature(sig.signature),
            }
            for sig in multisig.signatures
        ]
    }


def tx_to_serde_json(tx: Transaction) -> str:
    """Convert a Python Transaction to Rust serde JSON string.

    This produces JSON in the exact format that tos_common's Transaction
    expects for serde deserialization, which can then be passed to
    tos_codec.encode_tx() for byte-identical wire encoding.
    """
    obj: dict[str, Any] = {
        "version": int(tx.version),
        "chain_id": tx.chain_id,
        "source": _bytes_to_pubkey(tx.source),
        "data": _build_data(tx),
        "fee": tx.fee,
        "fee_type": FEE_TYPE_SERDE[int(tx.fee_type)],
        "nonce": tx.nonce,
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
