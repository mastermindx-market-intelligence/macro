"""Evidence-limited views over already curated ticker reports.

Pure reader policy. A company reference is a text match, not a claim of
primary subject, materiality, truth, completeness, or publisher entitlement.
Provider tags, withheld fields, bodies, and model output are never inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from engine.qkernel import publisher_domain

EDITORIAL_VIEW_VERSION = "ticker_news.editorial_view.v1"
# Bump when admission/reference rules change, independently of the wire schema.
EDITORIAL_RULES_VERSION = "ticker_news.editorial_rules.v2"
VIEW_MODES = frozenset({"all", "news", "company"})

_LEGAL_SUFFIX = re.compile(
    r"(?:,?\s+(?:incorporated|inc\.?|corporation|corp\.?|limited|ltd\.?|plc))$",
    re.I,
)
_SPACE = re.compile(r"\s+")
# Named formats, not predictions about an article's truth or investment value.
_FORMATS = (
    ("roundup", "named_roundup", re.compile(
        r"^(?:benzinga(?:['’]s)?\s+)?bulls\s+(?:and|&)\s+bears\b"
        r"|^(?:weekly\s+(?:roundup|recap)|week\s+in\s+review)\b"
        r"|(?:[:—–]\s*|\s+-\s+)(?:weekly\s+(?:roundup|recap)|week\s+in\s+review)\s*$",
        re.I,
    )),
    ("roundup", "options_activity_roundup", re.compile(
        r"^\d{1,2}\s+(?:[\w&-]+\s+){0,8}stocks?\s+"
        r"(?:with\s+)?(?:unusual\s+)?(?:whale\s+(?:alerts?|activity)|options\s+activity)\b",
        re.I,
    )),
    ("investment_template", "hypothetical_investment", re.compile(
        r"^\$[\d,.]+\s+invested\s+in\b.{1,180}\b(?:years?|decades?)\s+ago\b"
        r"|^if\s+you\s+(?:had\s+)?(?:invested|bought)\b.{1,180}\b(?:would|today|now)\b"
        r"|^here['’]s\s+how\s+much\b.{1,180}\b(?:invested|would\s+be\s+worth)\b",
        re.I,
    )),
    ("commentary", "explicit_commentary", re.compile(
        r"^(?:opinion|commentary)\s*:"
        r"|\((?:opinion|commentary)\)\s*$",
        re.I,
    )),
)


# This explicit portfolio interpretation frame needs corroborating publisher
# and permitted section evidence; it is not a blanket Investing Club rule.
_PORTFOLIO_COMMENTARY_FRAME = re.compile(
    r"(?:^|[.:;!?—–]\s*|\s+-\s+)what\s+it\s+means\s+for\s+our\s+stocks[.!?]?\s*$",
    re.I,
)


def plain_text(value: object) -> str:
    """Normalize projected display text without decoding entities a second time."""
    return _SPACE.sub(" ", unicodedata.normalize("NFKC", str(value or ""))).strip()


@dataclass(frozen=True, slots=True)
class CompanyReferenceContext:
    security_id: str
    ticker: str
    universe_revision: str
    names: tuple[str, ...]
    symbols: tuple[str, ...]

    @property
    def revision(self) -> str:
        payload = (self.security_id, self.ticker, self.universe_revision, self.names, self.symbols)
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def company_reference_context(
    *, security_id: str, ticker: str, universe_revision: str,
    names: tuple[str, ...] = (), symbols: tuple[str, ...] = (),
) -> CompanyReferenceContext:
    """Attach display-name evidence to an identity resolved by its existing owner.

    Only a closed legal suffix may be removed. No first-word, product, executive,
    subsidiary, acquisition, or historical identity inference is performed.
    """
    clean_symbols = tuple(sorted({
        plain_text(value).upper() for value in (ticker, *symbols)
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-]{0,15}", plain_text(value))
    }))
    clean_names: set[str] = set()
    for value in names:
        name = plain_text(value)
        if not name or len(name) > 160 or name.upper() in clean_symbols:
            continue
        for candidate in (name, _LEGAL_SUFFIX.sub("", name).strip()):
            if (len(candidate) >= 3 and candidate.upper() not in clean_symbols
                    and any(char.isalpha() for char in candidate)):
                clean_names.add(candidate.casefold())
    return CompanyReferenceContext(
        security_id, ticker, universe_revision,
        tuple(sorted(clean_names)), clean_symbols,
    )


def company_reference(title: str, teaser: str, context: CompanyReferenceContext | None) -> str:
    if context is None:
        return "not_observed"
    for field, value in (("headline", title), ("summary", teaser)):
        text = plain_text(value)
        for name in context.names:
            for match in re.finditer(r"(?<![\w@])" + re.escape(name) + r"(?![\w@])", text, re.I):
                # A single ordinary word in prose is not a company identifier.
                # This remains text-reference evidence, never semantic relevance.
                if " " in name or any(char.isupper() for char in match.group()):
                    return field
        for symbol in context.symbols:
            if re.search(
                r"(?<![\w$])(?:\$|(?:NASDAQ|NYSE|AMEX)\s*:\s*)"
                + re.escape(symbol) + r"(?![\w.\-])", text, re.I,
            ):
                return field
    return "not_observed"


def article_format(title: str, source: str, url: str = "") -> tuple[str, str | None]:
    """Identify explicit formats; absence of a match is deliberately unclassified."""
    text = plain_text(title)
    for kind, reason, pattern in _FORMATS:
        if pattern.search(text):
            return kind, reason
    # A publisher section is evidence only on that publisher's actual host.
    if source == "benzinga" or source == "massive:benzinga.com":
        try:
            parsed = urlsplit(plain_text(url))
            section = unquote(parsed.path).strip("/").split("/", 1)[0].casefold()
            if (parsed.scheme.casefold() in {"http", "https"}
                    and publisher_domain(parsed.hostname or "") == "benzinga.com"
                    and section == "opinion"):
                return "commentary", "publisher_opinion_section"
        except ValueError:
            pass
    if source == "massive:cnbc.com" and _PORTFOLIO_COMMENTARY_FRAME.search(text):
        try:
            parsed = urlsplit(plain_text(url))
            section = unquote(parsed.path).strip("/").split("/", 1)[0].casefold()
            if (parsed.scheme.casefold() in {"http", "https"}
                    and publisher_domain(parsed.hostname or "") == "cnbc.com"
                    and section == "investingclub"):
                return "commentary", "publisher_portfolio_commentary"
        except ValueError:
            pass
    return "unclassified", None


@dataclass(frozen=True, slots=True)
class NewsEditorialView:
    mode: str = "all"
    company: CompanyReferenceContext | None = None
    rights_revision: str = ""

    def __post_init__(self) -> None:
        if self.mode not in VIEW_MODES:
            raise ValueError("ticker_news:invalid_editorial_view")

    @property
    def revision(self) -> str:
        basis = (EDITORIAL_VIEW_VERSION, EDITORIAL_RULES_VERSION, self.mode,
                 self.company.revision if self.company else None, self.rights_revision)
        return hashlib.sha256(json.dumps(basis).encode()).hexdigest()

    def metadata(self) -> dict:
        return {
            "schema": EDITORIAL_VIEW_VERSION,
            "mode": self.mode,
            "rules": EDITORIAL_RULES_VERSION,
            "revision": self.revision,
            "name_coverage": "names_and_symbols" if self.company and self.company.names else
                "symbols_only" if self.company and self.company.symbols else "unavailable",
        }

    def allows(self, source: str, title: str, url: str = "", teaser: str = "") -> bool:
        if self.mode == "all":
            return True
        if article_format(title, source, url)[0] != "unclassified":
            return False
        return self.mode != "company" or company_reference(title, teaser, self.company) != "not_observed"

    def decision(self, source: str, title: str, url: str = "", teaser: str = "") -> dict:
        kind, reason = article_format(title, source, url)
        reference = company_reference(title, teaser, self.company)
        admitted = self.mode == "all" or (
            kind == "unclassified"
            and (self.mode != "company" or reference != "not_observed")
        )
        return {
            "schema": EDITORIAL_VIEW_VERSION,
            "format": kind,
            "format_reason": reason,
            "company_reference": reference,
            "eligible": admitted,
        }
