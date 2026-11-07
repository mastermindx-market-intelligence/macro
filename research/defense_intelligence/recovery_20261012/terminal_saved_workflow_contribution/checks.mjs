#!/usr/bin/env node
/**
 * Discriminating tests for the typed durable Government Revenue
 * saved-view/monitor declaration contribution.
 *
 * Exercises the PATCHED sources in-place (fixture harness only -- no real DB,
 * no browser, no network): the harness copies the patched lib modules into a
 * throwaway directory, supplies explicit stub modules for the three alias
 * leaves that carry no runtime under test (`@/lib/rmsViews`,
 * `@/lib/analysisSymbol`, `@/lib/watchlists`), and rewrites the `@/lib/x`
 * alias imports to relative `./x.ts` specifiers so Node's type stripping can
 * resolve them.
 *
 * Run:
 *   node --experimental-strip-types checks.mjs --root <repo-root>
 *
 * <repo-root> is the tree the patch was applied to; it must contain
 * terminal/lib/{savedViewContract,savedViews,theses,governmentRevenueMonitor}.ts
 * plus terminal/app/api/thesis-saved-views/route.ts and
 * supabase/migrations/0012_thesis_objects.sql (static artifact checks).
 *
 * Stub disclosure: MAX_SAVED_VIEW_NAME/MAX_SAVED_VIEWS and ANALYSIS_SYMBOL are
 * stub values matching the reviewed migration's patterns; nothing here is a
 * fixture proof about real production values.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import crypto from "node:crypto";

function argValue(name, fallback) {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}
const ROOT = path.resolve(argValue("--root", process.env.DECL_TEST_ROOT ?? process.cwd()));
const LIB = path.join(ROOT, "terminal", "lib");
// Bind the actual source under review before importing any code. This rejects
// changed files; it does not apply the patch or establish ownership.
const MANIFEST = JSON.parse(fs.readFileSync(path.join(path.dirname(fileURLToPath(import.meta.url)), "source-manifest.json"), "utf8"));
for (const row of MANIFEST.sources) {
  const actual = crypto.createHash("sha256").update(fs.readFileSync(path.join(ROOT, row.path))).digest("hex");
  assert.equal(actual, row.proposed_sha256, `source drift: ${row.path}`);
}
globalThis.fetch = async () => { throw new Error("network call prohibited in declaration fixture checks"); };


// --- harness: patched modules + explicit stubs ----------------------------
const BUILD = fs.mkdtempSync(path.join(os.tmpdir(), "govrev-decl-"));
process.on("exit", () => fs.rmSync(BUILD, { recursive: true, force: true }));

const COPIED = ["savedViewContract.ts", "savedViews.ts", "theses.ts", "governmentRevenueMonitor.ts"];
for (const name of COPIED) {
  const source = fs.readFileSync(path.join(LIB, name), "utf8");
  fs.writeFileSync(path.join(BUILD, name), source.replaceAll(/@\/lib\/([A-Za-z0-9_]+)/g, "./$1.ts"));
}
fs.writeFileSync(path.join(BUILD, "watchlists.ts"), `
export type DbRow = { key?: unknown; value?: unknown; updated_at?: unknown; [column: string]: unknown };
export type DbResult = { error: { message: string } | null; data: unknown };
export type WatchlistQuery = {
  select: (columns: string) => WatchlistQuery;
  eq: (column: string, value: unknown) => WatchlistQuery;
  order: (column: string, options: { ascending?: boolean }) => WatchlistQuery;
  range?: (from: number, to: number) => WatchlistQuery;
  limit: (count: number) => WatchlistQuery;
  maybeSingle: () => Promise<DbResult>;
  insert: (row: unknown) => Promise<DbResult>;
  update: (patch: unknown) => WatchlistQuery;
  delete: () => WatchlistQuery;
};
export type WatchlistDb = { from: (table: string) => WatchlistQuery };
`);
fs.writeFileSync(path.join(BUILD, "rmsViews.ts"), `
export const MAX_SAVED_VIEW_NAME = 80;
export const MAX_SAVED_VIEWS = 50;
export type ViewFilter = {
  lifecycle: "active" | "any";
  staleDays?: number;
  windowClosed?: boolean;
  subjectGroupKey?: string;
};
export type SavedView = { id: string; name: string; filter: ViewFilter; createdAt: string; updatedAt: string };
`);
fs.writeFileSync(path.join(BUILD, "analysisSymbol.ts"), `
// Stub pattern: the closed symbol vocabulary the reviewed 0012 migration enforces.
export const ANALYSIS_SYMBOL = /^(\^[A-Z0-9]+|[A-Z0-9]+([.-][A-Z0-9]+)*)$/;
`);

const contract = await import(pathToFileURL(path.join(BUILD, "savedViewContract.ts")).href);
const savedViews = await import(pathToFileURL(path.join(BUILD, "savedViews.ts")).href);
const theses = await import(pathToFileURL(path.join(BUILD, "theses.ts")).href);
const govrev = await import(pathToFileURL(path.join(BUILD, "governmentRevenueMonitor.ts")).href);

// --- fixture doubles ------------------------------------------------------
function resolveJsonPath(row, column) {
  const parts = column.split("->");
  let current = row[parts[0]];
  for (const part of parts.slice(1)) {
    if (current === null || typeof current !== "object") return null;
    current = part.startsWith(">") ? current[part.slice(1)] : current[part];
  }
  return current;
}
/** Minimal Supabase-shaped thenable covering exactly the builder paths the
 * saved-view owner and the thesis readers use. Fixture only. */
function createDb() {
  const store = new Map();
  const toRow = (row) => ({ key: row.key, value: row.value, updated_at: row.updated_at });
  function makeQuery(filters) {
    let wantRows = false;
    let update = null;
    let remove = false;
    let ordered = null;
    let range = null;
    const q = {
      select() { wantRows = true; return q; },
      order(column) { ordered = column; return q; },
      range(from, to) { range = [from, to]; return q; },
      limit() { return q; },
      maybeSingle() {
        const matched = rowsWhere(filters);
        return Promise.resolve({ error: null, data: matched.length ? toRow(matched[0]) : null });
      },
      eq(column, value) { filters.push([column, value]); return q; },
      insert(payload) { store.set(payload.key, { ...payload }); return Promise.resolve({ error: null, data: null }); },
      update(patch) { update = patch; return q; },
      delete() { remove = true; return q; },
      then(resolve, reject) {
        let matched = rowsWhere(filters);
        if (ordered) matched = [...matched].sort((a, b) => String(a[ordered]).localeCompare(String(b[ordered])));
        if (range) matched = matched.slice(range[0], range[1] + 1);
        if (update !== null) {
          for (const row of matched) { row.value = update.value; row.updated_at = update.updated_at; }
        } else if (remove) {
          for (const row of matched) store.delete(row.key);
        }
        return resolve(wantRows && !remove ? { error: null, data: matched.map(toRow) } : { error: null, data: null });
      },
    };
    return q;
  }
  function rowsWhere(filters) {
    const matched = [];
    for (const row of store.values()) {
      if (filters.every(([column, value]) => String(resolveJsonPath(row, column)) === String(value))) matched.push(row);
    }
    return matched;
  }
  return { from: () => makeQuery([]), __store: store };
}

const USER_A = "a0000000-0000-4000-8000-00000000000a";
const USER_B = "b0000000-0000-4000-8000-00000000000b";
const VIEW_ID = "0f0e0d0c-1111-4222-8333-444455556666";
const THESIS_ID = "5a5a5a5a-5a5a-4a5a-8a5a-5a5a5a5a5a5a";
const REF_SHA = `workspace-sha256:${"a".repeat(64)}`;
const REF_GRW = `grw2-${"b".repeat(24)}`;

const SUBJECT = {
  schema: "mastermind.thesis-subject-ref/v1",
  kind: "issuer",
  owner: "data_os.security_master",
  key: "LMT",
  identityState: "resolved",
  companyId: null,
  display: "Lockheed Martin",
};

function validDeclaration(overrides = {}) {
  return {
    schema: "government_revenue.monitor_declaration.v1",
    enabled: true,
    subject: SUBJECT,
    selection: { mode: "awards", truth: "defense", q: "hypersonics", agency: null, ticker: null, issuer: "LMT" },
    window: { start: "2026-01-01T00:00:00.000Z", end: "2026-12-31T23:59:59.999Z" },
    knowledgeCutoff: "2026-10-01T00:00:00.000Z",
    inputRefs: [REF_SHA, REF_GRW],
    baselineEvents: [],
    ...overrides,
  };
}
function monitorDefinition(monitor) {
  return { version: 1, kind: "government_revenue", monitor };
}
function baseContent(extra = {}) {
  return {
    schema: "mastermind.thesis-content/v1",
    title: "LMT award flow",
    statement: "Track defense award flow for the declared subject.",
    catalysts: ["quarterly awards"],
    falsifiers: ["awards collapse"],
    risks: ["budget delay"],
    horizon: "months",
    effectiveAt: null,
    revisionNote: null,
    ...extra,
  };
}
function wireVersionRow(version, previousVersion, transition, wireContent, recordedAt) {
  return {
    id: `c0000000-0000-4000-8000-${String(version).padStart(12, "0")}`,
    thesis_id: THESIS_ID,
    version,
    previous_version: previousVersion,
    transition,
    lifecycle_state: "active",
    subject_ref: theses.subjectToWire(theses.normalizeThesisSubject(SUBJECT)),
    content: wireContent,
    client_request_id: `d0000000-0000-4000-8000-${String(version).padStart(12, "0")}`,
    system_recorded_at: recordedAt,
    effective_at: wireContent.effective_at,
  };
}

// --- tests ----------------------------------------------------------------

test("existing saved-view kinds are preserved verbatim", () => {
  const thesisFilter = contract.normalizeSavedDefinition(
    { version: 1, kind: "thesis_filter", filter: { lifecycle: "active", staleDays: 7 } });
  assert.ok(thesisFilter);
  assert.equal(thesisFilter.kind, "thesis_filter");
  assert.deepEqual(thesisFilter.filter, { lifecycle: "active", staleDays: 7 });

  const heatmapFixed = contract.normalizeSavedDefinition({
    version: 1, kind: "heatmap_fixed", securityOwner: "data_os.security_master",
    securityKeys: ["LMT", "RTX"], universe: { owner: "data_os.security_master", key: "defense" },
    membershipVersion: "v1",
  });
  assert.ok(heatmapFixed);
  assert.deepEqual(heatmapFixed.securityKeys, ["LMT", "RTX"]);

  const heatmapLive = contract.normalizeSavedDefinition({
    version: 1, kind: "heatmap_live", universe: { owner: "data_os.security_master", key: "defense" },
    membershipPolicy: "current_on_open", sessionPolicy: "latest_eligible_close",
    metric: { id: "price_return_pct", window: "1D" }, condition: { operator: "gt", value: 2 },
  });
  assert.ok(heatmapLive);
  assert.equal(heatmapLive.metric.window, "1D");

  assert.equal(contract.normalizeSavedDefinition({ version: 1, kind: "gov_rev", monitor: {} }), null);
  assert.equal(contract.normalizeSavedDefinition({ version: 2, kind: "thesis_filter", filter: { lifecycle: "any" } }), null);
});

test("valid government_revenue declaration round-trips through the existing saved-view owner", async () => {
  const db = createDb();
  const definition = monitorDefinition(validDeclaration());
  const created = await savedViews.createWorkspaceSavedView(db, USER_A, { id: VIEW_ID, name: "GovRev LMT", definition });
  assert.ok(created.ok, JSON.stringify(created));
  assert.equal(created.replayed, false);
  assert.equal(created.view.revision, 1);
  assert.equal(created.view.definition.kind, "government_revenue");

  const lookup = await savedViews.lookupWorkspaceSavedView(db, USER_A, VIEW_ID);
  assert.ok(lookup.ok);
  assert.equal(lookup.result.state, "present");
  assert.deepEqual(lookup.result.view.definition, created.view.definition);
  assert.equal(lookup.result.view.definition.monitor.selection.issuer, "LMT");
  assert.equal(lookup.result.view.definition.monitor.selection.mode, "awards");
  assert.deepEqual(lookup.result.view.definition.monitor.inputRefs, [REF_SHA, REF_GRW]);

  const listed = await savedViews.listWorkspaceSavedViews(db, USER_A, "government_revenue");
  assert.ok(listed.ok);
  assert.equal(listed.views.length, 1);
  const legacy = await savedViews.listSavedViews(db, USER_A);
  assert.ok(legacy.ok);
  assert.equal(legacy.views.length, 0); // legacy thesis consumers never see non-thesis kinds

  const replay = await savedViews.createWorkspaceSavedView(db, USER_A, { id: VIEW_ID, name: "GovRev LMT", definition });
  assert.ok(replay.ok);
  assert.equal(replay.replayed, true);
  assert.equal(replay.receipt.fingerprint, created.receipt.fingerprint);

  // Canonicalization on the workspace owner path: ticker upper-cases, spaces trim.
  const canon = await savedViews.createWorkspaceSavedView(db, USER_A, {
    id: "0f0e0d0c-1111-4222-8333-444455557777", name: "GovRev canon",
    definition: monitorDefinition(validDeclaration({
      selection: { mode: "changes", truth: "official", q: null, agency: " Air Force ", ticker: " lmt ", issuer: null },
    })),
  });
  assert.ok(canon.ok, JSON.stringify(canon));
  assert.equal(canon.view.definition.monitor.selection.ticker, "LMT");
  assert.equal(canon.view.definition.monitor.selection.agency, "Air Force");
});

test("A/B ownership mismatch is refused by the existing owner", async () => {
  const db = createDb();
  const created = await savedViews.createWorkspaceSavedView(db, USER_A, {
    id: VIEW_ID, name: "GovRev LMT", definition: monitorDefinition(validDeclaration()),
  });
  assert.ok(created.ok);

  const lookup = await savedViews.lookupWorkspaceSavedView(db, USER_B, VIEW_ID);
  assert.ok(!lookup.ok);
  assert.equal(lookup.status, "not_found");

  const renamed = await savedViews.renameWorkspaceSavedView(db, USER_B, VIEW_ID, "stolen");
  assert.ok(!renamed.ok);
  assert.equal(renamed.status, "not_found");

  const removed = await savedViews.deleteWorkspaceSavedView(db, USER_B, VIEW_ID);
  assert.ok(!removed.ok);
  assert.equal(removed.status, "not_found");

  const stillThere = await savedViews.lookupWorkspaceSavedView(db, USER_A, VIEW_ID);
  assert.ok(stillThere.ok);
  assert.equal(stillThere.result.state, "present");
});

test("unknown, private and free-form keys are refused before any DB write", async () => {
  const cases = [
    ["top-level private key", monitorDefinition(validDeclaration({ sourceUrl: "https://example.com/feed" }))],
    ["selection private key", monitorDefinition(validDeclaration({
      selection: { mode: "awards", truth: "all", q: null, agency: null, ticker: null, issuer: null, private_note: "x" },
    }))],
    ["unknown schema", monitorDefinition(validDeclaration({ schema: "government_revenue.monitor_declaration.v2" }))],
    ["bad inputRef URL", monitorDefinition(validDeclaration({ inputRefs: ["https://example.com/feed"] }))],
    ["bad inputRef grw2 alphabet", monitorDefinition(validDeclaration({ inputRefs: [`grw2-${"z".repeat(24)}`] }))],
    ["non-quartet issuer", monitorDefinition(validDeclaration({
      selection: { mode: "awards", truth: "all", q: null, agency: null, ticker: null, issuer: "BA" },
    }))],
    ["bad mode", monitorDefinition(validDeclaration({
      selection: { mode: "everything", truth: "all", q: null, agency: null, ticker: null, issuer: null },
    }))],
    ["bad truth", monitorDefinition(validDeclaration({
      selection: { mode: "awards", truth: "rumor", q: null, agency: null, ticker: null, issuer: null },
    }))],
    ["empty enabled type", monitorDefinition(validDeclaration({ enabled: "yes" }))],
    ["display-only subject", monitorDefinition(validDeclaration({
      subject: { ...SUBJECT, owner: "terminal.analysis_symbol", identityState: "resolved" },
    }))],
    ["nested private subject", monitorDefinition(validDeclaration({
      subject: { ...SUBJECT, privateNotes: "private" },
    }))],
    ["duplicate inputRefs", monitorDefinition(validDeclaration({ inputRefs: [REF_SHA, REF_SHA] }))],
  ];
  for (const [label, definition] of cases) {
    assert.equal(contract.normalizeSavedDefinition(definition), null, label);
  }
  const written = await savedViews.createWorkspaceSavedView(createDb(), USER_A, {
    id: "0f0e0d0c-1111-4222-8333-444455558888", name: "GovRev bad",
    definition: cases[0][1],
  });
  assert.ok(!written.ok);
  assert.equal(written.status, "invalid_definition");
});

test("over-limit declarations are refused", () => {
  const manyRefs = monitorDefinition(validDeclaration({
    inputRefs: Array.from({ length: 17 }, (_, i) => `grw2-${String(i).padStart(24, "0")}`),
  }));
  assert.equal(contract.normalizeSavedDefinition(manyRefs), null, "17 inputRefs");

  const tinyEvents = Array.from({ length: 101 }, (_, i) => ({
    recordId: `r${i}`, eventId: `e${i}`, version: 1, knownAt: "2026-09-01T00:00:00.000Z",
  }));
  assert.equal(contract.normalizeSavedDefinition(
    monitorDefinition(validDeclaration({ baselineEvents: tinyEvents }))), null, "101 baseline events");

  const fatEvents = Array.from({ length: 100 }, (_, i) => ({
    recordId: `r${i}`.padEnd(128, "x"), eventId: `e${i}`.padEnd(128, "y"),
    version: 1, knownAt: "2026-09-01T00:00:00.000Z",
  }));
  assert.equal(contract.normalizeSavedDefinition(
    monitorDefinition(validDeclaration({ baselineEvents: fatEvents }))), null, ">24KiB declaration");

  const longQ = monitorDefinition(validDeclaration({
    selection: { mode: "awards", truth: "all", q: "q".repeat(121), agency: null, ticker: null, issuer: null },
  }));
  assert.equal(contract.normalizeSavedDefinition(longQ), null, "q over 120");
  assert.equal(govrev.normalizeGovernmentRevenueMonitor(
    validDeclaration({ baselineEvents: [{ recordId: "r", eventId: "e", version: 0, knownAt: "2026-09-01T00:00:00.000Z" }] })),
  null, "version 0");
  assert.equal(govrev.normalizeGovernmentRevenueMonitor(
    validDeclaration({ baselineEvents: [{ recordId: "r", eventId: "e", version: 1.5, knownAt: "2026-09-01T00:00:00.000Z" }] })),
  null, "fractional version");
  assert.equal(govrev.normalizeGovernmentRevenueMonitor(
    validDeclaration({ baselineEvents: [{ recordId: "r", eventId: "e", version: true, knownAt: "2026-09-01T00:00:00.000Z" }] })),
  null, "boolean version");
  assert.equal(govrev.normalizeGovernmentRevenueMonitor(
    validDeclaration({ baselineEvents: [{
      recordId: "r", eventId: "e", version: 1, knownAt: "2026-09-01T00:00:00.000Z",
    }, {
      recordId: "r", eventId: "e", version: 2, knownAt: "2026-09-02T00:00:00.000Z",
    }] })),
  null, "duplicate baseline identity");
});

test("malformed clocks and unordered windows are refused", () => {
  const cases = [
    ["missing milliseconds", validDeclaration({ window: { start: "2026-01-01T00:00:00Z", end: "2026-12-31T00:00:00.000Z" } })],
    ["offset instead of Z", validDeclaration({ window: { start: "2026-01-01T00:00:00.000+00:00", end: "2026-12-31T00:00:00.000Z" } })],
    ["impossible calendar date", validDeclaration({ window: { start: "2026-02-30T00:00:00.000Z", end: "2026-12-31T00:00:00.000Z" } })],
    ["start after end", validDeclaration({ window: { start: "2026-12-31T00:00:00.000Z", end: "2026-01-01T00:00:00.000Z" } })],
    ["bad cutoff", validDeclaration({ knowledgeCutoff: "2026-10-01 00:00:00" })],
    ["numeric clock", validDeclaration({ knowledgeCutoff: 1760000000000 })],
  ];
  for (const [label, declaration] of cases) {
    assert.equal(govrev.normalizeGovernmentRevenueMonitor(declaration), null, label);
    assert.equal(contract.normalizeSavedDefinition(monitorDefinition(declaration)), null, `saved view: ${label}`);
    assert.equal(theses.normalizeThesisContent(
      baseContent({ governmentRevenueMonitor: declaration })), null, `thesis content: ${label}`);
  }
});

test("immutable thesis wire carries the declaration in BOTH directions and legacy records stay unchanged", async () => {
  const content = baseContent({ governmentRevenueMonitor: validDeclaration() });
  const normalized = theses.normalizeThesisContent(content);
  assert.ok(normalized);
  const declaration = normalized.governmentRevenueMonitor;
  assert.ok(declaration);
  assert.equal(declaration.schema, "government_revenue.monitor_declaration.v1");

  // Outgoing wire: the canonical member rides the existing content mapping.
  const wireDeclaration = govrev.governmentRevenueMonitorToWire(declaration);
  assert.equal(wireDeclaration.schema, "government_revenue.monitor_declaration.v1");
  assert.deepEqual(wireDeclaration.selection, { mode: "awards", truth: "defense", q: "hypersonics", agency: null, ticker: null, issuer: "LMT" });
  assert.deepEqual(wireDeclaration.window, { start: "2026-01-01T00:00:00.000Z", end: "2026-12-31T23:59:59.999Z" });
  assert.equal(wireDeclaration.knowledge_cutoff, "2026-10-01T00:00:00.000Z");
  assert.deepEqual(wireDeclaration.input_refs, [REF_SHA, REF_GRW]);
  assert.deepEqual(wireDeclaration.baseline_events, []);

  // Incoming wire: the same bytes parse back to the same declaration.
  const recordedAt = "2026-10-02T00:00:00.000Z";
  const wireContentV2 = {
    schema: "mastermind.thesis-content/v1",
    title: "LMT award flow",
    statement: "Track defense award flow for the declared subject.",
    catalysts: ["quarterly awards"],
    falsifiers: ["awards collapse"],
    risks: ["budget delay"],
    horizon: "months",
    effective_at: null,
    revision_note: null,
    government_revenue_monitor: wireDeclaration,
  };
  const wireContentV1 = { ...wireContentV2 };
  delete wireContentV1.government_revenue_monitor;

  const db = {
    from(table) {
      if (table === "theses") {
        return {
          select: () => ({
            eq: () => ({ eq: () => ({
              maybeSingle: () => Promise.resolve({ error: null, data: {
                id: THESIS_ID, current_version: 2, lifecycle_state: "active",
                subject_ref: theses.subjectToWire(theses.normalizeThesisSubject(SUBJECT)),
                created_at: "2026-09-01T00:00:00.000Z", updated_at: recordedAt,
              } }),
            }) }),
          }),
        };
      }
      return {
        select: () => ({
          eq: () => ({ eq: () => ({
            order: () => ({ limit: () => Promise.resolve({ error: null, data: [
              wireVersionRow(2, 1, "revise", wireContentV2, recordedAt),
              wireVersionRow(1, null, "create", wireContentV1, "2026-09-01T00:00:00.000Z"),
            ] }) }),
          }) }),
        }),
      };
    },
  };
  const read = await theses.readThesis(db, USER_A, THESIS_ID);
  assert.ok(read.ok, JSON.stringify(read));
  assert.ok(read.thesis.current.content.governmentRevenueMonitor);
  assert.deepEqual(read.thesis.current.content.governmentRevenueMonitor, declaration);
  // Prior immutable version keeps its exact legacy shape: no member, no nulls injected.
  const prior = read.thesis.history.find((item) => item.version === 1);
  assert.ok(prior);
  assert.equal("governmentRevenueMonitor" in prior.content, false);
  assert.deepEqual(Object.keys(prior.content).sort(), [
    "catalysts", "effectiveAt", "falsifiers", "horizon", "revisionNote", "risks", "schema", "statement", "title",
  ]);

  // A malformed or non-canonical member cannot enter an immutable snapshot.
  const badRead = await theses.readThesis(db, USER_A, THESIS_ID);
  assert.ok(badRead.ok); // control read still fine

  const malformedDb = {
    from(table) {
      if (table === "theses") return db.from(table);
      return {
        select: () => ({ eq: () => ({ eq: () => ({
          order: () => ({ limit: () => Promise.resolve({ error: null, data: [
            wireVersionRow(2, 1, "revise", { ...wireContentV2, government_revenue_monitor: { ...wireDeclaration, privacy_leak: "x" } }, recordedAt),
            wireVersionRow(1, null, "create", wireContentV1, "2026-09-01T00:00:00.000Z"),
          ] }) }),
        }) }) }),
      };
    },
  };
  const refused = await theses.readThesis(malformedDb, USER_A, THESIS_ID);
  assert.ok(!refused.ok);
  assert.equal(refused.status, "unavailable");
});

test("explicit null declaration is preserved; inputs are never mutated", () => {
  const withNull = theses.normalizeThesisContent(baseContent({ governmentRevenueMonitor: null }));
  assert.ok(withNull);
  assert.equal(withNull.governmentRevenueMonitor, null);

  const content = Object.freeze(baseContent({ governmentRevenueMonitor: validDeclaration() }));
  const snapshot = JSON.stringify(content);
  const normalized = theses.normalizeThesisContent(content);
  assert.ok(normalized);
  assert.equal(JSON.stringify(content), snapshot); // prior/input version untouched
  assert.notEqual(normalized.governmentRevenueMonitor, content.governmentRevenueMonitor);
});

test("applyThesisVersion carries the declaration on the existing optimistic RPC and refuses a foreign subject", async () => {
  const rpcCalls = [];
  const thesisDb = {
    rpc: async (name, args) => {
      rpcCalls.push({ name, args });
      return { data: [{
        status: "advanced",
        thesis_id: args.p_thesis_id,
        version: args.p_expected_version + 1,
        current_version: args.p_expected_version + 1,
        lifecycle_state: "active",
        replayed: false,
      }] };
    },
  };
  const input = {
    action: "revise", id: THESIS_ID, expectedVersion: 1,
    clientRequestId: "e0000000-0000-4000-8000-000000000001",
    subject: SUBJECT,
    content: baseContent({ governmentRevenueMonitor: validDeclaration() }),
  };
  const result = await theses.applyThesisVersion(thesisDb, USER_A, input);
  assert.ok(result.ok, JSON.stringify(result));
  assert.equal(result.status, "advanced");
  assert.equal(rpcCalls.length, 1);
  assert.equal(rpcCalls[0].name, "apply_thesis_version_v1");
  const wire = rpcCalls[0].args.p_content;
  assert.ok(wire.government_revenue_monitor);
  assert.equal(wire.government_revenue_monitor.schema, "government_revenue.monitor_declaration.v1");
  assert.deepEqual(wire.government_revenue_monitor.subject, theses.subjectToWire(theses.normalizeThesisSubject(SUBJECT)));
  assert.deepEqual(wire.government_revenue_monitor.input_refs, [REF_SHA, REF_GRW]);

  // A/B ownership/identity mismatch: a declaration pointing at a different
  // issuer can never ride this thesis's revision.
  const foreignSubject = { ...SUBJECT, key: "RTX", display: "RTX" };
  const foreign = await theses.applyThesisVersion(thesisDb, USER_A, {
    ...input,
    clientRequestId: "e0000000-0000-4000-8000-000000000002",
    content: baseContent({
      governmentRevenueMonitor: validDeclaration({ subject: foreignSubject }),
    }),
  });
  assert.ok(!foreign.ok);
  assert.equal(foreign.status, "invalid_payload");
  assert.equal(rpcCalls.length, 1); // no second RPC was issued
});

test("patched artifacts carry the declaration end-to-end (static checks)", () => {
  const route = fs.readFileSync(path.join(ROOT, "terminal", "app", "api", "thesis-saved-views", "route.ts"), "utf8");
  assert.ok(route.includes('"government_revenue"'), "route kind whitelist admits government_revenue");

  const sql = fs.readFileSync(path.join(ROOT, "supabase", "migrations", "0012_thesis_objects.sql"), "utf8");
  assert.ok(sql.includes("'government_revenue.monitor_declaration.v1'"), "schema marker validated in SQL");
  assert.ok(
    sql.includes("v_content := v_content || jsonb_build_object('government_revenue_monitor', v_govrev);"),
    "optional typed member merged into canonical v_content (fingerprint input)",
  );
  assert.ok(
    sql.includes("'schema','title','statement','catalysts','falsifiers','risks','horizon','effective_at','revision_note'\n     ])"),
    "legacy required-key fence untouched",
  );
  assert.ok(sql.includes("workspace-sha256:[0-9a-f]{64}|grw2-[0-9a-f]{24}"), "inputRef shape enforced in SQL");
  assert.ok(sql.includes("^[1-9][0-9]{0,8}$"), "finite bounded event versions enforced in SQL");
});

 test("review repair: baseline limits match SQL and opaque refs have no trailing controls", () => {
   const good=validDeclaration();
   assert.equal(govrev.normalizeGovernmentRevenueMonitor({...good,baselineEvents:[{recordId:"r",eventId:"e",version:1_000_000_000,knownAt:"2026-06-01T00:00:00.000Z"}]}),null);
   assert.equal(govrev.normalizeGovernmentRevenueMonitor({...good,inputRefs:[good.inputRefs[0]+"\n"]}),null);
 });

 test("review repair: original baseline cannot include knowledge after its cutoff", () => {
   const good=validDeclaration();
   assert.equal(govrev.normalizeGovernmentRevenueMonitor({...good,baselineEvents:[{recordId:"r",eventId:"e",version:1,knownAt:"2026-12-01T00:00:00.000Z"}]}),null);
   assert.equal(govrev.canonicalUtcTimestamp("0000-01-01T00:00:00.000Z"),null);
 });
