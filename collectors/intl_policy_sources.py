"""Explicitly registered central-bank releases for the International collector."""
from __future__ import annotations
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
import re

from lib.intl_policy_evidence import normalize_policy_decision, normalize_policy_review
from lib.intl_forecast_vintages import normalize_publication

BOE_URL = "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/2026/september-2026"
CBC_URL = "https://www.cbc.gov.tw/en/cp-448-192883-c5fa1-2.html"
BOJ_URL = "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918a.pdf"
BOJ_REFERENCE_URL = "https://www.boj.or.jp/en/mopo/mpmdeci/mpr_2026/k260918b.pdf"
BOK_URL = "https://www.bok.or.kr/eng/bbs/E0000634/view.do?depth=400423&depth2=400417&depth3=400423&menuNo=400423&nttId=11064193&oldMenuNo=400423&pageIndex=1&pageUnit=10&programType=newsDataEng&searchCnd=1&searchKwd="
BOK_HISTORY_URL = "https://www.bok.or.kr/portal/singl/baseRate/list.do?menuNo=200761"
RBA_URL = "https://www.rba.gov.au/media-releases/2026/mr-26-27.html"
RBA_HISTORY_URL = "https://www.rba.gov.au/statistics/cash-rate/"
ECB_URL = "https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260910~314e508016.en.html"
ECB_HISTORY_URL = "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html"
ECB_DISCUSSION_URL = "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/2026/html/ecb.is260910~6a45359cfc.en.html"
RBI_URL = "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=63742"
RBI_IMPLEMENTATION_URL = "https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx?Id=13727"
RELEASES = (
    {"cc": "GB", "provider": "Bank of England", "instrument": "bank_rate",
     "source_url": BOE_URL, "published": "2026-09-17", "decision_date": "2026-09-16",
     "effective_date": "2026-09-16", "value": 3.75, "previous_value": 3.75,
     "votes": {"hold": 6, "increase": 3, "decrease": 0},
     "rationale_en": "Energy-price persistence raises inflation risks. Soft labour conditions and higher borrowing costs pull the other way; three members favoured an increase.",
     "rationale_zh": "能源价格持续偏高加大通胀风险；劳动力市场偏软与借贷成本上升形成反向影响。三名委员主张加息。"},
    {"cc": "TW", "provider": "Central Bank of the Republic of China (Taiwan)", "instrument": "discount_rate",
     "source_url": CBC_URL, "published": "2026-09-17", "decision_date": "2026-09-17",
     "effective_date": "2026-09-17", "value": 2.0, "previous_value": 2.0, "votes": None,
     "rationale_en": "The CBC balanced contained inflation and strong activity against global uncertainty. A discount-rate hold can coexist with rising market borrowing costs.",
     "rationale_zh": "台湾央行权衡可控通胀、强劲经济活动与全球不确定性。贴现率维持不变，并不代表市场借贷成本不会上升。"},
    {"cc": "JP", "provider": "Bank of Japan", "instrument": "uncollateralized_overnight_call_rate_target",
     "source_url": BOJ_URL, "published": "2026-09-18", "decision_date": "2026-09-18",
     "effective_date": "2026-09-24", "last_change_date": "2026-09-24",
     "value": 1.25, "previous_value": 1.0, "setting_qualifier": "around", "action": "increase", "votes": None,
     "rationale_en": "The BOJ raised the target by a 7–2 majority as wage and input costs spread into prices. Further normalization depends on activity, inflation and financial conditions.",
     "rationale_zh": "工资与投入成本向价格传导，日银以7票对2票上调目标。后续正常化取决于经济活动、通胀与金融条件。"},
    {"cc": "KR", "provider": "Bank of Korea", "instrument": "bok_base_rate",
     "source_url": BOK_URL, "published": "2026-08-27", "decision_date": "2026-08-27",
     "effective_date": "2026-08-27", "last_change_date": "2026-08-27",
     "value": 3.0, "previous_value": 2.75, "action": "increase",
     "votes": {"hold": 1, "increase": 6, "decrease": 0},
     "rationale_en": "Export strength is lifting domestic demand while inflation and Seoul housing risks persist. Six members backed an increase; one preferred a hold.",
     "rationale_zh": "出口强劲带动内需，通胀与首尔房市风险仍在。六名委员支持加息，一名主张维持不变。"},
    {"cc": "AU", "provider": "Reserve Bank of Australia", "instrument": "cash_rate_target",
     "source_url": RBA_URL, "published": "2026-09-29", "decision_date": "2026-09-29",
     "effective_date": "2026-09-30", "last_change_date": "2026-09-30",
     "value": 4.6, "previous_value": 4.35, "action": "increase", "votes": None,
     "rationale_en": "Inflation pressure broadened as energy and capacity costs rose, despite cooling spending and housing. The Board unanimously judged further tightening necessary.",
     "rationale_zh": "能源与产能成本上升使通胀压力扩散，消费与住房却在降温。委员会一致认为需要进一步收紧政策。"},
    {"cc": "EZ", "provider": "European Central Bank", "instrument": "deposit_facility_rate",
     "source_url": ECB_URL, "published": "2026-09-10", "decision_date": "2026-09-10",
     "effective_date": "2026-09-16", "last_change_date": "2026-09-16",
     "value": 2.5, "previous_value": 2.25, "action": "increase", "votes": None,
     "rationale_en": "The energy shock prolonged inflation pressure despite resilient growth. The increase was unanimous; subsequent decisions remain dependent on incoming evidence.",
     "rationale_zh": "增长保持韧性，能源冲击却延长了通胀压力。本次加息获一致支持；后续决定仍取决于新信息。"},
    {"cc": "IN", "provider": "Reserve Bank of India", "instrument": "policy_repo_rate",
     "source_url": RBI_URL, "published": "2026-10-07", "decision_date": "2026-10-07",
     "effective_date": "2026-10-07", "last_change_date": "2026-10-07",
     "value": 5.5, "previous_value": 5.25, "action": "increase",
     "votes": {"hold": 0, "increase": 6, "decrease": 0},
     "rationale_en": "Resilient demand met rising inflation risks. All six members backed the rate increase; two separately opposed changing the stance from neutral to calibrated tightening.",
     "rationale_zh": "需求保持韧性，通胀风险上升。六名委员均支持加息；其中两名另行反对将中性立场改为审慎收紧。"},
)

# These stable article bodies bind the reviewed rationale as well as the rates.
# A source correction requires review; changed navigation does not change a body.
REVIEWED_BODIES = {
    "AU": ("At its meeting today, the Board decided to increase the cash rate target",
           "Today’s policy decision was unanimous.",
           "462d8c463fba7e8b977c4ecb92c38219be154f69080d8ab72057ce548a27a94d"),
    "KR": ("Monetary Policy Decision The Monetary Policy Board of the Bank of Korea",
           "Opening Remarks to the Press Conference (August 27, 2026)",
           "5da422a3d7b5ba658f6426507a26295d14828a86d55bcdf50d04809dceb650ad"),
    "EZ": ("PRESS RELEASE Monetary policy decisions 10 September 2026", "CONTACT European Central Bank",
           "da19171579eade1eddd4caa14cfcbf013f0b5e9220c683feadd0517525c13725"),
    "IN": ("Monetary Policy Statement, 2026-27 Resolution of the Monetary Policy Committee", "Press Release:",
           "e0d3735a7a1ba5753c5fd1b29934fc6ba22f678bc8214659e0111521c9003098"),
}
REVIEWED_PDFS = {
    BOJ_URL: "36d7aa63ff283e25dcc07bc1f6e0caaad8e6764d30cf22433b5c2dd0b6bda391",
    BOJ_REFERENCE_URL: "9b2bf863babccf5d17b890274aa207d16ddc5467b5846e9ca85f8ce098c6c313",
}
SUPPORT_DOCUMENTS = {
    "JP": ((BOJ_REFERENCE_URL, "decision_reference", ("previous_value",)),),
    "KR": ((BOK_HISTORY_URL, "rate_history", ("previous_value", "effective_date")),),
    "AU": ((RBA_HISTORY_URL, "rate_history", ("previous_value", "effective_date")),),
    "EZ": ((ECB_HISTORY_URL, "rate_history", ("previous_value",)),
           (ECB_DISCUSSION_URL, "policy_discussion", ("votes",))),
    "IN": ((RBI_IMPLEMENTATION_URL, "implementation", ("previous_value", "effective_date")),),
}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.hidden = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _unique(pattern, text):
    matches = re.findall(pattern, text, flags=re.I)
    if len(set(matches)) != 1:
        raise ValueError("policy_release_statement_missing_or_ambiguous")
    return matches[0]


def _document_text(blob, url):
    if type(blob) is not bytes or not 1 <= len(blob) <= 4_000_000:
        raise ValueError("policy_document_size_or_type")
    if url in REVIEWED_PDFS:
        if not blob.startswith(b"%PDF-") or sha256(blob).hexdigest() != REVIEWED_PDFS[url]:
            raise ValueError("policy_reviewed_pdf_changed")
        import pdfplumber
        with pdfplumber.open(BytesIO(blob)) as pdf:
            if not 1 <= len(pdf.pages) <= 8:
                raise ValueError("policy_pdf_page_limit")
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
    else:
        parser = _Text()
        parser.feed(blob.decode("utf-8-sig"))
        text = " ".join(parser.parts)
    text = " ".join(text.split())
    if len(text) > 500_000:
        raise ValueError("policy_document_text_limit")
    return text


def _reviewed_body(text, cc):
    if cc not in REVIEWED_BODIES:
        return text
    start, end, expected = REVIEWED_BODIES[cc]
    begin = text.find(start)
    finish = text.find(end, begin + len(start))
    if text.count(start) != 1 or finish < 0:
        raise ValueError("policy_reviewed_body_missing_or_ambiguous")
    body = text[begin:finish + len(end)]
    if sha256(body.encode()).hexdigest() != expected:
        raise ValueError("policy_reviewed_body_changed")
    return body


def _supporting_evidence(release, supporting_blobs, *, retrieved_at):
    required = SUPPORT_DOCUMENTS.get(release["cc"], ())
    supplied = supporting_blobs if type(supporting_blobs) is dict else {}
    if set(supplied) != {url for url, _, _ in required}:
        raise ValueError("policy_supporting_source_missing_or_unregistered")
    evidence = []
    for url, label, roles in required:
        text = _document_text(supplied[url], url)
        if url == BOJ_REFERENCE_URL:
            target = _unique(r'raised to "around ([\d.]+)%"', text)
            prior = _unique(r'\(previously "around ([\d.]+)%"\)', text)
            if "uncollateralized overnight call rate" not in text or (float(target), float(prior)) != (1.25, 1.0):
                raise ValueError("boj_reference_changed")
        elif url == BOK_HISTORY_URL:
            values = _unique(r"변경일자 기준금리 2026 08월 27일 ([\d.]+) 2026 07월 16일 ([\d.]+)", text)
            if tuple(map(float, values)) != (3.0, 2.75):
                raise ValueError("bok_effective_setting_changed")
        elif url == RBA_HISTORY_URL:
            values = _unique(r"Effective Date Change % points Cash rate target % Related Documents 30 Sep 2026 ([+\d.]+) ([\d.]+) Statement Minutes 12 Aug 2026 ([\d.]+) ([\d.]+)", text)
            if tuple(map(float, values)) != (0.25, 4.6, 0.0, 4.35):
                raise ValueError("rba_effective_setting_changed")
        elif url == ECB_HISTORY_URL:
            if "Date (with effect from) Deposit facility" not in text:
                raise ValueError("ecb_history_definition_changed")
            values = _unique(r"Minimum bid rate 2026 16 Sep\. ([\d.]+) ([\d.]+) - ([\d.]+) 2026 17 Jun\. ([\d.]+) ([\d.]+) - ([\d.]+)", text)
            if tuple(map(float, values)) != (2.5, 2.65, 2.9, 2.25, 2.4, 2.65):
                raise ValueError("ecb_history_setting_changed")
        elif url == ECB_DISCUSSION_URL:
            if ("10 September 2026" not in text
                    or "which was, by the way, a unanimous decision" not in text):
                raise ValueError("ecb_policy_vote_changed")
        elif url == RBI_IMPLEMENTATION_URL:
            if ("RBI/2026-27/282" not in text or "October 07, 2026" not in text
                    or "FMOD.MAOG.No.154/01.01.001/2026-27" not in text):
                raise ValueError("rbi_implementation_identity_changed")
            values = _unique(r"policy repo rate under the Liquidity Adjustment Facility \(LAF\) by ([\d.]+) basis points from ([\d.]+) per cent to ([\d.]+) per cent with immediate effect", text)
            if tuple(map(float, values)) != (25.0, 5.25, 5.5):
                raise ValueError("rbi_effective_setting_changed")
        evidence.append({"source_url": url, "label": label, "roles": list(roles),
                         "source_sha256": sha256(supplied[url]).hexdigest(), "retrieved_at": retrieved_at})
    return evidence


def parse_registered_policy_release(blob, release, *, retrieved_at, supporting_blobs=None):
    if release not in RELEASES:
        raise ValueError("unregistered_policy_release")
    text = _document_text(blob, release["source_url"])
    supporting = _supporting_evidence(release, supporting_blobs, retrieved_at=retrieved_at)
    body = _reviewed_body(text, release["cc"])
    stamp = sha256(blob).hexdigest()
    forecasts = []
    if release["cc"] == "GB":
        if ("Published on 17 September 2026" not in text
                or "soft labour market conditions" not in text
                or "second-round effects" not in text):
            raise ValueError("boe_release_identity_or_rationale_changed")
        found = _unique(r"meeting ending on 16 September 2026,.*?majority of (\d+)[–-](\d+) to maintain Bank Rate at ([\d.]+)%", text)
        if (int(found[0]), int(found[1]), float(found[2])) != (6, 3, 3.75):
            raise ValueError("boe_reviewed_decision_changed")
        minority = _unique(r"Three members voted to increase Bank Rate by ([\d.]+) percentage points, to ([\d.]+)%", text)
        if tuple(map(float, minority)) != (0.25, 4.0):
            raise ValueError("boe_minority_vote_changed")
    elif release["cc"] == "TW":
        if ("Release Date: September 17, 2026" not in text or "Monetary Policy Decision of the Board Meeting (2026 Q3)" not in text
                or "higher base effect" not in text or "discount rate" not in text):
            raise ValueError("cbc_release_identity_changed")
        rates = _unique(r"discount rate, the rate on refinancing of secured loans, and the rate on temporary accommodations unchanged at ([\d.]+)%, ([\d.]+)%, and ([\d.]+)%", text)
        if tuple(map(float, rates)) != (2.0, 2.375, 4.25):
            raise ValueError("cbc_reviewed_decision_changed")
        current = float(_unique(r"([\d.]+)% for the year as a whole", text))
        following = float(_unique(r"higher base effect would lead the economic growth rate to register ([\d.]+)% next year", text))
        cpi = _unique(r"forecasts for Taiwan's CPI and core CPI inflation rates to ([\d.]+)% and ([\d.]+)%", text)
        next_cpi = _unique(r"next year the CPI and core CPI inflation rates will slow to ([\d.]+)% and ([\d.]+)%", text)
        if (current, following, float(cpi[0]), float(next_cpi[0])) != (11.48, 5.82, 2.03, 1.83):
            raise ValueError("cbc_reviewed_forecast_changed")
        for series, values in (("real_gdp_growth", {"2026": current, "2027": following}),
                               ("inflation_average", {"2026": float(cpi[0]), "2027": float(next_cpi[0])})):
            record = normalize_publication({
                "cc": "TW", "provider": "CBC", "family": "Monetary policy outlook", "edition": "2026-09-17",
                "kind": "sourced_forecast", "series_id": series, "published": release["published"],
                "source_url": CBC_URL, "unit": "percent", "period_basis": "calendar_year",
                "values": values, "precision": 2, "source_sha256": stamp,
                "retrieved_at": retrieved_at, "parser_version": "cbc_reviewed_release_v1",
            }, observed_at=retrieved_at)
            if record is None:
                raise ValueError("cbc_forecast_admission_failed")
            forecasts.append(record)
    elif release["cc"] == "JP":
        if "September 18, 2026 Bank of Japan" not in text:
            raise ValueError("boj_release_identity_changed")
        target = _unique(r"uncollateralized overnight call rate to remain at around ([\d.]+) percent", text)
        vote = _unique(r"decided, by a (\d+)-(\d+) majority vote, to set", text)
        effective = _unique(r"new guideline for money market operations will be effective from (September \d+, 2026)", text)
        if (float(target), tuple(map(int, vote)), effective) != (1.25, (7, 2), "September 24, 2026"):
            raise ValueError("boj_reviewed_decision_changed")
    elif release["cc"] == "KR":
        if "등록일 2026.08.27" not in text:
            raise ValueError("bok_release_identity_changed")
        values = _unique(r"raise the Base Rate by ([\d.]+) basis points from ([\d.]+)% to ([\d.]+)%", body)
        if (tuple(map(float, values)) != (25.0, 2.75, 3.0)
                or "Six Monetary Policy Board members supported" not in body
                or "one member, Hwang Kunil" not in body):
            raise ValueError("bok_reviewed_decision_changed")
    elif release["cc"] == "AU":
        if "Number 2026-27 Date 29 September 2026" not in text:
            raise ValueError("rba_release_identity_changed")
        values = _unique(r"increase the cash rate target by ([\d.]+) basis points to ([\d.]+) per cent", body)
        if tuple(map(float, values)) != (25.0, 4.6):
            raise ValueError("rba_reviewed_decision_changed")
    elif release["cc"] == "EZ":
        values = _unique(r"deposit facility, the main refinancing operations and the marginal lending facility will be increased to ([\d.]+)%, ([\d.]+)% and ([\d.]+)% respectively, with effect from (16 September 2026)", body)
        if tuple(map(float, values[:3])) != (2.5, 2.65, 2.9) or values[3] != "16 September 2026":
            raise ValueError("ecb_reviewed_decision_changed")
    elif release["cc"] == "IN":
        if "Date : Oct 07, 2026" not in text and "Date: Oct 07, 2026" not in text:
            raise ValueError("rbi_release_identity_changed")
        values = _unique(r"MPC voted unanimously to increase the policy repo rate under the liquidity adjustment facility \(LAF\) by ([\d.]+) bps to ([\d.]+) per cent", body)
        if (tuple(map(float, values)) != (25.0, 5.5)
                or "Two members - Dr. Nagesh Kumar and Prof. Ram Singh -" not in body):
            raise ValueError("rbi_rate_or_stance_vote_changed")
    else:
        raise ValueError("policy_release_parser_missing")
    payload = {**release, "schema": "intl_policy_decision.v1", "unit": "percent",
               "action": release.get("action", "hold"), "first_observed_at": retrieved_at, "source_sha256": stamp}
    if supporting:
        payload["supporting_sources"] = supporting
    decision = normalize_policy_decision(payload, observed_at=retrieved_at)
    if decision is None:
        raise ValueError("policy_decision_admission_failed")
    return {"policy_decisions": [decision], "forecast_archive": forecasts}


def collect_registered_policy(fetch_bytes, *, retrieved_at):
    decisions, forecasts, sources, errors, reviews = [], [], [], [], []
    for release in RELEASES:
        if date.fromisoformat(release["published"]) > date.fromisoformat(retrieved_at[:10]):
            continue
        attempted_url = release["source_url"]
        stage = "download"
        try:
            blob = fetch_bytes(attempted_url, max_bytes=4_000_000)
            supporting = {}
            for url, _, _ in SUPPORT_DOCUMENTS.get(release["cc"], ()):
                attempted_url = url
                supporting[url] = fetch_bytes(url, max_bytes=4_000_000)
            stage = "qualification"
            parsed = parse_registered_policy_release(blob, release, retrieved_at=retrieved_at,
                                                      supporting_blobs=supporting)
            decisions.extend(parsed["policy_decisions"])
            record = parsed["policy_decisions"][0]
            reviews.append(normalize_policy_review({**release, "schema": "intl_policy_review.v1",
                "status": "verified", "record_id": record["record_id"],
                "source_sha256": sha256(blob).hexdigest(), "observed_at": retrieved_at}))
            forecasts.extend(parsed["forecast_archive"])
            sources.append({"provider": release["provider"], "url": release["source_url"],
                            "published": release["published"], "sha256": sha256(blob).hexdigest(),
                            "status": "verified", "retrieved_at": retrieved_at})
            for item in parsed["policy_decisions"][0].get("supporting_sources", []):
                sources.append({"provider": release["provider"], "url": item["source_url"],
                                "roles": item["roles"], "sha256": item["source_sha256"],
                                "status": "verified_support", "retrieved_at": retrieved_at})
        except Exception as exc:
            error = {"source": release["provider"], "source_url": release["source_url"],
                     "error": type(exc).__name__, "detail": str(exc)[:160], "stage": stage,
                     "attempted_at": retrieved_at, "status": "release_not_verified"}
            if stage == "download":
                error["failed_url"] = attempted_url
            errors.append(error)
            if stage == "qualification" and type(blob) is bytes and blob:
                reviews.append(normalize_policy_review({**release, "schema": "intl_policy_review.v1",
                    "status": "review_required", "record_id": None,
                    "source_sha256": sha256(blob).hexdigest(), "observed_at": retrieved_at}))
    return {"policy_decisions": decisions, "policy_reviews": [event for event in reviews if event],
            "forecast_archive": forecasts, "sources": sources, "errors": errors}
