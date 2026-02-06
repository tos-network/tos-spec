"""Pytest hooks to generate fixtures (EEST-style)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from tos_spec.state_transition import apply_tx
from tos_spec.test_accounts import SEED_MAP, sign_transaction
from tos_spec.types import ChainState, Transaction
from tools.fixtures_io import state_to_json, tx_to_json


def _try_wire_hex(tx: Transaction) -> str:
    """Try to encode a transaction to wire hex using tos_codec.

    Returns the hex string on success, or empty string on failure.
    """
    try:
        import tos_codec
        from tos_spec.codec_adapter import tx_to_serde_json

        return tos_codec.encode_tx(tx_to_serde_json(tx))
    except Exception:
        return ""


def _auto_sign(tx: Transaction) -> None:
    """Sign the transaction if its source is a known test account.

    If encoding fails (e.g. intentionally invalid payload in negative tests),
    the existing dummy signature is kept so ``apply_tx`` can still run and
    report the expected validation error.
    """
    if tx.source in SEED_MAP:
        try:
            tx.signature = sign_transaction(tx)
        except Exception:
            pass

_STATE_CASES: dict[str, list[dict[str, Any]]] = {}
_WIRE_VECTORS: list[dict[str, Any]] = []
_VECTOR_CASES: dict[str, list[dict[str, Any]]] = {}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--output",
        action="store",
        default=None,
        help="Output directory for generated fixtures",
    )


@pytest.fixture
def state_test() -> Callable[[str, ChainState, Transaction], None]:
    """Collect a state transition case and append expected outputs."""

    def _state_test(name: str, pre_state: ChainState, tx: Transaction) -> None:
        _auto_sign(tx)
        post_state, result = apply_tx(pre_state, tx)
        tx_json = tx_to_json(tx)
        tx_json["wire_hex"] = _try_wire_hex(tx)
        _STATE_CASES.setdefault("tx_core.json", []).append(
            {
                "name": name,
                "pre_state": state_to_json(pre_state),
                "tx": tx_json,
                "expected": {
                    "ok": result.ok,
                    "error": result.error.code.name if result.error else None,
                    "post_state": state_to_json(post_state),
                },
            }
        )

    return _state_test


@pytest.fixture
def state_test_group() -> Callable[[str, str, ChainState, Transaction], None]:
    """Collect a state transition case under a specific fixture path."""

    def _state_test_group(
        rel_path: str, name: str, pre_state: ChainState, tx: Transaction
    ) -> None:
        _auto_sign(tx)
        post_state, result = apply_tx(pre_state, tx)
        tx_json = tx_to_json(tx)
        tx_json["wire_hex"] = _try_wire_hex(tx)
        _STATE_CASES.setdefault(rel_path, []).append(
            {
                "name": name,
                "pre_state": state_to_json(pre_state),
                "tx": tx_json,
                "expected": {
                    "ok": result.ok,
                    "error": result.error.code.name if result.error else None,
                    "post_state": state_to_json(post_state),
                },
            }
        )

    return _state_test_group


@pytest.fixture
def wire_vector() -> Callable[[str, dict[str, Any]], None]:
    """Collect a wire-format vector case."""

    def _wire_vector(name: str, vector: dict[str, Any]) -> None:
        payload = {"name": name}
        payload.update(vector)
        _WIRE_VECTORS.append(payload)

    return _wire_vector


@pytest.fixture
def vector_test_group() -> Callable[[str, dict[str, Any]], None]:
    """Collect pre-built test_vectors under a specific fixture path."""

    def _vector_test_group(rel_path: str, vector: dict[str, Any]) -> None:
        _VECTOR_CASES.setdefault(rel_path, []).append(vector)

    return _vector_test_group


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    output_dir = session.config.getoption("--output")
    if not output_dir:
        return

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for rel_path, cases in _STATE_CASES.items():
        if not cases:
            continue
        target = out / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"cases": cases}, indent=2))

    if _WIRE_VECTORS:
        (out / "wire_format.json").write_text(
            json.dumps({"vectors": _WIRE_VECTORS}, indent=2)
        )

    for rel_path, vectors in _VECTOR_CASES.items():
        if not vectors:
            continue
        target = out / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"test_vectors": vectors}, indent=2))
