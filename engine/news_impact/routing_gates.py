"""Routing gates for the news-impact continuation draw (DEC:NEWS-IMPACT-CONTINUATION-ROUTING-GATES).

The w2 routing check (DSC:NEWS-IMPACT-W2-ROUTING-MOSTLY-OFF-EVENT) found that most
w2 cases did not pair a real issuer event with a filing that reports it. These three
gates run, in order, before any case is labelled:

* G1 non-event headline: market reports, quote pages, solicitations, and
  commentary or list headlines carry no issuer event.
* G2 issuer guard: the resolved issuer must be named in the headline (a one-letter
  or common-word ticker needs the registrant's name, a cashtag or a parenthesised
  ticker). A headline that never names the issuer must be covered by the attached
  filing. A headline led by a name the filing never mentions is about someone else.
* G3 body-to-event match: the attached filing must contain the routed template's
  family language, and a results headline needs an attached item 2.02 filing.

The gates read the headline, the ticker, the template and the attached document
text. They never read ``proxy_cell``. The CLI writes a gate map (item id to
``gated_in`` or ``gated_out:<code>``) that ``tape_draw --gate-frame`` consumes; the
map and the report hold ids and codes only, never headline or filing text
(DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE). Gated-out cases are kept as reject material.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from engine.news_impact.tape_draw import FAMILY_PATTERNS, GATE_STATUS_RE

GATES_VERSION = "ni-routing-gates-1"
GATED_IN = "gated_in"
STATUS_RE = GATE_STATUS_RE

# Every gated-out code, by gate. A code outside this table is a bug.
CODES = {
    "no_body": "G0",
    "g1_market_report": "G1",
    "g1_quote_page": "G1",
    "g1_solicitation": "G1",
    "g1_commentary": "G1",
    "g2_ambiguous_ticker": "G2",
    "g2_issuer_absent": "G2",
    "g2_issuer_not_subject": "G2",
    "g3_no_family_language": "G3",
    "g3_results_without_202": "G3",
}


class RoutingGateError(ValueError):
    """Invalid gate input (never a gate verdict)."""


# --- G1: non-event headline ---------------------------------------------------

_G1_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "g1_market_report",
        re.compile(
            r"(?<!stock )\bmarkets? (?:size|share|forecast|report|research|analysis"
            r"|outlook|trends?|insights?)\b|\bcagr\b|\bforecast (?:to|through|till|until) 20\d\d\b"
            r"|\bdatabook\b",
            re.IGNORECASE,
        ),
    ),
    (
        "g1_quote_page",
        re.compile(
            r"\bstock quote\b|\bprice (?:and|&) forecast\b|\bprice predictions?\b",
            re.IGNORECASE,
        ),
    ),
    (
        "g1_solicitation",
        re.compile(
            r"\b(?:alert|reminder)\s*:|\bclass action\b|\blead plaintiff\b"
            r"|\bshareholder rights\b|\bfairness of\b",
            re.IGNORECASE,
        ),
    ),
    (
        "g1_commentary",
        re.compile(
            r"^\s*\d+\s+(?:[\w&'’-]+\s+){0,3}stocks?\b|\bstocks? to (?:buy|own|watch|hold)\b"
            r"|\bdividend stocks?\b|\bis (?:a|an) (?:great|good|top|smart|strong|solid)\b"
            r"|\bis a buy\b|\bright now\b|\bhow many shares\b|\byou['’]?d need\b"
            r"|\bthis (?:[\w-]+ ){0,3}stocks?\b|^\s*(?:will|should)\b"
            r"|\bon your (?:\w+ )?radar\b|\bhere['’]?s (?:why|how)\b",
            re.IGNORECASE,
        ),
    ),
)


def non_event_code(title: str) -> str | None:
    """G1: the first non-event category the headline matches, else None."""
    for code, pattern in _G1_RULES:
        if pattern.search(title or ""):
            return code
    return None


# --- shared tokenisation --------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9&'’.-]*", re.IGNORECASE)
_POSSESSIVE_RE = re.compile(r"['’]s$")

# Words that never identify a company or an event on their own.
_STOP = frozenset(
    """a an the of and or for to in on at by with from as is are was were be been its it
    this that these those after before over under into than but not new now just still all
    any our their his her who what why how when where which while about amid despite
    inc corp corporation co company companies ltd plc llc lp holdings holding group trust
    limited incorporated international technologies sa nv announces announced announce
    reports reported report says said year years quarter quarterly results stock stocks
    shares share q1 q2 q3 q4 fy first general national american united financial energy
    bank bancorp five global""".split()
)

_MONTHS = frozenset(
    "jan feb mar apr may jun jul aug sep sept oct nov dec january february march april "
    "june july august september october november december".split()
)

# Leading words that never make a headline "about someone else" (G2c).
_LEAD_EXEMPT = frozenset(
    """the a an why how what when where who here's heres this these those shares stock
    stocks analysts analyst investors wall report reports breaking exclusive update top
    best new fda sec eu ftc doj epa fcc cms ema nhtsa faa us u.s. federal court judge
    government congress white treasury fed""".split()
)

# Dateline prefixes stripped before the subject test (G2c).
_PREFIX_RE = re.compile(
    r"^\s*(?:stock market today|market wrap|markets? today|breaking(?: news)?|exclusive"
    r"|update(?: \d+)?|earnings (?:call )?(?:highlights?|recap)|analysis)\b[^:]{0,30}:\s*",
    re.IGNORECASE,
)

# Tickers that are ordinary words in headlines (G2a). Single letters are always ambiguous.
COMMON_WORD_TICKERS = frozenset(
    """AI ALL AM AN ARE AS AT BE BIG BY CAN CAR CEO CFO DO EAT EU EV FOR FUN GO HAS HE IF
    IN IPO IS IT KEY LOW MAN ME NEW NO NOW OK ON ONE OR OUT PM RUN SEE SO TWO UK UP US
    USA WE WELL YOU""".split()
)

_REGISTRANT_RE = re.compile(r"(.{0,160}?)\(\s*Exact name of (?:the )?registrant", re.IGNORECASE)
_REGISTRANT_CUT_RE = re.compile(r"\d{4}|_{3,}|reported\s*\)\s*:?|​", re.IGNORECASE)

_RESULTS_RE = re.compile(
    r"\b(?:earnings|results|eps|beat|beats|tops|topped|misses|missed)\b", re.IGNORECASE
)


def _norm(token: str) -> str:
    return _POSSESSIVE_RE.sub("", token.lower().rstrip(".,;:!?"))


def _word_set(text: str) -> frozenset[str]:
    """Lower-cased word tokens of text, plus the parts of hyphenated tokens."""
    out: set[str] = set()
    for raw in _WORD_RE.findall(text):
        tok = _norm(raw)
        if not tok:
            continue
        out.add(tok)
        if "-" in tok:
            out.update(p for p in tok.split("-") if p)
    return frozenset(out)


def _content_tokens(title: str) -> list[str]:
    """Headline tokens that can carry content: no stop words, months or digits."""
    out = []
    for raw in _WORD_RE.findall(title or ""):
        for part in _norm(raw).split("-"):
            if (
                len(part) >= 3
                and part not in _STOP
                and part not in _MONTHS
                and not any(ch.isdigit() for ch in part)
            ):
                out.append(part)
    return out


# --- documents ------------------------------------------------------------------


@dataclass(frozen=True)
class GateDocument:
    """One attached document: its type, its filing's 8-K items, and its text."""

    doc_type: str
    items: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class GateVerdict:
    code: str | None  # None when gated in

    @property
    def gated_in(self) -> bool:
        return self.code is None

    @property
    def gate(self) -> str | None:
        return None if self.code is None else CODES[self.code]

    def status(self) -> str:
        return GATED_IN if self.code is None else f"gated_out:{self.code}"


def registrant_tokens(documents: Sequence[GateDocument]) -> frozenset[str]:
    """Distinctive tokens of the registrant name on the 8-K cover pages.

    Empty when no cover page parses; the issuer test then rests on the ticker.
    """
    tokens: set[str] = set()
    for doc in documents:
        if doc.doc_type.upper() != "8-K":
            continue
        flat = re.sub(r"\s+", " ", doc.text[:20000])
        m = _REGISTRANT_RE.search(flat)
        if not m:
            continue
        name = _REGISTRANT_CUT_RE.split(m.group(1))[-1]
        for raw in _WORD_RE.findall(name):
            tok = _norm(raw)
            if len(tok) >= 2 and tok not in _STOP and not tok.isdigit():
                tokens.add(tok)
    return frozenset(tokens)


def _ticker_mentioned(title: str, ticker: str) -> bool:
    t = re.escape(ticker)
    if re.search(rf"\${t}\b|\(\s*{t}\s*\)|\b(?:NYSE|NASDAQ|Nasdaq|AMEX)\s*:\s*{t}\b", title):
        return True
    if len(ticker) <= 1 or ticker in COMMON_WORD_TICKERS:
        return False
    return re.search(rf"(?<![A-Za-z0-9&$.-]){t}(?![A-Za-z0-9&-])", title) is not None


def issuer_mention_index(title: str, ticker: str, names: frozenset[str]) -> int | None:
    """Token index of the issuer's first mention in title, or None if never named."""
    words = _WORD_RE.findall(title)
    for i, raw in enumerate(words):
        if _norm(raw) in names:
            return i
    if _ticker_mentioned(title, ticker):
        t = ticker.lower()
        for i, raw in enumerate(words):
            if _norm(raw) == t:
                return i
        return 0  # cashtag or exchange form whose token split differs
    return None


def headline_coverage(title: str, body_words: frozenset[str]) -> tuple[int, float]:
    """(content token count, share of them present in the body word set)."""
    toks = _content_tokens(title)
    if not toks:
        return 0, 0.0
    return len(toks), sum(1 for t in toks if t in body_words) / len(toks)


COVERAGE_MIN = 0.6
COVERAGE_MIN_TOKENS = 3


def classify(
    title: str, template: str, ticker: str, documents: Sequence[GateDocument]
) -> GateVerdict:
    """Apply G1, G2, G3 in order and return the first failing code, else gated in."""
    if template not in FAMILY_PATTERNS:
        raise RoutingGateError(f"unknown template {template!r}")
    if not isinstance(ticker, str) or not ticker:
        raise RoutingGateError(f"ticker must be a non-empty str: {ticker!r}")
    title = title or ""
    if not documents:
        return GateVerdict("no_body")

    code = non_event_code(title)
    if code:
        return GateVerdict(code)

    body = "\n".join(d.text for d in documents)
    body_words = _word_set(body)
    names = registrant_tokens(documents)
    stripped = _PREFIX_RE.sub("", title, count=1)
    mention = issuer_mention_index(stripped, ticker, names)
    if mention is None:
        if len(ticker) <= 1 or ticker in COMMON_WORD_TICKERS:
            return GateVerdict("g2_ambiguous_ticker")
        n, cov = headline_coverage(stripped, body_words)
        if n < COVERAGE_MIN_TOKENS or cov < COVERAGE_MIN:
            return GateVerdict("g2_issuer_absent")
    elif mention > 0:
        lead = _WORD_RE.findall(stripped)[0]
        lead_norm = _norm(lead)
        if (
            lead[:1].isupper()
            and lead_norm not in _LEAD_EXEMPT
            and lead_norm not in names
            and lead_norm not in body_words
        ):
            return GateVerdict("g2_issuer_not_subject")

    if not FAMILY_PATTERNS[template].search(body):
        return GateVerdict("g3_no_family_language")
    if _RESULTS_RE.search(title) and not any("2.02" in d.items for d in documents):
        return GateVerdict("g3_results_without_202")
    return GateVerdict(None)


# --- CLI ------------------------------------------------------------------------


def _read_jsonl(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError as exc:
                    raise RoutingGateError(f"{path}:{n} is not JSON: {exc}") from exc
    return rows


def _documents(body_row: Mapping, texts_dir: Path) -> list[GateDocument]:
    docs = []
    for filing in body_row.get("filings") or ():
        items = tuple(filing.get("items") or ())
        for doc in filing.get("documents") or ():
            if doc.get("status") != "available":
                continue
            path = texts_dir / f"{doc['text_sha256']}.txt"
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise RoutingGateError(f"body text missing: {path.name} ({exc})") from exc
            docs.append(GateDocument(str(doc.get("doc_type") or ""), items, text))
    return docs


def build_gate_map(
    candidates: Iterable[Mapping], bodies: Mapping[str, Mapping], texts_dir: Path
) -> dict[str, str]:
    """Gate status for every candidate; a candidate without an available body is no_body."""
    out: dict[str, str] = {}
    for cand in candidates:
        item_id = cand["item_id"]
        if item_id in out:
            raise RoutingGateError(f"duplicate candidate item_id {item_id!r}")
        row = bodies.get(item_id)
        docs = _documents(row, texts_dir) if row and row.get("status") == "available" else []
        if not docs:
            out[item_id] = GateVerdict("no_body").status()
            continue
        out[item_id] = classify(cand.get("title") or "", cand["template"], cand["ticker"], docs).status()
    return dict(sorted(out.items()))


def _sha256_file(path: str) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="engine.news_impact.routing_gates",
        description="Write a gate map (item id -> gated_in | gated_out:<code>) for a candidate pool.",
    )
    parser.add_argument("--candidates", required=True, help="tape_draw --candidates-out JSONL")
    parser.add_argument("--bodies", required=True, help="edgar_body bodies.jsonl")
    parser.add_argument("--texts", required=True, help="edgar_body texts directory")
    parser.add_argument("--out", required=True, help="gate map JSON to write")
    parser.add_argument("--report", default=None, help="optional gate report JSON (counts only)")
    args = parser.parse_args(argv)
    try:
        candidates = _read_jsonl(args.candidates)
        bodies = {r["item_id"]: r for r in _read_jsonl(args.bodies)}
        gate_map = build_gate_map(candidates, bodies, Path(args.texts))
    except (RoutingGateError, KeyError) as exc:
        print(f"routing_gates: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(gate_map, indent=2, sort_keys=True) + "\n"
    Path(args.out).write_text(payload, encoding="utf-8")
    counts: dict[str, int] = {}
    for status in gate_map.values():
        counts[status] = counts.get(status, 0) + 1
    summary = {
        "gates_version": GATES_VERSION,
        "n_candidates": len(gate_map),
        "n_gated_in": counts.get(GATED_IN, 0),
        "status_counts": dict(sorted(counts.items())),
        "gate_map_sha256": sha256(payload.encode("utf-8")).hexdigest(),
        "candidates_sha256": _sha256_file(args.candidates),
        "bodies_sha256": _sha256_file(args.bodies),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
