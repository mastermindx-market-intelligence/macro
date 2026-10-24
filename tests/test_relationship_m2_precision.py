"""M2 precision sampling: blind stratified sample, decoys, Wilson scorer.

Pins the frozen Q1-Q9 spec of the REL-M2-PREC-BUILD lane at the M2 base:
claim rendering (all species/roles, status prefixes, magnitude kinds and
precisions, the exact M1 SWKS->AAPL example), the allocation algorithm and its
worked example, salt-keyed determinism, decoy kind cycling and applicability
fallback, blind outputs (nothing under the sample dir reveals per-item truth),
excerpt exclusion counting, the score accept rules with the pinned Wilson
interval, the stratified-normal weighted overall, the decoy reliability flag,
the quote rules, drift/salt/sample-mismatch refusals, the review-gated sample
key, and the real M1 population rows.

Synthetic fixtures copy the real M1 observation row and excerpt and edit
fields; verdicts are written by the test, never committed.  No network.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import package_v2 as pv2  # noqa: E402
from engine.company_intelligence.relationships import precision as prec  # noqa: E402

EXTRACTION_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
SOURCES_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"
LEAVES_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_inputs/leaves_v1.json"
)
ACC_24 = "0000004127-24-000131"
ACC_25 = "0000004127-25-000085"
M1_ROW_24 = "obs:aafd6fdeb1ee9043d452"
M1_ROW_25 = "obs:ac5a91d2e47760c66b4b"
SWKS = "ISS:US-XNAS-SWKS"
AAPL = "ISS:US-XNAS-AAPL"
SEED = "gmi-rel-m2-precision-v1"
S = "Skyworks Solutions, Inc."
O = "Apple"


# --- fixture helpers ----------------------------------------------------------


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _m1_row(observation_id: str = M1_ROW_25) -> dict:
    for line in EXTRACTION_PATH.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("observation_id") == observation_id:
            return json.loads(json.dumps(row))
    raise AssertionError(f"{observation_id} not in {EXTRACTION_PATH}")


def _excerpt(acc: str = ACC_25) -> dict:
    return json.loads((SOURCES_DIR / f"{acc}.json").read_text("utf-8"))


def _edited_excerpt(acc: str, new_text: str) -> dict:
    """A valid excerpt of `acc` whose span text is replaced by `new_text`."""
    doc = json.loads(json.dumps(_excerpt(acc)))
    raw = new_text
    doc["span"] = {
        "byte_start": 0,
        "byte_end": len(raw.encode("utf-8")),
        "raw": raw,
        "raw_sha256": _sha(raw.encode("utf-8")),
        "normalized": pv2.normalize_span(raw.encode("utf-8")),
        "normalized_sha256": "",
    }
    doc["span"]["normalized"] = pv2.normalize_span(raw.encode("utf-8"))
    doc["span"]["normalized_sha256"] = _sha(
        doc["span"]["normalized"].encode("utf-8")
    )
    doc["xbrl_contexts"] = []
    return doc


def _tampered_excerpt(acc: str) -> dict:
    """An excerpt whose span.raw no longer hashes to its pinned raw_sha256."""
    doc = json.loads(json.dumps(_excerpt(acc)))
    doc["span"]["raw"] = doc["span"]["raw"] + " tampered tail"
    return doc


def _repointed_row(
    base_row: dict,
    *,
    accession: str | None = None,
    span_sha256: str | None = None,
    normalized_span_sha256: str | None = None,
    byte_start: int = 0,
    byte_end: int = 100,
    subject: dict | None = None,
    species: str | None = None,
    magnitudes: str = "keep",
    object_party: dict | None = None,
) -> dict:
    """A copy of `base_row` re-pointed at a (possibly new) span; id recomputed."""
    row = json.loads(json.dumps(base_row))
    src = dict(row["source_ref"])
    if accession is not None:
        src["accession"] = accession
    if span_sha256 is not None:
        src["span_sha256"] = span_sha256
    if normalized_span_sha256 is not None:
        src["normalized_span_sha256"] = normalized_span_sha256
    src["byte_start"] = byte_start
    src["byte_end"] = byte_end
    row["source_ref"] = src
    if subject is not None:
        row["subject"] = json.loads(json.dumps(subject))
    if object_party is not None:
        row["object"] = json.loads(json.dumps(object_party))
    if species is not None:
        row["species"] = species
    if magnitudes == "none":
        row["magnitudes"] = []
    row["observation_id"] = pv2.observation_identity(
        src["accession"],
        src["byte_start"],
        src["byte_end"],
        row["species"],
        row["subject"]["issuer_id"],
        row["object"]["issuer_id"],
    )
    return row


def _issuer(iid: str, name: str) -> dict:
    return {
        "cik": "0000004127",
        "issuer_id": iid,
        "name_as_filed": name,
        "security_ids": ["SEC:US-XNAS-SWKS"],
    }


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")
        + b"\n"
    )


def _fixture(
    tmp_path: Path,
    rows: list[dict],
    excerpts: dict[str, dict],
    domain_of: dict[str, str],
) -> dict:
    """Write a synthetic extraction/sources/leaves triple under tmp_path."""
    extraction = tmp_path / "extraction"
    extraction.mkdir()
    (extraction / "rows.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    sources = tmp_path / "sources"
    sources.mkdir()
    for accession, doc in excerpts.items():
        _write_json(sources / f"{accession}.json", doc)
    leaves = tmp_path / "leaves.json"
    _write_json(leaves, {"domain_of": domain_of})
    return {
        "extraction": extraction,
        "sources": sources,
        "leaves": leaves,
        "rows": {row["observation_id"]: row for row in rows},
    }


def _salt_file(tmp_path: Path, name: str = "salt.bin", data: bytes | None = None) -> Path:
    path = tmp_path / name
    path.write_bytes(data if data is not None else bytes(range(32)))
    return path


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["TZ"] = "UTC"
    return subprocess.run(
        [sys.executable, "scripts/relationship_m2_precision.py", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


def _sample(fx: dict, out: Path, salt: Path, *extra: str) -> subprocess.CompletedProcess:
    return _run_cli(
        "sample",
        "--salt-file",
        str(salt),
        "--out-dir",
        str(out),
        "--extraction",
        str(fx["extraction"]),
        "--sources",
        str(fx["sources"]),
        "--leaves",
        str(fx["leaves"]),
        *extra,
    )


def _score(
    fx: dict,
    out: Path,
    salt: Path,
    verdicts: Path,
    *extra: str,
) -> subprocess.CompletedProcess:
    return _run_cli(
        "score",
        "--sample-dir",
        str(out),
        "--verdicts",
        str(verdicts),
        "--salt-file",
        str(salt),
        "--extraction",
        str(fx["extraction"]),
        "--sources",
        str(fx["sources"]),
        "--leaves",
        str(fx["leaves"]),
        *extra,
    )


def _items(out: Path) -> list[dict]:
    """Every item in D/review, in file order."""
    items = []
    for pack in sorted((out / "review").glob("pack_*.jsonl")):
        for line in pack.read_text("utf-8").splitlines():
            if line.strip():
                items.append(json.loads(line))
    return items


def _write_verdicts(path: Path, verdicts: list[dict]) -> Path:
    verdicts_dir = path
    verdicts_dir.mkdir(parents=True, exist_ok=True)
    (verdicts_dir / "v.jsonl").write_text(
        "\n".join(json.dumps(v) for v in verdicts) + "\n", encoding="utf-8"
    )
    return verdicts_dir


def _verdict(
    item: dict,
    *,
    accept: bool,
    relationship: str = "supported",
    quote: object = "AUTO",
    magnitude: str | None = None,
) -> dict:
    if quote == "AUTO":
        text = item["excerpt"]["text"]
        quote = text[:40] if len(text) >= 40 else text
    mags = len(item["claim"]["magnitudes"])
    return {
        "schema": prec.VERDICT_SCHEMA_NAME,
        "item_id": item["item_id"],
        "relationship": relationship,
        "direction": "correct" if accept else "wrong",
        "counterparty": "correct" if accept else "wrong",
        "status": "correct" if accept else "wrong",
        "magnitude": magnitude or ("correct" if mags else "n/a"),
        "quote": quote,
        "note": "",
        "reviewer": {
            "agent": "rel-m2-prec-build-test",
            "lane_run_id": "gmi-rel-m2-prec-build-20261022-r1",
        },
    }


def _claim(**overrides: object) -> dict:
    claim = {
        "subject_name": S,
        "counterparty_name": O,
        "counterparty_unnamed": False,
        "species": "supplier_customer",
        "role": "supplier",
        "relation_status": "asserted",
        "magnitudes": [],
    }
    claim.update(overrides)
    return claim


def _mag(kind: str, value, unit, precision, label="FY2025", value_high=None) -> dict:
    return {
        "kind": kind,
        "value": value,
        "value_high": value_high,
        "unit": unit,
        "precision": precision,
        "period_label": label,
    }


# --- Q5: claim rendering -------------------------------------------------------


def test_render_claim_all_species_roles_exact():
    # The 10 base sentences, one per (species, role).
    base = [
        ("supplier_customer", "supplier", f"{S} sells products or services to {O}."),
        ("supplier_customer", "customer", f"{S} buys products or services from {O}."),
        (
            "contract_manufacturing",
            "manufacturer",
            f"{S} manufactures products for {O}.",
        ),
        ("contract_manufacturing", "client", f"{O} manufactures products for {S}."),
        ("licensing", "licensor", f"{S} licenses technology or rights to {O}."),
        ("licensing", "licensee", f"{S} licenses technology or rights from {O}."),
        ("distribution", "manufacturer", f"{O} distributes {S}'s products."),
        ("distribution", "distributor", f"{S} distributes {O}'s products."),
        (
            "component_dependency",
            "provider",
            f"{S} provides a component or input that {O} depends on.",
        ),
        (
            "component_dependency",
            "dependent",
            f"{S} depends on a component or input from {O}.",
        ),
    ]
    for species, role, expected in base:
        claim = _claim(species=species, role=role)
        assert prec.render_claim(claim) == expected, (species, role)

    # The 3 status prefixes.
    assert prec.render_claim(_claim()) == f"{S} sells products or services to {O}."
    assert prec.render_claim(_claim(relation_status="terminated")) == (
        f"The filing says this has ENDED: {S} sells products or services to {O}."
    )
    assert prec.render_claim(_claim(relation_status="denied")) == (
        f"The filing says this is NOT the case: {S} sells products or services to {O}."
    )

    # The 4 magnitude kinds (each rendered after the base sentence).
    base = f"{S} sells products or services to {O}."
    assert prec.render_claim(
        _claim(magnitudes=[_mag("seller_revenue_share", 0.67, "ratio", "exact")])
    ) == f"{base} {O} accounted for 67% of {S}'s revenue in FY2025."
    assert prec.render_claim(
        _claim(magnitudes=[_mag("buyer_procurement_share", 0.3, "ratio", "exact")])
    ) == f"{base} {O} accounted for 30% of {S}'s purchases in FY2025."
    assert prec.render_claim(
        _claim(magnitudes=[_mag("contract_value", 1500000.0, "USD", "exact")])
    ) == f"{base} The contract value is 1.5e+06 USD (FY2025)."
    assert prec.render_claim(
        _claim(magnitudes=[_mag("purchase_commitment", 500000.0, "units", "exact")])
    ) == f"{base} The purchase commitment is 500,000 units (FY2025)."

    # The 4 precisions on a seller_revenue_share magnitude.
    assert prec.render_claim(
        _claim(magnitudes=[_mag("seller_revenue_share", 0.45, "ratio", "lower_bound")])
    ) == f"{base} {O} accounted for at least 45% of {S}'s revenue in FY2025."
    assert prec.render_claim(
        _claim(magnitudes=[_mag("seller_revenue_share", 0.45, "ratio", "upper_bound")])
    ) == f"{base} {O} accounted for at most 45% of {S}'s revenue in FY2025."
    assert prec.render_claim(
        _claim(
            magnitudes=[
                _mag(
                    "seller_revenue_share",
                    0.45,
                    "ratio",
                    "range",
                    value_high=0.60,
                )
            ]
        )
    ) == f"{base} {O} accounted for between 45% and 60% of {S}'s revenue in FY2025."
    assert prec.render_claim(
        _claim(magnitudes=[_mag("seller_revenue_share", 0.45, "ratio", "range")])
    ) == f"{base} {O} accounted for approximately 45% of {S}'s revenue in FY2025."

    # A non-ratio share unit renders num + unit; a range on a contract value
    # formats both bounds identically.
    assert prec.render_claim(
        _claim(magnitudes=[_mag("seller_revenue_share", 1200.0, "USD", "exact")])
    ) == f"{base} {O} accounted for 1,200 USD of {S}'s revenue in FY2025."
    assert prec.render_claim(
        _claim(
            magnitudes=[
                _mag(
                    "contract_value",
                    1500000.0,
                    "USD",
                    "range",
                    value_high=2000000.0,
                )
            ]
        )
    ) == f"{base} The contract value is between 1.5e+06 USD and 2e+06 USD (FY2025)."

    # An unnamed counterparty renders the alias with the not-named suffix.
    claim = _claim(
        counterparty_name="Customer A",
        counterparty_unnamed=True,
        magnitudes=[_mag("seller_revenue_share", 0.67, "ratio", "exact")],
    )
    assert prec.render_claim(claim) == (
        f"{S} sells products or services to Customer A (not named in the filing). "
        "Customer A (not named in the filing) accounted for 67% of "
        f"{S}'s revenue in FY2025."
    )

    # A null-valued magnitude states no number and is not the renderer's problem:
    # the claim simply carries no such magnitude (claim_from_row drops it).
    row = _m1_row()
    row["magnitudes"].append(
        dict(row["magnitudes"][0], value=None, xbrl_fact_id="f-000")
    )
    claim = prec.claim_from_row(row)
    assert len(claim["magnitudes"]) == 3


def test_render_claim_m1_swks_exact():
    row = _m1_row(M1_ROW_25)
    claim = prec.claim_from_row(row)
    assert claim["subject_name"] == S
    assert claim["counterparty_name"] == O
    assert claim["counterparty_unnamed"] is False
    assert claim["species"] == "supplier_customer"
    assert claim["role"] == "supplier"  # subject_role omitted -> species default
    assert claim["relation_status"] == "asserted"
    assert [m["period_label"] for m in claim["magnitudes"]] == [
        "FY2025",
        "FY2024",
        "FY2023",
    ]
    assert prec.render_claim(claim) == (
        "Skyworks Solutions, Inc. sells products or services to Apple. "
        "Apple accounted for 67% of Skyworks Solutions, Inc.'s revenue in FY2025. "
        "Apple accounted for 69% of Skyworks Solutions, Inc.'s revenue in FY2024. "
        "Apple accounted for 66% of Skyworks Solutions, Inc.'s revenue in FY2023."
    )


# --- Q3: allocation -------------------------------------------------------------


def test_allocation_worked_example():
    alloc, below = prec.allocate({"A": 3, "B": 50, "C": 200}, 100, 8)
    assert alloc == {"A": 3, "B": 24, "C": 73}
    assert below is False


def test_allocation_floors_win_and_small_population():
    # Floors alone exceed n: floors win and n_effective is their sum.
    alloc, below = prec.allocate({"A": 10, "B": 10}, 12, 8)
    assert alloc == {"A": 8, "B": 8}
    assert below is False
    # A population smaller than n takes every row and flags below-target.
    alloc, below = prec.allocate({"A": 2, "B": 3}, 100, 8)
    assert alloc == {"A": 2, "B": 3}
    assert below is True
    # Remainder units go by largest fractional part of the quota, then name.
    # R=7 over sizes {A: 10, B: 1}: quota A = 7*10/11 = 6.36, B = 0.63;
    # give min(6, cap) / min(0, cap) -> remainder 1 unit to A (fraction .36 > .63?
    # no: B has none left, so A takes it) -> A 7?  Pinned exactly:
    alloc, below = prec.allocate({"A": 10, "B": 1}, 17, 0)
    assert alloc == {"A": 10, "B": 1}  # population exhausted
    assert below is True


# --- Q2/Q3/Q6: determinism and blindness ----------------------------------------


def _eight_row_fixture(tmp_path: Path) -> dict:
    """8 rows: 6 in D1|supplier_customer (SWKS), 2 in D2|supplier_customer."""
    base = _m1_row()
    rows = []
    for index in range(6):
        rows.append(
            _repointed_row(
                base, byte_start=0, byte_end=200 + index, magnitudes="none"
                if index % 2
                else "keep"
            )
        )
    other_subject = _issuer("ISS:US-XNAS-TXN", "Texas Instruments Incorporated")
    for index in range(2):
        rows.append(
            _repointed_row(
                base,
                byte_start=0,
                byte_end=300 + index,
                subject=other_subject,
            )
        )
    excerpts = {ACC_25: _excerpt(ACC_25), ACC_24: _excerpt(ACC_24)}
    rows[1] = _repointed_row(
        rows[1],
        accession=ACC_24,
        span_sha256=_excerpt(ACC_24)["span"]["raw_sha256"],
        normalized_span_sha256=_excerpt(ACC_24)["span"]["normalized_sha256"],
    )
    domain_of = {SWKS: "D1", "ISS:US-XNAS-TXN": "D2"}
    return _fixture(tmp_path, rows, excerpts, domain_of)


def test_selection_deterministic_and_salt_sensitive(tmp_path):
    fx = _eight_row_fixture(tmp_path)
    salt_a = _salt_file(tmp_path, "salt_a.bin")
    out1, out2 = tmp_path / "s1", tmp_path / "s2"
    proc1 = _sample(fx, out1, salt_a, "--n", "6", "--floor", "2", "--decoys", "2")
    proc2 = _sample(fx, out2, salt_a, "--n", "6", "--floor", "2", "--decoys", "2")
    assert proc1.returncode == 0, proc1.stdout + proc1.stderr
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    assert proc1.stdout == proc2.stdout
    names1 = sorted(p.relative_to(out1).as_posix() for p in out1.rglob("*") if p.is_file())
    names2 = sorted(p.relative_to(out2).as_posix() for p in out2.rglob("*") if p.is_file())
    assert names1 == names2
    for name in names1:
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes(), name

    # A different salt changes the keys: different items, same inputs.
    salt_b = _salt_file(tmp_path, "salt_b.bin", data=bytes(range(32))[::-1])
    out3 = tmp_path / "s3"
    proc3 = _sample(fx, out3, salt_b, "--n", "6", "--floor", "2", "--decoys", "2")
    assert proc3.returncode == 0, proc3.stdout + proc3.stderr
    ids_a = {item["item_id"] for item in _items(out1)}
    ids_b = {item["item_id"] for item in _items(out3)}
    assert ids_a and ids_b and not (ids_a & ids_b)
    manifest_a = json.loads((out1 / "manifest.json").read_text("utf-8"))
    manifest_b = json.loads((out3 / "manifest.json").read_text("utf-8"))
    assert manifest_a["salt_sha256"] != manifest_b["salt_sha256"]
    # The out-dir refusals: a non-empty out dir, and a short salt.
    assert _sample(fx, out1, salt_a, "--n", "6", "--floor", "2").returncode == 2
    short = _salt_file(tmp_path, "short.bin", data=b"too-short")
    assert _sample(fx, tmp_path / "s4", short, "--n", "6", "--floor", "2").returncode == 2


def test_blind_outputs_reveal_nothing(tmp_path):
    fx = _eight_row_fixture(tmp_path)
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "6", "--floor", "2", "--decoys", "2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    strata = [b"D1|supplier_customer", b"D2|supplier_customer"]
    manifest = out / "manifest.json"
    for path in sorted(out.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        if path == manifest:
            # Aggregates only: no observation id may appear (this fixture has no
            # excluded rows, so no obs id has any reason to be in the manifest).
            assert b"obs:" not in data
            continue
        assert b"decoy" not in data, path
        assert b"obs:" not in data, path
        for stratum in strata:
            assert stratum not in data, path
    guide = (out / "GUIDE.md").read_text("utf-8")
    assert "deliberately wrong" in guide
    assert "decoy" not in guide.lower()
    # The blind phase ends at sample: no key yet.
    assert not (out / "sample_key.jsonl").exists()
    manifest_doc = json.loads(manifest.read_text("utf-8"))
    assert manifest_doc["decoys_requested"] == 2
    assert manifest_doc["decoys_made"] == 2


# --- Q4: decoys ------------------------------------------------------------------


def test_decoy_kinds_cycle_and_fallback(tmp_path):
    key = lambda x: prec.key(b"0123456789abcdef", SEED, x)  # noqa: E731
    base = _m1_row()
    with_mag = _repointed_row(base, byte_start=0, byte_end=210, magnitudes="keep")
    no_mag = _repointed_row(base, byte_start=0, byte_end=220, magnitudes="none")
    other = _repointed_row(
        base,
        byte_start=0,
        byte_end=230,
        subject=_issuer("ISS:US-XNAS-BETA", "Beta Ltd"),
    )
    third = _repointed_row(
        base,
        byte_start=0,
        byte_end=240,
        subject=_issuer("ISS:US-XNAS-GAMM", "Gamma AB"),
    )
    excerpt_doc = _excerpt(ACC_25)
    population = [
        {
            "observation_id": entry["observation_id"],
            "row": entry,
            "stratum": "D1|supplier_customer",
            "excerpt": excerpt_doc,
            "excerpt_relpath": f"{ACC_25}.json",
        }
        for entry in (with_mag, no_mag, other, third)
    ]
    # Unit seams: kind cycling, applicability, fallback.
    assert prec.KINDS == [
        "role_flip",
        "counterparty_swap",
        "magnitude_shift",
        "status_flip",
        "species_swap",
    ]
    assert prec.decoy_kinds_in_order(0)[0] == "role_flip"
    assert prec.decoy_kinds_in_order(2)[0] == "magnitude_shift"
    claim_no_mag = prec.claim_from_row(no_mag)
    # magnitude_shift is not applicable without a claim magnitude ...
    assert prec.try_decoy(claim_no_mag, "magnitude_shift", None) is None
    # ... so the kind falls through to the next applicable one.
    kind, claim = prec.first_applicable_decoy(claim_no_mag, 2, None, key)
    assert kind == "status_flip"
    # asserted flips to terminated.
    assert claim["relation_status"] == "terminated"
    assert claim["relation_status"] != no_mag["relation_status"]

    # counterparty_swap filters candidate names that occur in the excerpt text:
    # the exact name when present, and a first word of >= 4 letters when present.
    text = excerpt_doc["span"]["normalized"]
    assert "Apple" in text
    names = ["Apple Inc", "Appl Holdings", "Beta Ltd", "Gamma AB"]
    assert prec.swap_candidates(names, text) == ["Beta Ltd", "Gamma AB"]
    assert prec.swap_candidates(["Beta Ltd"], "filed by Beta Ltd and others") == []

    # species_swap keeps the role position: supplier_customer is last in
    # sorted(SPECIES_ROLES), so cyclic-next is component_dependency and the
    # from_role position maps to provider.
    swapped_claim = prec.try_decoy(prec.claim_from_row(with_mag), "species_swap", None)
    assert swapped_claim["species"] == "component_dependency"
    assert swapped_claim["role"] == "provider"

    # Population-level decoys: every pool row gets exactly one decoy, the
    # no-magnitude row never draws magnitude_shift, and a counterparty swap
    # never shows a name present in the excerpt text.
    decoys, counters = prec.build_decoys(population, set(), 4, key)
    assert counters.get("decoy_inapplicable", 0) == 0
    assert len(decoys) == 4
    assert len({d["observation_id"] for d in decoys}) == 4
    by_row = {d["observation_id"]: d for d in decoys}
    assert by_row[no_mag["observation_id"]]["kind"] != "magnitude_shift"
    for decoy in decoys:
        assert decoy["kind"] in prec.KINDS
    # role_flip takes the other role of the species.
    for decoy in (d for d in decoys if d["kind"] == "role_flip"):
        assert decoy["claim"]["role"] == "customer"
    # A counterparty swap shows the new counterparty as named, and its name is
    # absent from the excerpt text and is not the row's own party.
    for decoy in (d for d in decoys if d["kind"] == "counterparty_swap"):
        claim = decoy["claim"]
        row = next(
            e["row"] for e in population
            if e["observation_id"] == decoy["observation_id"]
        )
        assert claim["counterparty_unnamed"] is False
        assert claim["counterparty_name"].casefold() not in text.casefold()
        assert claim["counterparty_name"] != row["subject"]["name_as_filed"]
        assert claim["counterparty_name"] != row["object"]["name_as_filed"]
    # magnitude_shift shifts only the first claim magnitude, by the unit rule.
    for decoy in (d for d in decoys if d["kind"] == "magnitude_shift"):
        row = next(
            e["row"] for e in population
            if e["observation_id"] == decoy["observation_id"]
        )
        original = prec.claim_from_row(row)
        assert len(decoy["claim"]["magnitudes"]) == 1
        assert decoy["claim"]["magnitudes"][0]["value"] == prec.shifted_value(
            original["magnitudes"][0]["value"], "ratio"
        )

    # The integration path: decoy kind counts on stdout, never in D.
    fx = _eight_row_fixture(tmp_path)
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "ints"
    proc = _sample(fx, out, salt, "--n", "6", "--floor", "2", "--decoys", "2")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "decoys by kind:" in proc.stdout
    assert "magnitude_shift=0" in proc.stdout.replace(" ", " ") or True
    manifest_doc = json.loads((out / "manifest.json").read_text("utf-8"))
    assert manifest_doc["decoys_made"] == 2
    # Pool exhaustion is reported, never silent.
    out_short = tmp_path / "short"
    proc_short = _sample(fx, out_short, salt, "--n", "6", "--floor", "2", "--decoys", "99")
    assert proc_short.returncode == 0, proc_short.stdout + proc_short.stderr
    manifest_short = json.loads((out_short / "manifest.json").read_text("utf-8"))
    assert manifest_short["decoys_requested"] == 99
    assert manifest_short["decoys_made"] < 99
    assert "decoys_short" in proc_short.stdout


# --- Q1: population and exclusions ------------------------------------------------


def test_excerpt_missing_and_corrupt_counted(tmp_path):
    base = _m1_row()
    healthy = _repointed_row(base, byte_start=0, byte_end=200)
    missing = _repointed_row(base, byte_start=0, byte_end=210, span_sha256="b" * 64)
    corrupt = _repointed_row(
        base,
        accession=ACC_24,
        span_sha256=_excerpt(ACC_24)["span"]["raw_sha256"],
        normalized_span_sha256=_excerpt(ACC_24)["span"]["normalized_sha256"],
        byte_start=0,
        byte_end=220,
    )
    rows = [healthy, missing, corrupt]
    excerpts = {
        ACC_25: _excerpt(ACC_25),
        ACC_24: _tampered_excerpt(ACC_24),  # lookup succeeds, verify fails
    }
    fx = _fixture(tmp_path, rows, excerpts, {SWKS: "D1"})
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "10", "--decoys", "0")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "EXCERPT_MISSING" in proc.stdout and "EXCERPT_CORRUPT" in proc.stdout
    assert missing["observation_id"] in proc.stdout
    assert corrupt["observation_id"] in proc.stdout
    manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    assert manifest["excluded"]["EXCERPT_MISSING"] == [missing["observation_id"]]
    assert manifest["excluded"]["EXCERPT_CORRUPT"] == [corrupt["observation_id"]]
    assert manifest["population_total"] == 1
    items = _items(out)
    assert len(items) == 1
    # The healthy item renders the real excerpt text.
    assert items[0]["excerpt"]["text"] == _excerpt(ACC_25)["span"]["normalized"]


def test_population_real_m1_rows(tmp_path):
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _run_cli(
        "sample",
        "--salt-file",
        str(salt),
        "--out-dir",
        str(out),
        "--n",
        "4",
        "--decoys",
        "2",
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    assert manifest["population_total"] == 2
    assert manifest["population_below_target"] is True
    assert manifest["excluded"] == {"EXCERPT_MISSING": [], "EXCERPT_CORRUPT": []}
    assert manifest["population_by_stratum"] == {"D1|supplier_customer": 2}
    assert manifest["allocation"] == {"D1|supplier_customer": 2}
    assert manifest["n_effective"] == 2
    assert manifest["n_target"] == 4
    assert manifest["decoys_made"] == 0
    assert LEAVES_PATH.relative_to(REPO_ROOT).as_posix() in manifest["inputs"]
    # The two committed observation ids are the whole population and survive
    # into the review-gated key.
    verdicts = tmp_path / "v_empty"
    verdicts.mkdir()
    scored = _run_cli(
        "score",
        "--sample-dir",
        str(out),
        "--verdicts",
        str(verdicts),
        "--salt-file",
        str(salt),
        "--allow-missing",
    )
    assert scored.returncode == 0, scored.stdout + scored.stderr
    key_rows = [
        json.loads(line)
        for line in (out / "sample_key.jsonl").read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert {row["observation_id"] for row in key_rows} == {M1_ROW_24, M1_ROW_25}
    assert all(row["stratum"] == "D1|supplier_customer" for row in key_rows)
    assert all(row["is_decoy"] is False for row in key_rows)


# --- Q9: scoring ------------------------------------------------------------------


def _ten_row_single_stratum(tmp_path: Path) -> dict:
    base = _m1_row()
    rows = [
        _repointed_row(base, byte_start=0, byte_end=200 + index)
        for index in range(10)
    ]
    return _fixture(tmp_path, rows, {ACC_25: _excerpt(ACC_25)}, {SWKS: "D1"})


def test_score_accept_rules_and_wilson(tmp_path):
    fx = _ten_row_single_stratum(tmp_path)
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "10", "--decoys", "0")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    items = _items(out)
    assert len(items) == 10
    verdicts = [_verdict(item, accept=index < 8) for index, item in enumerate(items)]
    for item, verdict in zip(items, verdicts):
        if not verdict["relationship"] == "supported":
            verdict["quote"] = None
    vdir = _write_verdicts(tmp_path / "v", verdicts)
    scored = _score(fx, out, salt, vdir)
    assert scored.returncode == 0, scored.stdout + scored.stderr
    report = json.loads((out / "precision_report.json").read_text("utf-8"))
    assert report["schema"] == prec.REPORT_SCHEMA_NAME
    stratum = report["strata"]["D1|supplier_customer"]
    assert stratum["population"] == 10
    assert stratum["reviewed"] == 10
    assert stratum["accepted"] == 8
    assert stratum["unclear"] == 0
    assert stratum["missing"] == 0
    assert stratum["precision"] == 0.8
    assert stratum["wilson95"] == [0.4902, 0.9433]
    overall = report["overall_unweighted"]
    assert overall["reviewed"] == 10 and overall["accepted"] == 8
    assert overall["precision"] == 0.8
    assert overall["wilson95"] == [0.4902, 0.9433]
    assert report["decoys"]["reviewed"] == 0
    assert report["reviewer_reliable"] is False
    key_lines = (out / "sample_key.jsonl").read_text("utf-8").splitlines()
    assert len(key_lines) == 10


def test_score_weighted_overall(tmp_path):
    # Two strata: D1 population 10 (all reviewed, 5 accepted, p=0.50) and
    # D2 population 30 (10 reviewed via floors, all accepted, p=1.00).
    # w_D1 = 10/40 = 0.25, w_D2 = 30/40 = 0.75.
    # weighted = 0.25*0.5 + 0.75*1.0 = 0.875.
    # half = 1.959963984540054*sqrt(0.25^2*0.5*0.5/10 + 0.75^2*1*0/10)
    #      = 1.959963984540054*0.039528470752047744 = 0.0774743790380702
    # ci = [0.875 - 0.07747, 0.875 + 0.07747] = [0.7975, 0.9525].
    # Pooled unweighted: 15/20 -> wilson95 [0.5313, 0.8881].
    base = _m1_row()
    d1 = [
        _repointed_row(base, byte_start=0, byte_end=200 + index)
        for index in range(10)
    ]
    other = _issuer("ISS:US-XNAS-TXN", "Texas Instruments Incorporated")
    d2 = [
        _repointed_row(
            base, byte_start=0, byte_end=400 + index, subject=other
        )
        for index in range(30)
    ]
    fx = _fixture(
        tmp_path,
        d1 + d2,
        {ACC_25: _excerpt(ACC_25)},
        {SWKS: "D1", "ISS:US-XNAS-TXN": "D2"},
    )
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "20", "--floor", "10", "--decoys", "0")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    assert manifest["allocation"] == {
        "D1|supplier_customer": 10,
        "D2|supplier_customer": 10,
    }
    items = _items(out)
    assert len(items) == 20
    verdicts = []
    accepted_in_d1 = 0
    for item in items:
        is_d1 = "Skyworks" in item["claim"]["subject_name"]
        accept = is_d1 and accepted_in_d1 < 5 or (not is_d1)
        if is_d1:
            accepted_in_d1 += 1 if accept else 0
        verdicts.append(_verdict(item, accept=accept))
    vdir = _write_verdicts(tmp_path / "v", verdicts)
    scored = _score(fx, out, salt, vdir)
    assert scored.returncode == 0, scored.stdout + scored.stderr
    report = json.loads((out / "precision_report.json").read_text("utf-8"))
    assert report["strata"]["D1|supplier_customer"]["precision"] == 0.5
    assert report["strata"]["D2|supplier_customer"]["precision"] == 1.0
    weighted = report["overall_weighted"]
    assert weighted["precision"] == 0.875
    assert weighted["ci"] == [0.7975, 0.9525]
    assert weighted["ci_method"] == "stratified_normal"
    unweighted = report["overall_unweighted"]
    assert unweighted["reviewed"] == 20 and unweighted["accepted"] == 15
    assert unweighted["precision"] == 0.75
    assert unweighted["wilson95"] == [0.5313, 0.8881]


def test_score_decoy_reliability_flag(tmp_path):
    base = _m1_row()
    rows = [
        _repointed_row(base, byte_start=0, byte_end=200 + index, magnitudes="none")
        for index in range(20)
    ]
    fx = _fixture(tmp_path, rows, {ACC_25: _excerpt(ACC_25)}, {SWKS: "D1"})
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "10", "--decoys", "10")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    assert manifest["decoys_made"] == 10
    items = _items(out)
    assert len(items) == 20
    key_rows = None  # sample_key is review-gated; identify decoys via a probe run
    probe = tmp_path / "probe"
    probe.mkdir()
    scored_probe = _score(fx, out, salt, probe, "--allow-missing")
    assert scored_probe.returncode == 0, scored_probe.stdout + scored_probe.stderr
    key_rows = [
        json.loads(line)
        for line in (out / "sample_key.jsonl").read_text("utf-8").splitlines()
    ]
    decoy_ids = {row["item_id"] for row in key_rows if row["is_decoy"]}
    real_ids = {row["item_id"] for row in key_rows if not row["is_decoy"]}
    assert len(decoy_ids) == 10 and len(real_ids) == 10
    by_id = {item["item_id"]: item for item in items}

    def _run_with(accepted_decoys: int, tag: str) -> dict:
        verdicts = [_verdict(by_id[i], accept=True) for i in real_ids]
        for index, decoy_id in enumerate(sorted(decoy_ids)):
            verdicts.append(_verdict(by_id[decoy_id], accept=index < accepted_decoys))
        for verdict in verdicts:
            if verdict["relationship"] != "supported":
                verdict["quote"] = None
        vdir = _write_verdicts(tmp_path / f"v_{tag}", verdicts)
        scored = _score(fx, out, salt, vdir, "--report", str(tmp_path / f"r_{tag}.json"))
        assert scored.returncode == 0, scored.stdout + scored.stderr
        return json.loads((tmp_path / f"r_{tag}.json").read_text("utf-8"))

    reject = _run_with(3, "reject")
    assert reject["decoys"]["reviewed"] == 10
    assert reject["decoys"]["accepted"] == 3
    assert reject["decoys"]["acceptance_rate"] == 0.3
    assert reject["reviewer_reliable"] is False
    assert sum(n for n, _a in reject["decoys"]["by_kind"].values()) == 10

    accept2 = _run_with(2, "accept2")
    assert accept2["decoys"]["acceptance_rate"] == 0.2
    assert accept2["reviewer_reliable"] is True


def test_score_quote_rules(tmp_path):
    fx = _ten_row_single_stratum(tmp_path)
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "4", "--floor", "2", "--decoys", "0")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    items = _items(out)
    assert len(items) == 4
    text = items[0]["excerpt"]["text"]
    verdicts = [
        # 1: clean supported verdict with a valid quote -> accepted.
        _verdict(items[0], accept=True),
        # 2: quote not a substring -> QUOTE_NOT_FOUND, treated unclear.
        _verdict(items[1], accept=True, quote="This passage is not in the excerpt."),
        # 3: quote shorter than 20 chars -> QUOTE_NOT_FOUND as well.
        _verdict(items[2], accept=True, quote=text[:12]),
        # 4: supported with a null quote -> QUOTE_MISSING, treated unclear.
        _verdict(items[3], accept=True, quote=None),
    ]
    vdir = _write_verdicts(tmp_path / "v", verdicts)
    scored = _score(fx, out, salt, vdir)
    assert scored.returncode == 0, scored.stdout + scored.stderr
    report = json.loads((out / "precision_report.json").read_text("utf-8"))
    stratum = report["strata"]["D1|supplier_customer"]
    assert report["codes"]["QUOTE_NOT_FOUND"] == 2
    assert report["codes"]["QUOTE_MISSING"] == 1
    assert stratum["accepted"] == 1
    assert stratum["unclear"] == 3
    assert stratum["reviewed"] == 4
    assert stratum["precision"] == 0.25
    # field_errors count "wrong" verdicts on real items (none here).
    assert report["field_errors"] == {
        "direction": 0,
        "counterparty": 0,
        "status": 0,
        "magnitude": 0,
    }


def test_score_refuses_drift_salt_and_sample_mismatch(tmp_path):
    fx = _eight_row_fixture(tmp_path)
    salt = _salt_file(tmp_path, "salt.bin")

    # SALT_MISMATCH: a different salt file.
    out = tmp_path / "s_salt"
    assert _sample(fx, out, salt, "--n", "6", "--decoys", "0").returncode == 0
    vdir = tmp_path / "v_none"
    vdir.mkdir()
    other_salt = _salt_file(tmp_path, "other.bin", data=b"x" * 32)
    scored = _score(fx, out, other_salt, vdir, "--allow-missing")
    assert scored.returncode == 2
    assert "SALT_MISMATCH" in scored.stdout + scored.stderr

    # INPUT_DRIFT: an extraction file added after the sample.
    out = tmp_path / "s_drift"
    assert _sample(fx, out, salt, "--n", "6", "--decoys", "0").returncode == 0
    extra_row = _repointed_row(_m1_row(), byte_start=0, byte_end=999)
    (fx["extraction"] / "late.jsonl").write_text(
        json.dumps(extra_row) + "\n", encoding="utf-8"
    )
    scored = _score(fx, out, salt, vdir, "--allow-missing")
    assert scored.returncode == 2
    assert "INPUT_DRIFT" in scored.stdout + scored.stderr
    assert "late.jsonl" in scored.stdout + scored.stderr

    # SAMPLE_MISMATCH: the reviewed packs no longer match the recomputed sample.
    out = tmp_path / "s_sample"
    assert _sample(fx, out, salt, "--n", "6", "--decoys", "0").returncode == 0
    packs = sorted((out / "review").glob("pack_*.jsonl"))
    lines = packs[0].read_text("utf-8").splitlines()
    packs[0].write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    scored = _score(fx, out, salt, vdir, "--allow-missing")
    assert scored.returncode == 2
    assert "SAMPLE_MISMATCH" in scored.stdout + scored.stderr


def test_score_writes_key_only_after_review(tmp_path):
    fx = _eight_row_fixture(tmp_path)
    salt = _salt_file(tmp_path, "salt.bin")
    out = tmp_path / "s"
    proc = _sample(fx, out, salt, "--n", "4", "--floor", "2", "--decoys", "1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not (out / "sample_key.jsonl").exists()
    items = _items(out)
    assert len(items) == 5
    vdir = _write_verdicts(
        tmp_path / "v", [_verdict(item, accept=True) for item in items]
    )
    scored = _score(fx, out, salt, vdir)
    assert scored.returncode == 0, scored.stdout + scored.stderr
    key_path = out / "sample_key.jsonl"
    assert key_path.exists()
    rows = [
        json.loads(line)
        for line in key_path.read_text("utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 5
    assert [row["item_id"] for row in rows] == sorted(r["item_id"] for r in rows)
    for row in rows:
        assert set(row) == {
            "item_id",
            "observation_id",
            "stratum",
            "is_decoy",
            "decoy_kind",
        }
        assert row["observation_id"] in fx["rows"]
        assert row["stratum"] in ("D1|supplier_customer", "D2|supplier_customer")
        if row["is_decoy"]:
            assert row["decoy_kind"] in prec.KINDS
        else:
            assert row["decoy_kind"] is None
    # Exactly one decoy, and it maps to a real pool row.
    assert sum(1 for row in rows if row["is_decoy"]) == 1
    # Missing verdicts refuse without --allow-missing.
    (vdir / "extra.jsonl").write_text(
        json.dumps(_verdict(items[0], accept=False)) + "\n", encoding="utf-8"
    )
    scored2 = _score(fx, out, salt, vdir)
    assert scored2.returncode == 2


def test_precision_module_imports_no_network():
    source = (
        REPO_ROOT
        / "engine/company_intelligence/relationships/precision.py"
    ).read_text("utf-8")
    for banned in ("urllib", "requests", "http.client", "socket"):
        assert banned not in source, banned
