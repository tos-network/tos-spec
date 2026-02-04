#!/usr/bin/env python3
"""Convert spec fixtures into client-consumable vectors.

This script is intentionally conservative: it mirrors fixtures into vectors
with a simple directory mapping so the conformance harness can consume them.
As vector schemas evolve, this script should be updated to emit the exact
vector format expected by Lab simulators.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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
        return Path("unmapped") / rel
    return Path(mapped) / Path(*rel.parts[1:])


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
        if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
            continue
        rel = path.relative_to(fixtures)
        dest = vectors / map_dest(rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        count += 1

    print(f"Copied {count} fixture files into vectors at {vectors}")


if __name__ == "__main__":
    main()
