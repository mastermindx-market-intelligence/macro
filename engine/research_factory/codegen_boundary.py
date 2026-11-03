"""Keep reserved codegen metadata out of the existing RF-16 factory paths.

This is a bounded metadata fence, not a code detector or an execution sandbox.
It grants no admission and never imports, evaluates or loads candidate content.
"""
from __future__ import annotations


_RESERVED_KEYS = frozenset({
    "codegen_manifest", "codegen_manifest_ref", "codegen_contract",
    "codegen_protocol_ref",
})
_RESERVED_VALUES = frozenset({"code_candidate", "research_codegen"})
_RESERVED_PREFIXES = ("research_codegen.", "rf-codegen-")
_MAX_NODES = 4096


def codegen_refusal(payload: object) -> str | None:
    """Return a fixed refusal for reserved metadata or an uninspectable payload.

    Exact built-in JSON containers avoid executing object hooks. A bounded walk
    also handles malformed in-memory cycles without recursion or unbounded work.
    Legacy inert acyclic JSON metadata within the inspection budget and without
    reserved markers retains its existing route.
    """
    pending = [(payload, False)]
    active: set[int] = set()
    visited = 0
    while pending:
        value, leaving = pending.pop()
        if leaving:
            active.remove(id(value))
            continue
        visited += 1
        if visited > _MAX_NODES:
            return "RF-16: candidate metadata exceeds the bounded codegen inspection limit"
        if type(value) is str:
            if value in _RESERVED_VALUES or value.startswith(_RESERVED_PREFIXES):
                return "RF-16: code-candidate generation and execution are not admitted"
        elif type(value) is dict or type(value) is list:
            identity = id(value)
            if identity in active:
                return "RF-16: candidate metadata must be an acyclic JSON tree"
            active.add(identity)
            pending.append((value, True))
            child_count = len(value) * (2 if type(value) is dict else 1)
            if child_count + len(pending) + visited > _MAX_NODES:
                return "RF-16: candidate metadata exceeds the bounded codegen inspection limit"
            if type(value) is dict:
                if any(type(key) is not str for key in value):
                    return "RF-16: candidate metadata keys must be exact strings"
                if _RESERVED_KEYS.intersection(value):
                    return "RF-16: code-candidate generation and execution are not admitted"
                children = [*value.keys(), *value.values()]
            else:
                children = value
            pending.extend((child, False) for child in children)
        elif value is not None and type(value) not in (bool, int, float):
            return "RF-16: candidate metadata must contain only inert JSON values"
    return None
