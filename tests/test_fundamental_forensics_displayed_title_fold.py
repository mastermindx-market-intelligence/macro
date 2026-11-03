"""Second-pass case/dash/quote fold for a single displayed-statement title."""
from __future__ import annotations

import pytest

from engine.fundamental_forensics import statement_graph
from engine.fundamental_forensics.statement_graph import (
    StatementGraphError,
    parse_displayed_primary_table,
)


def _statement_table(
    title_row: str,
    *,
    label: str = "Net income",
    ids: tuple[str, str] = ("ttl-ni-2025", "ttl-ni-2024"),
) -> str:
    """Smallest table parse_displayed_primary_table accepts (lane C shape)."""
    return f"""
    <table>
    <tr>{title_row}</tr>
    <tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>
    <tr>
      <td>{label}</td>
      <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2025" id="{ids[0]}" unitRef="usd" decimals="-6" scale="6">100</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="d2024" id="{ids[1]}" unitRef="usd" decimals="-6" scale="6">90</ix:nonFraction></td>
    </tr>
    </table>
    """


def _rows(parsed: dict) -> list[dict]:
    return [
        {
            "label": row["label"],
            "facts": [str(item.get("fact_id") or "") for item in row["value_facts"]],
        }
        for row in parsed["rows"]
    ]


def _counting_title_fold(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Patch statement_graph._title_fold with a call-counting wrapper."""
    calls = {"n": 0}
    real = statement_graph._title_fold

    def counting(text: str) -> str:
        calls["n"] += 1
        return real(text)

    monkeypatch.setattr(statement_graph, "_title_fold", counting)
    return calls


def test_ttl1_case_differing_title_found() -> None:
    html = _statement_table("<td>Consolidated Statements of Operations</td>")
    folded_search = parse_displayed_primary_table(
        html, title="CONSOLIDATED STATEMENTS OF OPERATIONS"
    )
    printed_search = parse_displayed_primary_table(
        html, title="Consolidated Statements of Operations"
    )
    assert folded_search["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert _rows(folded_search) == _rows(printed_search)
    assert _rows(folded_search) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


def test_ttl1_dash_and_quote_variants_fold() -> None:
    html = _statement_table("<td>Statements of Cash Flows – Parent Company</td>")
    parsed = parse_displayed_primary_table(
        html, title="STATEMENTS OF CASH FLOWS - PARENT COMPANY"
    )
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert [row["label"] for row in parsed["rows"]] == ["Net income"]

    html = _statement_table("<td>Consolidated Statements of Shareholders’ Equity</td>")
    parsed = parse_displayed_primary_table(
        html, title="CONSOLIDATED STATEMENTS OF SHAREHOLDERS' EQUITY"
    )
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert [row["label"] for row in parsed["rows"]] == ["Net income"]


def test_ttl1_exact_match_wins_without_pass_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _counting_title_fold(monkeypatch)
    title = "CONSOLIDATED STATEMENTS OF OPERATIONS"
    html = _statement_table(
        "<td>Consolidated Statements of Operations</td>",
        label="Decoy net income",
        ids=("ttl-decoy-2025", "ttl-decoy-2024"),
    ) + _statement_table(f"<td>{title}</td>")
    parsed = parse_displayed_primary_table(html, title=title)
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]
    assert calls["n"] == 0


def test_ttl1_list_mode_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _counting_title_fold(monkeypatch)
    html = _statement_table("<td>Consolidated Statements of Operations</td>")
    parsed = parse_displayed_primary_table(
        html,
        title=["STATEMENTS OF INCOME", "CONSOLIDATED STATEMENTS OF OPERATIONS"],
    )
    control = parse_displayed_primary_table(
        html,
        title=["STATEMENTS OF INCOME", "Consolidated Statements of Operations"],
    )
    assert parsed["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert _rows(parsed) == _rows(control)
    assert calls["n"] == 0


def test_ttl1_absent_title_message_and_code_unchanged() -> None:
    html = _statement_table("<td>Consolidated Statements of Operations</td>")
    search = "CONSOLIDATED BALANCE SHEETS"
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=search)
    assert excinfo.value.refusal_code == "displayed_table_absent"
    assert str(excinfo.value) == f"displayed statement table is absent: {search}"


def test_ttl1_no_fuzzy_match() -> None:
    html = _statement_table("<td>Consolidated Statements of Operations</td>")
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(
            html, title="CONSOLIDATED STATEMENT OF OPERATIONS"
        )
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1_discard_rearm_parity_under_fold() -> None:
    printed = "Consolidated Statements of Operations"
    html = (
        "<p>Management reviews the consolidated statements of operations "
        "with the chief accountant each quarter.</p>"
        "<table><tr><td>Item 8 index</td><td>Page 57</td></tr></table>"
        + _statement_table(f"<td>{printed}</td>")
    )
    folded = parse_displayed_primary_table(
        html, title="CONSOLIDATED STATEMENTS OF OPERATIONS"
    )
    exact = parse_displayed_primary_table(html, title=printed)
    assert folded["columns_iso"] == ["2025-09-27", "2024-09-28"]
    assert _rows(folded) == _rows(exact)
    assert _rows(folded) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


def test_ttl1_fold_function() -> None:
    folded = statement_graph._title_fold(
        "  Consolidated Statements – of  Shareholders’ Equity "
    )
    assert folded == "consolidated statements-of shareholders' equity"
    assert statement_graph._title_fold(folded) == folded


def test_ttl1_fold_narrative_mention_never_arms() -> None:
    """An auditor's sentence naming the statement must not arm the fold pass:
    the fact table after it is not the statement."""
    html = (
        "<p>We have audited the accompanying consolidated statements of "
        "operations of the Company for each of the two years.</p>"
        + _statement_table(
            "<td>Critical audit matters</td>",
            label="Audit fee",
            ids=("ttl-fee-2025", "ttl-fee-2024"),
        )
        + _statement_table("<td>Consolidated Statements of Operations</td>")
    )
    folded = parse_displayed_primary_table(
        html, title="CONSOLIDATED STATEMENTS OF OPERATIONS"
    )
    assert _rows(folded) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


@pytest.mark.parametrize(
    "printed",
    [
        "CONSOLIDATED CASH FLOW STATEMENTS",
        "CONSOLIDATED CASH FLOW STATEMENT (In thousands, except share data)",
        "Consolidated Cash Flow Statements (Unaudited) (In millions)",
    ],
)
def test_ttl1_fold_plural_and_parenthesised_qualifiers_arm(printed: str) -> None:
    html = _statement_table(f"<td>{printed}</td>")
    parsed = parse_displayed_primary_table(
        html, title="Consolidated Cash Flow Statement"
    )
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


@pytest.mark.parametrize(
    "printed",
    [
        "CONSOLIDATED CASH FLOW STATEMENT (IN MILLIONS) FOR THE YEARS PRESENTED",
        "Notes to the consolidated cash flow statement",
        "Consolidated cash flow statement data",
    ],
)
def test_ttl1_fold_trailing_or_leading_words_do_not_arm(printed: str) -> None:
    html = _statement_table(f"<td>{printed}</td>")
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title="Consolidated Cash Flow Statement")
    assert excinfo.value.refusal_code == "displayed_table_absent"


@pytest.mark.parametrize(
    "printed",
    [
        "CONSOLIDATED CASH FLOW STATEMENT (LOSS)",
        "CONSOLIDATED CASH FLOW STATEMENTS (1)",
        "Consolidated Cash Flow Statement (Loss) (unaudited)",
    ],
)
def test_ttl1a2_allowlisted_qualifiers_arm(printed: str) -> None:
    html = _statement_table(f"<td>{printed}</td>")
    parsed = parse_displayed_primary_table(
        html, title="Consolidated Cash Flow Statement"
    )
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


_ENTITY_QUALIFIERS = [
    "(Parent Company Only)",
    "(Guarantor Subsidiaries)",
    "(Predecessor)",
    "(Bank Only)",
    "(Registrant)",
    "(Continued)",
]


@pytest.mark.parametrize("qualifier", _ENTITY_QUALIFIERS)
def test_ttl1a2_entity_or_continuation_qualifier_does_not_arm(qualifier: str) -> None:
    html = _statement_table(f"<td>CONSOLIDATED CASH FLOW STATEMENTS {qualifier}</td>")
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title="Consolidated Cash Flow Statement")
    assert excinfo.value.refusal_code == "displayed_table_absent"


@pytest.mark.parametrize("qualifier", _ENTITY_QUALIFIERS)
def test_ttl1a2_entity_table_never_chosen_over_later_statement(qualifier: str) -> None:
    """A registrant-only table printed before the consolidated statement must
    not be served for it: the fold pass skips it and finds the real table."""
    html = _statement_table(
        f"<td>CONSOLIDATED CASH FLOW STATEMENTS {qualifier}</td>",
        label="Parent net income",
        ids=("ttl-pco-2025", "ttl-pco-2024"),
    ) + _statement_table("<td>CONSOLIDATED CASH FLOW STATEMENTS</td>")
    parsed = parse_displayed_primary_table(html, title="Consolidated Cash Flow Statement")
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


_TOC = (
    "<table><tr><td>CONSOLIDATED STATEMENTS OF OPERATIONS</td></tr>"
    "<tr><td>Page</td><td>57</td></tr></table>"
)


def test_ttl1a2_fold_discard_then_exact_fold_rearm() -> None:
    """A factless table armed by the folded title is discarded; a later
    narrative mention does not re-arm, and the title row of the real
    statement does."""
    html = (
        _TOC
        + "<p>Management reviews the consolidated statements of operations "
        "with the chief accountant each quarter.</p>"
        + _statement_table(
            "<td>Critical audit matters</td>",
            label="Audit fee",
            ids=("ttl-fee-2025", "ttl-fee-2024"),
        )
        + _statement_table("<td>CONSOLIDATED STATEMENTS OF OPERATIONS</td>")
    )
    parsed = parse_displayed_primary_table(
        html, title="Consolidated Statements of Operations"
    )
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


def test_ttl1a4_qualifier_variant_rearms_after_discard() -> None:
    """Amendment A4: after a discard the fold pass re-arms on the same whole
    text rule as a first capture, so an allowlisted qualifier variant re-arms
    and the first table it names is served."""
    html = (
        _TOC
        + _statement_table(
            "<td>CONSOLIDATED STATEMENTS OF OPERATIONS (Unaudited)</td>",
            label="Interim net income",
            ids=("ttl-int-2025", "ttl-int-2024"),
        )
        + _statement_table("<td>CONSOLIDATED STATEMENTS OF OPERATIONS</td>")
    )
    parsed = parse_displayed_primary_table(
        html, title="Consolidated Statements of Operations"
    )
    assert _rows(parsed) == [
        {"label": "Interim net income", "facts": ["ttl-int-2025", "ttl-int-2024"]}
    ]


@pytest.mark.parametrize(
    ("suffix", "arms"),
    [
        ("", True),
        ("s", True),
        (" (unaudited)", True),
        ("s(unaudited)", True),
        (" (loss)", True),
        (" (loss) (unaudited)", True),
        (" (1)", True),
        ("s (in thousands, except share data)", True),
        (" (in millions, except per share amounts) (unaudited)", True),
        (" (dollars in millions)", True),
        (" (parent company only)", False),
        (" (guarantor subsidiaries)", False),
        (" (predecessor)", False),
        (" (successor)", False),
        (" (continued)", False),
        (" (123)", False),
        (" (unaudited", False),
        (" ((unaudited))", False),
        (" (in millions) for the years presented", False),
        ("es", False),
    ],
)
def test_ttl1a2_qualifier_grammar(suffix: str, arms: bool) -> None:
    assert bool(statement_graph._TITLE_FOLD_QUALIFIER_RE.match(suffix)) is arms


# Amendment A3: a qualifier printed in a node next to the folded title is
# invisible to the title match, so the fold pass keeps a captured table only
# when most of its value facts sit in undimensioned contexts.  Amendment A4
# passes each context's dimension signature instead of a bare id list, and
# also keeps an entity-grouped face (``_capture_is_consolidated``).

_PLAIN = ("d2025", "d2024")
_PARENT = ("p2025", "p2024")
_PARENT_MEMBER = frozenset({("dei:LegalEntityAxis", "x:ParentMember")})
_DIMS = {
    "d2025": frozenset(),
    "d2024": frozenset(),
    "p2025": _PARENT_MEMBER,
    "p2024": _PARENT_MEMBER,
    "seg2025": frozenset({("srt:ProductOrServiceAxis", "us-gaap:ProductMember")}),
    "seg2024": frozenset({("srt:ProductOrServiceAxis", "us-gaap:ProductMember")}),
    "g2025": frozenset({("srt:ConsolidationItemsAxis", "x:GuarantorMember")}),
    "g2024": frozenset({("srt:ConsolidationItemsAxis", "x:GuarantorMember")}),
}


def _context_table(
    title_row: str,
    rows: list[tuple[str, tuple[str, str], tuple[str, str]]],
) -> str:
    """A lane-C table whose value rows carry explicit (label, contexts, ids)."""
    body = "".join(
        f"""
    <tr>
      <td>{label}</td>
      <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="{refs[0]}" id="{ids[0]}" unitRef="usd" decimals="-6" scale="6">100</ix:nonFraction></td>
      <td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="{refs[1]}" id="{ids[1]}" unitRef="usd" decimals="-6" scale="6">90</ix:nonFraction></td>
    </tr>"""
        for label, refs, ids in rows
    )
    return f"""
    <table>
    <tr>{title_row}</tr>
    <tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>{body}
    </table>
    """


_PARENT_ROWS = [("Parent net income", _PARENT, ("ttl-pco-2025", "ttl-pco-2024"))]
_CONSOLIDATED_ROWS = [("Net income", _PLAIN, ("ttl-ni-2025", "ttl-ni-2024"))]
_REAL_TABLE = _context_table(
    "<td>Consolidated Statements of Cash Flows</td>", _CONSOLIDATED_ROWS
)

# Each layout prints the entity qualifier outside the node the title arms on.
_NEIGHBOUR_QUALIFIED = {
    "paragraph_after_title": (
        "<p>Consolidated Statements of Cash Flows</p><p>(Parent Company Only)</p>"
        + _context_table("<td></td>", _PARENT_ROWS)
    ),
    "plain_node_after_bold_title": (
        "<p><b>Consolidated Statements of Cash Flows</b> (Parent Company Only)</p>"
        + _context_table("<td></td>", _PARENT_ROWS)
    ),
    "qualifier_row_after_title_row": _context_table(
        "<td>Consolidated Statements of Cash Flows</td></tr>"
        "<tr><td>(Parent Company Only)</td>",
        _PARENT_ROWS,
    ),
    "heading_before_title": (
        "<p>PARENT COMPANY ONLY</p>"
        + _context_table("<td>Consolidated Statements of Cash Flows</td>", _PARENT_ROWS)
    ),
}


@pytest.mark.parametrize("layout", sorted(_NEIGHBOUR_QUALIFIED))
def test_ttl1a3_neighbour_qualified_entity_table_refuses(layout: str) -> None:
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(
            _NEIGHBOUR_QUALIFIED[layout],
            title="CONSOLIDATED STATEMENTS OF CASH FLOWS",
            context_dimensions=_DIMS,
        )
    assert excinfo.value.refusal_code == "displayed_table_absent"


@pytest.mark.parametrize("layout", sorted(_NEIGHBOUR_QUALIFIED))
def test_ttl1a3_neighbour_qualified_entity_table_skipped_for_real_one(layout: str) -> None:
    parsed = parse_displayed_primary_table(
        _NEIGHBOUR_QUALIFIED[layout] + _REAL_TABLE,
        title="CONSOLIDATED STATEMENTS OF CASH FLOWS",
        context_dimensions=_DIMS,
    )
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


def test_ttl1a3_minority_dimensioned_rows_still_serve() -> None:
    """A consolidated statement may disaggregate a line on an axis (products
    and services); a minority of dimensioned facts keeps the table."""
    html = _context_table(
        "<td>Consolidated Statements of Operations</td>",
        [
            ("Products", ("seg2025", "seg2024"), ("ttl-pr-2025", "ttl-pr-2024")),
            ("Total net sales", _PLAIN, ("ttl-ns-2025", "ttl-ns-2024")),
            ("Net income", _PLAIN, ("ttl-ni-2025", "ttl-ni-2024")),
        ],
    )
    parsed = parse_displayed_primary_table(
        html,
        title="CONSOLIDATED STATEMENTS OF OPERATIONS",
        context_dimensions=_DIMS,
    )
    assert [row["label"] for row in parsed["rows"]] == [
        "Products",
        "Total net sales",
        "Net income",
    ]


def test_ttl1a3_half_dimensioned_table_refuses() -> None:
    html = _context_table(
        "<td>Consolidated Statements of Operations</td>",
        [
            ("Guarantor net income", ("g2025", "g2024"), ("ttl-g-2025", "ttl-g-2024")),
            ("Net income", _PLAIN, ("ttl-ni-2025", "ttl-ni-2024")),
        ],
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(
            html,
            title="CONSOLIDATED STATEMENTS OF OPERATIONS",
            context_dimensions=_DIMS,
        )
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a3_exact_pass_does_not_consult_contexts() -> None:
    """The context check belongs to the fold pass only; an exact title match
    is unchanged (its own containment rule is a separate, pre-existing case)."""
    html = _context_table(
        "<td>Consolidated Statements of Cash Flows</td>", _PARENT_ROWS
    )
    parsed = parse_displayed_primary_table(
        html,
        title="Consolidated Statements of Cash Flows",
        context_dimensions=_DIMS,
    )
    assert _rows(parsed) == [
        {"label": "Parent net income", "facts": ["ttl-pco-2025", "ttl-pco-2024"]}
    ]


def test_ttl1a3_without_contexts_the_fold_keeps_a2_selection() -> None:
    """A caller that supplies no contexts (reconstruct_statement always does)
    keeps the A2 behaviour, which cannot see a neighbouring qualifier."""
    parsed = parse_displayed_primary_table(
        _NEIGHBOUR_QUALIFIED["paragraph_after_title"],
        title="CONSOLIDATED STATEMENTS OF CASH FLOWS",
    )
    assert _rows(parsed) == [
        {"label": "Parent net income", "facts": ["ttl-pco-2025", "ttl-pco-2024"]}
    ]


@pytest.mark.parametrize(
    ("suffix", "arms"),
    [
        (" (in millions, except parent company only)", False),
        (" (in thousands, except guarantor subsidiaries)", False),
        (" (in millions, except per share data)", True),
        (" (in millions, except share and per share amounts)", True),
        (" (in thousands, except shares, per share and par value data)", True),
        (" (in millions, except ratios and percentages)", True),
        (" (dollars in millions, except per-share data)", True),
        (" (in millions of dollars)", True),
        (" (00)", False),
        (" (05)", False),
        (" (١)", False),
        (" (99)", True),
    ],
)
def test_ttl1a3_qualifier_grammar(suffix: str, arms: bool) -> None:
    assert bool(statement_graph._TITLE_FOLD_QUALIFIER_RE.match(suffix)) is arms


def test_ttl1a3_plural_s_never_follows_a_title_ending_in_s() -> None:
    assert statement_graph._title_fold_suffix_arms("consolidated statement of cash flow", "s")
    assert not statement_graph._title_fold_suffix_arms(
        "consolidated statements of cash flows", "s"
    )
    html = _statement_table("<td>CONSOLIDATED STATEMENTS OF CASH FLOWSS</td>")
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title="Consolidated Statements of Cash Flows")
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a4_reconstruct_statement_passes_context_dimensions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """reconstruct_statement hands the parser every filing context's
    dimension signature, empty for an undimensioned context."""
    seen: dict[str, object] = {}

    def fake_parse(html: str, *, title, context_dimensions=None):
        seen["contexts"] = dict(context_dimensions)
        raise StatementGraphError("stop", refusal_code="displayed_table_absent")

    monkeypatch.setattr(statement_graph, "parse_displayed_primary_table", fake_parse)
    monkeypatch.setattr(
        statement_graph,
        "_statement_identity",
        lambda package, statement_type: ("role", "Cash flow", "Cash flow"),
    )
    monkeypatch.setattr(statement_graph, "_stored_member", lambda package, name: b"")
    monkeypatch.setattr(statement_graph, "parse_presentation_tree", lambda pre, role_uri: {})
    monkeypatch.setattr(statement_graph, "_presentation_occurrences", lambda tree: {})
    monkeypatch.setattr(statement_graph, "parse_labels", lambda lab: {})
    monkeypatch.setattr(statement_graph, "parse_calculations", lambda cal: {})

    class _Package:
        manifest = {
            "primary_document": "doc.htm",
            "members": [{"name": "doc.htm", "state": "stored", "content_sha256": "0" * 64}],
        }
        members = {"doc.htm": b"<html></html>"}

    parsed_instance = {
        "facts": [],
        "units": [],
        "contexts": [
            {"context_id": "d2025", "dimensions": []},
            {"context_id": "d2024", "dimensions": []},
            {
                "context_id": "p2025",
                "dimensions": [
                    {
                        "dimension_qname": "dei:LegalEntityAxis",
                        "member_qname": "x:ParentMember",
                        "typed_value_xml": None,
                    }
                ],
            },
        ],
    }
    with pytest.raises(StatementGraphError):
        statement_graph.reconstruct_statement(
            statement_type="cash_flow",
            package=_Package(),
            parsed_instance=parsed_instance,
            registry=None,
        )
    assert seen["contexts"] == {
        "d2025": frozenset(),
        "d2024": frozenset(),
        "p2025": frozenset({("dei:LegalEntityAxis", "x:ParentMember")}),
    }


# Amendment A4: the unit-caption grammar reads six more printed captions, a
# continuation marker before any captured fact drops a fold capture, and an
# entity-grouped consolidated face (one legal-entity axis, two or more
# members, undimensioned totals) is kept.

_ENTITY_AXIS = "dei:LegalEntityAxis"
_ENTITY_DIMS = {
    **_DIMS,
    "m2025": frozenset({(_ENTITY_AXIS, "x:ManufacturingGroupMember")}),
    "m2024": frozenset({(_ENTITY_AXIS, "x:ManufacturingGroupMember")}),
    "f2025": frozenset({(_ENTITY_AXIS, "x:FinanceGroupMember")}),
    "f2024": frozenset({(_ENTITY_AXIS, "x:FinanceGroupMember")}),
    "s2025": frozenset({(_ENTITY_AXIS, "x:SubsidiaryMember")}),
    "s2024": frozenset({(_ENTITY_AXIS, "x:SubsidiaryMember")}),
    "two2025": frozenset(
        {(_ENTITY_AXIS, "x:FinanceGroupMember"), ("srt:ProductOrServiceAxis", "us-gaap:ProductMember")}
    ),
    "two2024": frozenset(
        {(_ENTITY_AXIS, "x:FinanceGroupMember"), ("srt:ProductOrServiceAxis", "us-gaap:ProductMember")}
    ),
}
_MFG = ("m2025", "m2024")
_FIN = ("f2025", "f2024")
_SUB = ("s2025", "s2024")
_BALANCE_TITLE = "CONSOLIDATED BALANCE SHEETS"


@pytest.mark.parametrize(
    ("suffix", "arms"),
    [
        (" (in thousands, except share amounts and per share data)", True),
        (" (in millions, except for per share data)", True),
        (" (in millions, except earnings per share)", True),
        (" (in millions, except per share data, unaudited)", True),
        (" (in thousands, except stated value)", True),
        (" (in millions, except per share amounts and shares in thousands)", True),
        (" (in millions, except parent company only)", False),
        (" (in millions, except for guarantor subsidiaries)", False),
        (" (in millions, except shares in billions)", False),
        (" (in millions, except per share data, audited)", False),
    ],
)
def test_ttl1a4_qualifier_grammar(suffix: str, arms: bool) -> None:
    assert bool(statement_graph._TITLE_FOLD_QUALIFIER_RE.match(suffix)) is arms


@pytest.mark.parametrize(
    "caption",
    [
        "(in thousands, except share amounts and per share data)",
        "(in millions, except for per share data)",
        "(in millions, except earnings per share)",
        "(in millions, except per share data, unaudited)",
        "(in thousands, except stated value)",
        "(in millions, except per share amounts and shares in thousands)",
    ],
)
def test_ttl1a4_captioned_first_part_serves_before_continued_part(caption: str) -> None:
    """The A3 review case: a first part whose caption A3 could not read let a
    later continued part arm alone.  The caption now arms the first part."""
    html = (
        f"<p>Consolidated Balance Sheets {caption}</p>"
        + _statement_table("<td></td>", label="Total assets", ids=("ttl-ta-2025", "ttl-ta-2024"))
        + "<p>Consolidated Balance Sheets</p><p>(Continued)</p>"
        + _statement_table("<td></td>", label="Total equity", ids=("ttl-te-2025", "ttl-te-2024"))
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert _rows(parsed) == [
        {"label": "Total assets", "facts": ["ttl-ta-2025", "ttl-ta-2024"]}
    ]


_CONTINUED_LAYOUTS = {
    "paragraph_after_title": "<p>Consolidated Balance Sheets</p><p>(Continued)</p>"
    + _statement_table("<td></td>"),
    "span_in_title_node": "<p><span>Consolidated Balance Sheets</span> <span>(Continued)</span></p>"
    + _statement_table("<td></td>"),
    "row_after_title_row": _statement_table(
        "<td>Consolidated Balance Sheets</td></tr><tr><td>(Continued)</td>"
    ),
    "dash_marker_after_title_paragraph": "<p>Consolidated Balance Sheets</p><p>- continued</p>"
    + _statement_table("<td></td>"),
    "title_and_marker_in_one_cell": _statement_table(
        "<td>Consolidated Balance Sheets - Continued</td>"
    ),
}


@pytest.mark.parametrize("layout", sorted(_CONTINUED_LAYOUTS))
def test_ttl1a4_continued_part_never_arms_alone(layout: str) -> None:
    """A part 1 the fold cannot read (an entity caption) is skipped, and the
    continued part 2 is never served as the whole statement."""
    html = (
        "<p>Consolidated Balance Sheets (in millions, except parent company only)</p>"
        + _statement_table("<td></td>", label="Total assets", ids=("ttl-ta-2025", "ttl-ta-2024"))
        + _CONTINUED_LAYOUTS[layout]
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert excinfo.value.refusal_code == "displayed_table_absent"


@pytest.mark.parametrize("layout", sorted(_CONTINUED_LAYOUTS))
def test_ttl1a4_continued_part_discard_rearms_on_a_later_title(layout: str) -> None:
    html = _CONTINUED_LAYOUTS[layout] + _statement_table(
        "<td>Consolidated Balance Sheets</td>",
        label="Total liabilities",
        ids=("ttl-tl-2025", "ttl-tl-2024"),
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert _rows(parsed) == [
        {"label": "Total liabilities", "facts": ["ttl-tl-2025", "ttl-tl-2024"]}
    ]


def test_ttl1a4_marker_after_captured_facts_changes_nothing() -> None:
    html = _statement_table("<td>Consolidated Balance Sheets</td>").replace(
        "</table>",
        "<tr><td>(Continued)</td></tr>"
        '<tr><td>Total equity</td><td><ix:nonFraction name="us-gaap:StockholdersEquity" '
        'contextRef="d2025" id="ttl-te-2025" unitRef="usd" decimals="-6" scale="6">5'
        "</ix:nonFraction></td><td>"
        '<ix:nonFraction name="us-gaap:StockholdersEquity" contextRef="d2024" '
        'id="ttl-te-2024" unitRef="usd" decimals="-6" scale="6">4</ix:nonFraction></td></tr>'
        "</table>",
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    facts = [fact for row in _rows(parsed) for fact in row["facts"] if fact]
    assert facts == ["ttl-ni-2025", "ttl-ni-2024", "ttl-te-2025", "ttl-te-2024"]


def test_ttl1a4_exact_pass_ignores_continuation_markers() -> None:
    """The continuation guard belongs to the fold pass; an exact title match
    keeps its pre-existing behaviour."""
    html = "<p>Consolidated Balance Sheets</p><p>(Continued)</p>" + _statement_table("<td></td>")
    parsed = parse_displayed_primary_table(html, title="Consolidated Balance Sheets")
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


@pytest.mark.parametrize(
    ("text", "continued"),
    [
        ("(Continued)", True),
        ("Continued", True),
        ("- continued", True),
        (", continued:", True),
        ("(in millions) (continued)", True),
        ("CONSOLIDATED BALANCE SHEETS - CONTINUED", True),
        ("Consolidated Balance Sheets (Continued).", True),
        ("Discontinued operations", False),
        ("discontinued", False),
        ("continued operations:", False),
        ("(continued on next page)", False),
        ("Consolidated Balance Sheets (Discontinued operations)", False),
        ("", False),
    ],
)
def test_ttl1a4_continuation_marker(text: str, continued: bool) -> None:
    parser = statement_graph._StatementTableParser("Consolidated Balance Sheets", fold=True)
    assert parser._continued(text) is continued


def test_ttl1a4_unit_caption_rearms_after_discard() -> None:
    """Probe 5b: a factless table of contents is discarded, then a title
    paragraph carrying an allowlisted caption re-arms the fold pass."""
    html = (
        "<table><tr><td>CONSOLIDATED BALANCE SHEETS</td></tr><tr><td>Page</td><td>57</td></tr></table>"
        "<p>Consolidated Balance Sheets (in millions, except per share data)</p>"
        + _statement_table("<td></td>", label="Total assets", ids=("ttl-ta-2025", "ttl-ta-2024"))
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert _rows(parsed) == [
        {"label": "Total assets", "facts": ["ttl-ta-2025", "ttl-ta-2024"]}
    ]


def test_ttl1a4_narrative_mention_still_never_rearms_after_discard() -> None:
    html = (
        "<table><tr><td>CONSOLIDATED BALANCE SHEETS</td></tr><tr><td>Page</td><td>57</td></tr></table>"
        "<p>We have audited the accompanying consolidated balance sheets.</p>"
        + _statement_table("<td></td>")
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert excinfo.value.refusal_code == "displayed_table_absent"


def _entity_parse(rows: list[tuple[str, tuple[str, str], tuple[str, str]]]) -> dict:
    return parse_displayed_primary_table(
        _context_table("<td>Consolidated Balance Sheets (Unaudited)</td>", rows),
        title=_BALANCE_TITLE,
        context_dimensions=_ENTITY_DIMS,
    )


def test_ttl1a4_entity_grouped_face_serves() -> None:
    """The Textron shape: manufacturing-group and finance-group lines on one
    legal-entity axis outnumber the undimensioned consolidated totals."""
    parsed = _entity_parse(
        [
            ("Manufacturing group cash", _MFG, ("ttl-mc-2025", "ttl-mc-2024")),
            ("Manufacturing group debt", _MFG, ("ttl-md-2025", "ttl-md-2024")),
            ("Finance group receivables", _FIN, ("ttl-fr-2025", "ttl-fr-2024")),
            ("Finance group debt", _FIN, ("ttl-fd-2025", "ttl-fd-2024")),
            ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
        ]
    )
    assert [row["label"] for row in parsed["rows"]] == [
        "Manufacturing group cash",
        "Manufacturing group debt",
        "Finance group receivables",
        "Finance group debt",
        "Total assets",
    ]


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param(
            [
                ("Parent net income", ("p2025", "s2024"), ("ttl-a-2025", "ttl-a-2024")),
                ("Subsidiary net income", _SUB, ("ttl-b-2025", "ttl-b-2024")),
                ("Net income", _PLAIN, ("ttl-ni-2025", "ttl-ni-2024")),
            ],
            id="consolidating_schedule_mixes_members_in_a_row",
        ),
        pytest.param(
            [
                ("Parent cash", _PARENT, ("ttl-a-2025", "ttl-a-2024")),
                ("Parent debt", _PARENT, ("ttl-b-2025", "ttl-b-2024")),
                ("Net income", _PLAIN, ("ttl-ni-2025", "ttl-ni-2024")),
            ],
            id="parent_only_with_plain_lines",
        ),
        pytest.param(
            [
                ("Manufacturing group cash", _MFG, ("ttl-a-2025", "ttl-a-2024")),
                ("Products", ("seg2025", "seg2024"), ("ttl-b-2025", "ttl-b-2024")),
                ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
            ],
            id="members_on_two_axes",
        ),
        pytest.param(
            [
                ("Manufacturing group cash", _MFG, ("ttl-a-2025", "ttl-a-2024")),
                ("Finance group product debt", ("two2025", "two2024"), ("ttl-b-2025", "ttl-b-2024")),
                ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
            ],
            id="two_axis_signature",
        ),
        pytest.param(
            [
                ("Manufacturing group cash", _MFG, ("ttl-a-2025", "ttl-a-2024")),
                ("Finance group receivables", _FIN, ("ttl-b-2025", "ttl-b-2024")),
                ("Finance group product debt", ("two2025", "two2024"), ("ttl-c-2025", "ttl-c-2024")),
                ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
            ],
            id="two_axis_signature_beside_two_members",
        ),
        pytest.param(
            [
                ("Manufacturing group cash", _MFG, ("ttl-a-2025", "ttl-a-2024")),
                ("Finance group receivables", _FIN, ("ttl-b-2025", "ttl-b-2024")),
            ],
            id="no_undimensioned_totals",
        ),
        pytest.param(
            [
                ("Manufacturing group cash", _MFG, ("ttl-a-2025", "ttl-a-2024")),
                ("Finance group receivables", _FIN, ("ttl-b-2025", "ttl-b-2024")),
                ("Unknown line", ("u2025", "u2024"), ("ttl-u-2025", "ttl-u-2024")),
                ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
            ],
            id="unknown_context_signature",
        ),
    ],
)
def test_ttl1a4_non_grouped_dimensioned_face_refuses(rows) -> None:
    with pytest.raises(StatementGraphError) as excinfo:
        _entity_parse(rows)
    assert excinfo.value.refusal_code == "displayed_table_absent"


def _notes_closed_parent_table() -> str:
    return _context_table("<td>Consolidated Balance Sheets</td>", _PARENT_ROWS).replace(
        "</table>",
        "<tr><td>See accompanying notes to the financial statements.</td></tr>"
        '<tr><td>Trailing line</td><td><ix:nonFraction name="us-gaap:NetIncomeLoss" '
        'contextRef="d2025" id="ttl-tr-2025" unitRef="usd" decimals="-6" scale="6">1'
        "</ix:nonFraction></td><td></td></tr></table>",
    )


def test_ttl1a4_notes_closed_dimensioned_capture_refuses() -> None:
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(
            _notes_closed_parent_table(), title=_BALANCE_TITLE, context_dimensions=_DIMS
        )
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a4_notes_closed_dimensioned_capture_skipped_for_real_one() -> None:
    parsed = parse_displayed_primary_table(
        _notes_closed_parent_table()
        + _context_table("<td>Consolidated Balance Sheets</td>", _CONSOLIDATED_ROWS),
        title=_BALANCE_TITLE,
        context_dimensions=_DIMS,
    )
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


def test_ttl1a4_context_dimension_sets_on_a_real_parse() -> None:
    """Explicit members key on their member qname, typed members on their
    typed value, both as the filing parser emits them."""
    from pathlib import Path

    from collectors.sec_filing_parser import parse_sec_filing_document

    fixture = Path(__file__).parent / "fixtures" / "sec_filings" / "minimal_instance.xml"
    parsed = parse_sec_filing_document(fixture.read_bytes(), document_name="minimal_instance.xml")
    contexts = {context["context_id"]: context for context in parsed["contexts"]}
    taxonomy = "{https://example.test/taxonomy}"
    assert statement_graph._context_dimension_sets(contexts) == {
        "instant": frozenset({(f"{taxonomy}RegionAxis", f"{taxonomy}NorthMember")}),
        "duration": frozenset(
            {(f"{taxonomy}ChannelAxis", "<ex:Channel>Direct</ex:Channel>")}
        ),
    }


def test_ttl1a4_context_dimension_sets_skips_malformed_contexts() -> None:
    assert statement_graph._context_dimension_sets(
        {
            "plain": {"context_id": "plain", "dimensions": []},
            "missing": {"context_id": "missing"},
            "not_a_mapping": ["dimensions"],
            "not_a_list": {"dimensions": {"dimension_qname": "a"}},
            "bad_member": {"dimensions": ["a"]},
        }
    ) == {"plain": frozenset(), "missing": frozenset()}


def _label_with_inline_fact(context_ref: str) -> str:
    return (
        "Property, plant and equipment, less accumulated depreciation of $"
        f'<ix:nonFraction name="us-gaap:AccumulatedDepreciation" contextRef="{context_ref}" '
        'id="ttl-ad-2025" unitRef="usd" decimals="-6" scale="6">4,000</ix:nonFraction>'
    )


@pytest.mark.parametrize("label_context", ["d2025", "f2025"])
def test_ttl1a4_inline_label_fact_does_not_split_a_grouped_row(label_context) -> None:
    """Textron prints the accumulated depreciation inside the manufacturing
    property label; the line builder serves only the cells after the label, so
    the row stays on its manufacturing signature."""
    parsed = _entity_parse(
        [
            (_label_with_inline_fact(label_context), _MFG, ("ttl-pp-2025", "ttl-pp-2024")),
            ("Manufacturing group cash", _MFG, ("ttl-mc-2025", "ttl-mc-2024")),
            ("Finance group receivables", _FIN, ("ttl-fr-2025", "ttl-fr-2024")),
            ("Finance group debt", _FIN, ("ttl-fd-2025", "ttl-fd-2024")),
            ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
        ]
    )
    rows = _rows(parsed)
    assert rows[0]["label"].startswith(
        "Property, plant and equipment, less accumulated depreciation of $"
    )
    assert rows[0]["facts"] == ["ttl-pp-2025", "ttl-pp-2024"]
    assert [row["label"] for row in rows[1:]] == [
        "Manufacturing group cash",
        "Finance group receivables",
        "Finance group debt",
        "Total assets",
    ]


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param(
            [
                (_label_with_inline_fact("d2025"), ("m2025", "f2024"), ("ttl-pp-2025", "ttl-pp-2024")),
                ("Finance group receivables", _FIN, ("ttl-fr-2025", "ttl-fr-2024")),
                ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
            ],
            id="value_cells_mix_members",
        ),
        pytest.param(
            [
                (_label_with_inline_fact("u2025"), _MFG, ("ttl-pp-2025", "ttl-pp-2024")),
                ("Finance group receivables", _FIN, ("ttl-fr-2025", "ttl-fr-2024")),
                ("Total assets", _PLAIN, ("ttl-ta-2025", "ttl-ta-2024")),
            ],
            id="label_fact_has_no_known_signature",
        ),
    ],
)
def test_ttl1a4_inline_label_fact_does_not_rescue_a_face(rows) -> None:
    """A label-cell fact is left out of the row check only; mixed value cells
    and an unknown label-fact context still drop the capture."""
    with pytest.raises(StatementGraphError) as excinfo:
        _entity_parse(rows)
    assert excinfo.value.refusal_code == "displayed_table_absent"


# Amendment A5: a title row whose own cells print a continuation marker never
# arms after a discard, a fold capture is judged on the grid the line builder
# reads (a rowspan label is the row's label), the continuation grammar reads
# "Cont'd", "(Cont.)" and "continued from previous page", and stray text after
# a fact cell in the row being read never drops the capture.

_ARMING_TOC = (
    "<table><tr><td>CONSOLIDATED BALANCE SHEETS</td></tr>"
    "<tr><td>Page</td><td>57</td></tr></table>"
)


def test_ttl1a5_continued_title_row_after_discard_refuses() -> None:
    """Probe M2: after a factless table of contents is discarded, a title row
    whose next cell prints "(Continued)" does not arm the later part."""
    html = _ARMING_TOC + _statement_table(
        "<td>Consolidated Balance Sheets</td><td>(Continued)</td>",
        label="Total equity",
        ids=("ttl-te-2025", "ttl-te-2024"),
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a5_continued_title_row_after_discard_skipped_for_real_one() -> None:
    html = (
        _ARMING_TOC
        + _statement_table(
            "<td>Consolidated Balance Sheets</td><td>(Continued)</td>",
            label="Total equity",
            ids=("ttl-te-2025", "ttl-te-2024"),
        )
        + _statement_table(
            "<td>Consolidated Balance Sheets</td>",
            label="Total liabilities",
            ids=("ttl-tl-2025", "ttl-tl-2024"),
        )
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert _rows(parsed) == [
        {"label": "Total liabilities", "facts": ["ttl-tl-2025", "ttl-tl-2024"]}
    ]


def _fact_cell(context_ref: str, fact_id: str) -> str:
    return (
        f'<td><ix:nonFraction name="us-gaap:NetIncomeLoss" contextRef="{context_ref}" '
        f'id="{fact_id}" unitRef="usd" decimals="-6" scale="6">100</ix:nonFraction></td>'
    )


def _rowspan_face(second_line: tuple[str, str]) -> str:
    """An entity-grouped face whose first label spans two printed lines; the
    second line prints value cells only."""
    return (
        "<table><tr><td>Consolidated Balance Sheets (Unaudited)</td></tr>"
        "<tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>"
        '<tr><td rowspan="2">Group cash</td>'
        + _fact_cell("m2025", "ttl-g1-2025")
        + _fact_cell("m2024", "ttl-g1-2024")
        + "</tr><tr>"
        + _fact_cell(second_line[0], "ttl-g2-2025")
        + _fact_cell(second_line[1], "ttl-g2-2024")
        + "</tr><tr><td>Finance group receivables</td>"
        + _fact_cell("f2025", "ttl-fr-2025")
        + _fact_cell("f2024", "ttl-fr-2024")
        + "</tr><tr><td>Total assets</td>"
        + _fact_cell("d2025", "ttl-ta-2025")
        + _fact_cell("d2024", "ttl-ta-2024")
        + "</tr></table>"
    )


def test_ttl1a5_rowspan_label_row_mixing_members_refuses() -> None:
    """Review finding 3: the carried label is the second line's label, so both
    of its value cells are read and their two members split the row."""
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(
            _rowspan_face(("m2025", "f2024")),
            title=_BALANCE_TITLE,
            context_dimensions=_ENTITY_DIMS,
        )
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a5_rowspan_label_row_on_one_member_serves() -> None:
    parsed = parse_displayed_primary_table(
        _rowspan_face(_MFG), title=_BALANCE_TITLE, context_dimensions=_ENTITY_DIMS
    )
    facts = [fact for row in _rows(parsed) for fact in row["facts"]]
    assert facts == [
        "ttl-g1-2025",
        "ttl-g1-2024",
        "ttl-g2-2025",
        "ttl-g2-2024",
        "ttl-fr-2025",
        "ttl-fr-2024",
        "ttl-ta-2025",
        "ttl-ta-2024",
    ]


def test_ttl1a5_unexpandable_dimensioned_capture_is_judged_on_raw_rows() -> None:
    """A capture whose rowspan overruns its table is judged on its raw rows;
    the parent-only face is dropped and the later statement serves."""
    overrun = (
        "<table><tr><td>Consolidated Balance Sheets</td></tr>"
        "<tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>"
        '<tr><td rowspan="3">Parent net income</td>'
        + _fact_cell("p2025", "ttl-pco-2025")
        + _fact_cell("p2024", "ttl-pco-2024")
        + "</tr></table>"
    )
    parsed = parse_displayed_primary_table(
        overrun + _context_table("<td>Consolidated Balance Sheets</td>", _CONSOLIDATED_ROWS),
        title=_BALANCE_TITLE,
        context_dimensions=_DIMS,
    )
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


@pytest.mark.parametrize(
    ("text", "continued"),
    [
        ("(Cont’d)", True),
        ("cont'd", True),
        ("(Cont.)", True),
        ("Cont", True),
        ("Continued from previous page", True),
        ("(continued from prior page)", True),
        ("continued from the preceding page", True),
        ("Consolidated Balance Sheets (Cont’d)", True),
        ("Contingencies", False),
        ("contingent liabilities", False),
        ("(continued on next page)", False),
        ("discontinued", False),
        ("Commitments and contingencies", False),
    ],
)
def test_ttl1a5_continuation_marker(text: str, continued: bool) -> None:
    parser = statement_graph._StatementTableParser("Consolidated Balance Sheets", fold=True)
    assert parser._continued(text) is continued


@pytest.mark.parametrize(
    "marker", ["(Cont’d)", "(Cont.)", "- Cont'd", "(Continued from previous page)"]
)
def test_ttl1a5_abbreviated_marker_drops_a_later_part(marker: str) -> None:
    """Probe P11: the first part's caption does not arm the fold, so the part
    printed under an abbreviated marker must not be served as the statement."""
    html = (
        "<p>Consolidated Balance Sheets (in millions, except parent company only)</p>"
        + _statement_table("<td></td>", label="Total assets", ids=("ttl-ta-2025", "ttl-ta-2024"))
        + f"<p>Consolidated Balance Sheets</p><p>{marker}</p>"
        + _statement_table("<td></td>")
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a5_stray_text_after_a_fact_cell_keeps_the_capture() -> None:
    """Review finding 5: text between cells of the row being read is checked
    against facts already read in that row, not only committed rows."""
    html = _statement_table("<td>Consolidated Balance Sheets</td>").replace(
        "100</ix:nonFraction></td>", "100</ix:nonFraction></td>continued", 1
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert _rows(parsed) == [
        {"label": "Net income", "facts": ["ttl-ni-2025", "ttl-ni-2024"]}
    ]


_TTL1A6_HEADER = "<tr><td>Line</td><td>September 27, 2025</td><td>September 28, 2024</td></tr>"


def _ttl1a6_table(label: str, ids: tuple[str, str], *, open_row: bool = False) -> str:
    row = "<tr><td>" + label + "</td>" + _fact_cell("d2025", ids[0]) + _fact_cell("d2024", ids[1])
    return "<table>" + _TTL1A6_HEADER + row + ("" if open_row else "</tr>") + "</table>"


_TTL1A6_TOTAL_EQUITY = _ttl1a6_table("Total equity", ("ttl-te-2025", "ttl-te-2024"))


@pytest.mark.parametrize("title_cell", [False, True])
def test_ttl1a6_unexpandable_undimensioned_capture_refuses(title_cell: bool) -> None:
    """A5 review finding 1 (probe P18): a capture of undimensioned facts whose
    rowspan overruns its table is judged on its raw rows and kept, so the
    layout is refused; the later table is not served in its place."""
    title = "<tr><td>Consolidated Balance Sheets</td></tr>" if title_cell else ""
    overrun = (
        ("" if title_cell else "<p>Consolidated Balance Sheets</p>")
        + "<table>"
        + title
        + _TTL1A6_HEADER
        + '<tr><td rowspan="3">Total assets</td>'
        + _fact_cell("d2025", "ttl-ta-2025")
        + _fact_cell("d2024", "ttl-ta-2024")
        + "</tr></table>"
    )
    html = overrun + "<p>Consolidated Balance Sheets</p><p>Supplemental</p>" + _TTL1A6_TOTAL_EQUITY
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE, context_dimensions=_DIMS)
    assert excinfo.value.refusal_code == "displayed_layout_unsupported"


# Each earlier table ends with a fact row whose </tr> never comes.
_TTL1A6_OPEN_ROW_BEFORE = {
    "unrelated_table": _ttl1a6_table("Shares outstanding", ("ttl-sh-2025", "ttl-sh-2024"), open_row=True),
    "first_part_not_armed": (
        "<p>Consolidated Balance Sheets (in millions, except parent company only)</p>"
        + _ttl1a6_table("Total assets", ("ttl-ta-2025", "ttl-ta-2024"), open_row=True)
    ),
}


@pytest.mark.parametrize("dims", [False, True])
@pytest.mark.parametrize("before", sorted(_TTL1A6_OPEN_ROW_BEFORE))
def test_ttl1a6_row_left_open_does_not_hide_a_continued_marker(before: str, dims: bool) -> None:
    """A5 review finding 2 (probes P01, P17): a row whose </tr> never came
    ends with its table, so a later "(Continued)" part is still dropped."""
    html = (
        _TTL1A6_OPEN_ROW_BEFORE[before]
        + "<p>Consolidated Balance Sheets</p><p>(Continued)</p>"
        + _TTL1A6_TOTAL_EQUITY
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(
            html, title=_BALANCE_TITLE, context_dimensions=_DIMS if dims else None
        )
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a6_row_open_outside_any_table_ends_at_the_next_table() -> None:
    """A fact row printed outside any table is dropped when a table opens, so
    the marker before that table's first row is still read."""
    html = (
        "<tr><td>Shares outstanding</td>"
        + _fact_cell("d2025", "ttl-sh-2025")
        + "<p>Consolidated Balance Sheets</p>"
        + _TTL1A6_TOTAL_EQUITY.replace("<table>", "<table>(Continued)", 1)
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert excinfo.value.refusal_code == "displayed_table_absent"


def test_ttl1a6_closed_rows_before_the_title_still_serve() -> None:
    """The row reset at table boundaries changes nothing when rows close."""
    html = (
        _ttl1a6_table("Shares outstanding", ("ttl-sh-2025", "ttl-sh-2024"))
        + "<p>Consolidated Balance Sheets</p>"
        + _TTL1A6_TOTAL_EQUITY
    )
    parsed = parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert _rows(parsed) == [
        {"label": "Total equity", "facts": ["ttl-te-2025", "ttl-te-2024"]}
    ]


@pytest.mark.parametrize(
    ("text", "continued"),
    [
        ("(Contd.)", True),
        ("(Cont’d.)", True),
        ("CONT'D.", True),
        ("(con’t)", True),
        ("(Continued from page 45)", True),
        ("continued from page 7", True),
        ("Consolidated Balance Sheets (Contd.)", True),
        ("(continued on page 46)", False),
        ("(continued from page)", False),
        ("Contents", False),
        ("Continuation", False),
        ("Contra", False),
    ],
)
def test_ttl1a6_continuation_marker(text: str, continued: bool) -> None:
    parser = statement_graph._StatementTableParser("Consolidated Balance Sheets", fold=True)
    assert parser._continued(text) is continued


@pytest.mark.parametrize(
    "marker", ["(Contd.)", "(Cont’d.)", "(con’t)", "(Continued from page 45)"]
)
def test_ttl1a6_widened_marker_drops_a_later_part(marker: str) -> None:
    """A5 review finding 3 (probes P05, P06): a part printed under one of
    these markers is not served as the statement."""
    html = (
        "<p>Consolidated Balance Sheets (in millions, except parent company only)</p>"
        + _statement_table("<td></td>", label="Total assets", ids=("ttl-ta-2025", "ttl-ta-2024"))
        + f"<p>Consolidated Balance Sheets</p><p>{marker}</p>"
        + _statement_table("<td></td>")
    )
    with pytest.raises(StatementGraphError) as excinfo:
        parse_displayed_primary_table(html, title=_BALANCE_TITLE)
    assert excinfo.value.refusal_code == "displayed_table_absent"
