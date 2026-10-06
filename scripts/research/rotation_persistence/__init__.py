"""Research-only leadership persistence measurement package.

This package reads existing point-in-time published theme snapshots.  It has no
network, production writer, signal, rank, gate, sizing, or trading authority.
"""

from .contracts import AUTHORITY, ContractError

__all__ = ["AUTHORITY", "ContractError"]
