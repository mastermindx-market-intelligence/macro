# Mastermind AI Bilingual Research Search R1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing Research Vault catalog search accept meaningful Chinese, English single-term, ticker-only, full-width, and exact qualified-identifier queries without weakening relevance, rights, ranking, or fail-soft behavior.

**Architecture:** Extend only the private lexical normalization/token/match helpers and admission guard in `engine/neuralweb/brain_market_intel.py`. Unicode NFKC plus casefold normalizes harmless width/case differences; Han spans match literally, plain words match exact words, and qualified identifiers match complete atoms. Existing catalog ownership, scoring weights, report/clusters modes, quotas, entitlements, and result envelopes remain unchanged.

**Tech Stack:** Python 3.12-compatible standard library (`re`, `unicodedata`), pytest, existing Macro CI manifest and deploy restart gate.

**Spec:** `research/MASTERMIND_AI_BILINGUAL_RESEARCH_R1_DESIGN_2026-09-10.md`

## Global Constraints

- Operation key: `mastermind-ai-r1-lexical-retrieval-20260911-sol-001`.
- Base: `origin/main@1f8eeab603fc37def47e1cfc6f7f3788c0300ad3`; refresh and reconcile before push/merge.
- Modify only `engine/neuralweb/brain_market_intel.py` and `tests/test_brain_market_intel.py` for product behavior; the design and this plan are the only new documentation paths.
- Do not modify `engine/research_vault/*`, `app/research.py`, `.github/ci/legacy-jobs.yml`, the corpus/index, permissions, quotas, gateway, UI, model routing, signals, forecasts, or trade authority.
- Preserve existing search scoring weights, recency, stable tie-breaks, result projection, clusters mode, report mode, and fail-soft envelopes.
- NFKC/casefold is normalization only. Do not claim or implement cross-language semantic translation.
- Meaningful one-atom searches are admitted; zero-atom and one-character searches remain `query too short`.
- Qualified identifiers match complete atoms; natural-language hyphen compounds retain ordinary word matching.
- Use strict RED → GREEN → REFACTOR. Never write production behavior before observing the new tests fail on the pinned base.
- Do not run the repository-wide suite from this sparse worktree.

---

### Task 1: Freeze the multilingual and exact-identifier lexical contract

**Files:**
- Modify: `tests/test_brain_market_intel.py` in the existing Research Vault search section

**Interfaces:**
- Consumes: existing `_catalog`, `_note`, `_search`, `bmi._tokenize`, `bmi._hits`, and `bmi.search_research` test helpers.
- Produces: failing acceptance tests defining literal Chinese matching, one-term admission, NFKC normalization, exact identifier matching, natural hyphen behavior, and honest no-atom rejection.

- [ ] **Step 1: Replace the obsolete one-token rejection test with the honest no-atom boundary**

Replace `test_a_short_query_says_so_rather_than_faking_a_search` with:

```python
@pytest.mark.parametrize("query", ["", "   ", "!!!", "a", "中", None])
def test_a_query_with_no_meaningful_search_atom_says_so(tmp_path, query):
    _catalog(tmp_path, [_note("r", "Momentum Crowding Risk")])
    result = _search(tmp_path, query)
    assert result["results"] == []
    assert result["count_scanned"] == 0
    assert result["note"] == "query too short"
```

- [ ] **Step 2: Add failing one-term, Chinese, and full-width tests**

Add:

```python
@pytest.mark.parametrize(
    "query,title",
    [
        ("semiconductors", "Semiconductors Capital Spending Outlook"),
        ("AAPL", "AAPL Services Margin Outlook"),
        ("中国流动性", "中国流动性观察"),
        ("半导体", "中国半导体行业展望"),
        ("半導體", "台灣半導體產業展望"),
        ("ＡＡＰＬ", "AAPL Services Margin Outlook"),
    ],
)
def test_meaningful_single_term_and_chinese_queries_are_searchable(tmp_path, query, title):
    _catalog(tmp_path, [
        _note("hit", title),
        _note("decoy", "Japanese Government Bond Supply"),
    ])
    result = _search(tmp_path, query)
    assert [row["id"] for row in result["results"]] == ["hit"]
    assert result["count_scanned"] == 2
```

The `半导体` case deliberately matches inside the longer Han span `中国半导体行业展望`.

- [ ] **Step 3: Add failing exact-boundary decoy tests**

Add:

```python
@pytest.mark.parametrize(
    "query,hit,decoys",
    [
        ("AAPL", "AAPL Margin Outlook", ["Pineapple Demand Outlook", "XAAPLZ Supplier Note"]),
        ("AI", "AI Infrastructure Outlook", ["Paid Search Outlook", "Mainframe Demand"]),
        ("600036.SH", "600036.SH Deposit Repricing", ["600036.SZ Deposit Repricing", "1600036.SH Note", "600036.SH.A Note"]),
        ("BRK-B", "BRK-B Capital Allocation", ["BRK-A Capital Allocation", "BRK-BETA Factor Note"]),
    ],
)
def test_single_terms_and_identifiers_do_not_match_larger_or_sibling_atoms(tmp_path, query, hit, decoys):
    items = [_note("hit", hit)] + [_note(f"d{index}", title) for index, title in enumerate(decoys)]
    _catalog(tmp_path, items)
    assert [row["id"] for row in _search(tmp_path, query)["results"]] == ["hit"]
```

- [ ] **Step 4: Add a failing natural-hyphen regression test**

Add:

```python
@pytest.mark.parametrize(
    "query,title",
    [
        ("near-term", "Near Term Inflation Outlook"),
        ("long-term", "Long Term Growth Risks"),
        ("risk-off", "Risk Off Market Playbook"),
        ("AI-driven", "AI Driven Capital Spending"),
    ],
)
def test_natural_hyphenated_research_terms_keep_word_matching(tmp_path, query, title):
    _catalog(tmp_path, [_note("hit", title), _note("decoy", "Unrelated Note")])
    assert [row["id"] for row in _search(tmp_path, query)["results"]] == ["hit"]
```

- [ ] **Step 5: Add deterministic tokenization assertions**

Add:

```python
def test_tokenize_normalizes_width_deduplicates_and_preserves_identifier_atoms():
    assert bmi._tokenize("ＡＡＰＬ AAPL aapl") == ("aapl",)
    assert bmi._tokenize("中国流动性 中国流动性") == ("中国流动性",)
    assert bmi._tokenize("600036．ＳＨ outlook") == ("600036.sh", "outlook")
    assert bmi._tokenize("BRK-B outlook") == ("brk-b", "outlook")
    assert bmi._tokenize("near-term outlook") == ("near", "term", "outlook")
```

- [ ] **Step 6: Run the new test subset and record RED**

Run:

```bash
python3 -m pytest tests/test_brain_market_intel.py -q \
  -k 'meaningful_single_term or identifiers_do_not_match or natural_hyphenated or tokenize_normalizes or no_meaningful_search_atom'
```

Expected: failures showing the pinned implementation rejects one-token/Han inputs, fragments full-width/qualified forms, or uses unsafe identifier substring matching. Verify the process exit code, not only the pytest summary.

- [ ] **Step 7: Commit the RED test contract separately**

```bash
git add tests/test_brain_market_intel.py
MM_ALLOW_RED_COMMIT=1 git commit -m "test(brain): define bilingual research search contract"
```

If repository hooks do not support `MM_ALLOW_RED_COMMIT`, leave the tests uncommitted and preserve the exact RED command/output in the task report; do not weaken tests to make the commit green.

---

### Task 2: Implement the smallest safe lexical repair

**Files:**
- Modify: `engine/neuralweb/brain_market_intel.py` around `_WORD_RE`, `_tokenize`, `_hits`, `search_research`, and `RESEARCH_TOOL_SCHEMA`
- Test: `tests/test_brain_market_intel.py`

**Interfaces:**
- Consumes: the tests from Task 1 and the existing `search_research(root, query, limit=5, *, mode=None, report_id="", user_ctx=None, now=None) -> dict` contract.
- Produces: `_search_normalize(text: str) -> str`, `_tokenize(query: str) -> tuple[str, ...]`, and `_hits(tokens: tuple[str, ...], haystack: str) -> int` with unchanged public envelopes and scoring.

- [ ] **Step 1: Add the standard-library dependency and lexical constants**

Add `import unicodedata` beside the existing standard-library imports. Replace the old `_QUALIFIED_RE` block with:

```python
_WORD_RE = re.compile(r"[a-z0-9]{2,}")
_HAN_RANGE = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002fa1f"
_HAN_RE = re.compile("[" + _HAN_RANGE + "]+")
_RAW_SEARCH_ATOM_RE = re.compile(
    r"[A-Za-z0-9]+(?:[.\-][A-Za-z0-9]+)*|[" + _HAN_RANGE + "]+"
)
```

- [ ] **Step 2: Implement normalization and identifier classification**

Add:

```python
def _search_normalize(text: str) -> str:
    """NFKC + casefold for matching only; returned query text stays original."""
    return unicodedata.normalize("NFKC", str(text or "")).casefold()


def _is_qualified_identifier(raw: str) -> bool:
    """Whether a punctuated ASCII atom should remain exact instead of split."""
    if "." in raw:
        return True
    parts = raw.split("-")
    return (
        len(parts) == 2
        and 1 <= len(parts[0]) <= 5
        and len(parts[1]) == 1
        and parts[0].isalnum()
        and parts[1].isalpha()
    )
```

The one-letter share-class rule preserves uppercase or lowercase forms such as `BRK-B`, `brk-b`, `BF-A`, and `bf-a` without misclassifying common compounds and numeric ranges such as `near-term`, `risk-off`, `AI-driven`, or `10-yr`.

- [ ] **Step 3: Replace `_tokenize` with typed-by-construction string atoms**

Implement:

```python
def _tokenize(query: str) -> tuple[str, ...]:
    """Query -> ordered, de-duplicated meaningful lexical atoms."""
    text = unicodedata.normalize("NFKC", str(query or ""))
    tokens: list[str] = []

    def add(token: str) -> None:
        normalized = token.casefold()
        if len(normalized) >= 2 and normalized not in tokens:
            tokens.append(normalized)

    for raw in _RAW_SEARCH_ATOM_RE.findall(text):
        if _HAN_RE.fullmatch(raw):
            add(raw)
        elif _is_qualified_identifier(raw):
            add(raw)
        else:
            for word in _WORD_RE.findall(raw.casefold()):
                add(word)
    return tuple(tokens)
```

- [ ] **Step 4: Replace `_hits` with exact class-aware matching**

Implement:

```python
def _hits(tokens: tuple[str, ...], haystack: str) -> int:
    """Count distinct normalized atoms supported by the haystack."""
    text = _search_normalize(haystack)
    if not text:
        return 0
    words = set(_WORD_RE.findall(text))
    atoms = {raw.casefold() for raw in _RAW_SEARCH_ATOM_RE.findall(
        unicodedata.normalize("NFKC", str(haystack or ""))
    )}
    count = 0
    for token in tokens:
        if _HAN_RE.fullmatch(token):
            count += int(token in text)
        elif "." in token or "-" in token:
            count += int(token in atoms)
        else:
            count += int(token in words)
    return count
```

- [ ] **Step 5: Admit one meaningful atom and update truthful documentation**

Change:

```python
if len(tokens) < 2:
```

to:

```python
if not tokens:
```

Update the function docstring to say that input with no meaningful atom returns `query too short`; meaningful one-term searches are allowed. Update the query property in `RESEARCH_TOOL_SCHEMA` to:

```python
"Search terms — a theme, ticker, institution, or Chinese phrase. One meaningful "
"term is accepted (e.g. 'semiconductors', 'AAPL', '中国流动性'); add focused terms "
"when the first result set is broad. Ignored when mode='clusters' or mode='report'; "
"pass '' there."
```

Do not alter any other tool-schema or public-result field.

- [ ] **Step 6: Run the Task 1 subset and observe GREEN**

```bash
python3 -m pytest tests/test_brain_market_intel.py -q \
  -k 'meaningful_single_term or identifiers_do_not_match or natural_hyphenated or tokenize_normalizes or no_meaningful_search_atom'
```

Expected: all selected tests pass and the process exits 0.

- [ ] **Step 7: Run the complete owning file**

```bash
python3 -m pytest tests/test_brain_market_intel.py -q
```

Expected: all runnable tests pass; sparse-checkout real-data tests may skip only under their pre-existing decorators. Confirm no module-guard failure appears after the pytest summary.

- [ ] **Step 8: Add one schema assertion and rerun the owning file**

Extend `test_research_tool_schema_shape_and_attribution_instruction` with:

```python
query_description = props["query"]["description"]
assert "One meaningful term is accepted" in query_description
assert "中国流动性" in query_description
assert "at least 2 words" not in query_description
```

Run the full owning file again and require exit 0.

- [ ] **Step 9: Run focused downstream and static gates**

```bash
python3 -m pytest \
  tests/test_brain_market_intel.py \
  tests/test_brain_gateway.py \
  tests/test_brain_seed_router.py \
  tests/test_brain_analyst_wiring.py -q
python3 scripts/check_contract_delta.py --base origin/main
python3 scripts/run_ci_pack.py --workflow .github/ci/legacy-jobs.yml --validate-only
python3 -m py_compile engine/neuralweb/brain_market_intel.py
python3 - <<'PY'
from pathlib import Path
from engine.neuralweb.brain_market_intel import search_research
root = Path('.')
for query in ('semiconductors', 'AAPL', '中国流动性', '600036.SH'):
    result = search_research(root, query)
    assert set(result) == {'query', 'results', 'count_scanned', 'note'}
print('brain-search-smoke: ok')
PY
git diff --check
```

If the real catalog is omitted by sparse checkout, the smoke must return the honest unavailable envelope without raising; do not materialize `data/` merely to make the smoke look richer.

- [ ] **Step 10: Inspect the exact diff and protected boundaries**

```bash
git status --short
git diff --stat
git diff -- engine/neuralweb/brain_market_intel.py tests/test_brain_market_intel.py
git diff -- engine/research_vault app/research.py .github/ci/legacy-jobs.yml config/mastermind_programs.yml
```

Expected: the protected-boundary diff is empty.

- [ ] **Step 11: Commit the green implementation**

```bash
git add engine/neuralweb/brain_market_intel.py tests/test_brain_market_intel.py
git commit -m "fix(brain): support bilingual one-term research search"
```

- [ ] **Step 12: Return the implementation packet**

Report exact head/tree, changed files, RED command/result, GREEN commands/results, remaining skips, contract/manifest results, and any deviations. Do not push, open a PR, or alter deployment; the commissioning Sol session owns review and delivery.

---

### Task 3: Independent review, source delivery, and production proof

**Files:**
- Review: all four changed/new paths in this operation
- No new product paths unless a verified review finding requires a bounded repair

**Interfaces:**
- Consumes: Task 2 exact candidate head and evidence packet.
- Produces: reviewed source commit, one pull request, concluded CI, merged main commit, deploy/restart evidence, and an honest production capability state.

- [ ] **Step 1: Run an independent spec-compliance review**

A separate reviewer reads the design, plan, exact diff, and test evidence. It must verify every acceptance item, identifier boundary, natural-hyphen regression, result-envelope preservation, fail-soft behavior, no new owner/control plane, and no authority widening. Findings are keyed to exact file/line and candidate SHA.

- [ ] **Step 2: Run an independent code-quality review**

The reviewer checks Unicode behavior, regex bounds, Python-version compatibility, false positives/negatives, duplicate scoring, performance over the current catalog size, doc/schema truth, and test discrimination. It explicitly attacks `BRK-B`, `risk-off`, `AI`, `AAPL`, `600036.SH`, full-width forms, simplified/traditional Chinese, punctuation-only input, and hostile larger atoms.

- [ ] **Step 3: Repair verified findings with RED-first tests**

For each accepted finding, add or tighten a failing test first, observe RED, implement the minimal correction, rerun affected and complete owning suites, and commit a forward fix. Do not rewrite history or broaden scope.

- [ ] **Step 4: Refresh source and collision state before publication**

```bash
git fetch origin main
git merge-base --is-ancestor origin/main HEAD
gh pr list --repo mastermindx-market-intelligence/macro --state open --limit 500 \
  --json number,title,headRefName,headRefOid,files
```

If `origin/main` moved, merge it normally into the feature branch only after confirming no overlap on the two primary paths; never reset, rebase, force, or overwrite another writer. Rerun affected tests after integration.

- [ ] **Step 5: Push and open one pull request**

Push the exact branch, verify remote readback, then open one PR whose body records the operation key, base/head/tree, outcome, files, tests, non-goals, collision census, restart behavior, and production-proof plan. Edit the complete body before the final source push when possible to avoid duplicate authority runs.

- [ ] **Step 6: Observe CI at a quota-safe cadence**

Read the current rate limit before watching. Use one watcher or checks poll at no less than 60-second cadence. Do not dispatch duplicate baselines over an in-flight main run, cancel shared workflows, or treat pending as green. Resolve only genuine candidate failures.

- [ ] **Step 7: Merge only after binding checks conclude**

Recheck review decision, exact remote head, current base, mergeability, hold text, and every binding status. Squash-merge the reviewed head without deleting the branch while its proof run is in flight. Verify the squash commit is on `origin/main`.

- [ ] **Step 8: Prove deployment and restart**

Wait for `https://mastermind-x.com/api/health` to advertise a main descendant containing the squash merge. Because `engine/neuralweb/brain_market_intel.py` is already in `app/deploy/update.sh`’s API restart trigger, verify `/var/log/macro-update.log` or systemd state shows a real `macro-api` PID transition after the changed commit.

- [ ] **Step 9: Run the deployed lexical consumer proof**

On the deployed checkout, call the deployed module against its actual Research Vault catalog for:

```text
semiconductors
AAPL
中国流动性
600036.SH
```

Verify each query is admitted, the catalog is actually scanned, decoy identifiers do not appear, and missing matches remain honest empty results. This is machine-consumer production proof. An authenticated Brain answer with a working passage/source open is recorded separately if an authorized identity and browser connection are available; absence of that external principal keeps the complete user journey `BUILT_NOT_PROVEN`, not falsely `PROVEN_LIVE`.

- [ ] **Step 10: Update durable records and define the successor wave**

Record the merged/deployed evidence and any residual in the existing `macro-mastermind-ai` organizational owner. The next independent wave is bilingual query planning plus existing-corpus full-text passage retrieval; it receives a fresh operation key and does not inherit source authority from this completed child.
