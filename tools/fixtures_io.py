"""Helpers to serialize/deserialize minimal fixtures for TOS specs."""

from __future__ import annotations

from typing import Any

from tos_spec.types import (
    AccountState,
    ChainState,
    DelegationEntry,
    EnergyPayload,
    FeeType,
    FreezeDuration,
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
    return {
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
    return state


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
        payload = None

    return {
        "version": int(tx.version),
        "chain_id": tx.chain_id,
        "source": _bytes_to_hex(tx.source),
        "tx_type": tx.tx_type.value,
        "payload": payload,
        "fee": tx.fee,
        "fee_type": int(tx.fee_type),
        "nonce": tx.nonce,
        "reference_hash": _bytes_to_hex(tx.reference_hash) if tx.reference_hash else None,
        "reference_topoheight": tx.reference_topoheight,
        "signature": _bytes_to_hex(tx.signature) if tx.signature else None,
    }


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
        payload = data.get("payload", 0)
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
        payload = data.get("payload")

    return Transaction(
        version=TxVersion(data["version"]),
        chain_id=data["chain_id"],
        source=_hex_to_bytes(data["source"]),
        tx_type=tx_type,
        payload=payload,
        fee=data["fee"],
        fee_type=FeeType(data["fee_type"]),
        nonce=data["nonce"],
        reference_hash=_hex_to_bytes(data["reference_hash"]) if data.get("reference_hash") else None,
        reference_topoheight=data.get("reference_topoheight"),
        signature=_hex_to_bytes(data["signature"]) if data.get("signature") else None,
    )
