#!/usr/bin/env node
// Characterizes existing source only. It is not a production fix or browser test.
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");
const base = __dirname;
const sourcePath = process.argv[2] || path.join(base, "source_inputs/confluence_screener.html.j2");
const outputPath = process.argv[3] || path.join(base, "CONFLUENCE_SOURCE_CHARACTERIZATION.json");
const fixture = JSON.parse(fs.readFileSync(path.join(base, "CONFLUENCE_HYDRATION_FIXTURES.json"), "utf8"));
const source = fs.readFileSync(sourcePath, "utf8");
const sourceHash = crypto.createHash("sha256").update(source, "utf8").digest("hex");
assert.equal(sourceHash, fixture.source_sha256, "Exact pinned template must match");
const start = source.indexOf("function bilingual");
const end = source.indexOf("function attemptHydrate", start);
assert(start >= 0 && end > start, "Expected contiguous helper boundary");
const helpers = source.slice(start, end);
assert(!/\b(fetch|attemptHydrate|MDXAuth)\s*\(/.test(helpers), "No network or auth helpers admitted");
class Node {
  constructor(tag, document) {
    this.tag = tag; this.doc = document; this.nodes = []; this.style = {};
    this.className = ""; this.attrs = {}; this.detached = false; this._text = "";
  }
  get children() { return this.nodes.filter(n => n.tag !== "#text"); }
  get textContent() { return this._text + this.nodes.map(n => n.textContent).join(""); }
  set textContent(value) { this.nodes = []; this._text = String(value); }
  appendChild(node) {
    if (node.tag === "#fragment") {
      this.nodes.push(...node.nodes); node.nodes = [];
    } else this.nodes.push(node);
    return node;
  }
  getAttribute(name) { return this.attrs[name] || null; }
  replaceWith(node) {
    assert(!this.detached, "A wall cannot be replaced twice");
    this.detached = true;
    this.doc.replacements.push({ combo_id: this.attrs["data-confluence-combo"], node });
  }
  querySelector(selector) {
    const wanted = selector.slice(1);
    return this.nodes.find(n => n.className.split(" ").includes(wanted)) || null;
  }
}
function walk(node, fn) { fn(node); node.nodes.forEach(n => walk(n, fn)); }
function runCase(test) {
  const doc = { walls: [], replacements: [] };
  doc.createElement = tag => new Node(tag, doc);
  doc.createDocumentFragment = () => new Node("#fragment", doc);
  doc.createTextNode = text => { const n = new Node("#text", doc); n.textContent = text; return n; };
  doc.walls = test.wall_ids.map(id => { const n = new Node("div", doc); n.attrs["data-confluence-combo"] = id; return n; });
  doc.band = new Node("div", doc);
  ["cb-tx", "cb-sub", "btn"].forEach(c => { const n = new Node("div", doc); n.className = c; n.textContent = "Original fixture"; doc.band.appendChild(n); });
  doc.querySelectorAll = selector => {
    assert.equal(selector, "[data-confluence-combo]");
    return doc.walls.filter(n => !n.detached);
  };
  doc.getElementById = id => id === "confluence-paid-cta" ? doc.band : null;
  const context = { document: doc, hydrated: false };
  vm.createContext(context);
  vm.runInContext(helpers, context, { timeout: 1000, filename: fixture.source_path + "#pure-dom-helpers" });
  const payload = { schema: test.payload_schema || "tier_payload.v1", page: "confluence_screener", gated: true, required_tier: "essential", built: test.built, combos: test.combos };
  context.fixturePayload = JSON.parse(JSON.stringify(payload));
  let error;
  try { vm.runInContext("hydrate(fixturePayload)", context, { timeout: 1000 }); }
  catch (e) { error = e.message; }
  const rendered = doc.replacements.map(r => {
    const tickerLinks = [];
    walk(r.node, n => { if (n.className === "tkr") tickerLinks.push({ href: n.href, text: n.textContent }); });
    return { combo_id: r.combo_id, ticker_links: tickerLinks, text: r.node.textContent };
  });
  const observed = {
    replacements: doc.replacements.length,
    remaining: doc.walls.filter(n => !n.detached).length,
    hydrated: context.hydrated,
    all_visible: doc.band.textContent.includes("All matching stocks available to your plan are visible above."),
    no_match_message: rendered.some(r => r.text.includes("No stock matches this one today.")),
    ...(error ? { error } : {})
  };
  for (const [key, expected] of Object.entries(test.expected_current)) {
    assert.deepEqual(observed[key], expected, test.id + ": existing behavior changed for " + key);
  }
  return { id: test.id, observed, rendered, required_future: test.required_future };
}
const results = fixture.cases.map(runCase);
const report = {
  status: "CURRENT_HYDRATOR_HAZARDS_REPRODUCED_NOT_FIX_ACCEPTANCE",
  source: { repository: fixture.source_repo, commit: fixture.source_commit, path: fixture.source_path, sha256: sourceHash },
  extraction: { first_line: source.slice(0, start).split("\n").length, end_exclusive_line: source.slice(0, end).split("\n").length, helper_sha256: crypto.createHash("sha256").update(helpers).digest("hex") },
  execution: { runtime: process.version, environment: "Node vm and minimal fake DOM", network_calls: 0, auth_calls: 0, browser_playback: false, installed_runtime_acceptance: false },
  cases: results,
  limits: ["No current production payload or account accessed.", "Current source only, without modifying helpers.", "Public generation and recipe context are controlled fixture declarations, not existing consumed DOM fields.", "Future identity and atomic reconciliation requirements remain implementation work."]
};
fs.writeFileSync(outputPath, JSON.stringify(report, null, 2) + "\n");
process.stdout.write(JSON.stringify({ status: report.status, cases: results.length, source_sha256: sourceHash, output: outputPath }) + "\n");
