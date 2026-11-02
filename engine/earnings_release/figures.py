"""Deterministic figure extraction from an earnings release body.

NO MODEL, NO INFERENCE.  Every number this module emits was read out of an exact
source location, and every number it declines to emit is reported as a **typed
absence** carrying the reason.  The governing law is handoff §Wave 1.5, restated
by the contract freeze: *a number without basis, units, period, and source is
ABSENT, not guessed.*

That is a deliberately expensive rule and it is the point.  Concretely:

* **Basis is never defaulted.**  A figure is ``gaap`` only under a caption that
  says so — the condensed consolidated statements are, by their own heading, the
  GAAP financial statements — or ``non_gaap`` under an explicit
  ``non-GAAP`` / ``adjusted`` / ``reconciliation`` signal.  A number under
  neither lands as ``basis_undeclared``.  Defaulting EPS to GAAP is exactly how
  an adjusted print gets compared against a GAAP estimate.
* **Currency is read off the column, not assumed.**  These statements typeset
  ``$`` on the first and total lines of a column only, so the first currency
  symbol seen in a column governs that column.  A column that never declares one
  lands as ``currency_undeclared``.
* **Per-share rows do not inherit the table's scale.**  ``(In millions)`` on the
  statement caption does not make ``$2.18`` two million dollars.  The bare
  ``Basic`` / ``Diluted`` labels are also scope-gated: the identical labels
  appear under ``Shares used in computing earnings per share``, where the value
  is a share count.  Reading that row as EPS is a real, shipped-elsewhere bug
  class, so the scope test is mandatory rather than a nicety.
* **An absence carries no value field at all**, so it cannot be read as zero.

Output is ``context_only``.  Nothing here ranks, sizes, gates or escalates.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
import math
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

from engine.fundamental_forensics.disclosure_diff import (
    BlockKind,
    DisclosureBlock,
    DisclosureDocument,
    TableCell,
)

from .receipts import ReceiptError, SpanReceipt, receipt_for_literal

FIGURES_SCHEMA = "earnings_release.figures/v1"
AUTHORITY = "context_only"


class Basis(str, Enum):
    GAAP = "gaap"
    NON_GAAP = "non_gaap"


class ValueKind(str, Enum):
    MONETARY = "monetary"
    PER_SHARE = "per_share"
    PERCENT = "percent"


class AbsenceReason(str, Enum):
    """Why a figure is absent.  Every value here is a *finding*, not an error."""

    CONCEPT_NOT_PRESENT = "concept_not_present"
    BASIS_UNDECLARED = "basis_undeclared"
    UNITS_UNDECLARED = "units_undeclared"
    CURRENCY_UNDECLARED = "currency_undeclared"
    PERIOD_UNDECLARED = "period_undeclared"
    VALUE_AMBIGUOUS = "value_ambiguous"
    RECEIPT_NOT_REPLAYABLE = "receipt_not_replayable"


# The roster is what "absent" is measured against.  Without a declared roster,
# silence and absence are indistinguishable and a coverage number means nothing.
CONCEPT_ROSTER: tuple[str, ...] = (
    "revenue",
    "gross_profit",
    "gross_margin_pct",
    "operating_income",
    "net_income",
    "eps_basic",
    "eps_diluted",
    "operating_cash_flow",
    "capital_expenditures",
    "guidance_revenue_low",
    "guidance_revenue_high",
)

_UNIT_BY_SCALE = {
    "thousands": "usd_thousands",
    "millions": "usd_millions",
    "billions": "usd_billions",
}
_SCALE_FACTOR = {"usd_thousands": 1e3, "usd_millions": 1e6, "usd_billions": 1e9}

# "(In millions)", "(in $ millions)", and the symbol-led "($ billions, except
# EPS)" / "$ in millions" forms.  A "$" in the caption also declares the
# currency of the table it governs.
_UNITS_CAPTION_RE = re.compile(
    r"\b(?:in|dollars in|amounts in|figures in)\s+(?:(?:US)?\$\s*)?(thousands|millions|billions)\b|"
    r"(?:\A|\()\s*(?:US)?\$\s*(?:in\s+)?(thousands|millions|billions)\b",
    re.I,
)
_CURRENCY_WORD_RE = re.compile(r"\b(?:U\.?S\.?\s+dollars|US\$|USD)\b", re.I)
_CURRENCY_SYMBOL = {"$": "USD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}

# A release typesets its hyphens and dashes as any of the Unicode dashes:
# "Non‑GAAP" (U+2011), "Twenty–Six Weeks", "Pro‒Forma", or a soft hyphen the
# browser never shows ("Twenty­Six").  Every pattern below spells a hyphen as
# "-", so the text it reads is folded first.  Only text that is matched is
# folded: a label, a caption, a period header.  A value cell never is, because
# its literal is replayed against the raw source, and a folded "−1.2" (U+2212)
# would read as negative while the "-1.2" the receipt cites is not in it.
# Every other format (Cf) character in the BMP, the musical-symbol format
# block and the tag block is dropped with the soft hyphen: a zero-width space
# or joiner, a byte-order mark, a direction mark or isolate ("Non\u200b-GAAP",
# "Non\u200eGAAP"), and the combining grapheme joiner.  The few format
# characters in other supplementary blocks are kept.
_DASH_FOLD = str.maketrans({
    **{code: None
       for block in (range(0x10000), range(0x1D173, 0x1D17B), range(0xE0000, 0xE0080))
       for code in block if unicodedata.category(chr(code)) == "Cf"},
    **{chr(code): "-" for code in range(0x2010, 0x2016)},
    "−": "-", "﹣": "-", "－": "-", "\u034f": None,
})


def _fold_dashes(text: str) -> str:
    return text.translate(_DASH_FOLD)


# A GAAP statement says so in its own caption.  This is reading the document,
# not assuming a default.
_GAAP_CAPTION_RE = re.compile(
    r"condensed\s+consolidated\s+(?:statements?|balance)|"
    r"consolidated\s+statements?\s+of\s+(?:operations|income|earnings|cash\s+flows)|"
    r"consolidated\s+(?:income|earnings)\s+information|"
    r"\A\s*(?:consolidated\s+)?income\s+statements?\s*(?:\(unaudited\))?\s*\Z|"
    r"\bU\.?S\.?\s+GAAP\b|\bGAAP\s+(?:results|measures|basis)\b|"
    # A section heading that reads exactly "GAAP" (its "Non-GAAP" twin is a
    # _NON_GAAP_CAPTION_RE caption): Visa's summary opens each half this way.
    r"\A\s*GAAP\s*:?\s*\Z",
    re.I,
)
_NON_GAAP_CAPTION_RE = re.compile(
    r"(?<![a-z])non[\s-]*GAAP|reconciliation\s+of\s+|\badjusted\s+(?:results|measures|basis)\b", re.I
)
# "Non GAAP Results" is the non-GAAP caption too, never "GAAP results"; the
# "non" of "Canon GAAP Results" is not.
_NON_GAAP_INLINE_RE = re.compile(r"(?<![a-z])non[\s-]*GAAP|\badjusted\b", re.I)
# A basis DECLARATION is a caption: "Non-GAAP Financial Measures",
# "CONDENSED CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)",
# "RECONCILIATION OF ADJUSTED OPERATING INCOME AND ADJUSTED OPERATING MARGIN".
# Prose that merely MENTIONS a basis ("Non-GAAP results exclude the impact
# from certain investments, explained in ...", "1Non-GAAP financial measure;
# excludes ...") governs nothing after it.  Across the 40-release census every
# real caption is at most nine words and none is punctuated as a sentence.
_CAPTION_MAX_WORDS = 9
_SENTENCE_PUNCTUATION_RE = re.compile(r";|\.\s*\Z")
# "Compared with GAAP results" is a clause about two bases, not a heading.  A
# comparison between periods ("Q3 2025 vs. Q3 2024") is not; only one whose
# object is a basis is read this way.
_BASIS_COMPARISON_RE = re.compile(
    r"(?:\bcompared\s+(?:with|to)|\bversus|\bvs\.?)\s+(?:the\s+)?"
    r"(non[\s-]*GAAP|GAAP|adjusted)\b",
    re.I,
)
# A GAAP statement title that is qualified is an adjusted presentation of that
# statement: "Adjusted Consolidated Statements of Earnings", "... - As
# Adjusted", "..., Excluding Special Items".  It is neither the GAAP statement
# nor a declared non-GAAP measure, so it declares no basis.  Kept apart from
# _NON_GAAP_CAPTION_RE because only a GAAP-titled caption is read this way;
# prose that merely says "excluding" declares nothing.  "(In millions,
# excluding per share amounts)" qualifies the units, not the statement.
# "Comparable", "Core", "Underlying", "Recast" and "Pro-Forma" name the same
# kind of restated presentation.
_ADJUSTED_QUALIFIER_RE = re.compile(
    r"\badjusted\b|\bexcluding\b(?!\s+(?:share\s+and\s+)?per[\s-]+share)|\bpro[\s-]*forma\b|"
    r"\bspecial\s+items\b|\bcomparable\b|\bcore\b|\bunderlying\b|\brecast\b",
    re.I,
)
# What may stand beside the basis a comparison is drawn against and still leave
# that basis the section's: "Compared with GAAP results", "Q3 2025 vs. GAAP".
# Any other word names what is being compared ("Core Results Compared With
# GAAP", "Comparable EPS versus GAAP EPS"), and that is not the GAAP section.
_COMPARISON_FILLER = frozenset({
    "results", "result", "measures", "measure", "financial", "information", "figures",
    "amounts", "basis", "as", "reported", "the", "of", "and", "in", "on", "to", "for", "a",
    "an", "our", "its", "with",
    "quarter", "quarters", "year", "years", "prior", "period", "periods", "fiscal", "full",
    "first", "second", "third", "fourth", "three", "six", "nine", "twelve", "months",
    "weeks", "ended", "ending", "same", "last", "current",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "jan", "feb", "mar", "apr", "jun", "jul", "aug",
    "sep", "sept", "oct", "nov", "dec",
})
_COMPARISON_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'’-]*")
_COMPARISON_PERIOD_TOKEN_RE = re.compile(r"\A(?:\d+|q[1-4]|fy\d*)\Z")

_NUMERIC_CELL_RE = re.compile(r"\A\(?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?%?\Z")
_BARE_NUMERIC_RE = re.compile(r"\A\(?-?\d+(?:\.\d+)?\)?%?\Z")
_FOOTNOTE_CELL_RE = re.compile(r"\A\(\d{1,2}\)\Z")
_FOOTNOTE_SUFFIX_RE = re.compile(r"\s*\(\d{1,2}\)\s*\Z")
_MONTHS = (
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)"
)
_DATE_CELL_RE = re.compile(r"\A" + _MONTHS + r"\s+(\d{1,2}),?\s+(\d{4})\Z", re.I)
# "Three Months Ended September 30, 2025" in one cell: the date is the tail.
_DATE_TAIL_RE = re.compile(r"\b" + _MONTHS + r"\s+(\d{1,2}),?\s+(\d{4})\Z", re.I)
# "September 30," (or "Three Months Ended September 30,") over a row of years.
_MONTH_DAY_TAIL_RE = re.compile(r"(?:\A|\s)" + _MONTHS + r"\s+(\d{1,2}),?\Z", re.I)
_SLASH_DATE_RE = re.compile(r"\A(\d{1,2})/(\d{1,2})/(\d{4})\Z")
_YEAR_CELL_RE = re.compile(r"\A(?:19|20)\d{2}\Z")
_PERIOD_PREFIX_RE = re.compile(
    r"\b(?:three|six|nine|twelve|three-?month|first|second|third|fourth)\b.*\b"
    r"(?:month|quarter|year)s?\b.*\b(?:ended|ending)\b|"
    r"\b(?:week|month|quarter|year)s?\s+(?:ended|ending)\b",
    re.I,
)
# How long a period header says its period runs: "Three Months Ended",
# "12 Weeks Ended", "Fiscal Year Ended", "Fourth Quarter".
_SPAN_WORDS = {"three": 3, "six": 6, "nine": 9, "twelve": 12, "thirteen": 13, "sixteen": 16}
# A count after a dash or a tens word is the tail of a larger number:
# "Twenty-Six Weeks", "Twenty–Six Weeks" and "Thirty Nine Weeks" are not six or
# nine weeks.
_SPAN_COUNT_START = r"\b(?<![-–—])(?<!\btwenty\s)(?<!\bthirty\s)(?<!\bforty\s)(?<!\bfifty\s)"
_PERIOD_SPAN_RE = re.compile(
    _SPAN_COUNT_START + r"(three|six|nine|twelve|thirteen|sixteen|\d{1,2})[\s-]+(month|week)s?\b",
    re.I,
)
_YEAR_SPAN_RE = re.compile(r"\byears?\s+(?:ended|ending)\b|\bfiscal\s+(?:year\b|\d{4})", re.I)
_QUARTER_SPAN_RE = re.compile(
    r"\bquarters?\s+(?:ended|ending)\b|\b(?:first|second|third|fourth)\s+quarter\b|\bQ[1-4]\b",
    re.I,
)
# "Three and Nine Months Ended" heads two spans; "Three Quarters Ended" is nine
# months; a year-to-date column's length depends on the quarter it closes.
# Two periods are joined by "and", "&", "/" or a comma: "Quarter & Year",
# "Fourth Quarter / Full Year", "Three Months Ended, and Year Ended".
_PERIOD_JOINER = r"(?:\s+and\s+|\s*[&/,]\s*(?:and\s+)?)"
_SPAN_PAIR_RE = re.compile(
    _SPAN_COUNT_START + r"(three|six|nine|twelve|thirteen|sixteen|\d{1,2})" + _PERIOD_JOINER
    + r"(three|six|nine|twelve|thirteen|sixteen|\d{1,2})[\s-]+(month|week)s?\b",
    re.I,
)
_QUARTER_COUNT_RE = re.compile(r"\b(two|three|four|[1-4])\s+quarters\b", re.I)
_QUARTER_COUNTS = {"two": 2, "three": 3, "four": 4}
_PERIOD_LABEL_MAX = 300
_YEAR_TO_DATE_RE = re.compile(r"\bYTD\b|\byear[\s-]+to[\s-]+date\b", re.I)
# "Fourth Quarter and Fiscal Year Ended", "Q4 and Full Year 2025", "Twelve
# Weeks and Forty Weeks Ended": a header that joins two periods.  "Ended
# September 30, 2025 and 2024" joins two years of one period, not two periods.
# The second period may follow a date ("Quarter Ended December 28, 2025 and
# Year Ended") or another joiner, with at most two words before its name; a
# second date ("..., 2025 and December 29, 2024") names no period.  A header
# also joins its periods with a dash, ";", "|", "plus" or a comparison ("vs",
# "compared to"), and names the second as "FY2025" or "FY25": "Fourth Quarter -
# Fiscal Year", "Quarter | Full Year", "Fourth Quarter / FY2025", "Q4-FY26 vs
# Q4-FY25".  This reads "Year-over-Year" and "Half-Year" as
# two periods too, which refuses rather than binds.
_TWO_PERIOD_JOINER = r"(?:\s+(?:and|plus|vs\.?|versus|compared\s+(?:to|with))\s+|\s*[&/,;|-]\s*(?:and\s+)?)"
_TWO_PERIOD_HEADER_RE = re.compile(
    r"\b(?:quarter|Q[1-4]|year|half|months?|weeks?)\b"
    r"(?:[^,]*?\band\b[^,]*?|.*?" + _TWO_PERIOD_JOINER
    + r"(?:(?:[a-z]+(?:-[a-z]+)?|\d{1,2})\s+){0,2})"
    r"\b(?:quarter|Q[1-4]|year|half|months?|weeks?|fiscal|FY(?:\d{2}){0,2})\b",
    re.I,
)
# "Q4-FY26" and "Fourth Quarter - Fiscal 2026" name one quarter of a numbered
# fiscal year, so the dash is a qualifier there; "Fourth Quarter - Fiscal Year"
# and "Q4 FY26 / FY25" still join two periods.
_QUARTER_OF_FISCAL_YEAR_RE = re.compile(
    r"\b(Q[1-4]|quarter)-(FY(?:\d{2}){1,2}|fiscal (?:\d{2}){1,2})\b", re.I
)
# A cell that holds a column's place but no value: "—", "n/m", "*".
_PLACEHOLDER_CELL_RE = re.compile(r"\A(?:[-–—]+|n\.?/?m\.?|n\.?/?a\.?|\*+)\s*%?\Z", re.I)
# The closing half of a value typeset across cells: "(0.12" + ")", "12.5" + "%".
_SUFFIX_CELLS = frozenset({")", "%", ")%", "%)"})
_PERCENT_HEADER_RE = re.compile(r"%|\bpercent", re.I)
# "USD | YoY Change": a change column reports the difference between two
# periods, never either period's amount, whether it is typeset in % or $.
_CHANGE_HEADER_RE = re.compile(r"\bchange\b", re.I)
# The sub-header that names a period's own amount: "USD", "$", "Amount",
# "As Reported", "GAAP", "(in millions)".
_AMOUNT_HEADER_RE = re.compile(
    r"\A\s*\(?\s*(?:US\$|\$|USD|amounts?|dollars|(?:as\s+)?reported|GAAP|"
    r"(?:\$\s*)?in\s+(?:millions|thousands|billions))\s*\)?\s*\Z",
    re.I,
)
# "Net revenues1": a footnote reference glued to the label word.
_GLUED_FOOTNOTE_RE = re.compile(r"(?<=[a-z])\d{1,2}\Z")
_EPS_LABEL_RE = re.compile(r"\bEPS\b", re.I)
_SEGMENT_SCOPE_RE = re.compile(r"by\s+(?:reportable\s+)?segment|segment\s+(?:results|revenue)", re.I)
_SHARE_COUNT_SCOPE_RE = re.compile(r"shares\s+used|weighted[- ]average\s+shares", re.I)
_PER_SHARE_SCOPE_RE = re.compile(r"per\s+(?:common\s+)?share", re.I)
_TOTAL_LABEL_RE = re.compile(r"\Atotal\b", re.I)

_GUIDANCE_SENTENCE_RE = re.compile(
    r"\b(?:expect|expects|expecting|guidance|outlook|anticipat\w*|forecast\w*|"
    r"we\s+are\s+guiding|guiding)\b",
    re.I,
)
_GUIDANCE_RANGE_RE = re.compile(
    r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|thousand)?\s*"
    r"(?:to|through|[-–—])\s*"
    r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(billion|million|thousand)?",
    re.I,
)
_GUIDANCE_PERIOD_RE = re.compile(
    r"\b(?:for|in)\s+(?:the\s+)?(?:(first|second|third|fourth|next|current)\s+)?"
    r"(?:fiscal\s+)?(quarter|year)\b(?:\s+(?:of\s+)?(?:fiscal\s+)?(\d{4}))?",
    re.I,
)
_GUIDANCE_MAGNITUDE = {"thousand": "usd_thousands", "million": "usd_millions", "billion": "usd_billions"}
# What may follow a per-share label and still name the reported figure itself:
# a basis tag, an attribution to the parent, a trailing colon.  The tail is a
# closed list because anything else names a different number: "Diluted EPS
# excluding special items" is an adjusted measure and "Diluted EPS growth" is a
# percentage, and both would otherwise bind as the GAAP per-share amount.
# The attribution is closed too: it names the parent's holders ("common
# stockholders"), the parent by self-reference ("the Company"), or the parent by
# its proper name ("Walmart", "Acme Inc.").  "attributable to discontinued
# operations" and "... to the Tax Act" name a component of EPS, not EPS, so a
# lowercase or component word refuses.  A capitalized phrase is only the parent
# when the release names a company by it ("Walmart Inc."): "attributable to
# Goodwill Impairment" is shaped like a name and is a component.  The named
# parent is captured as ``parent`` / ``holder_parent`` for _concept_for to check.
_EPS_BASIS_TAG = r"(?:\s*\((?:GAAP|non-?GAAP|EPS)\))?"
_EPS_HOLDERS = r"(?:common\s+)?(?:stockholders|shareholders|shareowners|share\s*owners|equity\s+holders)"
_EPS_NAME_WORD = r"(?:(?-i:[A-Z][\w&.'’-]*)|&)"
_EPS_NAME = _EPS_NAME_WORD + r"(?:\s+" + _EPS_NAME_WORD + r"){0,4}"
_EPS_SUFFIX = r"(?:Inc|Corp|Corporation|Co|Company|plc|N\.V|Ltd|LLC|L\.P|S\.A|AG|SE)\.?"
_EPS_SELF = r"(?:the\s+)?(?:Company|Corporation)(?:['’]s)?"
_EPS_LABEL_TAIL = (
    _EPS_BASIS_TAG
    + r"(?:\s*,?\s+attributable\s+to\s+"
    r"(?![^()%:]*\b(?:excluding|before|after|from|growth|change|operations|continuing|"
    r"discontinued|charges|act|tax|pro[\s-]*forma|adjusted|restructuring|items|special|"
    r"non-?controlling|minority|interests?|preferred|participating|securities|class)\b)"
    r"(?:" + _EPS_HOLDERS + r"(?:\s+of\s+(?:" + _EPS_SELF
    + r"|(?:the\s+)?(?P<holder_parent>" + _EPS_NAME + r")(?:,?\s+" + _EPS_SUFFIX + r")?))?"
    r"|" + _EPS_SELF + r"(?:\s+" + _EPS_HOLDERS + r")?"
    r"|(?:the\s+)?(?P<parent>" + _EPS_NAME + r")(?:,?\s+" + _EPS_SUFFIX + r")?"
    r"(?:\s+" + _EPS_HOLDERS + r")?))?"
    + _EPS_BASIS_TAG
    + r"\s*:?\Z"
)
# The company a release reports for, named by its corporate form AND as the
# reporter: "Walmart Inc. (NYSE: WMT) today reported", "The Procter & Gamble
# Company (NYSE: PG)", "Microsoft Corp. announced".  The form is a word of its
# own, set as a company sets it, so "Co-Founder" and "a Delaware corporation"
# name no company.  Without the exchange ticker or the reports/announces verb a
# corporate name is anyone the release mentions first: an advisor, a merger
# partner, a subsidiary.  Each trailing run of the name's words is a name the
# release may use for it ("Acme Holdings, Inc." is also "Holdings").
_ISSUER_FORM = (
    r"(?:Inc|INC|Corp|CORP|Corporation|CORPORATION|Co|CO|Company|COMPANY|plc|PLC|"
    r"N\.V|Ltd|LTD|LLC|L\.P|S\.A|AG|SE)\.?(?![\w-])"
)
_ISSUER_CUE = (
    r"(?:,?\s*(?:\([^()]{0,40}\)\s*)?\(\s*(?:NYSE|NASDAQ|Nasdaq|Cboe|CBOE|TSX|LSE)\b[^()]{0,40}\)"
    r"|(?:\s*\([^()]{0,40}\))?\s+(?:today\s+)?(?:reports?|reported|announces?|announced|posts?|posted)\b)"
)
_ISSUER_MENTION_RE = re.compile(
    r"(?<![\w'’&.])(?<!\w-)(" + _EPS_NAME + r"),?\s+" + _ISSUER_FORM + _ISSUER_CUE
)
_ISSUER_SUFFIX_RE = re.compile(
    r"(?:,?\s+(?:inc|corp|corporation|co|company|plc|n\.v|ltd|llc|l\.p|s\.a|ag|se)\.?)+\Z"
)
# A name in an attribution ("attributable to common stockholders of Acme,
# Inc.", "Diluted EPS Attributable To Acme Co.") is the one an EPS line claims,
# so it cannot also name the issuer.  The attribution may sit before the name
# or inside the words the name pattern takes in ("EPS Attributable To Acme").
_ATTRIBUTED_NAME_RE = re.compile(r"(?i:\battributable\s+to\b)(?:[^.;:]|\.(?=\S)){0,160}\Z")
# A per-share scope row ("Earnings per share attributable to Walmart:") is the
# label its bare "Basic" and "Diluted" rows complete, so the whole row is
# closed, as a full EPS label is.  Before "per share" it may say only a basis,
# basic or diluted, and net income, earnings or loss: "Core earnings", "FFO",
# "Book value" and "SpinCo Inc. earnings" are other numbers.  After it, it
# may say "data", "of common stock", which of basic and diluted, and the closed
# EPS tail: "for Acme Operating LLC", "impact of", "- Class B", "guidance" and
# "(Predecessor)" name another entity or another number, and refuse.
_EPS_SCOPE_HEAD_RE = re.compile(
    r"\A(?:(?:GAAP|non-?GAAP|adjusted)\s+)?"
    r"(?:(?:basic|diluted)(?:\s*(?:and|&|/|,)\s*(?:basic|diluted))?\s+)?"
    r"(?:(?:net\s+)?(?:\(\s*loss\s*\)\s+)?(?:income|earnings|loss)"
    r"(?:\s*\(\s*(?:loss|income|earnings)\s*\))?\s+)?\Z",
    re.I,
)
_EPS_SCOPE_TAIL_RE = re.compile(
    r"(?:\s+(?:data|amounts|information|of\s+common\s+stock))?"
    r"(?:\s*[-,;:(]?\s*(?:basic|diluted)(?:\s*(?:and|&|/|,)\s*(?:basic|diluted))?\)?)?"
    + _EPS_LABEL_TAIL,
    re.I,
)
# "Earnings per share (1):", "Earnings per share*:", "Earnings per share1:":
# a footnote mark before the scope's colon.  ``_scope_names_eps`` reads the
# text after "per share", so a digit at its start is glued to "share".
_SCOPE_FOOTNOTE_RE = re.compile(
    r"(?:\s*\(\d{1,2}\)|\s*[*\u2020\u2021]{1,3}|(?:\A|(?<=[A-Za-z]))\d{1,2}"
    r"|[\u00b9\u00b2\u00b3\u2070\u2074-\u2079]{1,2})(?=\s*:?\s*\Z)"
)
# A multi-class issuer reports EPS once per class of common stock: "Class A
# common stock" rows under a "Basic Earnings Per Share" scope.  No class row is
# the release's EPS by its label, and the unqualified "Earnings per share" of
# the summary, which says which class is, names neither basic nor diluted.
# Both read as internal candidates that only _resolve_share_classes turns into
# a roster figure; whatever it cannot resolve never reaches the caller.
_SHARE_CLASS_LABEL_RE = re.compile(
    r"\Aclass\s+[a-z](?:-\d{1,2})?\s+(?:common\s+|ordinary\s+)?(?:stock|shares?)\Z", re.I
)
_CLASS_EPS_SCOPE_RE = re.compile(
    r"\A(?:GAAP\s+|non-?GAAP\s+|adjusted\s+)?(basic|diluted)\s+"
    r"(?:(?:net\s+)?(?:income|earnings|loss)\s+per\s+(?:common\s+)?share|EPS)\s*:?\Z",
    re.I,
)
_HEADLINE_EPS_LABEL_RE = re.compile(
    r"\A(?:GAAP\s+|non-?GAAP\s+|adjusted\s+)?(?:net\s+)?(?:income|earnings)\s+per\s+"
    r"(?:common\s+)?share" + _EPS_LABEL_TAIL,
    re.I,
)
_BASIC_OR_DILUTED_RE = re.compile(r"\b(?:basic|diluted)\b", re.I)
_HEADLINE_EPS = "_headline_eps"
_CLASS_EPS_PREFIX = "_class_eps:"


@dataclass(frozen=True)
class _RowRule:
    """A label pattern and what concept it produces for each observed kind."""

    pattern: re.Pattern[str]
    kind_to_concept: Mapping[str, str]
    scope_required: re.Pattern[str] | None = None
    scope_forbidden: re.Pattern[str] | None = None


_ROW_RULES: tuple[_RowRule, ...] = (
    _RowRule(
        re.compile(
            r"\A(?:total\s+)?(?:net\s+)?(?:operating\s+)?(?:sales|revenues?)\Z|"
            r"\A(?:total\s+)?sales\s+to\s+customers\Z",
            re.I,
        ),
        {ValueKind.MONETARY.value: "revenue"},
    ),
    _RowRule(
        re.compile(r"\Agross\s+(?:margin|profit)(?:\s+percentage|\s+%)?\Z", re.I),
        {ValueKind.MONETARY.value: "gross_profit", ValueKind.PERCENT.value: "gross_margin_pct"},
    ),
    _RowRule(
        re.compile(r"\A(?:total\s+)?operating\s+(?:income|margin)\Z|\Aincome\s+from\s+operations\Z", re.I),
        {ValueKind.MONETARY.value: "operating_income", ValueKind.PERCENT.value: "operating_margin_pct"},
    ),
    _RowRule(
        re.compile(r"\Anet\s+(?:income|loss)(?:\s*\(loss\))?\Z", re.I),
        {ValueKind.MONETARY.value: "net_income"},
    ),
    _RowRule(
        re.compile(
            r"\A(?:net\s+)?cash\s+(?:generated\s+by|provided\s+by|from|used\s+in)\s+"
            r"operating\s+activities\Z",
            re.I,
        ),
        {ValueKind.MONETARY.value: "operating_cash_flow"},
    ),
    _RowRule(
        re.compile(
            r"\A(?:payments\s+for\s+)?(?:acquisition\s+of\s+|purchases?\s+of\s+)?"
            r"(?:property,?\s+plant\s+and\s+equipment|property\s+and\s+equipment|"
            r"capital\s+expenditures)\Z",
            re.I,
        ),
        {ValueKind.MONETARY.value: "capital_expenditures"},
    ),
    # Bare Basic/Diluted: valid ONLY under a per-share scope and never under a
    # share-count scope, where the identical labels carry share counts.
    _RowRule(
        re.compile(r"\Abasic\Z", re.I),
        {ValueKind.PER_SHARE.value: "eps_basic"},
        scope_required=_PER_SHARE_SCOPE_RE,
        scope_forbidden=_SHARE_COUNT_SCOPE_RE,
    ),
    _RowRule(
        re.compile(r"\Adiluted\Z", re.I),
        {ValueKind.PER_SHARE.value: "eps_diluted"},
        scope_required=_PER_SHARE_SCOPE_RE,
        scope_forbidden=_SHARE_COUNT_SCOPE_RE,
    ),
    _RowRule(
        re.compile(
            r"\A(?:adjusted\s+|non-?GAAP\s+)?basic\s+(?:net\s+)?"
            r"(?:income|earnings|loss)\s+per\s+(?:common\s+)?share" + _EPS_LABEL_TAIL,
            re.I,
        ),
        {ValueKind.PER_SHARE.value: "eps_basic"},
        scope_forbidden=_SHARE_COUNT_SCOPE_RE,
    ),
    _RowRule(
        re.compile(
            r"\A(?:adjusted\s+|non-?GAAP\s+)?diluted\s+(?:net\s+)?"
            r"(?:income|earnings|loss)\s+per\s+(?:common\s+)?share" + _EPS_LABEL_TAIL,
            re.I,
        ),
        {ValueKind.PER_SHARE.value: "eps_diluted"},
        scope_forbidden=_SHARE_COUNT_SCOPE_RE,
    ),
    # "Diluted EPS", "Adjusted diluted EPS", "EPS (diluted)", "EPS - diluted".
    _RowRule(
        re.compile(
            r"\A(?:adjusted\s+|non-?GAAP\s+)?basic\s+EPS" + _EPS_LABEL_TAIL
            + r"|\AEPS\s*[-–—(]\s*basic\)?\Z",
            re.I,
        ),
        {ValueKind.PER_SHARE.value: "eps_basic"},
        scope_forbidden=_SHARE_COUNT_SCOPE_RE,
    ),
    _RowRule(
        re.compile(
            r"\A(?:adjusted\s+|non-?GAAP\s+)?diluted\s+EPS" + _EPS_LABEL_TAIL
            + r"|\AEPS\s*[-–—(]\s*diluted\)?\Z",
            re.I,
        ),
        {ValueKind.PER_SHARE.value: "eps_diluted"},
        scope_forbidden=_SHARE_COUNT_SCOPE_RE,
    ),
)


# ─────────────────────────────────────────────────────────────────────────────
# Public records
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReleaseFigure:
    """One number that survived every requirement, with its exact location."""

    concept: str
    label: str
    value: float
    basis: str
    units: str
    currency: str | None
    period_label: str
    period_end: str
    receipt: SpanReceipt
    scale_factor: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "label": self.label,
            "value": self.value,
            "basis": self.basis,
            "units": self.units,
            "currency": self.currency,
            "period_label": self.period_label,
            "period_end": self.period_end,
            "scale_factor": self.scale_factor,
            "receipt": self.receipt.to_dict(),
        }


@dataclass(frozen=True)
class TypedAbsence:
    """A figure that is NOT present, and why.

    There is deliberately no ``value`` field.  An absence that carried a null
    would be one careless ``or 0`` away from becoming a reported zero.
    """

    concept: str
    reason: str
    detail: str
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "reason": self.reason,
            "detail": self.detail,
            "label": self.label,
        }


class BindingOutcome(str, Enum):
    """Why a release bound what it bound — so an empty figure list is never silent.

    "The release reports no figures" and "the parser could not read this
    release's layout" both leave ``figures`` empty.  The outcome says which,
    from the structure the binder actually walked.
    """

    FIGURES_BOUND = "figures_bound"
    NO_BLOCKS = "no_blocks"                  # the body normalized to nothing
    NO_TABLES = "no_tables"                  # prose only; nothing tabular to read
    NO_CANDIDATE_ROWS = "no_candidate_rows"  # tables, but no row names a roster concept
    NO_PERIOD_COLUMNS = "no_period_columns"  # roster rows, none under a header that names a date
    ALL_REFUSED = "all_refused"              # roster rows under dated headers, every one refused


@dataclass(frozen=True)
class ReleaseFigureSet:
    """Everything read out of one release body, plus everything refused.

    ``outcome`` and the counts are None on a set built by hand; the extractor
    always fills them.
    """

    figures: tuple[ReleaseFigure, ...] = ()
    absences: tuple[TypedAbsence, ...] = ()
    schema: str = FIGURES_SCHEMA
    authority: str = AUTHORITY
    outcome: str | None = None
    table_count: int | None = None
    period_table_count: int | None = None
    candidate_row_count: int | None = None

    def concepts(self) -> frozenset[str]:
        return frozenset(figure.concept for figure in self.figures)

    def figure(self, concept: str, *, basis: str | None = None) -> ReleaseFigure | None:
        for item in self.figures:
            if item.concept == concept and (basis is None or item.basis == basis):
                return item
        return None

    def absence(self, concept: str) -> TypedAbsence | None:
        for item in self.absences:
            if item.concept == concept:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "authority": self.authority,
            "figures": [item.to_dict() for item in self.figures],
            "absences": [item.to_dict() for item in self.absences],
            "bound_count": len(self.figures),
            "absent_count": len(self.absences),
            "outcome": self.outcome,
            "table_count": self.table_count,
            "period_table_count": self.period_table_count,
            "candidate_row_count": self.candidate_row_count,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Small deterministic readers
# ─────────────────────────────────────────────────────────────────────────────

def parse_numeric(text: str) -> tuple[float, str] | None:
    """Return ``(value, kind_hint)`` for a statement cell, or None.

    ``(50)`` is negative fifty — the accounting convention, not a footnote:
    ``_FOOTNOTE_CELL_RE`` is applied by the caller before this, so a bare
    ``(1)``/``(2)`` marker never reaches here.
    """
    raw = text.strip()
    if not raw:
        return None
    if not (_NUMERIC_CELL_RE.match(raw) or _BARE_NUMERIC_RE.match(raw)):
        return None
    kind = ValueKind.PERCENT.value if raw.endswith("%") else ""
    body = raw.rstrip("%")
    negative = body.startswith("(") and body.endswith(")")
    if negative:
        body = body[1:-1]
    body = body.replace(",", "")
    if not body or body in {"-", "."}:
        return None
    try:
        value = float(body)
    except ValueError:
        return None
    if negative:
        value = -value
    return value, kind


def parse_statement_date(text: str) -> str | None:
    match = _DATE_CELL_RE.match(text.strip())
    if match is None:
        return None
    for fmt in ("%B %d %Y", "%b %d %Y"):
        try:
            parsed = datetime.strptime(
                f"{match.group(1)} {match.group(2)} {match.group(3)}", fmt
            )
        except ValueError:
            continue
        return parsed.date().isoformat()
    return None


@dataclass
class _Context:
    """Document-order state: what the last caption declared."""

    units: str | None = None
    units_source: str = ""
    currency_from_caption: str | None = None
    basis: str | None = None
    basis_source: str = ""
    # Names the release gives a company by its corporate form ("Walmart Inc."):
    # the only proper names an EPS line may be attributed to.
    issuers: frozenset[str] = frozenset()

    def observe(self, text: str) -> None:
        source, text = text, _fold_dashes(text)
        units = _UNITS_CAPTION_RE.search(text)
        if units:
            self.units = _UNIT_BY_SCALE[(units.group(1) or units.group(2)).lower()]
            self.units_source = source
            if "$" in units.group(0):
                self.currency_from_caption = "USD"
        if _CURRENCY_WORD_RE.search(text):
            self.currency_from_caption = "USD"
        comparison = _BASIS_COMPARISON_RE.search(text)
        if comparison:
            # A comparison declares no basis.  The section stays what it was
            # only when it is the basis compared against and the rest of the
            # text is filler or periods; anything else names what is being
            # compared ("Core Results Compared With GAAP"), and that is not
            # this section, so the basis is unknown.
            compared = (Basis.GAAP.value if comparison.group(1).lower() == "gaap"
                        else Basis.NON_GAAP.value)
            remainder = f"{text[:comparison.start()]} {text[comparison.end():]}"
            same = {"gaap"} if compared == Basis.GAAP.value else {"non-gaap", "nongaap", "adjusted"}
            names_other = any(
                not (token in _COMPARISON_FILLER or token in same
                     or _COMPARISON_PERIOD_TOKEN_RE.match(token))
                for token in _COMPARISON_TOKEN_RE.findall(remainder.lower())
            )
            if self.basis != compared or names_other or _names_basis(remainder):
                self.basis, self.basis_source = None, ""
            return
        # Non-GAAP is checked first: "Reconciliation of GAAP to non-GAAP"
        # matches both patterns and is a non-GAAP scope.
        if _NON_GAAP_CAPTION_RE.search(text):
            declared = Basis.NON_GAAP.value
        elif _GAAP_CAPTION_RE.search(text):
            declared = None if _ADJUSTED_QUALIFIER_RE.search(text) else Basis.GAAP.value
        else:
            return
        if declared is not None and _is_caption_shaped(text):
            self.basis, self.basis_source = declared, source
        else:
            # Prose that mentions a basis declares nothing, but it does tell us
            # the section is no longer the one the last caption opened: a
            # footnote about non-GAAP measures under a GAAP statement is where a
            # release turns to its non-GAAP tables.  Unknown, not the old basis.
            # A qualified statement title closes the section the same way.
            self.basis, self.basis_source = None, ""

    def reset_table_scope(self, *, entry_basis: str | None, reported: bool) -> None:
        """Forget the per-table captions once their table is consumed.

        ``(In millions)`` is a typesetting statement about ONE table and never
        carries to the next; a release that omits it above a supplemental table
        has not declared units there, and the figures must land as absences.

        A GAAP / non-GAAP caption ABOVE a table is a section header and governs
        everything until the next one, so it is not reset here.  A basis
        declared INSIDE a table that reported values (a title row, a header
        cell, a "Reconciliation of cash ..." scope row in a GAAP cash-flow
        statement) speaks for that table only.  Once the table is consumed the
        basis is unknown rather than reverted: an untitled table after a
        reconciliation is as likely non-GAAP as GAAP.  A table that reported no
        values is typesetting a caption and is read as one.
        """
        self.units = None
        self.units_source = ""
        self.currency_from_caption = None
        if reported and self.basis != entry_basis:
            self.basis, self.basis_source = None, ""


def _is_caption_shaped(text: str) -> bool:
    stripped = text.strip()
    return len(stripped.split()) <= _CAPTION_MAX_WORDS and not _SENTENCE_PUNCTUATION_RE.search(stripped)


def _names_basis(text: str) -> bool:
    return bool(_NON_GAAP_CAPTION_RE.search(text) or _GAAP_CAPTION_RE.search(text)
                or _NON_GAAP_INLINE_RE.search(text))


def _issuer_names(document: DisclosureDocument) -> frozenset[str]:
    # The issuer is the first company the release names as its reporter, by
    # its corporate form with an exchange ticker or a reports/announces verb:
    # a release opens on its own name, in prose or in the layout table some
    # releases set their prose in.  A company named after it (a subsidiary, a
    # spin-off, an operating company) is not the issuer, nor is one named
    # without that cue.  "The Company" names no one, and a name an attribution
    # gives is what is being checked, so "Diluted EPS attributable to Goodwill
    # Impairment Co." cannot vouch for itself.  A release whose first such
    # company is not the filer would vouch for that company's attributions;
    # binding the issuer to the filer's CIK name is a recorded residual.
    for block in document.blocks:
        text = _fold_dashes(block.text)
        for mention in _ISSUER_MENTION_RE.finditer(text):
            words = _normalize_issuer(mention.group(1)).split()
            if not words or _ATTRIBUTED_NAME_RE.search(text, max(0, mention.start() - 160), mention.end(1)):
                continue
            return frozenset(" ".join(words[start:]) for start in range(len(words)))
    return frozenset()


def _normalize_issuer(name: str) -> str:
    # Every caller passes text whose dashes are already folded.
    text = " ".join(name.lower().replace("’", "'").split())
    # "JPMorgan Chase & Co." is "JPMorgan Chase", not "JPMorgan Chase &".
    text = _ISSUER_SUFFIX_RE.sub("", text).rstrip(",.& ")
    # "The Company" and "Our Company" are a self-reference, not a name.
    return "" if text in {"the", "our", "this"} else text[4:] if text.startswith("the ") else text


def _attributes_to_another(match: re.Match[str], issuers: frozenset[str]) -> bool:
    groups = match.groupdict()
    named = groups.get("parent") or groups.get("holder_parent")
    return bool(named) and _normalize_issuer(named) not in issuers


def _scope_names_eps(scope: str, issuers: frozenset[str]) -> bool:
    """Whether a per-share scope row names the issuer's reported EPS."""
    per_share = _PER_SHARE_SCOPE_RE.search(scope)
    if per_share is None or not _EPS_SCOPE_HEAD_RE.match(scope[:per_share.start()]):
        return False
    tail = _EPS_SCOPE_TAIL_RE.match(_SCOPE_FOOTNOTE_RE.sub("", scope[per_share.end():]))
    return tail is not None and not _attributes_to_another(tail, issuers)


_INLINE_CURRENCY_RE = re.compile(r"\A(US\$|\$|€|£|¥)\s*")


@dataclass(frozen=True)
class _Column:
    """One period column: where it sits in the header grid, and its period."""

    start: int
    end: int
    period_label: str
    period_end: str


@dataclass(frozen=True)
class _HeaderLayout:
    """The header grid of one table.

    ``slots`` are every value column the header names, in order: the dated
    ``columns`` plus the undated ones ("% Change", an unconverted year) that
    still take a value cell in each data row.  A row is mapped onto the slots,
    never onto the dated columns alone, so a "% Change" cell between two
    periods cannot shift a value into the wrong period.
    """

    columns: tuple[_Column, ...] = ()
    slots: tuple[tuple[int, int], ...] = ()
    width: int = 0
    # Index of the first row below the last row that names a period.
    body_start: int = 0
    # Period columns a sub-header splits into several amounts ("As Reported
    # (GAAP) | Adjustments | As Adjusted (non-GAAP)"): one period, many values.
    split: frozenset[tuple[int, int]] = frozenset()


@dataclass(frozen=True)
class _ValueCell:
    value: float
    kind: str
    currency: str | None
    literals: tuple[str, ...]
    open_paren: bool = False


@dataclass
class _Group:
    """One value position in a data row: its cells' grid span and what they read.

    ``value`` None is a placeholder ("—", "n/m") — a cell that holds a column's
    place but reports nothing — or, with ``unclosed``, a value whose sign
    cannot be read.
    """

    start: int
    end: int
    cell: TableCell | None = None
    value: float | None = None
    kind: str = ""
    currency: str | None = None
    literals: tuple[str, ...] = ()
    open_paren: bool = False
    unclosed: bool = False


@dataclass
class _TableStats:
    tables: int = 0
    period_tables: int = 0
    candidate_rows: int = 0
    dated_candidate_rows: int = 0


def _non_empty(cells: Sequence[TableCell]) -> list[TableCell]:
    return [cell for cell in cells if cell.text.strip()]


def _grid(cells: Sequence[TableCell]) -> list[tuple[int, int, TableCell]]:
    """Each cell with its ``[start, end)`` grid position, honouring colspan."""
    placed: list[tuple[int, int, TableCell]] = []
    position = 0
    for cell in cells:
        span = max(1, cell.colspan)
        placed.append((position, position + span, cell))
        position += span
    return placed


def _parse_value_cell(text: str) -> _ValueCell | None:
    """Read one value cell, including the currency-led forms ``parse_numeric`` refuses.

    ``$96,221``, ``$(0.12)`` and ``($0.12)`` carry their currency inline;
    ``$(0.12`` is the opening half of a negative whose ``)`` sits in the next
    cell.  ``literals`` are what the receipt looks for, most exact first: the
    raw cell text, then the bare number when an entity or space sits between
    the symbol and the digits in the source.
    """
    raw = text.strip()
    if not raw or _FOOTNOTE_CELL_RE.match(raw):
        return None
    parsed = parse_numeric(raw)
    if parsed is not None:
        return _ValueCell(parsed[0], parsed[1], None, (raw,))
    body, negative, currency = raw, False, None
    if body.startswith("(") and body.endswith(")"):
        body, negative = body[1:-1].strip(), True
    symbol = _INLINE_CURRENCY_RE.match(body)
    if symbol:
        currency = _CURRENCY_SYMBOL[symbol.group(1)]
        body = body[symbol.end():]
    if not body or (currency is None and not negative):
        return None
    literals = tuple(dict.fromkeys((raw, body)))
    parsed = parse_numeric(body)
    if parsed is not None:
        return _ValueCell(-parsed[0] if negative else parsed[0], parsed[1], currency, literals)
    if body.startswith("(") and not negative:
        parsed = parse_numeric(body + ")")
        if parsed is not None:
            return _ValueCell(parsed[0], parsed[1], currency, literals, open_paren=True)
    return None


def _is_value_cell(text: str) -> bool:
    raw = text.strip()
    if _parse_value_cell(raw) is not None:
        return True
    # "(0.12" with no currency: the open half of a negative split across cells.
    return raw.startswith("(") and parse_numeric(raw + ")") is not None


def _row_is_header(cells: Sequence[TableCell]) -> bool:
    populated = _non_empty(cells)
    if not populated:
        return True
    # "$ | (5)" is minus five, not a footnote marker: see ``_row_groups``.
    numeric = [
        cell for previous, cell in zip((None, *populated), populated)
        if _is_value_cell(cell.text) or (
            previous is not None and previous.text.strip() in _CURRENCY_SYMBOL
            and _FOOTNOTE_CELL_RE.match(cell.text.strip())
        )
    ]
    if not numeric:
        return True
    # A row of fiscal years ("2025   2024") under "September 30," is a column
    # header, not data — unless a currency or a roster label says otherwise.
    if not all(_YEAR_CELL_RE.match(cell.text.strip()) for cell in numeric):
        return False
    if any(
        cell.text.strip() in _CURRENCY_SYMBOL or _INLINE_CURRENCY_RE.match(cell.text.strip())
        for cell in populated
    ):
        return False
    first = next(
        (cell for cell in populated if not _FOOTNOTE_CELL_RE.match(cell.text.strip())), None
    )
    if first is None or first in numeric:
        return True
    label = _fold_dashes(_FOOTNOTE_SUFFIX_RE.sub("", first.text.strip()))
    return not any(rule.pattern.match(label) for rule in _ROW_RULES)


def _iso_date(month: str, day: str, year: str) -> str | None:
    try:
        return datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date().isoformat()
    except ValueError:
        return None


def _classify_header_cell(text: str) -> tuple[str, str, str, bool]:
    """Return ``(kind, label, value, has_prefix)`` for one header cell.

    kind is ``date`` (value = ISO period end), ``md`` (a month and day awaiting
    the year row below; value = "Month Day"), ``prefix`` ("Three Months
    Ended"), ``year`` (value = the year), or ``other`` ("% Change").
    """
    full = parse_statement_date(text)
    if full is not None:
        return "date", text, full, False
    slash = _SLASH_DATE_RE.match(text)
    if slash is not None:
        try:
            iso = datetime(
                int(slash.group(3)), int(slash.group(1)), int(slash.group(2))
            ).date().isoformat()
        except ValueError:
            iso = None
        if iso is not None:
            return "date", text, iso, False
    tail = _DATE_TAIL_RE.search(text)
    if tail is not None and _PERIOD_PREFIX_RE.search(text[: tail.start()]):
        iso = _iso_date(tail.group(1), tail.group(2), tail.group(3))
        if iso is not None:
            return "date", text, iso, True
    month_day = _MONTH_DAY_TAIL_RE.search(text)
    if month_day is not None:
        head = text[: month_day.start()].strip()
        if not head or _PERIOD_PREFIX_RE.search(head):
            return "md", text, f"{month_day.group(1)} {month_day.group(2)}", bool(head)
    if _PERIOD_PREFIX_RE.search(text):
        return "prefix", text, "", True
    year = _FOOTNOTE_SUFFIX_RE.sub("", text)
    if _YEAR_CELL_RE.match(year):
        return "year", text, year, False
    return "other", text, "", False


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _covering(span: tuple[int, int], candidates: Sequence[tuple[int, int, Any]]) -> Any:
    """The candidate whose span best overlaps ``span``; the sole one if none does."""
    best = max(candidates, key=lambda item: _overlap(span, item[:2]), default=None)
    if best is not None and _overlap(span, best[:2]) > 0:
        return best
    return candidates[0] if len(candidates) == 1 else None


def _header_layout(block: DisclosureBlock) -> _HeaderLayout:
    if block.table is None:
        return _HeaderLayout()
    rows: list[list[tuple[int, int, TableCell]]] = []
    for row in block.table.rows:
        if not _row_is_header(row):
            break
        rows.append(_grid(row))
    body_start = 0
    width = max((placed[-1][1] for placed in rows if placed), default=0)

    prefixes: list[tuple[int, int, str]] = []
    month_days: list[tuple[int, int, tuple[str, str, bool]]] = []
    dated: list[tuple[int, int, tuple[str, str, bool], int]] = []
    years: list[tuple[int, int, str, int]] = []
    others: list[tuple[int, int, str, int]] = []
    for index, placed in enumerate(rows):
        for start, end, cell in placed:
            text = cell.text.strip()
            if not text:
                continue
            kind, label, value, has_prefix = _classify_header_cell(text)
            if kind != "other":
                body_start = index + 1
            if kind == "date":
                dated.append((start, end, (label, value, has_prefix), index))
            elif kind == "md":
                month_days.append((start, end, (label, value, has_prefix)))
            elif kind == "prefix":
                prefixes.append((start, end, label))
            elif kind == "year":
                years.append((start, end, value, index))
            else:
                others.append((start, end, label, index))

    def with_prefix(span: tuple[int, int], label: str, has_prefix: bool) -> str:
        if has_prefix:
            return label
        prefix = _covering(span, prefixes)
        return f"{prefix[2]} {label}" if prefix is not None else label

    by_start: dict[int, tuple[_Column, int]] = {}
    for start, end, (label, iso, has_prefix), row in dated:
        column = _Column(start, end, with_prefix((start, end), label, has_prefix), iso)
        by_start[start] = (column, row)
    leftover: list[tuple[int, int]] = []
    for start, end, year, row in years:
        anchor = _covering((start, end), month_days)
        iso = None
        if anchor is not None:
            md_label, md_value, md_prefixed = anchor[2]
            month, day = md_value.split(" ")
            iso = _iso_date(month, day, year)
        if iso is None or start in by_start:
            if start not in by_start:
                leftover.append((start, end))
            continue
        label = with_prefix(anchor[:2], f"{md_label.rstrip(',')}, {year}", md_prefixed)
        by_start[start] = (_Column(start, end, label, iso), row)
    if not by_start:
        return _HeaderLayout(width=width, body_start=body_start)

    # Sub-headers set under one period column split it.  "Amount | % of Net
    # Sales" narrows the period to its one amount sub-column; "As Reported
    # (GAAP) | Impact | As Adjusted (non-GAAP)" holds several amounts for the
    # same period, and no position in it is THE value for that period.
    columns: list[_Column] = []
    sub_slots: list[tuple[int, int]] = []
    split: set[tuple[int, int]] = set()
    for start in sorted(by_start):
        column, row = by_start[start]
        subs = [
            (sub_start, sub_end, text) for sub_start, sub_end, text, sub_row in others
            if sub_row > row and column.start <= sub_start and sub_end <= column.end
        ]
        if len(subs) >= 2:
            amounts = [sub for sub in subs if not _PERCENT_HEADER_RE.search(sub[2])
                       and not _CHANGE_HEADER_RE.search(sub[2])]
            # The one sub-column left must SAY it is the period's amount.
            # "Adjusted | Change" or "Constant Currency | Reported Change"
            # leaves a column that is some other measure of the period.
            if len(amounts) == 1 and (_AMOUNT_HEADER_RE.match(amounts[0][2])
                                      or _NON_GAAP_CAPTION_RE.search(amounts[0][2])):
                column = _Column(amounts[0][0], amounts[0][1], column.period_label,
                                 column.period_end)
                sub_slots.extend(sub[:2] for sub in subs if sub is not amounts[0])
            elif amounts:
                # Each sub-column still takes a position in every data row.
                split.add((column.start, column.end))
                sub_slots.extend(sub[:2] for sub in subs)
        columns.append(column)

    first = columns[0].start
    spans = [(column.start, column.end) for column in columns]
    barriers = {
        (start, end)
        for start, end in [item[:2] for item in others] + leftover
        if start > first and not any(_overlap((start, end), span) for span in spans)
    }
    # A caption spanning two undated sub-columns is not itself a column.
    barriers = {
        outer for outer in barriers
        if not any(inner != outer and outer[0] <= inner[0] and inner[1] <= outer[1]
                   for inner in barriers)
    }
    slots = tuple(sorted(
        {span for span in spans if span not in split} | barriers | set(sub_slots)
    ))
    return _HeaderLayout(columns=tuple(columns), slots=slots, width=width,
                         body_start=body_start, split=frozenset(split))


def _columns_for_table(block: DisclosureBlock) -> tuple[_Column, ...]:
    """Derive the period each value column reports, from the header rows only.

    A table whose header never names a date yields no columns, and every figure
    in it becomes a ``period_undeclared`` absence.  That is the correct answer:
    a revenue number with no period is not a fact about a quarter.
    """
    return _header_layout(block).columns


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return slug or "unnamed"


# ─────────────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────────────

def _receipt_or_absence(
    *,
    document: DisclosureDocument,
    cell: TableCell,
    literals: Sequence[str],
    concept: str,
    label: str,
    absences: list[TypedAbsence],
) -> SpanReceipt | None:
    first_error: ReceiptError | None = None
    for literal in literals:
        try:
            return receipt_for_literal(
                source=document.raw_source,
                source_sha256=document.source_sha256,
                search_start=cell.source_span.char_start,
                search_end=cell.source_span.char_end,
                literal=literal,
            )
        except ReceiptError as exc:
            first_error = first_error or exc
    absences.append(
        TypedAbsence(
            concept=concept,
            reason=AbsenceReason.VALUE_AMBIGUOUS.value,
            detail=f"no unique source location for {literals[0]!r}: {first_error}",
            label=label,
        )
    )
    return None


def _row_groups(placed: Sequence[tuple[int, int, TableCell]]) -> list[_Group]:
    """The value positions of one data row, after its label cell.

    A currency symbol in its own cell, a value, and a trailing ")" or "%" in
    the next cell are one position: Workiva typesets "$ | (0.12 | )" as three
    cells under one column header.
    """
    groups: list[_Group] = []
    pending: tuple[str, int] | None = None
    for start, end, cell in placed:
        text = cell.text.strip()
        if not text:
            continue
        if text in _CURRENCY_SYMBOL:
            pending = (_CURRENCY_SYMBOL[text], start)
            continue
        if _FOOTNOTE_CELL_RE.match(text) and pending is None:
            # "(1)" alone is a footnote marker, but "$ | (5)" is minus five:
            # a currency symbol announces the next cell as a value.
            continue
        if text in _SUFFIX_CELLS:
            if groups:
                last = groups[-1]
                last.end = end
                if "%" in text and last.value is not None:
                    last.kind = ValueKind.PERCENT.value
                if ")" in text:
                    last.open_paren = False
            continue
        group_start = pending[1] if pending else start
        parsed = _parse_value_cell(text)
        if parsed is None and pending is not None and _FOOTNOTE_CELL_RE.match(text):
            signed = parse_numeric(text)
            if signed is not None:
                parsed = _ValueCell(signed[0], signed[1], None, (text,))
        if parsed is None and text.startswith("("):
            closed = parse_numeric(text + ")")
            if closed is not None:
                parsed = _ValueCell(closed[0], closed[1], None, (text,), open_paren=True)
        if parsed is not None:
            groups.append(_Group(
                start=group_start,
                end=end,
                cell=cell,
                value=parsed.value,
                kind=parsed.kind,
                currency=parsed.currency or (pending[0] if pending else None),
                literals=parsed.literals,
                open_paren=parsed.open_paren,
            ))
        elif _PLACEHOLDER_CELL_RE.match(text) or any(g.value is not None for g in groups):
            groups.append(_Group(start=group_start, end=end))
        pending = None
    for group in groups:
        # "(0.12" whose ")" never arrived is not a number we can sign.
        if group.open_paren:
            group.value, group.cell, group.literals, group.open_paren = None, None, (), False
            group.unclosed = True
    return groups


def _select_group(
    groups: Sequence[_Group],
    layout: _HeaderLayout,
    target: _Column | None,
    row_width: int,
) -> tuple[_Group, _Column | None, AbsenceReason | None, str]:
    """Pick the value position that reports ``target``, or say why none does."""
    values = [group for group in groups if group.value is not None]
    if target is None:
        return (values[0], None, AbsenceReason.PERIOD_UNDECLARED,
                "the table header names no period end date")
    wanted = (target.start, target.end)
    if wanted in layout.split:
        return values[0], None, AbsenceReason.VALUE_AMBIGUOUS, (
            "a sub-header splits the period column into several amounts "
            "(as reported / adjustments / as adjusted); refusing to pick one"
        )
    if row_width == layout.width:
        # Same grid as the header: a value belongs to the slot it sits under.
        under = []
        for group in groups:
            span = (group.start, group.end)
            best = max(
                layout.slots,
                key=lambda slot: (_overlap(span, slot), -abs(sum(span) - sum(slot))),
            )
            if best == wanted and _overlap(span, best) > 0:
                under.append(group)
        amounts = [group for group in under if group.kind != ValueKind.PERCENT.value]
        if len(amounts) > 1:
            return values[0], None, AbsenceReason.VALUE_AMBIGUOUS, (
                f"{len(amounts)} values sit side by side under the period column; "
                "refusing to pick one"
            )
        if under:
            return (amounts or under)[0], target, None, ""
        return (values[0], None, AbsenceReason.PERIOD_UNDECLARED,
                "value cell does not sit under the period column it maps to")
    # A different grid (Workiva drops the "$" cells on inner rows): map by
    # order, and only when the row has exactly one position per header slot.
    # A row with MORE positions carries a column the header does not name (a
    # "Note" reference, a leading line number), and counting from the left
    # would read that column as the first period.
    if len(groups) != len(layout.slots):
        return values[0], None, AbsenceReason.PERIOD_UNDECLARED, (
            f"the row has {len(groups)} value positions and the header has "
            f"{len(layout.slots)} columns; refusing to guess which period each reports"
        )
    return groups[layout.slots.index(wanted)], target, None, ""


def _is_scope_caption(row: Sequence[TableCell], index: int, layout: _HeaderLayout) -> bool:
    """A value-less row below the period header, set in the label column only.

    "(1) Net sales by reportable segment:" sits under the dates and before the
    first value row; it scopes the rows beneath it, it does not head a column.
    A units caption in the same place ("(in millions, except per share)") stays
    a caption: as a scope it would read every row beneath it as per-share.
    """
    if not layout.columns or index < layout.body_start:
        return False
    placed = [
        (start, cell.text.strip()) for start, _end, cell in _grid(row)
        if cell.text.strip() and not _FOOTNOTE_CELL_RE.match(cell.text.strip())
    ]
    if not placed or any(start >= layout.columns[0].start for start, _text in placed):
        return False
    return not _UNITS_CAPTION_RE.search(" ".join(text for _start, text in placed))


def _extract_table(
    document: DisclosureDocument,
    block: DisclosureBlock,
    context: _Context,
    figures: list[ReleaseFigure],
    absences: list[TypedAbsence],
    stats: _TableStats,
) -> bool:
    """Bind one table's rows; True when any row reported a value."""
    if block.table is None:
        return False
    reported = False
    layout = _header_layout(block)
    stats.tables += 1
    target: _Column | None = None
    if layout.columns:
        stats.period_tables += 1
        # The current period is the latest period end the header names.  The
        # first column with it wins, so the quarter precedes the year-to-date
        # column that ends on the same day.
        latest = max(column.period_end for column in layout.columns)
        target = next(column for column in layout.columns if column.period_end == latest)
    column_currency: dict[int, str] = {}
    scope = ""
    # "Header" is a position, not a shape.  A value-less row BEFORE the first
    # data row is a column header; the identical shape AFTER it is a scope
    # caption ("Earnings per share:", "(1) Net sales by reportable segment:").
    # Conflating the two silently drops every scope in the table, which drops
    # EPS (the bare Basic/Diluted labels need their scope) and every segment.
    seen_data_row = False

    for index, row in enumerate(block.table.rows):
        populated = _non_empty(row)
        if not populated:
            continue
        if (not seen_data_row and _row_is_header(row)
                and not _is_scope_caption(row, index, layout)):
            # Header rows may still carry a units caption typeset inside the
            # table rather than above it.
            for cell in populated:
                context.observe(cell.text)
            continue
        seen_data_row = True

        placed = _grid(row)
        row_width = placed[-1][1]
        placed = [item for item in placed if item[2].text.strip()]
        # Label: the first non-empty cell, stepping over a bare footnote marker
        # — EDGAR typesets "(1)" in its own cell before the real label.
        cursor = 0
        while cursor < len(placed) and _FOOTNOTE_CELL_RE.match(placed[cursor][2].text.strip()):
            cursor += 1
        if cursor >= len(placed):
            continue
        label = _FOOTNOTE_SUFFIX_RE.sub("", placed[cursor][2].text.strip())
        label = _GLUED_FOOTNOTE_RE.sub("", label)
        groups = _row_groups(placed[cursor + 1:])

        if not any(group.value is not None for group in groups):
            # A label-only row is a scope caption: "Earnings per share:",
            # "(1) Net sales by reportable segment:".  A row of placeholders
            # only ("Restructuring  —  —") reports nothing and changes no scope.
            if not groups and label:
                scope = label
                context.observe(label)
            continue
        reported = True

        # Only the current-period column is bound.  A prior-year column is a
        # different period and would need its own concept namespace.
        group, column, refusal_reason, refusal = _select_group(groups, layout, target, row_width)
        if group.value is None or group.cell is None:
            # The current-period cell holds a placeholder ("—", "n/m"): the row
            # names a figure the release does not report for this period.  It
            # is a candidate row with a finding, not a row that never existed,
            # or a table of placeholders would read as "no candidate rows".
            # A percent beside it ("— | 12%") is a change column and says
            # nothing about the kind of the missing amount.
            kind_hint = next((item.kind for item in groups if item.value is not None
                              and item.kind != ValueKind.PERCENT.value), "")
            concept = _concept_for(label=label, scope=scope, issuers=context.issuers, kind=_observed_kind(
                kind_hint=kind_hint, label=label, scope=scope, currency=None, context=context))
            if concept is not None and concept != _HEADLINE_EPS:
                absences.append(TypedAbsence(
                    concept=concept,
                    reason=(AbsenceReason.VALUE_AMBIGUOUS.value if group.unclosed
                            else AbsenceReason.CONCEPT_NOT_PRESENT.value),
                    detail=("the current-period cell opens a parenthesis it never closes; "
                            "its sign cannot be read" if group.unclosed
                            else "the current-period cell is a placeholder; the row reports "
                                 "no value for this period"),
                    label=label,
                ))
                stats.candidate_rows += 1
                stats.dated_candidate_rows += target is not None
            continue
        key = target.start if target is not None else 0
        if group.currency:
            column_currency.setdefault(key, group.currency)
        currency = column_currency.get(key) or context.currency_from_caption

        if _bind_row(
            document=document,
            cell=group.cell,
            value=group.value,
            kind_hint=group.kind,
            literals=group.literals,
            label=label,
            scope=scope,
            context=context,
            currency=currency,
            column=column,
            refusal_reason=refusal_reason,
            period_refusal=refusal,
            figures=figures,
            absences=absences,
        ):
            stats.candidate_rows += 1
            stats.dated_candidate_rows += target is not None
    return reported


def _observed_kind(
    *, kind_hint: str, label: str, scope: str, currency: str | None, context: _Context
) -> str | None:
    if kind_hint == ValueKind.PERCENT.value:
        return ValueKind.PERCENT.value
    label, scope = _fold_dashes(label), _fold_dashes(scope)
    if (_PER_SHARE_SCOPE_RE.search(scope) or _PER_SHARE_SCOPE_RE.search(label)
            or _EPS_LABEL_RE.search(label)):
        return ValueKind.PER_SHARE.value
    if currency or context.units:
        return ValueKind.MONETARY.value
    return None


def _bind_row(
    *,
    document: DisclosureDocument,
    cell: TableCell,
    value: float,
    kind_hint: str,
    literals: Sequence[str],
    label: str,
    scope: str,
    context: _Context,
    currency: str | None,
    column: _Column | None,
    refusal_reason: AbsenceReason | None,
    period_refusal: str,
    figures: list[ReleaseFigure],
    absences: list[TypedAbsence],
) -> bool:
    """Bind one row's current-period value, or record why not.

    Returns True when the row names a roster concept — bound or refused — so
    the caller can tell "no candidate rows" from "every candidate refused".  An
    unqualified headline EPS row names none on its own: it is evidence for
    _resolve_share_classes, never a candidate.
    """
    kind = _observed_kind(
        kind_hint=kind_hint, label=label, scope=scope, currency=currency, context=context
    )
    concept = _concept_for(label=label, scope=scope, kind=kind, issuers=context.issuers)
    if concept is None:
        return False
    counted = concept != _HEADLINE_EPS

    basis = _basis_for(label=label, scope=scope, context=context)
    if basis is None:
        absences.append(TypedAbsence(
            concept=concept,
            reason=AbsenceReason.BASIS_UNDECLARED.value,
            detail="no GAAP or non-GAAP caption governs this row; refusing to default a basis",
            label=label,
        ))
        return counted
    if kind is None:
        absences.append(TypedAbsence(
            concept=concept,
            reason=AbsenceReason.UNITS_UNDECLARED.value,
            detail="no units caption and no currency symbol govern this value",
            label=label,
        ))
        return counted
    if kind == ValueKind.MONETARY.value:
        if context.units is None:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.UNITS_UNDECLARED.value,
                detail="no '(In thousands/millions/billions)' caption governs this table",
                label=label,
            ))
            return counted
        if currency is None:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.CURRENCY_UNDECLARED.value,
                detail="no currency symbol governs this column and no caption names one",
                label=label,
            ))
            return counted
        units, scale = context.units, _SCALE_FACTOR[context.units]
    elif kind == ValueKind.PER_SHARE.value:
        if currency is None:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.CURRENCY_UNDECLARED.value,
                detail="a per-share amount with no currency symbol is not a price",
                label=label,
            ))
            return counted
        # A per-share amount never inherits the statement's (In millions) scale.
        units, scale = "per_share", 1.0
    else:
        units, scale, currency = "percent", 1.0, None

    if column is None:
        absences.append(TypedAbsence(
            concept=concept,
            reason=(refusal_reason or AbsenceReason.PERIOD_UNDECLARED).value,
            detail=period_refusal,
            label=label,
        ))
        return counted

    receipt = _receipt_or_absence(
        document=document, cell=cell, literals=literals,
        concept=concept, label=label, absences=absences,
    )
    if receipt is None:
        return counted

    figures.append(ReleaseFigure(
        concept=concept,
        label=label,
        value=value,
        basis=basis,
        units=units,
        currency=currency,
        period_label=column.period_label,
        period_end=column.period_end,
        receipt=receipt,
        scale_factor=scale,
    ))
    return counted


def _concept_for(
    *, label: str, scope: str, kind: str | None, issuers: frozenset[str] = frozenset()
) -> str | None:
    if not label:
        return None
    # Rules read the folded text; a concept key keeps the label as printed.
    printed, label, scope = label, _fold_dashes(label), _fold_dashes(scope)
    if _SEGMENT_SCOPE_RE.search(scope):
        # Under a segment breakdown, the "Total" line is the same fact the
        # statement already reported; emitting it again would double-count.
        if _TOTAL_LABEL_RE.match(label) or kind != ValueKind.MONETARY.value:
            return None
        return f"segment_revenue:{_slugify(printed)}"
    for rule in _ROW_RULES:
        matched = rule.pattern.match(label)
        if not matched:
            continue
        if _attributes_to_another(matched, issuers):
            # "... attributable to Goodwill Impairment" names a component, not
            # the issuer; it is no roster concept and no other rule applies.
            return None
        if rule.scope_forbidden is not None and rule.scope_forbidden.search(scope):
            return None
        if rule.scope_required is not None and not (
            _scope_names_eps(scope, issuers) if rule.scope_required.search(scope)
            else rule.scope_required.search(label)
        ):
            return None
        if kind is None:
            # Kind is unknown, but the label matched a roster concept: report
            # the concept so the caller learns WHICH figure went unbound.
            return next(iter(rule.kind_to_concept.values()))
        return rule.kind_to_concept.get(kind)
    if kind == ValueKind.PER_SHARE.value and not _SHARE_COUNT_SCOPE_RE.search(scope):
        per_class = _CLASS_EPS_SCOPE_RE.match(scope)
        if per_class and _SHARE_CLASS_LABEL_RE.match(label):
            return f"{_CLASS_EPS_PREFIX}eps_{per_class.group(1).lower()}:{_slugify(printed)}"
        headline = _HEADLINE_EPS_LABEL_RE.match(label)
        if headline and _attributes_to_another(headline, issuers):
            return None
        if headline and not _BASIC_OR_DILUTED_RE.search(scope):
            return _HEADLINE_EPS
    if _NON_GAAP_CAPTION_RE.search(scope) and kind == ValueKind.MONETARY.value:
        return f"non_gaap_adjustment:{_slugify(printed)}"
    return None


def _basis_for(*, label: str, scope: str, context: _Context) -> str | None:
    label, scope = _fold_dashes(label), _fold_dashes(scope)
    if _NON_GAAP_INLINE_RE.search(label) or _NON_GAAP_INLINE_RE.search(scope):
        return Basis.NON_GAAP.value
    return context.basis


def _extract_guidance(
    document: DisclosureDocument,
    block: DisclosureBlock,
    figures: list[ReleaseFigure],
    absences: list[TypedAbsence],
    seen: set[str],
) -> None:
    text = block.text
    if not _GUIDANCE_SENTENCE_RE.search(text):
        return
    match = _GUIDANCE_RANGE_RE.search(text)
    if match is None:
        return
    low_literal, low_mag, high_literal, high_mag = (
        match.group(1), match.group(2), match.group(3), match.group(4)
    )
    # "$72.8 billion to $78.6 billion" and "$72.8 to $78.6 billion" both occur;
    # the trailing magnitude governs both endpoints when the first omits it.
    magnitude = (low_mag or high_mag or "").lower()

    concept_stem = "guidance_revenue"
    if _NON_GAAP_INLINE_RE.search(text) and re.search(r"per\s+share|EPS", text, re.I):
        concept_stem, magnitude_units = "guidance_eps", "per_share"
    elif re.search(r"per\s+share|EPS", text, re.I):
        concept_stem, magnitude_units = "guidance_eps", "per_share"
    elif magnitude:
        magnitude_units = _GUIDANCE_MAGNITUDE[magnitude]
    else:
        magnitude_units = ""

    basis = Basis.NON_GAAP.value if _NON_GAAP_INLINE_RE.search(text) else None
    period = _GUIDANCE_PERIOD_RE.search(text)

    for suffix, literal in (("low", low_literal), ("high", high_literal)):
        concept = f"{concept_stem}_{suffix}"
        if concept in seen:
            continue
        seen.add(concept)
        if basis is None:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.BASIS_UNDECLARED.value,
                detail="guidance sentence names neither GAAP nor non-GAAP; "
                       "refusing to default a basis for a forward figure",
                label=None,
            ))
            continue
        if not magnitude_units:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.UNITS_UNDECLARED.value,
                detail="guidance range states no magnitude (thousand/million/billion)",
                label=None,
            ))
            continue
        if period is None:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.PERIOD_UNDECLARED.value,
                detail="guidance sentence names no period",
                label=None,
            ))
            continue
        try:
            receipt = receipt_for_literal(
                source=document.raw_source,
                source_sha256=document.source_sha256,
                search_start=block.source_span.char_start,
                search_end=block.source_span.char_end,
                literal=literal,
            )
        except ReceiptError as exc:
            absences.append(TypedAbsence(
                concept=concept,
                reason=AbsenceReason.VALUE_AMBIGUOUS.value,
                detail=f"no unique source location for {literal!r}: {exc}",
                label=None,
            ))
            continue
        qualifier, unit_word, year = period.group(1), period.group(2), period.group(3)
        period_label = " ".join(
            part for part in ("the", qualifier, unit_word, year) if part
        ).strip()
        figures.append(ReleaseFigure(
            concept=concept,
            label=period_label,
            value=float(literal.replace(",", "")),
            basis=basis,
            units=magnitude_units,
            currency="USD",
            period_label=period_label,
            # A guidance window has no reported period end; the label is the
            # only period identity the document declares.
            period_end="",
            receipt=receipt,
            scale_factor=_SCALE_FACTOR.get(magnitude_units, 1.0),
        ))


def _declared_period_months(period_label: str) -> int | None:
    """How many months the period header says it spans, or None if it says not.

    Weeks round to the nearest month, so "13 Weeks Ended", "Three Months
    Ended" and "Fourth Quarter" are all 3 and "52 Weeks Ended", "Twelve
    Months Ended" and "Fiscal Year Ended" are all 12: two names for one span
    stay one span, and readings that disagree on it stay a conflict.

    A header that names more than one span ("Three and Nine Months Ended",
    "Fourth Quarter and Fiscal Year Ended") or a year-to-date column declares
    no single length, so it is None: the shortest-period rule must not read a
    cumulative column as the quarter.
    A year phrase ("Fiscal 2026") only counts when nothing shorter is named,
    because "Fourth Quarter Fiscal 2026" is a quarter.
    """
    # "Twenty - Six" and "Twenty–Six" are "Twenty-Six": one count, not "Six".
    period_label = re.sub(r"\s*-\s*", "-", " ".join(_fold_dashes(period_label).split()))
    period_label = _QUARTER_OF_FISCAL_YEAR_RE.sub(r"\1 \2", period_label)
    # A header is a few words.  A longer one is no period name this reader
    # knows, and the two-period pattern is slow on it.
    if len(period_label) > _PERIOD_LABEL_MAX:
        return None
    if _YEAR_TO_DATE_RE.search(period_label) or _TWO_PERIOD_HEADER_RE.search(period_label):
        return None

    def months(count: str, unit: str) -> int:
        number = _SPAN_WORDS.get(count.lower()) or int(count)
        return round(number * 7 / 30.44) if unit.lower() == "week" else number

    spans: set[int] = set()
    for match in _SPAN_PAIR_RE.finditer(period_label):
        spans.update((months(match.group(1), match.group(3)),
                      months(match.group(2), match.group(3))))
    text = _SPAN_PAIR_RE.sub(" ", period_label)
    for match in _PERIOD_SPAN_RE.finditer(text):
        spans.add(months(match.group(1), match.group(2)))
    for match in _QUARTER_COUNT_RE.finditer(text):
        spans.add(3 * (_QUARTER_COUNTS.get(match.group(1).lower()) or int(match.group(1))))
    if _QUARTER_SPAN_RE.search(_QUARTER_COUNT_RE.sub(" ", text)):
        spans.add(3)
    if not spans and _YEAR_SPAN_RE.search(text):
        spans.add(12)
    return spans.pop() if len(spans) == 1 else None


def _footing_total(rows: Sequence[ReleaseFigure], values: set[float]) -> float | None:
    """The one amount that the other conflicting amounts sum to, if exactly one does.

    Only for currency amounts in one scale and currency, all positive, with at
    least two components: a per-share amount or a percentage does not add up
    across segments, a negative line is an elimination this rule cannot tell
    from a component, and a single other amount equal to the total is a
    restatement, not a breakdown.  The sum must be exact to float precision; a
    breakdown that misses by rounding stays ambiguous.

    The sum runs over every reading, not every distinct amount: two segments
    that each report 2,000 are two components, so 1,000 + 2,000 + 2,000 does
    not foot to 3,000.  Every reading of the total itself is left out of the
    sum, so a total that appears in two tables still foots.
    """
    if len(values) < 3 or min(values) <= 0:
        return None
    if len({(row.units, row.scale_factor, row.currency) for row in rows}) != 1:
        return None
    if rows[0].units not in _SCALE_FACTOR:
        return None
    amounts = [row.value for row in rows]
    totals = [
        value for value in values
        if math.isclose(value, sum(amount for amount in amounts if amount != value), rel_tol=1e-9)
    ]
    return totals[0] if len(totals) == 1 else None


def _resolve_share_classes(
    figures: list[ReleaseFigure], absences: list[TypedAbsence]
) -> tuple[list[ReleaseFigure], list[TypedAbsence]]:
    """Read per-class EPS as the release's EPS when its headline says which class.

    A multi-class issuer reports basic and diluted EPS once per class of common
    stock and headlines one unqualified "Earnings per share".  Within one basis
    and period, when there is exactly one unqualified amount and exactly one
    class's amount equals it, that class row is the release's eps_basic or
    eps_diluted, and every such match must name the same class.  Anything else
    refuses: no unqualified amount, two of them, two classes equal to it, or a
    basic match and a diluted match that name different classes.  A direct
    "Diluted EPS" row for the same basis and period is the release's own
    statement, so class rows never compete with it.  Internal concepts never
    leave this function: a class refusal is reported against its roster
    concept, and headline rows are dropped.
    """
    headline: dict[tuple[str, str], set[float]] = {}
    classed: dict[tuple[str, str, str], list[tuple[str, ReleaseFigure]]] = {}
    kept: list[ReleaseFigure] = []
    for figure in figures:
        if figure.concept == _HEADLINE_EPS:
            headline.setdefault((figure.basis, figure.period_end), set()).add(figure.value)
        elif figure.concept.startswith(_CLASS_EPS_PREFIX):
            concept, share_class = figure.concept[len(_CLASS_EPS_PREFIX):].split(":", 1)
            classed.setdefault((concept, figure.basis, figure.period_end), []).append(
                (share_class, figure)
            )
        else:
            kept.append(figure)

    direct = {(figure.concept, figure.basis, figure.period_end) for figure in kept}
    picks: dict[tuple[str, str, str], list[ReleaseFigure]] = {}
    refused: dict[tuple[str, str, str], str] = {}
    for key, rows in classed.items():
        if key in direct:
            continue
        concept, basis, period_end = key
        heads = headline.get((basis, period_end), set())
        matched = {share_class for share_class, row in rows if len(heads) == 1 and row.value in heads}
        if len(matched) == 1:
            picks[key] = [row for share_class, row in rows if share_class in matched]
            continue
        classes = len({share_class for share_class, _ in rows})
        stated = ", ".join(format(value, "g") for value in sorted(heads)) or "none"
        refused[key] = (
            f"{classes} share classes report {concept} for {period_end or 'this period'} on "
            f"a {basis} basis; the release's unqualified earnings per share ({stated}) "
            f"matches {len(matched)} of them — refusing to pick a class"
        )
    chosen = {row.concept.rsplit(":", 1)[1] for rows in picks.values() for row in rows}
    if len(chosen) > 1:
        for key in picks:
            refused[key] = (
                f"the unqualified earnings per share matches different share classes for "
                f"basic and diluted EPS ({', '.join(sorted(chosen))}) — refusing to pick one"
            )
        picks = {}
    for (concept, _, _), rows in picks.items():
        kept.extend(replace(row, concept=concept) for row in rows)

    resolved: list[TypedAbsence] = []
    for absence in absences:
        if absence.concept == _HEADLINE_EPS:
            continue
        if absence.concept.startswith(_CLASS_EPS_PREFIX):
            absence = replace(
                absence, concept=absence.concept[len(_CLASS_EPS_PREFIX):].split(":", 1)[0]
            )
        resolved.append(absence)
    for key, detail in refused.items():
        resolved.append(TypedAbsence(
            concept=key[0],
            reason=AbsenceReason.VALUE_AMBIGUOUS.value,
            detail=detail,
            label=classed[key][0][1].label,
        ))
    return kept, resolved


def _resolve_restatements(
    figures: list[ReleaseFigure], absences: list[TypedAbsence]
) -> tuple[list[ReleaseFigure], list[TypedAbsence]]:
    """Collapse identical restatements; refuse contradictory ones.

    A press release states the same fact more than once by design — net income
    heads the statement of operations and opens the cash-flow statement, and
    total net sales is repeated under every segment breakdown.  Two readings
    that AGREE on (concept, basis, period, value) are one fact and collapse.

    Two readings that DISAGREE are not a fact at all.  Keeping the first would
    make the answer depend on document order, so both are dropped and the
    conflict is reported as a typed absence.

    One disagreement is not a conflict: a fourth-quarter release heads its
    statement of operations "Three Months Ended September 30" and its
    cash-flow statement "Twelve Months Ended September 30".  Both end on the
    same day, but they are two periods.  When every reading declares how long
    its period runs and the shortest is a quarter, it is the release's own
    period, which is the
    in-table rule (the quarter precedes the year-to-date column) applied
    across tables.  The longer readings are cumulative facts that this
    figure's identity cannot hold, so they are not reported.

    Nor is a segment breakdown.  A table that labels each segment's line
    "Net sales" or "Revenue" under a segment-name heading reads as several
    revenue rows; when exactly one of the amounts equals the sum of all the
    others, the others are its components and that amount is the total.
    """
    grouped: dict[tuple[str, str, str], list[ReleaseFigure]] = {}
    for figure in figures:
        grouped.setdefault((figure.concept, figure.basis, figure.period_end), []).append(figure)

    kept: list[ReleaseFigure] = []
    extra: list[TypedAbsence] = []
    for (concept, basis, period_end), rows in grouped.items():
        values = {row.value for row in rows}
        if len(values) > 1:
            lengths = [_declared_period_months(row.period_label) for row in rows]
            # The shortest span wins only when it is a quarter (a 16-week
            # quarter rounds to 4): "Two Quarters" against "Twelve Months" is
            # two cumulative columns, and neither is this period's quarter.
            if None not in lengths and min(lengths) <= 4:
                rows = [row for row, days in zip(rows, lengths) if days == min(lengths)]
                values = {row.value for row in rows}
        if len(values) > 1:
            total = _footing_total(rows, values)
            if total is not None:
                rows = [row for row in rows if row.value == total]
                values = {total}
        if len(values) == 1:
            kept.append(rows[0])
            continue
        extra.append(TypedAbsence(
            concept=concept,
            reason=AbsenceReason.VALUE_AMBIGUOUS.value,
            detail=(
                f"{len(rows)} rows report {concept} for {period_end or 'this period'} "
                f"on a {basis} basis with different values "
                f"({', '.join(format(value, 'g') for value in sorted(values))}) — "
                "refusing to pick one by document order"
            ),
            label=rows[0].label,
        ))
    kept.sort(key=lambda row: (row.concept, row.basis, row.period_end))
    return kept, absences + extra


def extract_release_figures(
    document: DisclosureDocument,
    *,
    roster: Iterable[str] = CONCEPT_ROSTER,
) -> ReleaseFigureSet:
    """Read every roster concept out of a normalized release body.

    Emits one ``ReleaseFigure`` per concept it could bind to an exact, replayed
    source location, and one ``TypedAbsence`` per roster concept it could not.
    """
    figures: list[ReleaseFigure] = []
    absences: list[TypedAbsence] = []
    context = _Context()
    context.issuers = _issuer_names(document)
    guidance_seen: set[str] = set()
    stats = _TableStats()

    for block in document.blocks:
        if block.kind is BlockKind.TABLE:
            entry_basis = context.basis
            reported = _extract_table(document, block, context, figures, absences, stats)
            context.reset_table_scope(entry_basis=entry_basis, reported=reported)
            continue
        context.observe(block.text)
        if block.kind is BlockKind.PARAGRAPH:
            _extract_guidance(document, block, figures, absences, guidance_seen)

    figures, absences = _resolve_share_classes(figures, absences)
    figures, absences = _resolve_restatements(figures, absences)

    bound = {figure.concept for figure in figures}
    # An absence is a statement about the RELEASE, not about one row.  A release
    # that reports operating cash flow with full provenance in the cash-flow
    # statement and again, undeclared, in a supplemental table has reported it;
    # emitting both a figure and an absence for one concept is a contradiction,
    # not extra candour.
    absences = [item for item in absences if item.concept not in bound]
    reported_absent = {absence.concept for absence in absences}
    for concept in roster:
        if concept in bound or concept in reported_absent:
            continue
        absences.append(TypedAbsence(
            concept=concept,
            reason=AbsenceReason.CONCEPT_NOT_PRESENT.value,
            detail="no row or sentence in this release reports this concept",
            label=None,
        ))

    return ReleaseFigureSet(
        figures=tuple(figures),
        absences=tuple(sorted(absences, key=lambda item: (item.concept, item.reason))),
        outcome=_outcome(document, figures, stats).value,
        table_count=stats.tables,
        period_table_count=stats.period_tables,
        candidate_row_count=stats.candidate_rows,
    )


def _outcome(
    document: DisclosureDocument, figures: Sequence[ReleaseFigure], stats: _TableStats
) -> BindingOutcome:
    if figures:
        return BindingOutcome.FIGURES_BOUND
    if not document.blocks:
        return BindingOutcome.NO_BLOCKS
    if not stats.tables:
        return BindingOutcome.NO_TABLES
    if not stats.candidate_rows:
        return BindingOutcome.NO_CANDIDATE_ROWS
    if not stats.dated_candidate_rows:
        return BindingOutcome.NO_PERIOD_COLUMNS
    return BindingOutcome.ALL_REFUSED


__all__ = [
    "AUTHORITY",
    "AbsenceReason",
    "Basis",
    "BindingOutcome",
    "CONCEPT_ROSTER",
    "FIGURES_SCHEMA",
    "ReleaseFigure",
    "ReleaseFigureSet",
    "TypedAbsence",
    "ValueKind",
    "extract_release_figures",
    "parse_numeric",
    "parse_statement_date",
]
