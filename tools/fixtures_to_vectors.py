#!/usr/bin/env python3
"""Convert spec fixtures into client-consumable vectors.

This script converts scenario fixtures into runnable JSON vectors, and
mirrors other fixtures as-is. It is the spec layer's responsibility to
produce runnable vectors.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tos_spec.state_digest import compute_state_digest

MAPPING = {
    "api": "rpc",
    "consensus": "execution/consensus",
    "models": "state/models",
    "security": "errors/security",
    "syscalls": "execution/syscalls",
    "transactions": "execution/transactions",
}


def map_dest(rel: Path) -> Path:
    if not rel.parts:
        return Path("unmapped")
    top = rel.parts[0]
    mapped = MAPPING.get(top)
    if not mapped:
        if rel.name.startswith("tx_") or rel.name.startswith("wire_"):
            return Path("execution/transactions") / rel.name
        return Path("unmapped") / rel
    return Path(mapped) / Path(*rel.parts[1:])


def _hex_to_bytes(value: str | None) -> bytes:
    if value is None:
        return b""
    if not isinstance(value, str):
        raise TypeError("hex value must be string")
    v = value[2:] if value.startswith(("0x", "0X")) else value
    if v == "":
        return b""
    return bytes.fromhex(v)


def _u64_be(value: int) -> bytes:
    if value < 0:
        raise ValueError("u64 must be non-negative")
    return int(value).to_bytes(8, "big", signed=False)


def _map_error_code(name: str | None) -> int:
    if not name:
        from tos_spec.errors import ErrorCode

        return int(ErrorCode.SUCCESS)
    try:
        from tos_spec.errors import ErrorCode

        return int(ErrorCode[name])
    except Exception:
        from tos_spec.errors import ErrorCode

        return int(ErrorCode.UNKNOWN)


def _encode_tx_if_possible(tx: dict[str, Any]) -> str | None:
    try:
        from tos_spec.encoding import encode_transaction
        from tos_spec.types import FeeType, Transaction, TransactionType, TransferPayload, TxVersion

        version = TxVersion(tx["version"])
        chain_id = int(tx["chain_id"])
        source = _hex_to_bytes(tx["source"])
        tx_type = TransactionType(tx["tx_type"])
        payload = tx.get("payload")

        if tx_type == TransactionType.TRANSFERS:
            transfers = []
            for entry in payload or []:
                transfers.append(
                    TransferPayload(
                        asset=_hex_to_bytes(entry["asset"]),
                        destination=_hex_to_bytes(entry["destination"]),
                        amount=int(entry["amount"]),
                        extra_data=_hex_to_bytes(entry["extra_data"]) if entry.get("extra_data") else None,
                    )
                )
            payload_obj: object = transfers
        elif tx_type == TransactionType.BURN:
            payload_obj = {
                "asset": _hex_to_bytes(payload["asset"]),
                "amount": int(payload["amount"]),
            }
        else:
            payload_obj = payload

        sig = _hex_to_bytes(tx["signature"]) if tx.get("signature") else None
        ref_hash = _hex_to_bytes(tx["reference_hash"]) if tx.get("reference_hash") else None

        tx_obj = Transaction(
            version=version,
            chain_id=chain_id,
            source=source,
            tx_type=tx_type,
            payload=payload_obj,
            fee=int(tx["fee"]),
            fee_type=FeeType(int(tx["fee_type"])),
            nonce=int(tx["nonce"]),
            reference_hash=ref_hash,
            reference_topoheight=tx.get("reference_topoheight"),
            signature=sig,
        )
        return encode_transaction(tx_obj).hex()
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert fixtures to vectors")
    parser.add_argument("--fixtures", default=str(ROOT / "fixtures"))
    parser.add_argument("--vectors", default=str(ROOT / "vectors"))
    args = parser.parse_args()

    fixtures = Path(args.fixtures).resolve()
    vectors = Path(args.vectors).resolve()

    if not fixtures.exists():
        raise SystemExit(f"fixtures dir not found: {fixtures}")

    vectors.mkdir(parents=True, exist_ok=True)

    count = 0
    for path in fixtures.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix.lower() not in {".json"}:
            continue
        rel = path.relative_to(fixtures)
        dest = vectors / map_dest(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = json.loads(path.read_text())
        except Exception:
            shutil.copy2(path, dest)
            count += 1
            continue

        if isinstance(data, dict) and "cases" in data and isinstance(data["cases"], list):
            vectors_out = []
            for case in data["cases"]:
                expected = case.get("expected", {})
                post_state = expected.get("post_state")
                state_digest = compute_state_digest(post_state) if post_state else None
                error_code = _map_error_code(expected.get("error"))
                wire_hex = None
                if "tx" in case:
                    wire_hex = _encode_tx_if_possible(case["tx"])
                vectors_out.append(
                    {
                        "name": case.get("name", ""),
                        "description": case.get("description", ""),
                        "pre_state": case.get("pre_state"),
                        "input": {
                            "kind": "tx" if "tx" in case else "block",
                            "wire_hex": wire_hex or "",
                            "tx": case.get("tx"),
                        },
                        "expected": {
                            "success": bool(expected.get("ok", False)),
                            "error_code": int(error_code),
                            "state_digest": state_digest or "",
                            "post_state": post_state,
                        },
                    }
                )
            dest = dest.with_suffix(".json")
            dest.write_text(json.dumps({"test_vectors": vectors_out}, indent=2))
            count += 1
            continue

        shutil.copy2(path, dest)
        count += 1

    print(f"Copied {count} fixture files into vectors at {vectors}")


if __name__ == "__main__":
    main()
