"""Wire-format encoding utilities (minimal subset)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import (
    EXTRA_DATA_LIMIT_SIZE,
    EXTRA_DATA_LIMIT_SUM_SIZE,
    MAX_DELEGATEES,
    MAX_NAME_LENGTH,
    MAX_TRANSFER_COUNT,
    MIN_NAME_LENGTH,
    MIN_SHIELD_TOS_AMOUNT,
)
from .errors import ErrorCode, SpecError
from .types import (
    DelegationEntry,
    EnergyPayload,
    FeeType,
    FreezeDuration,
    MultiSig,
    SignatureId,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


TX_TYPE_IDS = {
    TransactionType.BURN: 0,
    TransactionType.TRANSFERS: 1,
    TransactionType.MULTISIG: 2,
    TransactionType.INVOKE_CONTRACT: 3,
    TransactionType.DEPLOY_CONTRACT: 4,
    TransactionType.ENERGY: 5,
    TransactionType.UNO_TRANSFERS: 18,
    TransactionType.SHIELD_TRANSFERS: 19,
    TransactionType.UNSHIELD_TRANSFERS: 20,
    TransactionType.REGISTER_NAME: 21,
    TransactionType.AGENT_ACCOUNT: 23,
}


@dataclass
class Writer:
    buf: bytearray

    def write_u8(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(1, "big", signed=False))

    def write_u16(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(2, "big", signed=False))

    def write_u32(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(4, "big", signed=False))

    def write_u64(self, v: int) -> None:
        self.buf.extend(int(v).to_bytes(8, "big", signed=False))

    def write_bytes(self, b: bytes) -> None:
        self.buf.extend(b)

    def write_bool(self, v: bool) -> None:
        self.write_u8(1 if v else 0)


def _expect_len(name: str, value: bytes, size: int) -> None:
    if len(value) != size:
        raise SpecError(ErrorCode.INVALID_FORMAT, f"{name} must be {size} bytes")


def _is_zero_hash(value: bytes) -> bool:
    return bytes(value) == b"\x00" * 32


def _kyc_level_to_tier(level: int) -> int:
    mapping = {
        0: 0,
        7: 1,
        31: 2,
        63: 3,
        255: 4,
        2047: 5,
        8191: 6,
        16383: 7,
        32767: 8,
    }
    return mapping.get(level, 0)


def _check_approval_uniqueness(approvals: list, label: str) -> None:
    seen = set()
    for ap in approvals:
        key = ap.get("member_pubkey")
        if not isinstance(key, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, f"{label} member_pubkey must be bytes")
        if bytes(key) in seen:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, f"duplicate {label} member_pubkey")
        seen.add(bytes(key))


def _check_member_uniqueness(members: list) -> None:
    seen = set()
    for member in members:
        key = member.get("public_key")
        if not isinstance(key, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member public_key must be bytes")
        if bytes(key) in seen:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "duplicate member public_key")
        seen.add(bytes(key))


def _check_approvals_time(approvals: list, current_time: int) -> None:
    max_future = current_time + APPROVAL_FUTURE_TOLERANCE_SECONDS
    min_valid = max(0, current_time - APPROVAL_EXPIRY_SECONDS)
    for ap in approvals:
        ts = int(ap.get("timestamp", 0))
        if ts > max_future:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approval timestamp too far in future")
        if ts < min_valid:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approval expired")


def _check_member_role(role: int) -> None:
    if role not in (0, 1, 2, 3):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid member role")


def _check_member_status(status: int) -> None:
    if status not in (0, 1, 2):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid member status")


def _write_hash(w: Writer, value: bytes) -> None:
    _expect_len("hash", value, 32)
    w.write_bytes(value)


def _write_pubkey(w: Writer, value: bytes) -> None:
    _expect_len("public_key", value, 32)
    w.write_bytes(value)


def _write_signature(w: Writer, value: bytes) -> None:
    _expect_len("signature", value, 64)
    w.write_bytes(value)


def _write_fixed_bytes(w: Writer, name: str, value: bytes, size: int) -> None:
    if not isinstance(value, (bytes, bytearray)):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, f"{name} must be bytes")
    _expect_len(name, bytes(value), size)
    w.write_bytes(bytes(value))


def _write_string_u8(w: Writer, value: str) -> None:
    data = value.encode()
    if len(data) > 255:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "string too long")
    w.write_u8(len(data))
    w.write_bytes(data)


def _write_string_u16(w: Writer, value: str) -> None:
    data = value.encode()
    if len(data) > 0xFFFF:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "string too long")
    w.write_u16(len(data))
    w.write_bytes(data)


def _write_optional_vec_u8(w: Writer, value: Optional[bytes]) -> None:
    if value is None:
        w.write_bool(False)
        return
    w.write_bool(True)
    w.write_u16(len(value))
    w.write_bytes(value)


def _write_multisig(w: Writer, multisig: Optional[MultiSig]) -> None:
    if multisig is None:
        w.write_bool(False)
        return
    w.write_bool(True)
    if len(multisig.signatures) > 0xFF:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "multisig signature count too large")
    signer_ids = [sig.signer_id for sig in multisig.signatures]
    if len(set(signer_ids)) != len(signer_ids):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "duplicate multisig signer_id")
    w.write_u8(len(multisig.signatures))
    for sig in multisig.signatures:
        if not (0 <= sig.signer_id <= 0xFF):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "signer_id must fit u8")
        if len(sig.signature) != 64:
            raise SpecError(ErrorCode.INVALID_FORMAT, "multisig signature must be 64 bytes")
        w.write_u8(sig.signer_id)
        w.write_bytes(sig.signature)


def _write_vec_u16(w: Writer, items: list, write_item) -> None:
    if len(items) > 0xFFFF:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "vector too large")
    w.write_u16(len(items))
    for item in items:
        write_item(w, item)


def _write_vec_u8(w: Writer, items: list, write_item) -> None:
    if len(items) > 0xFF:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "vector too large")
    w.write_u8(len(items))
    for item in items:
        write_item(w, item)


def _write_optional(w: Writer, value, write_item) -> None:
    if value is None:
        w.write_bool(False)
        return
    w.write_bool(True)
    write_item(w, value)


def _write_module(w: Writer, module: bytes) -> None:
    if not isinstance(module, (bytes, bytearray)):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "module must be bytes")
    if len(module) > 10 * 1024 * 1024:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "module too large")
    if len(module) < 4 or bytes(module[:4]) != b"\x7FELF":
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "module must be ELF bytecode")
    w.write_u32(len(module))
    w.write_bytes(bytes(module))


def _write_value_cell(w: Writer, cell) -> None:
    # cell is dict with kind or tuple form
    if isinstance(cell, dict):
        kind = cell.get("kind")
        value = cell.get("value")
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "value cell must be dict")

    if kind == "default":
        w.write_u8(0)
        _write_primitive(w, value)
    elif kind == "bytes":
        w.write_u8(1)
        if not isinstance(value, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "bytes cell value must be bytes")
        w.write_u32(len(value))
        w.write_bytes(bytes(value))
    elif kind == "object":
        w.write_u8(2)
        if not isinstance(value, list):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "object cell value must be list")
        w.write_u32(len(value))
        for v in value:
            _write_value_cell(w, v)
    elif kind == "map":
        w.write_u8(3)
        if not isinstance(value, list):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "map cell value must be list of pairs")
        w.write_u32(len(value))
        for k, v in value:
            _write_value_cell(w, k)
            _write_value_cell(w, v)
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown value cell kind")


def _primitive_type(value) -> str:
    if not isinstance(value, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "primitive must be dict")
    prim_type = value.get("type")
    if not isinstance(prim_type, str):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "primitive type must be string")
    return prim_type


def _write_primitive(w: Writer, value) -> None:
    if value is None:
        w.write_u8(0)
        return
    if isinstance(value, dict):
        prim_type = value.get("type")
        prim_value = value.get("value")
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "primitive must be dict")

    if prim_type == "u8":
        w.write_u8(1)
        w.write_u8(int(prim_value))
    elif prim_type == "u16":
        w.write_u8(2)
        w.write_u16(int(prim_value))
    elif prim_type == "u32":
        w.write_u8(3)
        w.write_u32(int(prim_value))
    elif prim_type == "u64":
        w.write_u8(4)
        w.write_u64(int(prim_value))
    elif prim_type == "u128":
        w.write_u8(5)
        w.write_u128(int(prim_value))
    elif prim_type == "u256":
        w.write_u8(6)
        if not isinstance(prim_value, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "u256 must be 32-byte bytes")
        _expect_len("u256", bytes(prim_value), 32)
        w.write_bytes(bytes(prim_value))
    elif prim_type == "bool":
        w.write_u8(7)
        w.write_bool(bool(prim_value))
    elif prim_type == "string":
        w.write_u8(8)
        _write_string_u16(w, str(prim_value))
    elif prim_type == "range":
        w.write_u8(9)
        left, right = prim_value
        left_type = _primitive_type(left)
        right_type = _primitive_type(right)
        if left_type not in {"u8", "u16", "u32", "u64", "u128", "u256"}:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "range requires numeric primitives")
        if right_type not in {"u8", "u16", "u32", "u64", "u128", "u256"}:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "range requires numeric primitives")
        if left_type != right_type:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "range primitive types must match")
        _write_primitive(w, left)
        _write_primitive(w, right)
    elif prim_type == "opaque":
        w.write_u8(10)
        if not isinstance(prim_value, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "opaque must be bytes")
        if len(prim_value) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "opaque bytes must be non-empty")
        w.write_bytes(bytes(prim_value))
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown primitive type")


def _encode_transfers(w: Writer, transfers: list[TransferPayload]) -> None:
    if not transfers or len(transfers) > MAX_TRANSFER_COUNT:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid transfer count")

    extra_sum = 0
    w.write_u16(len(transfers))
    for t in transfers:
        if t.extra_data is not None and len(t.extra_data) > EXTRA_DATA_LIMIT_SIZE:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
        if t.extra_data is not None:
            # Option<bool> + Vec<u8> (u16 len + bytes)
            extra_sum += 3 + len(t.extra_data)
            if extra_sum > EXTRA_DATA_LIMIT_SUM_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data sum too large")
        w.write_bytes(t.asset)
        w.write_bytes(t.destination)
        w.write_u64(t.amount)
        _write_optional_vec_u8(w, t.extra_data)

def _encode_freeze_duration(w: Writer, duration: FreezeDuration) -> None:
    w.write_u32(duration.days)


def _encode_energy(w: Writer, payload: EnergyPayload) -> None:
    if payload.variant == "freeze_tos":
        if payload.amount is None or payload.duration is None:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "freeze_tos missing fields")
        w.write_u8(0)
        w.write_u64(payload.amount)
        _encode_freeze_duration(w, payload.duration)
        return

    if payload.variant == "freeze_tos_delegate":
        if payload.delegatees is None or payload.duration is None:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "freeze_tos_delegate missing fields")
        if len(payload.delegatees) > MAX_DELEGATEES:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many delegatees")
        w.write_u8(1)
        w.write_u64(len(payload.delegatees))
        for entry in payload.delegatees:
            if not isinstance(entry, DelegationEntry):
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid delegation entry")
            w.write_bytes(entry.delegatee)
            w.write_u64(entry.amount)
        _encode_freeze_duration(w, payload.duration)
        return

    if payload.variant == "unfreeze_tos":
        if payload.amount is None or payload.from_delegation is None:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "unfreeze_tos missing fields")
        w.write_u8(2)
        w.write_u64(payload.amount)
        w.write_bool(payload.from_delegation)
        if payload.record_index is None:
            w.write_u8(0)
        else:
            w.write_u8(1)
            w.write_u32(payload.record_index)
        if payload.delegatee_address is None:
            w.write_u8(0)
        else:
            w.write_u8(1)
            w.write_bytes(payload.delegatee_address)
        return

    if payload.variant == "withdraw_unfrozen":
        w.write_u8(3)
        return

    raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown energy payload variant")


def encode_signing_bytes(tx: Transaction, current_time: Optional[int] = None) -> bytes:
    """Encode the unsigned portion of a transaction for signing.

    Matches Rust UnsignedTransaction::finalize() field order:
    [version:1][chain_id:1][source:32][tx_type_id+payload:var][fee:8][fee_type:1][nonce:8][ref_hash:32][ref_topo:8]
    """
    if tx.version != TxVersion.T1:
        raise SpecError(ErrorCode.INVALID_VERSION, "unsupported tx version")

    if tx.tx_type not in TX_TYPE_IDS:
        raise SpecError(ErrorCode.INVALID_TYPE, "unsupported tx type")

    if tx.reference_hash is None or tx.reference_topoheight is None:
        raise SpecError(ErrorCode.INVALID_FORMAT, "missing reference")
    if len(tx.reference_hash) != 32:
        raise SpecError(ErrorCode.INVALID_FORMAT, "reference_hash must be 32 bytes")

    if len(tx.source) != 32:
        raise SpecError(ErrorCode.INVALID_FORMAT, "source must be 32 bytes")
    if not (0 <= tx.chain_id <= 0xFF):
        raise SpecError(ErrorCode.INVALID_FORMAT, "chain_id must fit u8")

    w = Writer(bytearray())
    w.write_u8(tx.version)
    w.write_u8(tx.chain_id)
    w.write_bytes(tx.source)

    w.write_u8(TX_TYPE_IDS[tx.tx_type])

    _encode_payload(w, tx, current_time)

    w.write_u64(tx.fee)
    if not isinstance(tx.fee_type, FeeType):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "fee_type invalid")
    w.write_u8(tx.fee_type)
    w.write_u64(tx.nonce)

    w.write_bytes(tx.reference_hash)
    w.write_u64(tx.reference_topoheight)

    return bytes(w.buf)


def encode_transaction(tx: Transaction, current_time: Optional[int] = None) -> bytes:
    """Encode a transaction in wire format for supported types.

    Minimal subset for specs: Transfers and Burn.
    """
    if tx.version != TxVersion.T1:
        raise SpecError(ErrorCode.INVALID_VERSION, "unsupported tx version")

    if tx.tx_type not in TX_TYPE_IDS:
        raise SpecError(ErrorCode.INVALID_TYPE, "unsupported tx type")

    if tx.signature is None:
        raise SpecError(ErrorCode.INVALID_FORMAT, "missing signature")
    if len(tx.signature) != 64:
        raise SpecError(ErrorCode.INVALID_FORMAT, "signature must be 64 bytes")

    if tx.reference_hash is None or tx.reference_topoheight is None:
        raise SpecError(ErrorCode.INVALID_FORMAT, "missing reference")
    if len(tx.reference_hash) != 32:
        raise SpecError(ErrorCode.INVALID_FORMAT, "reference_hash must be 32 bytes")

    if len(tx.source) != 32:
        raise SpecError(ErrorCode.INVALID_FORMAT, "source must be 32 bytes")
    if not (0 <= tx.chain_id <= 0xFF):
        raise SpecError(ErrorCode.INVALID_FORMAT, "chain_id must fit u8")

    w = Writer(bytearray())
    w.write_u8(tx.version)
    w.write_u8(tx.chain_id)
    w.write_bytes(tx.source)

    w.write_u8(TX_TYPE_IDS[tx.tx_type])

    _encode_payload(w, tx, current_time)

    w.write_u64(tx.fee)
    if not isinstance(tx.fee_type, FeeType):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "fee_type invalid")
    w.write_u8(tx.fee_type)
    w.write_u64(tx.nonce)

    # UNO fields (only for Uno/Shield/Unshield)
    if tx.tx_type in (
        TransactionType.UNO_TRANSFERS,
        TransactionType.SHIELD_TRANSFERS,
        TransactionType.UNSHIELD_TRANSFERS,
    ):
        if len(tx.source_commitments) > 0xFF:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "source_commitments too large")
        w.write_u8(len(tx.source_commitments))
        for sc in tx.source_commitments:
            _expect_len("source_commitment", sc, 32)
            w.write_bytes(sc)
        if tx.tx_type == TransactionType.UNO_TRANSFERS:
            if tx.range_proof is None:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "range_proof required")
            w.write_bytes(tx.range_proof)
        elif tx.tx_type == TransactionType.UNSHIELD_TRANSFERS and tx.range_proof is not None:
            w.write_bytes(tx.range_proof)
    # Reference
    w.write_bytes(tx.reference_hash)
    w.write_u64(tx.reference_topoheight)

    # Multisig (Option<MultiSig>)
    _write_multisig(w, tx.multisig)

    # Signature
    w.write_bytes(tx.signature)

    return bytes(w.buf)


def _encode_payload(w: Writer, tx: Transaction, current_time: Optional[int]) -> None:
    payload = tx.payload

    if tx.tx_type == TransactionType.TRANSFERS:
        if not isinstance(payload, list):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "payload must be list")
        _encode_transfers(w, payload)
        return

    if tx.tx_type == TransactionType.BURN:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "burn payload must be dict")
        _write_hash(w, payload["asset"])
        w.write_u64(int(payload["amount"]))
        return

    if tx.tx_type == TransactionType.ENERGY:
        if not isinstance(payload, EnergyPayload):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "payload must be EnergyPayload")
        _encode_energy(w, payload)
        return

    if tx.tx_type == TransactionType.MULTISIG:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "multisig payload must be dict")
        threshold = int(payload["threshold"])
        w.write_u8(threshold)
        if threshold != 0:
            participants = payload.get("participants", [])
            _write_vec_u8(w, participants, lambda ww, p: _write_pubkey(ww, p))
        return

    if tx.tx_type == TransactionType.INVOKE_CONTRACT:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invoke_contract payload must be dict")
        _write_hash(w, payload["contract"])
        _write_contract_deposits(w, payload.get("deposits", []))
        w.write_u16(int(payload["entry_id"]))
        w.write_u64(int(payload["max_gas"]))
        params = payload.get("parameters", [])
        _write_vec_u8(w, params, _write_value_cell)
        return

    if tx.tx_type == TransactionType.DEPLOY_CONTRACT:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "deploy_contract payload must be dict")
        _write_module(w, payload["module"])
        invoke = payload.get("invoke")
        _write_optional(w, invoke, _write_invoke_constructor)
        return

    if tx.tx_type == TransactionType.AGENT_ACCOUNT:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "agent_account payload must be dict")
        _encode_agent_account(w, payload)
        return

    if tx.tx_type == TransactionType.REGISTER_NAME:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "register_name payload must be dict")
        name = payload["name"]
        if not isinstance(name, str):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "name must be string")
        if not (MIN_NAME_LENGTH <= len(name) <= MAX_NAME_LENGTH):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid name length")
        _write_string_u8(w, name)
        return

    if tx.tx_type in (
        TransactionType.UNO_TRANSFERS,
        TransactionType.SHIELD_TRANSFERS,
        TransactionType.UNSHIELD_TRANSFERS,
    ):
        _encode_privacy_payload(w, tx.tx_type, payload, tx.version)
        return

    raise SpecError(ErrorCode.NOT_IMPLEMENTED, "payload encoding not implemented")


def _write_contract_deposits(w: Writer, deposits: list) -> None:
    # Canonicalize to unique assets (matches Rust wire encoding, which uses IndexMap<Hash, ...>).
    # Duplicate assets are collapsed with "last value wins", while preserving first-seen order.
    #
    # This matters for signing-bytes and wire hex generation: if we encode duplicates as-is,
    # the daemon will decode into a map (dropping duplicates) and signature verification
    # will disagree.
    if not isinstance(deposits, list):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "deposits must be list")

    dedup: dict[bytes, int] = {}
    for dep in deposits:
        if not isinstance(dep, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "deposit must be dict")
        asset = dep.get("asset", b"")
        if isinstance(asset, (list, tuple)):
            asset = bytes(asset)
        if not isinstance(asset, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "deposit asset must be bytes")
        amount = int(dep.get("amount", 0))
        dedup[bytes(asset)] = amount

    if len(dedup) > 0xFF:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many deposits")

    w.write_u8(len(dedup))
    for asset, amount in dedup.items():
        _write_hash(w, asset)
        w.write_u8(0)  # type tag: public
        w.write_u64(amount)


def _write_invoke_constructor(w: Writer, invoke: dict) -> None:
    w.write_u64(int(invoke["max_gas"]))
    _write_contract_deposits(w, invoke.get("deposits", []))


def _encode_agent_account(w: Writer, payload: dict) -> None:
    variant = payload["variant"]
    if variant == "register":
        w.write_u8(0)
        _write_pubkey(w, payload["controller"])
        _write_hash(w, payload["policy_hash"])
        _write_optional(w, payload.get("energy_pool"), _write_pubkey)
        _write_optional(w, payload.get("session_key_root"), _write_hash)
    elif variant == "update_policy":
        w.write_u8(1)
        _write_hash(w, payload["policy_hash"])
    elif variant == "rotate_controller":
        w.write_u8(2)
        _write_pubkey(w, payload["new_controller"])
    elif variant == "set_status":
        w.write_u8(3)
        w.write_u8(int(payload["status"]))
    elif variant == "set_energy_pool":
        w.write_u8(4)
        _write_optional(w, payload.get("energy_pool"), _write_pubkey)
    elif variant == "set_session_key_root":
        w.write_u8(5)
        _write_optional(w, payload.get("session_key_root"), _write_hash)
    elif variant == "add_session_key":
        w.write_u8(6)
        _write_session_key(w, payload["key"])
    elif variant == "revoke_session_key":
        w.write_u8(7)
        w.write_u64(int(payload["key_id"]))
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown agent_account variant")


def _write_session_key(w: Writer, key: dict) -> None:
    w.write_u64(int(key["key_id"]))
    _write_pubkey(w, key["public_key"])
    w.write_u64(int(key["expiry_topoheight"]))
    w.write_u64(int(key["max_value_per_window"]))
    _write_vec_u16(w, key.get("allowed_targets", []), _write_pubkey)
    _write_vec_u16(w, key.get("allowed_assets", []), _write_hash)


def _encode_privacy_payload(
    w: Writer, tx_type: TransactionType, payload: dict, version: TxVersion
) -> None:
    if not isinstance(payload, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "privacy payload must be dict")

    transfers = payload.get("transfers", [])
    extra_sum = 0
    for t in transfers:
        extra_data = t.get("extra_data") if isinstance(t, dict) else None
        if extra_data is not None:
            if not isinstance(extra_data, (bytes, bytearray)):
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data must be bytes")
            if len(extra_data) > EXTRA_DATA_LIMIT_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data too large")
            extra_sum += 3 + len(extra_data)
            if extra_sum > EXTRA_DATA_LIMIT_SUM_SIZE:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "extra_data sum too large")
    if tx_type == TransactionType.UNO_TRANSFERS:
        _write_vec_u16(w, transfers, lambda ww, t: _write_uno_transfer(ww, t, version))
    elif tx_type == TransactionType.SHIELD_TRANSFERS:
        _write_vec_u16(w, transfers, _write_shield_transfer)
    elif tx_type == TransactionType.UNSHIELD_TRANSFERS:
        _write_vec_u16(w, transfers, lambda ww, t: _write_unshield_transfer(ww, t, version))
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown privacy tx type")


def _ct_validity_proof_size(version: TxVersion) -> int:
    if version >= TxVersion.T1:
        return 160
    return 128


def _write_uno_transfer(w: Writer, transfer: dict, version: TxVersion) -> None:
    _write_hash(w, transfer["asset"])
    _write_pubkey(w, transfer["destination"])
    _write_optional_vec_u8(w, transfer.get("extra_data"))
    _write_fixed_bytes(w, "commitment", transfer["commitment"], 32)
    _write_fixed_bytes(w, "sender_handle", transfer["sender_handle"], 32)
    _write_fixed_bytes(w, "receiver_handle", transfer["receiver_handle"], 32)
    _write_fixed_bytes(
        w, "ct_validity_proof", transfer["ct_validity_proof"], _ct_validity_proof_size(version)
    )


def _write_shield_transfer(w: Writer, transfer: dict) -> None:
    _write_hash(w, transfer["asset"])
    _write_pubkey(w, transfer["destination"])
    w.write_u64(int(transfer["amount"]))
    _write_optional_vec_u8(w, transfer.get("extra_data"))
    _write_fixed_bytes(w, "commitment", transfer["commitment"], 32)
    _write_fixed_bytes(w, "receiver_handle", transfer["receiver_handle"], 32)
    _write_fixed_bytes(w, "proof", transfer["proof"], 96)


def _write_unshield_transfer(w: Writer, transfer: dict, version: TxVersion) -> None:
    _write_hash(w, transfer["asset"])
    _write_pubkey(w, transfer["destination"])
    w.write_u64(int(transfer["amount"]))
    _write_optional_vec_u8(w, transfer.get("extra_data"))
    _write_fixed_bytes(w, "commitment", transfer["commitment"], 32)
    _write_fixed_bytes(w, "sender_handle", transfer["sender_handle"], 32)
    _write_fixed_bytes(
        w, "ct_validity_proof", transfer["ct_validity_proof"], _ct_validity_proof_size(version)
    )
