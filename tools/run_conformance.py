#!/usr/bin/env python3
"""
Run the conformance stack from ~/tos-spec with sane defaults.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def _compose_cmd() -> list[str]:
    if shutil.which("docker"):
        return ["docker", "compose"]
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    raise SystemExit("docker or docker-compose not found in PATH")


def _abs_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TOS conformance tests")
    parser.add_argument(
        "--vectors",
        default=str(Path(__file__).resolve().parent.parent / "vectors"),
        help="Host path to vectors directory (default: ~/tos-spec/vectors)",
    )
    parser.add_argument(
        "--results",
        default=str(Path(__file__).resolve().parent.parent / "conformance" / "results"),
        help="Host path to results directory (default: ~/tos-spec/conformance/results)",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Run docker compose build before up",
    )
    parser.add_argument(
        "--down",
        action="store_true",
        help="Run docker compose down after completion",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    compose_dir = repo_root / "conformance"
    if not compose_dir.exists():
        raise SystemExit(f"Missing conformance directory: {compose_dir}")

    env = os.environ.copy()
    env["VECTOR_DIR"] = _abs_path(args.vectors)
    env["RESULT_DIR"] = _abs_path(args.results)

    cmd = _compose_cmd()

    if args.build:
        subprocess.run(cmd + ["build"], cwd=compose_dir, env=env, check=True)

    subprocess.run(
        cmd
        + [
            "up",
            "--abort-on-container-exit",
            "--exit-code-from",
            "orchestrator",
        ],
        cwd=compose_dir,
        env=env,
        check=True,
    )

    if args.down:
        subprocess.run(cmd + ["down"], cwd=compose_dir, env=env, check=True)


if __name__ == "__main__":
    main()
