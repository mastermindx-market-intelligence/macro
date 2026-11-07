/* Add the reviewed source inspector to the immutable R32 reference. No product route duplication. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const read=p=>fs.readFileSync(path.join(__dirname,p),'utf8');
const base=read('../r32/reference/index.html');
const expected='b319f1bbf464b18a0ba94d6b1115d7e4b9a331d5ae78b68f2551ac12da76347f';
if(crypto.createHash('sha256').update(base).digest('hex')!==expected)throw Error('R32 baseline changed; review integration anchors');
let html=base;
function replaceOnce(old,next){const i=html.indexOf(old);if(i<0||html.indexOf(old,i+old.length)>=0)throw Error('Missing or repeated integration anchor: '+old.slice(0,70));html=html.slice(0,i)+next+html.slice(i+old.length);}
const r32app=read('../r32/reference-app.js');
const sourceStart=r32app.indexOf('  function sourceView()');
const sourceEnd=r32app.indexOf('  function coverageView(',sourceStart);
replaceOnce(r32app.slice(sourceStart,sourceEnd),'  function sourceView(){return window.MMXSourceInspector.view();}\n');
replaceOnce('bindNative(body);bindActions(body);bindValues(body);','bindNative(body);bindActions(body);bindValues(body);window.MMXSourceInspector.bind(body);');
replaceOnce("  $('#review-states').addEventListener('click',()=>show('review'));","  $('#source-inspector').addEventListener('click',()=>show('sources'));\n  $('#review-states').addEventListener('click',()=>show('review'));");
replaceOnce(".filter(x=>x.getClientRects().length&&getComputedStyle(x).visibility!=='hidden');",".filter(x=>x.getClientRects().length&&getComputedStyle(x).visibility!=='hidden'&&!Array.from(dialog.querySelectorAll('details:not([open])')).some(d=>d.contains(x)&&!d.querySelector(':scope > summary')?.contains(x)));");
replaceOnce('<button id="draft-button"','<button id="source-inspector" class="button">Sources</button><button id="draft-button"');
replaceOnce('R32 · Offline reference','R33 · Offline reference');
replaceOnce('Synthetic market values<br>Drafts stay in this tab','Synthetic scenario values<br>Captured source inspector<br>Drafts stay in this tab');
const font=fs.readFileSync(path.join(__dirname,'assets/source-cjk-subset.woff')).toString('base64');
const fontCss="@font-face{font-family:'Mastermind Source CJK Subset';src:url(data:font/woff;base64,"+font+") format('woff');font-weight:400 800;font-display:swap}body{font-family:Inter,system-ui,'Mastermind Source CJK Subset',sans-serif}";
replaceOnce('</style>','\n'+fontCss+'\n'+read('source-inspector.css')+'</style>');
replaceOnce('</head>','<!-- Font subset: Mastermind Source CJK Subset; original Noto Sans CJK SC. Licensed under SIL OFL 1.1. '+read('assets/OFL.txt').replaceAll('--','—')+' -->\n</head>');
const capture=JSON.parse(read('captured-owner-publication.json'));
const scripts='<script id="owner-publication" type="application/json">'+JSON.stringify(capture).replaceAll('<','\\u003c')+'</script><script>'+read('source-adapter.js')+'</script><script>'+read('source-inspector.js')+'</script>';
replaceOnce('<script>'+r32app.slice(0,100),scripts+'<script>'+r32app.slice(0,100));
const out=path.join(__dirname,'reference');fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'index.html'),html);
const report={baseline_sha256:expected,source_contract:capture.schema,captured_content_sha256:capture.publication.content_sha256,html_sha256:crypto.createHash('sha256').update(html).digest('hex'),bytes:Buffer.byteLength(html),routes:8,tool_families:15};
fs.writeFileSync(path.join(__dirname,'build-result.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
