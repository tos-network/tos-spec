"""Core types for TOS Python specs.

This repo intentionally tracks only the *core* transaction surface currently
implemented in `~/tos`:
Transfers, Burn, MultiSig, InvokeContract, DeployContract, Energy,
AgentAccount, UNO/Shield/Unshield transfers, and RegisterName.
"""

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
    AGENT_ACCOUNT = "agent_account"
    UNO_TRANSFERS = "uno_transfers"
    SHIELD_TRANSFERS = "shield_transfers"
    UNSHIELD_TRANSFERS = "unshield_transfers"
    REGISTER_NAME = "register_name"


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


# --- Contract ---


@dataclass
class ContractState:
    deployer: bytes
    module_hash: bytes
    module: bytes = b""
    storage: dict[bytes, bytes] = field(default_factory=dict)


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
    # Internal state used by the multisig tx rules. Not part of conformance post_state.
    multisig_configs: dict[bytes, MultisigConfig] = field(default_factory=dict)
    agent_accounts: dict[bytes, AgentAccountMeta] = field(default_factory=dict)
    tns_names: dict[str, TnsRecord] = field(default_factory=dict)
    tns_by_owner: dict[bytes, str] = field(default_factory=dict)
    contracts: dict[bytes, ContractState] = field(default_factory=dict)
    energy_resources: dict[bytes, EnergyResource] = field(default_factory=dict)
