"""Arbitration tx fixtures."""

from __future__ import annotations

import hashlib
import json

import tos_signer

from tos_spec.config import CHAIN_ID_DEVNET, COIN_VALUE, MIN_ARBITER_STAKE
from tos_spec.test_accounts import ALICE, BOB
from tos_spec.types import (
    AccountState,
    ChainState,
    FeeType,
    Transaction,
    TransactionType,
    TxVersion,
)


def _addr(byte: int) -> bytes:
    return bytes([byte]) * 32


def _hash(byte: int) -> bytes:
    return bytes([byte]) * 32


def _sig(byte: int) -> bytes:
    # Use byte only in first position of each 32-byte scalar half to ensure
    # the value is a canonical Ristretto scalar (< curve order l).
    return bytes([byte]) + b"\x00" * 31 + bytes([byte]) + b"\x00" * 31


def _canonical_hash_without_sig(obj: dict) -> bytes:
    """SHA3-256 of canonical JSON with 'signature' field removed.

    Mirrors Rust's canonical_hash_without_signature: remove the signature
    field, recursively sort all object keys, compact-serialize, SHA3-256.
    """
    d = {k: v for k, v in obj.items() if k != "signature"}
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha3_256(canonical).digest()


def _base_state() -> ChainState:
    state = ChainState(network_chain_id=CHAIN_ID_DEVNET)
    state.accounts[ALICE] = AccountState(
        address=ALICE, balance=10_000 * COIN_VALUE, nonce=5
    )
    return state


def _mk_arb_tx(
    sender: bytes, nonce: int, tx_type: TransactionType, payload: dict, fee: int
) -> Transaction:
    return Transaction(
        version=TxVersion.T1,
        chain_id=CHAIN_ID_DEVNET,
        source=sender,
        tx_type=tx_type,
        payload=payload,
        fee=fee,
        fee_type=FeeType.TOS,
        nonce=nonce,
        reference_hash=_hash(0),
        reference_topoheight=0,
        signature=bytes(64),
    )


# --- register_arbiter specs ---


def test_register_arbiter_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "name": "ArbiterAlice",
        "expertise": [1, 2, 3],
        "stake_amount": MIN_ARBITER_STAKE,
        "min_escrow_value": COIN_VALUE,
        "max_escrow_value": 1000 * COIN_VALUE,
        "fee_basis_points": 250,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/register_arbiter.json",
        "register_arbiter_success",
        state,
        tx,
    )


def test_register_arbiter_low_stake(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "name": "LowStake",
        "expertise": [1],
        "stake_amount": COIN_VALUE,
        "min_escrow_value": COIN_VALUE,
        "max_escrow_value": 10 * COIN_VALUE,
        "fee_basis_points": 100,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.REGISTER_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/register_arbiter.json",
        "register_arbiter_low_stake",
        state,
        tx,
    )


# --- update_arbiter specs ---


def test_update_arbiter_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "name": "ArbiterAliceUpdated",
        "fee_basis_points": 300,
        "deactivate": False,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.UPDATE_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/update_arbiter.json",
        "update_arbiter_success",
        state,
        tx,
    )


# --- request_arbiter_exit specs ---


def test_request_arbiter_exit(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {}
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.REQUEST_ARBITER_EXIT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/request_arbiter_exit.json",
        "request_arbiter_exit",
        state,
        tx,
    )


# --- withdraw_arbiter_stake specs ---


def test_withdraw_arbiter_stake_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {"amount": MIN_ARBITER_STAKE}
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.WITHDRAW_ARBITER_STAKE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/withdraw_arbiter_stake.json",
        "withdraw_arbiter_stake_success",
        state,
        tx,
    )


# --- cancel_arbiter_exit specs ---


def test_cancel_arbiter_exit(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {}
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.CANCEL_ARBITER_EXIT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/cancel_arbiter_exit.json",
        "cancel_arbiter_exit",
        state,
        tx,
    )


# --- slash_arbiter specs ---


def test_slash_arbiter_success(state_test_group) -> None:
    state = _base_state()
    sender = ALICE
    payload = {
        "committee_id": _hash(50),
        "arbiter_pubkey": _addr(30),
        "amount": COIN_VALUE * 10,
        "reason_hash": _hash(70),
        "approvals": [
            {
                "member_pubkey": _addr(10),
                "signature": _sig(10),
                "timestamp": 1_700_000_000,
            },
            {
                "member_pubkey": _addr(11),
                "signature": _sig(11),
                "timestamp": 1_700_000_000,
            },
        ],
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.SLASH_ARBITER, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/slash_arbiter.json",
        "slash_arbiter_success",
        state,
        tx,
    )


# --- commit_arbitration_open specs ---


def test_commit_arbitration_open(state_test_group) -> None:
    state = _base_state()
    sender = ALICE

    escrow_id = _hash(60)
    dispute_id = _hash(61)
    request_id = _hash(62)

    # Build ArbitrationOpen JSON matching Rust's serde(rename_all = "camelCase").
    # coordinator_pubkey must equal the tx signer (ALICE); opener signs the message.
    arb_open = {
        "type": "ArbitrationOpen",
        "version": 1,
        "chainId": CHAIN_ID_DEVNET,
        "escrowId": escrow_id.hex(),
        "escrowHash": _hash(70).hex(),
        "disputeId": dispute_id.hex(),
        "round": 1,
        "disputeOpenHeight": 100,
        "committeeId": _hash(71).hex(),
        "committeePolicyHash": _hash(72).hex(),
        "payer": "payer-account",
        "payee": "payee-account",
        "evidenceUri": "https://example.com/evidence",
        "evidenceHash": _hash(73).hex(),
        "evidenceManifestUri": "https://example.com/manifest",
        "evidenceManifestHash": _hash(74).hex(),
        "clientNonce": "test-nonce-123",
        "issuedAt": 1700000000,
        "expiresAt": 1700100000,
        "coordinatorPubkey": ALICE.hex(),
        "coordinatorAccount": "coordinator-account",
        "requestId": request_id.hex(),
        "openerPubkey": BOB.hex(),
        "signature": "00" * 64,  # placeholder replaced below
    }

    arb_open_hash = _canonical_hash_without_sig(arb_open)
    opener_sig = bytes(tos_signer.sign_data(arb_open_hash, 3))  # BOB = seed 3
    arb_open["signature"] = opener_sig.hex()

    arb_open_bytes = json.dumps(arb_open, separators=(",", ":")).encode("utf-8")

    payload = {
        "escrow_id": escrow_id,
        "dispute_id": dispute_id,
        "round": 1,
        "request_id": request_id,
        "arbitration_open_hash": arb_open_hash,
        "opener_signature": opener_sig,
        "arbitration_open_payload": arb_open_bytes,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_ARBITRATION_OPEN, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_arbitration_open.json",
        "commit_arbitration_open",
        state,
        tx,
    )


# --- commit_vote_request specs ---


def test_commit_vote_request(state_test_group) -> None:
    state = _base_state()
    sender = ALICE

    request_id = _hash(62)

    # Build VoteRequest JSON matching Rust's serde(rename_all = "camelCase").
    # coordinator_pubkey must equal the tx signer (ALICE); coordinator signs.
    vote_req = {
        "type": "VoteRequest",
        "version": 1,
        "requestId": request_id.hex(),
        "chainId": CHAIN_ID_DEVNET,
        "escrowId": _hash(60).hex(),
        "escrowHash": _hash(70).hex(),
        "disputeId": _hash(61).hex(),
        "round": 1,
        "disputeOpenHeight": 100,
        "committeeId": _hash(71).hex(),
        "committeePolicyHash": _hash(72).hex(),
        "selectionBlock": 200,
        "selectionCommitmentId": _hash(75).hex(),
        "arbitrationOpenHash": _hash(63).hex(),
        "issuedAt": 1700000000,
        "voteDeadline": 1700200000,
        "selectedJurors": ["juror1", "juror2", "juror3"],
        "selectedJurorsHash": _hash(76).hex(),
        "evidenceHash": _hash(73).hex(),
        "evidenceManifestHash": _hash(74).hex(),
        "evidenceUri": "https://example.com/evidence",
        "evidenceManifestUri": "https://example.com/manifest",
        "coordinatorPubkey": ALICE.hex(),
        "coordinatorAccount": "coordinator-account",
        "signature": "00" * 64,  # placeholder replaced below
    }

    vote_req_hash = _canonical_hash_without_sig(vote_req)
    coord_sig = bytes(tos_signer.sign_data(vote_req_hash, 2))  # ALICE = seed 2
    vote_req["signature"] = coord_sig.hex()

    vote_req_bytes = json.dumps(vote_req, separators=(",", ":")).encode("utf-8")

    payload = {
        "request_id": request_id,
        "vote_request_hash": vote_req_hash,
        "coordinator_signature": coord_sig,
        "vote_request_payload": vote_req_bytes,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_VOTE_REQUEST, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_vote_request.json",
        "commit_vote_request",
        state,
        tx,
    )


# --- commit_selection_commitment specs ---


def test_commit_selection_commitment(state_test_group) -> None:
    state = _base_state()
    sender = ALICE

    # For this type, the daemon only checks SHA3-256(raw_bytes) == id.
    # No JSON deserialization, no signature verification.
    commitment_payload = b"selection-commitment-test-data-v1"
    commitment_id = hashlib.sha3_256(commitment_payload).digest()

    payload = {
        "request_id": _hash(62),
        "selection_commitment_id": commitment_id,
        "selection_commitment_payload": commitment_payload,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_SELECTION_COMMITMENT, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_selection_commitment.json",
        "commit_selection_commitment",
        state,
        tx,
    )


# --- commit_juror_vote specs ---


def test_commit_juror_vote(state_test_group) -> None:
    state = _base_state()
    sender = ALICE

    request_id = _hash(62)

    # Build JurorVote JSON matching Rust's serde(rename_all = "camelCase").
    # juror_pubkey must be a real compressed Ristretto point (BOB).
    juror_vote = {
        "type": "JurorVote",
        "version": 1,
        "requestId": request_id.hex(),
        "chainId": CHAIN_ID_DEVNET,
        "escrowId": _hash(60).hex(),
        "escrowHash": _hash(70).hex(),
        "disputeId": _hash(61).hex(),
        "round": 1,
        "disputeOpenHeight": 100,
        "committeeId": _hash(71).hex(),
        "selectionBlock": 200,
        "selectionCommitmentId": _hash(75).hex(),
        "arbitrationOpenHash": _hash(63).hex(),
        "voteRequestHash": _hash(64).hex(),
        "evidenceHash": _hash(73).hex(),
        "evidenceManifestHash": _hash(74).hex(),
        "selectedJurorsHash": _hash(76).hex(),
        "committeePolicyHash": _hash(72).hex(),
        "jurorPubkey": BOB.hex(),
        "jurorAccount": "juror-account",
        "vote": "pay",
        "votedAt": 1700050000,
        "signature": "00" * 64,  # placeholder replaced below
    }

    vote_hash = _canonical_hash_without_sig(juror_vote)
    juror_sig = bytes(tos_signer.sign_data(vote_hash, 3))  # BOB = seed 3
    juror_vote["signature"] = juror_sig.hex()

    vote_bytes = json.dumps(juror_vote, separators=(",", ":")).encode("utf-8")

    payload = {
        "request_id": request_id,
        "juror_pubkey": BOB,
        "vote_hash": vote_hash,
        "juror_signature": juror_sig,
        "vote_payload": vote_bytes,
    }
    tx = _mk_arb_tx(sender, nonce=5, tx_type=TransactionType.COMMIT_JUROR_VOTE, payload=payload, fee=100_000)
    state_test_group(
        "transactions/arbitration/commit_juror_vote.json",
        "commit_juror_vote",
        state,
        tx,
    )
