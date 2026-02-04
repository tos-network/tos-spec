"""Generate hash/HMAC YAML vectors from Python specs."""

from __future__ import annotations

from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402


class PlainDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=None)


PlainDumper.add_representer(str, _str_representer)


def _dump_yaml(data: dict) -> str:
    try:
        import tos_yaml  # type: ignore  # noqa: WPS433

        return tos_yaml.dump_yaml(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    except Exception:
        return yaml.dump(data, Dumper=PlainDumper, sort_keys=False, width=4096)

from tos_spec.crypto.hash_vectors import (  # noqa: E402
    blake3_vectors,
    keccak256_vectors,
    sha256_vectors,
    sha3_512_vectors,
    sha512_vectors,
)
from tos_spec.crypto.hmac_vectors import hmac_sha256_vectors, hmac_sha512_vectors  # noqa: E402


def _prune(obj):  # remove None keys to match Rust serde skip_serializing_if
    if isinstance(obj, dict):
        return {k: _prune(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_prune(v) for v in obj]
    return obj


def _write(path: Path, data: dict) -> None:
    text = _dump_yaml(_prune(data))
    path.write_text(text)


def main() -> None:
    out = ROOT / "fixtures" / "crypto"
    out.mkdir(parents=True, exist_ok=True)

    _write(out / "sha256.yaml", sha256_vectors())
    _write(out / "sha512.yaml", sha512_vectors())
    _write(out / "sha3_512.yaml", sha3_512_vectors())
    _write(out / "keccak256.yaml", keccak256_vectors())
    _write(out / "blake3.yaml", blake3_vectors())
    _write(out / "hmac_sha256.yaml", hmac_sha256_vectors())
    _write(out / "hmac_sha512.yaml", hmac_sha512_vectors())


if __name__ == "__main__":
    main()
