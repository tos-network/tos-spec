"""RPC conformance vectors for the conformance server JSON-RPC endpoint.

These vectors are consumed by:
- Labu `simulators/tos/rpc` (Docker harness)
- `labu/tools/local_execution_runner.py` (local, single-machine)
"""

from __future__ import annotations

from tos_spec.config import COIN_VALUE
from tos_spec.state_digest import compute_state_digest
from tos_spec.types import (
    AccountState,
    ChainState,
    ContractState,
    EnergyResource,
    FreezeRecord,
    GlobalState,
    PendingUnfreeze,
    TnsRecord,
)
from tools.fixtures_io import state_to_json


ALICE = bytes.fromhex(
    "f05bc1df2831717c2992d85b57e0cf3d123fd6c254257de5f784be369747b249"
)
BOB = bytes.fromhex(
    "c29d170ab8a5b42a3520878501a87a27f9b5653fca8b0c59fc2786cf26e37824"
)
UNKNOWN = bytes.fromhex("11" * 32)


def _mk_state(*, variant: int) -> dict:
    st = ChainState(network_chain_id=1)
    st.global_state = GlobalState(
        total_supply=1_000_000 * COIN_VALUE,
        total_burned=0,
        total_energy=0,
        block_height=variant,
        timestamp=123_456_789 + variant,
    )
    st.accounts[ALICE] = AccountState(address=ALICE, balance=1000 * COIN_VALUE, nonce=7 + variant)
    st.accounts[BOB] = AccountState(address=BOB, balance=25 * COIN_VALUE, nonce=1)

    # Energy resource (frozen_tos is atomic in spec fixtures).
    er = EnergyResource(
        frozen_tos=10 * COIN_VALUE,
        energy=42 + variant,
        freeze_records=[
            FreezeRecord(
                amount=5 * COIN_VALUE,
                energy_gained=70,
                freeze_height=10,
                unlock_height=20,
            )
        ],
        pending_unfreezes=[
            PendingUnfreeze(amount=2 * COIN_VALUE, expire_height=30),
        ],
    )
    st.energy_resources[ALICE] = er

    st.tns_names["alice"] = TnsRecord(name="alice", owner=ALICE)

    contract_hash = bytes.fromhex("22" * 32)
    st.contracts[contract_hash] = ContractState(
        deployer=ALICE, module_hash=contract_hash, module=b"\x7fELF\x02\x01"
    )

    return state_to_json(st)


def _vec(name: str, description: str, pre_state: dict, rpc: dict, response: dict) -> dict:
    return {
        "name": name,
        "description": description,
        "pre_state": pre_state,
        "input": {"rpc_url": "/json_rpc", "rpc": rpc},
        "expected": {"response": response},
    }


def _export_expected(state_json: dict, *, rpc_id: int) -> dict:
    """Expected JSON-RPC response for tos_stateExport."""
    accounts = sorted(state_json.get("accounts", []), key=lambda a: a.get("address", ""))
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {
            "accounts": accounts,
            "agent_accounts": [],
            "contracts": state_json.get("contracts", []),
            "energy_resources": [],
            "global_state": state_json["global_state"],
            "network_chain_id": state_json["network_chain_id"],
            "tns_names": [],
        },
    }


def test_rpc_vectors(vector_test_group) -> None:
    out = "api/rpc.json"

    base = _mk_state(variant=0)
    alt = _mk_state(variant=1)

    base_digest = compute_state_digest(base)
    alt_digest = compute_state_digest(alt)

    # --- Happy path: state + account queries ---
    vector_test_group(
        out,
        _vec(
            "rpc_state_export_base",
            "JSON-RPC state export (base)",
            base,
            {"jsonrpc": "2.0", "id": 3, "method": "tos_stateExport", "params": {}},
            _export_expected(base, rpc_id=3),
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_state_digest_base",
            "JSON-RPC state digest (base)",
            base,
            {"jsonrpc": "2.0", "id": 1, "method": "tos_stateDigest", "params": {}},
            {"jsonrpc": "2.0", "id": 1, "result": base_digest},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_state_digest_alt",
            "JSON-RPC state digest (alt)",
            alt,
            {"jsonrpc": "2.0", "id": 2, "method": "tos_stateDigest", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "result": alt_digest},
        ),
    )

    alice_hex = ALICE.hex()
    bob_hex = BOB.hex()
    unknown_hex = UNKNOWN.hex()
    contract_hash_hex = ("22" * 32)

    vector_test_group(
        out,
        _vec(
            "rpc_account_get_alice",
            "JSON-RPC account get (Alice)",
            base,
            {"jsonrpc": "2.0", "id": 10, "method": "tos_accountGet", "params": {"address": alice_hex}},
            {
                "jsonrpc": "2.0",
                "id": 10,
                "result": {
                    "address": alice_hex,
                    "balance": 1000 * COIN_VALUE,
                    "nonce": 7,
                    "frozen": 10 * COIN_VALUE,
                    "energy": 42,
                    "flags": 0,
                    "data": "",
                },
            },
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_account_get_bob",
            "JSON-RPC account get (Bob)",
            base,
            {"jsonrpc": "2.0", "id": 11, "method": "tos_accountGet", "params": {"address": bob_hex}},
            {
                "jsonrpc": "2.0",
                "id": 11,
                "result": {
                    "address": bob_hex,
                    "balance": 25 * COIN_VALUE,
                    "nonce": 1,
                    "frozen": 0,
                    "energy": 0,
                    "flags": 0,
                    "data": "",
                },
            },
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_account_get_unknown",
            "JSON-RPC account get (unknown returns null)",
            base,
            {"jsonrpc": "2.0", "id": 12, "method": "tos_accountGet", "params": {"address": unknown_hex}},
            {"jsonrpc": "2.0", "id": 12, "result": None},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_account_get_missing_params",
            "JSON-RPC account get (missing params rejected)",
            base,
            {"jsonrpc": "2.0", "id": 13, "method": "tos_accountGet"},
            {"jsonrpc": "2.0", "id": 13, "error": {"code": -32602, "message": "Invalid params: address"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_account_get_invalid_type",
            "JSON-RPC account get (address wrong type rejected)",
            base,
            {"jsonrpc": "2.0", "id": 14, "method": "tos_accountGet", "params": {"address": 1}},
            {"jsonrpc": "2.0", "id": 14, "error": {"code": -32602, "message": "Invalid params: address"}},
        ),
    )

    # --- Energy / TNS / Contracts ---
    vector_test_group(
        out,
        _vec(
            "rpc_energy_get_alice",
            "JSON-RPC energy get (Alice)",
            base,
            {"jsonrpc": "2.0", "id": 20, "method": "tos_energyGet", "params": {"address": alice_hex}},
            {
                "jsonrpc": "2.0",
                "id": 20,
                "result": {
                    "address": alice_hex,
                    "energy": 42,
                    "frozen_tos": 10 * COIN_VALUE,
                    "last_update": 0,
                    "freeze_records": [
                        {
                            "amount": 5 * COIN_VALUE,
                            "energy_gained": 70,
                            "freeze_height": 10,
                            "unlock_height": 20,
                            "duration_days": 7,
                        }
                    ],
                    "pending_unfreezes": [{"amount": 2 * COIN_VALUE, "expire_height": 30}],
                },
            },
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_energy_get_unknown",
            "JSON-RPC energy get (unknown returns null)",
            base,
            {"jsonrpc": "2.0", "id": 21, "method": "tos_energyGet", "params": {"address": unknown_hex}},
            {"jsonrpc": "2.0", "id": 21, "result": None},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_energy_get_missing_params",
            "JSON-RPC energy get (missing params rejected)",
            base,
            {"jsonrpc": "2.0", "id": 22, "method": "tos_energyGet"},
            {"jsonrpc": "2.0", "id": 22, "error": {"code": -32602, "message": "Invalid params: address"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_tns_resolve_alice",
            "JSON-RPC resolve name -> owner (alice)",
            base,
            {"jsonrpc": "2.0", "id": 30, "method": "tos_tnsResolve", "params": {"name": "alice"}},
            {"jsonrpc": "2.0", "id": 30, "result": alice_hex},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_tns_resolve_unknown",
            "JSON-RPC resolve name -> null (missing)",
            base,
            {"jsonrpc": "2.0", "id": 31, "method": "tos_tnsResolve", "params": {"name": "missing"}},
            {"jsonrpc": "2.0", "id": 31, "result": None},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_contract_get_present",
            "JSON-RPC contract get (present)",
            base,
            {"jsonrpc": "2.0", "id": 40, "method": "tos_contractGet", "params": {"hash": contract_hash_hex}},
            {
                "jsonrpc": "2.0",
                "id": 40,
                "result": {"hash": contract_hash_hex, "module": "7f454c460201"},
            },
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_contract_get_missing",
            "JSON-RPC contract get (missing returns null)",
            base,
            {"jsonrpc": "2.0", "id": 41, "method": "tos_contractGet", "params": {"hash": "11" * 32}},
            {"jsonrpc": "2.0", "id": 41, "result": None},
        ),
    )

    # --- Methods list ---
    vector_test_group(
        out,
        _vec(
            "rpc_methods",
            "JSON-RPC supported method list",
            base,
            {"jsonrpc": "2.0", "id": 50, "method": "tos_methods", "params": {}},
            {
                "jsonrpc": "2.0",
                "id": 50,
                "result": [
                    "tos_stateDigest",
                    "tos_stateExport",
                    "tos_accountGet",
                    "tos_energyGet",
                    "tos_tnsResolve",
                    "tos_contractGet",
                    "tos_methods",
                ],
            },
        ),
    )

    # --- Error cases / edge coverage ---
    vector_test_group(
        out,
        _vec(
            "rpc_invalid_request_version",
            "Invalid JSON-RPC version rejected",
            base,
            {"jsonrpc": "1.0", "id": 60, "method": "tos_stateDigest", "params": {}},
            {"jsonrpc": "2.0", "id": 60, "error": {"code": -32600, "message": "Invalid Request"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_invalid_request_missing_jsonrpc",
            "Missing jsonrpc field rejected",
            base,
            {"id": 61, "method": "tos_stateDigest", "params": {}},
            {"jsonrpc": "2.0", "id": 61, "error": {"code": -32600, "message": "Invalid Request"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_method_not_found",
            "Unknown method rejected",
            base,
            {"jsonrpc": "2.0", "id": 62, "method": "tos_noSuchMethod", "params": {}},
            {"jsonrpc": "2.0", "id": 62, "error": {"code": -32601, "message": "Method not found"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_invalid_params_address",
            "Invalid address rejected",
            base,
            {"jsonrpc": "2.0", "id": 63, "method": "tos_accountGet", "params": {"address": "00"}},
            {"jsonrpc": "2.0", "id": 63, "error": {"code": -32602, "message": "Invalid params: address"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_invalid_params_name",
            "Missing/empty name rejected",
            base,
            {"jsonrpc": "2.0", "id": 64, "method": "tos_tnsResolve", "params": {"name": ""}},
            {"jsonrpc": "2.0", "id": 64, "error": {"code": -32602, "message": "Invalid params: name"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_invalid_params_hash",
            "Invalid contract hash rejected",
            base,
            {"jsonrpc": "2.0", "id": 65, "method": "tos_contractGet", "params": {"hash": "zz"}},
            {"jsonrpc": "2.0", "id": 65, "error": {"code": -32602, "message": "Invalid params: hash"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_contract_get_missing_params",
            "Missing contract hash rejected",
            base,
            {"jsonrpc": "2.0", "id": 66, "method": "tos_contractGet"},
            {"jsonrpc": "2.0", "id": 66, "error": {"code": -32602, "message": "Invalid params: hash"}},
        ),
    )
    vector_test_group(
        out,
        _vec(
            "rpc_state_digest_with_params",
            "stateDigest ignores extra params",
            base,
            {"jsonrpc": "2.0", "id": 67, "method": "tos_stateDigest", "params": {"foo": 1}},
            {"jsonrpc": "2.0", "id": 67, "result": base_digest},
        ),
    )

    # Bulk coverage: same queries with varying ids/params to hit target L3 vector count (~80).
    # This is intentionally repetitive to stress JSON-RPC envelope handling.
    i = 100
    for _ in range(15):
        vector_test_group(
            out,
            _vec(
                f"rpc_state_digest_repeat_{i}",
                "Repeat stateDigest with different id",
                base,
                {"jsonrpc": "2.0", "id": i, "method": "tos_stateDigest", "params": {}},
                {"jsonrpc": "2.0", "id": i, "result": base_digest},
            ),
        )
        i += 1
    for _ in range(15):
        vector_test_group(
            out,
            _vec(
                f"rpc_account_get_repeat_{i}",
                "Repeat accountGet(Alice) with different id",
                base,
                {"jsonrpc": "2.0", "id": i, "method": "tos_accountGet", "params": {"address": alice_hex}},
                {
                    "jsonrpc": "2.0",
                    "id": i,
                    "result": {
                        "address": alice_hex,
                        "balance": 1000 * COIN_VALUE,
                        "nonce": 7,
                        "frozen": 10 * COIN_VALUE,
                        "energy": 42,
                        "flags": 0,
                        "data": "",
                    },
                },
            ),
        )
        i += 1
    for _ in range(15):
        vector_test_group(
            out,
            _vec(
                f"rpc_energy_get_repeat_{i}",
                "Repeat energyGet(Alice) with different id",
                base,
                {"jsonrpc": "2.0", "id": i, "method": "tos_energyGet", "params": {"address": alice_hex}},
                {
                    "jsonrpc": "2.0",
                    "id": i,
                    "result": {
                        "address": alice_hex,
                        "energy": 42,
                        "frozen_tos": 10 * COIN_VALUE,
                        "last_update": 0,
                        "freeze_records": [
                            {
                                "amount": 5 * COIN_VALUE,
                                "energy_gained": 70,
                                "freeze_height": 10,
                                "unlock_height": 20,
                                "duration_days": 7,
                            }
                        ],
                        "pending_unfreezes": [{"amount": 2 * COIN_VALUE, "expire_height": 30}],
                    },
                },
            ),
        )
        i += 1

    for _ in range(10):
        vector_test_group(
            out,
            _vec(
                f"rpc_tns_resolve_repeat_{i}",
                "Repeat tnsResolve(alice) with different id",
                base,
                {"jsonrpc": "2.0", "id": i, "method": "tos_tnsResolve", "params": {"name": "alice"}},
                {"jsonrpc": "2.0", "id": i, "result": alice_hex},
            ),
        )
        i += 1

    for _ in range(10):
        vector_test_group(
            out,
            _vec(
                f"rpc_contract_get_repeat_{i}",
                "Repeat contractGet(present) with different id",
                base,
                {"jsonrpc": "2.0", "id": i, "method": "tos_contractGet", "params": {"hash": contract_hash_hex}},
                {
                    "jsonrpc": "2.0",
                    "id": i,
                    "result": {"hash": contract_hash_hex, "module": "7f454c460201"},
                },
            ),
        )
        i += 1

    for _ in range(5):
        vector_test_group(
            out,
            _vec(
                f"rpc_method_not_found_repeat_{i}",
                "Repeat method-not-found error with different id",
                base,
                {"jsonrpc": "2.0", "id": i, "method": "tos_noSuchMethod", "params": {}},
                {"jsonrpc": "2.0", "id": i, "error": {"code": -32601, "message": "Method not found"}},
            ),
        )
        i += 1
