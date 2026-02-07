"""Wire-format vectors for all transaction types."""

from __future__ import annotations

import time

from tos_spec.config import (
    CHAIN_ID_DEVNET,
    COIN_VALUE,
    EMERGENCY_SUSPEND_TIMEOUT,
    MIN_ARBITER_STAKE,
    MIN_TIMEOUT_BLOCKS,
)
from tos_spec.encoding import encode_transaction
from tos_spec.test_accounts import ALICE, BOB, CAROL, DAVE, EVE, FRANK, GRACE, HEIDI
from tos_spec.types import (
    DelegationEntry,
    EnergyPayload,
    FeeType,
    FreezeDuration,
    MultiSig,
    SignatureId,
    Transaction,
    TransactionType,
    TransferPayload,
    TxVersion,
)


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig() -> bytes:
    return bytes(64)


def _tx(source, tx_type, payload, **kwargs):
    """Helper to build a Transaction with common defaults."""
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=source,
        tx_type=tx_type,
        payload=payload,
        fee=kwargs.get("fee", 100_000),
        fee_type=kwargs.get("fee_type", FeeType.TOS),
        nonce=kwargs.get("nonce", 1),
        reference_hash=kwargs.get("reference_hash", _hash(0)),
        reference_topoheight=kwargs.get("reference_topoheight", 0),
        signature=kwargs.get("signature", _sig()),
        source_commitments=kwargs.get("source_commitments", []),
        range_proof=kwargs.get("range_proof", None),
        multisig=kwargs.get("multisig", None),
    )


def _vec(wire_vector, name, tx, encoded, payload_json):
    """Helper to record a wire vector."""
    wire_vector(
        name,
        {
            "tx": {
                "version": int(tx.version),
                "chain_id": tx.chain_id,
                "source": tx.source.hex(),
                "tx_type": tx.tx_type.value,
                "nonce": tx.nonce,
                "fee": tx.fee,
                "fee_type": int(tx.fee_type),
                "payload": payload_json,
                "reference_hash": tx.reference_hash.hex(),
                "reference_topoheight": tx.reference_topoheight,
                "signature": tx.signature.hex(),
            },
            "expected_hex": encoded.hex(),
        },
    )


# ---------------------------------------------------------------------------
# Existing tests
# ---------------------------------------------------------------------------


def test_transfer_wire_vector(wire_vector) -> None:
    sender = ALICE
    receiver = BOB
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.TRANSFERS,
        payload=[TransferPayload(asset=_hash(0), destination=receiver, amount=100_000)],
        fee=100_000,
        fee_type=FeeType.TOS,
        nonce=5,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )

    encoded = encode_transaction(tx)
    wire_vector(
        "transfer_basic",
        {
            "tx": {
                "version": int(tx.version),
                "chain_id": tx.chain_id,
                "source": tx.source.hex(),
                "tx_type": tx.tx_type.value,
                "nonce": tx.nonce,
                "fee": tx.fee,
                "fee_type": int(tx.fee_type),
                "payload": [
                    {
                        "asset": tx.payload[0].asset.hex(),
                        "destination": tx.payload[0].destination.hex(),
                        "amount": tx.payload[0].amount,
                        "extra_data": None,
                    }
                ],
                "reference_hash": tx.reference_hash.hex(),
                "reference_topoheight": tx.reference_topoheight,
                "signature": tx.signature.hex(),
            },
            "expected_hex": encoded.hex(),
        },
    )


def test_energy_freeze_wire_vector(wire_vector) -> None:
    sender = CAROL
    tx = Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=TransactionType.ENERGY,
        payload=EnergyPayload(
            variant="freeze_tos",
            amount=100_000_000,
            duration=FreezeDuration(days=7),
        ),
        fee=0,
        fee_type=FeeType.ENERGY,
        nonce=1,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )

    encoded = encode_transaction(tx)
    wire_vector(
        "energy_freeze_basic",
        {
            "tx": {
                "version": int(tx.version),
                "chain_id": tx.chain_id,
                "source": tx.source.hex(),
                "tx_type": tx.tx_type.value,
                "nonce": tx.nonce,
                "fee": tx.fee,
                "fee_type": int(tx.fee_type),
                "payload": {
                    "variant": "freeze_tos",
                    "amount": 100_000_000,
                    "duration_days": 7,
                },
                "reference_hash": tx.reference_hash.hex(),
                "reference_topoheight": tx.reference_topoheight,
                "signature": tx.signature.hex(),
            },
            "expected_hex": encoded.hex(),
        },
    )


# ---------------------------------------------------------------------------
# Group 1 - Core/Simple
# ---------------------------------------------------------------------------


def test_burn_wire_vector(wire_vector) -> None:
    payload = {"asset": _hash(0), "amount": 500_000}
    tx = _tx(ALICE, TransactionType.BURN, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "burn_basic", tx, encoded, {
        "asset": _hash(0).hex(),
        "amount": 500_000,
    })


def test_multisig_wire_vector(wire_vector) -> None:
    payload = {"threshold": 2, "participants": [BOB, CAROL]}
    tx = _tx(ALICE, TransactionType.MULTISIG, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "multisig_basic", tx, encoded, {
        "threshold": 2,
        "participants": [BOB.hex(), CAROL.hex()],
    })


# ---------------------------------------------------------------------------
# Group 2 - Energy variants
# ---------------------------------------------------------------------------


def test_energy_unfreeze_wire_vector(wire_vector) -> None:
    payload = EnergyPayload(
        variant="unfreeze_tos",
        amount=50_000_000,
        from_delegation=False,
        record_index=0,
        delegatee_address=None,
    )
    tx = _tx(ALICE, TransactionType.ENERGY, payload, fee=0, fee_type=FeeType.ENERGY)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "energy_unfreeze_basic", tx, encoded, {
        "variant": "unfreeze_tos",
        "amount": 50_000_000,
        "from_delegation": False,
        "record_index": 0,
        "delegatee_address": None,
    })


def test_energy_freeze_delegate_wire_vector(wire_vector) -> None:
    payload = EnergyPayload(
        variant="freeze_tos_delegate",
        delegatees=[DelegationEntry(delegatee=BOB, amount=50_000_000)],
        duration=FreezeDuration(days=14),
    )
    tx = _tx(ALICE, TransactionType.ENERGY, payload, fee=0, fee_type=FeeType.ENERGY)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "energy_freeze_delegate_basic", tx, encoded, {
        "variant": "freeze_tos_delegate",
        "delegatees": [{"delegatee": BOB.hex(), "amount": 50_000_000}],
        "duration_days": 14,
    })


def test_energy_withdraw_unfrozen_wire_vector(wire_vector) -> None:
    payload = EnergyPayload(variant="withdraw_unfrozen")
    tx = _tx(ALICE, TransactionType.ENERGY, payload, fee=0, fee_type=FeeType.ENERGY)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "energy_withdraw_unfrozen", tx, encoded, {
        "variant": "withdraw_unfrozen",
    })


# ---------------------------------------------------------------------------
# Group 3 - Contracts
# ---------------------------------------------------------------------------


def test_deploy_contract_wire_vector(wire_vector) -> None:
    # Minimal ELF module: magic header + padding
    module = b"\x7fELF" + b"\x00" * 60
    payload = {"module": module, "invoke": None}
    tx = _tx(ALICE, TransactionType.DEPLOY_CONTRACT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "deploy_contract_basic", tx, encoded, {
        "module": module.hex(),
        "invoke": None,
    })


def test_invoke_contract_wire_vector(wire_vector) -> None:
    payload = {
        "contract": _hash(0xAB),
        "deposits": [{"asset": _hash(0), "amount": 1000}],
        "entry_id": 1,
        "max_gas": 100_000,
        "parameters": [],
    }
    tx = _tx(ALICE, TransactionType.INVOKE_CONTRACT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "invoke_contract_basic", tx, encoded, {
        "contract": _hash(0xAB).hex(),
        "deposits": [{"asset": _hash(0).hex(), "amount": 1000}],
        "entry_id": 1,
        "max_gas": 100_000,
        "parameters": [],
    })


# ---------------------------------------------------------------------------
# Group 4 - Privacy
# ---------------------------------------------------------------------------


def test_uno_transfers_wire_vector(wire_vector) -> None:
    transfer = {
        "asset": _hash(0),
        "destination": BOB,
        "extra_data": None,
        "commitment": bytes(32),
        "sender_handle": bytes(32),
        "receiver_handle": bytes(32),
        "ct_validity_proof": bytes(160),
    }
    payload = {"transfers": [transfer]}
    # range_proof is required for UNO; use dummy 32 bytes
    range_proof = bytes(32)
    tx = _tx(
        ALICE,
        TransactionType.UNO_TRANSFERS,
        payload,
        fee_type=FeeType.UNO,
        source_commitments=[bytes(32)],
        range_proof=range_proof,
    )
    encoded = encode_transaction(tx)
    _vec(wire_vector, "uno_transfers_basic", tx, encoded, {
        "transfers": [{
            "asset": _hash(0).hex(),
            "destination": BOB.hex(),
            "extra_data": None,
            "commitment": bytes(32).hex(),
            "sender_handle": bytes(32).hex(),
            "receiver_handle": bytes(32).hex(),
            "ct_validity_proof": bytes(160).hex(),
        }],
    })


def test_shield_transfers_wire_vector(wire_vector) -> None:
    transfer = {
        "asset": _hash(0),
        "destination": BOB,
        "amount": 100 * COIN_VALUE,
        "extra_data": None,
        "commitment": bytes(32),
        "receiver_handle": bytes(32),
        "proof": bytes(96),
    }
    payload = {"transfers": [transfer]}
    tx = _tx(
        ALICE,
        TransactionType.SHIELD_TRANSFERS,
        payload,
        source_commitments=[bytes(32)],
    )
    encoded = encode_transaction(tx)
    _vec(wire_vector, "shield_transfers_basic", tx, encoded, {
        "transfers": [{
            "asset": _hash(0).hex(),
            "destination": BOB.hex(),
            "amount": 100 * COIN_VALUE,
            "extra_data": None,
            "commitment": bytes(32).hex(),
            "receiver_handle": bytes(32).hex(),
            "proof": bytes(96).hex(),
        }],
    })


def test_unshield_transfers_wire_vector(wire_vector) -> None:
    transfer = {
        "asset": _hash(0),
        "destination": BOB,
        "amount": 100 * COIN_VALUE,
        "extra_data": None,
        "commitment": bytes(32),
        "sender_handle": bytes(32),
        "ct_validity_proof": bytes(160),
    }
    payload = {"transfers": [transfer]}
    tx = _tx(
        ALICE,
        TransactionType.UNSHIELD_TRANSFERS,
        payload,
        fee_type=FeeType.UNO,
        source_commitments=[bytes(32)],
    )
    encoded = encode_transaction(tx)
    _vec(wire_vector, "unshield_transfers_basic", tx, encoded, {
        "transfers": [{
            "asset": _hash(0).hex(),
            "destination": BOB.hex(),
            "amount": 100 * COIN_VALUE,
            "extra_data": None,
            "commitment": bytes(32).hex(),
            "sender_handle": bytes(32).hex(),
            "ct_validity_proof": bytes(160).hex(),
        }],
    })


# ---------------------------------------------------------------------------
# Group 5 - TNS
# ---------------------------------------------------------------------------


def test_register_name_wire_vector(wire_vector) -> None:
    payload = {"name": "alice"}
    tx = _tx(ALICE, TransactionType.REGISTER_NAME, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "register_name_basic", tx, encoded, {"name": "alice"})


def test_ephemeral_message_wire_vector(wire_vector) -> None:
    payload = {
        "sender_name_hash": _hash(0x01),
        "recipient_name_hash": _hash(0x02),
        "message_nonce": 42,
        "ttl_blocks": 1000,
        "encrypted_content": b"\xAB" * 64,
        "receiver_handle": bytes(32),
    }
    tx = _tx(ALICE, TransactionType.EPHEMERAL_MESSAGE, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "ephemeral_message_basic", tx, encoded, {
        "sender_name_hash": _hash(0x01).hex(),
        "recipient_name_hash": _hash(0x02).hex(),
        "message_nonce": 42,
        "ttl_blocks": 1000,
        "encrypted_content": (b"\xAB" * 64).hex(),
        "receiver_handle": bytes(32).hex(),
    })


# ---------------------------------------------------------------------------
# Group 6 - Referral
# ---------------------------------------------------------------------------


def test_bind_referrer_wire_vector(wire_vector) -> None:
    payload = {"referrer": BOB, "extra_data": None}
    tx = _tx(ALICE, TransactionType.BIND_REFERRER, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "bind_referrer_basic", tx, encoded, {
        "referrer": BOB.hex(),
        "extra_data": None,
    })


def test_batch_referral_reward_wire_vector(wire_vector) -> None:
    payload = {
        "asset": _hash(0),
        "from_user": BOB,
        "total_amount": 1_000_000,
        "levels": 3,
        "ratios": [500, 300, 200],
    }
    tx = _tx(ALICE, TransactionType.BATCH_REFERRAL_REWARD, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "batch_referral_reward_basic", tx, encoded, {
        "asset": _hash(0).hex(),
        "from_user": BOB.hex(),
        "total_amount": 1_000_000,
        "levels": 3,
        "ratios": [500, 300, 200],
    })


# ---------------------------------------------------------------------------
# Group 7 - Escrow (9 types)
# ---------------------------------------------------------------------------


def test_create_escrow_wire_vector(wire_vector) -> None:
    payload = {
        "task_id": "task-001",
        "provider": BOB,
        "amount": 1_000_000,
        "asset": _hash(0),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": None,
        "metadata": None,
    }
    tx = _tx(ALICE, TransactionType.CREATE_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "create_escrow_basic", tx, encoded, {
        "task_id": "task-001",
        "provider": BOB.hex(),
        "amount": 1_000_000,
        "asset": _hash(0).hex(),
        "timeout_blocks": MIN_TIMEOUT_BLOCKS,
        "challenge_window": 100,
        "challenge_deposit_bps": 500,
        "optimistic_release": False,
        "arbitration_config": None,
        "metadata": None,
    })


def test_deposit_escrow_wire_vector(wire_vector) -> None:
    payload = {"escrow_id": _hash(0x01), "amount": 500_000}
    tx = _tx(ALICE, TransactionType.DEPOSIT_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "deposit_escrow_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "amount": 500_000,
    })


def test_release_escrow_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "amount": 500_000,
        "completion_proof": _hash(0xCC),
    }
    tx = _tx(ALICE, TransactionType.RELEASE_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "release_escrow_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "amount": 500_000,
        "completion_proof": _hash(0xCC).hex(),
    })


def test_refund_escrow_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "amount": 500_000,
        "reason": "cancelled",
    }
    tx = _tx(ALICE, TransactionType.REFUND_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "refund_escrow_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "amount": 500_000,
        "reason": "cancelled",
    })


def test_challenge_escrow_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "reason": "work incomplete",
        "evidence_hash": _hash(0xEE),
        "deposit": 50_000,
    }
    tx = _tx(ALICE, TransactionType.CHALLENGE_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "challenge_escrow_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "reason": "work incomplete",
        "evidence_hash": _hash(0xEE).hex(),
        "deposit": 50_000,
    })


def test_dispute_escrow_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "reason": "terms violated",
        "evidence_hash": _hash(0xDD),
    }
    tx = _tx(ALICE, TransactionType.DISPUTE_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "dispute_escrow_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "reason": "terms violated",
        "evidence_hash": _hash(0xDD).hex(),
    })


def test_appeal_escrow_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "reason": "unfair verdict",
        "new_evidence_hash": _hash(0xAA),
        "appeal_deposit": 100_000,
        "appeal_mode": 0,
    }
    tx = _tx(ALICE, TransactionType.APPEAL_ESCROW, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "appeal_escrow_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "reason": "unfair verdict",
        "new_evidence_hash": _hash(0xAA).hex(),
        "appeal_deposit": 100_000,
        "appeal_mode": 0,
    })


def test_submit_verdict_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "dispute_id": _hash(0x02),
        "round": 1,
        "payer_amount": 400_000,
        "payee_amount": 600_000,
        "signatures": [
            {
                "arbiter_pubkey": BOB,
                "signature": _sig(),
                "timestamp": 1000,
            }
        ],
    }
    tx = _tx(ALICE, TransactionType.SUBMIT_VERDICT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "submit_verdict_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "dispute_id": _hash(0x02).hex(),
        "round": 1,
        "payer_amount": 400_000,
        "payee_amount": 600_000,
        "signatures": [
            {
                "arbiter_pubkey": BOB.hex(),
                "signature": _sig().hex(),
                "timestamp": 1000,
            }
        ],
    })


def test_submit_verdict_by_juror_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "dispute_id": _hash(0x02),
        "round": 1,
        "payer_amount": 300_000,
        "payee_amount": 700_000,
        "signatures": [
            {
                "arbiter_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": 2000,
            }
        ],
    }
    tx = _tx(ALICE, TransactionType.SUBMIT_VERDICT_BY_JUROR, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "submit_verdict_by_juror_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "dispute_id": _hash(0x02).hex(),
        "round": 1,
        "payer_amount": 300_000,
        "payee_amount": 700_000,
        "signatures": [
            {
                "arbiter_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": 2000,
            }
        ],
    })


# ---------------------------------------------------------------------------
# Group 8 - Arbitration (10 types)
# ---------------------------------------------------------------------------


def test_register_arbiter_wire_vector(wire_vector) -> None:
    payload = {
        "name": "arbiter-1",
        "expertise": [0, 1],
        "stake_amount": MIN_ARBITER_STAKE,
        "min_escrow_value": 100_000,
        "max_escrow_value": 10_000_000,
        "fee_basis_points": 250,
    }
    tx = _tx(ALICE, TransactionType.REGISTER_ARBITER, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "register_arbiter_basic", tx, encoded, {
        "name": "arbiter-1",
        "expertise": [0, 1],
        "stake_amount": MIN_ARBITER_STAKE,
        "min_escrow_value": 100_000,
        "max_escrow_value": 10_000_000,
        "fee_basis_points": 250,
    })


def test_update_arbiter_wire_vector(wire_vector) -> None:
    payload = {
        "name": "arbiter-updated",
        "expertise": [2],
        "fee_basis_points": 300,
        "min_escrow_value": 200_000,
        "max_escrow_value": 20_000_000,
        "add_stake": 500_000,
        "status": 1,
        "deactivate": False,
    }
    tx = _tx(ALICE, TransactionType.UPDATE_ARBITER, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "update_arbiter_basic", tx, encoded, {
        "name": "arbiter-updated",
        "expertise": [2],
        "fee_basis_points": 300,
        "min_escrow_value": 200_000,
        "max_escrow_value": 20_000_000,
        "add_stake": 500_000,
        "status": 1,
        "deactivate": False,
    })


def test_slash_arbiter_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "committee_id": _hash(0x10),
        "arbiter_pubkey": BOB,
        "amount": 100_000,
        "reason_hash": _hash(0x11),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
    }
    tx = _tx(ALICE, TransactionType.SLASH_ARBITER, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "slash_arbiter_basic", tx, encoded, {
        "committee_id": _hash(0x10).hex(),
        "arbiter_pubkey": BOB.hex(),
        "amount": 100_000,
        "reason_hash": _hash(0x11).hex(),
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
    })


def test_request_arbiter_exit_wire_vector(wire_vector) -> None:
    payload = {}
    tx = _tx(ALICE, TransactionType.REQUEST_ARBITER_EXIT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "request_arbiter_exit_basic", tx, encoded, {})


def test_withdraw_arbiter_stake_wire_vector(wire_vector) -> None:
    payload = {"amount": 500_000}
    tx = _tx(ALICE, TransactionType.WITHDRAW_ARBITER_STAKE, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "withdraw_arbiter_stake_basic", tx, encoded, {"amount": 500_000})


def test_cancel_arbiter_exit_wire_vector(wire_vector) -> None:
    payload = {}
    tx = _tx(ALICE, TransactionType.CANCEL_ARBITER_EXIT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "cancel_arbiter_exit_basic", tx, encoded, {})


def test_commit_arbitration_open_wire_vector(wire_vector) -> None:
    payload = {
        "escrow_id": _hash(0x01),
        "dispute_id": _hash(0x02),
        "round": 1,
        "request_id": _hash(0x03),
        "arbitration_open_hash": _hash(0x04),
        "opener_signature": _sig(),
        "arbitration_open_payload": b"\xAB" * 16,
    }
    tx = _tx(ALICE, TransactionType.COMMIT_ARBITRATION_OPEN, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "commit_arbitration_open_basic", tx, encoded, {
        "escrow_id": _hash(0x01).hex(),
        "dispute_id": _hash(0x02).hex(),
        "round": 1,
        "request_id": _hash(0x03).hex(),
        "arbitration_open_hash": _hash(0x04).hex(),
        "opener_signature": _sig().hex(),
        "arbitration_open_payload": (b"\xAB" * 16).hex(),
    })


def test_commit_vote_request_wire_vector(wire_vector) -> None:
    payload = {
        "request_id": _hash(0x03),
        "vote_request_hash": _hash(0x05),
        "coordinator_signature": _sig(),
        "vote_request_payload": b"\xCD" * 16,
    }
    tx = _tx(ALICE, TransactionType.COMMIT_VOTE_REQUEST, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "commit_vote_request_basic", tx, encoded, {
        "request_id": _hash(0x03).hex(),
        "vote_request_hash": _hash(0x05).hex(),
        "coordinator_signature": _sig().hex(),
        "vote_request_payload": (b"\xCD" * 16).hex(),
    })


def test_commit_selection_commitment_wire_vector(wire_vector) -> None:
    payload = {
        "request_id": _hash(0x03),
        "selection_commitment_id": _hash(0x06),
        "selection_commitment_payload": b"\xEF" * 16,
    }
    tx = _tx(ALICE, TransactionType.COMMIT_SELECTION_COMMITMENT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "commit_selection_commitment_basic", tx, encoded, {
        "request_id": _hash(0x03).hex(),
        "selection_commitment_id": _hash(0x06).hex(),
        "selection_commitment_payload": (b"\xEF" * 16).hex(),
    })


def test_commit_juror_vote_wire_vector(wire_vector) -> None:
    payload = {
        "request_id": _hash(0x03),
        "juror_pubkey": BOB,
        "vote_hash": _hash(0x07),
        "juror_signature": _sig(),
        "vote_payload": b"\x12" * 16,
    }
    tx = _tx(ALICE, TransactionType.COMMIT_JUROR_VOTE, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "commit_juror_vote_basic", tx, encoded, {
        "request_id": _hash(0x03).hex(),
        "juror_pubkey": BOB.hex(),
        "vote_hash": _hash(0x07).hex(),
        "juror_signature": _sig().hex(),
        "vote_payload": (b"\x12" * 16).hex(),
    })


# ---------------------------------------------------------------------------
# Group 9 - KYC (8 types)
# ---------------------------------------------------------------------------


def test_set_kyc_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "account": BOB,
        "level": 7,
        "verified_at": now,
        "data_hash": _hash(0x01),
        "committee_id": _hash(0x10),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
    }
    tx = _tx(ALICE, TransactionType.SET_KYC, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "set_kyc_basic", tx, encoded, {
        "account": BOB.hex(),
        "level": 7,
        "verified_at": now,
        "data_hash": _hash(0x01).hex(),
        "committee_id": _hash(0x10).hex(),
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
    })


def test_revoke_kyc_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "account": BOB,
        "reason_hash": _hash(0x02),
        "committee_id": _hash(0x10),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
    }
    tx = _tx(ALICE, TransactionType.REVOKE_KYC, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "revoke_kyc_basic", tx, encoded, {
        "account": BOB.hex(),
        "reason_hash": _hash(0x02).hex(),
        "committee_id": _hash(0x10).hex(),
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
    })


def test_renew_kyc_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "account": BOB,
        "verified_at": now,
        "data_hash": _hash(0x03),
        "committee_id": _hash(0x10),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
    }
    tx = _tx(ALICE, TransactionType.RENEW_KYC, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "renew_kyc_basic", tx, encoded, {
        "account": BOB.hex(),
        "verified_at": now,
        "data_hash": _hash(0x03).hex(),
        "committee_id": _hash(0x10).hex(),
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
    })


def test_transfer_kyc_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "account": BOB,
        "source_committee_id": _hash(0x10),
        "source_approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
        "dest_committee_id": _hash(0x20),
        "dest_approvals": [
            {
                "member_pubkey": DAVE,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
        "new_data_hash": _hash(0x04),
        "transferred_at": now,
    }
    tx = _tx(ALICE, TransactionType.TRANSFER_KYC, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "transfer_kyc_basic", tx, encoded, {
        "account": BOB.hex(),
        "source_committee_id": _hash(0x10).hex(),
        "source_approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
        "dest_committee_id": _hash(0x20).hex(),
        "dest_approvals": [
            {
                "member_pubkey": DAVE.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
        "new_data_hash": _hash(0x04).hex(),
        "transferred_at": now,
    })


def test_appeal_kyc_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "account": BOB,
        "original_committee_id": _hash(0x10),
        "parent_committee_id": _hash(0x20),
        "reason_hash": _hash(0x05),
        "documents_hash": _hash(0x06),
        "submitted_at": now,
    }
    tx = _tx(ALICE, TransactionType.APPEAL_KYC, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "appeal_kyc_basic", tx, encoded, {
        "account": BOB.hex(),
        "original_committee_id": _hash(0x10).hex(),
        "parent_committee_id": _hash(0x20).hex(),
        "reason_hash": _hash(0x05).hex(),
        "documents_hash": _hash(0x06).hex(),
        "submitted_at": now,
    })


def test_bootstrap_committee_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "name": "root-committee",
        "members": [
            {"public_key": CAROL, "name": "carol", "role": 0},
            {"public_key": DAVE, "name": "dave", "role": 2},
            {"public_key": EVE, "name": "eve", "role": 2},
        ],
        "threshold": 2,
        "kyc_threshold": 1,
        "max_kyc_level": 255,
    }
    tx = _tx(ALICE, TransactionType.BOOTSTRAP_COMMITTEE, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "bootstrap_committee_basic", tx, encoded, {
        "name": "root-committee",
        "members": [
            {"public_key": CAROL.hex(), "name": "carol", "role": 0},
            {"public_key": DAVE.hex(), "name": "dave", "role": 2},
            {"public_key": EVE.hex(), "name": "eve", "role": 2},
        ],
        "threshold": 2,
        "kyc_threshold": 1,
        "max_kyc_level": 255,
    })


def test_register_committee_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "name": "sub-committee",
        "region": 1,
        "members": [
            {"public_key": DAVE, "name": "dave", "role": 0},
            {"public_key": EVE, "name": "eve", "role": 2},
            {"public_key": FRANK, "name": "frank", "role": 2},
        ],
        "threshold": 2,
        "kyc_threshold": 1,
        "max_kyc_level": 63,
        "parent_id": _hash(0x10),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
    }
    tx = _tx(ALICE, TransactionType.REGISTER_COMMITTEE, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "register_committee_basic", tx, encoded, {
        "name": "sub-committee",
        "region": 1,
        "members": [
            {"public_key": DAVE.hex(), "name": "dave", "role": 0},
            {"public_key": EVE.hex(), "name": "eve", "role": 2},
            {"public_key": FRANK.hex(), "name": "frank", "role": 2},
        ],
        "threshold": 2,
        "kyc_threshold": 1,
        "max_kyc_level": 63,
        "parent_id": _hash(0x10).hex(),
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
    })


def test_update_committee_wire_vector(wire_vector) -> None:
    now = int(time.time())
    payload = {
        "committee_id": _hash(0x10),
        "update": {
            "type": "add_member",
            "public_key": GRACE,
            "name": "grace",
            "role": 2,
        },
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
    }
    tx = _tx(ALICE, TransactionType.UPDATE_COMMITTEE, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "update_committee_basic", tx, encoded, {
        "committee_id": _hash(0x10).hex(),
        "update": {
            "type": "add_member",
            "public_key": GRACE.hex(),
            "name": "grace",
            "role": 2,
        },
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
    })


def test_emergency_suspend_wire_vector(wire_vector) -> None:
    now = int(time.time())
    expires_at = now + EMERGENCY_SUSPEND_TIMEOUT
    payload = {
        "account": BOB,
        "reason_hash": _hash(0x07),
        "committee_id": _hash(0x10),
        "approvals": [
            {
                "member_pubkey": CAROL,
                "signature": _sig(),
                "timestamp": now,
            },
            {
                "member_pubkey": DAVE,
                "signature": _sig(),
                "timestamp": now,
            },
        ],
        "expires_at": expires_at,
    }
    tx = _tx(ALICE, TransactionType.EMERGENCY_SUSPEND, payload)
    encoded = encode_transaction(tx, current_time=now)
    _vec(wire_vector, "emergency_suspend_basic", tx, encoded, {
        "account": BOB.hex(),
        "reason_hash": _hash(0x07).hex(),
        "committee_id": _hash(0x10).hex(),
        "approvals": [
            {
                "member_pubkey": CAROL.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
            {
                "member_pubkey": DAVE.hex(),
                "signature": _sig().hex(),
                "timestamp": now,
            },
        ],
        "expires_at": expires_at,
    })


# ---------------------------------------------------------------------------
# Group 10 - Account
# ---------------------------------------------------------------------------


def test_agent_account_register_wire_vector(wire_vector) -> None:
    payload = {
        "variant": "register",
        "controller": BOB,
        "policy_hash": _hash(0x01),
        "energy_pool": None,
        "session_key_root": None,
    }
    tx = _tx(ALICE, TransactionType.AGENT_ACCOUNT, payload)
    encoded = encode_transaction(tx)
    _vec(wire_vector, "agent_account_register_basic", tx, encoded, {
        "variant": "register",
        "controller": BOB.hex(),
        "policy_hash": _hash(0x01).hex(),
        "energy_pool": None,
        "session_key_root": None,
    })
