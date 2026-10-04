"""Tests for engine/communique_diff.py — the Communiqué Diff engine (W4 B1, spec D9).

Covers:
  * phrase matching including VARIANT forms (适度宽松 ~ 适度宽松的货币政策)
  * APPEARED / DROPPED logic against a trailing window
  * COLD-START behavior (no prior window → no appeared/dropped, organ flagged)
  * LEAD_SHIFT on People's Daily front-page lead-domain change
  * salience-only qledger claim registration (direction=0, horizon 21, macro
    scope vs 510300.SS) + idempotency
  * qbus emit rows shape

All PURE / on fixtures; qledger writes are redirected to tmp_path.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import communique_diff as cd  # noqa: E402
from engine import qledger  # noqa: E402


def _book():
    return cd.load_phrase_book()


def _row(organ, title, body, crawled, url="u", rank=-1):
    return {"organ": organ, "title": title, "body": body, "url": url,
            "_crawled_at": crawled, "seendate": crawled[:10], "layout_rank": rank}


# --------------------------------------------------------------------------- #
# phrase book + matching
# --------------------------------------------------------------------------- #
def test_phrase_book_loads_canonical_formulas():
    book = _book()
    zh = {r["zh"] for r in book}
    # the spec's named canonical formulas must all be present
    for formula in ("适度宽松", "房住不炒", "新质生产力", "反内卷",
                    "稳中求进", "超常规逆周期调节"):
        assert formula in zh, f"{formula} missing from phrase book"
    assert len(book) >= 40   # ~44-formula seed


def test_variant_form_maps_to_canonical():
    book = _book()
    # the variant 适度宽松的货币政策 must register as the CANONICAL 适度宽松
    hits = cd.phrases_in_text("央行实施适度宽松的货币政策", book)
    assert "适度宽松" in hits
    # a full property variant maps to 房住不炒
    hits2 = cd.phrases_in_text("坚持房子是用来住的不是用来炒的", book)
    assert "房住不炒" in hits2


def test_empty_text_matches_nothing():
    assert cd.phrases_in_text("", _book()) == set()
    assert cd.phrases_in_text("no chinese policy formula here", _book()) == set()


def test_phrase_meta_carries_polarity_and_review_status():
    meta = cd.phrase_meta(_book())
    assert meta["适度宽松"]["domain"] == "monetary"
    assert meta["适度宽松"]["polarity"] == 1
    # polarity is human-review PROVISIONAL until reviewed (spec §5)
    assert meta["房住不炒"]["review_status"] == "PROVISIONAL"


# --------------------------------------------------------------------------- #
# appeared / dropped
# --------------------------------------------------------------------------- #
def test_appeared_and_dropped_against_window():
    book = _book()
    today = [_row("pboc", "适度宽松", "实施适度宽松的货币政策", "2026-07-02T01:00:00")]
    prior = [_row("pboc", "稳健", "稳健的货币政策 房住不炒", "2026-06-20T01:00:00")]
    res = cd.compute_events(today + prior, "2026-07-02", book=book, window_days=30)
    kinds = {(e["kind"], e["phrase"]) for e in res["events"]}
    assert ("APPEARED", "适度宽松") in kinds        # newly present vs window
    assert ("DROPPED", "房住不炒") in kinds          # in window, absent today
    assert ("DROPPED", "稳健的货币政策") in kinds
    assert res["cold_start_organs"] == []


def test_appeared_event_carries_evidence_and_meta():
    book = _book()
    today = [_row("ndrc", "新质生产力", "发展新质生产力",
                  "2026-07-02T01:00:00", url="http://ndrc/x")]
    prior = [_row("ndrc", "旧文", "供给侧结构性改革", "2026-06-20T01:00:00")]
    res = cd.compute_events(today + prior, "2026-07-02", book=book)
    appeared = [e for e in res["events"] if e["kind"] == "APPEARED"]
    e = next(x for x in appeared if x["phrase"] == "新质生产力")
    assert e["organ"] == "ndrc"
    assert e["domain"] == "industrial"
    assert e["evidence_url"] == "http://ndrc/x"
    assert e["review_status"] == "PROVISIONAL"
    assert e["event_id"].startswith("cd_")



# --------------------------------------------------------------------------- #
# CIE-09 source revisions are evidence, not policy novelty
# --------------------------------------------------------------------------- #
def test_same_locator_content_revision_is_separate_from_appeared_dropped():
    book = _book()
    url = "https://www.pbc.gov.cn/policy/one.html"
    prior = [_row("pboc", "稳健", "稳健的货币政策", "2026-07-01T01:00:00", url=url)]
    today = [_row("pboc", "更正", "实施适度宽松的货币政策", "2026-07-02T01:00:00", url=url)]
    locator = "loc_pboc_one"
    prior[0]["source_locator_id"] = locator
    today[0]["source_locator_id"] = locator

    res = cd.compute_events(prior + today, "2026-07-02", book=book)
    assert res["events"] == []
    assert res["counts"]["n_appeared"] == 0
    assert res["counts"]["n_dropped"] == 0
    assert res["counts"]["n_document_revisions"] == 1

    rev = res["document_revisions"][0]
    assert rev["classification"] == "SOURCE_CONTENT_CHANGED_UNVERIFIED"
    assert rev["url"] == url
    assert rev["observed_at"] == "2026-07-02T01:00:00"
    assert rev["previous_observed_at"] == "2026-07-01T01:00:00"
    assert rev["content_sha256"] != rev["supersedes_content_sha256"]


def test_source_revision_does_not_hide_independent_new_document_novelty():
    book = _book()
    stable_prior = _row(
        "ndrc", "基线", "稳中求进", "2026-07-01T01:00:00",
        url="https://www.ndrc.gov.cn/policy/base.html",
    )
    revised_prior = _row(
        "ndrc", "旧版本", "供给侧结构性改革", "2026-07-01T02:00:00",
        url="https://www.ndrc.gov.cn/policy/revised.html",
    )
    revised_today = _row(
        "ndrc", "更正版本", "适度宽松", "2026-07-02T01:00:00",
        url="https://www.ndrc.gov.cn/policy/revised.html",
    )
    revised_prior["source_locator_id"] = "loc_ndrc_revised"
    revised_today["source_locator_id"] = "loc_ndrc_revised"
    independent_today = _row(
        "ndrc", "新文件", "发展新质生产力", "2026-07-02T02:00:00",
        url="https://www.ndrc.gov.cn/policy/new.html",
    )

    res = cd.compute_events(
        [stable_prior, revised_prior, revised_today, independent_today],
        "2026-07-02", book=book,
    )
    appeared = {(e["kind"], e["phrase"]) for e in res["events"]}
    assert ("APPEARED", "新质生产力") in appeared
    assert res["counts"]["n_document_revisions"] == 1
    # The same-URL edit itself must not mint either phrase as policy novelty.
    assert ("APPEARED", "适度宽松") not in appeared
    assert ("DROPPED", "供给侧结构性改革") not in appeared


def test_revision_uses_full_locator_history_beyond_novelty_window():
    book = _book()
    locator = "loc_pboc_long_gap"
    # The predecessor is 60+ days old, outside the 30d novelty window.
    old = _row(
        "pboc", "旧版本", "供给侧结构性改革",
        "2026-04-01T01:00:00",
        url="https://www.pbc.gov.cn/policy/long-gap.html",
    )
    old["source_locator_id"] = locator
    stable_prior = _row(
        "pboc", "近期基线", "稳中求进",
        "2026-05-20T01:00:00",
        url="https://www.pbc.gov.cn/policy/baseline.html",
    )
    revised = _row(
        "pboc", "更正版本", "实施适度宽松的货币政策",
        "2026-06-01T01:00:00",
        url="https://www.pbc.gov.cn/policy/long-gap.html",
    )
    revised["source_locator_id"] = locator
    stable_today = _row(
        "pboc", "今日基线", "稳中求进",
        "2026-06-01T02:00:00",
        url="https://www.pbc.gov.cn/policy/today.html",
    )

    res = cd.compute_events(
        [old, stable_prior, revised, stable_today],
        "2026-06-01",
        book=book,
        window_days=30,
    )
    kinds = {(e["kind"], e["phrase"]) for e in res["events"]}
    assert res["counts"]["n_document_revisions"] == 1
    assert ("APPEARED", "适度宽松") not in kinds
    assert ("DROPPED", "供给侧结构性改革") not in kinds
    rev = res["document_revisions"][0]
    assert rev["previous_observed_at"] == "2026-04-01T01:00:00"
    assert rev["added_phrases"] == ["适度宽松"]
    assert rev["removed_phrases"] == ["供给侧结构性改革"]


def test_revision_neutral_phrases_stay_in_both_novelty_unions():
    book = _book()
    locator = "loc_ndrc_neutral"
    old = _row(
        "ndrc", "旧版本", "发展新质生产力 稳中求进",
        "2026-07-01T01:00:00",
        url="https://www.ndrc.gov.cn/policy/neutral.html",
    )
    old["source_locator_id"] = locator
    revised = _row(
        "ndrc", "更正版本", "发展新质生产力 稳中求进 反内卷",
        "2026-07-02T01:00:00",
        url="https://www.ndrc.gov.cn/policy/neutral.html",
    )
    revised["source_locator_id"] = locator
    # Independent document repeats a phrase that already existed in the prior
    # version. Removing the corrected locator wholesale would falsely mint APPEARED.
    independent_today = _row(
        "ndrc", "独立新文", "发展新质生产力",
        "2026-07-02T02:00:00",
        url="https://www.ndrc.gov.cn/policy/independent.html",
    )

    res = cd.compute_events(
        [old, revised, independent_today],
        "2026-07-02",
        book=book,
        window_days=30,
    )
    kinds = {(e["kind"], e["phrase"]) for e in res["events"]}
    assert res["counts"]["n_document_revisions"] == 1
    assert ("APPEARED", "新质生产力") not in kinds
    assert ("DROPPED", "稳中求进") not in kinds
    # The correction-only phrase delta is evidence, not ordinary novelty.
    assert ("APPEARED", "反内卷") not in kinds
    rev = res["document_revisions"][0]
    assert "新质生产力" in rev["unchanged_phrases"]
    assert "稳中求进" in rev["unchanged_phrases"]
    assert "反内卷" in rev["added_phrases"]


def test_revised_layout_lead_cannot_mint_lead_shift():
    book = _book()
    locator = "loc_pd_lead"
    prior = _row(
        "peoples_daily", "新质生产力", "",
        "2026-07-01T01:00:00",
        url="https://paper.people.com.cn/lead.html",
        rank=0,
    )
    prior["source_locator_id"] = locator
    today = _row(
        "peoples_daily", "房住不炒", "",
        "2026-07-02T01:00:00",
        url="https://paper.people.com.cn/lead.html",
        rank=0,
    )
    today["source_locator_id"] = locator

    res = cd.compute_events([prior, today], "2026-07-02", book=book)
    assert res["counts"]["n_document_revisions"] == 1
    assert res["counts"]["n_lead_shift"] == 0


def test_revision_neutralization_does_not_hide_unrelated_new_phrase():
    book = _book()
    locator = "loc_pboc_revision_plus_independent"
    prior = _row(
        "pboc", "旧版本", "稳中求进",
        "2026-07-01T01:00:00",
        url="https://www.pbc.gov.cn/policy/revised-2.html",
    )
    prior["source_locator_id"] = locator
    revised = _row(
        "pboc", "更正版本", "稳中求进 适度宽松",
        "2026-07-02T01:00:00",
        url="https://www.pbc.gov.cn/policy/revised-2.html",
    )
    revised["source_locator_id"] = locator
    independent = _row(
        "pboc", "独立新文", "超常规逆周期调节",
        "2026-07-02T02:00:00",
        url="https://www.pbc.gov.cn/policy/independent-2.html",
    )

    res = cd.compute_events([prior, revised, independent], "2026-07-02", book=book)
    kinds = {(e["kind"], e["phrase"]) for e in res["events"]}
    assert ("APPEARED", "适度宽松") not in kinds
    assert ("APPEARED", "超常规逆周期调节") in kinds


# --------------------------------------------------------------------------- #
# cold start
# --------------------------------------------------------------------------- #
def test_cold_start_emits_no_appear_drop_and_flags_organ():
    book = _book()
    # only a today document, NO prior window → cannot tell appeared from always-present
    today = [_row("pboc", "适度宽松", "实施适度宽松的货币政策", "2026-07-02T01:00:00")]
    res = cd.compute_events(today, "2026-07-02", book=book)
    assert res["counts"]["n_appeared"] == 0
    assert res["counts"]["n_dropped"] == 0
    assert "pboc" in res["cold_start_organs"]


def test_window_excludes_out_of_range_prior():
    book = _book()
    today = [_row("csrc", "反内卷", "综合整治内卷式竞争", "2026-07-02T01:00:00")]
    # prior doc is OUTSIDE the 30-day window → treated as no prior → cold start
    prior_old = [_row("csrc", "旧", "反内卷", "2026-01-01T01:00:00")]
    res = cd.compute_events(today + prior_old, "2026-07-02", book=book, window_days=30)
    assert "csrc" in res["cold_start_organs"]
    assert res["counts"]["n_appeared"] == 0


# --------------------------------------------------------------------------- #
# lead shift (People's Daily front-page prominence)
# --------------------------------------------------------------------------- #
def test_lead_shift_on_front_page_domain_change():
    book = _book()
    # prior day lead = tech (新质生产力 / 科技自立自强); today lead = property
    prior = [_row("peoples_daily", "科技自立自强 新质生产力", "", "2026-07-01T01:00:00",
                  url="a", rank=0)]
    today = [_row("peoples_daily", "房住不炒 保交楼", "", "2026-07-02T01:00:00",
                  url="b", rank=0)]
    res = cd.compute_events(prior + today, "2026-07-02", book=book)
    shifts = [e for e in res["events"] if e["kind"] == "LEAD_SHIFT"]
    assert len(shifts) == 1
    assert shifts[0]["from_domain"] in ("tech", "industrial")
    assert shifts[0]["to_domain"] == "property"


def test_no_lead_shift_when_domain_unchanged():
    book = _book()
    prior = [_row("peoples_daily", "适度宽松", "", "2026-07-01T01:00:00", url="a", rank=0)]
    today = [_row("peoples_daily", "降准降息", "", "2026-07-02T01:00:00", url="b", rank=0)]
    res = cd.compute_events(prior + today, "2026-07-02", book=book)
    # both lead items are monetary → no shift
    assert res["counts"]["n_lead_shift"] == 0


def test_lead_domain_reads_top_of_page():
    book = _book()
    rows = [_row("peoples_daily", "房住不炒", "", "2026-07-02T01:00:00", rank=0),
            _row("peoples_daily", "适度宽松", "", "2026-07-02T01:00:00", rank=1)]
    # rank 0 (front-page lead) is property, so that wins over the rank-1 monetary
    assert cd.lead_domain(rows, book) == "property"


# --------------------------------------------------------------------------- #
# qledger claim registration (salience-only) + qbus emit
# --------------------------------------------------------------------------- #
def test_register_claims_are_salience_only_macro(tmp_path):
    book = _book()
    today = [_row("pboc", "适度宽松", "实施适度宽松的货币政策", "2026-07-02T01:00:00")]
    prior = [_row("pboc", "稳健", "稳健的货币政策", "2026-06-20T01:00:00")]
    res = cd.compute_events(today + prior, "2026-07-02", book=book)
    n = cd.register_claims(res, root=tmp_path)
    assert n == res["counts"]["n_events"] > 0
    claims = qledger.load_claims(tmp_path)
    c = claims[0]
    assert c["desk"] == cd.DESK
    assert c["direction"] == 0                    # salience-only (polarity PROVISIONAL)
    assert c["horizon_d"] == cd.HORIZON_D == 21
    assert c["claim_family"] == cd.CLAIM_FAMILY
    assert c["scope"]["type"] == "macro"
    assert c["scope"]["key"] == "510300.SS"       # machine-checkable observable (D4)
    assert c["bench"] == "510300.SS"
    assert c["status"] == "open"                  # a valid macro claim, not rejected
    assert c["event_kind"] in ("APPEARED", "DROPPED")


def test_register_claims_idempotent(tmp_path):
    book = _book()
    today = [_row("ndrc", "反内卷", "综合整治内卷式竞争", "2026-07-02T01:00:00")]
    prior = [_row("ndrc", "旧", "供给侧结构性改革", "2026-06-20T01:00:00")]
    res = cd.compute_events(today + prior, "2026-07-02", book=book)
    cd.register_claims(res, root=tmp_path)
    n1 = len(qledger.load_claims(tmp_path))
    cd.register_claims(res, root=tmp_path)         # re-run
    n2 = len(qledger.load_claims(tmp_path))
    assert n1 == n2 and n1 > 0                      # dedupe by claim_id


def test_qbus_rows_shape():
    book = _book()
    today = [_row("pboc", "适度宽松", "实施适度宽松的货币政策", "2026-07-02T01:00:00")]
    prior = [_row("pboc", "稳健", "稳健的货币政策", "2026-06-20T01:00:00")]
    res = cd.compute_events(today + prior, "2026-07-02", book=book)
    rows = cd._to_qbus_rows(res, "2026-07-02T02:00:00")
    assert rows
    r = rows[0]
    assert r["desk"] == cd.DESK
    assert r["lang"] == "zh"
    assert r["source_tier"] == 1
    assert r["themes"] == ["policy"]
    assert r["timestamp_quality"] == "CRAWL_BOUNDED"


def test_no_events_when_corpus_empty():
    res = cd.compute_events([], "2026-07-02", book=_book())
    assert res["counts"]["n_events"] == 0
    assert res["events"] == []
