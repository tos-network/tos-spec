"""Spec fixtures (non-executable, spec-only vectors)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Tuple

import yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "fixtures"


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
            continue
        if "name" in doc or "description" in doc:
            yield doc


def _iter_vectors(
    doc: Any, path: Path
) -> Iterator[Tuple[str, str, Dict[str, Any]]]:
    if isinstance(doc, dict) and isinstance(doc.get("spec"), dict):
        spec = doc["spec"]
        name = spec.get("name", path.stem)
        desc = spec.get("description", "")
        yield name, desc, {"kind": "spec", "source": path.name}
        return

    if isinstance(doc, dict):
        vector_keys = [k for k, v in doc.items() if k.endswith("_vectors") and isinstance(v, list)]
        if vector_keys:
            for key in vector_keys:
                for idx, entry in enumerate(doc.get(key, [])):
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("name", f"{path.stem}:{key}:{idx}")
                    desc = entry.get("description", "")
                    payload = {"kind": "vector_set", "group": key, "data": entry}
                    yield name, desc, payload
            return

        name = doc.get("name", path.stem)
        desc = doc.get("description", "")
        yield name, desc, {"kind": "raw_spec", "data": doc}
        return

    if isinstance(doc, list):
        for idx, entry in enumerate(doc):
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", f"{path.stem}:{idx}")
            desc = entry.get("description", "")
            yield name, desc, {"kind": "raw_spec", "data": entry}


def test_spec_yaml_vectors(vector_test_group) -> None:
    for path in sorted(FIXTURES_DIR.rglob("*.yaml")):
        rel_yaml = path.relative_to(FIXTURES_DIR)
        rel_json = rel_yaml.with_suffix(".json")
        if (FIXTURES_DIR / rel_json).exists():
            continue
        try:
            docs = list(yaml.safe_load_all(path.read_text()))
        except yaml.YAMLError:
            continue
        for doc in docs:
            for name, desc, payload in _iter_vectors(doc, path):
                vector_test_group(
                    str(rel_json),
                    {
                        "name": name,
                        "description": desc,
                        "runnable": False,
                        "input": payload,
                        "expected": {},
                    },
                )
