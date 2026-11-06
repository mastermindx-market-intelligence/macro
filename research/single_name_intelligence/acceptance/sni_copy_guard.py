"""SNI-local DRAFT lexical copy guard for acceptance rows A14 and A30.

This module CONSUMES owner-supplied markdown text under
research/single_name_intelligence/. It does not mint, derive, or guess
canonical HK/US issuer or security identifiers; unknown identity stays
UNRESOLVED / null. Identity ids are caller-supplied opaque strings owned
by Stock Identity / Data OS.

It does not re-implement Data OS identity, Company Event/Earnings, FIF,
Capital Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation. It does not feed a ranker, gate, sizer, signal,
escalation, or trade path. rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay false;
refuse_nonfalse_authority raises if a caller tries to set any of them true.

A14: holdings / southbound / options OI (and the rest of the subject list)
plus a live-flow or intent label in the same sentence is a finding.
A30: a failed-state token plus a forecast-success token in the same
sentence is a finding. Matches use word boundaries. This is a lexical
check, never a forecast, never causal, never a claim of news impact.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping, NamedTuple, Sequence

_MODULE_DIR = Path(__file__).resolve().parent
SNI_ROOT = _MODULE_DIR.parent
REPO_ROOT = SNI_ROOT.parent.parent

AUTHORITY_FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)
AUTHORITY_FLAGS = {name: False for name in AUTHORITY_FLAG_NAMES}

RULE_A14 = "A14"
RULE_A30 = "A30"
EXCERPT_LIMIT = 160

# Subject terms (A14). Word-boundary, case-insensitive.
A14_SUBJECT_TERMS: tuple[str, ...] = (
    "holdings",
    "southbound",
    "northbound",
    "stock connect",
    "short interest",
    "short-interest",
    "CCASS",
    "open interest",
    "options OI",
    "OI",
    "13F",
    "shareholding",
)

# Intent / live-flow terms (A14). "positioning" alone is not intent;
# only "positioning for" / "positioned for" count.
A14_INTENT_TERMS: tuple[str, ...] = (
    "smart money",
    "accumulating",
    "accumulation",
    "net buying",
    "net selling",
    "inflow",
    "inflows",
    "outflow",
    "outflows",
    "betting on",
    "bets on",
    "positioning for",
    "positioned for",
    "signals intent",
    "conviction",
    "whale",
    "whales",
    "loading up",
    "dumping",
)

# Failed-state terms (A30).
A30_FAILED_STATE_TERMS: tuple[str, ...] = (
    "NO-GO",
    "failed",
    "retired",
    "RETIRED-CONTAMINATED",
    "contaminated",
    "NON-CONFIRMATORY",
    "BLOCKED-AS-EVIDENCE",
    "NOT SUPPORTED",
    "DESCRIPTIVE_ONLY",
)

# Forecast-success terms (A30). "works" is a whole word: it does not
# match inside "workspace".
A30_SUCCESS_TERMS: tuple[str, ...] = (
    "predicts",
    "predictive",
    "predicted correctly",
    "outperform",
    "outperforms",
    "outperformed",
    "beats",
    "beat the",
    "proven",
    "edge",
    "alpha",
    "winning",
    "works",
    "profitable",
    "forecast skill",
)

# Ban-stating negators. A sentence is tolerated when one of these appears
# in the same sentence BEFORE the intent term (A14) or success term (A30).
# Keep this list simple. Blind spot: a negator anywhere earlier in a long
# sentence hides a later plain claim. "no" does not match the NO- of
# NO-GO; "not" does not match the NOT of NOT SUPPORTED.
NEGATORS: tuple[str, ...] = (
    "must not",
    "does not",
    "do not",
    "is not",
    "are not",
    "cannot",
    "never",
    "without",
    "forbidden",
    "forbid",
    "banned",
    "ban",
    "not",
    "no",
)


class Finding(NamedTuple):
    path: str
    line: int
    rule: str
    sentence_excerpt: str
    subject_term: str
    claim_term: str


class AllowlistEntry(NamedTuple):
    path: str
    line: int
    rule: str
    exact_excerpt_substring: str
    justification: str


# False-positive suppressions. An entry matches only when path, line, and
# rule agree AND the substring occurs in the finding's sentence excerpt.
# Empty: the BASE tree's lexical A30 hits are pinned as KNOWN_FINDINGS in
# the test module (true collocations on sealed reports; not edited here).
ALLOWLIST: tuple[AllowlistEntry, ...] = ()


def refuse_nonfalse_authority(flags: Mapping[str, object]) -> None:
    """Raise if a caller tries to set any authority flag true."""
    for name in AUTHORITY_FLAG_NAMES:
        if flags.get(name) is True:
            raise ValueError(
                f"{name} must stay false; the SNI copy guard does not feed "
                "a ranker, gate, sizer, signal, escalation, or trade path"
            )


def _phrase_re(phrase: str) -> re.Pattern[str]:
    body = r"\s+".join(re.escape(part) for part in phrase.split())
    return re.compile(rf"\b{body}\b", re.IGNORECASE)


def _negator_re(phrase: str) -> re.Pattern[str]:
    lowered = phrase.lower()
    if lowered == "no":
        # Do not treat the NO- prefix of NO-GO as the negator "no".
        return re.compile(r"\bno(?!-go\b)\b", re.IGNORECASE)
    if lowered == "not":
        # Do not treat NOT SUPPORTED as the negator "not".
        return re.compile(r"\bnot\b(?!\s+supported\b)", re.IGNORECASE)
    return _phrase_re(phrase)


_A14_SUBJECT_RX = tuple((t, _phrase_re(t)) for t in A14_SUBJECT_TERMS)
_A14_INTENT_RX = tuple((t, _phrase_re(t)) for t in A14_INTENT_TERMS)
_A30_FAILED_RX = tuple((t, _phrase_re(t)) for t in A30_FAILED_STATE_TERMS)
_A30_SUCCESS_RX = tuple((t, _phrase_re(t)) for t in A30_SUCCESS_TERMS)
_NEGATOR_RX = tuple((t, _negator_re(t)) for t in NEGATORS)


def _first_match(
    text: str, pairs: Sequence[tuple[str, re.Pattern[str]]]
) -> tuple[int, int, str] | None:
    """Earliest match; longest term wins on a tied start."""
    best: tuple[int, int, str] | None = None
    for term, rx in pairs:
        m = rx.search(text)
        if m is None:
            continue
        cand = (m.start(), m.end(), term)
        if best is None:
            best = cand
            continue
        if cand[0] < best[0] or (
            cand[0] == best[0] and (cand[1] - cand[0]) > (best[1] - best[0])
        ):
            best = cand
    return best


def _negator_before(masked: str, claim_start: int) -> bool:
    for _term, rx in _NEGATOR_RX:
        for m in rx.finditer(masked):
            if m.start() < claim_start:
                return True
    return False


def mask_quoted(text: str) -> str:
    """Mask double quotes, curly quotes, and backtick spans with spaces.

    Reviews that quote banned copy in order to reject it do not fire.
    Inline code is still part of the sentence (not skipped); only the
    quoted span itself is masked. Unclosed openers are left as-is.
    """
    chars = list(text)
    n = len(chars)
    i = 0
    while i < n:
        ch = chars[i]
        closer = None
        if ch == '"':
            closer = '"'
        elif ch == "\u201c":
            closer = "\u201d"
        elif ch == "`":
            closer = "`"
        if closer is None:
            i += 1
            continue
        j = i + 1
        while j < n and chars[j] != closer:
            j += 1
        if j < n:
            for k in range(i, j + 1):
                chars[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(chars)


def _is_fence_line(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def split_sentences(text: str) -> list[tuple[int, str]]:
    """Split into (1-based start line, sentence) pairs.

    Split on `.`, `!`, `?` followed by whitespace, on blank lines, and on
    markdown table cell boundaries `|`. Fenced code blocks are skipped.
    Inline code is kept so table cells such as `engine/options_*.py` remain
    visible to the allowlist.
    """
    results: list[tuple[int, str]] = []
    buf: list[str] = []
    buf_start: int | None = None
    in_fence = False

    def flush() -> None:
        nonlocal buf, buf_start
        sentence = "".join(buf).strip()
        if sentence:
            assert buf_start is not None
            results.append((buf_start, sentence))
        buf = []
        buf_start = None

    def add(ch: str, line_no: int) -> None:
        nonlocal buf_start
        if buf_start is None:
            buf_start = line_no
        buf.append(ch)

    for line_no, line in enumerate(text.splitlines(), start=1):
        if _is_fence_line(line):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line.strip():
            flush()
            continue
        i = 0
        length = len(line)
        while i < length:
            ch = line[i]
            if ch == "|":
                flush()
                i += 1
                continue
            nxt = line[i + 1] if i + 1 < length else "\n"
            if ch in ".!?" and nxt.isspace():
                add(ch, line_no)
                flush()
                i += 1
                continue
            add(ch, line_no)
            i += 1
        if buf:
            buf.append(" ")
    flush()
    return results


def _excerpt(sentence: str) -> str:
    collapsed = " ".join(sentence.split())
    return collapsed[:EXCERPT_LIMIT]


def rule_a14_flow_intent(sentence: str) -> tuple[str, str] | None:
    """Return (subject_term, intent_term) when the sentence violates A14."""
    masked = mask_quoted(sentence)
    subject = _first_match(masked, _A14_SUBJECT_RX)
    intent = _first_match(masked, _A14_INTENT_RX)
    if subject is None or intent is None:
        return None
    if _negator_before(masked, intent[0]):
        return None
    return subject[2], intent[2]


def rule_a30_forecast_success(sentence: str) -> tuple[str, str] | None:
    """Return (failed-state term, success term) when the sentence violates A30."""
    masked = mask_quoted(sentence)
    failed = _first_match(masked, _A30_FAILED_RX)
    success = _first_match(masked, _A30_SUCCESS_RX)
    if failed is None or success is None:
        return None
    if _negator_before(masked, success[0]):
        return None
    return failed[2], success[2]


def check_text(text: str, path: str, **kwargs: object) -> list[Finding]:
    """Return ordered A14 then A30 findings for each sentence in text."""
    refuse_nonfalse_authority(kwargs)
    findings: list[Finding] = []
    for line_no, sentence in split_sentences(text):
        excerpt = _excerpt(sentence)
        a14 = rule_a14_flow_intent(sentence)
        if a14 is not None:
            findings.append(
                Finding(path, line_no, RULE_A14, excerpt, a14[0], a14[1])
            )
        a30 = rule_a30_forecast_success(sentence)
        if a30 is not None:
            findings.append(
                Finding(path, line_no, RULE_A30, excerpt, a30[0], a30[1])
            )
    return findings


def is_allowlisted(finding: Finding) -> bool:
    """True when an ALLOWLIST entry matches path, line, rule, and substring."""
    for entry in ALLOWLIST:
        if (
            finding.path == entry.path
            and finding.line == entry.line
            and finding.rule == entry.rule
            and entry.exact_excerpt_substring in finding.sentence_excerpt
        ):
            return True
    return False


def unallowlisted(findings: Iterable[Finding]) -> list[Finding]:
    return [f for f in findings if not is_allowlisted(f)]


def _require_sni_md(path: Path | str) -> Path:
    resolved = Path(path).resolve()
    sni = SNI_ROOT.resolve()
    try:
        resolved.relative_to(sni)
    except ValueError as exc:
        raise ValueError(
            f"scan_paths refuses path outside the SNI markdown tree: {path}"
        ) from exc
    if resolved.suffix.lower() != ".md":
        raise ValueError(f"scan_paths refuses non-markdown path: {path}")
    return resolved


def scan_paths(
    paths: Iterable[Path | str], **kwargs: object
) -> list[Finding]:
    """Read the given files and return ordered findings.

    Refuses (ValueError) a path outside research/single_name_intelligence/
    or a path that is not a .md file. Does not glob, does not walk, does
    not read anything else.
    """
    refuse_nonfalse_authority(kwargs)
    findings: list[Finding] = []
    for raw in paths:
        resolved = _require_sni_md(raw)
        rel = resolved.relative_to(REPO_ROOT).as_posix()
        text = resolved.read_text(encoding="utf-8")
        findings.extend(check_text(text, rel))
    return findings
