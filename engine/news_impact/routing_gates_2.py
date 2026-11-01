"""Routing gates, version 2 (DEC:NEWS-IMPACT-ROUTING-GATES-1-MISS-PATH item 3).

ni-routing-gates-1 (``engine.news_impact.routing_gates``, frozen at a8f98d21) missed its
pre-registered gated-in bar (DSC:NEWS-IMPACT-ROUTING-GATES-1-VALIDATION). This module is
a separate gate set with its own version string, so gates-1 stays byte-reproducible.
It runs the gates-1 checks unchanged and adds:

* G1 widenings: a market wrap (an index led headline with a move verb), solicitation
  shapes (losses, law firms, investigations announced on behalf of investors) and a
  quote-page "opinions on" shape. Commentary is unchanged: a headline that reports an
  event and then adds "here's what investors need to know" still reports the event.
* Event kind: the headline's event kinds inside the routed family (T1 repurchase,
  dividend, offering, split, redemption; T2 guidance, contract; T3 partnership,
  launch, fda).
* G3 template sense (``g3_template_sense``): a bare "offering" under T1 must be a
  capital offering (a capital qualifier in the headline or underwriting language in
  the filing); a T3 "launch" of a performance report or of a proxy, tender, review or
  bid is not a product launch; an at-the-market equity agreement is not a T3 event.
* G3 event match (``g3_event_mismatch``): the filing must report one of the
  headline's event kinds, and a T3 case whose filings carry only items 2.02 and 9.01
  reports results, not a strategic event.
* T2 relaxations of ``g3_no_family_language``: a guidance headline with an attached
  item 2.02 filing, or a contract headline with an attached item 1.01 filing, passes
  the family check even when the filing words the event outside the family pattern.

The gates read the headline, the ticker, the template and the attached document text,
never ``proxy_cell``. The CLI writes the same gate map shape as gates-1 (item id to
``gated_in`` or ``gated_out:<code>``), which ``tape_draw --gate-frame`` consumes; the
map and report hold ids and codes only (DEC:NEWS-IMPACT-BENCHMARK-BODY-SOURCE).
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

from engine.news_impact import routing_gates as g1
from engine.news_impact.tape_draw import FAMILY_PATTERNS, GATE_STATUS_RE

GATES_VERSION = "ni-routing-gates-2"
GATED_IN = g1.GATED_IN
STATUS_RE = GATE_STATUS_RE
GateDocument = g1.GateDocument
RoutingGateError = g1.RoutingGateError

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
    "g3_template_sense": "G3",
    "g3_event_mismatch": "G3",
}


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


# --- G1: non-event headline (gates-1 rules first, then the widenings) -----------

_INDEX = (
    r"(?:nasdaq(?: composite)?|s&p(?: 500)?|dow(?: jones)?(?: industrials)?|wall st(?:reet|\.)?"
    r"|stocks|(?:stock )?futures|markets?|equities|ftse(?: 100)?|nikkei|hang seng|stoxx(?: 600)?"
    r"|tsx|asx)"
)
_MOVE = (
    r"(?:lift(?:s|ed)?|rise[sn]?|rose|fall(?:s|en)?|fell|gain(?:s|ed)?|drop(?:s|ped)?"
    r"|rall(?:y|ies|ied)|mixed|slip(?:s|ped)?|climb(?:s|ed)?|jump(?:s|ed)?|sinks?|sank"
    r"|tumble[sd]?|surge[sd]?|edge[sd]?|ends?|ended|close[sd]?|opens?|opened|higher|lower"
    r"|flat|record)"
)
_G1_EXTRA: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "g1_market_report",
        re.compile(
            rf"^\s*{_INDEX}(?:\s*(?:,|and|&)\s*{_INDEX}){{0,2}}\s+(?:[\w'’-]+\s+){{0,2}}{_MOVE}\b"
            r"|\binvestors (?:eye|await|weigh|digest)\b",
            re.IGNORECASE,
        ),
    ),
    ("g1_quote_page", re.compile(r"\bopinions? on\b", re.IGNORECASE)),
    (
        "g1_solicitation",
        re.compile(
            r"\binvestors who (?:suffered|lost|incurred)\b|\bsuffered losses\b|\bencouraged to contact\b"
            r"|\blaw firm\b|\bsecurities (?:fraud|litigation)\b|\bannounces (?:an )?investigation\b"
            r"|\bon behalf of (?:investors|shareholders)\b",
            re.IGNORECASE,
        ),
    ),
)


def non_event_code(title: str) -> str | None:
    """G1: the gates-1 non-event code, else the first widening the headline matches."""
    code = g1.non_event_code(title)
    if code:
        return code
    for code, pattern in _G1_EXTRA:
        if pattern.search(title or ""):
            return code
    return None


# --- event kind (headline) -------------------------------------------------------

_KIND_HEADLINE: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "T1": (
        ("repurchase", re.compile(r"\brepurchas\w*|\bbuy-?backs?\b|\btender offers?\b", re.I)),
        ("dividend", re.compile(r"\bdividends?\b", re.I)),
        (
            "offering",
            re.compile(
                r"\bofferings?\b|\bprivate placements?\b|\bshare sales?\b|\bsells? shares\b|\braises? \$|\bipo\b",
                re.I,
            ),
        ),
        ("split", re.compile(r"\b(?:stock|reverse) splits?\b", re.I)),
        (
            "redemption",
            re.compile(
                r"\bredeem\w*|\bredemptions?\b|\bsenior notes\b|\bconvertible\w*|\bnotes due\b"
                r"|\bdebt (?:offering|issuance|raise)\b",
                re.I,
            ),
        ),
    ),
    "T2": (
        (
            "guidance",
            re.compile(
                r"\bguidance\b|\boutlook\b|\bforecasts?\b|\bwarns?\b|\bprofit warning\b"
                r"|\bpre-?announce\w*|\breaffirm\w*|\breiterat\w*",
                re.I,
            ),
        ),
        (
            "contract",
            re.compile(
                r"\bcontracts?\b|\borders?\b|\bdeals?\b|\bawards?\b|\bawarded\b|\bbacklog\b|\bbookings\b", re.I
            ),
        ),
    ),
    "T3": (
        (
            "partnership",
            re.compile(
                r"\bpartner\w*|\bcollaborat\w*|\balliances?\b|\bjoint ventures?\b|\bagreements?\b"
                r"|\btie-?ups?\b|\bteam(?:s|ed)? up\b|\blicens\w*",
                re.I,
            ),
        ),
        ("launch", re.compile(r"\blaunch\w*|\bunveil\w*|\brolls? out\b|\brolled out\b|\bintroduc\w*|\bdebut\w*", re.I)),
        ("fda", re.compile(r"\bfda\b|\bapprov\w*|\bclearance\b", re.I)),
    ),
}


def event_kinds(title: str, template: str) -> frozenset[str]:
    """The routed family's event kinds the headline names (empty: no kind check)."""
    return frozenset(kind for kind, pattern in _KIND_HEADLINE[template] if pattern.search(title or ""))


# --- G3 template sense ----------------------------------------------------------

_CAPITAL_BY_NATURE = re.compile(r"\bprivate placements?\b|\bshare sales?\b|\bsells? shares\b|\braises? \$|\bipo\b", re.I)
_CAPITAL_QUALIFIER = re.compile(
    r"\b(?:public|secondary|registered|underwritten|proposed|follow-on|at-the-market|direct|stock|share"
    r"|equity|debt|notes?|bond|convertible|common|preferred|senior|initial public)\s+(?:[\w-]+\s+){0,2}offerings?\b"
    r"|\bofferings? of (?:[\w,.$-]+\s+){0,4}(?:shares|notes|stock|units|bonds|debentures|warrants)\b"
    r"|\bpric(?:es|ed|ing)\b.{0,40}\bofferings?\b|\bofferings?\b.{0,40}\bpric(?:es|ed|ing)\b",
    re.I,
)
_CAPITAL_BODY = re.compile(
    r"underwrit|placement agent|sales agreement|prospectus supplement|at[- ]the[- ]market", re.I
)
_LAUNCH_PERFORMANCE = re.compile(
    r"\b(?:launch\w*|unveil\w*|introduc\w*|rolls? out|debut\w*)\s+(?:[\w&'’.-]+\s+){0,4}?"
    r"(?:performance|results|figures|metrics|statistics|stats|traffic|numbers|earnings)"
    r"(?=\s*$|\s*[,.;:!?(|–—-]|\s+(?:for|in|of|at|on|from|as|amid|after|and|with|to|through)\b)",
    re.I,
)
_LAUNCH_NON_PRODUCT = re.compile(
    r"\b(?:launch\w*|unveil\w*)\s+(?:(?:a|an|the|its|new|formal|strategic|hostile)\s+)*"
    r"(?:proxy|tender|offering|review|investigation|bid|fight|consent solicitation)\b",
    re.I,
)
_ATM_AGREEMENT = re.compile(
    r"\bequity distribution agreement\b|\b(?:equity|atm|at-the-market) sales agreement\b|\bat-the-market\b", re.I
)


def sense_code(title: str, template: str, kinds: frozenset[str], body: str) -> str | None:
    """G3 template sense: the headline's family word used in another sense."""
    if template == "T1" and kinds == frozenset({"offering"}):
        if not (_CAPITAL_BY_NATURE.search(title) or _CAPITAL_QUALIFIER.search(title) or _CAPITAL_BODY.search(body)):
            return "g3_template_sense"
    if template == "T3":
        if "launch" in kinds and (_LAUNCH_PERFORMANCE.search(title) or _LAUNCH_NON_PRODUCT.search(title)):
            return "g3_template_sense"
        if _ATM_AGREEMENT.search(title):
            return "g3_template_sense"
    return None


# --- G3 event match ---------------------------------------------------------------

_KIND_BODY: dict[str, re.Pattern[str]] = {
    "repurchase": re.compile(r"repurchas|buy-?back|tender offer", re.I),
    "dividend": re.compile(
        r"\b(?:declar\w*|increas\w*|rais\w*|cut\w*|reduc\w*|suspend\w*|initiat\w*|reinstat\w*|approv\w*)"
        r"\s+(?:[\w-]+\s+){0,4}dividends?\b"
        r"|\bdividends?\b[\s\S]{0,80}?\b(?:declared|payable|per share|record date|of record)\b",
        re.I,
    ),
    "offering": re.compile(
        r"underwrit|offering|placement|prospectus|10b5-1"
        r"|\b(?:sell\w*|sale|sold|issu\w*)\b[\s\S]{0,40}?\b(?:shares|stock|securities)\b",
        re.I,
    ),
    "split": re.compile(r"\bsplit", re.I),
    "redemption": re.compile(r"redeem|redemption|indenture|\bnotes\b|convertible|debentures?", re.I),
    "guidance": re.compile(r"guidance|outlook|forecast|expect\w*|anticipat\w*", re.I),
    "contract": re.compile(r"contract|agreement|\border|award|backlog|bookings", re.I),
    "partnership": re.compile(r"partner\w*|collaborat\w*|alliance|joint venture|agreement|licens\w*", re.I),
    "launch": re.compile(
        r"launch\w*|introduc\w*|unveil\w*|rolls? out|rolled out|debut\w*|now available"
        r"|(?:commercial|general) availability",
        re.I,
    ),
    "fda": re.compile(r"\bfda\b|food and drug administration|approv\w*|clearance|510\(k\)", re.I),
}
# An attached item that reports the kind even when the text words it otherwise.
_KIND_ITEMS: dict[str, frozenset[str]] = {
    "guidance": frozenset({"2.02", "7.01", "8.01"}),
    "contract": frozenset({"1.01"}),
    "partnership": frozenset({"1.01"}),
}
_RESULTS_ONLY_ITEMS = frozenset({"2.02", "9.01"})


def event_match(template: str, kinds: frozenset[str], body: str, items: frozenset[str]) -> bool:
    """G3 event match: some headline kind is reported by the attached filings."""
    if template == "T3" and items and items <= _RESULTS_ONLY_ITEMS:
        return False
    if not kinds:
        return True
    return any(_KIND_BODY[k].search(body) or (_KIND_ITEMS.get(k, frozenset()) & items) for k in kinds)


def t2_relaxed(template: str, kinds: frozenset[str], items: frozenset[str]) -> bool:
    """A T2 event the filing words outside the family pattern, carried by its item."""
    if template != "T2":
        return False
    return ("guidance" in kinds and "2.02" in items) or ("contract" in kinds and "1.01" in items)


def classify(title: str, template: str, ticker: str, documents: Sequence[GateDocument]) -> GateVerdict:
    """Gate verdict for one candidate under ni-routing-gates-2."""
    if template not in FAMILY_PATTERNS:
        raise RoutingGateError(f"unknown template {template!r}")
    if not isinstance(ticker, str) or not ticker:
        raise RoutingGateError(f"ticker must be a non-empty string, got {ticker!r}")
    title = title or ""
    if not documents:
        return GateVerdict("no_body")
    code = non_event_code(title)
    if code:
        return GateVerdict(code)
    # gates-2 G1 is a superset of gates-1 G1, so gates-1 here answers G2 and its own G3 only.
    base = g1.classify(title, template, ticker, documents).code
    kinds = event_kinds(title, template)
    items = frozenset(i for d in documents for i in d.items)
    if base == "g3_no_family_language" and t2_relaxed(template, kinds, items):
        base = None
        if g1._RESULTS_RE.search(title) and "2.02" not in items:
            base = "g3_results_without_202"
    if base is not None:
        return GateVerdict(base)
    body = "\n".join(d.text for d in documents)
    code = sense_code(title, template, kinds, body)
    if code:
        return GateVerdict(code)
    if not event_match(template, kinds, body, items):
        return GateVerdict("g3_event_mismatch")
    return GateVerdict(None)


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
        docs = g1._documents(row, texts_dir) if row and row.get("status") == "available" else []
        if not docs:
            out[item_id] = GateVerdict("no_body").status()
            continue
        out[item_id] = classify(cand.get("title") or "", cand["template"], cand["ticker"], docs).status()
    return dict(sorted(out.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="engine.news_impact.routing_gates_2",
        description="Write a gates-2 map (item id -> gated_in | gated_out:<code>) for a candidate pool.",
    )
    parser.add_argument("--candidates", required=True, help="tape_draw --candidates-out JSONL")
    parser.add_argument("--bodies", required=True, help="edgar_body bodies.jsonl")
    parser.add_argument("--texts", required=True, help="edgar_body texts directory")
    parser.add_argument("--out", required=True, help="gate map JSON to write")
    parser.add_argument("--report", default=None, help="optional gate report JSON (counts only)")
    args = parser.parse_args(argv)
    try:
        candidates = g1._read_jsonl(args.candidates)
        bodies = {r["item_id"]: r for r in g1._read_jsonl(args.bodies)}
        gate_map = build_gate_map(candidates, bodies, Path(args.texts))
    except (RoutingGateError, KeyError) as exc:
        print(f"routing_gates_2: {exc}", file=sys.stderr)
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
        "candidates_sha256": g1._sha256_file(args.candidates),
        "bodies_sha256": g1._sha256_file(args.bodies),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
