/* Assemble an offline reference from current editable Paper exports and plain DOM code. */
const fs = require('node:fs');
const path = require('node:path');
const local = path.join(__dirname, 'source-input.json');
let input;
if (fs.existsSync(local)) input = JSON.parse(fs.readFileSync(local, 'utf8'));
else {
  const dir = path.join(__dirname, '..');
  const read = p => fs.readFileSync(path.join(dir, p), 'utf8');
  const manifest = JSON.parse(read('manifest.json'));
  input = { boards: manifest.boards, nodes: manifest.r32_nodes, tokens: JSON.parse(read('tokens.snapshot.json')), r30: JSON.parse(read('fixtures.json')), r31: JSON.parse(read('r31/fixtures.json')), contracts: JSON.parse(read('interaction_contracts.json')), exports: {} };
  for (const k of Object.keys(input.boards)) {
    const raw = read('jsx/' + k + '.paper.jsx');
    input.exports[k] = raw.slice(raw.indexOf('return ') + 7, raw.lastIndexOf(';'));
  }
}
function esc(x) { return String(x).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
function jsxToHtml(raw) {
  let text = raw.trim().replace(/^\(\s*/, '').replace(/\s*\)$/, '');
  text = text.replace(/style=\{\{([\s\S]*?)\}\}/g, (_, body) => {
    const pairs = [...body.matchAll(/([A-Za-z][\w]*):\s*('(?:\\.|[^'])*'|"(?:\\.|[^"])*"|-?\d+(?:\.\d+)?)/g)];
    let css = '';
    for (const [, prop, rawValue] of pairs) {
      let value = /^['"]/.test(rawValue) ? rawValue.slice(1,-1).replace(/\\'/g,"'").replace(/\\"/g,'"') : rawValue;
      const name = prop.replace(/[A-Z]/g, m => '-' + m.toLowerCase()).replace(/^moz-/, '-moz-').replace(/^webkit-/, '-webkit-');
      css += name + ':' + value + ';';
    }
    return 'style="' + esc(css) + '"';
  });
  text = text.replace(/\bid="([^"]+)"/g, 'id="$1" data-paper-id="$1"');
  const attrs = ['strokeWidth','strokeLinecap','strokeLinejoin','strokeDasharray','strokeDashoffset','fillRule','clipRule','clipPath','fillOpacity','strokeOpacity','textAnchor','dominantBaseline','fontSize','fontFamily','fontWeight','letterSpacing'];
  for (const name of attrs) text = text.replace(new RegExp('\\b' + name + '=', 'g'), name.replace(/[A-Z]/g, m=>'-'+m.toLowerCase()) + '=');
  text = text.replace(/\{['"]\s['"]\}/g, ' ').replace(/\{\/\*[\s\S]*?\*\/\}/g,'');
  text = text.replace(/<div\b([^>]*?)\/>/g, '<div$1></div>');
  text = text.replace(/>\s+</g,'><').replace(/>\s+([^<>\n]+)\s+</g,(_,value)=>'>'+value.trim()+'<');
  if (/style=\{|\{\{/.test(text)) throw new Error('Unconverted JSX');
  return text;
}
function extract(html, id) {
  const start = html.indexOf('<div id="' + id + '"');
  if (start < 0) throw new Error('Missing Paper node ' + id);
  const tags = /<\/?div\b[^>]*>/g; tags.lastIndex = start; let depth = 0, m;
  while ((m=tags.exec(html))) { depth += m[0].startsWith('</') ? -1 : 1; if (!depth) return html.slice(start, tags.lastIndex); }
  throw new Error('Unbalanced Paper node ' + id);
}
const html = Object.fromEntries(Object.entries(input.exports).map(([k,v])=>[k,jsxToHtml(v)]));
const routeKeys = ['bonds','curve','credit','capital','transmission','scenario','replay','saved'];
const routes = Object.fromEntries(routeKeys.map(k=>[k,extract(html[k],input.boards[k].body)]));
const bindings = {
  value:['overlays','662W-1'], calculation:['overlays','663U-1'], evidence:['overlays','6644-1'], conditions:['overlays','665W-1'],
  financing:['depth','6BMD-1'], cash:['depth','6BRC-1'], missingCash:['depth','6BVT-1'], hedge:['tools','669F-1'], cds:['tools','66DX-1'], issuer:['tools','66CC-1'],
  filters:['research_tools','67NJ-1'], calendar:['research_tools','67OU-1'], model:['research_tools','67QO-1'], outcome:['research_tools','67RX-1'], structure:['depth','6B78-1'],
  flows:['continuity','6C2T-1'], pipes:['continuity','6CZY-1'], save:['continuity','6CEV-1'], compare:['continuity','6CLB-1'], readUnavailable:['continuity','6CML-1'], conflict:['continuity','6E4N-1'],
  paths:['continuity',input.nodes.pathCompare], draft:['continuity',input.nodes.draftReview], mismatch:['continuity',input.nodes.contextMismatch], eventReview:['continuity',input.nodes.triggerFollowthrough]
};
const tools = Object.fromEntries(Object.entries(bindings).map(([name,[board,id]])=>[name,extract(html[board],id)]));
const specimens = {routes,tools,bindings,boards:input.boards,nodes:input.nodes,fixtures:{r30:input.r30,r31:input.r31},contracts:input.contracts};
const tokens = input.tokens.used_tokens.map(t=>t.name + ':' + (t.name==='--font-ui'?'Inter,system-ui,sans-serif':t.value) + ';').join('');
const css = fs.readFileSync(path.join(__dirname,'reference.css'),'utf8');
const logic = fs.readFileSync(path.join(__dirname,'reference-logic.js'),'utf8');
const app = fs.readFileSync(path.join(__dirname,'reference-app.js'),'utf8');
const page = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>Mastermind · Bonds & Transmission · Interactive reference</title><style>:root{'+tokens+'}'+css+'</style></head><body><a class="skip-link" href="#page">Skip to research</a><div class="app-shell"><aside class="sidebar"><div class="brand"><span class="brand-mark">M</span> MASTERMIND</div><div class="nav-label">BONDS & TRANSMISSION</div><nav id="route-nav" aria-label="Research workspaces"></nav><div class="sidebar-bottom"><button id="review-states" class="button full">Review implementation states</button><div class="reference-note">Interactive design reference<br>Synthetic market values<br>Drafts stay in this tab</div></div></aside><div class="main-column"><header class="app-header"><button id="mobile-nav" class="button mobile-only" aria-label="Open workspace navigation" aria-expanded="false">☰</button><div id="breadcrumb">Markets / Bonds</div><div class="header-actions"><span class="reference-pill">R32 · Offline reference</span><button id="theme" class="button" aria-label="Switch color theme">Dark</button><button id="draft-button" class="button">Draft <span id="draft-count">0</span></button></div></header><main id="page" tabindex="-1"></main></div></div><div id="toast" role="status" aria-live="polite"></div><div id="tooltip" role="tooltip" hidden></div><dialog id="tool-dialog" aria-labelledby="dialog-title"><div class="dialog-header"><h2 id="dialog-title"></h2><button id="dialog-close" class="button icon" aria-label="Close dialog">×</button></div><div id="dialog-content" class="dialog-content"></div></dialog><script id="specimens" type="application/json">'+JSON.stringify(specimens).replace(/<\/script/gi,'<\\/script')+'</script><script>'+logic+'</script><script>'+app+'</script></body></html>';
const out=path.join(__dirname,'reference'); fs.mkdirSync(out,{recursive:true}); fs.writeFileSync(path.join(out,'index.html'),page);
console.log(JSON.stringify({file:path.join(out,'index.html'),bytes:Buffer.byteLength(page),routes:routeKeys.length,toolSpecimens:Object.keys(tools).length,nativeArtboards:Object.keys(input.exports).length}));
