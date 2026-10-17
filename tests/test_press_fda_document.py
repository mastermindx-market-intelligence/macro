"""Offline tests for the FDA drug-release document reader.

Synthetic minimal HTML only: no live requests, no full copyrighted fixtures.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.press.fda_document import FDA_POLICY_URL, read_fda_drug_release

RELEASE_SLUG = (
    "fda-approves-nogapendekin-alfa-inbakicept-pmln-bladder-cancer"
)
RELEASE_URL_PATH = f"/drugs/resources-information-approved-drugs/{RELEASE_SLUG}"
CANONICAL_RELEASE_URL = "https://www.fda.gov" + RELEASE_URL_PATH
DEFAULT_PUBLISHED_META = "Wed, 10/14/2026 - 11:15"
PUBLISHED = datetime(2026, 10, 14, 15, 15, 50, tzinfo=timezone.utc)
QUALIFIERS = ["Cohort A of QUILT-3.032", "1-800-FDA-1088"]

RELEASE_BODY_PARAGRAPHS = (
    "On October 14, 2026, the Food and Drug Administration (FDA) approved "
    "nogapendekin alfa inbakicept-pmln (Anktiva) with Bacillus Calmette-"
    "Guérin (BCG) for adults with BCG-unresponsive non-muscle invasive "
    "bladder cancer (NMIBC)."
)
SUMMARY = (
    "On October 14, 2026, the Food and Drug Administration (FDA) approved "
    "nogapendekin alfa inbakicept-pmln (Anktiva) with Bacillus Calmette-"
    "Guérin (BCG) for adults with BCG-unresponsive non-muscle invasive "
    "bladder cancer (NMIBC)."
)
EFFICACY_PARAGRAPHS = (
    "Efficacy was previously demonstrated in Cohort A of QUILT-3.032, a "
    "single-arm, multicenter trial of 77 patients with BCG-unresponsive "
    "high-risk NMIBC. The CR rate was 62% (95% CI: 51, 73).",
    "The most common adverse reactions (≥15%) were increased creatinine, "
    "dysuria, hematuria, and pyrexia.",
    "Healthcare professionals should report all serious adverse events "
    "suspected to be associated with the use of any medicine and device to "
    "FDA’s MedWatch Reporting System or by calling 1-800-FDA-1088.",
    "Recommended Dosage: the recommended dose is 400 mcg administered "
    "intravesically with BCG once a week for 6 weeks as induction therapy.",
)

POLICY_SENTENCE_1 = (
    "Unless otherwise noted, the contents of the FDA website (www.fda.gov) "
    "— both text and graphics — are not copyrighted."
)
POLICY_SENTENCE_2 = (
    "They are in the public domain and may be republished, reprinted and "
    "otherwise used freely by anyone without the need to obtain permission "
    "from FDA."
)
POLICY_TAIL = (
    "If a person, nonetheless, decides to copy content or images, FDA "
    "strongly recommends that the copied item lists the date that the "
    "material was copied and provides a link back to its source on the FDA "
    "website."
)


def release_doc(
    *,
    canonical=CANONICAL_RELEASE_URL,
    published_meta=DEFAULT_PUBLISHED_META,
    paragraphs=(SUMMARY,) + EFFICACY_PARAGRAPHS,
    wrapper=True,
    extra_canonicals=(),
    extra_metas=(),
    extra_articles=(),
):
    head = _canonical_link(canonical)
    head += "".join(_canonical_link(href) for href in extra_canonicals)
    head += _published_meta_tag(published_meta) + "".join(extra_metas)
    inner = _article(paragraphs)
    if wrapper:
        inner = inner.replace("<article>", '<article><div class="col-md-8">').replace("</article>", "</div></article>")
    for extra in extra_articles:
        inner += extra.replace("<article>", '<article><div class="col-md-8">').replace("</article>", "</div></article>")
    return (
        "<!doctype html><html><head>" + head + "</head>"
        "<body><main>" + inner + "</main></body></html>"
    )


def policy_doc(
    *,
    canonical=FDA_POLICY_URL,
    sentences=(POLICY_SENTENCE_1, POLICY_SENTENCE_2, POLICY_TAIL),
    extra_head="",
):
    body = "".join(f"<p>{sentence}</p>" for sentence in sentences)
    return (
        "<!doctype html><html><head>" + _canonical_link(canonical) + extra_head
        + "</head><body><article><div class=\"col-md-8\">" + body
        + "</div></article></body></html>"
    )


def _canonical_link(href):
    return "" if href is None else f'<link rel="canonical" href="{href}">'


def _published_meta_tag(content):
    return (
        ""
        if content is None
        else f'<meta property="article:published_time" content="{content}">'
    )


def _article(paragraphs):
    return "<article>" + "".join(f"<p>{p}</p>" for p in paragraphs) + "</article>"


def write_pair(tmp_path, release_text, policy_text):
    release_path = tmp_path / "release.html"
    policy_path = tmp_path / "policy.html"
    release_path.write_text(release_text, encoding="utf-8")
    policy_path.write_text(policy_text, encoding="utf-8")
    q = {
        "item_url": "http://www.fda.gov" + RELEASE_URL_PATH,
        "event_date": "2026-10-14",
        "release_sha256": hashlib.sha256(release_path.read_bytes()).hexdigest(),
        "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
        "rights_basis": {"policy_url": FDA_POLICY_URL},
        "source_qualifiers": list(QUALIFIERS),
    }
    return q, release_path, policy_path


def read_ok(tmp_path, **kwargs):
    q, release_path, policy_path = write_pair(
        tmp_path, kwargs.pop("release", release_doc()), kwargs.pop("policy", policy_doc())
    )
    q.update(kwargs.pop("q_updates", {}))
    return read_fda_drug_release(
        q, kwargs.pop("summary", SUMMARY), kwargs.pop("published", PUBLISHED),
        release_path, policy_path,
    )


def read_refuses(tmp_path, message_part, **kwargs):
    q, release_path, policy_path = write_pair(
        tmp_path, kwargs.pop("release", release_doc()), kwargs.pop("policy", policy_doc())
    )
    q.update(kwargs.pop("q_updates", {}))
    with pytest.raises(ValueError) as excinfo:
        read_fda_drug_release(
            q, kwargs.pop("summary", SUMMARY), kwargs.pop("published", PUBLISHED),
            release_path, policy_path,
        )
    assert message_part in str(excinfo.value)


def test_valid_release_returns_entire_clean_body(tmp_path):
    q, release_path, policy_path = write_pair(tmp_path, release_doc(), policy_doc())
    release_bytes_before = release_path.read_bytes()
    body = read_fda_drug_release(q, SUMMARY, PUBLISHED, release_path, policy_path)
    # Entire body, not just the summary.
    assert body == " ".join((SUMMARY,) + EFFICACY_PARAGRAPHS)
    assert SUMMARY in body and len(body) > len(SUMMARY)
    # Old-cohort and safety qualifiers preserved verbatim.
    assert "Cohort A of QUILT-3.032" in body
    assert "1-800-FDA-1088" in body
    assert "62% (95% CI: 51, 73)" in body
    # Input bytes unchanged by the read.
    assert release_path.read_bytes() == release_bytes_before


def test_https_item_url_accepted(tmp_path):
    body = read_ok(
        tmp_path,
        q_updates={"item_url": CANONICAL_RELEASE_URL},
    )
    assert "October 14, 2026" in body


def test_unrelated_layout_columns_do_not_change_the_article_body(tmp_path):
    doc = release_doc().replace('</main>', '<div class="col-md-8">Navigation</div></main>')
    assert 'Navigation' not in read_ok(tmp_path, release=doc)


def test_policy_language_outside_the_canonical_body_cannot_qualify(tmp_path):
    doc = policy_doc(sentences=('No reuse statement here.',)).replace(
        '</body>', '<footer>' + POLICY_SENTENCE_1 + POLICY_SENTENCE_2 + POLICY_TAIL + '</footer></body>')
    read_refuses(tmp_path, 'policy is missing', policy=doc)


def test_blank_summary_cannot_corroborate_any_release(tmp_path):
    read_refuses(tmp_path, 'summary', summary='  ')


@pytest.mark.parametrize('url', [
    'https://www.fda.gov:' + RELEASE_URL_PATH,
    'https://WWW.FDA.GOV' + RELEASE_URL_PATH,
    'https://www.fda.gov/drugs/resources-information-approved-drugs/%2e%2e',
    CANONICAL_RELEASE_URL + '?',
    CANONICAL_RELEASE_URL + '#',
    CANONICAL_RELEASE_URL.replace('www.fda.gov', 'www.f\nda.gov'),
])
def test_noncanonical_authority_and_escaped_slug_refuse(tmp_path, url):
    read_refuses(tmp_path, 'item_url', q_updates={'item_url': url})


def test_cross_utc_midnight_cannot_relabel_the_publisher_day(tmp_path):
    # 20:00 UTC-5 is still October 14 locally even though UTC says October 15.
    published = datetime(2026, 10, 14, 20, 0, tzinfo=timezone(timedelta(hours=-5)))
    read_refuses(tmp_path, "same day", published=published)


def test_policy_published_date_need_not_match_event(tmp_path):
    stale_policy = policy_doc(
        extra_head='<meta property="article:published_time" '
        'content="Mon, 06/01/2020 - 09:00">'
    )
    body = read_ok(tmp_path, policy=stale_policy)
    assert "Cohort A of QUILT-3.032" in body


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://www.fda.gov.abs.example" + RELEASE_URL_PATH,  # lookalike host
        "https://fda.gov" + RELEASE_URL_PATH,  # non-www host
        "https://www.fda.gov/about-fda/about-website/website-policies",  # wrong route
        "https://www.fda.gov" + RELEASE_URL_PATH + "?utm_source=rss",  # query string
        "https://editor@www.fda.gov:8443" + RELEASE_URL_PATH,  # userinfo and port
    ],
)
def test_bad_item_url_refused(tmp_path, bad_url):
    read_refuses(tmp_path, "item_url", q_updates={"item_url": bad_url})


@pytest.mark.parametrize("which", ["release", "policy"])
def test_evidence_hash_mismatch_refused(tmp_path, which):
    q, release_path, policy_path = write_pair(tmp_path, release_doc(), policy_doc())
    if which == "release":
        release_path.write_text(release_doc(paragraphs=(SUMMARY, "<p>tampered</p>")), encoding="utf-8")
    else:
        policy_path.write_text(policy_doc(sentences=(POLICY_SENTENCE_1, "changed.")), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        read_fda_drug_release(q, SUMMARY, PUBLISHED, release_path, policy_path)


@pytest.mark.parametrize(
    "release_kwargs",
    [
        {"canonical": None},  # missing canonical
        {"extra_canonicals": (CANONICAL_RELEASE_URL,)},  # duplicate canonical
        {"canonical": "https://www.fda.gov.example" + RELEASE_URL_PATH},  # wrong href
    ],
)
def test_bad_release_canonical_refused(tmp_path, release_kwargs):
    read_refuses(tmp_path, "canonical", release=release_doc(**release_kwargs))


@pytest.mark.parametrize(
    "policy_kwargs",
    [
        {"canonical": None},
        {"canonical": "https://www.fda.gov/about-fda"},
    ],
)
def test_bad_policy_canonical_refused(tmp_path, policy_kwargs):
    read_refuses(tmp_path, "canonical", policy=policy_doc(**policy_kwargs))


@pytest.mark.parametrize(
    "release_kwargs,message_part",
    [
        ({"extra_articles": ("<article><p>A second article.</p></article>",)}, "article"),
        ({"wrapper": False}, "div.col-md-8"),
        ({"paragraphs": ("",)}, "empty"),
        ({"paragraphs": ("x" * 20_050,)}, "20,000"),
    ],
)
def test_bad_release_body_refused(tmp_path, release_kwargs, message_part):
    read_refuses(tmp_path, message_part, release=release_doc(**release_kwargs))


@pytest.mark.parametrize(
    "release_kwargs",
    [
        {"published_meta": None},
        {"extra_metas": (_published_meta_tag(DEFAULT_PUBLISHED_META),)},
        {"published_meta": "2026-10-14T11:15:50Z"},  # not the observed FDA format
        {"published_meta": None, "extra_metas": (
            '<meta property="article:modified_time" content="Thu, 10/15/2026 - 09:00">',
        )},  # updated metadata never substitutes for the publisher date
    ],
)
def test_bad_or_ambiguous_publisher_metadata_refused(tmp_path, release_kwargs):
    read_refuses(tmp_path, "published_time", release=release_doc(**release_kwargs))


@pytest.mark.parametrize(
    "published,event_day",
    [
        (datetime(2026, 10, 14, 15, 15, 50, tzinfo=timezone.utc), "2026-10-15"),
        (datetime(2026, 10, 15, 0, 30, tzinfo=timezone.utc), "2026-10-14"),
        (datetime(2026, 10, 15, 1, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))), "2026-10-14"),
    ],
)
def test_event_day_mismatch_refused(tmp_path, published, event_day):
    read_refuses(
        tmp_path,
        "same day",
        published=published,
        q_updates={"event_date": event_day},
    )


def test_naive_published_instant_refused(tmp_path):
    read_refuses(
        tmp_path,
        "timezone",
        published=datetime(2026, 10, 14, 15, 15, 50),
    )


def test_summary_not_in_body_refused(tmp_path):
    read_refuses(
        tmp_path,
        "summary",
        summary="FDA approved an unrelated oncology product today.",
    )


def test_full_event_date_absent_from_body_refused(tmp_path):
    trimmed = (SUMMARY.replace("October 14, 2026", "10/14/2026"),) + EFFICACY_PARAGRAPHS
    read_refuses(
        tmp_path,
        "full event date",
        release=release_doc(paragraphs=trimmed),
    )


@pytest.mark.parametrize(
    "sentences,message_part",
    [
        # Policy exception wording absent.
        ((POLICY_SENTENCE_2, POLICY_TAIL), "not-copyrighted"),
        ((POLICY_SENTENCE_1, POLICY_TAIL), "public-domain"),
        # Copied-date recommendation absent.
        ((POLICY_SENTENCE_1, POLICY_SENTENCE_2, POLICY_TAIL.replace(
            "lists the date that the material was copied and ", "")), "copied-date"),
        # Link-back-to-source recommendation absent.
        ((POLICY_SENTENCE_1, POLICY_SENTENCE_2, POLICY_TAIL.replace(
            "and provides a link back to its source", "")), "link-back"),
    ],
)
def test_incomplete_policy_text_refused(tmp_path, sentences, message_part):
    read_refuses(tmp_path, message_part, policy=policy_doc(sentences=sentences))


@pytest.mark.parametrize(
    "qualifiers,message_part",
    [
        ([], "1.."),
        ([f"QUILT-3.032 Cohort {n} of the trial" for n in range(11)], "1.."),
        (["1-800-FDA-1088", "1-800-FDA-1088", "Cohort A of QUILT-3.032"], "distinct"),
        (["This number appears nowhere in the release body"], "present in release body"),
        ([""], "nonempty"),
        (["Q" * 1001], "at most 1000"),
    ],
)
def test_bad_source_qualifiers_refused(tmp_path, qualifiers, message_part):
    read_refuses(
        tmp_path, message_part, q_updates={"source_qualifiers": qualifiers}
    )


def test_non_fda_policy_url_refused(tmp_path):
    read_refuses(
        tmp_path,
        "policy URL",
        q_updates={"rights_basis": {"policy_url": "https://www.fda.gov/about-fda"}},
    )
