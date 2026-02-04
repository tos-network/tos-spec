"""Run pytest and generate fixtures (EEST-style flow)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "fixtures"


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(ROOT / "tests"),
        "-q",
        "--output",
        str(OUT),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, env=env, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
