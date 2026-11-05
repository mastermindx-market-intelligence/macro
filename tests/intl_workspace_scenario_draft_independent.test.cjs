"use strict";

const { describe, it, before } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

const api = require("../templates/intl_workspace_scenario.js");

const CTX_A = Object.freeze({
  selected_market: "KR",
  horizon: "6m",
  currency_basis: "local"
});
const CTX_B = Object.freeze({
  selected_market: "BR",
  horizon: "2y",
  currency_basis: "usd_unhedged"
});
const CTX_NULL_MARKET = Object.freeze({
  selected_market: null,
  horizon: "1q",
  currency_basis: "usd_unhedged"
});

const DRAFT_KEYS = [
  "context",
  "raw",
  "result",
  "rows",
  "pending",
  "reset_pending",
  "errors",
  "tab"
];

function sha256(rel) {
  return crypto.createHash("sha256").update(fs.readFileSync(path.join(__dirname, rel))).digest("hex");
}

function reduce(draft, command, locale) {
  return api.reduceDraft(draft, command, locale === undefined ? "en" : locale);
}

function edit(draft, field, raw, locale) {
  return reduce(draft, { type: "edit", field, raw }, locale);
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function oracle(localPercent, fxPercent) {
  return api.calculateScenario(localPercent, fxPercent);
}

function fill(ctx, localRaw, fxRaw) {
  const started = api.createDraft(ctx);
  const afterLocal = edit(started, "local", localRaw);
  assert.equal(afterLocal.ok, true);
  const afterFx = edit(afterLocal.draft, "fx", fxRaw);
  assert.equal(afterFx.ok, true);
  return afterFx.draft;
}

function mustCalculate(draft, locale) {
  const r = reduce(draft, { type: "calculate" }, locale);
  assert.equal(r.ok, true, r.reason);
  assert.equal(r.draft.result.status, "valid");
  return r;
}

function assertTypeError(fn) {
  assert.throws(fn, (err) => {
    assert.equal(err instanceof TypeError, true);
    assert.equal(err.message, "invalid_scenario_draft");
    return true;
  });
}

function assertUnchangedCore(actual, expected) {
  assert.deepEqual(actual.context, expected.context);
  assert.deepEqual(actual.raw, expected.raw);
  assert.deepEqual(actual.result, expected.result);
  assert.deepEqual(actual.rows, expected.rows);
}

function assertWithheld(r) {
  assert.equal(r.visible_result, null);
  assert.deepEqual(r.visible_rows, []);
  assert.notEqual(r.visible_rows, r.draft.rows);
}

function assertNoPersistenceSideEffects(beforeKeys, writes) {
  assert.deepEqual(Object.keys(globalThis).sort(), beforeKeys);
  assert.deepEqual(writes, []);
}

function assertDraftShape(draft) {
  assert.deepEqual(Object.keys(draft).sort(), DRAFT_KEYS.slice().sort());
  assert.equal("source" in draft, false);
  assert.equal("pin" in draft, false);
  assert.equal("pins" in draft, false);
  assert.equal("history" in draft, false);
  assert.equal("url" in draft, false);
  assert.equal("artifact_ref" in draft, false);
}

describe("independent draft transition review", () => {
  const storageWrites = [];
  let globalKeysBefore;

  before(() => {
    const store = {
      setItem(k, v) {
        storageWrites.push(["setItem", k, v]);
      },
      getItem() {
        storageWrites.push(["getItem"]);
        return null;
      },
      removeItem(k) {
        storageWrites.push(["removeItem", k]);
      },
      clear() {
        storageWrites.push(["clear"]);
      }
    };
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      enumerable: false,
      value: store
    });
    Object.defineProperty(globalThis, "sessionStorage", {
      configurable: true,
      enumerable: false,
      value: store
    });
    globalThis.fetch = function fetch() {
      storageWrites.push(["fetch"]);
      throw new Error("network_forbidden");
    };
    // Snapshot after this harness installs its spies; Node 26 already exposes sessionStorage.
    globalKeysBefore = Object.keys(globalThis).sort();
  });

  it("createDraft starts blank with no sample assumptions and detaches context", () => {
    const incoming = { selected_market: "KR", horizon: "6m", currency_basis: "local" };
    const d = api.createDraft(incoming);
    incoming.selected_market = "ZZ";
    incoming.horizon = "hack";
    incoming.currency_basis = "usd_unhedged";
    assert.deepEqual(d.raw, { local: "", fx: "" });
    assert.equal(d.result, null);
    assert.deepEqual(d.rows, []);
    assert.equal(d.pending, null);
    assert.equal(d.reset_pending, false);
    assert.deepEqual(d.errors, { local: null, fx: null });
    assert.equal(d.tab, "history");
    assert.deepEqual(d.context, CTX_A);
    assertDraftShape(d);
    d.context.horizon = "mutated";
    assert.equal(incoming.horizon, "hack");
    const blank = reduce(api.createDraft(CTX_A), { type: "calculate" });
    assert.equal(blank.ok, false);
    assert.equal(blank.draft.result, null);
    assert.notEqual(blank.draft.raw.local, "5");
    assert.notEqual(blank.draft.raw.fx, "-3");
  });

  it("null selected_market is admitted; empty market or extra keys are invalid state", () => {
    const d = api.createDraft(CTX_NULL_MARKET);
    assert.equal(d.context.selected_market, null);
    assertTypeError(() =>
      api.createDraft({ selected_market: "", horizon: "6m", currency_basis: "local" })
    );
    assertTypeError(() =>
      api.createDraft({
        selected_market: "KR",
        horizon: "6m",
        currency_basis: "local",
        roster: ["KR"]
      })
    );
    assertTypeError(() =>
      api.createDraft({ selected_market: "KR", horizon: "", currency_basis: "local" })
    );
    assertTypeError(() =>
      api.createDraft({ selected_market: "KR", horizon: "6m", currency_basis: "usd" })
    );
  });

  it("committed arithmetic follows the accepted engine with no annualization or quote switch", () => {
    const filled = fill(CTX_A, "8", "-2");
    const r = mustCalculate(filled);
    const expected = oracle(8, -2);
    assert.equal(r.draft.result.usdPercent, expected.usdPercent);
    assert.equal(r.draft.result.fxContributionPp, expected.fxContributionPp);
    assert.deepEqual(
      r.draft.rows.map((row) => row.fxPercent),
      api.sensitivityCases(8, -2).map((row) => row.fxPercent)
    );
    assert.equal(r.announce, true);
    assert.equal(r.draft.raw.local, "8");
    assert.equal(r.draft.raw.fx, "-2");

    const pending = reduce(r.draft, { type: "propose_context", context: CTX_B });
    assert.equal(pending.ok, true);
    assertWithheld(pending);
    const confirmed = reduce(pending.draft, { type: "confirm_context" });
    assert.equal(confirmed.ok, true);
    assert.deepEqual(confirmed.context_commit, CTX_B);
    assert.deepEqual(confirmed.draft.context, CTX_B);
    assert.equal(confirmed.draft.result.usdPercent, expected.usdPercent);
    assert.equal(confirmed.draft.result.fxContributionPp, expected.fxContributionPp);
    assert.equal(confirmed.announce, true);
  });

  it("breaks if staging mutates original context, raw, or private result", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const before = clone(calculated.draft);
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B });
    assert.equal(staged.ok, true);
    assert.equal(staged.context_commit, null);
    assert.equal(staged.announce, false);
    assertUnchangedCore(staged.draft, before);
    assert.deepEqual(staged.draft.pending.context, CTX_B);
    assert.deepEqual(staged.draft.pending.raw, before.raw);
    assert.deepEqual(staged.draft.pending.original_errors, before.errors);
    assertWithheld(staged);
    assert.equal(staged.draft.result.usdPercent, oracle(8, -2).usdPercent);

    const edited = edit(staged.draft, "local", "9");
    assert.equal(edited.ok, true);
    assert.deepEqual(edited.draft.raw, before.raw);
    assert.deepEqual(edited.draft.context, before.context);
    assert.deepEqual(edited.draft.result, calculated.draft.result);
    assert.equal(edited.draft.pending.raw.local, "9");
    assert.equal(edited.draft.pending.raw.fx, "-2");
    assert.equal(edited.announce, false);
    assertWithheld(edited);
  });

  it("cancel restores original raw, context, result, and pre-stage errors without adopting the candidate", () => {
    const invalid = reduce(fill(CTX_A, "8", "1,5"), { type: "calculate" });
    assert.equal(invalid.ok, false);
    assert.equal(invalid.draft.errors.fx, "invalid_format");
    const poisoned = invalid.draft;
    const staged = reduce(poisoned, { type: "propose_context", context: CTX_B });
    const edited = edit(edit(staged.draft, "fx", "-").draft, "local", "99").draft;
    const failedConfirm = reduce(edited, { type: "confirm_context" });
    assert.equal(failedConfirm.ok, false);
    assert.equal(failedConfirm.focus, "fx");
    assert.deepEqual(failedConfirm.draft.context, CTX_A);
    assert.equal(failedConfirm.context_commit, null);
    assert.ok(failedConfirm.draft.pending);
    assertWithheld(failedConfirm);

    const cancelled = reduce(failedConfirm.draft, { type: "cancel_context" });
    assert.equal(cancelled.ok, true);
    assert.equal(cancelled.announce, false);
    assert.equal(cancelled.context_commit, null);
    assert.deepEqual(cancelled.draft.context, CTX_A);
    assert.deepEqual(cancelled.draft.raw, { local: "8", fx: "1,5" });
    assert.equal(cancelled.draft.pending, null);
    assert.equal(cancelled.draft.errors.fx, "invalid_format");
    assert.equal(cancelled.draft.result, null);
    assert.equal(cancelled.visible_result, null);
  });

  it("successful confirm is atomic: new context, candidate raw, and new result commit together", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B }).draft;
    const edited = edit(staged, "fx", "4").draft;
    const mid = clone(edited);
    const confirmed = reduce(edited, { type: "confirm_context" }, "zh");
    assert.equal(confirmed.ok, true);
    assert.deepEqual(confirmed.draft.context, CTX_B);
    assert.deepEqual(confirmed.draft.raw, { local: "8", fx: "4" });
    assert.equal(confirmed.draft.pending, null);
    assert.deepEqual(confirmed.context_commit, CTX_B);
    const expected = oracle(8, 4);
    assert.equal(confirmed.draft.result.usdPercent, expected.usdPercent);
    assert.equal(confirmed.draft.result.fxContributionPp, expected.fxContributionPp);
    assert.equal(confirmed.visible_result.usdPercent, expected.usdPercent);
    assert.equal(confirmed.announce, true);
    assert.notDeepEqual(confirmed.draft.context, mid.context);
    assert.notDeepEqual(confirmed.draft.raw, mid.raw);
    assert.equal(mid.pending.raw.fx, "4");
    assert.deepEqual(mid.raw, { local: "8", fx: "-2" });
  });

  it("invalid confirm keeps the old context and withholds proposed values, including loss and overflow-class inputs", () => {
    const calculated = mustCalculate(fill(CTX_A, "2", "4"));
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B }).draft;

    const fxLoss = reduce(edit(staged, "fx", "-100").draft, { type: "confirm_context" });
    assert.equal(fxLoss.ok, false);
    assert.equal(fxLoss.reason, "invalid_inputs");
    assert.equal(fxLoss.focus, "fx");
    assert.equal(fxLoss.draft.errors.fx, "fx_nonpositive_endpoint");
    assert.deepEqual(fxLoss.draft.context, CTX_A);
    assert.deepEqual(fxLoss.draft.raw, { local: "2", fx: "4" });
    assert.equal(fxLoss.draft.pending.raw.fx, "-100");
    assert.equal(fxLoss.context_commit, null);
    assert.equal(fxLoss.announce, false);
    assertWithheld(fxLoss);
    assert.equal(fxLoss.draft.result.usdPercent, oracle(2, 4).usdPercent);

    const localLoss = reduce(edit(fxLoss.draft, "local", "-100.01").draft, { type: "confirm_context" });
    assert.equal(localLoss.ok, false);
    assert.equal(localLoss.focus, "local");
    assert.equal(localLoss.draft.errors.local, "local_below_total_loss");
    assert.deepEqual(localLoss.draft.context, CTX_A);

    const blankCandidate = edit(edit(localLoss.draft, "local", "").draft, "fx", " ").draft;
    const blankConfirm = reduce(blankCandidate, { type: "confirm_context" });
    assert.equal(blankConfirm.ok, false);
    assert.equal(blankConfirm.focus, "local");
    assert.equal(blankConfirm.draft.errors.local, "input_required");
    assert.equal(blankConfirm.draft.errors.fx, "input_required");
    assert.deepEqual(blankConfirm.draft.context, CTX_A);
    assert.ok(blankConfirm.draft.pending);
  });

  it("calculate cannot bypass pending, reveal numbers, or commit context", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_NULL_MARKET });
    const bypass = reduce(staged.draft, { type: "calculate" });
    assert.equal(bypass.ok, false);
    assert.equal(bypass.reason, "confirmation_required");
    assert.deepEqual(bypass.draft, staged.draft);
    assert.equal(bypass.context_commit, null);
    assert.equal(bypass.announce, false);
    assertWithheld(bypass);
    assert.equal(bypass.draft.result.usdPercent, oracle(8, -2).usdPercent);
    assert.ok(bypass.draft.rows.length > 0);
  });

  it("second proposal cannot replace an unresolved candidate; same context is a no-op", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const same = reduce(calculated.draft, {
      type: "propose_context",
      context: { selected_market: "KR", horizon: "6m", currency_basis: "local" }
    });
    assert.equal(same.ok, true);
    assert.deepEqual(same.draft, calculated.draft);
    assert.equal(same.context_commit, null);
    assert.equal(same.announce, false);
    assert.equal(same.visible_result.usdPercent, oracle(8, -2).usdPercent);

    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B });
    const hijack = reduce(staged.draft, { type: "propose_context", context: CTX_NULL_MARKET });
    assert.equal(hijack.ok, false);
    assert.equal(hijack.reason, "confirmation_pending");
    assert.deepEqual(hijack.draft, staged.draft);
    assert.deepEqual(hijack.draft.pending.context, CTX_B);
  });

  it("whitespace or any nonempty raw requires staging; exact empty strings commit immediately", () => {
    const nbsp = edit(api.createDraft(CTX_A), "local", "\u3000");
    const staged = reduce(nbsp.draft, { type: "propose_context", context: CTX_B });
    assert.equal(staged.ok, true);
    assert.equal(staged.context_commit, null);
    assert.equal(staged.draft.raw.local, "\u3000");
    assert.deepEqual(staged.draft.context, CTX_A);
    assert.ok(staged.draft.pending);

    const empty = reduce(api.createDraft(CTX_A), { type: "propose_context", context: CTX_B });
    assert.equal(empty.ok, true);
    assert.deepEqual(empty.context_commit, CTX_B);
    assert.deepEqual(empty.draft.context, CTX_B);
    assert.equal(empty.draft.pending, null);
    assert.equal(empty.visible_result, null);

    const cleared = mustCalculate(fill(CTX_A, "8", "-2"));
    const afterReset = reduce(
      reduce(cleared.draft, { type: "request_reset" }).draft,
      { type: "confirm_reset" }
    );
    const direct = reduce(afterReset.draft, { type: "propose_context", context: CTX_B });
    assert.equal(direct.ok, true);
    assert.deepEqual(direct.context_commit, CTX_B);
    assert.equal(direct.draft.pending, null);
    assert.deepEqual(direct.draft.raw, { local: "", fx: "" });
  });

  it("raw strings stay exact, including invalid over-length and fullwidth text", () => {
    const fullwidth = fill(CTX_A, "＋８％", "−２");
    const calculated = mustCalculate(fullwidth, "zh");
    assert.deepEqual(calculated.draft.raw, { local: "＋８％", fx: "−２" });
    assert.equal(calculated.draft.result.usdPercent, oracle(8, -2).usdPercent);

    const long = "9".repeat(129);
    const edited = edit(calculated.draft, "local", long);
    assert.equal(edited.ok, true);
    assert.equal(edited.draft.raw.local, long);
    assert.equal(edited.draft.raw.local.length, 129);
    assert.equal(edited.draft.result, null);
    const parsed = reduce(edited.draft, { type: "calculate" });
    assert.equal(parsed.ok, false);
    assert.equal(parsed.draft.errors.local, "max_length");
    assert.equal(parsed.draft.raw.local.length, 129);
    assert.equal(parsed.draft.result, null);
    assert.equal(parsed.announce, false);
  });

  it("blank, editing, locale, and loss boundaries stay field-local and do not invent caps", () => {
    const blank = reduce(api.createDraft(CTX_A), { type: "calculate" });
    assert.equal(blank.ok, false);
    assert.equal(blank.focus, "local");
    assert.equal(blank.draft.errors.local, "input_required");
    assert.equal(blank.draft.errors.fx, "input_required");

    const editing = reduce(fill(CTX_A, "8", "-."), { type: "calculate" });
    assert.equal(editing.ok, false);
    assert.equal(editing.focus, "fx");
    assert.equal(editing.draft.errors.fx, "input_required");
    assert.equal(editing.draft.result, null);

    const words = reduce(fill(CTX_A, "8", "1e3"), { type: "calculate" });
    assert.equal(words.draft.errors.fx, "invalid_format");

    const locale = reduce(fill(CTX_A, "8", "-2"), { type: "calculate" }, "fr");
    assert.equal(locale.ok, false);
    assert.ok(String(locale.draft.errors.local).startsWith("unsupported_locale"));
    assert.equal(locale.draft.result, null);

    const zh = mustCalculate(fill(CTX_A, "8", "-2"), "zh");
    assert.equal(zh.draft.result.usdPercent, oracle(8, -2).usdPercent);

    const totalLoss = mustCalculate(fill(CTX_A, "-100", "8"));
    assert.equal(totalLoss.draft.result.usdPercent, oracle(-100, 8).usdPercent);
    assert.equal(totalLoss.draft.result.fxContributionPp, 0);

    const fxFloor = reduce(fill(CTX_A, "8", "-100"), { type: "calculate" });
    assert.equal(fxFloor.ok, false);
    assert.equal(fxFloor.draft.errors.fx, "fx_nonpositive_endpoint");

    const huge = mustCalculate(fill(CTX_A, "9".repeat(128), "-1"));
    assert.equal(huge.ok, true);
    assert.equal(huge.draft.result.status, "valid");
    assert.equal(typeof huge.draft.result.usdPercent, "number");
    assert.equal(Number.isFinite(huge.draft.result.usdPercent), true);
    assert.notEqual(huge.reason, "too_large");
    assert.notEqual(huge.draft.errors.local, "too_large");
  });

  it("valid edit clears committed output immediately and never announces or auto-calculates", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const edited = edit(calculated.draft, "local", "2");
    assert.equal(edited.ok, true);
    assert.equal(edited.announce, false);
    assert.equal(edited.draft.result, null);
    assert.deepEqual(edited.draft.rows, []);
    assert.equal(edited.visible_result, null);
    assert.equal(edited.draft.raw.fx, "-2");
    assert.deepEqual(edited.draft.context, CTX_A);
  });

  it("reset asks once, cancel is exact, confirm clears only assumptions, and confirmation is single-use", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    calculated.draft.tab = calculated.draft.tab;
    const tabbed = reduce(calculated.draft, { type: "set_tab", tab: "scenario" });
    const asked = reduce(tabbed.draft, { type: "request_reset" });
    assert.equal(asked.ok, true);
    assert.equal(asked.draft.reset_pending, true);
    assertUnchangedCore(asked.draft, tabbed.draft);
    assert.equal(asked.draft.tab, "scenario");
    assert.equal(asked.announce, false);

    const askedAgain = reduce(asked.draft, { type: "request_reset" });
    assert.equal(askedAgain.ok, true);
    assert.deepEqual(askedAgain.draft, asked.draft);

    const cancelled = reduce(asked.draft, { type: "cancel_reset" });
    assert.equal(cancelled.ok, true);
    assert.deepEqual(cancelled.draft, tabbed.draft);

    const confirmed = reduce(asked.draft, { type: "confirm_reset" });
    assert.equal(confirmed.ok, true);
    assert.deepEqual(confirmed.draft.raw, { local: "", fx: "" });
    assert.equal(confirmed.draft.result, null);
    assert.deepEqual(confirmed.draft.rows, []);
    assert.deepEqual(confirmed.draft.errors, { local: null, fx: null });
    assert.deepEqual(confirmed.draft.context, CTX_A);
    assert.equal(confirmed.draft.tab, "scenario");
    assert.equal(confirmed.draft.reset_pending, false);
    assert.equal(confirmed.context_commit, null);

    const twice = reduce(confirmed.draft, { type: "confirm_reset" });
    assert.equal(twice.ok, false);
    assert.equal(twice.reason, "confirmation_required");
    assert.deepEqual(twice.draft, confirmed.draft);

    const withoutAsk = reduce(tabbed.draft, { type: "confirm_reset" });
    assert.equal(withoutAsk.ok, false);
    assert.deepEqual(withoutAsk.draft, tabbed.draft);
  });

  it("reset and context confirmation exclude each other; edits and calculate refuse while reset waits", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B });
    const resetDuringPending = reduce(staged.draft, { type: "request_reset" });
    assert.equal(resetDuringPending.ok, false);
    assert.equal(resetDuringPending.reason, "confirmation_pending");
    assert.deepEqual(resetDuringPending.draft, staged.draft);

    const reset = reduce(calculated.draft, { type: "request_reset" });
    assert.equal(reduce(reset.draft, { type: "propose_context", context: CTX_B }).ok, false);
    assert.equal(edit(reset.draft, "local", "1").ok, false);
    assert.equal(reduce(reset.draft, { type: "calculate" }).ok, false);
    assert.equal(reduce(reset.draft, { type: "confirm_context" }).ok, false);
    const tab = reduce(reset.draft, { type: "set_tab", tab: "scenario" });
    assert.equal(tab.ok, true);
    assert.equal(tab.draft.reset_pending, true);
    assertUnchangedCore(tab.draft, reset.draft);
  });

  it("tab changes are independent of staged context and do not announce", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B }).draft;
    const tabbed = reduce(staged, { type: "set_tab", tab: "scenario" });
    assert.equal(tabbed.ok, true);
    assert.equal(tabbed.announce, false);
    assert.equal(tabbed.draft.tab, "scenario");
    assert.deepEqual(tabbed.draft.context, CTX_A);
    assert.deepEqual(tabbed.draft.raw, calculated.draft.raw);
    assertWithheld(tabbed);
    const cancelled = reduce(tabbed.draft, { type: "cancel_context" });
    assert.equal(cancelled.draft.tab, "scenario");
    assert.deepEqual(cancelled.draft.raw, calculated.draft.raw);
    assert.deepEqual(cancelled.draft.result, calculated.draft.result);
    assert.equal(cancelled.visible_result.usdPercent, oracle(8, -2).usdPercent);
  });

  it("once-only context confirmation; later calculate does not reannounce unchanged numbers", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const staged = reduce(calculated.draft, { type: "propose_context", context: CTX_B }).draft;
    const confirmed = reduce(staged, { type: "confirm_context" });
    assert.equal(confirmed.announce, true);
    const again = reduce(confirmed.draft, { type: "confirm_context" });
    assert.equal(again.ok, false);
    assert.equal(again.reason, "confirmation_required");
    assert.equal(again.announce, false);
    const repeat = reduce(confirmed.draft, { type: "calculate" });
    assert.equal(repeat.ok, true);
    assert.equal(repeat.announce, false);
    assert.deepEqual(repeat.draft.result, confirmed.draft.result);
    const afterTab = reduce(repeat.draft, { type: "set_tab", tab: "scenario" });
    const still = reduce(afterTab.draft, { type: "calculate" });
    assert.equal(still.announce, false);
  });

  it("failed and inapplicable commands do not announce or mutate", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const before = clone(calculated.draft);
    const commands = [
      { type: "calculate", extra: true },
      { type: "nope" },
      { type: "edit", field: "local", raw: 8 },
      { type: "edit", field: "horizon", raw: "8" },
      { type: "set_tab", tab: "History" },
      { type: "cancel_context" },
      { type: "confirm_context" },
      { type: "cancel_reset" },
      { type: "refresh_source" },
      { type: "save_draft" },
      { type: "pin" }
    ];
    for (const command of commands) {
      const r = reduce(calculated.draft, command);
      assert.equal(r.ok, false, JSON.stringify(command));
      assert.equal(r.announce, false, JSON.stringify(command));
      assert.equal(r.context_commit, null, JSON.stringify(command));
      assert.deepEqual(r.draft, calculated.draft, JSON.stringify(command));
      assert.deepEqual(calculated.draft, before);
    }
  });

  it("inputs and outputs are detached; mutating commit, command, or result cannot rewrite prior state", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const before = clone(calculated.draft);
    const command = { type: "propose_context", context: { ...CTX_B } };
    const staged = reduce(calculated.draft, command);
    command.context.horizon = "broken";
    command.type = "confirm_context";
    staged.draft.pending.raw.local = "changed";
    staged.context_commit;
    staged.draft.context.selected_market = "XX";
    assert.deepEqual(calculated.draft, before);
    assert.equal(staged.draft.pending.context.horizon, "2y");

    const fresh = reduce(calculated.draft, { type: "propose_context", context: CTX_B });
    const confirmed = reduce(fresh.draft, { type: "confirm_context" });
    const commit = confirmed.context_commit;
    commit.horizon = "broken";
    confirmed.visible_result.usdPercent = 0;
    assert.equal(confirmed.draft.context.horizon, "2y");
    assert.deepEqual(calculated.draft, before);
  });

  it("malicious getters and toJSON hooks never run on draft or command", () => {
    let count = 0;
    const command = { type: "edit", field: "local" };
    Object.defineProperty(command, "raw", {
      enumerable: true,
      get() {
        count += 1;
        return "20";
      }
    });
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    assert.equal(reduce(calculated.draft, command).ok, false);
    assert.equal(count, 0);

    const nested = { type: "propose_context" };
    Object.defineProperty(nested, "context", {
      enumerable: true,
      get() {
        count += 1;
        return CTX_B;
      }
    });
    assert.equal(reduce(calculated.draft, nested).ok, false);
    assert.equal(count, 0);

    const jsonCmd = {
      type: "calculate",
      toJSON() {
        count += 1;
        return { type: "calculate" };
      }
    };
    assert.equal(reduce(calculated.draft, jsonCmd).ok, false);
    assert.equal(count, 0);

    const ctx = { horizon: "6m", currency_basis: "local" };
    Object.defineProperty(ctx, "selected_market", {
      enumerable: true,
      get() {
        count += 1;
        return "KR";
      }
    });
    assertTypeError(() => api.createDraft(ctx));
    assert.equal(count, 0);

    const jsonDraft = mustCalculate(fill(CTX_A, "8", "-2")).draft;
    jsonDraft.toJSON = function toJSON() {
      count += 1;
      return {};
    };
    assertTypeError(() => reduce(jsonDraft, { type: "calculate" }));
    assert.equal(count, 0);
  });

  it("invalid state throws before any command effect", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    const tamperedResult = clone(calculated.draft);
    tamperedResult.result.usdPercent = 99;
    assertTypeError(() => reduce(tamperedResult, { type: "calculate" }));

    const extra = clone(calculated.draft);
    extra.note = "nope";
    assertTypeError(() => reduce(extra, { type: "set_tab", tab: "scenario" }));

    const rowsOnly = clone(calculated.draft);
    rowsOnly.result = null;
    assertTypeError(() => reduce(rowsOnly, { type: "calculate" }));

    const badTab = clone(calculated.draft);
    badTab.tab = "History";
    assertTypeError(() => reduce(badTab, { type: "calculate" }));

    const pendingSame = clone(calculated.draft);
    pendingSame.pending = {
      context: clone(CTX_A),
      raw: clone(calculated.draft.raw),
      original_errors: { local: null, fx: null }
    };
    assertTypeError(() => reduce(pendingSame, { type: "cancel_context" }));

    const bothFlags = clone(calculated.draft);
    bothFlags.reset_pending = true;
    bothFlags.pending = {
      context: clone(CTX_B),
      raw: clone(calculated.draft.raw),
      original_errors: { local: null, fx: null }
    };
    assertTypeError(() => reduce(bothFlags, { type: "cancel_reset" }));

    const getterDraft = mustCalculate(fill(CTX_A, "8", "-2")).draft;
    const raw = getterDraft.raw;
    Object.defineProperty(getterDraft, "raw", {
      enumerable: true,
      get() {
        return raw;
      }
    });
    assertTypeError(() => reduce(getterDraft, { type: "calculate" }));
    assertTypeError(() => reduce(null, { type: "calculate" }));
    assertTypeError(() => reduce(undefined, { type: "calculate" }));
  });

  it("sequence: pending edit failure, repair, confirm, then empty-reset context switch", () => {
    const calculated = mustCalculate(fill(CTX_A, "8", "-2"));
    let d = reduce(calculated.draft, { type: "propose_context", context: CTX_B }).draft;
    d = edit(d, "fx", "words").draft;
    let r = reduce(d, { type: "confirm_context" });
    assert.equal(r.ok, false);
    assert.deepEqual(r.draft.context, CTX_A);
    d = edit(r.draft, "fx", "4").draft;
    r = reduce(d, { type: "confirm_context" });
    assert.equal(r.ok, true);
    assert.deepEqual(r.draft.context, CTX_B);
    assert.equal(r.draft.result.usdPercent, oracle(8, 4).usdPercent);

    d = reduce(r.draft, { type: "request_reset" }).draft;
    r = reduce(d, { type: "confirm_reset" });
    assert.deepEqual(r.draft.context, CTX_B);
    r = reduce(r.draft, { type: "propose_context", context: CTX_NULL_MARKET });
    assert.equal(r.ok, true);
    assert.deepEqual(r.context_commit, CTX_NULL_MARKET);
    assert.equal(r.draft.pending, null);
    assert.deepEqual(r.draft.raw, { local: "", fx: "" });
  });

  it("helper has no source, pin, or persistence effect across the transition surface", () => {
    const calculated = mustCalculate(fill(CTX_A, "＋８％", "-2"), "zh");
    reduce(calculated.draft, { type: "propose_context", context: CTX_B });
    reduce(reduce(calculated.draft, { type: "propose_context", context: CTX_B }).draft, {
      type: "confirm_context"
    });
    reduce(calculated.draft, { type: "request_reset" });
    reduce(reduce(calculated.draft, { type: "request_reset" }).draft, { type: "confirm_reset" });
    assert.equal(typeof api.createDraft, "function");
    assert.equal(typeof api.reduceDraft, "function");
    assert.equal(typeof api.parsePercent, "function");
    assert.equal(typeof api.calculateScenario, "function");
    assert.equal(typeof api.sensitivityCases, "function");
    assert.deepEqual(Object.keys(api).sort(), [
      "calculateScenario",
      "createDraft",
      "parsePercent",
      "reduceDraft",
      "sensitivityCases"
    ]);
    assert.equal(typeof document, "undefined");
    assertNoPersistenceSideEffects(globalKeysBefore, storageWrites);
  });


});
