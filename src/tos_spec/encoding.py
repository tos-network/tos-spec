"""Wire-format encoding utilities (minimal subset)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import (
    EMERGENCY_SUSPEND_MIN_APPROVALS,
    EMERGENCY_SUSPEND_TIMEOUT,
    EXTRA_DATA_LIMIT_SIZE,
    EXTRA_DATA_LIMIT_SUM_SIZE,
    APPROVAL_EXPIRY_SECONDS,
    APPROVAL_FUTURE_TOLERANCE_SECONDS,
    MAX_ARBITRATION_OPEN_BYTES,
    MAX_APPROVALS,
    MAX_ARBITER_NAME_LEN,
    MAX_BPS,
    MAX_COMMITTEE_MEMBERS,
    MAX_COMMITTEE_NAME_LEN,
    MAX_DELEGATEES,
    MAX_JUROR_VOTE_BYTES,
    MAX_ENCRYPTED_SIZE,
    MAX_FEE_BPS,
    MAX_MEMBER_NAME_LEN,
    MAX_NAME_LENGTH,
    MAX_REASON_LEN,
    MAX_REFUND_REASON_LEN,
    MAX_SELECTION_COMMITMENT_BYTES,
    MAX_TASK_ID_LEN,
    MAX_TIMEOUT_BLOCKS,
    MAX_TRANSFER_COUNT,
    MAX_TTL,
    MAX_VOTE_REQUEST_BYTES,
    MIN_ARBITER_STAKE,
    MIN_COMMITTEE_MEMBERS,
    MIN_NAME_LENGTH,
    MIN_TIMEOUT_BLOCKS,
    MIN_TTL,
    VALID_KYC_LEVELS,
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
    TransactionType.BIND_REFERRER: 7,
    TransactionType.BATCH_REFERRAL_REWARD: 8,
    TransactionType.SET_KYC: 9,
    TransactionType.REVOKE_KYC: 10,
    TransactionType.RENEW_KYC: 11,
    TransactionType.BOOTSTRAP_COMMITTEE: 12,
    TransactionType.REGISTER_COMMITTEE: 13,
    TransactionType.UPDATE_COMMITTEE: 14,
    TransactionType.EMERGENCY_SUSPEND: 15,
    TransactionType.TRANSFER_KYC: 16,
    TransactionType.APPEAL_KYC: 17,
    TransactionType.UNO_TRANSFERS: 18,
    TransactionType.SHIELD_TRANSFERS: 19,
    TransactionType.UNSHIELD_TRANSFERS: 20,
    TransactionType.REGISTER_NAME: 21,
    TransactionType.EPHEMERAL_MESSAGE: 22,
    TransactionType.AGENT_ACCOUNT: 23,
    TransactionType.CREATE_ESCROW: 24,
    TransactionType.DEPOSIT_ESCROW: 25,
    TransactionType.RELEASE_ESCROW: 26,
    TransactionType.REFUND_ESCROW: 27,
    TransactionType.CHALLENGE_ESCROW: 28,
    TransactionType.SUBMIT_VERDICT: 29,
    TransactionType.DISPUTE_ESCROW: 30,
    TransactionType.APPEAL_ESCROW: 31,
    TransactionType.SUBMIT_VERDICT_BY_JUROR: 32,
    TransactionType.REGISTER_ARBITER: 33,
    TransactionType.UPDATE_ARBITER: 34,
    TransactionType.COMMIT_ARBITRATION_OPEN: 35,
    TransactionType.COMMIT_VOTE_REQUEST: 36,
    TransactionType.COMMIT_SELECTION_COMMITMENT: 37,
    TransactionType.COMMIT_JUROR_VOTE: 38,
    TransactionType.SLASH_ARBITER: 44,
    TransactionType.REQUEST_ARBITER_EXIT: 45,
    TransactionType.WITHDRAW_ARBITER_STAKE: 46,
    TransactionType.CANCEL_ARBITER_EXIT: 47,
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

    if tx.tx_type == TransactionType.BIND_REFERRER:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "bind_referrer payload must be dict")
        _write_pubkey(w, payload["referrer"])
        _write_optional_vec_u8(w, payload.get("extra_data"))
        return

    if tx.tx_type == TransactionType.BATCH_REFERRAL_REWARD:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "batch_referral_reward payload must be dict")
        _write_hash(w, payload["asset"])
        _write_pubkey(w, payload["from_user"])
        w.write_u64(int(payload["total_amount"]))
        w.write_u8(int(payload["levels"]))
        ratios = payload.get("ratios", [])
        _write_vec_u8(w, ratios, lambda ww, r: ww.write_u16(int(r)))
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

    if tx.tx_type == TransactionType.EPHEMERAL_MESSAGE:
        if not isinstance(payload, dict):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "ephemeral_message payload must be dict")
        _write_hash(w, payload["sender_name_hash"])
        _write_hash(w, payload["recipient_name_hash"])
        w.write_u64(int(payload["message_nonce"]))
        ttl_blocks = int(payload["ttl_blocks"])
        if not (MIN_TTL <= ttl_blocks <= MAX_TTL):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "ttl_blocks out of range")
        w.write_u32(ttl_blocks)
        content = payload["encrypted_content"]
        if not isinstance(content, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "encrypted_content must be bytes")
        if len(content) == 0 or len(content) > MAX_ENCRYPTED_SIZE:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "encrypted_content size invalid")
        w.write_u16(len(content))
        w.write_bytes(bytes(content))
        _expect_len("receiver_handle", payload["receiver_handle"], 32)
        w.write_bytes(payload["receiver_handle"])
        return

    if tx.tx_type in (
        TransactionType.CREATE_ESCROW,
        TransactionType.DEPOSIT_ESCROW,
        TransactionType.RELEASE_ESCROW,
        TransactionType.REFUND_ESCROW,
        TransactionType.CHALLENGE_ESCROW,
        TransactionType.DISPUTE_ESCROW,
        TransactionType.APPEAL_ESCROW,
        TransactionType.SUBMIT_VERDICT,
        TransactionType.SUBMIT_VERDICT_BY_JUROR,
    ):
        _encode_escrow_payload(w, tx.tx_type, payload)
        return

    if tx.tx_type in (
        TransactionType.REGISTER_ARBITER,
        TransactionType.UPDATE_ARBITER,
        TransactionType.COMMIT_ARBITRATION_OPEN,
        TransactionType.COMMIT_VOTE_REQUEST,
        TransactionType.COMMIT_SELECTION_COMMITMENT,
        TransactionType.COMMIT_JUROR_VOTE,
        TransactionType.SLASH_ARBITER,
        TransactionType.REQUEST_ARBITER_EXIT,
        TransactionType.WITHDRAW_ARBITER_STAKE,
        TransactionType.CANCEL_ARBITER_EXIT,
    ):
        _encode_arbitration_payload(w, tx.tx_type, payload)
        return

    if tx.tx_type in (
        TransactionType.SET_KYC,
        TransactionType.REVOKE_KYC,
        TransactionType.RENEW_KYC,
        TransactionType.TRANSFER_KYC,
        TransactionType.APPEAL_KYC,
        TransactionType.BOOTSTRAP_COMMITTEE,
        TransactionType.REGISTER_COMMITTEE,
        TransactionType.UPDATE_COMMITTEE,
        TransactionType.EMERGENCY_SUSPEND,
    ):
        _encode_kyc_payload(w, tx.tx_type, payload, current_time)
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


def _encode_escrow_payload(w: Writer, tx_type: TransactionType, payload: dict) -> None:
    if not isinstance(payload, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "escrow payload must be dict")

    if tx_type == TransactionType.CREATE_ESCROW:
        task_id = payload["task_id"]
        if not isinstance(task_id, str):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "task_id must be string")
        if task_id == "" or len(task_id) > MAX_TASK_ID_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid task_id length")
        _write_string_u8(w, task_id)
        _write_pubkey(w, payload["provider"])
        amount = int(payload["amount"])
        if amount <= 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "amount must be > 0")
        w.write_u64(amount)
        _write_hash(w, payload["asset"])
        timeout_blocks = int(payload["timeout_blocks"])
        if timeout_blocks < MIN_TIMEOUT_BLOCKS or timeout_blocks > MAX_TIMEOUT_BLOCKS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "timeout_blocks out of range")
        w.write_u64(timeout_blocks)
        challenge_window = int(payload["challenge_window"])
        if challenge_window <= 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "challenge_window must be > 0")
        w.write_u64(challenge_window)
        challenge_deposit_bps = int(payload["challenge_deposit_bps"])
        if challenge_deposit_bps < 0 or challenge_deposit_bps > MAX_BPS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "challenge_deposit_bps out of range")
        w.write_u16(challenge_deposit_bps)
        optimistic_release = bool(payload["optimistic_release"])
        w.write_bool(optimistic_release)
        arbitration_config = payload.get("arbitration_config")
        if optimistic_release and arbitration_config is None:
            raise SpecError(
                ErrorCode.INVALID_PAYLOAD,
                "optimistic_release requires arbitration_config",
            )
        _write_optional(w, arbitration_config, _write_arbitration_config)
        _write_optional_vec_u8(w, payload.get("metadata"))
        return

    if tx_type == TransactionType.DEPOSIT_ESCROW:
        _write_hash(w, payload["escrow_id"])
        w.write_u64(int(payload["amount"]))
        return

    if tx_type == TransactionType.RELEASE_ESCROW:
        _write_hash(w, payload["escrow_id"])
        w.write_u64(int(payload["amount"]))
        _write_optional(w, payload.get("completion_proof"), _write_hash)
        return

    if tx_type == TransactionType.REFUND_ESCROW:
        _write_hash(w, payload["escrow_id"])
        w.write_u64(int(payload["amount"]))
        reason = payload.get("reason")
        if reason is not None:
            if not isinstance(reason, str):
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "refund reason must be string")
            if len(reason) > MAX_REFUND_REASON_LEN:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "refund reason too long")
        _write_optional(w, reason, _write_string_u8)
        return

    if tx_type == TransactionType.CHALLENGE_ESCROW:
        _write_hash(w, payload["escrow_id"])
        reason = payload["reason"]
        if not isinstance(reason, str) or reason == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason must be non-empty string")
        if len(reason) > MAX_REASON_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason too long")
        _write_string_u8(w, reason)
        _write_optional(w, payload.get("evidence_hash"), _write_hash)
        w.write_u64(int(payload["deposit"]))
        return

    if tx_type == TransactionType.DISPUTE_ESCROW:
        _write_hash(w, payload["escrow_id"])
        reason = payload["reason"]
        if not isinstance(reason, str) or reason == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason must be non-empty string")
        if len(reason) > MAX_REASON_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason too long")
        _write_string_u8(w, reason)
        _write_optional(w, payload.get("evidence_hash"), _write_hash)
        return

    if tx_type == TransactionType.APPEAL_ESCROW:
        _write_hash(w, payload["escrow_id"])
        reason = payload["reason"]
        if not isinstance(reason, str) or reason == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason must be non-empty string")
        if len(reason) > MAX_REASON_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason too long")
        _write_string_u8(w, reason)
        _write_optional(w, payload.get("new_evidence_hash"), _write_hash)
        w.write_u64(int(payload["appeal_deposit"]))
        w.write_u8(int(payload["appeal_mode"]))
        return

    if tx_type in (TransactionType.SUBMIT_VERDICT, TransactionType.SUBMIT_VERDICT_BY_JUROR):
        _write_hash(w, payload["escrow_id"])
        _write_hash(w, payload["dispute_id"])
        w.write_u32(int(payload["round"]))
        w.write_u64(int(payload["payer_amount"]))
        w.write_u64(int(payload["payee_amount"]))
        sigs = payload.get("signatures", [])
        _write_vec_u16(w, sigs, _write_arbiter_signature)
        return

    raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown escrow tx type")


def _encode_arbitration_payload(w: Writer, tx_type: TransactionType, payload: dict) -> None:
    if not isinstance(payload, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbitration payload must be dict")

    if tx_type == TransactionType.REGISTER_ARBITER:
        name = payload["name"]
        if not isinstance(name, str) or name == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter name must be non-empty string")
        if len(name) > MAX_ARBITER_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter name too long")
        _write_string_u8(w, name)
        _write_vec_u16(w, payload.get("expertise", []), lambda ww, e: ww.write_u8(int(e)))
        stake_amount = int(payload["stake_amount"])
        if stake_amount < MIN_ARBITER_STAKE:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "stake_amount below minimum")
        w.write_u64(stake_amount)
        min_value = int(payload["min_escrow_value"])
        max_value = int(payload["max_escrow_value"])
        if min_value > max_value:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "min_escrow_value > max_escrow_value")
        w.write_u64(min_value)
        w.write_u64(max_value)
        fee_bps = int(payload["fee_basis_points"])
        if fee_bps < 0 or fee_bps > MAX_FEE_BPS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "fee_basis_points out of range")
        w.write_u16(fee_bps)
        return

    if tx_type == TransactionType.UPDATE_ARBITER:
        if "name" in payload and payload.get("name") is not None:
            name = payload.get("name")
            if not isinstance(name, str) or name == "":
                raise SpecError(
                    ErrorCode.INVALID_PAYLOAD, "arbiter name must be non-empty string"
                )
            if len(name) > MAX_ARBITER_NAME_LEN:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbiter name too long")
        _write_optional(w, payload.get("name"), _write_string_u8)
        _write_optional(w, payload.get("expertise"), lambda ww, e: _write_vec_u16(ww, e, lambda w2, v: w2.write_u8(int(v))))
        if "fee_basis_points" in payload and payload.get("fee_basis_points") is not None:
            fee_bps = int(payload.get("fee_basis_points"))
            if fee_bps < 0 or fee_bps > MAX_FEE_BPS:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "fee_basis_points out of range")
        _write_optional(w, payload.get("fee_basis_points"), lambda ww, v: ww.write_u16(int(v)))
        if payload.get("min_escrow_value") is not None and payload.get("max_escrow_value") is not None:
            min_value = int(payload.get("min_escrow_value"))
            max_value = int(payload.get("max_escrow_value"))
            if min_value > max_value:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "min_escrow_value > max_escrow_value")
        _write_optional(w, payload.get("min_escrow_value"), lambda ww, v: ww.write_u64(int(v)))
        _write_optional(w, payload.get("max_escrow_value"), lambda ww, v: ww.write_u64(int(v)))
        _write_optional(w, payload.get("add_stake"), lambda ww, v: ww.write_u64(int(v)))
        if payload.get("status") is not None:
            status = int(payload.get("status"))
            if status != 1:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid arbiter status update")
        _write_optional(w, payload.get("status"), lambda ww, v: ww.write_u8(int(v)))
        deactivate = bool(payload.get("deactivate", False))
        if deactivate and payload.get("add_stake") not in (None, 0):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "deactivate cannot add stake")
        w.write_bool(deactivate)
        return

    if tx_type == TransactionType.COMMIT_ARBITRATION_OPEN:
        _write_hash(w, payload["escrow_id"])
        _write_hash(w, payload["dispute_id"])
        w.write_u32(int(payload["round"]))
        _write_hash(w, payload["request_id"])
        _write_hash(w, payload["arbitration_open_hash"])
        _write_signature(w, payload["opener_signature"])
        data = payload.get("arbitration_open_payload", b"")
        if not isinstance(data, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbitration_open_payload must be bytes")
        if len(data) > MAX_ARBITRATION_OPEN_BYTES:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbitration_open_payload too large")
        w.write_u32(len(data))
        w.write_bytes(bytes(data))
        return

    if tx_type == TransactionType.COMMIT_VOTE_REQUEST:
        _write_hash(w, payload["request_id"])
        _write_hash(w, payload["vote_request_hash"])
        _write_signature(w, payload["coordinator_signature"])
        data = payload.get("vote_request_payload", b"")
        if not isinstance(data, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "vote_request_payload must be bytes")
        if len(data) > MAX_VOTE_REQUEST_BYTES:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "vote_request_payload too large")
        w.write_u32(len(data))
        w.write_bytes(bytes(data))
        return

    if tx_type == TransactionType.COMMIT_SELECTION_COMMITMENT:
        _write_hash(w, payload["request_id"])
        _write_hash(w, payload["selection_commitment_id"])
        data = payload.get("selection_commitment_payload", b"")
        if not isinstance(data, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "selection_commitment_payload must be bytes")
        if len(data) > MAX_SELECTION_COMMITMENT_BYTES:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "selection_commitment_payload too large")
        w.write_u32(len(data))
        w.write_bytes(bytes(data))
        return

    if tx_type == TransactionType.COMMIT_JUROR_VOTE:
        _write_hash(w, payload["request_id"])
        _write_pubkey(w, payload["juror_pubkey"])
        _write_hash(w, payload["vote_hash"])
        _write_signature(w, payload["juror_signature"])
        data = payload.get("vote_payload", b"")
        if not isinstance(data, (bytes, bytearray)):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "vote_payload must be bytes")
        if len(data) > MAX_JUROR_VOTE_BYTES:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "vote_payload too large")
        w.write_u32(len(data))
        w.write_bytes(bytes(data))
        return

    if tx_type == TransactionType.SLASH_ARBITER:
        _write_hash(w, payload["committee_id"])
        _write_pubkey(w, payload["arbiter_pubkey"])
        amount = int(payload["amount"])
        if amount <= 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "slash amount must be > 0")
        w.write_u64(amount)
        reason_hash = payload["reason_hash"]
        if _is_zero_hash(reason_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash cannot be zero")
        _write_hash(w, reason_hash)
        approvals = payload.get("approvals", [])
        if len(approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "slash approvals required")
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        _write_vec_u16(w, approvals, _write_committee_approval)
        return

    if tx_type == TransactionType.REQUEST_ARBITER_EXIT:
        # empty payload
        return

    if tx_type == TransactionType.CANCEL_ARBITER_EXIT:
        # empty payload
        return

    if tx_type == TransactionType.WITHDRAW_ARBITER_STAKE:
        w.write_u64(int(payload["amount"]))
        return

    raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown arbitration tx type")


def _encode_kyc_payload(
    w: Writer, tx_type: TransactionType, payload: dict, current_time: Optional[int]
) -> None:
    if not isinstance(payload, dict):
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "kyc payload must be dict")
    if current_time is None:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "current_time required for kyc validation")
    current_time = int(current_time)

    def write_approval(ww: Writer, ap: dict) -> None:
        _write_pubkey(ww, ap["member_pubkey"])
        _write_signature(ww, ap["signature"])
        ww.write_u64(int(ap["timestamp"]))

    if tx_type == TransactionType.SET_KYC:
        _write_pubkey(w, payload["account"])
        level = int(payload["level"])
        if level not in VALID_KYC_LEVELS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid kyc level")
        w.write_u16(level)
        verified_at = int(payload["verified_at"])
        if verified_at > current_time + APPROVAL_FUTURE_TOLERANCE_SECONDS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "verified_at too far in future")
        w.write_u64(verified_at)
        data_hash = payload["data_hash"]
        if _is_zero_hash(data_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "data_hash cannot be zero")
        _write_hash(w, data_hash)
        _write_hash(w, payload["committee_id"])
        approvals = payload.get("approvals", [])
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        if len(approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
        if _kyc_level_to_tier(level) >= 5 and len(approvals) < 2:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "tier >=5 requires 2 approvals")
        _check_approval_uniqueness(approvals, "set_kyc")
        _check_approvals_time(approvals, current_time)
        _write_vec_u8(w, approvals, write_approval)
        return

    if tx_type == TransactionType.RENEW_KYC:
        _write_pubkey(w, payload["account"])
        verified_at = int(payload["verified_at"])
        if verified_at > current_time + APPROVAL_FUTURE_TOLERANCE_SECONDS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "verified_at too far in future")
        w.write_u64(verified_at)
        data_hash = payload["data_hash"]
        if _is_zero_hash(data_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "data_hash cannot be zero")
        _write_hash(w, data_hash)
        _write_hash(w, payload["committee_id"])
        approvals = payload.get("approvals", [])
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        if len(approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
        _check_approval_uniqueness(approvals, "renew_kyc")
        _check_approvals_time(approvals, current_time)
        _write_vec_u8(w, approvals, write_approval)
        return

    if tx_type == TransactionType.REVOKE_KYC:
        _write_pubkey(w, payload["account"])
        reason_hash = payload["reason_hash"]
        if _is_zero_hash(reason_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash cannot be zero")
        _write_hash(w, reason_hash)
        _write_hash(w, payload["committee_id"])
        approvals = payload.get("approvals", [])
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        if len(approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
        _check_approval_uniqueness(approvals, "revoke_kyc")
        _check_approvals_time(approvals, current_time)
        _write_vec_u8(w, approvals, write_approval)
        return

    if tx_type == TransactionType.EMERGENCY_SUSPEND:
        _write_pubkey(w, payload["account"])
        reason_hash = payload["reason_hash"]
        if _is_zero_hash(reason_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason_hash cannot be zero")
        _write_hash(w, reason_hash)
        _write_hash(w, payload["committee_id"])
        approvals = payload.get("approvals", [])
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        if len(approvals) < EMERGENCY_SUSPEND_MIN_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "not enough approvals")
        _check_approval_uniqueness(approvals, "emergency_suspend")
        _check_approvals_time(approvals, current_time)
        _write_vec_u8(w, approvals, write_approval)
        expires_at = int(payload["expires_at"])
        base_expires = current_time + EMERGENCY_SUSPEND_TIMEOUT
        min_expires = max(0, base_expires - APPROVAL_FUTURE_TOLERANCE_SECONDS)
        max_expires = base_expires + APPROVAL_FUTURE_TOLERANCE_SECONDS
        if not (min_expires <= expires_at <= max_expires):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "expires_at out of allowed window")
        w.write_u64(expires_at)
        return

    if tx_type == TransactionType.TRANSFER_KYC:
        _write_pubkey(w, payload["account"])
        if payload["source_committee_id"] == payload["dest_committee_id"]:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "source/dest committee must differ")
        _write_hash(w, payload["source_committee_id"])
        source_approvals = payload.get("source_approvals", [])
        if len(source_approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many source approvals")
        if len(source_approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "source approvals required")
        _check_approval_uniqueness(source_approvals, "transfer_kyc_source")
        _check_approvals_time(source_approvals, current_time)
        _write_vec_u8(w, source_approvals, write_approval)
        _write_hash(w, payload["dest_committee_id"])
        dest_approvals = payload.get("dest_approvals", [])
        if len(dest_approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many dest approvals")
        if len(dest_approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "dest approvals required")
        if len(source_approvals) + len(dest_approvals) > MAX_APPROVALS * 2:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many combined approvals")
        _check_approval_uniqueness(dest_approvals, "transfer_kyc_dest")
        _check_approvals_time(dest_approvals, current_time)
        # No duplicate approvers across committees
        source_keys = {bytes(ap["member_pubkey"]) for ap in source_approvals}
        for ap in dest_approvals:
            if bytes(ap["member_pubkey"]) in source_keys:
                raise SpecError(
                    ErrorCode.INVALID_PAYLOAD,
                    "duplicate approver across source/dest committees",
                )
        _write_vec_u8(w, dest_approvals, write_approval)
        new_data_hash = payload["new_data_hash"]
        if _is_zero_hash(new_data_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "new_data_hash cannot be zero")
        _write_hash(w, new_data_hash)
        transferred_at = int(payload["transferred_at"])
        if transferred_at > current_time + APPROVAL_FUTURE_TOLERANCE_SECONDS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "transferred_at too far in future")
        w.write_u64(transferred_at)
        return

    if tx_type == TransactionType.APPEAL_KYC:
        _write_pubkey(w, payload["account"])
        if payload["original_committee_id"] == payload["parent_committee_id"]:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committees must differ")
        _write_hash(w, payload["original_committee_id"])
        _write_hash(w, payload["parent_committee_id"])
        reason_hash = payload["reason_hash"]
        documents_hash = payload["documents_hash"]
        if _is_zero_hash(reason_hash) or _is_zero_hash(documents_hash):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "reason/documents hash cannot be zero")
        _write_hash(w, reason_hash)
        _write_hash(w, documents_hash)
        submitted_at = int(payload["submitted_at"])
        if submitted_at > current_time + APPROVAL_FUTURE_TOLERANCE_SECONDS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "submitted_at too far in future")
        if submitted_at < max(0, current_time - APPROVAL_FUTURE_TOLERANCE_SECONDS):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "submitted_at too far in past")
        w.write_u64(submitted_at)
        return

    if tx_type == TransactionType.BOOTSTRAP_COMMITTEE:
        name = payload["name"]
        if not isinstance(name, str) or name == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committee name must be non-empty string")
        if len(name) > MAX_COMMITTEE_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committee name too long")
        _write_string_u8(w, name)
        members = payload.get("members", [])
        if len(members) < MIN_COMMITTEE_MEMBERS or len(members) > MAX_COMMITTEE_MEMBERS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid member count")
        _check_member_uniqueness(members)
        _write_vec_u8(w, members, _write_committee_member_init)
        threshold = int(payload["threshold"])
        kyc_threshold = int(payload["kyc_threshold"])
        if threshold <= 0 or threshold > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid threshold")
        if kyc_threshold <= 0 or kyc_threshold > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid kyc_threshold")
        w.write_u8(threshold)
        w.write_u8(kyc_threshold)
        max_kyc_level = int(payload["max_kyc_level"])
        if max_kyc_level not in VALID_KYC_LEVELS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid max_kyc_level")
        w.write_u16(max_kyc_level)
        return

    if tx_type == TransactionType.REGISTER_COMMITTEE:
        name = payload["name"]
        if not isinstance(name, str) or name == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committee name must be non-empty string")
        if len(name) > MAX_COMMITTEE_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committee name too long")
        _write_string_u8(w, name)
        region = int(payload["region"])
        if region in (0, 255):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid region")
        w.write_u8(region)
        members = payload.get("members", [])
        if len(members) < MIN_COMMITTEE_MEMBERS or len(members) > MAX_COMMITTEE_MEMBERS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid member count")
        _check_member_uniqueness(members)
        _write_vec_u8(w, members, _write_new_committee_member)
        threshold = int(payload["threshold"])
        kyc_threshold = int(payload["kyc_threshold"])
        if threshold <= 0 or threshold > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid threshold")
        if kyc_threshold <= 0 or kyc_threshold > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid kyc_threshold")
        w.write_u8(threshold)
        w.write_u8(kyc_threshold)
        max_kyc_level = int(payload["max_kyc_level"])
        if max_kyc_level not in VALID_KYC_LEVELS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid max_kyc_level")
        w.write_u16(max_kyc_level)
        _write_hash(w, payload["parent_id"])
        approvals = payload.get("approvals", [])
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        if len(approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
        _check_approval_uniqueness(approvals, "register_committee")
        _check_approvals_time(approvals, current_time)
        _write_vec_u8(w, approvals, write_approval)
        return

    if tx_type == TransactionType.UPDATE_COMMITTEE:
        _write_hash(w, payload["committee_id"])
        _write_committee_update_data(w, payload["update"])
        approvals = payload.get("approvals", [])
        if len(approvals) > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "too many approvals")
        if len(approvals) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "approvals required")
        _check_approval_uniqueness(approvals, "update_committee")
        _check_approvals_time(approvals, current_time)
        _write_vec_u8(w, approvals, write_approval)
        return

    raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown kyc tx type")


def _write_committee_member_init(w: Writer, member: dict) -> None:
    _write_pubkey(w, member["public_key"])
    name = member.get("name")
    if name is not None:
        if not isinstance(name, str):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name must be string")
        if len(name) > MAX_MEMBER_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name too long")
    _write_optional(w, name, _write_string_u8)
    role = int(member["role"])
    _check_member_role(role)
    w.write_u8(role)


def _write_new_committee_member(w: Writer, member: dict) -> None:
    _write_pubkey(w, member["public_key"])
    name = member.get("name")
    if name is not None:
        if not isinstance(name, str):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name must be string")
        if len(name) > MAX_MEMBER_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name too long")
    _write_optional(w, name, _write_string_u8)
    role = int(member["role"])
    _check_member_role(role)
    w.write_u8(role)


_ARB_MODE_MAP = {"single": 1, "committee": 2, "juror": 3}


def _write_arbitration_config(w: Writer, cfg: dict) -> None:
    # ArbitrationConfig serializer order:
    # mode (u8) + arbiters (Vec<PublicKey>) + threshold (Option<u8>) + fee_amount (u64) + allow_appeal (bool)
    raw_mode = cfg["mode"]
    mode = _ARB_MODE_MAP.get(raw_mode, raw_mode) if isinstance(raw_mode, str) else raw_mode
    mode = int(mode)
    if mode == 0:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "arbitration mode cannot be None")
    arbiters = cfg.get("arbiters", [])
    # Convert hex strings to bytes if needed
    arbiters = [bytes.fromhex(a) if isinstance(a, str) else a for a in arbiters]
    if mode == 1:
        if len(arbiters) != 1:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "single mode requires 1 arbiter")
    if mode == 2 or mode == 3:
        if len(arbiters) == 0:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "mode requires arbiters")
    w.write_u8(mode)
    _write_vec_u16(w, arbiters, _write_pubkey)
    threshold = cfg.get("threshold")
    if threshold is not None:
        threshold = int(threshold)
        if threshold <= 0 or threshold > len(arbiters):
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid threshold")
    _write_optional(w, threshold, lambda ww, v: ww.write_u8(int(v)))
    w.write_u64(int(cfg["fee_amount"]))
    w.write_bool(bool(cfg["allow_appeal"]))


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


def _write_committee_approval(w: Writer, ap: dict) -> None:
    _write_pubkey(w, ap["member_pubkey"])
    _write_signature(w, ap["signature"])
    w.write_u64(int(ap["timestamp"]))


def _write_arbiter_signature(w: Writer, sig: dict) -> None:
    pubkey = sig.get("arbiter_pubkey") or sig["member_pubkey"]
    _write_pubkey(w, pubkey)
    _write_signature(w, sig["signature"])
    w.write_u64(int(sig["timestamp"]))


def _write_committee_update_data(w: Writer, update: dict) -> None:
    update_type = update["type"]
    if update_type == "add_member":
        w.write_u8(0)
        _write_pubkey(w, update["public_key"])
        name = update.get("name")
        if name is not None:
            if not isinstance(name, str):
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name must be string")
            if len(name) > MAX_MEMBER_NAME_LEN:
                raise SpecError(ErrorCode.INVALID_PAYLOAD, "member name too long")
        _write_optional(w, name, _write_string_u8)
        role = int(update["role"])
        _check_member_role(role)
        w.write_u8(role)
    elif update_type == "remove_member":
        w.write_u8(1)
        _write_pubkey(w, update["public_key"])
    elif update_type == "update_member_role":
        w.write_u8(2)
        _write_pubkey(w, update["public_key"])
        new_role = int(update["new_role"])
        _check_member_role(new_role)
        w.write_u8(new_role)
    elif update_type == "update_member_status":
        w.write_u8(3)
        _write_pubkey(w, update["public_key"])
        new_status = int(update["new_status"])
        _check_member_status(new_status)
        w.write_u8(new_status)
    elif update_type == "update_threshold":
        w.write_u8(4)
        new_threshold = int(update["new_threshold"])
        if new_threshold <= 0 or new_threshold > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid new_threshold")
        w.write_u8(new_threshold)
    elif update_type == "update_kyc_threshold":
        w.write_u8(5)
        new_kyc_threshold = int(update["new_kyc_threshold"])
        if new_kyc_threshold <= 0 or new_kyc_threshold > MAX_APPROVALS:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "invalid new_kyc_threshold")
        w.write_u8(new_kyc_threshold)
    elif update_type == "update_name":
        w.write_u8(6)
        new_name = update["new_name"]
        if not isinstance(new_name, str) or new_name == "":
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committee name must be non-empty string")
        if len(new_name) > MAX_COMMITTEE_NAME_LEN:
            raise SpecError(ErrorCode.INVALID_PAYLOAD, "committee name too long")
        _write_string_u8(w, new_name)
    elif update_type == "suspend_committee":
        w.write_u8(7)
    elif update_type == "activate_committee":
        w.write_u8(8)
    else:
        raise SpecError(ErrorCode.INVALID_PAYLOAD, "unknown committee update type")
