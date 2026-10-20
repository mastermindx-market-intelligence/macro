"""Producer registry: the only place a producer module is imported.

``produce_pack`` refuses any pack id without a registered producer — including
ids the contract knows but no lane has shipped yet, and ids outside
``specialist_pack_contract.PACK_IDS`` — with the same
``SpecialistPackError("no producer registered: <id>")`` refusal.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from . import pk01_debt, pk02_sbc, pk06_leases
from .base import PackInput, PackProducer, SpecialistPackError, produce_pack_result

_PRODUCER_MODULES = (pk01_debt, pk02_sbc, pk06_leases)


def _build() -> Mapping[str, PackProducer]:
    table: dict[str, PackProducer] = {}
    for module in _PRODUCER_MODULES:
        producer = module.PRODUCER
        pack_id = producer.spec.pack_id
        if pack_id in table:
            raise SpecialistPackError(f"duplicate producer registration: {pack_id}")
        table[pack_id] = producer
    return MappingProxyType(table)


PACK_PRODUCERS: Mapping[str, PackProducer] = _build()


def produce_pack(pack_id: str, pack_input: PackInput) -> dict:
    """Produce one pack result through the registered producer."""
    producer = PACK_PRODUCERS.get(pack_id)
    if producer is None:
        raise SpecialistPackError(f"no producer registered: {pack_id}")
    return produce_pack_result(producer, pack_input)


def registered_pack_ids() -> tuple[str, ...]:
    return tuple(sorted(PACK_PRODUCERS))


__all__ = [
    "PACK_PRODUCERS",
    "PackInput",
    "produce_pack",
    "registered_pack_ids",
]
