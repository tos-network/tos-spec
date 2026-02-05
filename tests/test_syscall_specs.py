"""Syscall spec fixtures (non-executable, spec-only vectors)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
SYSCALL_SPECS = ROOT / "fixtures" / "syscalls"


def _iter_specs(path: Path) -> Iterable[Dict[str, Any]]:
    try:
        docs = list(yaml.safe_load_all(path.read_text()))
    except yaml.YAMLError:
        return []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        spec = doc.get("spec")
        if isinstance(spec, dict):
            yield spec


def test_syscall_spec_vectors(vector_test_group) -> None:
    for path in sorted(SYSCALL_SPECS.glob("*.yaml")):
        out_name = path.with_suffix(".json").name
        rel_path = f"syscalls/{out_name}"
        for spec in _iter_specs(path):
            name = spec.get("name", path.stem)
            vector_test_group(
                rel_path,
                {
                    "name": name,
                    "description": spec.get("description", ""),
                    "runnable": False,
                    "input": {"kind": "spec", "source": path.name},
                    "expected": {},
                },
            )
