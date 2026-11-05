"""Finite local supervision for the single future Fabric canary commission.

No default execution. The worker calls launch exactly once with root-sealed
source bytes. This is a subprocess collector, not a scheduler or retry owner.
"""
import base64
import hashlib
import json
import os
import selectors
import signal
import subprocess
import time
import zlib

ROOT = '01a1333c-a475-7052-95a8-72a88eb8c17b'
OPERATION = 'rf-fixed-smoke-runsc-01a1333c-v4'
ARGV = ('/usr/bin/sudo', '-n', '/usr/bin/env', '-i',
        'PATH=/usr/sbin:/usr/bin:/sbin:/bin', 'LANG=C', 'LC_ALL=C',
        '/usr/bin/python3', '-I', '-S', '-')
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}


def payload(bootstrap, bootstrap_sha, capsule, capsule_sha, commission_sha, started):
    if (type(bootstrap) is not bytes or type(capsule) is not bytes
            or len(bootstrap) > 20000 or len(capsule) > 500000
            or hashlib.sha256(bootstrap).hexdigest() != bootstrap_sha
            or hashlib.sha256(capsule).hexdigest() != capsule_sha
            or type(commission_sha) is not str or len(commission_sha) != 64
            or not set(commission_sha) <= set('0123456789abcdef')):
        raise ValueError('sealed_input_mismatch')
    b = base64.b64encode(zlib.compress(bootstrap)).decode('ascii')
    c = base64.b64encode(zlib.compress(capsule)).decode('ascii')
    # Constants are serialized with repr; no shell interpolation or arguments
    # from source documents. Exception details and ambient environment omitted.
    return ('''import base64,hashlib,json,time,types,zlib
try:
    bootstrap=zlib.decompress(base64.b64decode(%r))
    capsule=zlib.decompress(base64.b64decode(%r))
    assert hashlib.sha256(bootstrap).hexdigest()==%r
    module=types.ModuleType('canary_bootstrap')
    exec(compile(bootstrap,'canary_bootstrap.py','exec'),module.__dict__)
    first=[True]
    def clock():
        if first[0]:
            first[0]=False
            return %r
        return time.monotonic()
    result=module.bootstrap(capsule,%r,%r,clock=clock)
except BaseException as exc:
    result={'schema':'rf.fixed_canary.v1','root':%r,'operation':%r,
            'status':'BOOTSTRAP_STOPPED_NO_RETRY','failure_type':type(exc).__name__,
            'candidate_admission':False,'containment_qualified':False}
print(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False))
''' % (b,c,bootstrap_sha,started,capsule_sha,commission_sha,ROOT,OPERATION)).encode('ascii')


def launch(bootstrap, bootstrap_sha, capsule, capsule_sha, commission_sha):
    started = time.monotonic()
    data = payload(bootstrap, bootstrap_sha, capsule, capsule_sha, commission_sha, started)
    # Same monotonic origin is injected in the root bootstrap. All setup, CLI,
    # archive/install/image/smoke and return collection share this 900s boundary.
    deadline = started + 900
    output, problem, proc, sent = bytearray(), None, None, 0
    try:
        proc = subprocess.Popen(ARGV, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, env=ENV, start_new_session=True, close_fds=True)
        for stream in (proc.stdin, proc.stdout):
            os.set_blocking(stream.fileno(), False)
        with selectors.DefaultSelector() as poll:
            poll.register(proc.stdin, selectors.EVENT_WRITE, 'stdin')
            poll.register(proc.stdout, selectors.EVENT_READ, 'stdout')
            while poll.get_map():
                left = deadline - time.monotonic()
                if left <= 0:
                    problem = 'TOTAL_DEADLINE'; break
                for key, _ in poll.select(min(.1, left)):
                    if key.data == 'stdin':
                        try:
                            count = os.write(key.fd, data[sent:sent+65536])
                        except BrokenPipeError:
                            poll.unregister(key.fileobj); key.fileobj.close(); continue
                        if count <= 0:
                            problem = 'STDIN_INCOMPLETE'; break
                        sent += count
                        if sent == len(data):
                            poll.unregister(key.fileobj); key.fileobj.close()
                    else:
                        block = os.read(key.fd, min(4096, 65536-len(output)))
                        if not block:
                            poll.unregister(key.fileobj)
                        else:
                            output.extend(block)
                            if len(output) >= 65536:
                                problem = 'RETURN_OUTPUT_CAP'; break
                if problem:
                    break
            if not problem:
                proc.wait(timeout=max(.001, deadline-time.monotonic()))
    except Exception as exc:
        problem = type(exc).__name__
    termination = 'NOT_REQUIRED'
    if proc is not None and proc.poll() is None:
        # Only this launched process group. A denied signal ends all further
        # control attempts; no root tool, fallback signal or alternate carrier.
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            termination = 'SIGNAL_SENT_NOT_TERMINATION_PROOF'
        except ProcessLookupError:
            termination = 'GROUP_NOT_FOUND_NOT_DAEMON_PROOF'
        except PermissionError:
            termination = 'SIGNAL_PERMISSION_REFUSED'
        except OSError:
            termination = 'SIGNAL_UNCONFIRMED'
    rc = proc.poll() if proc is not None else None
    if proc is not None:
        for stream in (proc.stdin, proc.stdout):
            try:
                if stream and not stream.closed: stream.close()
            except OSError:
                pass
    return {'schema':'rf.fixed_canary_carrier.v1','root':ROOT,'operation':OPERATION,
        'commission_sha256':commission_sha, 'capsule_sha256':capsule_sha,
        'bootstrap_sha256':bootstrap_sha,'pid':proc.pid if proc else None,
        'started_monotonic':started,'elapsed_seconds':time.monotonic()-started,
        'rc':rc,'problem':problem,'supervision':termination,
        'stdin_complete':sent==len(data),'output_bytes':len(output),
        'output_sha256':hashlib.sha256(output).hexdigest(),
        'output_b64':base64.b64encode(output).decode('ascii'),
        'physical_result_accepted':False,'candidate_admission':False,
        'containment_qualified':False,'same_operation_reconciliation_required':
            problem is not None or rc != 0}
