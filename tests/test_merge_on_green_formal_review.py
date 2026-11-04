"""Fail-closed formal-review gate for the incumbent Macro merge-on-green sweeper.

All network responses are synthetic. No merge endpoint or GitHub credentials used.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

import scripts.merge_on_green as MOG

HEAD = "a" * 40
OLD_HEAD = "b" * 40


def _pull():
    return {
        "number": 4242,
        "user": {"login": "builder"},
        "head": {"sha": HEAD},
    }


def _commit(author="builder", committer="build-bot", message="scoped fix"):
    return {
        "author": {"login": author},
        "committer": {"login": committer},
        "commit": {
            "author": {"name": author, "email": author + "@users.noreply.github.com"},
            "committer": {
                "name": committer,
                "email": committer + "@users.noreply.github.com",
            },
            "message": message,
        },
    }


def _review(
    login="independent", state="APPROVED", head=HEAD,
    ident=101, submitted="2026-11-03T16:00:00Z"
):
    return {
        "id": ident,
        "state": state,
        "user": {"login": login, "type": "User"},
        "commit_id": head,
        "submitted_at": submitted,
    }


def _wire(monkeypatch, reviews=None, commits=None, failures=None):
    reviews = [_review()] if reviews is None else reviews
    commits = [_commit()] if commits is None else commits
    failures = failures or {}
    calls = []

    def fake_request(method, url, token, payload=None):
        assert method == "GET"
        assert token == "read"
        resource = urlparse(url).path.rsplit("/", 1)[-1]
        page = int(parse_qs(urlparse(url).query)["page"][0])
        calls.append((resource, page))
        assert resource in {"reviews", "commits"}, url
        if resource in failures:
            return failures[resource], {"message": "not authorized or throttled"}
        seq = reviews if resource == "reviews" else commits
        return 200, seq[(page - 1) * 100: page * 100]

    monkeypatch.setattr(MOG, "_request", fake_request)
    return calls


def test_live_exact_head_non_author_approval_qualifies(monkeypatch):
    calls = _wire(monkeypatch)
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        True, "review-approved"
    )
    assert calls == [("reviews", 1), ("commits", 1)]


@pytest.mark.parametrize(
    "reviews,reason",
    [
        ([], "review-missing-current-independent-approval"),
        ([_review(head=OLD_HEAD)], "review-missing-current-independent-approval"),
        ([_review(login="builder")], "review-missing-current-independent-approval"),
        ([_review(login="build-bot")], "review-missing-current-independent-approval"),
        ([_review(state="DISMISSED")], "review-missing-current-independent-approval"),
        ([_review(state="CHANGES_REQUESTED")], "review-changes-requested"),
    ],
)
def test_missing_stale_self_and_revoked_reviews_do_not_qualify(monkeypatch, reviews, reason):
    _wire(monkeypatch, reviews=reviews)
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        False, reason
    )


def test_later_change_request_blocks_prior_approval_even_with_another_approval(monkeypatch):
    _wire(monkeypatch, reviews=[
        _review(login="other", ident=100, submitted="2026-11-03T14:00:00Z"),
        _review(login="independent", ident=101, submitted="2026-11-03T15:00:00Z"),
        _review(
            login="other", ident=102, state="CHANGES_REQUESTED",
            submitted="2026-11-03T16:00:00Z",
        ),
    ])
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        False, "review-changes-requested"
    )


def test_last_decisive_review_wins_and_comment_does_not_rescind(monkeypatch):
    _wire(monkeypatch, reviews=[
        _review(ident=100, state="CHANGES_REQUESTED", submitted="2026-11-03T13:00:00Z"),
        _review(ident=101, state="APPROVED", submitted="2026-11-03T14:00:00Z"),
        _review(ident=102, state="COMMENTED", submitted="2026-11-03T15:00:00Z"),
    ])
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        True, "review-approved"
    )


def test_coauthor_username_and_noreply_email_both_prevent_self_review(monkeypatch):
    for coauthor in (
        "Co-authored-by: independent <independent@users.noreply.github.com>",
        "Co-authored-by: Example <123+independent@users.noreply.github.com>",
    ):
        _wire(monkeypatch, commits=[_commit(message="Fix\n\n" + coauthor)])
        assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
            False, "review-missing-current-independent-approval"
        )


@pytest.mark.parametrize("resource", ["reviews", "commits"])
@pytest.mark.parametrize("status", [403, 429, 500])
def test_permission_rate_limit_or_server_failure_does_not_authorize(monkeypatch, resource, status):
    _wire(monkeypatch, failures={resource: status})
    ok, reason = MOG.formal_review_release_gate("acme/widgets", _pull(), "read")
    assert not ok
    assert reason in {"review-inventory-unreadable", "review-authorship-unreadable"}


@pytest.mark.parametrize("resource", ["reviews", "commits"])
def test_paginated_inventory_exceeding_bound_is_refused_not_truncated(monkeypatch, resource):
    rows = [_review(ident=200 + index) for index in range(300)]
    commits = [_commit()] * 300
    _wire(
        monkeypatch,
        reviews=rows if resource == "reviews" else [_review()],
        commits=commits if resource == "commits" else [_commit()],
    )
    ok, reason = MOG.formal_review_release_gate("acme/widgets", _pull(), "read")
    assert not ok
    assert reason == (
        "review-inventory-unreadable" if resource == "reviews"
        else "review-authorship-unreadable"
    )


def test_second_page_approval_is_read_and_accepted(monkeypatch):
    reviews = [_review(state="COMMENTED", ident=100 + i) for i in range(100)]
    reviews.append(_review(ident=500))
    calls = _wire(monkeypatch, reviews=reviews)
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        True, "review-approved"
    )
    assert calls == [("reviews", 1), ("reviews", 2), ("commits", 1)]


def test_no_pr_author_or_unverifiable_commit_authorship_fails_closed(monkeypatch):
    calls = _wire(monkeypatch)
    p = _pull()
    p.pop("user")
    assert MOG.formal_review_release_gate("acme/widgets", p, "read") == (
        False, "review-pr-identity-unknown"
    )
    assert not calls
    _wire(monkeypatch, commits=[{"commit": {"message": "incomplete"}}])
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        False, "review-authorship-unreadable"
    )


def test_unparseable_decisive_review_metadata_is_not_approval(monkeypatch):
    item = _review()
    item["submitted_at"] = "unparseable"
    _wire(monkeypatch, reviews=[item])
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        False, "review-state-unverifiable"
    )



def test_bot_or_unverified_account_type_never_satisfies_human_review(monkeypatch):
    for kind in ("Bot", None):
        item = _review()
        item["user"]["type"] = kind
        _wire(monkeypatch, reviews=[item])
        assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
            False, "review-missing-current-independent-approval"
        )


def test_later_dismissal_invalidates_current_head_approval(monkeypatch):
    _wire(monkeypatch, reviews=[
        _review(ident=201, submitted="2026-11-03T15:00:00Z"),
        _review(ident=202, state="DISMISSED", submitted="2026-11-03T16:00:00Z"),
    ])
    assert MOG.formal_review_release_gate("acme/widgets", _pull(), "read") == (
        False, "review-missing-current-independent-approval"
    )
