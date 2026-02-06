"""Helpers to serialize/deserialize minimal fixtures for TOS specs."""

from __future__ import annotations

from typing import Any

from tos_spec.types import (
    AccountState,
    AgentAccountMeta,
    ArbitrationConfig,
    ArbiterAccount,
    ArbiterStatus,
    ChainState,
    Committee,
    CommitteeMember,
    DelegationEntry,
    DisputeInfo,
    EnergyPayload,
    EnergyResource,
    EscrowAccount,
    EscrowStatus,
    FeeType,
    FreezeRecord,
    FreezeDuration,
    PendingUnfreeze,
    KycData,
    KycStatus,
    ReferralBinding,
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


def _escrow_to_json(e: EscrowAccount) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": _bytes_to_hex(e.id),
        "task_id": e.task_id,
        "payer": _bytes_to_hex(e.payer),
        "payee": _bytes_to_hex(e.payee),
        "amount": e.amount,
        "total_amount": e.total_amount,
        "released_amount": e.released_amount,
        "refunded_amount": e.refunded_amount,
        "challenge_deposit": e.challenge_deposit,
        "asset": _bytes_to_hex(e.asset),
        "state": e.status.value,
        "timeout_blocks": e.timeout_blocks,
        "challenge_window": e.challenge_window,
        "challenge_deposit_bps": e.challenge_deposit_bps,
        "optimistic_release": e.optimistic_release,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
        "timeout_at": e.timeout_at,
    }
    if e.arbitration_config is not None:
        ac = e.arbitration_config
        d["arbitration_config"] = {
            "mode": ac.mode,
            "arbiters": [_bytes_to_hex(a) for a in ac.arbiters],
            "threshold": ac.threshold,
            "fee_amount": ac.fee_amount,
            "allow_appeal": ac.allow_appeal,
        }
    if e.release_requested_at is not None:
        d["release_requested_at"] = e.release_requested_at
    if e.pending_release_amount is not None:
        d["pending_release_amount"] = e.pending_release_amount
    if e.dispute is not None:
        dd: dict[str, Any] = {
            "initiator": _bytes_to_hex(e.dispute.initiator),
            "reason": e.dispute.reason,
            "disputed_at": e.dispute.disputed_at,
            "deadline": e.dispute.deadline,
        }
        if e.dispute.evidence_hash is not None:
            dd["evidence_hash"] = _bytes_to_hex(e.dispute.evidence_hash)
        d["dispute"] = dd
    if e.dispute_id is not None:
        d["dispute_id"] = _bytes_to_hex(e.dispute_id)
    if e.dispute_round is not None:
        d["dispute_round"] = e.dispute_round
    return d


def state_to_json(state: ChainState) -> dict[str, Any]:
    result: dict[str, Any] = {
        "network_chain_id": state.network_chain_id,
        "global_state": {
            "total_supply": state.global_state.total_supply,
            "total_burned": state.global_state.total_burned,
            "total_energy": state.global_state.total_energy,
            "block_height": state.global_state.block_height,
            "timestamp": state.global_state.timestamp,
        },
        "accounts": [
            {
                "address": _bytes_to_hex(a.address),
                "balance": a.balance,
                "nonce": a.nonce,
                "frozen": a.frozen,
                "energy": a.energy,
                "flags": a.flags,
                "data": _bytes_to_hex(a.data),
            }
            for a in state.accounts.values()
        ],
    }

    if state.escrows:
        result["escrows"] = [_escrow_to_json(e) for e in state.escrows.values()]

    if state.arbiters:
        result["arbiters"] = [
            {
                "public_key": _bytes_to_hex(a.public_key),
                "name": a.name,
                "status": a.status.value,
                "expertise": a.expertise,
                "stake_amount": a.stake_amount,
                "fee_basis_points": a.fee_basis_points,
                "min_escrow_value": a.min_escrow_value,
                "max_escrow_value": a.max_escrow_value,
                "reputation_score": a.reputation_score,
                "total_cases": a.total_cases,
                "active_cases": a.active_cases,
                "registered_at": a.registered_at,
                "total_slashed": a.total_slashed,
            }
            for a in state.arbiters.values()
        ]

    if state.kyc_data:
        result["kyc_data"] = [
            {
                "address": _bytes_to_hex(addr),
                "level": k.level,
                "status": k.status.value,
                "verified_at": k.verified_at,
                "data_hash": _bytes_to_hex(k.data_hash),
                "committee_id": _bytes_to_hex(k.committee_id),
            }
            for addr, k in state.kyc_data.items()
        ]

    if state.committees:
        result["committees"] = []
        for c in state.committees.values():
            entry = {
                "id": _bytes_to_hex(c.id),
                "name": c.name,
                "region": c.region,
                "members": [
                    {
                        "public_key": _bytes_to_hex(m.public_key),
                        "name": m.name,
                        "role": m.role,
                    }
                    for m in c.members
                ],
                "threshold": c.threshold,
                "kyc_threshold": c.kyc_threshold,
                "max_kyc_level": c.max_kyc_level,
            }
            if c.parent_id is not None:
                entry["parent_id"] = _bytes_to_hex(c.parent_id)
            result["committees"].append(entry)

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

    if state.referrals:
        result["referrals"] = [
            {
                "user": _bytes_to_hex(user),
                "referrer": _bytes_to_hex(referrer),
            }
            for user, referrer in state.referrals.items()
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

    for e in data.get("escrows", []):
        arb_cfg = None
        if "arbitration_config" in e:
            ac = e["arbitration_config"]
            arb_cfg = ArbitrationConfig(
                mode=ac.get("mode", "single"),
                arbiters=[_hex_to_bytes(a) for a in ac.get("arbiters", [])],
                threshold=ac.get("threshold"),
                fee_amount=ac.get("fee_amount", 0),
                allow_appeal=ac.get("allow_appeal", False),
            )
        dispute = None
        if "dispute" in e:
            dd = e["dispute"]
            dispute = DisputeInfo(
                initiator=_hex_to_bytes(dd.get("initiator", "00" * 32)),
                reason=dd.get("reason", ""),
                evidence_hash=_hex_to_bytes(dd["evidence_hash"]) if dd.get("evidence_hash") else None,
                disputed_at=dd.get("disputed_at", 0),
                deadline=dd.get("deadline", 0),
            )
        escrow = EscrowAccount(
            id=_hex_to_bytes(e["id"]),
            task_id=e["task_id"],
            payer=_hex_to_bytes(e["payer"]),
            payee=_hex_to_bytes(e["payee"]),
            amount=e["amount"],
            total_amount=e["total_amount"],
            released_amount=e.get("released_amount", 0),
            refunded_amount=e.get("refunded_amount", 0),
            challenge_deposit=e.get("challenge_deposit", 0),
            asset=_hex_to_bytes(e.get("asset", "00" * 32)),
            status=EscrowStatus(e.get("state", "created")),
            timeout_blocks=e.get("timeout_blocks", 0),
            challenge_window=e.get("challenge_window", 0),
            challenge_deposit_bps=e.get("challenge_deposit_bps", 0),
            optimistic_release=e.get("optimistic_release", False),
            created_at=e.get("created_at", 0),
            updated_at=e.get("updated_at", 0),
            timeout_at=e.get("timeout_at", 0),
            arbitration_config=arb_cfg,
            release_requested_at=e.get("release_requested_at"),
            pending_release_amount=e.get("pending_release_amount"),
            dispute=dispute,
            dispute_id=_hex_to_bytes(e["dispute_id"]) if e.get("dispute_id") else None,
            dispute_round=e.get("dispute_round"),
        )
        state.escrows[escrow.id] = escrow

    for a in data.get("arbiters", []):
        arbiter = ArbiterAccount(
            public_key=_hex_to_bytes(a["public_key"]),
            name=a.get("name", ""),
            status=ArbiterStatus(a.get("status", "active")),
            expertise=a.get("expertise", []),
            stake_amount=a.get("stake_amount", 0),
            fee_basis_points=a.get("fee_basis_points", 0),
            min_escrow_value=a.get("min_escrow_value", 0),
            max_escrow_value=a.get("max_escrow_value", 0),
            reputation_score=a.get("reputation_score", 0),
            total_cases=a.get("total_cases", 0),
            active_cases=a.get("active_cases", 0),
            registered_at=a.get("registered_at", 0),
            total_slashed=a.get("total_slashed", 0),
        )
        state.arbiters[arbiter.public_key] = arbiter

    for k in data.get("kyc_data", []):
        addr = _hex_to_bytes(k["address"])
        kyc = KycData(
            level=k.get("level", 0),
            status=KycStatus(k.get("status", "active")),
            verified_at=k.get("verified_at", 0),
            data_hash=_hex_to_bytes(k.get("data_hash", "00" * 32)),
            committee_id=_hex_to_bytes(k.get("committee_id", "00" * 32)),
        )
        state.kyc_data[addr] = kyc

    for c in data.get("committees", []):
        members = [
            CommitteeMember(
                public_key=_hex_to_bytes(m["public_key"]),
                name=m.get("name", ""),
                role=m.get("role", 0),
            )
            for m in c.get("members", [])
        ]
        parent_raw = c.get("parent_id")
        parent_id = _hex_to_bytes(parent_raw) if parent_raw else None
        committee = Committee(
            id=_hex_to_bytes(c["id"]),
            name=c.get("name", ""),
            region=c.get("region", 0),
            members=members,
            threshold=c.get("threshold", 0),
            kyc_threshold=c.get("kyc_threshold", 0),
            max_kyc_level=c.get("max_kyc_level", 0),
            parent_id=parent_id,
        )
        state.committees[committee.id] = committee

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

    for r in data.get("referrals", []):
        user = _hex_to_bytes(r["user"])
        referrer = _hex_to_bytes(r["referrer"])
        state.referrals[user] = referrer

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
