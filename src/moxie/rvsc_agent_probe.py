from __future__ import annotations

from typing import Literal

__all__ = ["delivery_identity"]


def delivery_identity() -> Literal["RVSC_AA002_DANIEL_DELIVERED"]:
    """Return the exact delivery marker for RVSC-AA-002-DANIEL-DELIVERY."""
    return "RVSC_AA002_DANIEL_DELIVERED"
