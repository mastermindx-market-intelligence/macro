"""Project the existing site tokens without importing its global page styling.

Only the canonical sheet's top-level root/theme/language declarations are
eligible. The admin keeps its legacy dark tokens; a prefix lets its governed
stylesheet opt into canonical values without repainting unrelated pages.
There is no palette or filesystem access in this module.
"""
from __future__ import annotations

import re

_SELECTOR = re.compile(r'(?:\:root|html(?:\[data-(?:theme|lang)="(?:light|dark|en|zh)"\])+)\Z')
_PROPERTY = re.compile(r'--[A-Za-z_][A-Za-z0-9_-]*\Z')
_REFERENCE = re.compile(r'\bvar\(\s*(--[A-Za-z_][A-Za-z0-9_-]*)')


def _outside_strings(source: str, transform):
    """Strip comments and transform syntax, preserving quoted bytes literally."""
    parts = []
    start = 0
    i = 0
    while i < len(source):
        if source.startswith("/*", i):
            parts.append(transform(source[start:i]))
            end = source.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated theme comment")
            parts.append(" ")
            i = end + 2
            start = i
            continue
        if source[i] in "\"'":
            parts.append(transform(source[start:i]))
            quote = source[i]
            start = i
            i += 1
            while i < len(source):
                if source[i] == "\\":
                    i += 2
                    continue
                if source[i] == quote:
                    break
                i += 1
            else:
                raise ValueError("Unterminated theme string")
            i += 1
            parts.append(source[start:i])
            start = i
            continue
        i += 1
    parts.append(transform(source[start:]))
    return "".join(parts)


def _segments(source: str, delimiter: str):
    """Split CSS outside strings, comments and parentheses; preserve bytes."""
    start = 0
    quote = None
    parens = 0
    i = 0
    while i < len(source):
        c = source[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif source.startswith("/*", i):
            end = source.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated theme comment")
            i = end + 2
            continue
        elif c in "\"'":
            quote = c
        elif c == "(":
            parens += 1
        elif c == ")":
            parens -= 1
            if parens < 0:
                raise ValueError("Unbalanced theme value")
        elif c == delimiter and parens == 0:
            yield source[start:i]
            start = i + 1
        i += 1
    if quote or parens:
        raise ValueError("Unterminated theme value")
    yield source[start:]


def project_theme_tokens(source: str) -> str:
    """Return custom properties only, with names/references consistently prefixed.

    This deliberately supports the canonical sheet's current top-level token
    contract, not arbitrary nested CSS. A malformed selected block fails closed.
    Component-local tokens, imports, fonts and all ordinary declarations stay
    with their original stylesheets.
    """
    source = _outside_strings(source, lambda value: value)
    blocks = []
    start = 0
    opening = None
    depth = 0
    quote = None
    i = 0
    while i < len(source):
        c = source[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c == ";" and depth == 0:
            start = i + 1  # e.g. an @import, never part of a selector
        elif c == "{":
            if depth == 0:
                selector = source[start:i].strip()
                opening = i + 1
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("Unbalanced theme block")
            if depth == 0:
                if _SELECTOR.fullmatch(selector):
                    body = source[opening:i]
                    if "{" in body or "}" in body:
                        raise ValueError("Nested canonical token block")
                    declarations = []
                    for declaration in _segments(body, ";"):
                        if not declaration.strip():
                            continue
                        name, sep, value = declaration.partition(":")
                        name, value = name.strip(), value.strip()
                        if not sep:
                            raise ValueError("Invalid canonical token declaration")
                        if not name.startswith("--"):
                            continue
                        if not _PROPERTY.fullmatch(name) or not value:
                            raise ValueError("Invalid canonical token")
                        value = _outside_strings(value, lambda syntax: _REFERENCE.sub(
                            lambda m: "var(--admin-canonical-" + m[1][2:], syntax))
                        declarations.append(f"  --admin-canonical-{name[2:]}: {value};")
                    if declarations:
                        blocks.append(selector + " {\n" + "\n".join(declarations) + "\n}")
                start = i + 1
        i += 1
    if depth or quote:
        raise ValueError("Unterminated theme block")
    if not blocks or not blocks[0].startswith(":root "):
        raise ValueError("Canonical root tokens unavailable")
    return "/* Derived from templates/theme.css; edit that owner for token values. */\n" + "\n".join(blocks) + "\n"
