/* Run the accepted core journey suite against the R33 artifact to detect integration regressions. */
const fs=require('node:fs'),path=require('node:path'),Module=require('node:module');
let source=fs.readFileSync(path.join(__dirname,'../r32/test-journeys.cjs'),'utf8');
const old="const out=path.join(__dirname,'verification');";
if(source.split(old).length!==2)throw Error('Core verification anchor changed');
source=source.replace(old,"const out=path.join(__dirname,'verification/core');");
source=source.replace("suite:'r32_rendered_offline_journeys'","suite:'r33_core_regression_journeys'");
const runner=new Module(__filename,module);runner.filename=__filename;runner.paths=module.paths;runner._compile(source,__filename);
