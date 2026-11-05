"""Fixed trusted Docker smoke; never a research candidate or containment proof."""
import errno
import json
import os
import socket
import sys
import tempfile

records = []

def check(name, ok, observed):
    records.append({"check": name, "status": "PASS" if ok else "FAIL", "observed": observed})

def deny_connect(name, address):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.25)
    try:
        sock.connect((address, 9))
    except OSError as exc:
        code = exc.errno
        records.append({"check": name, "status": "PASS" if code == errno.ENETUNREACH else "INCONCLUSIVE", "errno": code})
    else:
        records.append({"check": name, "status": "FAIL", "observed": "unexpected_connection"})
    finally:
        sock.close()

try:
    check("allowed_computation", 6 * 7 == 42, 6 * 7)
    check("uid_gid", (os.getuid(), os.getgid()) == (65534, 65534), [os.getuid(), os.getgid()])
    names = sorted(os.environ)
    check("minimal_environment", names == ["LANG", "PATH"], names)
    check("readonly_root", bool(os.statvfs("/").f_flag & os.ST_RDONLY), bool(os.statvfs("/").f_flag & os.ST_RDONLY))
    path = None
    try:
        fd, path = tempfile.mkstemp(dir="/tmp", prefix="rf-fixed-smoke-")
        try:
            written = os.write(fd, b"fixed-smoke-0000")
        finally:
            os.close(fd)
        check("allowed_small_scratch", written == 16, written)
    finally:
        if path is not None:
            os.unlink(path)
    with open("/proc/self/status", "rb") as stream:
        raw = stream.read(8193)
    if len(raw) > 8192:
        raise ValueError("own_status_exceeds_bound")
    selected = {}
    for line in raw.decode("ascii").splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {"NoNewPrivs", "CapEff", "Seccomp"}:
            selected[key] = value.strip()
    check("no_new_privileges", selected.get("NoNewPrivs") == "1", selected.get("NoNewPrivs"))
    check("capabilities_dropped", int(selected.get("CapEff", "-1"), 16) == 0, selected.get("CapEff"))
    check("seccomp_present", selected.get("Seccomp") == "2", selected.get("Seccomp"))
    check("api_socket_absent", not os.path.lexists("/var/run/docker.sock"), os.path.lexists("/var/run/docker.sock"))
    deny_connect("public_egress", "192.0.2.1")
    for name in ["dns", "host_labels", "vault", "siblings", "subtree_exhaustion", "malicious_code_escape"]:
        records.append({"check": name, "status": "SKIP", "reason": "no_authorized_fixture_or_out_of_smoke_scope"})
except Exception as exc:
    records.append({"check": "probe_exception", "status": "FAIL", "exception_type": type(exc).__name__})
passed = all(record["status"] in {"PASS", "SKIP"} for record in records)
print(json.dumps({"schema": "rf.fixed_docker_smoke.v1", "mechanical_checks_passed": passed, "candidate_admission": False, "containment_qualified": False, "records": records}, sort_keys=True, separators=(",", ":")))
sys.exit(0 if passed else 1)
