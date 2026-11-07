/* Render the actual Admin cost view using bounded API/DOM fixtures. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../admin/static/app.js"), "utf8");
const begin = source.indexOf("RENDER.cost = async () => {");
const end = source.indexOf("\n};", begin);
assert(begin >= 0 && end > begin, "actual cost renderer");
const helpers = ["fmtUSD", "fmtTokens"].map(name => {
  const match = source.match(new RegExp("const " + name + " = [^\\n]+"));
  assert(match, "actual formatting helper " + name);
  return match[0];
}).join("\n");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const view = {innerHTML: ""};
const context = {
  RENDER: {},
  $: selector => selector === "#view" ? view : null,
  api: async url => {assert.equal(url, "/api/cost"); return input;},
  esc: value => String(value ?? "").replace(/[&<>"]/g, char => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"
  })[char]),
  card: (title, body) => '<section data-card="' + title + '"><h2>' + title + "</h2>" + body + "</section>",
  fmtAge: value => String(value) + "h",
};
vm.createContext(context);
vm.runInContext(helpers + "\n" + source.slice(begin, end + 3), context, {timeout: 1000});
context.RENDER.cost().then(() => {
  assert(view.innerHTML.includes("30-day known cost estimate"));
  process.stdout.write(view.innerHTML);
}).catch(error => {console.error(error); process.exitCode = 1;});
