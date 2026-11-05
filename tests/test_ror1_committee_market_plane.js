"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const rendererFile = process.env.ROR1_RENDERER_FILE ||
  path.resolve(__dirname, "..", "site", "committee.html");
const text = fs.readFileSync(rendererFile, "utf8");
function extract(source) {
  const marker = "  function renderMarketPlane(d) {";
  const endMarker = "  // ── NW read layer: Web Health panel";
  const start = source.indexOf(marker);
  const end = source.indexOf(endMarker, start);
  return start >= 0 && end > start ? source.slice(start, end) : source;
}
const code = extract(text);
assert(code.includes("function renderMarketPlane(d)"), "Source renderer not found");
// A paired Jinja/template path cannot diverge on the user-visible fact copy.
if (!process.env.ROR1_RENDERER_FILE) {
  const companion = fs.readFileSync(
    path.resolve(__dirname, "..", "templates", "committee.html.j2"), "utf8");
  assert.equal(extract(companion), code, "Published/template market-plane renderer drift");
}

function render(source) {
  const classes = new Set();
  const strip = {
    innerHTML: "",
    style: { display: "none" },
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); }
    },
  };
  const esc = (value) => String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
  const fn = vm.runInNewContext(code + "\nrenderMarketPlane;", {
    document: { getElementById(id) { return id === "mp_strip" ? strip : null; } },
    esc,
  });
  fn(source);
  return strip;
}
const sample = () => ({
  schema: "neuralweb.market_plane.v1",
  asof: "2026-10-14",
  stale: false,
  verdict: {
    verdict: "MIXED", score: 50, label_en: "Mixed", label_zh: "混合",
    source_session: "2026-10-13",
    source_freshness: {
      any_input_stale: true,
      data_asof: "2026-10-13",
      expected_asof: "2026-10-13",
    },
  },
});

let count = 0;
function it(name, f) {
  try { f(); count++; process.stdout.write("PASS " + name + "\n"); }
  catch (err) { process.stderr.write("FAIL " + name + "\n"); throw err; }
}
it("date and delayed-input qualification accompany the unchanged Mixed score", () => {
  const html = render(sample()).innerHTML;
  assert(html.includes("Mixed"));
  assert(html.includes(">50</span>"));
  assert(html.includes("2026-10-13"));
  assert(html.includes("Some inputs late"));
  assert(html.includes("部分输入延迟"));
  assert(html.includes("As of "));
  assert(html.includes("截至"));
});
it("same-session explicit healthy input is dated but no fake warning", () => {
  const d = sample();
  d.asof = "2026-10-14";
  d.verdict.source_session = "2026-10-14";
  d.verdict.source_freshness.any_input_stale = false;
  const html = render(d).innerHTML;
  assert(html.includes("As of 2026-10-14"));
  assert(!html.includes("Some inputs late"));
  assert(!html.includes("Input health unverified"));
});
it("old payload is explicitly unverified rather than synthesized fresh", () => {
  const d = sample();
  delete d.verdict.source_session;
  delete d.verdict.source_freshness;
  const html = render(d).innerHTML;
  assert(html.includes("Source date unverified"));
  assert(html.includes("Input freshness unverified"));
  assert(!html.includes("As of 2026-10-14")); // processor date not passed off as observation
});
it("invalid or unsafe native source dates are not echoed", () => {
  const d = sample();
  d.verdict.source_session = "<script>alert(1)</script>";
  const html = render(d).innerHTML;
  assert(html.includes("Source date unverified"));
  assert(!html.includes("<script>"));
  assert(!html.includes("alert(1)"));
});
it("whole-plane stale marker is independent and preserved", () => {
  const d = sample(); d.stale = true;
  const el = render(d);
  assert(el.classList.contains("mp-stale"));
  assert(el.innerHTML.includes("stale"));
  assert(el.innerHTML.includes("Some inputs late"));
});
it("missing verdict remains harmless and does not assert all-clear", () => {
  const d = { schema: "neuralweb.market_plane.v1", stale: false, asof: "2026-10-14" };
  const html = render(d).innerHTML;
  assert(!html.includes("Risk-on"));
  assert(!html.includes("As of 2026-10-14"));
});
console.log("COMMITTEE_RENDERER_CHARACTERIZATION_TESTS=" + count);
