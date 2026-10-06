from pathlib import Path
import subprocess, json, time, hashlib

root = Path(__file__).resolve().parent
receipt = {'scope': 'ISOLATED_TRANSACTION_ACCEPTANCE', 'production_effects': False, 'cases_pass': 0, 'fixture_cleanup': False}
container_id = None
first = None
owner = '11111111-1111-4111-8111-111111111111'
op_a = '21111111-1111-4111-8111-111111111111'
op_b = '22222222-2222-4222-8222-222222222222'
prefix = f"SET ROLE authenticated; SET request.jwt.claim.sub='{owner}';"
payload = '[{"id":"proof-user-hline","schemaVersion":1,"source":"user","kind":"hline","points":[{"p":10.5,"t":"2024-01-01"}]}]'

def query(sql):
    result = subprocess.run(['docker','exec','-i',container_id,'psql','-U','postgres','-v','ON_ERROR_STOP=1','-Atq'],input=sql,text=True,capture_output=True,timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return result.stdout.strip()

try:
    image = subprocess.check_output(['docker','image','inspect','postgres:17','--format','{{.Id}}'],text=True).strip()
    container_id = subprocess.check_output(['docker','create','--name','terminal-a04-01a10f92-concurrent','--network','none','--memory','384m','--cpus','1','--tmpfs','/var/lib/postgresql/data:rw,noexec,nosuid,size=128m','-e','POSTGRES_HOST_AUTH_METHOD=trust',image],text=True).strip()
    receipt['container_id'] = container_id
    receipt['image_id'] = image
    subprocess.run(['docker','start',container_id],check=True,capture_output=True)
    for _ in range(30):
        ready = subprocess.run(['docker','exec',container_id,'pg_isready','-U','postgres'],capture_output=True)
        if ready.returncode == 0: break
        time.sleep(0.5)
    else: raise RuntimeError('Fixture did not start')
    query('\n'.join((root/f).read_text() for f in ['fixture-setup.sql','direct-validator.sql','fixture-ddl.sql','replace-drawings.sql']))
    receipt['function_sha256'] = hashlib.sha256((root/'replace-drawings.sql').read_bytes()).hexdigest()
    assert receipt['function_sha256'] == '1bb8d8639c73945bae80e1523d64d84414a49cde0964ea8ab82af69809cb38d2'
    statement_a = prefix + f" BEGIN; SELECT public.replace_drawings_collection('CONCURRENT', '{payload}'::jsonb, NULL, '{op_a}'::uuid); SELECT 'A_INSERTED_BEFORE_COMMIT'; SELECT pg_sleep(2); COMMIT;"
    first = subprocess.Popen(['docker','exec','-i',container_id,'psql','-U','postgres','-v','ON_ERROR_STOP=1','-Atq'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    first.stdin.write(statement_a); first.stdin.close(); first.stdin = None
    a_lines = []
    while True:
        line = first.stdout.readline()
        if not line: raise RuntimeError('First session ended before insert marker')
        a_lines.append(line.strip())
        if line.strip() == 'A_INSERTED_BEFORE_COMMIT': break
    start = time.monotonic()
    b = json.loads(query(prefix + f" SELECT public.replace_drawings_collection('CONCURRENT', '[]'::jsonb, NULL, '{op_b}'::uuid);"))
    receipt['second_session_elapsed_s'] = round(time.monotonic()-start,3)
    rest, a_err = first.communicate(timeout=10)
    if first.returncode: raise RuntimeError(a_err[-3000:])
    a = json.loads(a_lines[0])
    current = json.loads(query(prefix + " SELECT jsonb_build_object('rows',count(*),'data',jsonb_agg(data)->0) FROM public.drawings WHERE symbol='CONCURRENT';"))
    assert a['ok'] is True and a['idempotentReplay'] is False
    assert b['ok'] is False and b['code'] == 'revision_conflict'
    assert receipt['second_session_elapsed_s'] >= 1.0
    assert current['rows'] == 1 and current['data']['operation_id'] == op_a
    assert current['data']['drawings'] == json.loads(payload)
    receipt['cases_pass'] += 1
    before = query(prefix + " SELECT jsonb_agg(to_jsonb(d) ORDER BY id)::text FROM public.drawings d WHERE symbol='CONCURRENT';")
    replay = json.loads(query(prefix + f" SELECT public.replace_drawings_collection('CONCURRENT', '{payload}'::jsonb, NULL, '{op_a}'::uuid);"))
    after = query(prefix + " SELECT jsonb_agg(to_jsonb(d) ORDER BY id)::text FROM public.drawings d WHERE symbol='CONCURRENT';")
    assert replay['ok'] is True and replay['idempotentReplay'] is True and replay['revision'] == a['revision']
    assert before == after
    receipt['cases_pass'] += 1
    changed = json.loads(query(prefix + f" BEGIN; SELECT public.replace_drawings_collection('CONCURRENT', '[]'::jsonb, '{a['revision']}'::uuid, '{op_b}'::uuid); ROLLBACK;"))
    after_rollback = query(prefix + " SELECT jsonb_agg(to_jsonb(d) ORDER BY id)::text FROM public.drawings d WHERE symbol='CONCURRENT';")
    assert changed['ok'] is True and changed['revision'] != a['revision'] and after_rollback == before
    receipt['cases_pass'] += 1
    receipt['outcomes'] = ['two real sessions: one commit, one explicit conflict', 'lost response replay: stable revision and exact row preimage', 'admitted replacement rolled back: exact original row preimage']
    receipt['version'] = query('SHOW server_version;')
except Exception as error:
    receipt['error'] = str(error)
finally:
    if first and first.poll() is None:
        first.terminate()
        try: first.wait(timeout=5)
        except subprocess.TimeoutExpired: first.kill(); first.wait(timeout=5)
    if container_id:
        remove = subprocess.run(['docker','rm','-f',container_id],capture_output=True)
        inspect = subprocess.run(['docker','inspect',container_id],capture_output=True)
        receipt['fixture_cleanup'] = remove.returncode == 0 and inspect.returncode != 0
        receipt['cleanup_remove_exit'] = remove.returncode
        receipt['cleanup_inspect_exit'] = inspect.returncode
    (root/'concurrent-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))
if receipt.get('error') or not receipt['fixture_cleanup'] or receipt['cases_pass'] != 3:
    raise SystemExit(1)
