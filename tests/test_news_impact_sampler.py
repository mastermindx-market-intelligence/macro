"""Hermetic tests for engine/news_impact/sampler.py (Phase 1 benchmark draw).

Every frozen rule of the B2_sampler commission has a test that would fail if the
rule were deleted: determinism/replay, seed sensitivity, issuer cap, megacap
share cap at the boundary, one case per group, prospective cohort isolation,
short cells (never padded), tag quotas filled first, RightsRefused, input
counters, group closure, manifest schema, canonical JSON stability, and every
error path's exact code string.

Hermetic: synthetic candidates built here, no network, no repo data files (the
load_tape happy path skips cleanly when pandas/parquet are unavailable on the
host), tmp_path for any file.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

import pytest

from engine.news_impact import sampler as S

UTC = timezone.utc
WIN_START = date(2026, 7, 13)
WIN_END = date(2026, 10, 11)
TAPE_SHA = "ab" * 32


def iso(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def cik(n: int) -> str:
    return f"cik:{n:010d}"


def cand(
    item_id: str,
    *,
    issuer: str | None = None,
    ticker: str | None = None,
    template: str = "T1",
    proxy_cell: str = "positive",
    seendate: datetime | None = None,
    source: str = "reuters",
    event_key: str | None = None,
    tags: frozenset[str] = frozenset(),
    title: str = "",
) -> S.Candidate:
    return S.Candidate(
        item_id=item_id,
        # deterministic default issuer (NEVER hash(): str hash is per-process random)
        issuer=issuer if issuer is not None else cik(int(sha256(item_id.encode()).hexdigest()[:8], 16) % 100 + 1),
        ticker=ticker,
        template=template,
        proxy_cell=proxy_cell,
        seendate=seendate if seendate is not None else iso(1),
        source=source,
        source_sha256=sha256(item_id.encode()).hexdigest(),
        event_key=event_key,
        tags=tags,
        title=title,
    )


def plan(**kw) -> S.SamplePlan:
    base = dict(
        seed=20261012,
        window_start=WIN_START,
        window_end=WIN_END,
        tape_sha256=TAPE_SHA,
    )
    base.update(kw)
    return S.SamplePlan(**base)


def draw(cands, p=None, **kw):
    rights = kw.pop("rights_allow", lambda s: True)
    return S.draw_sample(cands, p or plan(), rights_allow=rights, **kw)


def hash_order(seed: int, ids: list[str]) -> list[str]:
    """The frozen bucket order, recomputed white-box for boundary crafting."""
    return sorted(ids, key=lambda i: sha256(f"{seed}:{i}".encode()).hexdigest())


def find_id_with_rank(seed: int, target: str, others: list[str], rank: int) -> str:
    """Deterministically search suffixes until `target<suffix>` sits at `rank` in hash order."""
    for n in range(5000):
        candidate = f"{target}{n:04d}"
        order = hash_order(seed, others + [candidate])
        if order.index(candidate) == rank:
            return candidate
    raise AssertionError("no id found for the wanted hash rank")


# --- frozen constants ----------------------------------------------------------


def test_constants_frozen():
    assert S.SAMPLER_VERSION == "ni-sampler-1"
    assert S.TEMPLATES == ("T1", "T2", "T3")
    assert S.CELLS == ("positive", "negative", "ambiguous", "no_change")
    assert S.CELL_TARGETS == {"positive": 90, "negative": 50, "ambiguous": 30, "no_change": 30}
    assert S.MEGACAPS == frozenset({"NVDA", "MSFT", "AAPL", "GOOGL", "TSLA", "AMZN", "META"})


# --- determinism and seed sensitivity ------------------------------------------


def _ample_pool(n_per_cell: int = 12) -> list[S.Candidate]:
    out = []
    for cell in S.CELLS:
        for t in S.TEMPLATES:
            for i in range(n_per_cell):
                out.append(
                    cand(
                        f"{t}-{cell}-{i:03d}",
                        issuer=cik(1000 + i),
                        template=t,
                        proxy_cell=cell,
                        seendate=iso(1 + (i % 28)),
                        title=f"story {t} {cell} {i:03d}",  # unique -> singleton groups
                    )
                )
    return out


def test_determinism_same_plan_identical_manifest_and_order():
    pool = _ample_pool()
    p = plan(cell_targets={"positive": 4, "negative": 3, "ambiguous": 2, "no_change": 2})
    d1 = draw(pool, p)
    d2 = draw(pool, p)
    assert d1.manifest["manifest_sha256"] == d2.manifest["manifest_sha256"]
    assert d1.manifest["cases_sha256"] == d2.manifest["cases_sha256"]
    assert d1.cases == d2.cases
    assert [c.item_id for c in d1.cases] == [c.item_id for c in d2.cases]


def test_seed_sensitivity_changes_order_not_counts():
    pool = _ample_pool()
    targets = {"positive": 4, "negative": 3, "ambiguous": 2, "no_change": 2}
    d1 = draw(pool, plan(seed=101, cell_targets=targets))
    d2 = draw(pool, plan(seed=102, cell_targets=targets))
    o1 = [c.item_id for c in d1.cases]
    o2 = [c.item_id for c in d2.cases]
    # ample pools: every cell fills to target under both seeds (counts equal);
    # which items and in what order differs with the seed.
    for t in S.TEMPLATES:
        for cell in S.CELLS:
            assert d1.manifest["cells"][t][cell]["drawn"] == d2.manifest["cells"][t][cell]["drawn"]
    assert len(o1) == len(o2) == 33  # 3 templates x (4+3+2+2)
    assert o1 != o2  # different seed -> different case order


# --- caps ------------------------------------------------------------------------


def test_issuer_cap_binds_at_six_groups():
    cands = [
        cand(f"same-issuer-{i:02d}", issuer=cik(7), seendate=iso(1 + i),
             title=f"distinct story {i}")
        for i in range(10)
    ]
    p = plan(cell_targets={"positive": 10, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(cands, p)
    assert d.manifest["cells"]["T1"]["positive"]["drawn"] == 6
    assert d.manifest["max_issuer_groups"]["T1"] == 6
    assert len({c.item_id for c in d.cases}) == 6


def test_megacap_admitted_exactly_at_boundary_share():
    # 9 non-megacaps + 1 megacap whose hash position is LAST -> admitted as the
    # 10th case, share exactly 1/10 == cap 0.10.
    others = [f"n{i:02d}" for i in range(9)]
    mega_id = find_id_with_rank(20261012, "mega", others, 9)
    cands = [cand(i, issuer=cik(100 + int(i[1:])), seendate=iso(1)) for i in others]
    cands.append(cand(mega_id, issuer=cik(999), ticker="NVDA", seendate=iso(1)))
    p = plan(cell_targets={"positive": 10, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(cands, p)
    assert mega_id in {c.item_id for c in d.cases}
    assert d.manifest["megacap_share"]["T1"] == pytest.approx(0.10)


def test_megacap_skipped_when_share_would_exceed():
    # cap 0.5, target 2: a megacap FIRST in hash order would make the share 100%
    # at admission time -> skipped permanently, final share 0.0.
    others = [f"x{i:02d}" for i in range(3)]
    mega_id = find_id_with_rank(7, "m", others, 0)
    cands = [cand(i, issuer=cik(300 + int(i[1:])), seendate=iso(2)) for i in others]
    cands.append(cand(mega_id, issuer=cik(999), ticker="MSFT", seendate=iso(2)))
    p = plan(seed=7, cell_targets={"positive": 2, "negative": 0, "ambiguous": 0, "no_change": 0},
             megacap_share_cap=0.5)
    d = draw(cands, p)
    assert mega_id not in {c.item_id for c in d.cases}
    assert d.manifest["megacap_share"]["T1"] == 0.0
    assert d.manifest["cells"]["T1"]["positive"]["drawn"] == 2


def test_megacap_share_never_exceeds_cap_under_skips():
    # 60 megacaps + 60 others, target 30: whatever the hash order does, the
    # prefix-share rule keeps the final share <= cap.
    cands = [cand(f"m{i:03d}", issuer=cik(900 + i), ticker="AAPL", seendate=iso(3)) for i in range(60)]
    cands += [cand(f"o{i:03d}", issuer=cik(2000 + i), seendate=iso(4)) for i in range(60)]
    p = plan(cell_targets={"positive": 30, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(cands, p)
    assert d.manifest["megacap_share"]["T1"] <= 0.10 + 1e-12
    assert d.manifest["cells"]["T1"]["positive"]["drawn"] == 30


def test_economic_cluster_cap_and_manifest_report():
    def econ(item_id: str) -> str | None:
        return "semis" if item_id.startswith("s") else None

    cands = [cand(f"s{i:03d}", issuer=cik(500 + i), seendate=iso(5)) for i in range(20)]
    cands += [cand(f"z{i:03d}", issuer=cik(700 + i), seendate=iso(6)) for i in range(20)]
    p = plan(cell_targets={"positive": 20, "negative": 0, "ambiguous": 0, "no_change": 0},
             economic_cluster_cap=0.25)
    d = draw(cands, p, economic_cluster=econ)
    assert d.manifest["economic_cluster"]["status"] == "checked"
    assert d.manifest["economic_cluster"]["max_share"] <= 0.25 + 1e-12
    drawn_semis = sum(1 for c in d.cases if c.item_id.startswith("s"))
    assert drawn_semis <= 5  # 25% of 20


def test_economic_cluster_unchecked_reports_reason():
    d = draw(_ample_pool(2))
    assert d.manifest["economic_cluster"] == {
        "status": "unchecked",
        "reason": "economic_cluster callable not provided",
    }


# --- grouping --------------------------------------------------------------------


def test_one_case_per_group_per_template():
    cands = [
        cand("g-a", issuer=cik(1), event_key="ev-1", seendate=iso(10)),
        cand("g-b", issuer=cik(2), event_key="ev-1", seendate=iso(11)),
        cand("g-c", issuer=cik(3), event_key="ev-1", seendate=iso(12)),
    ]
    p = plan(cell_targets={"positive": 3, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(cands, p)
    assert len(d.cases) == 1
    assert d.manifest["cells"]["T1"]["positive"] == {"target": 3, "drawn": 1, "short": 2}


def test_group_closure_event_key_then_title():
    a = cand("a", issuer=cik(1), event_key="e1", seendate=iso(1, 1), title="Alpha reports")
    b = cand("b", issuer=cik(2), event_key="e1", seendate=iso(1, 2), title="Beta reports")
    c = cand("c", issuer=cik(2), event_key=None, seendate=iso(1, 3), title="beta   REPORTS")
    gids = S.group_ids([a, b, c])
    expected = "grp:" + sha256("\n".join(sorted(["a", "b", "c"])).encode()).hexdigest()[:16]
    assert set(gids.values()) == {expected}


def test_group_title_join_requires_72h_window():
    near = cand("n1", issuer=cik(1), seendate=iso(1, 1), title="Same headline")
    far = cand("n2", issuer=cik(1), seendate=iso(1, 1) + timedelta(hours=73), title="Same headline")
    assert len(set(S.group_ids([near, far]).values())) == 2
    edge = cand("n3", issuer=cik(1), seendate=iso(1, 1) + timedelta(hours=72), title="Same headline")
    assert len(set(S.group_ids([near, edge]).values())) == 1


def test_group_ids_rejects_duplicate_item_id():
    with pytest.raises(S.SamplerError, match=re.escape("duplicate item_id in candidates: 'a'")):
        S.group_ids([cand("a"), cand("a")])


# --- folds ------------------------------------------------------------------------


def test_prospective_cohort_never_in_numbered_folds():
    cands = [
        cand(f"old-{i:02d}", issuer=cik(10 + i), seendate=iso(1 + i)) for i in range(10)
    ] + [
        cand(f"new-{i:02d}", issuer=cik(100 + i), seendate=datetime(2026, 9, 20, tzinfo=UTC))
        for i in range(5)
    ]
    p = plan(prospective_from=date(2026, 9, 1),
             cell_targets={"positive": 15, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(cands, p)
    fold_by_id = {c.item_id: c.fold for c in d.cases}
    assert all(fold_by_id[f"new-{i:02d}"] == "prospective" for i in range(5))
    numbered = {fold_by_id[f"old-{i:02d}"] for i in range(10)}
    assert numbered <= {"f1", "f2", "f3", "f4", "f5"}
    assert "prospective" not in numbered
    assert sum(v for k, v in d.manifest["folds"].items() if k != "prospective") == 10


def test_assign_folds_near_equal_group_counts():
    cands = [
        cand(f"i{i:02d}", issuer=cik(1), seendate=iso(1) + timedelta(hours=i),
             title=f"headline {i}")
        for i in range(10)
    ]
    gids = S.group_ids(cands)
    folds = S.assign_folds(cands, gids, plan(folds=3))
    counts: dict[str, int] = {}
    for f in folds.values():
        counts[f] = counts.get(f, 0) + 1
    assert counts == {"f1": 4, "f2": 3, "f3": 3}
    with pytest.raises(S.SamplerError, match=re.escape("groups map missing item_id: 'zz'")):
        S.assign_folds(cands + [cand("zz")], gids, plan())


# --- short cells and tag quotas -----------------------------------------------------


def test_short_cell_reported_never_padded_or_duplicated():
    cands = [
        cand(f"neg-{i}", issuer=cik(i + 1), proxy_cell="negative", seendate=iso(2)) for i in range(3)
    ]
    p = plan()
    d = draw(cands, p)
    assert d.manifest["cells"]["T1"]["negative"] == {"target": 50, "drawn": 3, "short": 47}
    assert d.manifest["cells"]["T1"]["positive"] == {"target": 90, "drawn": 0, "short": 90}
    assert len(d.cases) == 3
    ids = [c.item_id for c in d.cases]
    assert len(set(ids)) == len(ids)  # no duplicates
    assert all(i.startswith("neg-") for i in ids)  # no borrowing from another cell


def test_tag_quotas_filled_first_inside_cells():
    tagged = [
        cand(f"tag-{i}", issuer=cik(i + 1), tags=frozenset({"near_duplicate"}), seendate=iso(3))
        for i in range(2)
    ]
    untagged = [
        cand(f"plain-{i}", issuer=cik(100 + i), seendate=iso(4)) for i in range(8)
    ]
    p = plan(cell_targets={"positive": 5, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(tagged + untagged, p)
    drawn_ids = {c.item_id for c in d.cases}
    assert {t.item_id for t in tagged} <= drawn_ids  # tagged drawn first, whatever the hash order
    assert d.manifest["tag_quotas"]["T1"]["near_duplicate"]["drawn"] == 2
    assert d.manifest["tag_quotas"]["T1"]["near_duplicate"]["short"] == 18
    assert d.manifest["tag_quotas"]["T1"]["indirect_transfer"] == {
        "target": 10, "drawn": 0, "short": 10,
    }


# --- rights and input accounting ------------------------------------------------------


def test_rights_refused_raises_naming_source():
    cands = [cand("r1", issuer=cik(1), source="banned.example", seendate=iso(1))]
    with pytest.raises(S.RightsRefused) as ei:
        draw(cands, rights_allow=lambda s: s != "banned.example")
    assert "banned.example" in str(ei.value)
    assert str(ei.value).startswith("rights registry does not admit source:")


def test_outside_window_and_unresolved_counters():
    cands = [
        cand("in-1", issuer=cik(1), seendate=datetime(2026, 8, 1, tzinfo=UTC)),
        cand("before", issuer=cik(2), seendate=datetime(2026, 7, 12, 23, tzinfo=UTC)),
        cand("after", issuer=cik(3), seendate=datetime(2026, 10, 12, tzinfo=UTC)),
        cand("unres", issuer="UNRESOLVED", seendate=datetime(2026, 8, 2, tzinfo=UTC)),
    ]
    d = draw(cands)
    assert d.manifest["counters"] == {
        "outside_window": 2,
        "low_value": 0,  # applied upstream by engine.news_common.is_low_value
        "unresolved_issuer": 1,
        "rights_refused": 0,  # any refusal raises instead
    }
    assert [c.item_id for c in d.cases] == ["in-1"]


# --- manifest, schema, canonical JSON ---------------------------------------------------


def _rich_draw():
    p = plan(cell_targets={"positive": 6, "negative": 4, "ambiguous": 3, "no_change": 3})
    pool = _ample_pool(9)
    pool[0] = cand(pool[0].item_id, issuer=cik(1000), tags=frozenset({"near_duplicate"}),
                   template=pool[0].template, proxy_cell=pool[0].proxy_cell,
                   seendate=pool[0].seendate)
    return draw(pool, p)


def test_manifest_reports_every_frozen_key():
    m = _rich_draw().manifest
    assert set(m) == {
        "sampler_version", "seed", "tape_sha256", "window", "plan", "cells",
        "tag_quotas", "megacap_share", "max_issuer_groups", "economic_cluster",
        "counters", "folds", "cases_sha256", "manifest_sha256",
    }
    assert m["sampler_version"] == "ni-sampler-1"
    assert m["window"] == {"start": "2026-07-13", "end": "2026-10-11"}
    assert m["plan"]["issuer_cap"] == 6 and m["plan"]["folds"] == 5
    assert set(m["cells"]) == set(S.TEMPLATES)


def test_case_shape_is_the_frozen_nine_fields():
    d = _rich_draw()
    assert d.cases, "rich draw must produce cases"
    c = d.cases[0]
    assert set(c.to_dict()) == {
        "item_id", "issuer", "template", "proxy_cell", "group_id", "fold",
        "source_sha256", "seendate", "tags",
    }
    assert c.seendate.endswith("Z")  # ISO-8601 UTC
    assert list(c.tags) == sorted(c.tags)
    assert c.group_id.startswith("grp:") and len(c.group_id) == 20


def test_canonical_json_stability_and_sha_recompute():
    d = _rich_draw()
    cases_json = json.dumps(
        [c.to_dict() for c in d.cases], sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    assert sha256(cases_json.encode()).hexdigest() == d.manifest["cases_sha256"]
    without = {k: v for k, v in d.manifest.items() if k != "manifest_sha256"}
    mj = json.dumps(without, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert sha256(mj.encode()).hexdigest() == d.manifest["manifest_sha256"]
    # non-ASCII in an item_id survives as an escape; the sha stays recomputable
    pool = _ample_pool(4) + [cand("iteém-1", issuer=cik(4242), seendate=iso(9))]
    d2 = draw(pool, plan(cell_targets={"positive": 3, "negative": 2, "ambiguous": 2, "no_change": 2}))
    without2 = {k: v for k, v in d2.manifest.items() if k != "manifest_sha256"}
    mj2 = json.dumps(without2, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert sha256(mj2.encode()).hexdigest() == d2.manifest["manifest_sha256"]


def test_build_manifest_statsless_path_uses_megacap_ciks():
    # AAPL candidate admitted among non-megacaps; rebuild without stats derives
    # the share from the case issuers and must agree with the draw-time figure.
    others = [f"q{i:02d}" for i in range(9)]
    cands = [cand(i, issuer=cik(400 + int(i[1:])), seendate=iso(7)) for i in others]
    # a megacap last in hash order is admitted at exactly 1/10 share
    cands.append(
        cand(find_id_with_rank(20261012, "qm", others, 9), issuer="cik:0000320193",
             ticker="AAPL", seendate=iso(7))
    )
    p = plan(cell_targets={"positive": 10, "negative": 0, "ambiguous": 0, "no_change": 0})
    d = draw(cands, p)
    m2 = S.build_manifest(p, d.cases, d.manifest["counters"])
    assert m2["megacap_share"]["T1"] == pytest.approx(d.manifest["megacap_share"]["T1"])
    assert m2["manifest_sha256"] == d.manifest["manifest_sha256"]


def test_manifest_validates_against_schema():
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover - jsonschema absent on some hosts
        pytest.skip("jsonschema not importable on this host; schema validation unverified here")
    Draft202012Validator.check_schema(S.MANIFEST_SCHEMA)
    validator = Draft202012Validator(S.MANIFEST_SCHEMA)
    for m in (_rich_draw().manifest, draw([]).manifest):
        validator.validate(m)
    bad = dict(_rich_draw().manifest)
    bad.pop("counters")
    assert list(validator.iter_errors(bad)), "schema must reject a manifest missing a key"


def test_schema_file_written_matches_module_schema():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "contracts" / "news_impact" / "sample_manifest.v1.schema.json"
    if not path.exists():
        pytest.fail(f"missing {path}")
    assert json.loads(path.read_text()) == S.MANIFEST_SCHEMA


# --- error paths (exact code strings) ---------------------------------------------------


@pytest.mark.parametrize(
    "kwargs, match",
    [
        (dict(template="T9"), "candidate template not in TEMPLATES ['T1', 'T2', 'T3']: 'T9'"),
        (dict(proxy_cell="bullish"), "candidate proxy_cell not in CELLS"),
        (dict(tags=frozenset({"viral"})), "candidate tags outside ['indirect_transfer', 'near_duplicate']: ['viral']"),
        (dict(seendate=datetime(2026, 8, 1)), "candidate seendate must be a timezone-aware datetime"),
        (dict(item_id=""), "candidate item_id must be non-empty"),
        (dict(source=""), "candidate source must be non-empty"),
        (dict(title=7), "candidate title must be a str"),
    ],
)
def test_candidate_validation(kwargs, match):
    item_id = kwargs.pop("item_id", "bad-1")
    with pytest.raises(S.SamplerError, match=re.escape(match)):
        cand(item_id, **kwargs)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        (dict(folds=0), "plan.folds must be an int >= 1: 0"),
        (dict(window_start=date(2026, 10, 12)), "plan.window_start after plan.window_end"),
        (dict(tape_sha256="zz"), "plan.tape_sha256 must be 64 lowercase hex"),
        (dict(megacap_share_cap=1.5), "plan.megacap_share_cap must be within [0, 1]: 1.5"),
        (dict(issuer_cap=0), "plan.issuer_cap must be an int >= 1: 0"),
        (dict(near_duplicate_min=-1), "plan.near_duplicate_min must be an int >= 0: -1"),
        (dict(cell_targets={"positive": 1}), "plan.cell_targets missing cell: negative"),
        (dict(seed="x"), "plan.seed must be an int: 'x'"),
    ],
)
def test_plan_validation(kwargs, match):
    with pytest.raises(S.SamplerError, match=re.escape(match)):
        plan(**kwargs)


def test_build_manifest_rejects_wrong_counter_keys():
    d = _rich_draw()
    with pytest.raises(S.SamplerError, match=re.escape("counters must have exactly the keys")):
        S.build_manifest(plan(), d.cases, {"outside_window": 0})


def test_load_tape_raises_sampler_error_without_pandas(monkeypatch):
    monkeypatch.setitem(sys.modules, "pandas", None)
    with pytest.raises(S.SamplerError, match=re.escape("pandas is not installed")):
        S.load_tape("/nonexistent/items.parquet", window_start=WIN_START, window_end=WIN_END)


def test_load_tape_reads_window_and_sorts(tmp_path):
    pd = pytest.importorskip("pandas", reason="pandas not importable on this host")
    try:
        frame = pd.DataFrame(
            [
                {"item_id": "b", "seendate": "2026-08-02T10:00:00+00:00", "title": "B"},
                {"item_id": "a", "seendate": "2026-08-01T09:00:00+00:00", "title": "A"},
                {"item_id": "out", "seendate": "2026-06-01T09:00:00+00:00", "title": "O"},
            ]
        )
        path = tmp_path / "items.parquet"
        frame.to_parquet(path)
    except Exception as exc:  # no parquet engine on the host
        pytest.skip(f"parquet engine unavailable on this host: {exc}")
    rows = S.load_tape(str(path), window_start=WIN_START, window_end=WIN_END)
    assert [r["item_id"] for r in rows] == ["a", "b"]
    assert rows[0]["seendate"].tzinfo is not None


def test_load_tape_drops_and_counts_undated_rows(tmp_path):
    # the 2026-10-12 qbus tape carries 1,311 blank seendates; an undated row
    # must be dropped and counted by reason, never crash and never be guessed
    pd = pytest.importorskip("pandas", reason="pandas not importable on this host")
    try:
        frame = pd.DataFrame(
            [
                {"item_id": "a", "seendate": "2026-08-01T09:00:00+08:00", "title": "A"},
                {"item_id": "blank", "seendate": "", "title": "B"},
                {"item_id": "space", "seendate": "  ", "title": "S"},
                {"item_id": "junk", "seendate": "not-a-date", "title": "J"},
            ]
        )
        path = tmp_path / "items.parquet"
        frame.to_parquet(path)
    except Exception as exc:  # no parquet engine on the host
        pytest.skip(f"parquet engine unavailable on this host: {exc}")
    dropped = {}
    rows = S.load_tape(str(path), window_start=WIN_START, window_end=WIN_END, dropped=dropped)
    assert [r["item_id"] for r in rows] == ["a"]
    assert dropped == {"seendate_blank": 2, "seendate_unparseable": 1}
    assert S.load_tape(str(path), window_start=WIN_START, window_end=WIN_END) == rows
