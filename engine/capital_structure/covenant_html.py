"""Bounded SEC HTML text view with exact retained-byte provenance.

This is a parsing view, not a browser renderer. Known deleted/hidden subtrees
are excluded. A caller may assert a source span only for literal retained bytes;
decoded entities, inserted separators and markup-spanning values fail closed.
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re

_VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
_BLOCK = frozenset('address article aside blockquote br div dl dt dd footer h1 h2 h3 h4 h5 h6 header hr li main ol p pre section table tr td th ul'.split())
_HIDDEN = frozenset(('head', 'script', 'style', 'del', 's', 'strike'))


@dataclass(frozen=True)
class VisibleSource:
    text: str
    raw: bytes
    # visible start/end; raw byte start/end, or None for generated text.
    chunks: tuple[tuple[int, int, int | None, int | None], ...]

    def exact_byte_span(self, start: int, end: int) -> tuple[int, int]:
        if not (type(start) is int and type(end) is int and 0 <= start < end <= len(self.text)):
            raise ValueError('invalid visible-text range')
        covered = [c for c in self.chunks if c[1] > start and c[0] < end]
        if not covered or any(c[2] is None for c in covered):
            raise ValueError('range contains decoded or generated text')
        first, last = covered[0], covered[-1]
        a = first[2] + len(self.text[first[0]:start].encode('utf-8'))
        b = last[2] + len(self.text[last[0]:end].encode('utf-8'))
        if self.raw[a:b] != self.text[start:end].encode('utf-8'):
            raise ValueError('range is not literal contiguous source bytes')
        return a, b


class _View(HTMLParser):
    def __init__(self, raw: bytes, start: int = 0, end: int | None = None):
        super().__init__(convert_charrefs=False)
        self.raw = raw
        self.source = raw[start:end].decode('utf-8', errors='strict')
        self.byte_offsets = array('I', [start])
        self.lines = [0]
        for i, c in enumerate(self.source):
            self.byte_offsets.append(self.byte_offsets[-1] + len(c.encode('utf-8')))
            if c == '\n':
                self.lines.append(i + 1)
        self.stack: list[tuple[str, bool]] = []
        self.parts: list[str] = []
        self.chunks: list[tuple[int, int, int | None, int | None]] = []
        self.length = 0
        self.tags = 0

    @property
    def hidden(self):
        return bool(self.stack and self.stack[-1][1])

    def append(self, value: str, literal: bool = False):
        if self.hidden or not value:
            return
        a = b = None
        if literal:
            line, col = self.getpos()
            pos = self.lines[line - 1] + col
            a, b = self.byte_offsets[pos], self.byte_offsets[pos + len(value)]
            if self.raw[a:b] != value.encode('utf-8'):
                raise ValueError('HTML parser offset mismatch')
        self.parts.append(value)
        self.chunks.append((self.length, self.length + len(value), a, b))
        self.length += len(value)

    def handle_starttag(self, tag, attrs):
        self.tags += 1
        if self.tags > 100_000:
            raise ValueError('HTML tag limit exceeded')
        attrs = dict(attrs)
        style = attrs.get('style') or ''
        hidden = self.hidden or tag in _HIDDEN or 'hidden' in attrs or bool(re.search(
            r'(?:^|;)\s*(?:display\s*:\s*none\b|visibility\s*:\s*hidden\b|text-decoration(?:-line)?\s*:[^;]*\bline-through\b)', style, re.I))
        if tag in _BLOCK and not hidden:
            self.append('\n')
        if tag not in _VOID:
            self.stack.append((tag, hidden))
            if len(self.stack) > 128:
                raise ValueError('HTML depth limit exceeded')

    def handle_endtag(self, tag):
        if tag in _VOID:
            return
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError('unsupported malformed HTML nesting')
        was_hidden = self.hidden
        self.stack.pop()
        if tag in _BLOCK and not was_hidden:
            self.append('\n')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_data(self, data):
        self.append(data, literal=True)

    def handle_entityref(self, name):
        self.append(unescape('&' + name + ';'))

    def handle_charref(self, name):
        self.append(unescape('&#' + name + ';'))


def visible_html(raw: bytes) -> VisibleSource:
    if not isinstance(raw, bytes) or len(raw) > 2 * 1024 * 1024:
        raise ValueError('HTML input must be bytes within 2 MiB')
    # Native child-document retention includes these SEC SGML metadata lines;
    # they are not nested HTML elements. Keep offsets against the full object.
    header = re.match(
        rb'\s*<TYPE>[^\r\n]+\r?\n<SEQUENCE>[^\r\n]+\r?\n'
        rb'<FILENAME>[^\r\n]+\r?\n(?:<DESCRIPTION>[^\r\n]*\r?\n)?\s*<TEXT>',
        raw, re.I)
    if header:
        closing = re.search(rb'</TEXT>\s*\Z', raw, re.I)
        if not closing or len(re.findall(rb'</?TEXT>', raw, re.I)) != 2:
            raise ValueError('invalid SEC child-document envelope')
        parser = _View(raw, header.end(), closing.start())
    else:
        parser = _View(raw)
    parser.feed(parser.source)
    parser.close()
    if parser.stack:
        raise ValueError('unterminated HTML nesting')
    return VisibleSource(''.join(parser.parts), raw, tuple(parser.chunks))
