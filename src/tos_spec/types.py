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


# --- Escrow domain state ---


class EscrowStatus(Enum):
    CREATED = "created"
    FUNDED = "funded"
    PENDING_RELEASE = "pending_release"
    CHALLENGED = "challenged"
    RELEASED = "released"
    REFUNDED = "refunded"
    RESOLVED = "resolved"
    EXPIRED = "expired"


@dataclass
class ArbitrationConfig:
    mode: str = "single"  # "none", "single", "committee", "dao-governance"
    arbiters: list[bytes] = field(default_factory=list)
    threshold: int | None = None
    fee_amount: int = 0
    allow_appeal: bool = False


@dataclass
class DisputeInfo:
    initiator: bytes = field(default_factory=lambda: bytes(32))
    reason: str = ""
    evidence_hash: bytes | None = None
    disputed_at: int = 0
    deadline: int = 0


@dataclass
class EscrowAccount:
    id: bytes
    task_id: str
    payer: bytes
    payee: bytes
    amount: int
    total_amount: int
    released_amount: int = 0
    refunded_amount: int = 0
    challenge_deposit: int = 0
    asset: bytes = field(default_factory=lambda: bytes(32))
    status: EscrowStatus = EscrowStatus.CREATED
    timeout_blocks: int = 0
    challenge_window: int = 0
    challenge_deposit_bps: int = 0
    optimistic_release: bool = False
    created_at: int = 0
    updated_at: int = 0
    timeout_at: int = 0
    arbitration_config: ArbitrationConfig | None = None
    release_requested_at: int | None = None
    pending_release_amount: int | None = None
    dispute: DisputeInfo | None = None
    dispute_id: bytes | None = None
    dispute_round: int | None = None


# --- Arbiter domain state ---


class ArbiterStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXITING = "exiting"
    REMOVED = "removed"


@dataclass
class ArbiterAccount:
    public_key: bytes
    name: str
    status: ArbiterStatus = ArbiterStatus.ACTIVE
    expertise: list[int] = field(default_factory=list)
    stake_amount: int = 0
    fee_basis_points: int = 0
    min_escrow_value: int = 0
    max_escrow_value: int = 0
    reputation_score: int = 0
    total_cases: int = 0
    active_cases: int = 0
    registered_at: int = 0
    total_slashed: int = 0


# --- Multisig ---


@dataclass
class MultisigConfig:
    threshold: int
    participants: list[bytes]


# --- Agent Account ---


@dataclass
class AgentAccountMeta:
    owner: bytes
    controller: bytes
    policy_hash: bytes
    status: int = 0
    energy_pool: Optional[bytes] = None
    session_key_root: Optional[bytes] = None


# --- TNS (Name Service) ---


@dataclass
class TnsRecord:
    name: str
    owner: bytes
    registered_at: int = 0


# --- KYC ---


class KycStatus(Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


@dataclass
class KycData:
    level: int
    status: KycStatus = KycStatus.ACTIVE
    verified_at: int = 0
    data_hash: bytes = field(default_factory=lambda: bytes(32))
    committee_id: bytes = field(default_factory=lambda: bytes(32))


# --- Committee ---


@dataclass
class CommitteeMember:
    public_key: bytes
    name: str = ""
    role: int = 0


@dataclass
class Committee:
    id: bytes
    name: str = ""
    region: int = 0
    members: list[CommitteeMember] = field(default_factory=list)
    threshold: int = 0
    kyc_threshold: int = 0
    max_kyc_level: int = 0
    parent_id: bytes | None = None


# --- Referral ---


@dataclass
class ReferralBinding:
    referee: bytes
    referrer: bytes


# --- Contract ---


@dataclass
class ContractState:
    deployer: bytes
    module_hash: bytes
    storage: dict[bytes, bytes] = field(default_factory=dict)


# --- Arbitration Commits ---


@dataclass
class ArbitrationCommit:
    sender: bytes
    payload_hash: bytes
    data: bytes = b""


# --- Energy domain state ---


@dataclass
class FreezeRecord:
    amount: int
    energy_gained: int
    freeze_height: int = 0
    unlock_height: int = 0


@dataclass
class DelegatedFreezeRecord:
    delegatee: bytes
    amount: int
    energy_gained: int
    freeze_height: int = 0
    unlock_height: int = 0


@dataclass
class PendingUnfreeze:
    amount: int
    from_delegation: bool = False
    expire_height: int = 0


@dataclass
class EnergyResource:
    freeze_records: list[FreezeRecord] = field(default_factory=list)
    delegated_records: list[DelegatedFreezeRecord] = field(default_factory=list)
    pending_unfreezes: list[PendingUnfreeze] = field(default_factory=list)
    frozen_tos: int = 0
    energy: int = 0


# --- ChainState (expanded) ---


@dataclass
class ChainState:
    accounts: dict[bytes, AccountState] = field(default_factory=dict)
    global_state: GlobalState = field(default_factory=GlobalState)
    network_chain_id: int = 0
    escrows: dict[bytes, EscrowAccount] = field(default_factory=dict)
    arbiters: dict[bytes, ArbiterAccount] = field(default_factory=dict)
    multisig_configs: dict[bytes, MultisigConfig] = field(default_factory=dict)
    agent_accounts: dict[bytes, AgentAccountMeta] = field(default_factory=dict)
    tns_names: dict[str, TnsRecord] = field(default_factory=dict)
    tns_by_owner: dict[bytes, str] = field(default_factory=dict)
    kyc_data: dict[bytes, KycData] = field(default_factory=dict)
    committees: dict[bytes, Committee] = field(default_factory=dict)
    referrals: dict[bytes, bytes] = field(default_factory=dict)
    contracts: dict[bytes, ContractState] = field(default_factory=dict)
    arbitration_commits: dict[bytes, ArbitrationCommit] = field(default_factory=dict)
    energy_resources: dict[bytes, EnergyResource] = field(default_factory=dict)
    # Raw commit data lists for conformance pre_state loading
    arbitration_commit_opens: list = field(default_factory=list)
    arbitration_commit_vote_requests: list = field(default_factory=list)
    arbitration_commit_selections: list = field(default_factory=list)
