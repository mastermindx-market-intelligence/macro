import test from "node:test";
import assert from "node:assert/strict";
import { deriveCaseSelection, isCopyCompletionCurrent } from "./catalyst-selection-state-reference.mjs";

// Exact identity/value subset of the existing TEST fixture, not market evidence.
// terminal/lib/__tests__/fixtures/catalystOpportunity.json
// commit 3e2f8db782b0ba2f98343edf5199a4b8ce921ec9
// blob e438c093a553615737d0527fff709b07a88290bc
const SOURCE = [
  {
    "id": "co:market:energy_complex",
    "theme_id": "energy_complex",
    "name": "Energy Complex",
    "name_zh": "能源综合体",
    "observed_on": "2026-10-16",
    "metrics": {
      "rel_5d": 0.0621,
      "pct50": 0.75
    }
  },
  {
    "id": "co:market:defense",
    "theme_id": "defense",
    "name": "Defense & Aerospace",
    "name_zh": "国防与航空航天",
    "observed_on": "2026-10-16",
    "metrics": {
      "rel_5d": 0.0165,
      "pct50": 0.6
    }
  }
];
const CASES = Object.freeze(SOURCE.map((row) =>
  Object.freeze({ ...row, metrics: Object.freeze({ ...row.metrics }) })));
const [energy, defense] = CASES;

function choose(overrides = {}) {
  return deriveCaseSelection({
    readState: "resolved",
    cases: CASES,
    visibleThemeIds: CASES.map((row) => row.theme_id),
    requestedId: "defense",
    ...overrides,
  });
}

test("an explicit Defense case survives an Energy-only result list", () => {
  const state = choose({ visibleThemeIds: ["energy_complex"] });
  assert.equal(state.kind, "selected");
  assert.equal(state.selectionMode, "explicit");
  assert.strictEqual(state.selected, defense);
  assert.deepEqual(state.visibleCases, [energy]);
  assert.equal(state.outsideFilters, true);
  assert.equal(state.copyThemeId, "defense");
  assert.equal(state.requestedId, "defense");
});

test("zero filtered results keep the explicit eligible case and its copy identity", () => {
  const state = choose({ visibleThemeIds: [] });
  assert.deepEqual(state.visibleCases, []);
  assert.strictEqual(state.selected, defense);
  assert.equal(state.outsideFilters, true);
  assert.equal(state.copyThemeId, "defense");
});

test("Clear restores list visibility without changing explicit identity", () => {
  const before = choose({ visibleThemeIds: [] });
  const cleared = choose();
  assert.strictEqual(cleared.selected, before.selected);
  assert.equal(cleared.requestedId, before.requestedId);
  assert.equal(cleared.outsideFilters, false);
  assert.deepEqual(cleared.visibleCases, CASES);
});

test("history-selected identities are resolved independently of the retained filter", () => {
  const restored = ["defense", "energy_complex", "defense"].map((requestedId) =>
    choose({ requestedId, visibleThemeIds: ["energy_complex"] }));
  assert.deepEqual(restored.map((state) => state.copyThemeId),
    ["defense", "energy_complex", "defense"]);
  assert.deepEqual(restored.map((state) => state.outsideFilters), [true, false, true]);
});

test("an absent explicit case never falls back to a visible alternative", () => {
  const state = choose({ cases: [energy], visibleThemeIds: ["energy_complex"] });
  assert.equal(state.kind, "missing");
  assert.equal(state.requestedId, "defense");
  assert.strictEqual(state.visibleCases[0], energy);
  assert.equal(state.selected, null);
  assert.equal(state.selectionMode, null);
  assert.equal(state.copyThemeId, null);
  assert.equal(state.outsideFilters, false);
});

test("without an explicit case the initial default follows the supplied visible order", () => {
  const state = choose({ requestedId: null, visibleThemeIds: ["defense", "energy_complex"] });
  assert.equal(state.selectionMode, "default");
  assert.strictEqual(state.selected, defense);
  assert.deepEqual(state.visibleCases, [defense, energy]);
  assert.equal(state.requestedId, null);
});

test("without an explicit case zero results have no default detail", () => {
  const state = choose({ requestedId: null, visibleThemeIds: [] });
  assert.equal(state.kind, "none");
  assert.equal(state.selected, null);
  assert.equal(state.copyThemeId, null);
});

for (const readState of ["pending", "unavailable", "auth", "access"]) {
  test(readState + " ignores stale payloads and is never inferred as absence", () => {
    const unreadable = new Proxy({}, { get() { throw new Error("Stale rows were inspected"); } });
    const state = choose({ readState, cases: unreadable, visibleThemeIds: unreadable });
    assert.equal(state.kind, readState);
    assert.equal(state.selected, null);
    assert.equal(state.copyThemeId, null);
    assert.deepEqual(state.visibleCases, []);
  });
}

test("same-theme replacement returns one new canonical row without old-field mixing", () => {
  const nextDefense = Object.freeze({
    ...defense, observed_on: "2026-10-19",
    metrics: Object.freeze({ rel_5d: null, pct50: 0 }),
    cautions: Object.freeze(["Test-only replacement context"]),
  });
  const state = choose({ cases: [energy, nextDefense], visibleThemeIds: ["energy_complex"] });
  assert.strictEqual(state.selected, nextDefense);
  assert.equal(state.selected.observed_on, "2026-10-19");
  assert.equal(state.selected.metrics.rel_5d, null);
  assert.equal(state.selected.metrics.pct50, 0);
  assert.deepEqual(state.selected.cautions, ["Test-only replacement context"]);
  assert.equal(defense.observed_on, "2026-10-16");
  assert.equal(defense.metrics.rel_5d, 0.0165);
});

test("invalid resolved input fails explicitly instead of becoming a quiet or missing case", () => {
  assert.throws(() => choose({ readState: "success-ish" }), /readState/);
  assert.throws(() => choose({ cases: null }), /arrays/);
  assert.throws(() => choose({ cases: [defense, defense] }), /Duplicate eligible/);
  assert.throws(() => choose({ visibleThemeIds: ["defense", "defense"] }), /Duplicate visible/);
  assert.throws(() => choose({ visibleThemeIds: ["outside_owner"] }), /outside the authorized/);
  assert.throws(() => choose({ requestedId: " defense " }), /exact identity/);
  assert.throws(() => choose({ requestedId: undefined }), /exact identity/);
  assert.throws(() => choose({ requestedId: "" }), /exact identity/);
});

test("projection preserves source values, source objects and caller order", () => {
  const state = choose();
  assert.strictEqual(state.selected, defense);
  assert.strictEqual(state.visibleCases[0], energy);
  assert.strictEqual(state.visibleCases[1], defense);
  assert.equal(state.selected.metrics.rel_5d, 0.0165);
  assert.equal(state.selected.metrics.pct50, 0.6);
  assert.ok(Object.isFrozen(state));
  assert.ok(Object.isFrozen(state.visibleCases));
  assert.deepEqual(CASES.map((row) => row.theme_id), ["energy_complex", "defense"]);
});

test("a current copy completion can publish status for the selected theme", () => {
  const attempt = Symbol("copy A"), readContext = Symbol("owned read A");
  const completion = { attempt, readContext, themeId: "defense" };
  assert.equal(isCopyCompletionCurrent(completion,
    { attempt, readContext, selection: choose() }), true);
});

test("selection change retires copy status even after a return to the same theme", () => {
  const attempt = Symbol("copy A"), readContext = Symbol("owned read A");
  const completion = { attempt, readContext, themeId: "defense" };
  assert.equal(isCopyCompletionCurrent(completion, {
    attempt, readContext, selection: choose({ requestedId: "energy_complex" }),
  }), false);
  // The existing owner retires the attempt on the first selection change.
  assert.equal(isCopyCompletionCurrent(completion,
    { attempt: null, readContext, selection: choose() }), false);
});

test("overlapping copies accept only the latest attempt regardless of completion order", () => {
  const first = Symbol("copy 1"), second = Symbol("copy 2"), readContext = Symbol("owned read A");
  const current = { attempt: second, readContext, selection: choose() };
  const oldCompletion = { attempt: first, readContext, themeId: "defense" };
  const newCompletion = { attempt: second, readContext, themeId: "defense" };
  assert.equal(isCopyCompletionCurrent(newCompletion, current), true);
  assert.equal(isCopyCompletionCurrent(oldCompletion, current), false);
});

test("a new owned read invalidates copy status even with unchanged content generation", () => {
  const attempt = Symbol("copy A");
  const oldRead = { identity: "A", revision: 1, generation: "same-content" };
  const newRead = { identity: "A", revision: 2, generation: "same-content" };
  const completion = { attempt, readContext: oldRead, themeId: "defense" };
  assert.equal(isCopyCompletionCurrent(completion,
    { attempt, readContext: newRead, selection: choose() }), false);
});

test("blocked or absent selections cannot accept a clipboard completion status", () => {
  const attempt = Symbol("copy A"), readContext = Symbol("owned read A");
  const completion = { attempt, readContext, themeId: "defense" };
  for (const selection of [
    choose({ readState: "pending" }),
    choose({ readState: "access" }),
    choose({ cases: [energy], visibleThemeIds: ["energy_complex"] }),
    choose({ requestedId: null, visibleThemeIds: [] }),
  ]) {
    assert.equal(isCopyCompletionCurrent(completion, { attempt, readContext, selection }), false);
  }
  assert.equal(isCopyCompletionCurrent(completion,
    { attempt: null, readContext, selection: choose() }), false);
  assert.equal(isCopyCompletionCurrent(null, null), false);
});

test("a blocked read clears output even before an identity or inventory is initialized", () => {
  const state = deriveCaseSelection({ readState: "access" });
  assert.equal(state.kind, "access");
  assert.equal(state.requestedId, null);
  assert.equal(state.selected, null);
  assert.deepEqual(state.visibleCases, []);
});

test("returning to an account does not resurrect an old read context", () => {
  const attempt = Symbol("copy A");
  const firstA = { account: "A", read: 1 };
  const laterA = { account: "A", read: 3 };
  const completion = { attempt, readContext: firstA, themeId: "defense" };
  assert.equal(isCopyCompletionCurrent(completion,
    { attempt, readContext: laterA, selection: choose() }), false);
});

test("disposal and uninitialized tokens cannot qualify completion status", () => {
  const attempt = Symbol("copy A"), readContext = Symbol("owned read A");
  const completion = { attempt, readContext, themeId: "defense" };
  assert.equal(isCopyCompletionCurrent(completion,
    { attempt: null, readContext: null, selection: choose() }), false);
  for (const absent of [null, undefined]) {
    assert.equal(isCopyCompletionCurrent(
      { attempt: absent, readContext: absent, themeId: "defense" },
      { attempt: absent, readContext: absent, selection: choose() }), false);
  }
});

