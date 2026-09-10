"""Kodierung der CUKTECH-Protokollschalter (PIID 21)."""
from __future__ import annotations
from .const import PROTOCOL_BITS


def decode_protocol_switches(value: int | None) -> dict[str, dict[str, bool]]:
    try:
        v = int(value or 0)
    except (TypeError, ValueError):
        v = 0
    return {
        port: {proto: bool(v & (1 << bit)) for proto, bit in protos.items()}
        for port, protos in PROTOCOL_BITS.items()
    }


def _c1c2_flags(ps: dict | None) -> int:
    if not ps:
        return 0
    v = 0x08
    if ps.get("pd"):
        v |= 0x01
    if ps.get("pps"):
        v |= 0x02
    if ps.get("ufcs"):
        v |= 0x04
    return v


def _c3a_flags(ps: dict | None) -> int:
    if not ps:
        return 0
    v = 0
    if ps.get("ufcs"):
        v |= 0x01
    if ps.get("scp"):
        v |= 0x02
    return v


def encode_protocol_switches(switches: dict) -> int:
    c1 = _c1c2_flags(switches.get("c1"))
    c2 = _c1c2_flags(switches.get("c2"))
    c3 = _c3a_flags(switches.get("c3"))
    a = _c3a_flags(switches.get("a"))
    return (a << 24) | (c3 << 16) | (c2 << 8) | c1
