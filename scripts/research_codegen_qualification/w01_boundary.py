"""Fixed observations; host oracles remain separate."""
import errno as ER, json, os, socket, sys, time

UIDT = 65534
PORT = 39173
SCRATCH = "/tmp/rf-w01-scratch.txt"
FORBIDDEN = "/rf-forbidden-write"
X = "/rf-excluded/"
EXCLUDED = tuple(X + n for n in (
    "evaluator-labels.json", "publisher-credential.fixture",
    "evaluator-source.py", "trial-vault.fixture", "adjacent-fold.fixture",
    "host-socket.fixture"))
def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r
def emit(r, out=sys.stdout):
    out.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")
def ecat(e):
    return "errno_" + ER.errorcode.get(getattr(e, "errno", None), "unk")
def identity_env():
    u, g = os.getuid(), os.getgid()
    e = os.environ
    return (rec("w01.identity", "observed", uid=u, gid=g, uid_met=u == UIDT,
                gid_met=g == UIDT, answer=6*7),
            rec("w01.env_names", "observed", lang="LANG" in e,
                path="PATH" in e, extra_count=len(set(e)-{"LANG", "PATH"})))
def try_write(path, expect_ok):
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as e:
        how = "failed" if expect_ok else "observed_denied"
        return rec("w01.scratch" if expect_ok else "w01.ro_root", how,
                   category=ecat(e))
    if not expect_ok:
        os.close(fd)
        return rec("w01.ro_root", "failed", category="denial_missing")
    try:
        n = os.write(fd, b"rf01")
    finally:
        os.close(fd)
    os.unlink(path)
    return rec("w01.scratch", "observed", bytes_written=n)
def read_status():
    try:
        with open("/proc/self/status", "rb") as f:
            n = len(f.read(8193))
        return rec("w01.status", "observed", readable=True, capped_len=n,
                   infer="none")
    except OSError as e:
        return rec("w01.status", "observed", readable=False,
                   category=ecat(e), infer="none")
def named_sockets():
    pths = "/var/run/docker.sock", "/var/run/sshd.sock", "/tmp/rf-mcp-gateway.sock"
    return rec("w01.sockets", "observed",
               exists={p: os.path.exists(p) for p in pths})
def excluded_probe():
    cats = {}
    for p in EXCLUDED:
        try:
            fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK)
        except OSError as e:
            cats[p] = ecat(e)
            continue
        os.close(fd)
        cats[p] = "open_succeeded_disclosure"
    d = sum(c.startswith("open") for c in cats.values())
    return rec("w01.excluded", "failed" if d else "observed",
               categories=cats, disclosures=d)
def loopback_probe(now=time.monotonic):
    t0, cats, dg = now(), [], socket.SOCK_DGRAM
    for label, kind in (("tcp_connected", socket.SOCK_STREAM),
                        ("udp_sent_unconfirmed", dg),
                        ("dns_srg_sent_unconfirmed", dg)):
        if now() - t0 >= 2.0:
            cats.append(label + "_skipped_budget")
            continue
        s = socket.socket(socket.AF_INET, kind)
        s.settimeout(0.25)
        try:
            if kind == dg:
                s.sendto(b"rf01x", ("127.0.0.1", PORT))
            else:
                s.connect(("127.0.0.1", PORT))
            cats.append(label)
        except OSError as e:
            cats.append(ecat(e))
        finally:
            s.close()
    return rec("w01.loopback", "observed", categories=cats)
def main(out=sys.stdout):
    emit(rec("w01.header", "started"), out)
    rs = list(identity_env())
    rs += [try_write(SCRATCH, True), try_write(FORBIDDEN, False),
           read_status(), named_sockets(), excluded_probe(),
           loopback_probe()]
    bad = [r["case_id"] for r in rs if r["outcome"] == "failed"]
    for r in rs:
        emit(r, out)
    emit(rec("w01.final", "observed", failures=len(bad)), out)
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
