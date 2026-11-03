import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

if (process.argv.length !== 6) throw Error("Pass old summary, new summary, AAPL JSON, and the actual explorer Jinja template.");
const [oldSummary, newSummary, ticker] = process.argv.slice(2,5).map(file => JSON.parse(fs.readFileSync(file, "utf8")));
const template = fs.readFileSync(process.argv[5], "utf8");
function check(label, expression) {
  assert.ok(expression, label);
  console.log("PASS | " + label);
}
check("New render time, same observation blob and latest collection", oldSummary.rendered_at !== newSummary.rendered_at && oldSummary.source.observations_blob_sha1 === newSummary.source.observations_blob_sha1 && oldSummary.source.latest_session.at === newSummary.source.latest_session.at);
check("Both summary generations and ticker explicitly forbid financial influence and K3E", [oldSummary, newSummary, ticker].every(o => o.financial_influence === false && o.k3e_admissible === false));
const q = ticker.series.EPS["0q"], fy = ticker.series.EPS["0y"];
check("Same period-end, different horizons and contributor counts", q.at(-1).period_end === fy.at(-1).period_end && q.at(-1).average === 1.98895 && q.at(-1).analysts === 28 && fy.at(-1).average === 8.83838 && fy.at(-1).analysts === 40);
check("Undated identity and missing median remain distinct", ticker.identity_status === "undated" && q.at(-1).median === null);
check("Prior valid ticker point differs from prior global session", q.at(-2).at.slice(0,10) === "2026-10-20" && newSummary.source.prior_session.at.slice(0,10) === "2026-10-21");
const f = template.match(/function priorAvg\(pts, i\) \{[\s\S]*?\n  \}/)?.[0];
assert.ok(f, "pinned priorAvg implementation");
assert.ok(template.includes("var pctv = (p.average - prev) / Math.abs(prev)"), "pinned readout expression");
const priorAvg = vm.runInNewContext("(" + f + ")", {}, { timeout: 500 });
const prev = priorAvg(q, 1);
check("Defect reproduced: compared null period to dated period and produced a finite zero", q[0].period_end === null && q[1].period_end === "2026-09-30" && (q[1].average - prev) / Math.abs(prev) === 0);
console.log("Known defect reproduced. Required reader outcome is no comparable prior. This is an offline source check.");
