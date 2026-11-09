import test from "node:test";
import assert from "node:assert/strict";
import {
  createRankedSearchState,
  projectRankedSearch,
  transitionRankedSearch,
} from "./ranked-search-state-reference.mjs";

// Synthetic interaction inventory only. The other 47 names carry no market data.
const inventoryKey = "synthetic-t47-50-row-reference";
const rows = Object.freeze(Array.from({ length: 50 }, (_, index) => {
  const rank = index + 1;
  const named = rank === 1 ? ["BTC", "Bitcoin"]
    : rank === 2 ? ["ETH", "Ethereum"]
    : rank === 21 ? ["XMR", "Monero"]
    : ["DEMO" + rank, "Example asset " + rank];
  return Object.freeze({
    id: "supplied-row-" + rank,
    symbol: named[0],
    name: named[1],
    rank,
    group: rank <= 20 ? "primary" : "secondary",
    displayedValue: null,
  });
}));
const initial = (expanded = false, key = inventoryKey) =>
  createRankedSearchState({ inventoryKey: key, expanded });
const step = (state, event, supplied = rows, key = inventoryKey) =>
  transitionRankedSearch({ rows: supplied, state, inventoryKey: key, event });
const view = (state, supplied = rows, key = inventoryKey) =>
  projectRankedSearch({ rows: supplied, state, inventoryKey: key });

test("zero matches -> rank 21 -> Clear restores both original choices", async (t) => {
  for (const expanded of [false, true]) {
    await t.test(expanded ? "originally open" : "originally closed", () => {
      const zero = step(initial(expanded), { type: "query", value: "zzzz" });
      assert.equal(zero.projection.totalCount, 50);
      assert.equal(zero.projection.matchCount, 0);
      assert.equal(zero.projection.noMatches, true);
      assert.equal(zero.projection.disclosureVisible, false);
      assert.equal(zero.focus, null);

      const match = step(zero.state, { type: "query", value: "monero" });
      assert.equal(match.projection.matchCount, 1);
      assert.equal(match.projection.disclosureOpen, true);
      assert.deepEqual(match.projection.visibleRows.map((row) => row.rank), [21]);
      assert.strictEqual(match.projection.visibleRows[0], rows[20]);
      assert.equal(match.state.beforeSearchOpen, expanded);
      assert.equal(match.focus, null);

      const cleared = step(match.state, { type: "clear" });
      assert.equal(cleared.state.expanded, expanded);
      assert.equal(cleared.state.beforeSearchOpen, null);
      assert.equal(cleared.projection.matchCount, 50);
      assert.equal(cleared.projection.visibleRows.length, expanded ? 50 : 20);
      assert.equal(cleared.focus, "search-input");
    });
  }
});

test("manually emptying the input restores the same list without a focus request", () => {
  for (const expanded of [false, true]) {
    const searched = step(initial(expanded), { type: "query", value: "XMR" });
    const emptied = step(searched.state, { type: "query", value: "" });
    const cleared = step(searched.state, { type: "clear" });
    assert.deepEqual(emptied.state, cleared.state);
    assert.deepEqual(emptied.projection, cleared.projection);
    assert.equal(emptied.focus, null);
  }
});

test("later nonempty queries and temporary toggles do not replace the baseline", () => {
  const found = step(initial(false), { type: "query", value: "monero" });
  const closed = step(found.state, { type: "disclosure", open: false });
  const unchanged = step(closed.state, { type: "query", value: "monero" });
  assert.equal(unchanged.projection.disclosureOpen, false);
  const zero = step(unchanged.state, { type: "query", value: "zzzz" });
  const foundAgain = step(zero.state, { type: "query", value: "XMR" });
  assert.equal(foundAgain.projection.disclosureOpen, true);
  assert.equal(foundAgain.state.beforeSearchOpen, false);
  assert.equal(step(foundAgain.state, { type: "clear" }).state.expanded, false);
});

test("the next search captures the reader's new resting disclosure choice", () => {
  const first = step(initial(false), { type: "query", value: "XMR" });
  const cleared = step(first.state, { type: "clear" });
  const opened = step(cleared.state, { type: "disclosure", open: true });
  const second = step(opened.state, { type: "query", value: "zzzz" });
  assert.equal(second.state.beforeSearchOpen, true);
  assert.equal(step(second.state, { type: "clear" }).state.expanded, true);
});

test("literal symbol OR name matching ignores case but not punctuation or spaces", () => {
  assert.equal(step(initial(), { type: "query", value: "mOnErO" }).projection.matchCount, 1);
  assert.equal(step(initial(), { type: "query", value: "xmr" }).projection.matchCount, 1);
  assert.equal(step(initial(), { type: "query", value: ".*" }).projection.matchCount, 0);
  assert.equal(step(initial(), { type: "query", value: " monero " }).projection.matchCount, 0);
  assert.equal(step(initial(), { type: "query", value: "Monero XMR" }).projection.matchCount, 0);
});

test("a primary-only match has no empty secondary disclosure", () => {
  const result = step(initial(true), { type: "query", value: "bitcoin" });
  assert.equal(result.projection.noMatches, false);
  assert.equal(result.projection.disclosureVisible, false);
  assert.deepEqual(result.projection.visibleRows, [rows[0]]);
  assert.equal(step(result.state, { type: "clear" }).state.expanded, true);
});

test("an empty supplied inventory is not a zero-match result", () => {
  const result = step(initial(), { type: "query", value: "BTC" }, []);
  assert.equal(result.projection.noRows, true);
  assert.equal(result.projection.noMatches, false);
  assert.equal(result.projection.controlsAvailable, false);
  assert.equal(result.projection.disclosureVisible, false);
  assert.equal(step(result.state, { type: "clear" }, []).focus, null);
});

test("missing names and values remain missing; symbols still match", () => {
  const supplied = Object.freeze([
    Object.freeze({ id: "unknown-name", symbol: "ABC", name: null, group: "primary", value: null }),
    Object.freeze({ id: "unknown-both", symbol: null, name: null, group: "secondary", value: null }),
  ]);
  const found = step(initial(), { type: "query", value: "abc" }, supplied);
  assert.strictEqual(found.projection.visibleRows[0], supplied[0]);
  assert.equal(found.projection.visibleRows[0].name, null);
  assert.equal(found.projection.visibleRows[0].value, null);
  assert.equal(view(initial(true), supplied).visibleRows.length, 2);
});

test("host group and supplied order are preserved without deriving or renumbering rank", () => {
  const supplied = [
    { id: "tail", symbol: "SAME2", name: "Same", group: "secondary", rank: 107 },
    { id: "front", symbol: "SAME1", name: "Same", group: "primary", rank: 3 },
  ];
  const result = step(initial(), { type: "query", value: "same" }, supplied);
  assert.deepEqual(result.projection.visibleRows.map((row) => row.id), ["tail", "front"]);
  assert.deepEqual(result.projection.visibleRows.map((row) => row.rank), [107, 3]);
  assert.strictEqual(result.projection.visibleRows[0], supplied[0]);
});

test("stale disclosure events cannot alter a zero-match view or its return choice", () => {
  const zero = step(initial(false), { type: "query", value: "zzzz" });
  const stale = step(zero.state, { type: "disclosure", open: true });
  assert.equal(stale.handled, false);
  assert.deepEqual(stale.state, zero.state);
  assert.equal(stale.focus, null);
});

test("different inventory identity requires explicit new initialization", () => {
  assert.throws(
    () => step(initial(), { type: "query", value: "BTC" }, rows, "different-snapshot"),
    /inventory changed/
  );
  const next = initial(true, "different-snapshot");
  assert.equal(view(next, rows, "different-snapshot").visibleRows.length, 50);
});

test("invalid row identity or group fails before enhancement can be accepted", () => {
  assert.throws(
    () => view(initial(), [rows[0], rows[0]]),
    /unique, nonempty host IDs/
  );
  assert.throws(
    () => view(initial(), [{ id: "x", symbol: "X", group: "inferred" }]),
    /existing disclosure/
  );
  assert.throws(
    () => view(initial(), [{ id: "x", symbol: 0, group: "primary" }]),
    /symbol must be/
  );
});

test("source objects and prior state are never mutated", () => {
  const state = initial(false);
  const beforeRows = JSON.stringify(rows);
  const result = step(state, { type: "query", value: "monero" });
  assert.equal(state.query, "");
  assert.equal(state.expanded, false);
  assert.equal(state.beforeSearchOpen, null);
  assert.equal(JSON.stringify(rows), beforeRows);
  assert.equal(result.projection.matchingRows[0].displayedValue, null);
  assert.ok(Object.isFrozen(result.state));
});

test("invalid event or impossible state is not silently repaired", () => {
  assert.throws(() => step(initial(), { type: "query", value: null }), /query must be/);
  assert.throws(() => step(initial(), { type: "fetch" }), /unsupported event/);
  assert.throws(
    () => view({ ...initial(), beforeSearchOpen: true }),
    /must not retain/
  );
});

