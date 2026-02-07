"""Privacy transaction spec stubs (UNO/Shield/Unshield)."""

from __future__ import annotations

from ..errors import ErrorCode, SpecError
from ..types import ChainState, Transaction


def verify(state: ChainState, tx: Transaction) -> None:
    raise SpecError(ErrorCode.INVALID_FORMAT, "privacy transactions not supported")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    raise SpecError(ErrorCode.INVALID_FORMAT, "privacy transactions not supported")
