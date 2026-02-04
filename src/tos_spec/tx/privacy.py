"""Privacy transaction spec stubs (UNO/Shield/Unshield)."""

from __future__ import annotations

from ..errors import ErrorCode, SpecError
from ..types import ChainState, Transaction


def verify(state: ChainState, tx: Transaction) -> None:
    raise SpecError(ErrorCode.NOT_IMPLEMENTED, "privacy.verify not implemented")


def apply(state: ChainState, tx: Transaction) -> ChainState:
    raise SpecError(ErrorCode.NOT_IMPLEMENTED, "privacy.apply not implemented")
