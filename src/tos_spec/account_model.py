"""Account model specification (from tck/specs/account-model.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional


# Constants (see tck/specs/account-model.md)
COIN_DECIMALS = 8
COIN_VALUE = 100_000_000
MAXIMUM_SUPPLY = 184_000_000 * COIN_VALUE
MAX_MULTISIG_PARTICIPANTS = 255
MAX_FREEZE_RECORDS = 32
MAX_PENDING_UNFREEZES = 32

NATIVE_TOS_ASSET = bytes(32)
UNO_ASSET = bytes(31) + b"\x01"


TopoHeight = int
Nonce = int


@dataclass
class Balance:
    amounts: Dict[bytes, int] = field(default_factory=dict)


@dataclass
class VersionedBalance:
    version: TopoHeight
    balance: Balance


@dataclass
class VersionedNonce:
    version: TopoHeight
    nonce: Nonce


@dataclass
class FreezeDuration:
    days: int


@dataclass
class FreezeRecord:
    amount: int
    duration: FreezeDuration
    freeze_topoheight: TopoHeight
    unlock_topoheight: TopoHeight
    energy_gained: int


@dataclass
class DelegatedFreezeRecord:
    delegator: bytes
    amount: int
    duration: FreezeDuration
    freeze_topoheight: TopoHeight
    unlock_topoheight: TopoHeight
    energy_gained: int


@dataclass
class PendingUnfreeze:
    amount: int
    unlock_topoheight: TopoHeight


@dataclass
class EnergyLease:
    delegator: bytes
    amount: int
    expiry_topoheight: TopoHeight


@dataclass
class EnergyResource:
    energy: int
    freeze_records: List[FreezeRecord] = field(default_factory=list)
    delegated_records: List[DelegatedFreezeRecord] = field(default_factory=list)
    pending_unfreezes: List[PendingUnfreeze] = field(default_factory=list)
    leases: List[EnergyLease] = field(default_factory=list)


@dataclass
class UnoBalance:
    ciphertext: bytes


@dataclass
class VersionedUnoBalance:
    version: TopoHeight
    balance: UnoBalance


@dataclass
class ExternalOwnedAccount:
    public_key: bytes
    balance: VersionedBalance
    nonce: VersionedNonce
    energy: Optional[EnergyResource] = None
    uno_balance: Optional[VersionedUnoBalance] = None


@dataclass
class ContractAccount:
    contract_hash: bytes
    module: bytes
    storage: Dict[bytes, bytes] = field(default_factory=dict)


@dataclass
class MultiSigAccount:
    threshold: int
    participants: List[bytes]


@dataclass
class AgentAccount:
    parent: bytes
    session_key: bytes
    permissions: int
    expiry: TopoHeight


class AccountModelErrorCode(IntEnum):
    INSUFFICIENT_BALANCE = 0x01
    INVALID_NONCE = 0x02
    ACCOUNT_NOT_FOUND = 0x03
    ACCOUNT_NOT_ACTIVE = 0x04
    BALANCE_OVERFLOW = 0x05
    ENERGY_EXHAUSTED = 0x06


@dataclass(frozen=True)
class AccountModelError(Exception):
    code: AccountModelErrorCode
    message: str

    def __str__(self) -> str:
        return f"{self.code.name}({self.code:#04x}): {self.message}"


def energy_from_freeze(amount_atomic: int, duration_days: int) -> int:
    """Energy = (TOS_amount / COIN_VALUE) * (2 * days)."""
    tos_amount = amount_atomic // COIN_VALUE
    return tos_amount * (2 * duration_days)


def apply_balance_change(balance: int, delta: int) -> int:
    """Apply +/- balance with u64 bounds."""
    new_balance = balance + delta
    if new_balance < 0:
        raise AccountModelError(AccountModelErrorCode.INSUFFICIENT_BALANCE, "negative balance")
    if new_balance > (1 << 64) - 1:
        raise AccountModelError(AccountModelErrorCode.BALANCE_OVERFLOW, "balance overflow")
    return new_balance


def apply_nonce_increment(nonce: int, increment: int = 1) -> int:
    new_nonce = nonce + increment
    if new_nonce > (1 << 64) - 1:
        raise AccountModelError(AccountModelErrorCode.INVALID_NONCE, "nonce overflow")
    return new_nonce


def create_eoa_from_transfer(public_key: bytes, amount: int, topoheight: TopoHeight) -> ExternalOwnedAccount:
    """Implicit account creation on first incoming transfer."""
    balance = VersionedBalance(version=topoheight, balance=Balance(amounts={NATIVE_TOS_ASSET: amount}))
    nonce = VersionedNonce(version=topoheight, nonce=0)
    return ExternalOwnedAccount(public_key=public_key, balance=balance, nonce=nonce)
