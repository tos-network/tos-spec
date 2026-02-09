"""Wire-format vectors (golden tx encoding hex) for core transaction types.

The published L0 vectors under `vectors/execution/transactions/wire_format_roundtrip.json`
are derived from `fixtures/wire_format.json`, which is emitted by this test suite.

We keep the source corpus vendored in `tests/data/wire_format_core.json` so `tos-spec`
remains hermetic (no runtime dependency on the `~/tos` repo).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


def test_wire_format_core_vectors(
    wire_vector: Callable[[str, dict[str, Any]], None],
) -> None:
    path = Path(__file__).resolve().parent / "data" / "wire_format_core.json"
    data = json.loads(path.read_text())
    for item in data.get("vectors", []) or []:
        wire_vector(
            item["name"],
            {
                "tx": item["tx"],
                "expected_hex": item["expected_hex"],
            },
        )

