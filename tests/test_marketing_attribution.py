"""tests/test_marketing_attribution.py — UTM attribution join tests (docket D07 W1b).

Test list:
1. test_user_ref_opaque_deterministic
2. test_parse_utm_flat_nested_absent
3. test_load_signups_strips_pii
4. test_join_matched_and_unmatched
5. test_append_ledger_dedup
6. test_ledger_no_pii_bytes
7. test_posts_index_outbox_seam
8. test_trial_to_paid_passthrough
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from engine.marketing.attribution import join_attribution, load_signups, parse_utm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _worktree_root() -> Path:
    p = Path(__file__).resolve()
    for candidate in [p.parent, p.parent.parent, p.parent.parent.parent]:
        if (candidate / "engine").is_dir():
            return candidate
    raise RuntimeError(f"Could not locate repo root from {p}")


ROOT = _worktree_root()
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "marketing" / "signups_sample.json"

# Minimal content-plan dict whose queue items cover the two matched post ids.
_MINIMAL_PLAN = {
    "accounts": [
        {
            "id": "flagship",
            "queue": [
                {"id": "post-flagship-001", "account": "flagship", "type": "signal"},
                {"id": "post-conf-flagship-001", "account": "flagship", "type": "signal"},
            ],
        }
    ]
}

# Expected complete key set for every ledger row.
_EXPECTED_ROW_KEYS = {
    "schema",
    "schema_version",
    "user_ref",
    "signup_at",
    "plan",
    "trial_to_paid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "post_id",
    "account",
    "kind",
    "matched",
}


# ---------------------------------------------------------------------------
# 1. user_ref: deterministic, opaque, 18 chars, raw id not present in output
# ---------------------------------------------------------------------------

def test_user_ref_opaque_deterministic():
    from engine.marketing.attribution import user_ref

    ref1 = user_ref("sb_001")
    ref2 = user_ref("sb_001")

    assert ref1 == ref2, "user_ref must be deterministic"
    assert ref1.startswith("u_"), "user_ref must start with 'u_'"
    assert len(ref1) == 18, f"user_ref must be 18 chars, got {len(ref1)}: {ref1!r}"
    assert "sb_001" not in ref1, "raw id must not appear in user_ref output"


# ---------------------------------------------------------------------------
# 2. parse_utm: flat, nested, flat-beats-nested, absent
# ---------------------------------------------------------------------------

def test_parse_utm_flat_nested_absent():
    from engine.marketing.attribution import parse_utm, _UTM_KEYS

    # Flat record
    flat = {
        "utm_source": "x",
        "utm_medium": "flagship",
        "utm_campaign": "signal",
        "utm_content": "post-flagship-001",
    }
    result = parse_utm(flat)
    assert result["utm_source"] == "x"
    assert result["utm_medium"] == "flagship"
    assert result["utm_campaign"] == "signal"
    assert result["utm_content"] == "post-flagship-001"

    # Nested record
    nested = {
        "utm": {
            "utm_source": "twitter",
            "utm_medium": "receipts",
            "utm_campaign": "conf",
            "utm_content": "post-conf-flagship-001",
        }
    }
    result2 = parse_utm(nested)
    assert result2["utm_source"] == "twitter"
    assert result2["utm_content"] == "post-conf-flagship-001"

    # Flat beats nested on conflict
    conflict = {
        "utm_content": "post-flat-winner",
        "utm": {"utm_content": "post-nested-loser"},
    }
    result3 = parse_utm(conflict)
    assert result3["utm_content"] == "post-flat-winner"

    # Absent — all None
    absent = {"id": "x"}
    result4 = parse_utm(absent)
    assert set(result4.keys()) == set(_UTM_KEYS)
    assert all(v is None for v in result4.values()), f"Expected all None, got {result4}"

    # Empty string → None
    empty_str = {"utm_content": "   "}
    result5 = parse_utm(empty_str)
    assert result5["utm_content"] is None


# ---------------------------------------------------------------------------
# 3. load_signups: PII stripped, no-id record dropped, jsonl path
# ---------------------------------------------------------------------------

def test_load_signups_strips_pii(tmp_path):
    from engine.marketing.attribution import load_signups

    # Load the real fixture
    records = load_signups(FIXTURE_PATH)

    # PII "email" must be absent from every record
    for rec in records:
        assert "email" not in rec, f"PII key 'email' leaked into record: {rec}"

    # Record 6 (no id, no user_id) must be dropped → 5 records remain
    assert len(records) == 5, (
        f"Expected 5 records after dropping no-id record, got {len(records)}"
    )

    # JSONL path: write two records into tmp_path and load
    jsonl_path = tmp_path / "test.jsonl"
    jsonl_path.write_text(
        json.dumps({"id": "j1", "utm_content": "p1", "email": "should@strip.com"}) + "\n"
        + "\n"  # blank line must be skipped
        + json.dumps({"user_id": "j2", "plan": "pro"}) + "\n",
        encoding="utf-8",
    )
    jl_records = load_signups(jsonl_path)
    assert len(jl_records) == 2
    assert "email" not in jl_records[0]


# ---------------------------------------------------------------------------
# 4. join_attribution: matched/unmatched, key set, index truth wins
# ---------------------------------------------------------------------------

def test_join_matched_and_unmatched():
    from engine.marketing.attribution import load_signups, posts_index, join_attribution

    records = load_signups(FIXTURE_PATH)
    index = posts_index(_MINIMAL_PLAN)
    rows = join_attribution(records, index)

    # Should produce one row per loaded record (5 rows)
    assert len(rows) == 5, f"Expected 5 rows, got {len(rows)}"

    # Every row must have exactly the full expected key set
    for row in rows:
        assert set(row.keys()) == _EXPECTED_ROW_KEYS, (
            f"Row key mismatch: {set(row.keys()) ^ _EXPECTED_ROW_KEYS}"
        )

    # Records 1 and 2 (sb_001 and sb_002) are matched
    matched_rows = [r for r in rows if r["matched"]]
    assert len(matched_rows) == 3, (
        # Record 5 is a duplicate of record 1 — still in join output (dedup happens in append)
        f"Expected 3 matched rows (sb_001 x2 + sb_002), got {len(matched_rows)}"
    )

    # Index truth: post_id, account, kind come from index for matched rows
    flagship_001_rows = [r for r in matched_rows if r["post_id"] == "post-flagship-001"]
    assert flagship_001_rows, "Expected at least one matched row for post-flagship-001"
    for row in flagship_001_rows:
        assert row["account"] == "flagship"
        assert row["kind"] == "signal"

    conf_rows = [r for r in matched_rows if r["post_id"] == "post-conf-flagship-001"]
    assert conf_rows, "Expected matched row for post-conf-flagship-001"
    assert conf_rows[0]["account"] == "flagship"
    assert conf_rows[0]["kind"] == "signal"

    # Ghost post (sb_003) and organic (sb_004) must be unmatched with post_id=None
    unmatched = [r for r in rows if not r["matched"]]
    for row in unmatched:
        assert row["post_id"] is None
        assert row["account"] is None
        assert row["kind"] is None


# ---------------------------------------------------------------------------
# 5. append_ledger: dedup on second call, file line count unchanged
# ---------------------------------------------------------------------------

def test_append_ledger_dedup(tmp_path):
    from engine.marketing.attribution import load_signups, posts_index, join_attribution, append_ledger

    records = load_signups(FIXTURE_PATH)
    index = posts_index(_MINIMAL_PLAN)
    rows = join_attribution(records, index)

    ledger = tmp_path / "ledger.jsonl"

    result1 = append_ledger(rows, path=ledger)
    assert result1["appended"] > 0
    line_count_after_first = len(ledger.read_text(encoding="utf-8").strip().splitlines())

    # Second identical call: nothing new appended
    result2 = append_ledger(rows, path=ledger)
    assert result2["appended"] == 0, (
        f"Second call must append 0 rows, got appended={result2['appended']}"
    )
    assert result2["skipped_duplicates"] > 0

    # File line count must be unchanged
    line_count_after_second = len(ledger.read_text(encoding="utf-8").strip().splitlines())
    assert line_count_after_first == line_count_after_second, (
        f"Line count changed after dedup pass: {line_count_after_first} → {line_count_after_second}"
    )

    # Every line in the file must parse as JSON
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)  # raises on malformed
        assert isinstance(obj, dict)


# ---------------------------------------------------------------------------
# 6. No PII bytes in ledger after end-to-end build_attribution
# ---------------------------------------------------------------------------

def test_ledger_no_pii_bytes(tmp_path):
    from engine.marketing.attribution import build_attribution

    ledger = tmp_path / "attr_ledger.jsonl"
    build_attribution(FIXTURE_PATH, _MINIMAL_PLAN, ledger_path=ledger)

    raw_bytes = ledger.read_bytes()
    assert b"leak@example.com" not in raw_bytes, "PII email address found in ledger bytes"
    assert b'"email"' not in raw_bytes, "PII key 'email' found in ledger bytes"


# ---------------------------------------------------------------------------
# 7. posts_index: outbox-seam (plain list with "kind" key)
# ---------------------------------------------------------------------------

def test_posts_index_outbox_seam():
    from engine.marketing.attribution import posts_index

    outbox_items = [
        {"id": "post-flagship-001", "account": "flagship", "kind": "signal"},
        {"id": "post-conf-flagship-001", "account": "flagship", "kind": "signal"},
        {"id": "post-mover-001", "account": "research_b", "kind": "mover"},
        {"account": "orphan"},  # no id — must be skipped
    ]

    index = posts_index(outbox_items)

    assert "post-flagship-001" in index
    assert index["post-flagship-001"]["account"] == "flagship"
    assert index["post-flagship-001"]["kind"] == "signal"

    assert "post-mover-001" in index
    assert index["post-mover-001"]["kind"] == "mover"

    # Item without id must not appear
    assert len(index) == 3, f"Expected 3 entries, got {len(index)}: {list(index.keys())}"


# ---------------------------------------------------------------------------
# 8. trial_to_paid passthrough: true and None survive into rows
# ---------------------------------------------------------------------------

def test_trial_to_paid_passthrough():
    from engine.marketing.attribution import load_signups, posts_index, join_attribution

    records = load_signups(FIXTURE_PATH)
    index = posts_index(_MINIMAL_PLAN)
    rows = join_attribution(records, index)

    # sb_002 has trial_to_paid=true
    sb002_ref_candidates = [
        r for r in rows
        if r.get("utm_content") == "post-conf-flagship-001"
    ]
    assert sb002_ref_candidates, "sb_002 row not found by utm_content"
    assert sb002_ref_candidates[0]["trial_to_paid"] is True, (
        f"Expected trial_to_paid=True for sb_002, got {sb002_ref_candidates[0]['trial_to_paid']}"
    )

    # sb_001 has trial_to_paid=null (JSON null → Python None)
    # Records 1 and 5 are both sb_001 (duplicate); both should have None
    sb001_rows = [
        r for r in rows
        if r.get("post_id") == "post-flagship-001"
        and r.get("utm_campaign") == "signal"
    ]
    assert sb001_rows, "sb_001 rows not found"
    for row in sb001_rows:
        assert row["trial_to_paid"] is None, (
            f"Expected trial_to_paid=None for sb_001, got {row['trial_to_paid']!r}"
        )


# Landing controller -> Supabase signup metadata -> existing D07 join.
# Offline contract: actual controller code, mocked storage/auth/render I/O.
# This does not claim a real signup, verification email, or nightly ingestion.
UTM = {"utm_source": "x", "utm_medium": "flagship", "utm_campaign": "signal",
       "utm_content": "post-flagship-001"}
QUERY = "?" + "&".join(f"{key}={value}" for key, value in UTM.items())

HARNESS = r"""
const fs = require('node:fs'), vm = require('node:vm');
const args = JSON.parse(fs.readFileSync(0, 'utf8'));
const source = fs.readFileSync(args.source, 'utf8');
const stored = new Map(Object.entries(args.stored || {}));
let requests = [], transitions = [], removed = [];
async function page(search, mode = 'signup', changedSearch) {
  const storage = {
    getItem(k) { if (args.blocked) throw Error('storage denied'); return stored.get(k) || null; },
    setItem(k,v) { if (args.blocked) throw Error('storage denied'); stored.set(k,v); },
    removeItem(k) { if (args.blocked) throw Error('storage denied'); removed.push(k); stored.delete(k); }
  };
  const location = {search, pathname:'/', hash:'', hostname:'www.mastermind-x.com'};
  const document = {readyState:'loading', cookie:'', addEventListener(){},
    querySelector(){return null;}, getElementById(){return null;},
    documentElement:{getAttribute(){return 'light';}, setAttribute(){}, classList:{remove(){}}}};
  const context = {console, URLSearchParams, URL, location, document,
    localStorage:storage, sessionStorage:storage,
    fetch:async()=>({ok:false}), setTimeout, clearTimeout,
    __auth: {auth:{
      signUp:async o=>{requests.push(o); return {data:{session:null}};},
      signInWithPassword:async o=>{requests.push({signin:o});return {data:{session:{}}};}
    }}, __transitions:transitions};
  context.window = context;
  const seam = `
    showErr=function(){};setSubmitBusy=function(){};
    go=function(step){S.step=step;__transitions.push({step,confirmPending:S.confirmPending});};
    sbClient=function(){return Promise.resolve(__auth);};authEnabled=function(){return true;};
    window.__submit=function(mode){S.mode=mode;S.email='reader@example.com';S.password='synthetic-password';
      S.firstName='Synthetic';S.lastName='Reader';onAccountSubmit({preventDefault(){}});};
  `;
  const end = source.lastIndexOf('})();');
  vm.runInNewContext(source.slice(0,end)+seam+source.slice(end), context);
  if (changedSearch !== undefined) location.search = changedSearch;
  context.__submit(mode);
  await new Promise(resolve=>setImmediate(resolve));
}
(async()=>{
  for (const visit of args.visits) await page(visit.search, visit.mode, visit.changedSearch);
  process.stdout.write(JSON.stringify({requests,transitions,stored:Object.fromEntries(stored),removed}));
})().catch(e=>{console.error(e);process.exit(1);});
"""


def controller(visits, **extra):
    result = subprocess.run(
        ["node", "-e", HARNESS], input=json.dumps({"source": str(ROOT / "templates/onboard.js"),
                                                  "visits": visits, **extra}),
        text=True, capture_output=True, check=True,
    )
    return json.loads(result.stdout)


def test_landing_signup_metadata_joins_actual_supabase_export(tmp_path):
    result = controller([{"search": QUERY, "changedSearch": "?onboard=resume&code=synthetic"}])
    data = result["requests"][0]["options"]["data"]
    assert data == {"first_name": "Synthetic", "last_name": "Reader", "utm": UTM}
    assert result["transitions"] == [{"step": 2, "confirmPending": True}]
    path = tmp_path / "supabase-users.json"
    path.write_text(json.dumps([{"id": "opaque-account-1", "email": "reader@example.com",
                                "created_at": "2026-10-24T00:00:00Z",
                                "raw_user_meta_data": data}]))
    rows = join_attribution(load_signups(path), {
        "post-flagship-001": {"account": "authoritative-account", "kind": "authoritative-kind"}})
    assert rows[0]["matched"] is True
    assert rows[0]["account"] == "authoritative-account"
    assert rows[0]["kind"] == "authoritative-kind"
    assert rows[0]["signup_at"] == "2026-10-24T00:00:00Z"
    assert rows[0]["plan"] is None and rows[0]["trial_to_paid"] is None
    for private in ("reader@example.com", "Synthetic", "Reader", "synthetic-password", "code=", "opaque-account-1"):
        assert private not in json.dumps(rows)


def test_first_touch_survives_reload_and_verification_return_without_overwrite():
    result = controller([{"search": QUERY}, {"search": "?onboard=resume&code=synthetic"},
                         {"search": QUERY.replace("flagship", "later-account")}])
    assert [r["options"]["data"]["utm"] for r in result["requests"]] == [UTM] * 3


@pytest.mark.parametrize("query", ["", "?utm_source=x", QUERY.replace("=x&", "=a%40b.com&"),
                                  QUERY + "&utm_source=other", QUERY.replace("=x&", "=" + "a" * 129 + "&"),
                                  QUERY.replace("=x&", "=https%3A%2F%2Fprivate.example&"),
                                  QUERY.replace("=x&", "=x%0A&")],
                         ids=["absent", "partial", "email", "duplicate", "oversized", "url", "newline"])
def test_invalid_or_absent_touch_adds_no_attribution(query):
    result = controller([{"search": query}])
    assert "utm" not in result["requests"][0]["options"]["data"]


def test_storage_denial_keeps_signup_working_with_in_memory_touch():
    result = controller([{"search": QUERY}], blocked=True)
    assert result["requests"][0]["options"]["data"]["utm"] == UTM
    assert result["stored"] == {}


def test_incomplete_campaigns_are_never_mixed():
    result = controller([{"search": "?utm_source=old&utm_medium=old"},
                         {"search": "?utm_campaign=new&utm_content=new"},
                         {"search": QUERY}])
    assert all("utm" not in r["options"]["data"] for r in result["requests"][:2])
    assert result["requests"][2]["options"]["data"]["utm"] == UTM


@pytest.mark.parametrize("invalid", ["not-json", "[]", "null", '"string"',
                                      json.dumps({**UTM, "email": "private@example.com"}),
                                      json.dumps({"utm_source": "x"}), "x" * 3000],
                         ids=["bad-json", "array", "null", "string", "unknown-field", "partial", "oversized"])
def test_invalid_stored_touch_is_cleared_and_replaced_atomically(invalid):
    result = controller([{"search": QUERY}], stored={"mm.firstTouchUtm": invalid})
    assert result["requests"][0]["options"]["data"]["utm"] == UTM
    assert "mm.firstTouchUtm" in result["removed"]
    assert json.loads(result["stored"]["mm.firstTouchUtm"]) == UTM


def test_unknown_query_metadata_is_never_copied_and_signin_has_no_metadata():
    result = controller([{"search": QUERY + "&email=private%40example.com&plan=pro&access_token=synthetic"},
                         {"search": QUERY, "mode": "signin"}])
    assert result["requests"][0]["options"]["data"]["utm"] == UTM
    assert "options" not in result["requests"][1]
    assert "private@example.com" not in json.dumps(result["stored"])


def test_metadata_is_one_validated_touch_with_explicit_legacy_precedence():
    assert parse_utm({"raw_user_meta_data": {"utm": UTM}}) == UTM
    assert parse_utm({"user_metadata": {"utm": UTM}}) == UTM
    assert parse_utm({"utm_content": None, "raw_user_meta_data": {"utm": UTM}})["utm_content"] is None
    legacy = {"utm_content": "legacy-post"}
    assert parse_utm({"utm": legacy, "raw_user_meta_data": {"utm": UTM}})["utm_content"] == "legacy-post"
    for malformed in ([], "oops", None, {**UTM, "email": "private@example.com"},
                      {**UTM, "utm_source": "a" * 129}, {"utm_content": UTM["utm_content"]}):
        assert not any(parse_utm({"raw_user_meta_data": {"utm": malformed}}).values())
    for malformed in ([], "oops", True, None):
        assert not any(parse_utm({"raw_user_meta_data": malformed}).values())
    # A partial legacy touch and a malformed primary export cannot borrow fields
    # from another shape to invent a complete first touch.
    legacy_partial = parse_utm({"utm_source": "old", "raw_user_meta_data": {"utm": UTM}})
    assert legacy_partial["utm_source"] == "old" and legacy_partial["utm_content"] is None
    assert not any(parse_utm({"raw_user_meta_data": [], "user_metadata": {"utm": UTM}}).values())
