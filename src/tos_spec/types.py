"""Core types for TOS Python specs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional


class TxVersion(IntEnum):
    T1 = 0x01


class FeeType(IntEnum):
    TOS = 0x00
    ENERGY = 0x01
    UNO = 0x02


class TransactionType(Enum):
    TRANSFERS = "transfers"
    BURN = "burn"
    MULTISIG = "multisig"
    INVOKE_CONTRACT = "invoke_contract"
    DEPLOY_CONTRACT = "deploy_contract"
    ENERGY = "energy"
    BIND_REFERRER = "bind_referrer"
    BATCH_REFERRAL_REWARD = "batch_referral_reward"
    SET_KYC = "set_kyc"
    REVOKE_KYC = "revoke_kyc"
    RENEW_KYC = "renew_kyc"
    TRANSFER_KYC = "transfer_kyc"
    APPEAL_KYC = "appeal_kyc"
    BOOTSTRAP_COMMITTEE = "bootstrap_committee"
    REGISTER_COMMITTEE = "register_committee"
    UPDATE_COMMITTEE = "update_committee"
    EMERGENCY_SUSPEND = "emergency_suspend"
    AGENT_ACCOUNT = "agent_account"
    UNO_TRANSFERS = "uno_transfers"
    SHIELD_TRANSFERS = "shield_transfers"
    UNSHIELD_TRANSFERS = "unshield_transfers"
    REGISTER_NAME = "register_name"
    EPHEMERAL_MESSAGE = "ephemeral_message"
    CREATE_ESCROW = "create_escrow"
    DEPOSIT_ESCROW = "deposit_escrow"
    RELEASE_ESCROW = "release_escrow"
    REFUND_ESCROW = "refund_escrow"
    CHALLENGE_ESCROW = "challenge_escrow"
    DISPUTE_ESCROW = "dispute_escrow"
    APPEAL_ESCROW = "appeal_escrow"
    SUBMIT_VERDICT = "submit_verdict"
    SUBMIT_VERDICT_BY_JUROR = "submit_verdict_by_juror"
    COMMIT_ARBITRATION_OPEN = "commit_arbitration_open"
    COMMIT_VOTE_REQUEST = "commit_vote_request"
    COMMIT_SELECTION_COMMITMENT = "commit_selection_commitment"
    COMMIT_JUROR_VOTE = "commit_juror_vote"
    REGISTER_ARBITER = "register_arbiter"
    UPDATE_ARBITER = "update_arbiter"
    SLASH_ARBITER = "slash_arbiter"
    REQUEST_ARBITER_EXIT = "request_arbiter_exit"
    WITHDRAW_ARBITER_STAKE = "withdraw_arbiter_stake"
    CANCEL_ARBITER_EXIT = "cancel_arbiter_exit"


@dataclass
class FreezeDuration:
    days: int


@dataclass
class DelegationEntry:
    delegatee: bytes
    amount: int


@dataclass
class EnergyPayload:
    variant: str
    amount: Optional[int] = None
    duration: Optional[FreezeDuration] = None
    delegatees: Optional[list[DelegationEntry]] = None
    from_delegation: Optional[bool] = None
    record_index: Optional[int] = None
    delegatee_address: Optional[bytes] = None


@dataclass
class TransferPayload:
    asset: bytes
    destination: bytes
    amount: int
    extra_data: Optional[bytes] = None


@dataclass
class Transaction:
    version: TxVersion
    chain_id: int
    source: bytes
    tx_type: TransactionType
    payload: object
    fee: int
    fee_type: FeeType
    nonce: int
    source_commitments: List[bytes] = field(default_factory=list)
    range_proof: Optional[bytes] = None
    reference_hash: Optional[bytes] = None
    reference_topoheight: Optional[int] = None
    multisig: Optional["MultiSig"] = None
    signature: Optional[bytes] = None


@dataclass
class SignatureId:
    signer_id: int
    signature: bytes


@dataclass
class MultiSig:
    signatures: List[SignatureId]


@dataclass
class AccountState:
    address: bytes
    balance: int = 0
    nonce: int = 0
    frozen: int = 0
    energy: int = 0
    flags: int = 0
    data: bytes = b""


@dataclass
class GlobalState:
    total_supply: int = 0
    total_burned: int = 0
    total_energy: int = 0
    block_height: int = 0
    timestamp: int = 0


@dataclass
class ChainState:
    accounts: dict[bytes, AccountState] = field(default_factory=dict)
    global_state: GlobalState = field(default_factory=GlobalState)
    network_chain_id: int = 0
