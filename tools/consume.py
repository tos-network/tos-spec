"""Consume fixtures and validate against Python specs."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from tos_spec.encoding import encode_transaction  # noqa: E402
from tos_spec.state_transition import apply_tx  # noqa: E402
from fixtures_io import state_from_json, tx_from_json  # noqa: E402


def _check_state_cases(path: Path) -> list[str]:
    failures: list[str] = []
    data = json.loads(path.read_text())

    for case in data.get("cases", []):
        pre_state = state_from_json(case["pre_state"])
        tx = tx_from_json(case["tx"])
        post_state, result = apply_tx(pre_state, tx)

        expected = case["expected"]
        if result.ok != expected["ok"]:
            failures.append(f"{case['name']}: ok_mismatch")
            continue

        actual_err = result.error.code.name if result.error else None
        if actual_err != expected["error"]:
            failures.append(f"{case['name']}: error_mismatch")
            continue

        expected_state = state_from_json(expected["post_state"])
        if post_state.accounts.keys() != expected_state.accounts.keys():
            failures.append(f"{case['name']}: accounts_mismatch")
            continue

        for addr, acct in post_state.accounts.items():
            exp = expected_state.accounts[addr]
            if (acct.balance, acct.nonce) != (exp.balance, exp.nonce):
                failures.append(f"{case['name']}: account_state_mismatch")
                break

    return failures


def _check_wire_vectors(path: Path) -> list[str]:
    failures: list[str] = []
    data = json.loads(path.read_text())
    for vec in data.get("vectors", []):
        tx = tx_from_json(vec["tx"])
        encoded = encode_transaction(tx).hex()
        if encoded != vec["expected_hex"]:
            failures.append(f"{vec['name']}: wire_mismatch")
    return failures


def main() -> None:
    fixtures = ROOT / "fixtures"

    failures: list[str] = []

    tx_core = fixtures / "tx_core.json"
    if tx_core.exists():
        failures.extend(_check_state_cases(tx_core))

    wire = fixtures / "wire_format.json"
    if wire.exists():
        failures.extend(_check_wire_vectors(wire))

    if failures:
        for f in failures:
            print("FAIL", f)
        raise SystemExit(1)

    print("All fixtures passed")


if __name__ == "__main__":
    main()
