"""Offline source-boundary witnesses; these HTML responses are synthetic fixtures."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import pytest

from collectors import china_ths_concepts as ths

BOARD = "301558"
CLOCK_A = "2026-10-04T02:00:00Z"
CLOCK_B = "2026-10-04T02:00:01Z"


def _url(page=1, board=BOARD):
    return f"https://q.10jqka.com.cn/gn/detail/order/desc/page/{page}/ajax/1/code/{board}/"


def _table(codes):
    return ('<table><thead><tr><th>代码</th><th>名称</th></tr></thead><tbody>'
            + "".join(f"<tr><td>{code}</td><td>fixture-{code}</td></tr>" for code in codes)
            + "</tbody></table>")


@dataclass
class Response:
    text: str
    url: str
    status_code: int = 200
    headers: dict | None = None

    @property
    def content(self):
        return self.text.encode("utf-8")


class Session:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        page = int(url.split("/page/")[1].split("/")[0])
        outcome = self.outcomes[page]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(ths.time, "sleep", lambda *args: None)
    # Any unstubbed attempt to mint a network/cookie session is a test failure.
    monkeypatch.setattr(ths, "_session", lambda *args: pytest.fail("unexpected real session"))
    monkeypatch.setattr(ths, "_collection_clock", lambda: CLOCK_A, raising=False)


def _observe(monkeypatch, outcomes, *, clocks=(CLOCK_A, CLOCK_B)):
    session = Session(outcomes)
    monkeypatch.setattr(ths, "_session", lambda *args: session)
    ticks = iter(clocks)
    monkeypatch.setattr(ths, "_collection_clock", lambda: next(ticks), raising=False)
    return ths.concept_members_observation(BOARD, session), session


def test_complete_positive_receipt_is_bound_to_response_and_truthful_clock(monkeypatch):
    html = _table(["600001", "000002"])
    observation, session = _observe(monkeypatch, {1: Response(html, _url())})
    assert observation["state"] == "complete_nonempty"
    assert observation["qualified"] is True
    assert observation["board_id"] == BOARD
    assert observation["members"] == [
        {"ticker": "600001.SS", "name": "fixture-600001"},
        {"ticker": "000002.SZ", "name": "fixture-000002"},
    ]
    assert observation["started_at"] == CLOCK_A and observation["finished_at"] == CLOCK_B
    assert observation["source_asof"] is None and observation["source_asof_status"] == "unknown"
    assert observation["completion_basis"] == "short_member_page"
    assert observation["coverage"]["unique_members"] == 2
    assert observation["coverage"]["expected_members"] is None
    receipt = observation["responses"][0]
    assert receipt["requested_url"] == receipt["response_url"] == _url()
    assert receipt["body_sha256"] == hashlib.sha256(html.encode()).hexdigest()
    assert receipt["body_bytes"] == len(html.encode())
    assert session.calls == [(_url(), 25)]
    json.dumps(observation)


@pytest.mark.parametrize("html,reason", [
    ("", "member_table_parse_failed"),
    ("<html>access denied</html>", "member_table_parse_failed"),
    ("<table><tr><th>广告</th></tr><tr><td>blocked</td></tr></table>", "member_columns_invalid"),
    (_table([]), "empty_membership_unconfirmed"),
])
def test_empty_or_interstitial_html_never_certifies_complete_empty(monkeypatch, html, reason):
    observation, _ = _observe(monkeypatch, {1: Response(html, _url())})
    assert observation["qualified"] is False
    assert observation["state"] != "complete_empty"
    assert observation["members"] == []
    assert observation["reason"] == reason
    assert observation["source_asof"] is None


def test_a_source_response_date_header_is_not_a_membership_publication_clock(monkeypatch):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001"]), _url(),
                               headers={"Date": "Sat, 04 Oct 2026 02:00:00 GMT"})})
    assert observation["qualified"] is True
    assert observation["source_asof"] is None
    assert observation["source_asof_status"] == "unknown"


def test_two_valid_pages_preserve_all_members_and_completion_basis(monkeypatch):
    first = [f"6000{i:02d}" for i in range(10)]
    second = ["600010", "600011"]
    observation, session = _observe(monkeypatch, {
        1: Response(_table(first), _url(1)), 2: Response(_table(second), _url(2))})
    assert observation["state"] == "complete_nonempty"
    assert len(observation["members"]) == 12
    assert observation["coverage"]["pages_parsed"] == 2
    assert [r["page"] for r in observation["responses"]] == [1, 2]
    assert len(session.calls) == 2


def test_valid_empty_terminal_member_table_after_a_full_page_is_not_an_empty_board(monkeypatch):
    first = [f"6000{i:02d}" for i in range(10)]
    observation, _ = _observe(monkeypatch, {
        1: Response(_table(first), _url(1)), 2: Response(_table([]), _url(2))})
    assert observation["state"] == "complete_nonempty"
    assert observation["qualified"] is True and len(observation["members"]) == 10
    assert observation["completion_basis"] == "terminal_empty_member_table"


@pytest.mark.parametrize("failure,reason", [
    (OSError("fixture network outage"), "fetch_failed"),
    (Response("", _url(2), status_code=403), "http_failure"),
    (Response("", _url(2)), "member_table_parse_failed"),
    (Response("<table><tr><th>notice</th></tr><tr><td>blocked</td></tr></table>", _url(2)),
     "member_columns_invalid"),
])
def test_truncation_or_omitted_second_page_retains_partial_facts_without_admission(monkeypatch, failure, reason):
    first = [f"6000{i:02d}" for i in range(10)]
    observation, _ = _observe(monkeypatch, {1: Response(_table(first), _url(1)), 2: failure})
    assert observation["state"] == "partial"
    assert observation["qualified"] is False
    assert len(observation["members"]) == 10
    assert observation["reason"] == reason


@pytest.mark.parametrize("failure,reason", [
    (OSError("fixture network outage"), "fetch_failed"),
    (Response("", _url(), status_code=429), "http_failure"),
])
def test_failed_first_page_is_not_an_empty_observation(monkeypatch, failure, reason):
    observation, _ = _observe(monkeypatch, {1: failure})
    assert observation["state"] == "failed" and observation["qualified"] is False
    assert observation["members"] == []
    assert observation["reason"] == reason
    assert observation["coverage"]["pages_parsed"] == 0


@pytest.mark.parametrize("response_url", [_url(board="301559"), _url(2),
                                          "https://example.test/gn/detail/order/desc/page/1/ajax/1/code/301558/"])
def test_response_identity_mismatch_refuses_other_board_page_or_origin(monkeypatch, response_url):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001"]), response_url)})
    assert observation["qualified"] is False
    assert observation["reason"] == "response_identity_mismatch"
    assert observation["board_id"] == BOARD and observation["members"] == []


def test_unknown_response_identity_is_uncovered_not_fabricated_from_request(monkeypatch):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001"]), None)})
    assert observation["qualified"] is False
    assert observation["reason"] == "response_identity_unknown"
    assert observation["responses"][0]["response_url"] is None


@pytest.mark.parametrize("board", ["", "not-a-board", "301558/../301559", None])
def test_invalid_board_is_uncovered_without_fetch(monkeypatch, board):
    session = Session({})
    observation = ths.concept_members_observation(board, session)
    assert observation["state"] == "uncovered" and observation["qualified"] is False
    assert observation["reason"] == "invalid_board_id" and observation["responses"] == []
    assert session.calls == []


def test_page_ceiling_with_no_natural_end_is_partial(monkeypatch):
    monkeypatch.setattr(ths, "_MAX_PAGES", 2)
    observation, _ = _observe(monkeypatch, {
        page: Response(_table([f"60{page}{i:03d}" for i in range(10)]), _url(page))
        for page in (1, 2)})
    assert observation["state"] == "partial" and observation["qualified"] is False
    assert len(observation["members"]) == 20
    assert observation["reason"] == "page_ceiling_without_end"


def test_full_repeated_page_cannot_substitute_for_missing_member_coverage(monkeypatch):
    codes = [f"6000{i:02d}" for i in range(10)]
    observation, session = _observe(monkeypatch, {
        1: Response(_table(codes), _url(1)), 2: Response(_table(codes), _url(2))})
    assert observation["state"] == "partial" and observation["qualified"] is False
    assert observation["reason"] == "repeated_member_page"
    assert len(observation["members"]) == 10 and len(session.calls) == 2


def test_duplicate_members_are_disclosed_and_do_not_duplicate_identity(monkeypatch):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001", "600001"]), _url())})
    assert len(observation["members"]) == 1
    assert observation["coverage"]["duplicate_members"] == 1


@pytest.mark.parametrize("code", ["not-a-security", "-1"])
def test_invalid_member_identity_does_not_qualify_a_short_page(monkeypatch, code):
    observation, _ = _observe(monkeypatch, {1: Response(_table([code]), _url())})
    assert observation["qualified"] is False and observation["members"] == []
    assert observation["reason"] == "member_identity_invalid"


def test_repeat_receipt_identity_excludes_rerun_clock_but_changes_with_source_bytes(monkeypatch):
    html = _table(["600001"])
    first, _ = _observe(monkeypatch, {1: Response(html, _url())})
    second, _ = _observe(monkeypatch, {1: Response(html, _url())},
                          clocks=("2026-10-05T02:00:00Z", "2026-10-05T02:00:01Z"))
    corrected, _ = _observe(monkeypatch, {1: Response(_table(["600002"]), _url())})
    assert first["observation_id"] == second["observation_id"]
    assert first["started_at"] != second["started_at"]
    assert first["observation_id"] != corrected["observation_id"]


def test_compatibility_wrapper_returns_list_only_for_admitted_positive(monkeypatch):
    session = Session({1: Response(_table(["600001"]), _url())})
    assert ths.concept_members(BOARD, session) == [{"ticker": "600001.SS", "name": "fixture-600001"}]


def test_compatibility_wrapper_keeps_empty_board_unresolved(monkeypatch):
    session = Session({1: Response(_table([]), _url())})
    assert ths.concept_members(BOARD, session) == []


def test_compatibility_wrapper_does_not_return_partial_on_missing_page(monkeypatch):
    session = Session({1: Response(_table([f"6000{i:02d}" for i in range(10)]), _url()),
                       2: Response("", _url(2))})
    monkeypatch.setattr(ths, "_session", lambda *args: session)
    with pytest.raises(ths.ThsTruncated):
        ths.concept_members(BOARD, session)



def test_integral_numeric_html_code_preserves_legacy_ticker_compatibility(monkeypatch):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001.0"]), _url())})
    assert observation["qualified"] is True
    assert observation["members"][0]["ticker"] == "600001.SS"


def test_fractional_numeric_code_cannot_be_silently_truncated_into_an_identity(monkeypatch):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001.5"]), _url())})
    assert observation["qualified"] is False
    assert observation["reason"] == "member_identity_invalid"


def test_same_path_redirect_with_changed_query_cannot_bind_another_population(monkeypatch):
    observation, _ = _observe(monkeypatch, {1: Response(_table(["600001"]), _url() + "?code=301559")})
    assert observation["qualified"] is False
    assert observation["reason"] == "response_identity_mismatch"


def test_retry_history_is_audit_evidence_not_a_new_positive_source_observation(monkeypatch):
    html = _table(["600001"])
    first, _ = _observe(monkeypatch, {1: Response(html, _url())})
    class RetrySession:
        def __init__(self):
            self.calls = 0
        def get(self, url, timeout):
            self.calls += 1
            return Response("", url, status_code=503) if self.calls == 1 else Response(html, url)
    retry = RetrySession()
    monkeypatch.setattr(ths, "_session", lambda *args: retry)
    monkeypatch.setattr(ths, "_collection_clock", lambda: CLOCK_B, raising=False)
    repeated = ths.concept_members_observation(BOARD, retry)
    assert repeated["qualified"] is True
    assert repeated["observation_id"] == first["observation_id"]
    assert len(repeated["responses"]) == 2 and retry.calls == 2



@pytest.mark.parametrize("page", [1, 2])
def test_parser_recovery_of_unclosed_html_cannot_supply_a_completion_receipt(monkeypatch, page):
    broken = _table(["600099"]).removesuffix("</table>")
    outcomes = {page: Response(broken, _url(page))}
    if page == 2:
        outcomes[1] = Response(_table([f"6000{i:02d}" for i in range(10)]), _url(1))
    observation, _ = _observe(monkeypatch, outcomes)
    assert observation["state"] == "partial" and observation["qualified"] is False
    assert observation["reason"] == "member_table_unclosed"
    assert len(observation["members"]) == (1 if page == 1 else 11)
    assert observation["responses"][-1]["member_table_closed"] is False


def test_closed_hidden_table_cannot_mask_a_truncated_member_table(monkeypatch):
    hidden = '<table style="display:none"><tr><th>discard</th></tr></table>'
    broken = hidden + _table(["600099"]).removesuffix("</table>")
    observation, _ = _observe(monkeypatch, {1: Response(broken, _url(1))})
    assert observation["state"] == "partial" and not observation["qualified"]
    assert observation["reason"] == "member_table_unclosed"
    assert observation["members"] == [{"ticker": "600099.SS", "name": "fixture-600099"}]


@pytest.mark.parametrize("page", [1, 2])
def test_unclosed_empty_table_is_never_a_pagination_end(monkeypatch, page):
    outcomes = {page: Response(_table([]).removesuffix("</table>"), _url(page))}
    if page == 2:
        outcomes[1] = Response(_table([f"600{i:03}" for i in range(10)]), _url(1))
    observation, _ = _observe(monkeypatch, outcomes)
    assert observation["state"] == ("failed" if page == 1 else "partial")
    assert not observation["qualified"]
    assert observation["reason"] == "member_table_unclosed"


def test_compatibility_wrapper_refuses_recovered_truncated_members(monkeypatch):
    session = Session({1: Response(_table(["600099"]).removesuffix("</table>"), _url(1))})
    with pytest.raises(ths.ThsTruncated, match="member_table_unclosed"):
        ths.concept_members("301558", session)


@pytest.mark.parametrize("second,reason,unique", [
    (_table([f"6000{i:02d}" for i in range(2)]), "repeated_member_page", 10),
    ('<div class="error">访问过于频繁，请稍后重试</div>' + _table([]),
     "source_error_response", 10),
    (_table(["600010"]).replace("<table>", '<table style="display:none">') + _table([]),
     "member_tables_ambiguous", 11),
])
def test_independent_terminal_counterexamples_remain_partial(monkeypatch, second, reason, unique):
    first = _table([f"6000{i:02d}" for i in range(10)])
    outcomes = {1: Response(first, _url(1)), 2: Response(second, _url(2))}
    observation, _ = _observe(monkeypatch, outcomes)
    assert observation["state"] == "partial" and not observation["qualified"]
    assert observation["reason"] == reason
    assert observation["completion_basis"] is None
    assert len(observation["members"]) == unique
    if reason == "repeated_member_page":
        assert observation["coverage"]["duplicate_members"] == 2
    monkeypatch.setattr(ths, "_collection_clock", lambda: CLOCK_A)
    with pytest.raises(ths.ThsTruncated, match=reason):
        ths.concept_members(BOARD, Session(outcomes))


def test_unique_member_table_after_unrelated_table_can_qualify(monkeypatch):
    unrelated = "<table><tr><th>notice</th></tr><tr><td>fixture notice</td></tr></table>"
    observation, _ = _observe(monkeypatch, {
        1: Response(unrelated + _table(["600099"]), _url(1))})
    assert observation["qualified"] and observation["state"] == "complete_nonempty"
    assert observation["members"] == [{"ticker": "600099.SS", "name": "fixture-600099"}]
    assert observation["responses"][0]["member_table_count"] == 1


def test_explicit_error_with_positive_rows_preserves_only_partial_facts(monkeypatch):
    html = '<div class="error">访问过于频繁，请稍后重试</div>' + _table(["600099"])
    observation, _ = _observe(monkeypatch, {1: Response(html, _url(1))})
    assert observation["state"] == "partial" and not observation["qualified"]
    assert observation["reason"] == "source_error_response"
    assert observation["members"] == [{"ticker": "600099.SS", "name": "fixture-600099"}]
    assert observation["responses"][0]["source_error"] is True


def test_two_closed_positive_member_tables_cannot_certify_a_unique_population(monkeypatch):
    observation, _ = _observe(monkeypatch, {
        1: Response(_table(["600098"]) + _table(["600099"]), _url(1))})
    assert observation["state"] == "partial" and not observation["qualified"]
    assert observation["reason"] == "member_tables_ambiguous"
    assert {member["ticker"] for member in observation["members"]} == {"600098.SS", "600099.SS"}
    assert observation["responses"][0]["member_table_count"] == 2
