"""P2P spec fixtures (non-executable, spec-only vectors)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml


P2P_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "p2p"


def _load_docs(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for doc in yaml.safe_load_all(handle):
            if isinstance(doc, dict):
                yield doc


def _build_vector(doc: dict[str, Any]) -> dict[str, Any]:
    spec = doc.get("spec") or {}
    name = spec.get("name") or ""
    desc = spec.get("description") or ""
    category = spec.get("category") or "p2p"
    subcategory = spec.get("subcategory") or ""

    return {
        "name": name,
        "description": desc,
        "runnable": False,
        "input": {
            "kind": "p2p",
            "category": category,
            "subcategory": subcategory,
            "preconditions": doc.get("preconditions") or [],
            "action": doc.get("action") or {},
        },
        "expected": doc.get("expected") or {},
    }


def test_p2p_specs(vector_test_group) -> None:
    for path in sorted(P2P_FIXTURES.glob("*.yaml")):
        rel = f"p2p/{path.stem}.json"
        for doc in _load_docs(path):
            vector = _build_vector(doc)
            if vector.get("name"):
                vector_test_group(rel, vector)
