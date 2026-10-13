"""Behavioral holiday/client contract: run the real browser asset in Node."""
from pathlib import Path
import shutil
import subprocess


def test_live_holiday_client_behavior():
    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    assert node, "Node is required for the live holiday client behavior contract"
    result = subprocess.run(
        [node, "--test", str(root / "tests/live_holiday.test.mjs")],
        cwd=root, text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# cx-p3-polish-w3 N2 (seat commission R30 W3-A): paintChg honours an opt-in per-node flat cut-off
# (data-flat, set only by the crypto board chip). Inside it the chip reads an unsigned 0.0% with no
# tone class; every node without data-flat repaints exactly as before.
_W3_PAINT_JS = r"""
import fs from "node:fs";
import vm from "node:vm";
const src = fs.readFileSync(process.argv[2], "utf8");
const at = src.indexOf("function paintChg(");
let i = src.indexOf("{", at), depth = 0, end = -1;
for (; i < src.length; i++) {
  if (src[i] === "{") depth++;
  else if (src[i] === "}") { depth--; if (depth === 0) { end = i + 1; break; } }
}
const ctx = { isTnx: () => false, tnxBps: () => null };
vm.runInNewContext(src.slice(at, end) + "\nthis.paint = paintChg;", ctx);
const cases = JSON.parse(process.argv[3]);
const out = cases.map(([flat, chg, stale]) => {
  const cls = new Set(["nb-chg", "up"]);
  const el = {
    textContent: "+1.00%",
    dataset: flat === null ? {} : { flat },
    classList: { add: (...v) => v.forEach(x => cls.add(x)), remove: (...v) => v.forEach(x => cls.delete(x)), contains: x => cls.has(x) },
  };
  ctx.paint(el, chg, stale, { price: 1 });
  return [el.textContent, [...cls].sort().join(" ")];
});
process.stdout.write(JSON.stringify(out));
"""


def test_cxp3_w3_n2_live_repaint_flat_branch_is_opt_in():
    root = Path(__file__).resolve().parents[1]
    live = (root / "templates" / "live.js").read_text(encoding="utf-8")
    body = live[live.index("function paintChg("):]
    body = body[:body.index("\n  }\n") + 4]
    assert "el.dataset.flat" in body
    assert body.index("el.dataset.flat") < body.index("Math.abs(Number(chg)) < 0.005")
    crypto = (root / "templates" / "crypto.html.j2").read_text(encoding="utf-8")
    assert 'data-flat="{{ FLAT_CHG_PCT }}"' in crypto


def test_cxp3_w3_n2_live_repaint_flat_behaviour(tmp_path):
    import json

    root = Path(__file__).resolve().parents[1]
    node = shutil.which("node")
    assert node, "Node is required for the live repaint flat cut-off behaviour contract"
    script = tmp_path / "paint.mjs"
    script.write_text(_W3_PAINT_JS, encoding="utf-8")
    cases = [
        ["0.05", -0.03, False], ["0.05", 0.04, True], ["0.05", -0.06, False], ["0.05", 0.07, False],
        [None, -0.03, False], [None, 0.004, False], [None, 0.04, True],
    ]
    result = subprocess.run([node, str(script), str(root / "templates" / "live.js"), json.dumps(cases)],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == [
        ["0.0%", "nb-chg"], ["0.0%", "nb-chg stale"], ["-0.06%", "down nb-chg"], ["+0.07%", "nb-chg up"],
        ["-0.03%", "down nb-chg"], ["+0.00%", "nb-chg up"], ["+0.04%", "nb-chg stale up"],
    ]
