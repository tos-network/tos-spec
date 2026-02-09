"""Helpers to serialize/deserialize minimal fixtures for TOS specs."""

from __future__ import annotations

from typing import Any

from tos_spec.types import (
    AccountState,
    AgentAccountMeta,
    ChainState,
    ContractState,
    DelegationEntry,
    EnergyPayload,
    EnergyResource,
    FeeType,
    FreezeRecord,
    FreezeDuration,
    PendingUnfreeze,
    TnsRecord,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _hex_to_bytes(v: str) -> bytes:
    return bytes.fromhex(v)


def _bytes_to_hex(v: bytes) -> str:
    return v.hex()


def state_to_json(state: ChainState) -> dict[str, Any]:
    # Conformance daemon derives exported account `frozen/energy` from EnergyResource when present,
    # and computes `global_state.total_energy` as the sum of account energy. Normalize here so
    # fixtures line up with daemon export/digest behavior.
    er_by_addr = state.energy_resources
    accounts_out: list[dict[str, Any]] = []
    total_energy = 0
    for a in state.accounts.values():
        frozen = a.frozen
        energy = a.energy
        er = er_by_addr.get(a.address)
        if er is not None:
            frozen = er.frozen_tos
            energy = er.energy
        total_energy += int(energy)
        accounts_out.append(
            {
                "address": _bytes_to_hex(a.address),
                "balance": a.balance,
                "nonce": a.nonce,
                "frozen": frozen,
                "energy": energy,
                "flags": a.flags,
                "data": _bytes_to_hex(a.data),
            }
        )

    result: dict[str, Any] = {
        "network_chain_id": state.network_chain_id,
        "global_state": {
            "total_supply": state.global_state.total_supply,
            "total_burned": state.global_state.total_burned,
            "total_energy": total_energy,
            "block_height": state.global_state.block_height,
            "timestamp": state.global_state.timestamp,
        },
        "accounts": accounts_out,
    }

    if state.agent_accounts:
        result["agent_accounts"] = [
            {
                "address": _bytes_to_hex(addr),
                "owner": _bytes_to_hex(a.owner),
                "controller": _bytes_to_hex(a.controller),
                "policy_hash": _bytes_to_hex(a.policy_hash),
                "status": a.status,
            }
            for addr, a in state.agent_accounts.items()
        ]

    if state.tns_names:
        result["tns_names"] = [
            {
                "name": r.name,
                "owner": _bytes_to_hex(r.owner),
            }
            for r in state.tns_names.values()
        ]

    if state.energy_resources:
        result["energy_resources"] = []
        for addr, er in state.energy_resources.items():
            entry: dict[str, Any] = {
                "address": _bytes_to_hex(addr),
                "energy": er.energy,
                "frozen_tos": er.frozen_tos,
            }
            if er.freeze_records:
                entry["freeze_records"] = [
                    {
                        "amount": fr.amount,
                        "energy_gained": fr.energy_gained,
                        "freeze_height": fr.freeze_height,
                        "unlock_height": fr.unlock_height,
                    }
                    for fr in er.freeze_records
                ]
            if er.pending_unfreezes:
                entry["pending_unfreezes"] = [
                    {
                        "amount": pu.amount,
                        "expire_height": pu.expire_height,
                    }
                    for pu in er.pending_unfreezes
                ]
            result["energy_resources"].append(entry)

    if state.contracts:
        result["contracts"] = [
            {
                "hash": _bytes_to_hex(h),
                "module": _bytes_to_hex(c.module),
            }
            for h, c in state.contracts.items()
        ]

    return result


def state_from_json(data: dict[str, Any]) -> ChainState:
    state = ChainState(network_chain_id=data["network_chain_id"])
    gs = data.get("global_state", {})
    state.global_state.total_supply = gs.get("total_supply", 0)
    state.global_state.total_burned = gs.get("total_burned", 0)
    state.global_state.total_energy = gs.get("total_energy", 0)
    state.global_state.block_height = gs.get("block_height", 0)
    state.global_state.timestamp = gs.get("timestamp", 0)

    for a in data.get("accounts", []):
        acct = AccountState(
            address=_hex_to_bytes(a["address"]),
            balance=a.get("balance", 0),
            nonce=a.get("nonce", 0),
            frozen=a.get("frozen", 0),
            energy=a.get("energy", 0),
            flags=a.get("flags", 0),
            data=_hex_to_bytes(a.get("data", "")) if a.get("data") else b"",
        )
        state.accounts[acct.address] = acct

    for a in data.get("agent_accounts", []):
        addr = _hex_to_bytes(a["address"])
        meta = AgentAccountMeta(
            owner=_hex_to_bytes(a["owner"]),
            controller=_hex_to_bytes(a["controller"]),
            policy_hash=_hex_to_bytes(a.get("policy_hash", "00" * 32)),
            status=a.get("status", 0),
        )
        state.agent_accounts[addr] = meta

    for t in data.get("tns_names", []):
        rec = TnsRecord(name=t["name"], owner=_hex_to_bytes(t["owner"]))
        state.tns_names[rec.name] = rec

    for er in data.get("energy_resources", []):
        addr = _hex_to_bytes(er["address"])
        freeze_records = [
            FreezeRecord(
                amount=fr.get("amount", 0),
                energy_gained=fr.get("energy_gained", 0),
                freeze_height=fr.get("freeze_height", 0),
                unlock_height=fr.get("unlock_height", 0),
            )
            for fr in er.get("freeze_records", [])
        ]
        pending_unfreezes = [
            PendingUnfreeze(
                amount=pu.get("amount", 0),
                expire_height=pu.get("expire_height", 0),
            )
            for pu in er.get("pending_unfreezes", [])
        ]
        resource = EnergyResource(
            frozen_tos=er.get("frozen_tos", 0),
            energy=er.get("energy", 0),
            freeze_records=freeze_records,
            pending_unfreezes=pending_unfreezes,
        )
        state.energy_resources[addr] = resource

    for c in data.get("contracts", []):
        h = _hex_to_bytes(c["hash"])
        module_bytes = _hex_to_bytes(c["module"])
        state.contracts[h] = ContractState(
            deployer=b"",
            module_hash=h,
            module=module_bytes,
        )

    return state


def _payload_to_json(payload: Any) -> Any:
    """Recursively convert a payload value, turning bytes into hex strings."""
    if payload is None:
        return None
    if isinstance(payload, (bytes, bytearray)):
        return _bytes_to_hex(bytes(payload))
    if isinstance(payload, dict):
        return {k: _payload_to_json(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [_payload_to_json(item) for item in payload]
    return payload


def tx_to_json(tx: Transaction) -> dict[str, Any]:
    payload: Any
    if tx.tx_type == TransactionType.TRANSFERS:
        payload = [
            {
                "asset": _bytes_to_hex(p.asset),
                "destination": _bytes_to_hex(p.destination),
                "amount": p.amount,
                "extra_data": _bytes_to_hex(p.extra_data) if p.extra_data else None,
            }
            for p in tx.payload
        ]
    elif tx.tx_type == TransactionType.BURN:
        payload = tx.payload
        if isinstance(payload, dict):
            payload = dict(payload)
            asset = payload.get("asset")
            if isinstance(asset, (bytes, bytearray)):
                payload["asset"] = _bytes_to_hex(bytes(asset))
    elif tx.tx_type == TransactionType.ENERGY:
        if tx.payload is None:
            payload = None
        else:
            payload = {
                "variant": tx.payload.variant,
                "amount": tx.payload.amount,
                "duration_days": tx.payload.duration.days if tx.payload.duration else None,
                "delegatees": [
                    {"delegatee": _bytes_to_hex(d.delegatee), "amount": d.amount}
                    for d in (tx.payload.delegatees or [])
                ],
                "from_delegation": tx.payload.from_delegation,
                "record_index": tx.payload.record_index,
                "delegatee_address": _bytes_to_hex(tx.payload.delegatee_address)
                if tx.payload.delegatee_address
                else None,
            }
    else:
        payload = _payload_to_json(tx.payload)

    result: dict[str, Any] = {
        "version": int(tx.version),
        "chain_id": tx.chain_id,
        "source": _bytes_to_hex(tx.source),
        "tx_type": tx.tx_type.value,
        "payload": payload,
        "fee": tx.fee,
        "fee_type": int(tx.fee_type),
        "nonce": tx.nonce,
    }
    if tx.source_commitments:
        result["source_commitments"] = [_bytes_to_hex(sc) for sc in tx.source_commitments]
    if tx.range_proof is not None:
        result["range_proof"] = _bytes_to_hex(tx.range_proof)
    result["reference_hash"] = _bytes_to_hex(tx.reference_hash) if tx.reference_hash else None
    result["reference_topoheight"] = tx.reference_topoheight
    result["signature"] = _bytes_to_hex(tx.signature) if tx.signature else None
    return result


_BYTES_FIELDS: set[str] = {
    "source", "destination", "provider", "controller", "new_controller",
    "referrer", "delegatee", "buyer", "seller", "arbiter", "issuer",
    "subject", "target", "from_user", "from_issuer", "to_issuer",
    "arbiter_pubkey", "member_pubkey", "juror_pubkey", "proposer",
    "account", "public_key", "energy_pool",
    "asset", "contract", "escrow_id", "dispute_id", "request_id",
    "committee_id", "source_committee_id", "dest_committee_id",
    "original_committee_id", "parent_committee_id", "parent_id",
    "reason_hash", "data_hash", "new_data_hash", "documents_hash",
    "policy_hash", "session_key_root", "evidence_hash", "new_evidence_hash",
    "completion_proof", "arbitration_open_hash", "vote_request_hash",
    "selection_commitment_id", "vote_hash", "sender_name_hash",
    "recipient_name_hash",
    "signature", "opener_signature", "coordinator_signature", "juror_signature",
    "extra_data", "module", "metadata", "encrypted_content", "receiver_handle",
    "commitment", "sender_handle", "proof", "ct_validity_proof",
    "arbitration_open_payload", "vote_request_payload",
    "selection_commitment_payload", "vote_payload",
}


def _json_to_bytes_payload(payload: Any) -> Any:
    """Recursively convert hex string fields to bytes in a JSON payload."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        result: dict[str, Any] = {}
        for key, value in payload.items():
            if key in _BYTES_FIELDS and isinstance(value, str) and value:
                result[key] = _hex_to_bytes(value)
            elif isinstance(value, (dict, list)):
                result[key] = _json_to_bytes_payload(value)
            else:
                result[key] = value
        return result
    if isinstance(payload, list):
        return [_json_to_bytes_payload(item) for item in payload]
    return payload


def tx_from_json(data: dict[str, Any]) -> Transaction:
    tx_type = TransactionType(data["tx_type"])

    if tx_type == TransactionType.TRANSFERS:
        payload = [
            TransferPayload(
                asset=_hex_to_bytes(p["asset"]),
                destination=_hex_to_bytes(p["destination"]),
                amount=p["amount"],
                extra_data=_hex_to_bytes(p["extra_data"]) if p.get("extra_data") else None,
            )
            for p in data.get("payload", [])
        ]
    elif tx_type == TransactionType.BURN:
        payload = _json_to_bytes_payload(data.get("payload", 0))
    elif tx_type == TransactionType.ENERGY:
        p = data.get("payload") or {}
        delegatees = [
            DelegationEntry(
                delegatee=_hex_to_bytes(d["delegatee"]), amount=d["amount"]
            )
            for d in p.get("delegatees", [])
        ]
        duration = (
            FreezeDuration(days=p["duration_days"])
            if p.get("duration_days") is not None
            else None
        )
        payload = EnergyPayload(
            variant=p.get("variant", ""),
            amount=p.get("amount"),
            duration=duration,
            delegatees=delegatees if delegatees else None,
            from_delegation=p.get("from_delegation"),
            record_index=p.get("record_index"),
            delegatee_address=_hex_to_bytes(p["delegatee_address"])
            if p.get("delegatee_address")
            else None,
        )
    else:
        payload = _json_to_bytes_payload(data.get("payload"))

    source_commitments = [
        _hex_to_bytes(sc) for sc in data.get("source_commitments", []) or []
    ]
    range_proof_raw = data.get("range_proof")
    range_proof = _hex_to_bytes(range_proof_raw) if range_proof_raw else None

    return Transaction(
        version=TxVersion(data["version"]),
        chain_id=data["chain_id"],
        source=_hex_to_bytes(data["source"]),
        tx_type=tx_type,
        payload=payload,
        fee=data["fee"],
        fee_type=FeeType(data["fee_type"]),
        nonce=data["nonce"],
        source_commitments=source_commitments,
        range_proof=range_proof,
        reference_hash=_hex_to_bytes(data["reference_hash"]) if data.get("reference_hash") else None,
        reference_topoheight=data.get("reference_topoheight"),
        signature=_hex_to_bytes(data["signature"]) if data.get("signature") else None,
    )
