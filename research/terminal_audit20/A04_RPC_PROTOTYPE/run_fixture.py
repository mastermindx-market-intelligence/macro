from pathlib import Path
import subprocess, json, time, re

root = Path(__file__).resolve().parent
name = 'terminal-a04-01a10f92-transaction-r6'
container_id = None
receipt = {'scope':'TRANSACTION_ARTIFACT_FIXTURE_ONLY', 'production_effects':False, 'cases_pass':0, 'fixture_cleanup':False}
try:
    image = subprocess.check_output(['docker','image','inspect','postgres:17','--format','{{.Id}}'], text=True).strip()
    receipt['image_id'] = image
    container_id = subprocess.check_output(['docker','create','--name',name,'--network','none','--memory','384m','--cpus','1','--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=128m','-e','POSTGRES_HOST_AUTH_METHOD=trust',image],text=True).strip()
    receipt['container_id'] = container_id
    (root/'fixture-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    subprocess.run(['docker','start',container_id],check=True,capture_output=True)
    for _ in range(30):
        check = subprocess.run(['docker','exec',container_id,'pg_isready','-U','postgres'],capture_output=True)
        if check.returncode == 0:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('Fixture PostgreSQL did not become ready')
    sql = '\n'.join([(root/n).read_text() for n in ['fixture-setup.sql','direct-validator.sql','fixture-role.sql','validator-regressions.sql']] + ['RESET ROLE;'] + [(root/n).read_text() for n in ['fixture-ddl.sql','replace-drawings.sql','transaction-regressions.sql']])
    run = subprocess.run(['docker','exec','-i',container_id,'psql','-U','postgres','-v','ON_ERROR_STOP=1'], input=sql, text=True, capture_output=True)
    (root/'psql-actual.log').write_text(run.stdout+'\n'+run.stderr)
    receipt['psql_exit'] = run.returncode
    match = re.search(r'ACTUAL_VALIDATION_CASES=(\d+)',run.stderr)
    receipt['cases_pass'] = int(match.group(1)) if match else 0
    receipt['cases_skip'] = 0
    receipt['transaction_notices'] = re.findall(r'NOTICE:\s+(PASS: .*?)\n',run.stderr.split('ACTUAL_VALIDATION_CASES=33',1)[-1])
    receipt['transaction_cases_pass'] = len(receipt['transaction_notices'])
    receipt['version'] = subprocess.check_output(['docker','exec',container_id,'psql','-U','postgres','-tAc','show server_version'],text=True).strip()
    if run.returncode:
        raise RuntimeError('Actual transaction regressions failed; see psql-actual.log; accepted guard result remains separately scoped')
    if receipt['transaction_cases_pass'] != 11:
        raise RuntimeError('Expected11 actual transaction assertions')
    if receipt['cases_pass'] != 33:
        raise RuntimeError('Expected 33 actual causal cases')
except Exception as exc:
    receipt['error'] = str(exc)
finally:
    if container_id:
        remove = subprocess.run(['docker','rm','-f',container_id],capture_output=True,text=True)
        inspect = subprocess.run(['docker','inspect',container_id],capture_output=True,text=True)
        receipt['cleanup_remove_exit'] = remove.returncode
        receipt['cleanup_inspect_exit'] = inspect.returncode
        receipt['fixture_cleanup'] = remove.returncode == 0 and inspect.returncode != 0
    (root/'fixture-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
if receipt.get('error') or not receipt['fixture_cleanup']:
    raise SystemExit(1)
