"""TOS Python spec error codes and exceptions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ErrorCategory(IntEnum):
    SUCCESS = 0x00
    VALIDATION = 0x01
    AUTHORIZATION = 0x02
    RESOURCE = 0x03
    STATE = 0x04
    CONTRACT = 0x05
    NETWORK = 0x06
    INTERNAL = 0xFF


class ErrorCode(IntEnum):
    # Success
    SUCCESS = 0x0000

    # Validation
    INVALID_FORMAT = 0x0100
    INVALID_VERSION = 0x0101
    INVALID_TYPE = 0x0102
    INVALID_SIGNATURE = 0x0103
    INVALID_TIMESTAMP = 0x0104
    INVALID_AMOUNT = 0x0105
    INVALID_ADDRESS = 0x0106
    INVALID_PAYLOAD = 0x0107
    NONCE_TOO_LOW = 0x0110
    NONCE_TOO_HIGH = 0x0111
    NONCE_DUPLICATE = 0x0112

    # Authorization
    UNAUTHORIZED = 0x0200
    KYC_REQUIRED = 0x0201
    KYC_LEVEL_TOO_LOW = 0x0202
    NOT_OWNER = 0x0203
    NOT_COMMITTEE = 0x0204
    NOT_ARBITRATOR = 0x0205
    MULTISIG_THRESHOLD = 0x0206

    # Resource
    INSUFFICIENT_BALANCE = 0x0300
    INSUFFICIENT_FEE = 0x0301
    INSUFFICIENT_ENERGY = 0x0302
    INSUFFICIENT_FROZEN = 0x0303
    OVERFLOW = 0x0304
    UNDERFLOW = 0x0305

    # State
    ACCOUNT_NOT_FOUND = 0x0400
    ACCOUNT_EXISTS = 0x0401
    ESCROW_NOT_FOUND = 0x0402
    ESCROW_WRONG_STATE = 0x0403
    DOMAIN_NOT_FOUND = 0x0404
    DOMAIN_EXISTS = 0x0405
    DOMAIN_EXPIRED = 0x0406
    DELEGATION_NOT_FOUND = 0x0407
    DELEGATION_EXISTS = 0x0408
    SELF_OPERATION = 0x0409

    # Contract
    CONTRACT_NOT_FOUND = 0x0500
    CONTRACT_REVERT = 0x0501
    OUT_OF_CU = 0x0502
    INVALID_OPCODE = 0x0503
    STACK_OVERFLOW = 0x0504
    STACK_UNDERFLOW = 0x0505
    MEMORY_LIMIT = 0x0506

    # Network
    BLOCK_NOT_FOUND = 0x0600
    INVALID_PARENT = 0x0601
    INVALID_DIFFICULTY = 0x0602
    INVALID_POW = 0x0603
    TIMESTAMP_TOO_OLD = 0x0604
    TIMESTAMP_TOO_NEW = 0x0605
    EXPECTED_TIPS = 0x0606
    INVALID_TIPS_COUNT = 0x0607
    INVALID_TIPS_NOT_FOUND = 0x0608
    INVALID_TIPS_DIFFICULTY = 0x0609
    INVALID_REACHABILITY = 0x060A
    MISSING_VRF_DATA = 0x060B
    INVALID_VRF_DATA = 0x060C
    INVALID_BLOCK_VERSION = 0x060D
    INVALID_BLOCK_HEIGHT = 0x060E

    # Internal
    INTERNAL_ERROR = 0xFF00
    NOT_IMPLEMENTED = 0xFF01
    UNKNOWN = 0xFFFF


@dataclass(frozen=True)
class SpecError(Exception):
    code: ErrorCode
    message: str

    def __str__(self) -> str:
        return f"{self.code.name}({self.code:#06x}): {self.message}"


# Allow Python's Exception machinery to set __traceback__/__context__/__cause__
# while keeping dataclass fields frozen (Python 3.13 contextlib compat).
_EXCEPTION_ATTRS = frozenset(("__traceback__", "__context__", "__cause__"))
_frozen_setattr = SpecError.__setattr__


def _spec_error_setattr(self: SpecError, name: str, value: object) -> None:
    if name in _EXCEPTION_ATTRS:
        object.__setattr__(self, name, value)
    else:
        _frozen_setattr(self, name, value)


SpecError.__setattr__ = _spec_error_setattr  # type: ignore[method-assign]


def ok() -> None:
    return None


def err(code: ErrorCode, message: str) -> SpecError:
    return SpecError(code=code, message=message)
