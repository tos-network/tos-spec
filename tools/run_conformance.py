#!/usr/bin/env python3
"""Run the Labu conformance harness with sane defaults."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def _abs_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOS conformance tests via Labu")
    parser.add_argument(
        "--vectors",
        default=str(Path(__file__).resolve().parent.parent / "vectors"),
        help="Host path to vectors directory (default: ~/tos-spec/vectors)",
    )
    parser.add_argument(
        "--sim",
        default="tos/execution",
        help="Simulator name (default: tos/execution)",
    )
    parser.add_argument(
        "--client",
        default="tos-rust,avatar-c",
        help="Comma-separated client names (default: tos-rust,avatar-c)",
    )
    parser.add_argument(
        "--workspace",
        default=str(Path(__file__).resolve().parent.parent / "vectors" / "_labu_workspace"),
        help="Output directory for Labu logs/results",
    )
    args = parser.parse_args()

    lab_root = Path(os.environ.get("LABU_ROOT", "~/labu")).expanduser().resolve()
    lab_bin = Path(os.environ.get("LABU_BIN", lab_root / "labu")).expanduser().resolve()
    if not lab_bin.exists():
        raise SystemExit(
            f"Labu binary not found: {lab_bin}. Build it with: cd {lab_root} && go build -o labu ./cmd/labu"
        )

    cmd = [
        str(lab_bin),
        "--sim",
        args.sim,
        "--client",
        args.client,
        "--vectors",
        _abs_path(args.vectors),
        "--workspace",
        _abs_path(args.workspace),
    ]
    subprocess.run(cmd, cwd=lab_root, check=True)


if __name__ == "__main__":
    main()
