// Executes the actual calculator script from both checked-in artifacts.
// Text/event adapter plus stub-success Copy handler paths; no native clipboard proof.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

const SOURCES = [
  'templates/calculators/risk_reward.html.j2',
  'site/tools/calculators/risk-reward.html',
];

const WARNING =
  'Note: your target and stop appear to be on the same side of your entry. ' +
  'Check the prices. ';

// Fixed expected-output fixtures, not a duplicate calculation.
const SUMMARY = new Map([
  [null,
    'Risk-to-Reward: 3.0:1 · breakeven 25.0% win rate — mastermind-x.com'],
  [40,
    'Risk-to-Reward: 3.0:1 · breakeven 25.0% win rate' +
    ' · expectancy +0.60 R — mastermind-x.com'],
  [0,
    'Risk-to-Reward: 3.0:1 · breakeven 25.0% win rate' +
    ' · expectancy -1.00 R — mastermind-x.com'],
]);

const DIRECTIONS = [
  { dir: 'long', S: 95, valid: 115, warning: 85 },
  { dir: 'short', S: 105, valid: 85, warning: 115 },
];

function loadClient(path, copyMode = null) {
  assert.ok([null, 'clipboard-api', 'legacy'].includes(copyMode));
  const source = readFileSync(
    new URL(`../../${path}`, import.meta.url), 'utf8',
  ).replace(/\r\n/g, '\n');

  const scripts = [...source.matchAll(
    /<script\b[^>]*>([\s\S]*?)<\/script>/gi,
  )].map(match => match[1]).filter(script =>
    script.includes('function compute(inp)') &&
    script.includes('function copyLine()'),
  );
  assert.equal(scripts.length, 1, `${path}: unique calculator script`);

  // Fail closed if the source structure changes. Only expose references;
  // do not replace compute, render, copyLine, or their lexical dependencies.
  const anchor = '    render();\n  });';
  assert.equal(
    scripts[0].split(anchor).length, 2,
    `${path}: unique final-render adapter seam`,
  );
  const instrumented = scripts[0].replace(anchor, `
    globalThis.__riskRewardTest = {
      compute: compute,
      copyLine: copyLine,
      current: function(){ return last; }
    };
${anchor}`);

  const ids = [
    'entry', 'stop', 'target', 'winrate',
    'out-main', 'out-plain', 'out-breakeven',
    'out-reward', 'out-risk', 'out-exp',
    'copy-result', 'copied', 'copy-fail', 'copy-manual', 'copy-manual-text', 'copy-manual-select',
  ];
  const nodes = Object.fromEntries(ids.map(id => [id, {
    value: '',
    textContent: '',
    className: '',
    listeners: new Map(),
    addEventListener(type, fn) {
      assert.equal(this.listeners.has(type), false, `${id}: duplicate ${type}`);
      this.listeners.set(type, fn);
    },
  }]));

  // Only the browser surfaces used by the current Copy handler are supported.
  // Trace the boundary arguments, never supply expected summary text to the client.
  const trace = [];
  const created = new Set();
  const attached = new Set();
  const pending = [];
  const timers = [];
  const violations = [];
  const copiedClasses = new Set();
  let selected = null;
  nodes.copied.classList = Object.freeze({
    add(token) {
      assert.equal(token, 'show', 'unsupported copied.classList.add');
      copiedClasses.add(token);
    },
    remove(token) {
      assert.equal(token, 'show', 'unsupported copied.classList.remove');
      copiedClasses.delete(token);
    },
  });
  const documentTransport = {
    createElement(tag) {
      assert.equal(copyMode, 'legacy', 'unexpected legacy fallback');
      assert.equal(tag, 'textarea', 'unsupported element');
      const ta = Object.seal({
        value: '',
        style: {},
        setAttribute(name,value) { assert.equal(name,'readonly'); assert.equal(value,''); },
        select() {
          assert.ok(attached.has(this), 'select requires an attached textarea');
          selected = this;
          trace.push({ op: 'select', text: this.value });
        },
      });
      created.add(ta);
      trace.push({ op: 'createElement', tag });
      return ta;
    },
    body: Object.freeze({
      appendChild(ta) {
        assert.ok(created.has(ta), 'append requires this adapter\'s textarea');
        assert.equal(attached.has(ta), false, 'textarea already attached');
        attached.add(ta);
        trace.push({ op: 'appendChild', text: ta.value });
        return ta;
      },
      removeChild(ta) {
        assert.ok(attached.delete(ta), 'remove requires an attached textarea');
        trace.push({ op: 'removeChild', text: ta.value });
        if (selected === ta) selected = null;
        return ta;
      },
    }),
    execCommand(command) {
      // Production catches execCommand exceptions. Preserve violations for
      // a second assertion outside that catch so unsupported calls cannot pass.
      try {
        assert.equal(copyMode, 'legacy');
        assert.equal(command, 'copy', 'unsupported execCommand');
        assert.ok(attached.has(selected), 'copy requires selected attached text');
      } catch (error) {
        violations.push(error.message);
        throw error;
      }
      trace.push({ op: 'execCommand', command, text: selected.value });
      return true; // Simulated successful legacy transport only.
    },
  };

  let ready;
  const errors = [];
  const context = vm.createContext({
    navigator: copyMode === 'clipboard-api' ? {
      clipboard: {
        writeText(text) {
          trace.push({ op: 'writeText', text });
          const resolved = Promise.resolve();
          pending.push(resolved);
          return resolved; // Simulated successful Clipboard API only.
        },
      },
    } : {},
    setTimeout(fn) {
      assert.equal(typeof fn, 'function');
      timers.push(fn);
      return timers.length; // Virtual timers, not real elapsed-time proof.
    },
    clearTimeout() {},
    document: {
      ...documentTransport,
      getElementById(id) {
        assert.ok(nodes[id], `unexpected element ${id}`);
        return nodes[id];
      },
      addEventListener(type, fn) {
        assert.equal(type, 'DOMContentLoaded');
        assert.equal(ready, undefined);
        ready = fn;
      },
    },
    console: { error: (...args) => errors.push(args.join(' ')) },
  });
  new vm.Script(instrumented, { filename: path })
    .runInContext(context, { timeout: 1000 });
  assert.equal(typeof ready, 'function');
  ready();
  assert.deepEqual(errors, [], `${path}: embedded worked examples`);

  const api = context.__riskRewardTest;
  assert.equal(typeof api.compute, 'function');
  assert.equal(typeof api.copyLine, 'function');
  for (const id of ['entry', 'stop', 'target', 'winrate']) {
    assert.equal(typeof nodes[id].listeners.get('input'), 'function');
  }

  return {
    nodes,
    transport: { trace, attachedCount: () => attached.size },
    async clickCopy() {
      assert.notEqual(copyMode, null, 'choose an explicit successful transport');
      const click = nodes['copy-result'].listeners.get('click');
      assert.equal(typeof click, 'function', 'real Copy callback was registered');
      click.call(nodes['copy-result']);
      await Promise.all(pending.splice(0));
      assert.deepEqual(violations, [], 'unsupported legacy transport operation');
      for (const fn of timers.splice(0)) fn();
    },
    copy: () => api.copyLine(),
    input({ E, S, T, w = null }) {
      for (const [id, value] of Object.entries({
        entry: E, stop: S, target: T, winrate: w,
      })) nodes[id].value = value == null ? '' : String(value);

      // Run the real registered input callback, which calls real render()
      // and compute(), including the real assignment to last on failure.
      nodes.target.listeners.get('input')();
      return api.current();
    },
  };
}

async function assertCopyClick(client, copyMode, text) {
  assert.equal(client.transport.attachedCount(), 0);
  const before = client.transport.trace.length;
  await client.clickCopy();
  assert.deepEqual(client.transport.trace.slice(before),
    copyMode === 'clipboard-api' ? [
      { op: 'writeText', text },
    ] : [
      { op: 'createElement', tag: 'textarea' },
      { op: 'appendChild', text },
      { op: 'select', text },
      { op: 'execCommand', command: 'copy', text },
      { op: 'removeChild', text },
    ],
    'the real Copy callback must send the exact expected summary once',
  );
  assert.equal(client.transport.attachedCount(), 0, 'temporary textarea removed');
}

function checkFixture(client, direction, target, w, warning) {
  const got = client.input({ E: 100, S: direction.S, T: target, w });
  assert.equal(got.ok, true);
  assert.equal(got.dir, direction.dir);
  assert.equal(got.targetWarn, warning);
  assert.equal(got.RR, 3);
  assert.equal(got.breakevenWin, 25);
  assert.equal(got.riskPer, 5);
  assert.equal(got.rewardPer, 15);
  assert.equal(got.hasWinRate, w !== null);
  if (w !== null) {
    const expected = w === 40 ? 0.6 : -1;
    assert.ok(Math.abs(got.expectancyR - expected) < 1e-12);
  }

  assert.equal(
    client.copy(),
    (warning ? WARNING : '') + SUMMARY.get(w),
  );
  assert.equal(
    client.nodes['out-plain'].textContent.startsWith(WARNING), warning,
    'visible and copied warning must agree',
  );
  assert.equal(client.nodes['out-main'].textContent, '3.0');
}

for (const path of SOURCES) {
  test(`${path}: initial empty inputs cannot copy`, () => {
    assert.equal(loadClient(path).copy(), '');
  });

  for (const direction of DIRECTIONS) {
    for (const w of [null, 40]) {
      const label = w === null ? 'absent win rate' : '40% win rate';

      test(`${path}: warning ${direction.dir}, ${label}`, () => {
        checkFixture(
          loadClient(path), direction, direction.warning, w, true,
        );
      });

      test(`${path}: valid ${direction.dir}, ${label} stays unchanged`, () => {
        checkFixture(
          loadClient(path), direction, direction.valid, w, false,
        );
      });

      test(`${path}: ${direction.dir}, ${label}, warning → valid → warning`, () => {
        const client = loadClient(path);
        checkFixture(client, direction, direction.warning, w, true);
        checkFixture(client, direction, direction.valid, w, false);
        checkFixture(client, direction, direction.warning, w, true);
      });
    }

    for (const warning of [false, true]) {
      test(`${path}: ${direction.dir}, warning=${warning}, 0% is valid`, () => {
        checkFixture(
          loadClient(path), direction,
          warning ? direction.warning : direction.valid,
          0, warning,
        );
      });
    }

    test(`${path}: ${direction.dir} invalid inputs clear prior copy`, () => {
      const client = loadClient(path);
      const base = { E: 100, S: direction.S, T: direction.valid, w: 40 };
      const invalid = [
        ['zero entry', { ...base, E: 0 }],
        ['zero stop', { ...base, S: 0 }],
        ['zero target', { ...base, T: 0 }],
        ['stop equals entry', { ...base, S: 100 }],
        ['target equals entry', { ...base, T: 100 }],
      ];

      for (const [label, input] of invalid) {
        checkFixture(client, direction, direction.valid, 40, false);
        const got = client.input(input);
        assert.equal(got.ok, false, label);
        assert.equal(client.copy(), '', `${label}: no stale summary`);
        assert.equal(client.nodes['out-main'].textContent, '—', label);
      }

      // A failed calculation must not permanently suppress later valid copy.
      checkFixture(client, direction, direction.valid, 40, false);
    });
  }
}

// Additional contract case 5 coverage, using the same two actual artifacts.
for (const path of SOURCES) {
  for (const copyMode of ['clipboard-api', 'legacy']) {
    test(`${path}: ${copyMode}, initial empty Copy does not write`, async () => {
      const client = loadClient(path, copyMode);
      await client.clickCopy();
      assert.deepEqual(client.transport.trace, []);
      assert.equal(client.transport.attachedCount(), 0);
    });

    for (const direction of DIRECTIONS) {
      for (const w of [null, 40]) {
        const label = w === null ? 'absent win rate' : '40% win rate';
        test(`${path}: ${copyMode}, warning ${direction.dir}, ${label}`,
          async () => {
            const client = loadClient(path, copyMode);
            const got = client.input({
              E: 100, S: direction.S, T: direction.warning, w,
            });
            assert.equal(got.ok, true);
            assert.equal(got.targetWarn, true);
            assert.ok(client.nodes['out-plain'].textContent.startsWith(WARNING));
            await assertCopyClick(client, copyMode, WARNING + SUMMARY.get(w));
          },
        );
      }

      test(`${path}: ${copyMode}, ${direction.dir} invalidation does not write`,
        async () => {
          const client = loadClient(path, copyMode);
          const base = { E: 100, S: direction.S, T: direction.valid, w: 40 };
          const invalid = [
            ['zero entry', { ...base, E: 0 }],
            ['zero stop', { ...base, S: 0 }],
            ['zero target', { ...base, T: 0 }],
            ['stop equals entry', { ...base, S: 100 }],
            ['target equals entry', { ...base, T: 100 }],
          ];
          for (const [label, input] of invalid) {
            assert.equal(client.input(base).ok, true);
            await assertCopyClick(client, copyMode, SUMMARY.get(40));
            const priorTrace = client.transport.trace.slice();
            assert.equal(client.input(input).ok, false, label);
            await client.clickCopy();
            assert.deepEqual(client.transport.trace, priorTrace,
              `${label}: neither stale write nor legacy textarea work`);
            assert.equal(client.transport.attachedCount(), 0, label);
          }
          assert.equal(client.input(base).ok, true);
          await assertCopyClick(client, copyMode, SUMMARY.get(40));
        },
      );
    }
  }
}

// Whole-controller copy feedback lifecycle; synthetic DOM, not native clipboard.
function app(path, mode='modern'){
 const src=readFileSync(new URL('../../'+path,import.meta.url),'utf8');
 const scripts=[...src.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]).filter(x=>x.includes('function compute(inp)')&&x.includes('function copyLine()'));
 assert.equal(scripts.length,1);
 const nodes={};const classes=new Set();const writes=[];const pending=[];const timers=new Map();const oldTimers=[];const attached=new Set();let ready,legacyCount=0,sequence=0;
 function node(id){return nodes[id] ||= {value:'',hidden:true,textContent:'',className:'',listeners:{},style:{},addEventListener(k,f){this.listeners[k]=f},classList:{add(x){classes.add(x)},remove(x){classes.delete(x)}},setAttribute(){},select(){this.selected=true},focus(){this.focused=true}};}
 for(const [id,value] of Object.entries({entry:'100',stop:'95',target:'115',winrate:'40'}))node(id).value=value;
 const document={getElementById:node,addEventListener(k,f){ready=f},createElement(){return {value:'',style:{},setAttribute(){},select(){}}},body:{appendChild(x){attached.add(x)},removeChild(x){assert.ok(attached.delete(x))}},execCommand(){legacyCount++;if(mode==='legacy-throw')throw Error('denied');return mode==='legacy-ok'}};
 const navigator=mode.startsWith('legacy')?{}:{clipboard:{writeText(text){writes.push(text);if(mode==='throw')throw Error('denied');return new Promise((resolve,reject)=>pending.push({resolve,reject}));}}};
 vm.runInNewContext(scripts[0],{document,navigator,console,setTimeout(fn){const id=++sequence;timers.set(id,fn);oldTimers.push(fn);return id},clearTimeout(id){timers.delete(id)}},{timeout:1000});ready();
 return {nodes,node,classes,writes,pending,timers,oldTimers,attached,get legacyCount(){return legacyCount},click(){node('copy-result').listeners.click()},input(id,value){node(id).value=value;node(id).listeners.input()},manual(){node('copy-manual-select').listeners.click()}};
}
const flush=async()=>{await Promise.resolve();await Promise.resolve()};
for(const [name,file] of [['template',SOURCES[0]],['page',SOURCES[1]]]){
 test(`${name} modern success only after acknowledgement`,async()=>{let a=app(file);a.click();assert.ok(!a.classes.has('show'));assert.match(a.writes[0],/expectancy \+0.60 R/);a.pending[0].resolve();await flush();assert.ok(a.classes.has('show'));});
 test(`${name} modern rejection offers manual text, no fallback`,async()=>{let a=app(file);a.click();a.pending[0].reject(Error('denied'));await flush();assert.ok(!a.classes.has('show'));assert.equal(a.node('copy-manual').hidden,false);assert.equal(a.node('copy-manual-text').value,a.writes[0]);assert.equal(a.legacyCount,0);a.manual();assert.ok(a.node('copy-manual-text').focused&&a.node('copy-manual-text').selected);});
 test(`${name} synchronous modern failure`,()=>{let a=app(file,'throw');assert.doesNotThrow(()=>a.click());assert.equal(a.node('copy-fail').hidden,false);assert.ok(!a.classes.has('show'));});
 for(const mode of ['legacy-ok','legacy-false','legacy-throw'])test(`${name} ${mode}`,()=>{let a=app(file,mode);a.click();assert.equal(a.classes.has('show'),mode==='legacy-ok');assert.equal(a.attached.size,0);assert.equal(a.node('copy-manual').hidden,mode==='legacy-ok');});
 for(const outcome of ['resolve','reject'])test(`${name} input invalidates delayed ${outcome}`,async()=>{let a=app(file);a.click();a.input('target','120');a.pending[0][outcome]();await flush();assert.ok(!a.classes.has('show'));assert.equal(a.node('copy-manual').hidden,true);assert.equal(a.node('copy-manual-text').value,'');});
 test(`${name} older receipt cannot overwrite newer failure`,async()=>{let a=app(file);a.click();a.click();a.pending[1].reject();await flush();a.pending[0].resolve();await flush();assert.ok(!a.classes.has('show'));assert.equal(a.node('copy-manual').hidden,false);});
 test(`${name} stale timer cannot erase newer success`,async()=>{let a=app(file);a.click();a.pending[0].resolve();await flush();let stale=a.oldTimers[0];a.click();a.pending[1].resolve();await flush();stale();assert.ok(a.classes.has('show'));assert.equal(a.timers.size,1);});
 test(`${name} input clears success and invalid copy makes no write`,async()=>{let a=app(file);a.click();a.pending[0].resolve();await flush();a.input('entry','');assert.ok(!a.classes.has('show'));a.click();assert.equal(a.writes.length,1);assert.equal(a.node('copy-manual').hidden,true);});
 test(`${name} same-side warning and recovery preserved`,async()=>{let a=app(file);a.input('target','85');a.click();assert.match(a.writes[0],/^Note:.*same side/);a.pending[0].reject();await flush();assert.equal(a.node('copy-manual-text').value,a.writes[0]);a.input('target','115');a.click();assert.match(a.writes[1],/^Risk-to-Reward:/);a.pending[1].resolve();await flush();assert.ok(a.classes.has('show'));assert.equal(a.node('copy-manual').hidden,true);});
}
