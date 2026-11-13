import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { describe, test } from "node:test";

const ROOT = process.env.ROR_FIXTURE_ROOT
  ? path.resolve(process.env.ROR_FIXTURE_ROOT)
  : fileURLToPath(new URL("../../", import.meta.url));
const SOURCES = [
  "templates/calculators/risk_of_ruin.html.j2",
  "site/tools/calculators/risk-of-ruin.html",
];

function calculatorScript(source) {
  const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)]
    .map(match => match[1])
    .filter(script => script.includes("function mulberry32(a)") && script.includes("function simulate(p)"));
  assert.equal(scripts.length, 1, "one complete actual calculator controller");
  return scripts[0];
}

// Controlled browser boundaries; the complete product controller and its actual
// serialized Worker computation execute unchanged. This is not a browser test.
function boot(source, options = {}) {
  let now = 0, nextTimer = 0;
  const timers = new Map(), elements = new Map(), copies = [], copyCompletions = [];
  const workers = [], idle = [], errors = [], bodyChildren = [];
  class Element {
    constructor(id) {
      this.id = id; this.value = ""; this._text = "—"; this.writes = [];
      this.style = {}; this.className = ""; this.events = new Map();
      this.disabled = id === "copy-result" &&
        /<button\b[^>]*id="copy-result"[^>]*\bdisabled(?:[=>\s])/.test(source);
      this.classes = new Set();
      this.classList = {
        add: value => this.classes.add(value),
        remove: value => this.classes.delete(value),
        contains: value => this.classes.has(value),
      };
    }
    get textContent() { return this._text; }
    set textContent(value) { this._text = String(value); this.writes.push(this._text); }
    addEventListener(type, callback) {
      const callbacks = this.events.get(type) || [];
      callbacks.push(callback); this.events.set(type, callbacks);
    }
    fire(type) { for (const callback of this.events.get(type) || []) callback({ target: this }); }
    select() {}
  }
  const get = id => {
    if (!elements.has(id)) elements.set(id, new Element(id));
    return elements.get(id);
  };
  const setTimer = (callback, delay) => {
    const id = ++nextTimer; timers.set(id, { at: now + delay, callback }); return id;
  };
  const tick = elapsed => {
    const end = now + elapsed;
    let executions = 0;
    while (true) {
      const next = [...timers.entries()]
        .filter(([, timer]) => timer.at <= end)
        .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
      if (!next) break;
      assert.ok(++executions < 1000, "bounded timer delivery");
      timers.delete(next[0]); now = next[1].at; next[1].callback();
    }
    now = end;
  };
  class Blob {
    constructor(parts) { this.source = parts.join(""); }
  }
  class Worker {
    constructor(blob) {
      if (options.constructorFails) throw new Error("controlled constructor failure");
      this.messages = []; this.postAttempts = 0; this.terminated = false;
      workers.push(this);
      const self = { postMessage: data => this.onmessage?.({ data }) };
      this.realm = vm.createContext({ self });
      vm.runInContext(blob.source, this.realm);
    }
    postMessage(message) {
      this.postAttempts++;
      if (options.postMessageFails) throw new Error("controlled postMessage failure");
      this.messages.push(structuredClone(message));
    }
    deliver(index) {
      const message = this.messages[index];
      assert.ok(message, "actual worker request exists before response delivery");
      this.realm.self.onmessage({ data: message });
    }
    fail() { this.onerror?.({ message: "controlled worker execution failure" }); }
    terminate() { this.terminated = true; }
  }
  const document = {
    getElementById: get,
    addEventListener: (type, callback) => {
      if (type === "DOMContentLoaded") document.ready = callback;
    },
    createElement: tag => new Element(tag),
    body: {
      appendChild: element => bodyChildren.push(element),
      removeChild: element => bodyChildren.splice(bodyChildren.indexOf(element), 1),
    },
    execCommand: command => {
      assert.equal(command, "copy");
      if (options.legacyThrows) throw new Error("controlled legacy copy failure");
      if (options.legacySuccess === false) return false;
      copies.push(bodyChildren.at(-1)?.value);
      return true;
    },
  };
  const navigator = {};
  if (options.clipboard !== "missing") {
    navigator.clipboard = {
      writeText: text => {
        copies.push(text);
        if (options.clipboard === "throw") throw new Error("controlled clipboard throw");
        if (options.clipboard === "reject") return Promise.reject(new Error("controlled clipboard rejection"));
        if (options.clipboard === "deferred") {
          return new Promise((resolve, reject) => copyCompletions.push({ resolve, reject }));
        }
        return Promise.resolve();
      },
    };
  }
  const window = {
    Worker: options.noWorker ? undefined : Worker,
    Blob,
    URL: { createObjectURL: blob => blob },
    requestIdleCallback: callback => idle.push(callback),
  };
  const context = vm.createContext({
    window, document, navigator, Worker, Blob,
    setTimeout: setTimer, clearTimeout: id => timers.delete(id),
    console: { error: (...args) => errors.push(args), log() {}, warn() {} },
  });
  vm.runInContext(calculatorScript(source), context);
  assert.equal(typeof document.ready, "function");
  document.ready();
  const set = (id, value) => { get(id).value = String(value); get(id).fire("input"); };
  const fill = (winRate, overrides = {}) => {
    for (const [id, value] of Object.entries({
      winrate: winRate, payoff: 1, riskpct: 2, ruindd: 50, trades: 500, ...overrides,
    })) set(id, value);
    tick(150);
  };
  const state = () => ({
    main: get("out-main").textContent,
    expectancy: get("out-exp").textContent,
    plain: get("out-plain").textContent,
    dd: get("out-dd").textContent,
    accounts: get("out-m").textContent,
    trades: get("out-n").textContent,
    disabled: get("copy-result").disabled,
    copied: get("copied").classList.contains("show"),
  });
  // Programmatic delivery also exercises the handler's eligibility guard;
  // native disabled-button behavior is independently asserted in each state.
  const copy = () => { get("copy-result").fire("click"); return copies.at(-1); };
  return {
    get, set, fill, tick, state, copy, copies, copyCompletions, workers, errors, bodyChildren,
    worker: workers[0],
    timerCount: () => timers.size,
    runIdle: () => idle.splice(0).forEach(callback => callback()),
  };
}

async function settlePromises() { await Promise.resolve(); await Promise.resolve(); }
function assertWithheld(h) {
  assert.equal(h.state().main, "—");
  assert.equal(h.state().disabled, true);
  assert.equal(h.state().copied, false);
  const requests = h.copies.length;
  h.copy();
  assert.equal(h.copies.length, requests, "no stale clipboard request");
}
function assertCompleted(h, main, expectancy) {
  assert.equal(h.state().main, main);
  assert.equal(h.state().expectancy, expectancy);
  assert.equal(h.state().disabled, false);
  assert.ok(h.state().plain.includes(main), "narrative and headline use one result");
}

for (const sourcePath of SOURCES) {
  const source = fs.readFileSync(path.join(ROOT, sourcePath), "utf8");
  describe(sourcePath, () => {
    test("initial invalid form withholds result and export", () => {
      const h = boot(source);
      assertWithheld(h);
      assert.match(h.state().plain, /win rate/i);
      assert.equal(h.workers[0].messages.length, 0);
    });

    test("completed all-win result is invalidated at edit and stays withheld during recomputation", () => {
      const h = boot(source);
      h.fill(100); h.worker.deliver(0);
      assertCompleted(h, "0.00%", "+1.00 R");
      assert.match(h.copy(), /Risk of ruin: 0\.00%.*expectancy \+1\.00 R/);
      h.set("winrate", 0);
      assertWithheld(h);
      assert.equal(h.state().expectancy, "—");
      assert.doesNotMatch(h.state().plain, /almost always survives|positive edge/);
      h.tick(150);
      assertWithheld(h);
      assert.equal(h.state().expectancy, "-1.00 R");
      assert.match(h.state().plain, /calculating.*current inputs/i);
      h.worker.deliver(1);
      assertCompleted(h, "100.0%", "-1.00 R");
      assert.match(h.state().plain, /severe.*negative edge/);
      assert.match(h.copy(), /Risk of ruin: 100\.0%.*expectancy -1\.00 R/);
    });

    test("obsolete response cannot paint during a valid-input debounce", () => {
      const h = boot(source);
      h.fill(0); h.set("winrate", 100); h.tick(100); h.worker.deliver(0);
      assertWithheld(h);
      h.tick(50); h.worker.deliver(1);
      assertCompleted(h, "0.00%", "+1.00 R");
    });

    test("obsolete response cannot paint during an invalid-input debounce", () => {
      const h = boot(source);
      h.fill(0); h.set("winrate", "invalid"); h.tick(100); h.worker.deliver(0);
      assertWithheld(h);
      h.tick(50);
      assertWithheld(h);
      assert.match(h.state().plain, /win rate/i);
      assert.equal(h.state().expectancy, "—");
    });

    test("an invalid form recovers only through its newest valid request", () => {
      const h = boot(source);
      h.fill(0); h.set("winrate", "invalid"); h.tick(150);
      h.worker.deliver(0); assertWithheld(h);
      h.set("winrate", 100); h.tick(150); assertWithheld(h);
      h.worker.deliver(1);
      assertCompleted(h, "0.00%", "+1.00 R");
    });

    test("reversed response order preserves the newest completed display and copy", () => {
      const h = boot(source);
      h.fill(100); h.set("winrate", 0); h.tick(150);
      h.worker.deliver(1);
      assertCompleted(h, "100.0%", "-1.00 R");
      const current = h.state();
      h.worker.deliver(0);
      assert.deepEqual(h.state(), current);
      assert.match(h.copy(), /100\.0%.*expectancy -1\.00 R/);
    });

    test("existing after-render sequence control rejects an older response", () => {
      const h = boot(source);
      h.fill(100); h.set("winrate", 0); h.tick(150); h.worker.deliver(0);
      assertWithheld(h);
      h.worker.deliver(1);
      assertCompleted(h, "100.0%", "-1.00 R");
    });

    test("duplicate current response cannot recommit a completed snapshot", () => {
      const h = boot(source);
      h.fill(0); h.worker.deliver(0);
      const writes = h.get("out-main").writes.length, current = h.state();
      h.worker.deliver(0);
      assert.deepEqual(h.state(), current);
      assert.equal(h.get("out-main").writes.length, writes);
    });

    for (const [id, value] of Object.entries({ winrate: 0, payoff: 2, riskpct: 3, ruindd: 60, trades: 501 })) {
      test("editing " + id + " immediately invalidates a completed snapshot", () => {
        const h = boot(source);
        h.fill(100); h.worker.deliver(0);
        h.set(id, value);
        assertWithheld(h);
        assert.equal(h.state().expectancy, "—");
      });
    }

    test("rapid edits coalesce into one current worker request", () => {
      const h = boot(source);
      h.fill(0);
      h.set("winrate", 20); h.tick(50);
      h.set("winrate", 40); h.tick(50);
      h.set("winrate", 100); h.tick(149);
      assert.equal(h.worker.messages.length, 1);
      assertWithheld(h);
      h.tick(1);
      assert.equal(h.worker.messages.length, 2);
      h.worker.deliver(0); assertWithheld(h);
      h.worker.deliver(1);
      assertCompleted(h, "0.00%", "+1.00 R");
    });

    test("worker failure during debounce renders the current form once", () => {
      const h = boot(source);
      h.fill(0); h.set("winrate", 100); h.tick(100);
      h.worker.fail();
      assert.equal(h.worker.terminated, true);
      assertCompleted(h, "0.00%", "+1.00 R");
      assert.equal(h.timerCount(), 0, "failure consumes the obsolete debounce");
      const writes = h.get("out-main").writes.length;
      h.tick(300); h.worker.fail(); h.worker.deliver(0);
      assertCompleted(h, "0.00%", "+1.00 R");
      assert.equal(h.get("out-main").writes.length, writes, "late worker errors/results do not repaint fallback");
      h.set("winrate", 0); assertWithheld(h); h.tick(150);
      assertCompleted(h, "100.0%", "-1.00 R");
      assert.equal(h.worker.messages.length, 1);
    });

    test("worker failure while current form is invalid cannot restore success", () => {
      const h = boot(source);
      h.fill(0); h.set("winrate", "invalid"); h.worker.fail();
      assertWithheld(h);
      assert.match(h.state().plain, /win rate/i);
      assert.equal(h.timerCount(), 0);
      h.worker.deliver(0); assertWithheld(h);
    });

    test("synchronous postMessage failure falls back once and ignores late onerror", () => {
      const h = boot(source, { postMessageFails: true });
      assert.doesNotThrow(() => h.fill(0));
      assertCompleted(h, "100.0%", "-1.00 R");
      assert.equal(h.worker.terminated, true);
      assert.equal(h.worker.postAttempts, 1);
      const writes = h.get("out-main").writes.length;
      h.worker.fail(); h.tick(300);
      assert.equal(h.get("out-main").writes.length, writes);
      h.set("winrate", 100); assertWithheld(h); h.tick(150);
      assertCompleted(h, "0.00%", "+1.00 R");
      assert.equal(h.worker.postAttempts, 1);
    });

    for (const option of ["noWorker", "constructorFails"]) {
      test(option + " keeps the synchronous fallback current across edits", () => {
        const h = boot(source, { [option]: true });
        h.fill(100); assertCompleted(h, "0.00%", "+1.00 R");
        h.set("winrate", 0); assertWithheld(h);
        h.tick(150); assertCompleted(h, "100.0%", "-1.00 R");
        assert.match(h.copy(), /100\.0%.*expectancy -1\.00 R/);
      });
    }

    test("late clipboard success from an older generation does not show current feedback", async () => {
      const h = boot(source, { clipboard: "deferred" });
      h.fill(100); h.worker.deliver(0); h.copy();
      assert.equal(h.copyCompletions.length, 1);
      h.set("winrate", 0); assertWithheld(h);
      h.copyCompletions[0].resolve(); await settlePromises();
      assert.equal(h.state().copied, false);
      h.tick(150); h.worker.deliver(1); h.copy();
      h.copyCompletions[1].resolve(); await settlePromises();
      assert.equal(h.state().copied, true);
      assert.match(h.copies.at(-1), /100\.0%.*expectancy -1\.00 R/);
    });

    test("late clipboard rejection from an older generation does not show feedback", async () => {
      const h = boot(source, { clipboard: "deferred" });
      h.fill(100); h.worker.deliver(0); h.copy();
      h.set("winrate", 0);
      h.copyCompletions[0].reject(new Error("controlled late rejection"));
      await settlePromises();
      assertWithheld(h);
    });

    for (const mode of ["reject", "throw"]) {
      test("clipboard " + mode + " never claims Copied", async () => {
        const h = boot(source, { clipboard: mode });
        h.fill(0); h.worker.deliver(0);
        assert.doesNotThrow(() => h.copy());
        await settlePromises();
        assert.equal(h.state().copied, false);
        assertCompleted(h, "100.0%", "-1.00 R");
      });
    }

    test("an old feedback timer cannot hide a new generation's fresh feedback", async () => {
      const h = boot(source);
      h.fill(100); h.worker.deliver(0); h.copy(); await settlePromises();
      assert.equal(h.state().copied, true);
      h.tick(1000); h.set("winrate", 0); h.tick(150); h.worker.deliver(1);
      h.copy(); await settlePromises();
      assert.equal(h.state().copied, true);
      h.tick(450);
      assert.equal(h.state().copied, true, "old generation's expiry has no authority");
      h.tick(1150);
      assert.equal(h.state().copied, false);
    });

    test("the latest repeated copy owns its feedback expiry", async () => {
      const h = boot(source);
      h.fill(0); h.worker.deliver(0); h.copy(); await settlePromises();
      h.tick(1000); h.copy(); await settlePromises();
      h.tick(600); assert.equal(h.state().copied, true);
      h.tick(1000); assert.equal(h.state().copied, false);
    });

    test("legacy copy succeeds only for a current complete result", () => {
      const h = boot(source, { clipboard: "missing" });
      h.fill(100); assertWithheld(h);
      h.worker.deliver(0);
      assert.match(h.copy(), /0\.00%.*expectancy \+1\.00 R/);
      assert.equal(h.state().copied, true);
      assert.equal(h.bodyChildren.length, 0);
      h.set("winrate", 0); assertWithheld(h);
    });

    for (const option of [{ legacySuccess: false }, { legacyThrows: true }]) {
      test("legacy copy failure " + Object.keys(option)[0] + " never claims success", () => {
        const h = boot(source, { clipboard: "missing", ...option });
        h.fill(0); h.worker.deliver(0); h.copy();
        assert.equal(h.state().copied, false);
        assert.equal(h.copies.length, 0);
        assert.equal(h.bodyChildren.length, 0);
      });
    }

    test("worker requests retain deterministic seed, account count and trade cap", () => {
      const h = boot(source);
      h.fill(0, { trades: "10,000" });
      const request = h.worker.messages[0];
      assert.equal(request.sim.M, 10000);
      assert.equal(request.sim.N, 1000);
      assert.equal(request.sim.seed, 0x9E3779B9);
      h.worker.deliver(0);
      assertCompleted(h, "100.0%", "-1.00 R");
      assert.equal(h.state().trades, "1,000");
      assert.match(h.state().plain, /capped at 1,000 trades/);
    });

    test("blank run length fields retain the existing defaults", () => {
      const h = boot(source);
      h.fill(0, { ruindd: "", trades: "" });
      h.worker.deliver(0);
      assertCompleted(h, "100.0%", "-1.00 R");
      assert.equal(h.state().dd, "50%");
      assert.equal(h.state().trades, "500");
    });

    test("middle-case results remain deterministic across generations", () => {
      const h = boot(source);
      h.fill(50); h.worker.deliver(0);
      const first = h.state(), firstCopy = h.copy();
      assert.ok(parseFloat(first.main) >= 1 && parseFloat(first.main) <= 99);
      h.set("winrate", 50); h.tick(150); h.worker.deliver(1);
      assert.equal(h.state().main, first.main);
      assert.equal(h.state().expectancy, first.expectancy);
      assert.equal(h.state().plain, first.plain);
      assert.equal(h.copy(), firstCopy);
    });

    test("the actual deferred mathematical self-check retains its controls", () => {
      const h = boot(source);
      h.runIdle();
      assert.deepEqual(h.errors, []);
    });
  });
}
