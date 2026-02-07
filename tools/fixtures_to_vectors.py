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
    "crypto": "execution/crypto",
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


def _encode_tx_via_codec(tx: dict[str, Any]) -> str | None:
    """Encode a fixture tx dict via tos_codec (handles all tx types)."""
    try:
        import tos_codec
        from tos_spec.codec_adapter import tx_to_serde_json

        from fixtures_io import tx_from_json

        tx_obj = tx_from_json(tx)
        serde = tx_to_serde_json(tx_obj)
        return tos_codec.encode_tx(serde)
    except Exception:
        return None


def _encode_tx_if_possible(tx: dict[str, Any]) -> str | None:
    result = _encode_tx_via_codec(tx)
    if result:
        return result
    try:
        from tos_spec.encoding import encode_transaction

        from fixtures_io import tx_from_json

        tx_obj = tx_from_json(tx)
        # KYC types need current_time; use payload timestamp if available
        ct = None
        if isinstance(tx_obj.payload, dict):
            ct = tx_obj.payload.get("transferred_at") or tx_obj.payload.get("timestamp")
        return encode_transaction(tx_obj, current_time=ct).hex()
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

    # Collect the set of output paths we will write, then remove only stale
    # generated files.  Never delete manually-maintained files such as
    # accounts.json that live in vectors/ but have no fixtures source.
    vectors.mkdir(parents=True, exist_ok=True)

    # Snapshot existing files so we can remove stale ones afterwards.
    old_files = {p.resolve() for p in vectors.rglob("*") if p.is_file()}
    written: set[Path] = set()

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
            written.add(dest.resolve())
            count += 1
            continue

        if isinstance(data, dict) and "test_vectors" in data and isinstance(
            data["test_vectors"], list
        ):
            shutil.copy2(path, dest)
            written.add(dest.resolve())
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
                    wire_hex = case["tx"].get("wire_hex") or _encode_tx_if_possible(case["tx"])
                vec_entry: dict = {
                        "name": case.get("name", ""),
                        "description": case.get("description", ""),
                        "pre_state": case.get("pre_state"),
                }
                if case.get("runnable") is False or (not wire_hex and "tx" in case):
                    vec_entry["runnable"] = False
                vec_entry.update({
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
                vectors_out.append(vec_entry)
            dest = dest.with_suffix(".json")
            dest.write_text(json.dumps({"test_vectors": vectors_out}, indent=2))
            written.add(dest.resolve())
            count += 1
            continue

        shutil.copy2(path, dest)
        written.add(dest.resolve())
        count += 1

    # Remove stale generated files that no longer have a fixtures source.
    # Only touch files inside known generated subdirectories; top-level files
    # like accounts.json are manually maintained and must be preserved.
    generated_prefixes = tuple(
        vectors / p
        for p in (
            *MAPPING.values(),
            "unmapped",
        )
    )
    removed = 0
    for old in sorted(old_files - written):
        if any(str(old).startswith(str(pfx)) for pfx in generated_prefixes):
            old.unlink()
            removed += 1
    # Prune empty directories left behind (bottom-up).
    for d in sorted(vectors.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    print(f"Written {count} vector files into {vectors}")
    if removed:
        print(f"Removed {removed} stale files")


if __name__ == "__main__":
    main()
