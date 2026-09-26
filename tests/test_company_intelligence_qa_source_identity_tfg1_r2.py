"""TFG-1 R2 — source-native separator / questioner / respondent-role law.

Hostile format discriminators for the frozen law. Every case is synthetic; no held
revision, no network, no model call, and no holdout body is touched.
"""
from __future__ import annotations

import pytest

from engine.company_intelligence import qa_source_identity as si


def _seg(role: str, speaker: str, text: str) -> dict[str, str]:
    return {"role": role, "speaker": speaker, "text": text}


def _call(*segments: dict[str, str]) -> list[dict[str, str]]:
    return list(segments)


# --------------------------------------------------------------------------- separators


@pytest.mark.parametrize(
    "handoff",
    [
        "Our next question comes from the line of Dana Reyes with North Peak. Please go ahead.",
        "Our next question comes from the line of Dana Reyes with North Peak. Your line is now open.",
        "Our next question comes from the line of Dana Reyes with North Peak. Your line is live.",
        "Your next question comes from Dana Reyes with North Peak.",
        "We'll move on now to Dana Reyes with North Peak.",
    ],
)
def test_named_question_handoff_is_a_separator_in_every_dialect(handoff: str) -> None:
    """Terminal cue phrases carry zero admission authority."""
    segments = _call(
        _seg("Operator", "Operator", handoff),
        _seg("", "Dana Reyes", "Thanks. How is pricing trending?"),
        _seg("CEO", "Robin Vale", "Pricing is stable."),
    )
    assert si.structural_separators(segments) == [0]


@pytest.mark.parametrize(
    "text",
    [
        "To ask a question, please press star one one. Please go ahead and queue up.",
        "Ladies and gentlemen, that concludes today's conference. You may now disconnect.",
        "I would now like to turn the call back over to Robin Vale for closing remarks.",
        "I'll hand the call over to Robin Vale, Chief Executive Officer. Please go ahead.",
    ],
)
def test_queue_closing_and_return_segments_are_never_separators(text: str) -> None:
    segments = _call(
        _seg("Operator", "Operator", text),
        _seg("CEO", "Robin Vale", "Thank you everyone."),
    )
    assert si.structural_separators(segments) == []


def test_a_handoff_with_no_following_source_turn_is_not_a_separator() -> None:
    segments = _call(
        _seg("Operator", "Operator", "Our next question comes from Dana Reyes."),
        _seg("Operator", "Operator", "That concludes today's call."),
    )
    assert si.structural_separators(segments) == []


# --------------------------------------------------------------------------- questioner


def test_exact_name_match_is_a_direct_questioner() -> None:
    segments = _call(
        _seg("Operator", "Operator", "Our next question comes from Dana Reyes with North Peak."),
        _seg("", "Dana Reyes", "Thanks for taking my question."),
        _seg("CEO", "Robin Vale", "Sure."),
    )
    assert si.resolve_questioner(segments, 0)["state"] == "direct"


@pytest.mark.parametrize("binding", ["on for", "sitting in for", "filling in for"])
def test_full_name_stand_in_stating_their_own_name_is_an_explicit_proxy(binding: str) -> None:
    segments = _call(
        _seg("Operator", "Operator", "Our next question comes from Dana Reyes with North Peak."),
        _seg("", "Sam Okafor", f"Hi, this is Sam Okafor {binding} Dana. One question."),
        _seg("CEO", "Robin Vale", "Sure."),
    )
    resolved = si.resolve_questioner(segments, 0)
    assert resolved["state"] == "proxy"
    assert resolved["name"] == "Sam Okafor"


@pytest.mark.parametrize(
    ("speaker", "utterance"),
    [
        # First-name-only stand-in behind a placeholder speaker.
        ("Speaker 4", "Hi. This is Sam on for Dana. Can you hear me?"),
        # Placeholder speaker with no self-identification at all.
        ("Speaker 7", "Good morning, thanks for taking the question."),
        # Full name that simply does not match and claims no stand-in role.
        ("Dale Rogers", "Hey, it's Dale. One on margins."),
        # Near-miss surname typo must never be repaired.
        ("Dana Reyez", "Thanks for taking my question."),
    ],
)
def test_unsupported_questioner_identity_stays_unresolved(speaker: str, utterance: str) -> None:
    segments = _call(
        _seg("Operator", "Operator", "Our next question comes from Dana Reyes with North Peak."),
        _seg("", speaker, utterance),
        _seg("CEO", "Robin Vale", "Sure."),
    )
    assert si.resolve_questioner(segments, 0)["state"] == "unresolved"
    # The separator itself survives, so window geometry is never corrupted.
    assert si.structural_separators(segments) == [0]


def test_a_stand_in_may_not_inherit_the_principals_identity() -> None:
    segments = _call(
        _seg("Operator", "Operator", "Our next question comes from Dana Reyes with North Peak."),
        _seg("", "Sam Okafor", "Hi, this is Sam Okafor on for Dana."),
        _seg("CEO", "Robin Vale", "Sure."),
    )
    resolved = si.resolve_questioner(segments, 0)
    assert resolved["name"] == "Sam Okafor"
    assert resolved["name"] != resolved["operator_named"]


# --------------------------------------------------------------------------- roles


def test_name_first_and_title_first_rosters_bind_identically() -> None:
    name_first = _call(
        _seg("IR", "Avery Lin", "With us today are Robin Vale, our CEO, and Jess Park, our CFO."),
        _seg("", "Robin Vale", "Good morning."),
        _seg("", "Jess Park", "Good morning."),
    )
    title_first = _call(
        _seg("IR", "Avery Lin", "I'm joined by our CEO, Robin Vale, and our CFO, Jess Park."),
        _seg("", "Robin Vale", "Good morning."),
        _seg("", "Jess Park", "Good morning."),
    )
    for segments in (name_first, title_first):
        roster = si.roster(segments)
        assert roster[si.norm_person("Robin Vale")]["role"] == "CEO"
        assert roster[si.norm_person("Jess Park")]["role"] == "CFO"


def test_titles_do_not_bleed_across_people_in_a_multi_person_roster() -> None:
    segments = _call(
        _seg(
            "IR",
            "Avery Lin",
            "On the call are Dale Rogers, President and Chief Executive Officer, "
            "Jess Park, Chief Financial Officer, and Sam Okafor, Chief Investment Officer.",
        ),
        _seg("", "Jess Park", "Good morning."),
        _seg("", "Sam Okafor", "Good morning."),
    )
    roster = si.roster(segments)
    assert roster[si.norm_person("Jess Park")]["role"] == "CFO"
    assert roster[si.norm_person("Sam Okafor")]["declared_titles"] == [
        "chief investment officer"
    ]


def test_a_non_speaking_declared_participant_still_terminates_the_clause() -> None:
    """Dale never speaks, so he binds nothing — but he must still stop Jess's clause."""
    segments = _call(
        _seg(
            "IR",
            "Avery Lin",
            "On the call are Dale Rogers, Chief Executive Officer, Jess Park, "
            "Chief Financial Officer.",
        ),
        _seg("", "Jess Park", "Good morning."),
    )
    roster = si.roster(segments)
    assert si.norm_person("Dale Rogers") not in roster
    assert roster[si.norm_person("Jess Park")]["role"] == "CFO"


def test_declared_name_binds_a_speaker_only_as_an_exact_contiguous_alias() -> None:
    bound = _call(
        _seg("IR", "Avery Lin", "With us is Jess Park, our Chief Financial Officer."),
        _seg("", "Jess Park Ndiaye", "Good morning."),
    )
    assert si.roster(bound)[si.norm_person("Jess Park Ndiaye")]["role"] == "CFO"

    unbound = _call(
        _seg("IR", "Avery Lin", "With us is Dave Sedgwick, our Chief Financial Officer."),
        _seg("", "David Sedgwick", "Good morning."),
    )
    assert si.roster(unbound) == {}


def test_an_alias_claimed_by_two_speakers_binds_nobody() -> None:
    """One declaration may never role two different people."""
    segments = _call(
        _seg("IR", "Avery Lin", "With us is Jordan Lee, our Chief Financial Officer."),
        _seg("", "Jordan Lee", "Good morning."),
        _seg("", "Jordan Lee Smith", "Good morning."),
    )
    assert si.roster(segments) == {}

    unambiguous = _call(
        _seg("IR", "Avery Lin", "With us is Jordan Lee, our Chief Financial Officer."),
        _seg("", "Jordan Lee", "Good morning."),
    )
    assert unambiguous and si.roster(unambiguous)[si.norm_person("Jordan Lee")]["role"] == "CFO"


def test_a_stand_in_naming_a_third_party_is_not_a_proxy() -> None:
    segments = _call(
        _seg("Operator", "Operator", "Our next question comes from Dana Reyes with North Peak."),
        _seg("", "Sam Okafor", "Hi, this is Lee Jordan on for Dana."),
        _seg("CEO", "Robin Vale", "Sure."),
    )
    assert si.resolve_questioner(segments, 0)["state"] == "unresolved"


def test_a_speaker_may_declare_their_own_role_but_mere_mention_never_binds() -> None:
    declares = _call(_seg("", "Jess Park", "I will be stepping down as CFO this quarter."))
    assert si.roster(declares)[si.norm_person("Jess Park")]["role"] == "CFO"

    mentions = _call(_seg("", "Jess Park", "I want to thank our CFO for the handover."))
    assert si.roster(mentions) == {}


def test_cio_is_not_an_alias_for_any_closed_officer_role() -> None:
    assert si.canonical_role("Chief Investment Officer") != "CFO"
    assert si.canonical_role("Chief Investment Officer") not in {"CEO", "CFO", "COO"}
    assert si.canonical_role("Chief Executive Officer") == "CEO"
    assert si.canonical_role("Chief Financial Officer") == "CFO"
    assert si.canonical_role("Chief Operating Officer") == "COO"


def test_segment_role_contradicting_a_declared_title_is_a_conflict() -> None:
    segments = _call(
        _seg("IR", "Avery Lin", "With us is Jess Park, our Chief Investment Officer."),
        _seg("CFO", "Jess Park", "Good morning."),
    )
    conflicts = si.role_conflict(segments)
    assert [c["speaker"] for c in conflicts] == ["Jess Park"]


def test_a_segment_role_among_several_declared_titles_is_not_a_conflict() -> None:
    segments = _call(
        _seg("IR", "Avery Lin", "With us is Robin Vale, our President and Chief Executive Officer."),
        _seg("CEO", "Robin Vale", "Good morning."),
    )
    assert si.role_conflict(segments) == []


# --------------------------------------------------------------------------- pathology


@pytest.mark.parametrize(
    "segments",
    [
        [],
        [{"role": "Operator", "speaker": "Operator"}],
        [{"role": None, "speaker": None, "text": None}],
        [_seg("Operator", "Operator", "Our next question comes from Dana Reyes." * 400)],
    ],
)
def test_malformed_or_oversized_input_never_raises(segments: list[dict[str, object]]) -> None:
    si.structural_separators(segments)
    si.roster(segments)
    si.role_conflict(segments)


def test_module_carries_no_issuer_or_boundary_literal() -> None:
    import pathlib
    import re

    source = pathlib.Path(si.__file__).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith("#")
    )
    for ticker in ("AAPL", "GOOGL", "MBLY", "ARRY", "KREF", "SCCO", "COF", "FANG"):
        assert not re.search(rf"\b{ticker}\b", body)
    assert "Apple" not in body and "Alphabet" not in body
