from pathlib import Path
import subprocess,os,json,hashlib,datetime,time,sys,re
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");P=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/pending_scenario_20261022");G=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_gs_20261022")
phase=sys.argv[1];assert phase in ['focused','browser','history']
env=dict(os.environ,PATH='/tmp/intl-country-cockpit-ci-20261021/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin',PYTHONDONTWRITEBYTECODE='1',NODE_PATH='/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/intl-parent-proof-20261022/terminal/node_modules',PLAYWRIGHT_CHROMIUM_CHANNEL='chrome')
if phase=='focused':args=['/opt/homebrew/bin/node','--test','--test-reporter=tap','--test-name-pattern=Scenario query ordering|GS query composition|refused native popstate preserves the pending scenario','tests/intl_workspace_controller.test.cjs']
elif phase=='history':args=['/opt/homebrew/bin/node','--test','--test-reporter=tap','tests/intl_workspace_history_independent.test.cjs']
else:args=next(x['command'] for x in json.loads((G/'regressions_candidate/receipt.json').read_text())['checks'] if x['name']=='international_browser')
bindings={str(x):hashlib.sha256((R/x).read_bytes()).hexdigest() for x in ['tests/intl_workspace_controller.test.cjs','templates/intl_workspace.js','site/intl_workspace.js','templates/intl_workspace_state.js','templates/shared_shell_bridge.js','templates/intl_workspace_scenario.js','tests/intl_workspace_history_independent.test.cjs']}
record={'command':args,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bindings':bindings}
assert record['head']=='9bf7161b6c856a8df5eaa18a0b9ef8fbb1e206bb'
log=P/(phase+'.log');assert not log.exists();tick=time.monotonic()
with log.open('w') as out:result=subprocess.run(args,cwd=R,env=env,stdout=out,stderr=subprocess.STDOUT,timeout=1200)
record.update(exit_code=result.returncode,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),duration_seconds=round(time.monotonic()-tick,2),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),bindings_unchanged=all(hashlib.sha256((R/x).read_bytes()).hexdigest()==h for x,h in bindings.items()),counts={k:int(v) for k,v in re.findall(r'^# (tests|pass|fail|skipped|cancelled|todo) (\d+)$',log.read_text(),re.M)})
(P/(phase+'_receipt.json')).write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record));print('\n'.join(log.read_text().splitlines()[-25:]))
sys.exit(result.returncode)
