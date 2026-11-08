// Paired source-only fixture: explicit existing dependency/source root, no
// installs, downloads, app startup or fallback to another Terminal checkout.
const path=require('node:path'),fs=require('node:fs'),cp=require('node:child_process');
const terminal=process.env.INTL_TERMINAL_SOURCE_ROOT;
if(!terminal || cp.execFileSync('git',['rev-parse','HEAD'],{cwd:path.dirname(terminal),encoding:'utf8',env:{...process.env,GIT_NO_LAZY_FETCH:'1'}}).trim()!=='0449c164c5158cc96ecd8ea8f967fa48c4356ef7')throw Error('Exact commissioned Terminal source required');
if(!fs.existsSync(path.join(terminal,'node_modules/vitest/vitest.mjs')))throw Error('Existing qualified fixture dependencies required; no installation');
module.exports={root:path.resolve(__dirname,'..'),cacheDir:path.resolve(__dirname,'../node_modules/.vite'),
 test:{env:{INVESTIGATION_API_ADMISSION:'open'},include:['tests/intl_investigation_page_join.test.tsx'],environment:'jsdom',poolOptions:{threads:{singleThread:true}}},
 resolve:{alias:{'@':terminal,'react':path.join(terminal,'node_modules/react'),'react-dom':path.join(terminal,'node_modules/react-dom'),
 'vitest':path.join(terminal,'node_modules/vitest/dist/index.js'),'server-only':path.join(terminal,'lib/__tests__/stubs/serverOnly.ts')}},
 server:{fs:{allow:[path.resolve(__dirname,'..'),terminal]}}};
