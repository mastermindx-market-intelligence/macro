#!/usr/bin/env bash
# Pull-IF-CHANGED refresh of the served site. Installed as /usr/local/bin/macro-update
# by setup.sh; run by a FREQUENT cron (every few min) + by hand. Cheap no-op when main
# hasn't moved, so it's safe to run often — that's what makes mastermind-x.com track
# main within minutes (the render.yml express lane + the nightly both land here fast)
# instead of waiting on a once-a-night pull.
set -euo pipefail
APP_DIR="/opt/macro"
# BEGIN LIVE_SOURCE_OWNER
# The source transaction belongs to macro-update. This embedded stdlib program
# runs before checkout imports and remains available after an interrupted reset.
live_source_control() {
	/usr/bin/python3 -I -S - "/proc/$$/fd/255" "$@" <<'MMX_LIVE_SOURCE_PY'
import configparser
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

APP = Path("/opt/macro")
OWNER = Path("/usr/local/bin/macro-update")
LOCK = Path("/run/lock/macro-live-source.lock")
STATE = Path("/var/lib/macro-live/state")
PENDING = STATE / "source-update.pending"
CAPSULES = STATE / "source-update-capsules"
UNIT_DIR = Path("/etc/systemd/system")
CGROUP = Path("/sys/fs/cgroup")
BOOT_ID = Path("/proc/sys/kernel/random/boot_id")
LANES = ("fast", "snapshot", "bars")
RUN_LANES = (*LANES, "sector-inputs")
UNITS = tuple("macro-live-" + lane + suffix for lane in LANES
              for suffix in (".service", ".timer"))
CORE_TIMERS = tuple(unit for unit in UNITS if unit.endswith(".timer"))
ANCILLARY_UNITS = tuple("macro-live-" + lane + suffix
                        for lane in ("prophet", "closepass", "breadth")
                        for suffix in (".service", ".timer"))
ANCILLARY_TIMERS = tuple(unit for unit in ANCILLARY_UNITS if unit.endswith(".timer"))
SETUP_MEMBERS = ("setup/live-setup.sh",) + tuple("setup/units/" + unit for unit in ANCILLARY_UNITS)
CRONTAB = "/usr/bin/crontab"
CRON_SPOOL = Path("/var/spool/cron/crontabs")
HELPERS = tuple("market-memory-options-" + name + ".sh"
                for name in ("unit-boundary", "runtime-fence", "dropin-migration"))
PHASES = ("PREPARED", "GUARDS_READY", "MUTATING", "SOURCE_READY", "RESTORING")
READY = ("SOURCE_READY", "RESTORING")
SYSTEMCTL = "/usr/bin/systemctl"
GIT = "/usr/bin/git"
SYNC = "/usr/bin/sync"
BASH = "/usr/bin/bash"
ROOT_UID = 0
ROOT_GID = 0
MAX_MANIFEST = 4 * 1024 * 1024
MAX_OWNER = 2 * 1024 * 1024


class Refusal(RuntimeError):
    pass


class EffectNeedsReadback(Refusal):
    """A rename/unlink became visible but its final durability/readback failed."""


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def exact_keys(value, keys, name):
    require(type(value) is dict and set(value) == set(keys), name + " fields")


def closed_json(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(Refusal("nonfinite JSON")))


def directory(path, *, create=False, sticky=False):
    """Walk all ancestors without following symlinks; root owns every entry."""
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "noncanonical directory")
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try:
            s = current.lstat()
        except FileNotFoundError:
            if not create:
                raise
            current.mkdir(mode=0o755 if current in (STATE.parent, STATE) else 0o700)
            sync_dir(current.parent)
            s = current.lstat()
        require(stat.S_ISDIR(s.st_mode) and (s.st_uid, s.st_gid) in
                ((0, 0), (ROOT_UID, ROOT_GID)),
                "unsafe directory: " + str(current))
        writable = s.st_mode & 0o022
        allowed_sticky = sticky and current == path and bool(s.st_mode & stat.S_ISVTX)
        require(not writable or allowed_sticky, "writable directory: " + str(current))
    return path


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def safe_read(path, limit, *, mode=None):
    path = Path(path)
    directory(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == ROOT_UID
                and before.st_gid == ROOT_GID and before.st_nlink == 1
                and not before.st_mode & 0o022, "unsafe file: " + str(path))
        if mode is not None:
            require(stat.S_IMODE(before.st_mode) == mode, "unexpected file mode: " + str(path))
        require(0 <= before.st_size <= limit, "oversized file: " + str(path))
        with os.fdopen(os.dup(fd), "rb") as stream:
            data = stream.read(limit + 1)
        after = os.fstat(fd)
        require(len(data) <= limit and (before.st_dev, before.st_ino, before.st_size,
                before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino,
                after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                "file changed during capture: " + str(path))
        return data
    finally:
        os.close(fd)


def atomic_write(path, data, mode):
    path = Path(path)
    directory(path.parent)
    try:
        s = path.lstat()
    except FileNotFoundError:
        s = None
    if s is not None:
        require(stat.S_ISREG(s.st_mode) and s.st_uid == ROOT_UID and s.st_gid == ROOT_GID
                and s.st_nlink == 1 and not s.st_mode & 0o022, "unsafe replacement: " + str(path))
    temp = path.parent / ("." + path.name + "." + uuid.uuid4().hex)
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    published = False
    try:
        os.fchmod(fd, mode)
        os.fchown(fd, ROOT_UID, ROOT_GID)
        with os.fdopen(os.dup(fd), "wb") as stream:
            stream.write(data)
            stream.flush()
        os.fsync(fd)
        os.replace(temp, path)
        published = True
        sync_dir(path.parent)
    except OSError as exc:
        if published:
            raise EffectNeedsReadback("replacement visible at " + str(path) +
                                     "; expected sha256=" + sha(data) + "; " + str(exc)) from exc
        raise
    finally:
        os.close(fd)
        if temp.exists():
            temp.unlink()


def json_write(path, value):
    atomic_write(path, (json.dumps(value, sort_keys=True, separators=(",", ":"),
                                  allow_nan=False) + "\n").encode(), 0o600)


def run(args, *, accepted=(0,), input=None, timeout=None):
    bounded = {"timeout": timeout} if timeout is not None else {}
    result = subprocess.run(args, input=input, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False, **bounded)
    require(result.returncode in accepted,
            "command failed (" + str(result.returncode) + "): " + " ".join(map(str, args[:3])))
    return result.stdout.decode("utf-8", "strict").strip()


def git(*args, timeout=None):
    bounded = {"timeout": timeout} if timeout is not None else {}
    return run([GIT, "-C", str(APP), *args], **bounded)


def source_revision(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value), "invalid source revision")
    return value


def owner_bytes(script_fd):
    # /proc/self/fd/255 in this child is not the executing Bash file.
    require(re.fullmatch(r"/proc/[1-9][0-9]*/fd/255", script_fd), "executing owner descriptor missing")
    fd = os.open(script_fd, os.O_RDONLY | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == ROOT_UID and s.st_gid == ROOT_GID
                and not s.st_mode & 0o022 and 0 < s.st_size <= MAX_OWNER, "unsafe executing owner")
        with os.fdopen(os.dup(fd), "rb") as stream:
            data = stream.read(MAX_OWNER + 1)
        after = os.fstat(fd)
        require(len(data) == s.st_size and len(data) <= MAX_OWNER and
                (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                "executing owner changed during capture")
        return data
    finally:
        os.close(fd)


def owner_identity(script_fd, *, candidate=False):
    data = owner_bytes(script_fd)
    if not candidate:
        require(data == safe_read(OWNER, MAX_OWNER, mode=0o755), "installed/executing owner mismatch")
    return sha(data)


def boot_identity():
    value = BOOT_ID.read_text().strip()
    require(re.fullmatch(r"[0-9a-f-]{36}", value), "invalid boot identity")
    return value


def object_bytes(revision, rel):
    result = subprocess.run([GIT, "-C", str(APP), "show", revision + ":" + rel],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(result.returncode == 0, "missing captured target object: " + rel)
    return result.stdout


def unit_show(unit, prop):
    require(unit in UNITS + ANCILLARY_UNITS, "foreign unit")
    return run([SYSTEMCTL, "show", "-p", prop, "--value", unit])


def unit_enabled(unit):
    value = run([SYSTEMCTL, "is-enabled", unit], accepted=(0, 1, 3, 4))
    require(value in ("enabled", "disabled", "enabled-runtime", "masked", "masked-runtime",
                      "static", "not-found"), "unknown unit enablement: " + unit)
    return value



def reviewed_unit_shape(name, body):
    """Closed core-unit shape: every executable command is the guarded entry."""
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        parser.read_string(body.decode("utf-8", "strict"))
    except (configparser.Error, UnicodeError) as exc:
        raise Refusal("invalid target unit syntax: " + name) from exc
    service = name.endswith(".service")
    expected_sections = {"Unit", "Service" if service else "Timer", "Install"}
    require(set(parser.sections()) == expected_sections and not parser.defaults(), "foreign unit sections: " + name)
    allowed = {
        "Unit": {"Description", "After", "Wants"},
        "Service": {"Type", "WorkingDirectory", "EnvironmentFile", "ExecStart", "TimeoutStartSec",
                    "Nice", "CPUWeight", "CPUQuota", "MemoryHigh", "MemoryMax", "IOWeight",
                    "NoNewPrivileges", "PrivateTmp"},
        "Timer": {"OnBootSec", "OnUnitActiveSec", "OnCalendar", "AccuracySec",
                  "RandomizedDelaySec", "Persistent", "Unit"},
        "Install": {"WantedBy"},
    }
    for section in parser.sections():
        require(set(parser[section]) <= allowed[section]
                and all("\n" not in value and "\\" not in value for value in parser[section].values()),
                "foreign execution hook/continuation in target unit: " + name)
    lane = name.removeprefix("macro-live-").rsplit(".", 1)[0]
    if service:
        required = {"Type": "oneshot", "WorkingDirectory": "/opt/macro",
                    "EnvironmentFile": "-/etc/macro-live.env",
                    "ExecStart": "/usr/local/bin/macro-update --live-lane " + lane,
                    "NoNewPrivileges": "true", "PrivateTmp": "true"}
        require(all(parser["Service"].get(key) == value for key, value in required.items()),
                "target service is not exclusively guarded: " + name)
        require(parser["Install"].get("WantedBy") == "multi-user.target", "foreign service target")
    else:
        require(parser["Timer"].get("Unit") == "macro-live-" + lane + ".service"
                and parser["Install"].get("WantedBy") == "timers.target", "foreign timer target")

def unit_inventory(units=UNITS, *, check_public=True):
    directory(UNIT_DIR)
    states = {}
    for unit in units:
        path = UNIT_DIR / unit
        try:
            s = path.lstat()
        except FileNotFoundError:
            s = None
        load = unit_show(unit, "LoadState")
        absent = s is None and load == "not-found"
        if not absent:
            require(s is not None and stat.S_ISREG(s.st_mode) and s.st_uid == ROOT_UID
                    and s.st_gid == ROOT_GID and not s.st_mode & 0o022,
                    "partial, masked or foreign installation: " + unit)
            require(load in ("loaded", "not-found"), "ambiguous manager state: " + unit)
            require(not unit_show(unit, "DropInPaths"), "foreign live-unit drop-ins: " + unit)
        states[unit] = {"absent": absent}
    count = sum(int(v["absent"]) for v in states.values())
    require(count in (0, len(units)), "partial live-unit installation")
    if count == len(units):
        if check_public:
            public = STATE.parent / "public"
            try:
                public.lstat()
            except FileNotFoundError:
                pass
            else:
                raise Refusal("live public footprint without all six units")
        return "absent", {}
    timers = {}
    for unit in units:
        if not unit.endswith(".timer"):
            continue
        enabled = unit_enabled(unit)
        require(enabled in ("enabled", "disabled"), "masked/foreign timer intent: " + unit)
        active = unit_show(unit, "ActiveState")
        require(active in ("active", "inactive"), "transitional/failed timer intent: " + unit)
        timers[unit] = {"enabled": enabled, "active": active == "active"}
    return "present", timers


def pending_exists():
    try:
        directory(PENDING.parent)
    except FileNotFoundError:
        return False
    try:
        PENDING.lstat()
    except FileNotFoundError:
        return False
    return True


def read_pending(owner):
    if not pending_exists():
        return None
    journal = closed_json(safe_read(PENDING, 65536, mode=0o600))
    exact_keys(journal, ("schema", "attempt", "manifest_sha256", "phase", "restoration", "mirrors", "setup"), "journal")
    require(journal["schema"] == "macro.live-source-update.v1"
            and type(journal["attempt"]) is str and re.fullmatch(r"[0-9a-f]{32}", journal["attempt"])
            and journal["phase"] in PHASES, "invalid source journal")
    capsule = CAPSULES / journal["attempt"]
    raw = safe_read(capsule / "manifest.json", MAX_MANIFEST, mode=0o600)
    require(sha(raw) == journal["manifest_sha256"], "capsule manifest mismatch")
    manifest = closed_json(raw)
    exact_keys(manifest, ("schema", "attempt", "owner_sha256", "old", "new", "changed",
                         "boot_id", "enrollment", "timers", "service_cgroups", "members", "purpose", "setup"), "manifest")
    require(manifest["schema"] == journal["schema"] and manifest["attempt"] == journal["attempt"]
            and manifest["owner_sha256"] == owner, "incompatible transaction owner")
    source_revision(manifest["old"])
    source_revision(manifest["new"])
    require(type(manifest["changed"]) is list and len(manifest["changed"]) <= 20000
            and all(type(x) is str and x and "\n" not in x and "\x00" not in x
                    and len(x) <= 4096 for x in manifest["changed"]), "invalid changed-path capture")
    require(type(manifest["boot_id"]) is str and re.fullmatch(r"[0-9a-f-]{36}", manifest["boot_id"]),
            "invalid captured boot identity")
    require(manifest["enrollment"] in ("absent", "present"), "invalid enrollment")
    timer_names = {"macro-live-" + x + ".timer" for x in LANES} if manifest["enrollment"] == "present" else set()
    exact_keys(manifest["timers"], timer_names, "timer intent")
    exact_keys(journal["restoration"], timer_names, "timer restoration")
    for unit in timer_names:
        value = manifest["timers"][unit]
        exact_keys(value, ("enabled", "active"), "timer intent")
        require(value["enabled"] in ("enabled", "disabled")
                and type(value["active"]) is bool, "invalid timer intent")
        require(journal["restoration"][unit] in ("pending", "starting", "restored"), "invalid restoration phase")
    services = {unit for unit in UNITS if unit.endswith(".service")} if manifest["enrollment"] == "present" else set()
    exact_keys(manifest["service_cgroups"], services, "original service cgroups")
    for unit, group in manifest["service_cgroups"].items():
        require(type(group) is str and (not group or
                (group.startswith("/") and ".." not in Path(group).parts and Path(group).name == unit)),
                "invalid original service cgroup")
    exact_keys(journal["mirrors"], ("site", "news", "research"), "mirror progress")
    require(all(value in ("pending", "complete", "absent", "not-required")
                for value in journal["mirrors"].values()), "invalid mirror progress")
    if manifest["old"] == manifest["new"]:
        require(set(journal["mirrors"].values()) == {"not-required"}, "unexpected no-change mirror")
    else:
        require("not-required" not in journal["mirrors"].values(), "missing changed-source mirrors")
        if journal["phase"] in READY:
            require(journal["mirrors"]["site"] == "complete" and
                    all(value in ("complete", "absent") for value in journal["mirrors"].values()),
                    "incomplete ready mirror receipts")
    require(manifest["purpose"] in ("update", "setup"), "unknown source purpose")
    members = {("helpers/" + x) for x in HELPERS} | {("units/" + x) for x in UNITS}
    if manifest["purpose"] == "setup":
        members |= set(SETUP_MEMBERS)
    exact_keys(manifest["members"], members, "capsule members")
    for rel, digest in manifest["members"].items():
        require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest), "invalid member digest")
        data = safe_read(capsule / rel, 256 * 1024, mode=0o600)
        require(sha(data) == digest, "changed capsule member: " + rel)
    validate_setup(journal, manifest, capsule)
    return journal, manifest, capsule


def entry_capture(owner):
    old = source_revision(git("rev-parse", "HEAD"))
    data = {}
    for name in HELPERS:
        rel = "app/deploy/" + name
        body = safe_read(APP / rel, 256 * 1024)
        require(body == object_bytes(old, rel), "checkout helper is not complete at HEAD: " + name)
        data[name] = body
    directory(CAPSULES, create=True)
    capsule = CAPSULES / uuid.uuid4().hex
    directory(capsule, create=True)
    directory(capsule / "helpers", create=True)
    for name, body in data.items():
        atomic_write(capsule / "helpers" / name, body, 0o600)
    json_write(capsule / "entry.json", {"owner_sha256": owner, "old": old,
                                      "helpers": {name: sha(body) for name, body in data.items()}})
    return capsule


def entry_read(owner, attempt, old):
    require(re.fullmatch(r"[0-9a-f]{32}", attempt), "invalid entry capsule")
    capsule = CAPSULES / attempt
    entry = closed_json(safe_read(capsule / "entry.json", 65536, mode=0o600))
    exact_keys(entry, ("owner_sha256", "old", "helpers"), "entry capture")
    require(entry["owner_sha256"] == owner and entry["old"] == old, "entry/source mismatch")
    exact_keys(entry["helpers"], HELPERS, "entry helpers")
    data = {}
    for name in HELPERS:
        body = safe_read(capsule / "helpers" / name, 256 * 1024, mode=0o600)
        require(sha(body) == entry["helpers"][name], "changed entry helper")
        data["helpers/" + name] = body
    return capsule, data



def entry_old(owner, attempt):
    """Read the preflight capture; never recapture a later checkout revision."""
    require(type(attempt) is str and re.fullmatch(r"[0-9a-f]{32}", attempt), "invalid entry capsule")
    entry = closed_json(safe_read(CAPSULES / attempt / "entry.json", 65536, mode=0o600))
    exact_keys(entry, ("owner_sha256", "old", "helpers"), "entry capture")
    old = source_revision(entry["old"])
    entry_read(owner, attempt, old)
    return old


def retire_entry(attempt):
    """Retire only a verified unprepared capsule, never transaction evidence."""
    require(not pending_exists(), "cannot retire entry while a transaction is pending")
    require(type(attempt) is str and re.fullmatch(r"[0-9a-f]{32}", attempt), "invalid entry retirement")
    capsule = CAPSULES / attempt
    directory(capsule)
    require({p.name for p in capsule.iterdir()} == {"entry.json", "helpers"},
            "entry capsule has transaction or unexpected evidence")
    entry = closed_json(safe_read(capsule / "entry.json", 65536, mode=0o600))
    exact_keys(entry, ("owner_sha256", "old", "helpers"), "entry capture")
    require(type(entry["owner_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", entry["owner_sha256"]),
            "invalid entry owner")
    source_revision(entry["old"])
    entry_read(entry["owner_sha256"], attempt, entry["old"])
    directory(capsule / "helpers")
    require({p.name for p in (capsule / "helpers").iterdir()} == set(HELPERS), "unexpected entry helper")
    for name in HELPERS:
        (capsule / "helpers" / name).unlink()
    (capsule / "helpers").rmdir()
    (capsule / "entry.json").unlink()
    capsule.rmdir()
    try:
        sync_dir(CAPSULES)
    except OSError as exc:
        raise EffectNeedsReadback("entry retirement visible for " + attempt + "; " + str(exc)) from exc


def retire_unprepared_entries():
    if not CAPSULES.exists():
        return
    directory(CAPSULES)
    retired = 0
    for candidate in CAPSULES.iterdir():
        if retired == 64:
            break
        if not re.fullmatch(r"[0-9a-f]{32}", candidate.name):
            continue
        directory(candidate)
        try:
            (candidate / "manifest.json").lstat()
        except FileNotFoundError:
            # Partially created or unknown entries are preserved for diagnosis.
            if {p.name for p in candidate.iterdir()} != {"entry.json", "helpers"}:
                continue
            retire_entry(candidate.name)
            retired += 1


def write_journal(journal):
    json_write(PENDING, journal)


def prepare(owner, old, new, attempt, purpose="update"):
    require(not pending_exists(), "pending transaction already exists")
    old, new = source_revision(old), source_revision(new)
    require(git("rev-parse", "HEAD") == old, "source changed before preparation")
    require(git("rev-parse", new + "^{commit}") == new, "target commit unavailable")
    capsule, data = entry_read(owner, attempt, old)
    require(purpose in ("update", "setup"), "invalid source purpose")
    require(purpose != "setup" or old == new, "setup cannot change source revision")
    enrollment, timers = unit_inventory()
    setup = setup_capture(attempt) if purpose == "setup" else None
    if setup is not None:
        setup["activate"] = list((CORE_TIMERS if enrollment == "absent" else ()) +
                                 (ANCILLARY_TIMERS if setup["ancillary_enrollment"] == "absent" else ()))
        for rel in SETUP_MEMBERS:
            source = "app/deploy/" + Path(rel).name
            body = object_bytes(new, source)
            require(0 < len(body) <= 256 * 1024 and safe_read(APP / source, 256 * 1024) == body,
                    "setup capture differs from selected source")
            directory((capsule / rel).parent, create=True)
            atomic_write(capsule / rel, body, 0o600)
            data[rel] = body
    changed = git("diff", "--name-only", old, new).splitlines()
    require(len(changed) <= 20000 and all("\n" not in x and len(x) <= 4096 for x in changed),
            "changed-path capture too large")
    for name in UNITS:
        body = object_bytes(new, "app/deploy/" + name)
        require(0 < len(body) <= 65536, "invalid target unit size")
        reviewed_unit_shape(name, body)
        data["units/" + name] = body
    directory(capsule / "units", create=True)
    for rel, body in data.items():
        if rel.startswith("units/"):
            atomic_write(capsule / rel, body, 0o600)
    manifest = {"schema": "macro.live-source-update.v1", "attempt": attempt,
                "owner_sha256": owner, "old": old, "new": new, "changed": changed,
                "purpose": purpose, "setup": setup, "boot_id": boot_identity(), "enrollment": enrollment, "timers": timers,
                "service_cgroups": {unit: unit_show(unit, "ControlGroup") for unit in UNITS
                                   if unit.endswith(".service")} if enrollment == "present" else {},
                "members": {rel: sha(body) for rel, body in data.items()}}
    raw = (json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    require(len(raw) <= MAX_MANIFEST, "oversized manifest")
    atomic_write(capsule / "manifest.json", raw, 0o600)
    sync_dir(capsule)
    sync_dir(CAPSULES)
    journal = {"schema": manifest["schema"], "attempt": attempt, "manifest_sha256": sha(raw),
               "phase": "PREPARED", "restoration": {unit: "pending" for unit in timers},
               "mirrors": {name: "not-required" if old == new else "pending"
                           for name in ("site", "news", "research")},
               "setup": None if setup is None else {
                   "stage": "PACKAGES", "smoke": None, "cron": None,
                   "activation": {unit: {"enable": "pending", "start": "pending"}
                                  for unit in setup["activate"]}}}
    write_journal(journal)
    return capsule


def open_lock():
    directory(LOCK.parent, sticky=True)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        verify_lock(fd)
    except BaseException:
        os.close(fd)
        raise
    return fd


def verify_lock(fd):
    directory(LOCK.parent, sticky=True)
    st, named = os.fstat(fd), LOCK.lstat()
    require(stat.S_ISREG(st.st_mode) and stat.S_ISREG(named.st_mode)
            and st.st_uid == ROOT_UID and st.st_gid == ROOT_GID
            and stat.S_IMODE(st.st_mode) == 0o600 and st.st_nlink == 1
            and (st.st_dev, st.st_ino) == (named.st_dev, named.st_ino), "unsafe/replaced source lock")


def check_cgroup(unit, captured=""):
    require(unit in UNITS and unit.endswith(".service"), "foreign cgroup unit")
    directory(CGROUP)
    # Only the admitted unified hierarchy supplies this proof. A missing
    # interface is not an empty process population.
    require((CGROUP / "cgroup.controllers").is_file()
            and not (CGROUP / "cgroup.controllers").is_symlink(), "unified cgroup interface unavailable")
    groups = {captured, unit_show(unit, "ControlGroup"), "/system.slice/" + unit} - {""}
    for value in groups:
        require(value.startswith("/") and ".." not in Path(value).parts and Path(value).name == unit,
                "invalid original/current control group")
        group_root = CGROUP / value.lstrip("/")
        try:
            directory(group_root)
        except FileNotFoundError:
            continue
        def walk_error(error):
            raise error
        for current, dirs, files in os.walk(group_root, followlinks=False, onerror=walk_error):
            current = Path(current)
            require(not any((current / name).is_symlink() for name in dirs), "symlink cgroup subtree")
            procs = current / "cgroup.procs"
            try:
                metadata = procs.lstat()
            except FileNotFoundError:
                try:
                    current.lstat()
                except FileNotFoundError:
                    continue
                raise Refusal("cgroup process-membership interface unavailable")
            require(stat.S_ISREG(metadata.st_mode), "invalid cgroup process file")
            require(not procs.read_text().strip(), "live service cgroup remains populated")


def recovery_target(manifest):
    require(git("rev-parse", "HEAD") in (manifest["old"], manifest["new"]),
            "foreign HEAD during original source transaction")


def source_ready(manifest, journal):
    require(git("rev-parse", "HEAD") == manifest["new"], "HEAD differs from captured target")
    # Runtime data artifacts have separate owners. This source fence is bounded
    # to the three core lanes and does not assert estate-wide writer isolation.
    run([GIT, "-C", str(APP), "diff", "--quiet", "--no-ext-diff", manifest["new"], "--",
         "*.py", "*.sh", "*.yml", "*.yaml", "*.toml", "app/deploy"])
    run([SYNC, "-f", str(APP)])
    for name, target in (("site", APP / "site.served"), ("news", APP / "press_news.served"),
                         ("research", APP / "press_research.served")):
        try:
            directory(target)
        except FileNotFoundError:
            require(journal["mirrors"][name] != "complete",
                    "completed mirror destination is missing: " + name)
            continue
        run([SYNC, "-f", str(target)])


def record_mirror(journal, manifest, name, outcome):
    require(journal["phase"] == "MUTATING" and name in ("site", "news", "research")
            and outcome in ("complete", "absent"), "invalid mirror completion")
    source = APP / "site" if name == "site" else APP / "properties" / name
    destination = APP / "site.served" if name == "site" else APP / ("press_" + name + ".served")
    if outcome == "absent":
        require(name != "site", "main site mirror cannot be absent")
        try:
            source.lstat()
        except FileNotFoundError:
            pass
        else:
            raise Refusal("mirror source is present")
    else:
        directory(source)
        directory(destination)
        run([SYNC, "-f", str(destination)])
    journal["mirrors"][name] = outcome
    write_journal(journal)


def complete(journal, manifest, capsule):
    final_journal = (json.dumps(journal, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    json_write(capsule / "completion.json", {
        "schema": journal["schema"], "attempt": journal["attempt"], "new": manifest["new"],
        "purpose": manifest["purpose"], "phase": "COMPLETE",
        "manifest_sha256": journal["manifest_sha256"], "journal_sha256": sha(final_journal),
        "journal": journal})
    PENDING.unlink()
    try:
        sync_dir(PENDING.parent)
    except OSError as exc:
        raise EffectNeedsReadback("journal retirement visible for attempt " + journal["attempt"] +
                                 "; reconcile pending absence and completion receipt; " + str(exc)) from exc


def restore(journal, manifest, capsule, *, retire=True):
    require(journal["phase"] in READY, "source is not ready for timer restoration")
    source_ready(manifest, journal)
    journal["phase"] = "RESTORING"
    write_journal(journal)
    boot_changed = boot_identity() != manifest["boot_id"]
    held = []
    for unit, intent in manifest["timers"].items():
        try:
            require(unit_enabled(unit) == intent["enabled"], "timer enablement changed; preserving " + unit)
            active = unit_show(unit, "ActiveState")
            require(active in ("active", "inactive"), "timer is in a foreign/transitional state: " + unit)
            progress = journal["restoration"][unit]
            if boot_changed and intent["enabled"] == "disabled" and intent["active"]:
                raise Refusal("manual timer activation does not survive a boot: " + unit)
            start = intent["active"] and active == "inactive"
            if start:
                require(progress == "pending", "ambiguous/withdrawn timer restoration: " + unit)
            elif not intent["active"]:
                require(active == "inactive", "inactive timer intent changed: " + unit)
        except (Refusal, OSError) as exc:
            held.append(str(exc))
            continue
        if start:
            journal["restoration"][unit] = "starting"
            # Persistence failures terminate this invocation. A sibling must not
            # accidentally publish an in-memory state whose write failed.
            write_journal(journal)
            try:
                run([SYSTEMCTL, "start", unit])
                require(unit_enabled(unit) == intent["enabled"] and unit_show(unit, "ActiveState") == "active",
                        "timer restoration failed: " + unit)
            except (Refusal, OSError) as exc:
                held.append(str(exc))
                continue
        journal["restoration"][unit] = "restored"
        write_journal(journal)
    for unit, intent in manifest["timers"].items():
        try:
            require(unit_enabled(unit) == intent["enabled"] and
                    unit_show(unit, "ActiveState") == ("active" if intent["active"] else "inactive"),
                    "timer changed during restoration: " + unit)
        except (Refusal, OSError) as exc:
            held.append(str(exc))
    require(not held, "; ".join(dict.fromkeys(held)))
    if retire:
        complete(journal, manifest, capsule)


def replace_owner(script_fd, revision, *, adoption=False):
    require(not pending_exists(), "cannot replace owner while a transaction is unresolved")
    revision = source_revision(revision)
    data = object_bytes(revision, "app/deploy/update.sh")
    require(0 < len(data) <= MAX_OWNER, "invalid owner candidate")
    require(b"# BEGIN LIVE_SOURCE_OWNER" in data and b"# END LIVE_SOURCE_OWNER" in data,
            "candidate has no embedded source owner")
    if adoption:
        require(owner_bytes(script_fd) == data, "adoption candidate is not the exact selected Git object")
    else:
        require(safe_read(APP / "app/deploy/update.sh", MAX_OWNER) == data,
                "checkout owner differs from selected Git object")
    run([BASH, "-n"], input=data)
    fd = open_lock()
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        verify_lock(fd)
        require(not pending_exists(), "source transaction appeared before owner replacement")
        owner_identity(script_fd, candidate=adoption)
        atomic_write(OWNER, data, 0o755)
        try:
            require(safe_read(OWNER, MAX_OWNER, mode=0o755) == data, "installed owner readback mismatch")
        except (Refusal, OSError) as exc:
            raise EffectNeedsReadback("owner replacement visible; expected sha256=" + sha(data) +
                                     "; readback failed: " + str(exc)) from exc
    finally:
        os.close(fd)
    print(sha(data))


# Setup is a purpose of this installed owner, not a second installer controller.
def setup_capture(attempt):
    ancillary, timers = unit_inventory(ANCILLARY_UNITS, check_public=False)
    target = APP / ".venv"
    try:
        info = target.lstat()
    except FileNotFoundError:
        environment = {"mode": "create", "path": str(STATE.parent / "envs" / attempt),
                       "device": None, "inode": None}
    else:
        require(info.st_uid == ROOT_UID and info.st_gid == ROOT_GID
                and (stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)),
                "unsafe existing live environment")
        resolved = target.resolve(strict=True)
        directory(resolved)
        info = resolved.stat()
        environment = {"mode": "existing", "path": str(resolved),
                       "device": info.st_dev, "inode": info.st_ino}
    return {"environment": environment, "ancillary_enrollment": ancillary,
            "ancillary_timers": timers, "activate": []}


def validate_setup(journal, manifest, capsule):
    if manifest["purpose"] == "update":
        require(manifest["setup"] is None and journal["setup"] is None, "foreign setup state")
        return
    require(manifest["purpose"] == "setup" and manifest["old"] == manifest["new"],
            "invalid setup source purpose")
    config, state = manifest["setup"], journal["setup"]
    exact_keys(config, ("environment", "ancillary_enrollment", "ancillary_timers", "activate"), "setup capture")
    exact_keys(state, ("stage", "smoke", "activation", "cron"), "setup progress")
    require(state["stage"] in ("PACKAGES", "READY", "SMOKED", "ARMED", "CRON_RETIRED"),
            "invalid setup stage")
    require((state["stage"] == "PACKAGES") == (journal["phase"] not in READY),
            "setup stage/source phase disagreement")
    env = config["environment"]
    exact_keys(env, ("mode", "path", "device", "inode"), "setup environment")
    require(env["mode"] in ("existing", "create") and type(env["path"]) is str
            and Path(env["path"]).is_absolute() and ".." not in Path(env["path"]).parts,
            "invalid setup environment")
    if env["mode"] == "create":
        require(env["path"] == str(STATE.parent / "envs" / manifest["attempt"])
                and env["device"] is None and env["inode"] is None, "foreign candidate environment")
    else:
        require(type(env["device"]) is int and type(env["inode"]) is int
                and env["device"] >= 0 and env["inode"] > 0, "invalid environment identity")
    require(config["ancillary_enrollment"] in ("present", "absent"), "invalid ancillary enrollment")
    names = set(ANCILLARY_TIMERS) if config["ancillary_enrollment"] == "present" else set()
    exact_keys(config["ancillary_timers"], names, "ancillary intent")
    for intent in config["ancillary_timers"].values():
        exact_keys(intent, ("enabled", "active"), "ancillary intent")
        require(intent["enabled"] in ("enabled", "disabled") and type(intent["active"]) is bool,
                "invalid ancillary intent")
    expected = (set(CORE_TIMERS) if manifest["enrollment"] == "absent" else set()) | (
        set(ANCILLARY_TIMERS) if config["ancillary_enrollment"] == "absent" else set())
    require(type(config["activate"]) is list and len(config["activate"]) == len(expected)
            and set(config["activate"]) == expected, "invalid fresh activation intent")
    exact_keys(state["activation"], expected, "activation progress")
    for value in state["activation"].values():
        exact_keys(value, ("enable", "start"), "activation step")
        require(all(x in ("pending", "starting", "done") for x in value.values()), "invalid activation step")
    smoke = state["smoke"]
    if smoke is not None:
        keys = {"phase", "boot_id", "previous_invocation", "not_before", "monotonic_us"}
        require(type(smoke) is dict and smoke.get("phase") in ("starting", "passed"), "invalid smoke phase")
        if smoke["phase"] == "passed":
            keys |= {"invocation", "status_sha256", "quotes_sha256"}
        exact_keys(smoke, keys, "smoke receipt")
        require(type(smoke["boot_id"]) is str and re.fullmatch(r"[0-9a-f-]{36}", smoke["boot_id"])
                and type(smoke["previous_invocation"]) is str
                and (smoke["previous_invocation"] == "" or re.fullmatch(r"[0-9a-f]{32}", smoke["previous_invocation"]))
                and type(smoke["monotonic_us"]) is int and smoke["monotonic_us"] >= 0,
                "invalid smoke identity")
        utc_timestamp(smoke["not_before"])
        if smoke["phase"] == "passed":
            require(type(smoke["invocation"]) is str and re.fullmatch(r"[0-9a-f]{32}", smoke["invocation"]),
                    "invalid completed invocation")
            for name, limit in (("status", 2 * 1024 * 1024), ("quotes", 32 * 1024 * 1024)):
                digest = smoke[name + "_sha256"]
                require(type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest), "invalid smoke hash")
                require(sha(safe_read(capsule / ("smoke-" + name + ".json"), limit, mode=0o600)) == digest,
                        "changed captured smoke publication")
    if state["stage"] in ("SMOKED", "ARMED", "CRON_RETIRED"):
        require(smoke is not None and smoke["phase"] == "passed", "missing completed smoke")
    cron = state["cron"]
    if cron is not None:
        exact_keys(cron, ("phase", "before_sha256", "after_sha256", "before_absent"), "cron receipt")
        require(cron["phase"] in ("planned", "applying", "applied") and type(cron["before_absent"]) is bool,
                "invalid cron phase")
        for name in ("before", "after"):
            require(sha(safe_read(capsule / ("cron." + name), 1024 * 1024, mode=0o600)) == cron[name + "_sha256"],
                    "changed cron capture")
    if state["stage"] == "CRON_RETIRED":
        require(cron is not None and cron["phase"] == "applied", "missing cron postimage")
    if state["stage"] == "PACKAGES":
        require(smoke is None and cron is None, "package phase contains later effect receipts")
    if state["stage"] == "READY":
        require(smoke is None or smoke["phase"] == "starting", "ready phase contains completed smoke")
    if state["stage"] in ("PACKAGES", "READY"):
        require(all(set(value.values()) == {"pending"} for value in state["activation"].values()),
                "activation preceded successful smoke")
    if state["stage"] in ("PACKAGES", "READY", "SMOKED"):
        require(cron is None, "cron retirement preceded timer qualification")
    if state["stage"] in ("ARMED", "CRON_RETIRED"):
        require(all(set(value.values()) == {"done"} for value in state["activation"].values())
                and all(value == "restored" for value in journal["restoration"].values()),
                "armed stage has unfinished timer effects")


def utc_timestamp(value):
    require(type(value) is str, "invalid timestamp type")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset() == timedelta(0), "timestamp is not UTC")
    return parsed


def setup_environment(manifest):
    env = manifest["setup"]["environment"]
    target = APP / ".venv"
    if env["mode"] == "existing":
        resolved = target.resolve(strict=True)
        directory(resolved)
        info = resolved.stat()
        require(str(resolved) == env["path"] and (info.st_dev, info.st_ino) == (env["device"], env["inode"]),
                "live environment identity changed")
        return "reuse", resolved
    candidate = Path(env["path"])
    try:
        info = target.lstat()
    except FileNotFoundError:
        directory(candidate, create=True)
        return "prepare", candidate
    require(stat.S_ISLNK(info.st_mode) and info.st_uid == ROOT_UID and info.st_gid == ROOT_GID
            and os.readlink(target) == str(candidate), "foreign live environment appeared")
    directory(candidate)
    return "reuse", candidate


def qualify_environment(path):
    directory(path)
    result = subprocess.run([str(path / "bin/python"), "-c",
        "import pandas,pyarrow,numpy,requests,yaml,jinja2,datasketch,boto3;"
        "import scripts.vps_live_orchestrator"],
        cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=90)
    require(result.returncode == 0, "captured live runtime imports failed")


def publish_environment(manifest, journal):
    # This precedes every checkout import, including the bind-only setup stage.
    source_ready(manifest, journal)
    mode, path = setup_environment(manifest)
    qualify_environment(path)
    if mode == "reuse":
        return
    directory(APP)
    run([SYNC, "-f", str(path)])
    published = False
    try:
        # symlink creation is atomic and fails on any existing destination. An
        # absence check followed by replace would permit a competing postimage.
        os.symlink(str(path), APP / ".venv")
        published = True
        sync_dir(APP)
    except OSError as exc:
        if published:
            raise EffectNeedsReadback("live environment link visible; reconcile " + str(path)) from exc
        raise


def setup_smoke(journal, manifest, capsule):
    state = journal["setup"]
    require(journal["phase"] in READY and state["stage"] in ("READY", "SMOKED"), "setup smoke not ready")
    if state["smoke"] is not None and state["smoke"]["phase"] == "passed":
        return
    unit = "macro-live-fast.service"
    if state["smoke"] is None:
        require(unit_show(unit, "ActiveState") in ("inactive", "failed")
                and unit_show(unit, "MainPID") == "0" and unit_show(unit, "ControlPID") == "0",
                "fast lane is already running")
        state["smoke"] = {"phase": "starting", "boot_id": boot_identity(),
                          "previous_invocation": unit_show(unit, "InvocationID"),
                          "not_before": datetime.now(timezone.utc).isoformat(),
                          "monotonic_us": time.monotonic_ns() // 1000}
        write_journal(journal)
        run([SYSTEMCTL, "start", unit])
    smoke = state["smoke"]
    require(boot_identity() == smoke["boot_id"], "in-flight smoke crossed a boot; reconcile original invocation")
    invocation = unit_show(unit, "InvocationID")
    require(re.fullmatch(r"[0-9a-f]{32}", invocation) and invocation != smoke["previous_invocation"],
            "no new guarded smoke invocation")
    require(unit_show(unit, "ActiveState") == "inactive" and unit_show(unit, "MainPID") == "0"
            and unit_show(unit, "ControlPID") == "0" and unit_show(unit, "Result") == "success"
            and unit_show(unit, "ExecMainStatus") == "0" and unit_show(unit, "ExecMainCode") == "1",
            "original smoke invocation has not completed successfully")
    started = int(unit_show(unit, "ExecMainStartTimestampMonotonic"))
    finished = int(unit_show(unit, "ExecMainExitTimestampMonotonic"))
    require(smoke["monotonic_us"] <= started <= finished, "smoke invocation predates admission")
    status = safe_read(STATE / "status-fast.json", 2 * 1024 * 1024)
    row = closed_json(status)
    require(type(row) is dict and row.get("schema") == "vps_live_lane.v1" and row.get("lane") == "fast"
            and row.get("ok") is True and row.get("invocation_id") == invocation,
            "fast publication status is not bound to the guarded invocation")
    boundary = utc_timestamp(smoke["not_before"])
    require(boundary <= utc_timestamp(row.get("started_at")) <= utc_timestamp(row.get("finished_at"))
            <= datetime.now(timezone.utc), "fast publication does not belong to this smoke")
    tasks = row.get("tasks")
    require(type(tasks) is list, "missing fast task evidence")
    quotes_tasks = [task for task in tasks if type(task) is dict and task.get("name") == "display_quotes"]
    require(len(quotes_tasks) == 1 and quotes_tasks[0].get("status") == "ok"
            and quotes_tasks[0].get("returncode") == 0
            and "live/quotes.json" in quotes_tasks[0].get("published", []), "fresh quote publication is unproven")
    quote_path = STATE.parent / "public/live/quotes.json"
    quotes = safe_read(quote_path, 32 * 1024 * 1024)
    hashes = quotes_tasks[0].get("publication_sha256")
    require(type(hashes) is dict and hashes.get("live/quotes.json") == sha(quotes),
            "quote bytes do not match the guarded producer publication")
    # Reuse the live producer's actual quote gate. Never substitute a setup-only
    # freshness formula or accept an old file on a successful systemctl return.
    result = subprocess.run([str(APP / ".venv/bin/python"), "-c",
        "from pathlib import Path; import sys;"
        "from scripts.vps_live_orchestrator import quote_snapshot_error;"
        "sys.exit(1 if quote_snapshot_error(Path(sys.argv[1]),min_resolved=5,min_coverage=.10) else 0)",
        str(quote_path)], cwd=APP, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    require(result.returncode == 0 and safe_read(quote_path, 32 * 1024 * 1024) == quotes,
            "smoke quote validation or stable capture failed")
    require(safe_read(STATE / "status-fast.json", 2 * 1024 * 1024) == status
            and unit_show(unit, "InvocationID") == invocation, "smoke evidence changed during capture")
    atomic_write(capsule / "smoke-status.json", status, 0o600)
    atomic_write(capsule / "smoke-quotes.json", quotes, 0o600)
    smoke.update(phase="passed", invocation=invocation, status_sha256=sha(status), quotes_sha256=sha(quotes))
    state["stage"] = "SMOKED"
    write_journal(journal)


def verify_ancillary_intent(manifest):
    for unit, intent in manifest["setup"]["ancillary_timers"].items():
        require(unit_enabled(unit) == intent["enabled"]
                and unit_show(unit, "ActiveState") == ("active" if intent["active"] else "inactive"),
                "ancillary timer intent changed: " + unit)


def setup_arm(journal, manifest, capsule):
    state = journal["setup"]
    require(state["stage"] in ("SMOKED", "ARMED") and journal["phase"] in READY, "setup arming is not ready")
    restore(journal, manifest, capsule, retire=False)
    verify_ancillary_intent(manifest)
    for unit in manifest["setup"]["activate"]:
        progress = state["activation"][unit]
        enabled = unit_enabled(unit)
        if enabled != "enabled":
            require(enabled == "disabled" and progress["enable"] == "pending",
                    "ambiguous/withdrawn fresh timer enablement: " + unit)
            progress["enable"] = "starting"
            write_journal(journal)
            run([SYSTEMCTL, "enable", unit])
            require(unit_enabled(unit) == "enabled", "fresh timer was not enabled: " + unit)
        else:
            require(progress["enable"] != "pending", "foreign fresh timer enablement: " + unit)
        # Reapply the durability barrier on an observed postimage as well as a
        # newly issued enable. A previous invocation may have stopped here.
        try:
            run([SYNC, "-f", str(UNIT_DIR)])
        except (Refusal, OSError) as exc:
            raise EffectNeedsReadback("fresh enablement visible; reconcile " + unit) from exc
        progress["enable"] = "done"
        write_journal(journal)
        active = unit_show(unit, "ActiveState")
        if active != "active":
            require(active == "inactive" and progress["start"] == "pending",
                    "ambiguous/withdrawn fresh timer activation: " + unit)
            progress["start"] = "starting"
            write_journal(journal)
            run([SYSTEMCTL, "start", unit])
            require(unit_show(unit, "ActiveState") == "active", "fresh timer was not activated: " + unit)
        # An already-active timer satisfies the captured fresh intent. This
        # includes boot activation after our durable enablement. Observe it;
        # never issue another start merely to manufacture an action receipt.
        progress["start"] = "done"
        write_journal(journal)
    state["stage"] = "ARMED"
    write_journal(journal)


def cron_read():
    result = subprocess.run([CRONTAB, "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, env={**os.environ, "LC_ALL": "C"})
    require(len(result.stdout) <= 1024 * 1024 and len(result.stderr) <= 65536, "oversized crontab response")
    if result.returncode == 0:
        return result.stdout, False
    require(result.returncode == 1 and not result.stdout
            and result.stderr.strip() == b"no crontab for root", "cannot establish original crontab")
    return b"", True


def retire_setup_cron(journal, manifest, capsule):
    state = journal["setup"]
    require(state["stage"] in ("ARMED", "CRON_RETIRED"), "setup timers are not qualified")
    if state["cron"] is None:
        before, absent = cron_read()
        after = b"".join(line for line in before.splitlines(keepends=True)
                         if b"macro-live" not in line and b"build_live_overlay" not in line)
        atomic_write(capsule / "cron.before", before, 0o600)
        atomic_write(capsule / "cron.after", after, 0o600)
        state["cron"] = {"phase": "planned", "before_sha256": sha(before),
                         "after_sha256": sha(after), "before_absent": absent}
        write_journal(journal)
    receipt = state["cron"]
    current, absent = cron_read()
    if sha(current) != receipt["after_sha256"]:
        require(receipt["phase"] == "planned" and sha(current) == receipt["before_sha256"]
                and absent == receipt["before_absent"], "cron retirement requires original-effect reconciliation")
        receipt["phase"] = "applying"
        write_journal(journal)
        run([CRONTAB, str(capsule / "cron.after")])
        current, _ = cron_read()
        require(sha(current) == receipt["after_sha256"], "cron retirement postimage mismatch")
    try:
        run([SYNC, "-f", str(CRON_SPOOL)])
    except (Refusal, OSError) as exc:
        raise EffectNeedsReadback("cron postimage observed; durability requires readback") from exc
    require(sha(cron_read()[0]) == receipt["after_sha256"], "cron changed during durability verification")
    receipt["phase"] = "applied"
    state["stage"] = "CRON_RETIRED"
    write_journal(journal)


def setup_action(action, journal, manifest, capsule):
    require(manifest["purpose"] == "setup", "not an original setup transaction")
    state = journal["setup"]
    if action == "inspect":
        print(state["stage"])
    elif action == "environment":
        require(state["stage"] == "PACKAGES" and journal["phase"] == "MUTATING",
                "setup package mutation is not admitted")
        mode, path = setup_environment(manifest)
        print(mode + "\n" + str(path))
    elif action == "bind-environment":
        require(state["stage"] == "PACKAGES" and journal["phase"] == "MUTATING", "environment mutation not admitted")
        publish_environment(manifest, journal)
    elif action == "ready":
        require(state["stage"] == "PACKAGES" and journal["phase"] == "MUTATING", "setup mutation not admitted")
        publish_environment(manifest, journal)
        source_ready(manifest, journal)
        journal["phase"] = "SOURCE_READY"
        state["stage"] = "READY"
        write_journal(journal)
    elif action == "smoke":
        source_ready(manifest, journal)
        setup_smoke(journal, manifest, capsule)
    elif action == "arm":
        setup_arm(journal, manifest, capsule)
    elif action == "finish":
        require(state["stage"] in ("ARMED", "CRON_RETIRED"), "setup is not ready to complete")
        source_ready(manifest, journal)
        qualify_environment(setup_environment(manifest)[1])
        verify_ancillary_intent(manifest)
        for unit, intent in manifest["timers"].items():
            require(unit_enabled(unit) == intent["enabled"] and unit_show(unit, "ActiveState") ==
                    ("active" if intent["active"] else "inactive"), "restored core timer changed: " + unit)
        for unit in manifest["setup"]["activate"]:
            require(unit_enabled(unit) == "enabled" and unit_show(unit, "ActiveState") == "active",
                    "fresh timer changed before setup completion: " + unit)
        retire_setup_cron(journal, manifest, capsule)
        complete(journal, manifest, capsule)
    else:
        raise Refusal("unknown setup action")


def main(argv):
    require(os.geteuid() == ROOT_UID, "source owner requires root")
    script_fd, action, *args = argv
    # This absolute budget includes owner verification and waiting for fd 8.
    # The same host monotonic clock survives exec; it is never a data timestamp.
    live_budget = {"snapshot": 400.0, "bars": 880.0, "sector-inputs": 880.0}.get(args[0]) if action == "run" and len(args) == 1 else None
    live_deadline = time.monotonic() + live_budget if live_budget is not None else None
    if action == "adopt-owner":
        require(len(args) == 1, "adopt-owner arguments")
        owner_identity(script_fd, candidate=True)
        replace_owner(script_fd, args[0], adoption=True)
        return
    owner = owner_identity(script_fd)
    if action == "run":
        require(len(args) == 1 and args[0] in RUN_LANES, "unknown live lane")
        try:
            os.close(9)
        except OSError:
            pass
        fd = open_lock()
        if fd != 8:
            os.dup2(fd, 8, inheritable=True)
            os.close(fd)
        else:
            os.set_inheritable(8, True)
        if live_deadline is None:
            fcntl.flock(8, fcntl.LOCK_SH)
        else:
            while True:
                require(time.monotonic() < live_deadline, "live lane budget exhausted waiting for source")
                try:
                    fcntl.flock(8, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(min(.05, max(0, live_deadline - time.monotonic())))
        verify_lock(8)
        # The installed owner may have changed while this invocation waited.
        owner = owner_identity(script_fd)
        found = read_pending(owner)
        if found:
            journal, manifest, _ = found
            require(journal["phase"] in READY, "source update is pending: " + journal["phase"])
        remaining = None if live_deadline is None else live_deadline - time.monotonic()
        require(remaining is None or remaining > 0, "live lane budget exhausted before source identity")
        try:
            revision = source_revision(git("rev-parse", "HEAD",
                timeout=None if remaining is None else min(5.0, remaining)))
        except subprocess.TimeoutExpired:
            raise Refusal("live lane budget exhausted during source identity") from None
        if found:
            require(revision == manifest["new"], "ready transaction HEAD mismatch")
        command = [str(APP / ".venv/bin/python"), "-m", "scripts.vps_live_orchestrator",
                   "--lane", args[0], "--source-revision", revision, "--source-lock-fd", "8"]
        if live_deadline is not None:
            require(time.monotonic() < live_deadline, "live lane budget exhausted before exec")
            command.extend(["--deadline-monotonic", repr(live_deadline)])
        os.chdir(APP)
        os.execv(str(APP / ".venv/bin/python"), command)
    elif action == "lock-path":
        fd = open_lock()
        os.close(fd)
        print(LOCK)
    elif action in ("lock", "unlock"):
        verify_lock(8)
        fcntl.flock(8, fcntl.LOCK_EX if action == "lock" else fcntl.LOCK_UN)
        verify_lock(8)
    elif action == "preflight":
        require(len(args) == 2 and args[0] in ("update", "setup"), "preflight purpose arguments")
        purpose, attempt = args
        found = read_pending(owner)
        if found:
            require(found[1]["purpose"] == purpose, "pending transaction belongs to " + found[1]["purpose"])
            require(not attempt or attempt == found[0]["attempt"], "foreign setup control attempt")
            recovery_target(found[1])
            print("1\n" + str(found[2]))
        else:
            require(not attempt, "original setup transaction is absent")
            retire_unprepared_entries()
            print("0\n" + str(entry_capture(owner)))
    elif action == "entry-old":
        require(len(args) == 1, "entry-old arguments")
        print(entry_old(owner, args[0]))
    elif action == "retire-entry":
        require(len(args) == 1, "retire-entry arguments")
        retire_entry(args[0])
    elif action == "enrollment":
        print(unit_inventory()[0])
    elif action == "prepare":
        require(len(args) == 4, "prepare arguments")
        print(prepare(owner, *args))
    elif action == "cgroup":
        require(len(args) == 1, "cgroup arguments")
        found = read_pending(owner)
        require(found is not None, "missing original cgroup capture")
        check_cgroup(args[0], found[1]["service_cgroups"].get(args[0], ""))
    elif action == "replace-owner":
        require(len(args) == 1, "replace-owner arguments")
        replace_owner(script_fd, args[0])
    elif action == "fsync-units":
        for unit in UNITS:
            path = UNIT_DIR / unit
            safe_read(path, 65536, mode=0o644)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        sync_dir(UNIT_DIR)
    else:
        found = read_pending(owner)
        require(found is not None, "missing source transaction")
        journal, manifest, capsule = found
        if action == "get":
            require(len(args) == 1 and args[0] in ("old", "new", "changed", "phase", "enrollment", "purpose"), "get arguments")
            value = journal["phase"] if args[0] == "phase" else manifest[args[0]]
            print("\n".join(value) if type(value) is list else value)
        elif action == "verify-target":
            recovery_target(manifest)
        elif action == "guards":
            require(journal["phase"] not in READY, "cannot re-enter mutation after source readiness")
            journal["phase"] = "GUARDS_READY"
            write_journal(journal)
        elif action == "mutating":
            require(journal["phase"] == "GUARDS_READY", "guards were not admitted")
            journal["phase"] = "MUTATING"
            write_journal(journal)
        elif action == "mirror":
            require(len(args) == 2, "mirror arguments")
            record_mirror(journal, manifest, *args)
        elif action == "ready":
            require(manifest["purpose"] == "update", "ordinary ready cannot admit setup")
            require(journal["phase"] == "MUTATING" or
                    (journal["phase"] == "GUARDS_READY" and manifest["old"] == manifest["new"]),
                    "source mutation has not completed")
            require(manifest["old"] == manifest["new"] or
                    (journal["mirrors"]["site"] == "complete" and
                     all(value in ("complete", "absent") for value in journal["mirrors"].values())),
                    "mirror completion is unproven")
            source_ready(manifest, journal)
            journal["phase"] = "SOURCE_READY"
            write_journal(journal)
        elif action == "verify-ready":
            require(journal["phase"] in READY, "source is not ready")
            source_ready(manifest, journal)
        elif action == "restore":
            require(manifest["purpose"] == "update", "ordinary restore cannot retire setup")
            restore(journal, manifest, capsule)
        elif action == "setup-action":
            require(len(args) == 1, "setup action arguments")
            setup_action(args[0], journal, manifest, capsule)
        else:
            raise Refusal("unknown source-owner action")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except EffectNeedsReadback as exc:
        print("macro-update: source barrier effect requires readback: " + str(exc), file=sys.stderr)
        sys.exit(75)
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("macro-update: source barrier refused: " + str(exc), file=sys.stderr)
        sys.exit(75)
MMX_LIVE_SOURCE_PY
}

# Closed service entry: no updater mutex, checkout helper, fetch, reset, status
# writer or fall-through. Python exit statuses (including 75) remain failures.
if [ "$#" -ge 1 ] && [ "$1" = --live-lane ]; then
	[ "$#" -eq 2 ] || exit 2
	case "$2" in fast|snapshot|bars|sector-inputs) ;; *) exit 2 ;; esac
	# Close the waiting Bash wrapper's inherited mutex copy as well.
	exec 9>&-
	live_source_control run "$2"
	exit $?
fi
# First adoption is install-only. It never resets the checkout or invokes the
# ordinary updater while still holding fd9. setup.sh supplies an exact Git object.
if [ "$#" -ge 1 ] && [ "$1" = --install-source-owner ]; then
	[ "$#" -eq 2 ] && [[ "$2" =~ ^[0-9a-f]{40}$ ]] || exit 2
	# Full provisioning may already own this very mutex description.
	if ! { : >&9; } 2>/dev/null; then
		exec 9>/var/lock/macro-update.lock
	fi
	[ /proc/$$/fd/9 -ef /var/lock/macro-update.lock ] || {
		echo "macro-update: inherited updater mutex is foreign" >&2; exit 75;
	}
	flock -n 9 || { echo "macro-update: owner adoption is busy" >&2; exit 75; }
	live_source_control adopt-owner "$2"
	exit $?
fi
# END LIVE_SOURCE_OWNER
# Attended recovery of a source baseline which was installed but never adopted
# by the complete API-managed Caddy configuration. Normal cron has no arguments.
CADDY_SOURCE_BASELINE=""
CADDY_RECONCILE_ARGS=()
LIVE_SOURCE_PURPOSE=update
LIVE_SETUP_CONTROL=""
LIVE_SETUP_ATTEMPT=""
if [ "$#" -eq 1 ] && [ "$1" = --live-setup ]; then
    LIVE_SOURCE_PURPOSE=setup
    shift
elif [ "$#" -eq 3 ] && [ "$1" = --live-setup-control ]; then
    [[ "$2" =~ ^[0-9a-f]{32}$ ]] || exit 2
    case "$3" in inspect|environment|bind-environment|ready|smoke|arm|finish) ;; *) exit 2 ;; esac
    LIVE_SOURCE_PURPOSE=setup
    LIVE_SETUP_ATTEMPT=$2
    LIVE_SETUP_CONTROL=$3
    shift 3
fi
if [ "$#" -ne 0 ]; then
	if [ "$#" -ne 2 ] || [ "$1" != --caddy-source-baseline ] ||
	   [[ ! "$2" =~ ^[0-9a-f]{40}$ ]]; then
		echo "macro-update: expected --caddy-source-baseline <protected-40-SHA>" >&2
		exit 2
	fi
	CADDY_SOURCE_BASELINE=$2
	CADDY_RECONCILE_ARGS=(--source-baseline "$2")
fi

# Serialize runs. Cron fires every 3 min, but a big nightly render commit can
# take longer than that (fetch + reset + rsync of a multi-hundred-MB site/).
# Without the lock, a second run's `git reset --hard` truncates-and-rewrites
# work-tree files WHILE the first run's rsync is still READING them — and rsync
# then renames a partial/0-byte copy into site.served with a perfectly atomic
# rename. Skipping is free: the next cron tick picks up whatever this run got.
if [ -n "$LIVE_SETUP_CONTROL" ]; then
    [ /proc/$$/fd/9 -ef /var/lock/macro-update.lock ] || {
        echo "macro-update: setup control must borrow the original updater mutex" >&2; exit 75;
    }
    flock -n 9 || exit 75
else
    exec 9>/var/lock/macro-update.lock
    if [ "$LIVE_SOURCE_PURPOSE" = update ]; then
        flock -n 9 || exit 0
    else
        flock -n 9 || exit 75
    fi
fi
# BEGIN OHLC_DELIVERY_RECONCILE
# OHLC generations live outside both rsync trees. The helper borrows this
# process's existing lock; it must never unlock or reacquire that shared fd.
# Carry a refusal to the final status while unrelated deployment work proceeds.
OHLC_DELIVERY_EXIT_STATUS=0
reconcile_ohlc_delivery() {
	if /usr/bin/python3 "$APP_DIR/scripts/publish_ohlc.py" reconcile --lock-fd 9; then
		return 0
	else
		OHLC_DELIVERY_EXIT_STATUS=$?
		echo "macro-update: OHLC reconciliation refused (status $OHLC_DELIVERY_EXIT_STATUS); preserving the selected generation" >&2
	fi
}
# END OHLC_DELIVERY_RECONCILE

# Resolve recovery before executing any mutable checkout helper. A new entry
# captures the exact HEAD helpers; a pending entry uses its original capsule.
LIVE_SOURCE_ENTRY=$(live_source_control preflight "$LIVE_SOURCE_PURPOSE" "$LIVE_SETUP_ATTEMPT")
LIVE_SOURCE_PENDING="${LIVE_SOURCE_ENTRY%%$'\n'*}"
LIVE_SOURCE_CAPSULE="${LIVE_SOURCE_ENTRY#*$'\n'}"
source "$LIVE_SOURCE_CAPSULE/helpers/market-memory-options-unit-boundary.sh"
source "$LIVE_SOURCE_CAPSULE/helpers/market-memory-options-runtime-fence.sh"
source "$LIVE_SOURCE_CAPSULE/helpers/market-memory-options-dropin-migration.sh"

OPTIONS_TIMER_WAS_ENABLED=0
if systemctl is-enabled macro-market-memory-options.timer >/dev/null 2>&1; then
	OPTIONS_TIMER_WAS_ENABLED=1
fi
OPTIONS_TIMER_WAS_ACTIVE=0
if systemctl is-active macro-market-memory-options.timer >/dev/null 2>&1; then
	OPTIONS_TIMER_WAS_ACTIVE=1
fi
OPTIONS_TIMER_DISARMED=0
OPTIONS_API_FENCE_MARKER=/run/macro-api-market-memory-options-deny.ready
OPTIONS_RECIPROCAL_FENCE_MARKER=/run/macro-market-memory-options-reciprocal-deny.ready
OPTIONS_RUNTIME_CLOSURE_REGEX='^(app/requirements\.txt|app/deploy/(update\.sh|codex-runtime-setup\.sh|macro-api\.service|macro-market-memory-(options|source|context|identity|breadth|technicals|experience|production-records)\.(service|timer)|market-memory-options-(prereqs|unit-boundary|runtime-fence|dropin-migration)\.sh)|scripts/(__init__|capture_market_memory_option_oi)\.py|engine/(__init__\.py|neuralweb/(__init__|market_memory|market_memory_(option_oi_observation|option_oi_store|pit))\.py)|contracts/market_memory/(option_oi_probe_receipt|spy_option_oi_source_observation|option_oi_capture_receipt|option_oi_store)\.v1\.schema\.json|config/market_memory_option_oi_source\.v1\.json|research/licenses/MASSIVE_ENTITLEMENT_RECORD\.md)$'
OPTIONS_RECIPROCAL_CLOSURE_REGEX='^(app/requirements\.txt|app/deploy/(update|market-memory-spy-rest-prereqs|market-memory-options-(unit-boundary|runtime-fence|dropin-migration))\.sh|app/deploy/macro-market-memory-(source|source-spy-rest|context|identity|breadth|technicals|technicals-v2|experience|experience-v2|production-records|options-context-audit)\.(service|timer)|scripts/(__init__|accrue_market_memory_spy_experience|accrue_market_memory_spy_experience_v2|audit_options_market_memory_context|capture_market_memory_options_episodes|capture_market_memory_technicals_v2|ingest_market_memory_sources_spy)\.py|engine/(__init__|options_signal_episode|options_market_memory_context|options_market_memory_receipt_store)\.py|engine/neuralweb/(__init__|market_memory(_pit|_trusted|_technical_observation|_technical_store|_experience_accrual|_production_records|_source_kernel|_sources(_spy)?)?)\.py|contracts/market_memory/(spy_experience_(registration|opportunity|outcome_revision|population_receipt)|options_signal_episode_production_record)\.v1\.schema\.json|contracts/options/options\.signal_episode\.v1\.schema\.json|config/market_memory_(canary|technical_price_basis|spy_experience_registration)\.v1\.json|config/market_memory_spy_experience_registration\.v2\.json|lib/(__init__|nyse_calendar)\.py|data/options_signal_episode/episodes\.jsonl|research/licenses/MASSIVE_ENTITLEMENT_RECORD\.md)$'
MARKET_MEMORY_EXPERIENCE_RUNTIME_REGEX='^(app/requirements\.txt|scripts/(__init__|accrue_market_memory_spy_experience)\.py|engine/(__init__\.py|neuralweb/(__init__|market_memory(_pit|_trusted|_technical_observation|_technical_store|_experience_accrual)?)\.py)|contracts/market_memory/spy_experience_(registration|opportunity|outcome_revision|population_receipt)\.v1\.schema\.json|config/market_memory_(canary|technical_price_basis|spy_experience_registration)\.v1\.json|lib/(__init__|nyse_calendar)\.py|research/licenses/MASSIVE_ENTITLEMENT_RECORD\.md)$'
MARKET_MEMORY_EXPERIENCE_ROOT=/var/lib/macro-market-memory/state/experience-v1
MARKET_MEMORY_EXPERIENCE_INSTALLATION="$MARKET_MEMORY_EXPERIENCE_ROOT/registration_installation.json"
MARKET_MEMORY_EXPERIENCE_TERMINAL="$MARKET_MEMORY_EXPERIENCE_ROOT/TERMINAL.json"
MARKET_MEMORY_EXPERIENCE_PYTHON=/opt/macro-api/.venv/bin/python
RECIPROCAL_TIMERS_PAUSED=0
OPTIONS_DEFER_REARM_FOR_SELF_UPDATE=0

# BEGIN W1B5_UNIT_STOP_HELPERS
unit_absent_from_manager_and_disk() {
	local unit=$1 installed=$2 load_state
	[ ! -e "$installed" ] && [ ! -L "$installed" ] || return 1
	load_state=$(systemctl show -p LoadState --value "$unit") || return 1
	[ "$load_state" = not-found ]
}

stop_unit_and_verify_inactive() {
	local unit=$1 installed=$2 active_state main_pid control_pid
	if ! systemctl stop "$unit" >/dev/null 2>&1; then
		unit_absent_from_manager_and_disk "$unit" "$installed" || return 1
		return 0
	fi
	active_state=$(systemctl show -p ActiveState --value "$unit") || return 1
	main_pid=$(systemctl show -p MainPID --value "$unit") || return 1
	control_pid=$(systemctl show -p ControlPID --value "$unit") || return 1
	case "$active_state" in
		inactive|failed) ;;
		*) return 1 ;;
	esac
	case "$unit" in
		*.timer)
			# Timers have no execution process. systemd therefore reports these
			# service-only properties as empty on the production release.
			case "$main_pid" in ""|0) ;; *) return 1 ;; esac
			case "$control_pid" in ""|0) ;; *) return 1 ;; esac
			;;
		*.service)
			[ "$main_pid" = 0 ] && [ "$control_pid" = 0 ]
			;;
		*) return 1 ;;
	esac
}
# END W1B5_UNIT_STOP_HELPERS


# BEGIN LIVE_SOURCE_TRANSACTION
LIVE_SOURCE_UNITS=(
	macro-live-fast.service macro-live-fast.timer
	macro-live-snapshot.service macro-live-snapshot.timer
	macro-live-bars.service macro-live-bars.timer
)
LIVE_SOURCE_ACTIVE=0
LIVE_SOURCE_REPLAY=0
LIVE_SOURCE_ENROLLMENT=""

live_source_units_ready() {
	local directory=$1 unit lane
	for unit in "${LIVE_SOURCE_UNITS[@]}"; do
		mm_loaded_unit_ready "$directory/$unit" "/etc/systemd/system/$unit" "$unit" || return 1
		case "$unit" in
			*.service)
				lane=${unit#macro-live-}; lane=${lane%.service}
				grep -Fxq "ExecStart=/usr/local/bin/macro-update --live-lane $lane" "$directory/$unit" || return 1
				;;
		esac
	done
}

live_source_begin() {
	local phase unit directory lock_path
	local -a sources
	if [ "$LIVE_SOURCE_PENDING" -eq 0 ]; then
		LIVE_SOURCE_ENROLLMENT=$(live_source_control enrollment)
		if [ "$LIVE_SOURCE_PURPOSE" = update ] && [ "$OLD" = "$NEW" ]; then
			if [ "$LIVE_SOURCE_ENROLLMENT" = absent ] || live_source_units_ready "$APP_DIR/app/deploy"; then
				live_source_control retire-entry "${LIVE_SOURCE_CAPSULE##*/}"
				return 0
			fi
		fi
		LIVE_SOURCE_CAPSULE=$(live_source_control prepare "$OLD" "$NEW" "${LIVE_SOURCE_CAPSULE##*/}" "$LIVE_SOURCE_PURPOSE")
		LIVE_SOURCE_PENDING=1
	else
		LIVE_SOURCE_ENROLLMENT=$(live_source_control get enrollment)
	fi
	phase=$(live_source_control get phase)
	directory="$LIVE_SOURCE_CAPSULE/units"
	lock_path=$(live_source_control lock-path)
	# Open without truncate/unlink; the embedded owner checks this very fd's inode.
	exec 8<>"$lock_path"
	live_source_control lock
	live_source_control verify-target
	case "$phase" in
		SOURCE_READY|RESTORING)
			if [ "$LIVE_SOURCE_ENROLLMENT" = present ] || [ "$LIVE_SOURCE_PURPOSE" = setup ]; then
				live_source_units_ready "$directory"
			fi
			live_source_control verify-ready
			live_source_control unlock
			exec 8>&-
			# No reset, mirrors or new fetch on this branch. Restoration may hold
			# the journal, which also prevents the later self-install.
			if [ "$LIVE_SOURCE_PURPOSE" = update ]; then
				live_source_control restore
				LIVE_SOURCE_PENDING=0
			fi
			return 0
			;;
	esac
	if [ "$LIVE_SOURCE_ENROLLMENT" = present ] || [ "$LIVE_SOURCE_PURPOSE" = setup ]; then
		sources=()
		for unit in "${LIVE_SOURCE_UNITS[@]}"; do
			mm_unit_repair_inputs_safe "$directory/$unit" "/etc/systemd/system/$unit"
			sources+=("$directory/$unit")
		done
		systemd-analyze verify "${sources[@]}"
		# Admit guarded manager definitions before any reset. A late start then
		# waits on fd8; an older unwrapped process is stopped and drained below.
		for unit in "${LIVE_SOURCE_UNITS[@]}"; do
			install -m 0644 "$directory/$unit" "/etc/systemd/system/$unit"
		done
		systemctl daemon-reload
		live_source_control fsync-units
		live_source_units_ready "$directory"
		for unit in macro-live-fast.timer macro-live-snapshot.timer macro-live-bars.timer; do
			stop_unit_and_verify_inactive "$unit" "/etc/systemd/system/$unit"
		done
		for unit in macro-live-fast.service macro-live-snapshot.service macro-live-bars.service; do
			stop_unit_and_verify_inactive "$unit" "/etc/systemd/system/$unit"
			live_source_control cgroup "$unit"
		done
	fi
	# Re-do guard admission and draining on every incomplete-source recovery,
	# including a new boot. A phase value alone is not a current process proof.
	live_source_control guards
	LIVE_SOURCE_ACTIVE=1
	LIVE_SOURCE_REPLAY=1
}

live_source_finish() {
	[ "$LIVE_SOURCE_ACTIVE" -eq 1 ] || return 0
	if [ "$LIVE_SOURCE_ENROLLMENT" = present ]; then
		live_source_units_ready "$LIVE_SOURCE_CAPSULE/units"
	fi
	live_source_control ready
	live_source_control unlock
	exec 8>&-
	# Restore immediately after the coherent source is available, before the
	# ordinary updater's unrelated package/network/reconciliation work.
	live_source_control restore
	LIVE_SOURCE_PENDING=0
	LIVE_SOURCE_ACTIVE=0
}
# END LIVE_SOURCE_TRANSACTION

# Setup borrows the same captured helpers and source transaction. Its child
# stages keep fd9 for the whole attempt and never invoke an ordinary update.
if [ "$LIVE_SOURCE_PURPOSE" = setup ]; then
    if [ -n "$LIVE_SETUP_CONTROL" ]; then
        case "$LIVE_SETUP_CONTROL" in
            bind-environment|ready)
                lock_path=$(live_source_control lock-path)
                exec 8<>"$lock_path"
                live_source_control lock
                live_source_control verify-target
                live_source_units_ready "$LIVE_SOURCE_CAPSULE/units"
                if [ "$LIVE_SETUP_CONTROL" = ready ]; then
                    for unit in macro-live-prophet.service macro-live-prophet.timer \
                        macro-live-closepass.service macro-live-closepass.timer \
                        macro-live-breadth.service macro-live-breadth.timer; do
                        mm_loaded_unit_ready "$LIVE_SOURCE_CAPSULE/setup/units/$unit" "/etc/systemd/system/$unit" "$unit"
                    done
                fi
                live_source_control setup-action "$LIVE_SETUP_CONTROL"
                live_source_control unlock
                exec 8>&-
                ;;
            smoke|arm|finish)
                live_source_units_ready "$LIVE_SOURCE_CAPSULE/units"
                for unit in macro-live-prophet.service macro-live-prophet.timer \
                    macro-live-closepass.service macro-live-closepass.timer \
                    macro-live-breadth.service macro-live-breadth.timer; do
                    mm_loaded_unit_ready "$LIVE_SOURCE_CAPSULE/setup/units/$unit" "/etc/systemd/system/$unit" "$unit"
                done
                live_source_control setup-action "$LIVE_SETUP_CONTROL"
                ;;
            *) live_source_control setup-action "$LIVE_SETUP_CONTROL" ;;
        esac
        exit $?
    fi
    if [ "$LIVE_SOURCE_PENDING" -eq 1 ]; then
        OLD=$(live_source_control get old)
    else
        OLD=$(live_source_control entry-old "${LIVE_SOURCE_CAPSULE##*/}")
    fi
    NEW=$OLD
    live_source_begin
    if [ "$LIVE_SOURCE_ACTIVE" -eq 1 ]; then
        live_source_control mutating
        live_source_control unlock
        exec 8>&-
    fi
    bash "$LIVE_SOURCE_CAPSULE/setup/live-setup.sh" --source-attempt "${LIVE_SOURCE_CAPSULE##*/}"
    exit $?
fi


# BEGIN W1B5_RECIPROCAL_STOP
stop_reciprocal_market_memory_writers() {
	local profile service timer
	rm -f "$OPTIONS_RECIPROCAL_FENCE_MARKER"
	for profile in source source-spy-rest context identity breadth technicals technicals-v2 experience experience-v2 production-records options-context-audit; do
		service="macro-market-memory-$profile.service"
		timer="macro-market-memory-$profile.timer"
		if ! stop_unit_and_verify_inactive \
			"$timer" "/etc/systemd/system/$timer"; then
			echo "macro-update: FAILED to pause reciprocal timer $timer" >&2
			return 1
		fi
		if ! stop_unit_and_verify_inactive \
			"$service" "/etc/systemd/system/$service"; then
			echo "macro-update: FAILED to stop reciprocal writer $service" >&2
			return 1
		fi
	done
	RECIPROCAL_TIMERS_PAUSED=1
}
# END W1B5_RECIPROCAL_STOP

reciprocal_market_memory_units_ready() {
	local profile
	for profile in source context identity breadth technicals experience production-records; do
		mm_loaded_unit_ready \
			"$APP_DIR/app/deploy/macro-market-memory-$profile.service" \
			"/etc/systemd/system/macro-market-memory-$profile.service" \
			"macro-market-memory-$profile.service" || return 1
		mm_loaded_unit_ready \
			"$APP_DIR/app/deploy/macro-market-memory-$profile.timer" \
			"/etc/systemd/system/macro-market-memory-$profile.timer" \
			"macro-market-memory-$profile.timer" || return 1
	done
}

unit_repair_inputs_safe() {
	local source unit
	for source in "$@"; do
		unit=$(basename "$source")
		mm_unit_repair_inputs_safe "$source" "/etc/systemd/system/$unit" || return 1
	done
}

# BEGIN W2C_DEPLOY_HELPERS
w2c_start_owner_chain() {
	local owner
	for owner in source context technicals; do
		if ! systemctl start "macro-market-memory-$owner.service"; then
			echo "macro-update: W2C owner replay failed: $owner" >&2
			return 1
		fi
	done
}

w2c_verify_installation() {
	"${MARKET_MEMORY_EXPERIENCE_PYTHON:-/opt/macro-api/.venv/bin/python}" \
		"${APP_DIR:-/opt/macro}/scripts/accrue_market_memory_spy_experience.py" \
		--repository-root "${APP_DIR:-/opt/macro}" \
		--experience-root "$MARKET_MEMORY_EXPERIENCE_ROOT" \
		--verify-installation >/dev/null
}

w2c_terminal_ledger_state() {
	local status
	if "${MARKET_MEMORY_EXPERIENCE_PYTHON:-/opt/macro-api/.venv/bin/python}" \
		"${APP_DIR:-/opt/macro}/scripts/accrue_market_memory_spy_experience.py" \
		--repository-root "${APP_DIR:-/opt/macro}" \
		--experience-root "$MARKET_MEMORY_EXPERIENCE_ROOT" \
		--verify-terminal >/dev/null; then
		return 0
	else
		status=$?
	fi
	[ "$status" -eq 3 ] && return 3
	echo "macro-update: W2C terminal ledger authentication failed" >&2
	return 2
}

w2c_reconcile_timer() {
	local terminal_state=0
	w2c_terminal_ledger_state || terminal_state=$?
	case "$terminal_state" in
		0)
			systemctl disable --now macro-market-memory-experience.timer || return 1
			if systemctl is-enabled macro-market-memory-experience.timer >/dev/null 2>&1 || \
			   systemctl is-active macro-market-memory-experience.timer >/dev/null 2>&1; then
				echo "macro-update: W2C terminal timer disarm verification failed" >&2
				return 1
			fi
			;;
		3)
			if ! w2c_verify_installation; then
				echo "macro-update: W2C installation authentication failed" >&2
				return 1
			fi
			if systemctl is-enabled macro-market-memory-experience.timer >/dev/null 2>&1 && \
			   systemctl is-active macro-market-memory-experience.timer >/dev/null 2>&1; then
				return 0
			fi
			if [ "${W2C_OWNER_REPLAY_READY:-0}" -ne 1 ]; then
				echo "macro-update: refusing to arm W2C before synchronous owner replay" >&2
				return 1
			fi
			systemctl enable --now macro-market-memory-experience.timer || return 1
			systemctl is-enabled macro-market-memory-experience.timer >/dev/null 2>&1 || return 1
			systemctl is-active macro-market-memory-experience.timer >/dev/null 2>&1 || return 1
			;;
		*)
			echo "macro-update: W2C terminal state is invalid" >&2
			return 1
			;;
	esac
}
# END W2C_DEPLOY_HELPERS

# BEGIN W1B5_TIMER_DISARM
disarm_options_timer() {
	local unit_file_state
	if [ "$OPTIONS_TIMER_DISARMED" -eq 1 ]; then
		return 0
	fi
	if ! systemctl disable --now macro-market-memory-options.timer >/dev/null 2>&1; then
		# Removing the marker is the secondary fail-closed fence: even if an
		# already-loaded timer could not be stopped, its service condition fails.
		rm -f "$OPTIONS_API_FENCE_MARKER"
		if ! unit_absent_from_manager_and_disk \
			macro-market-memory-options.timer \
			/etc/systemd/system/macro-market-memory-options.timer; then
			echo "macro-update: FAILED to disarm option-OI timer" >&2
			return 1
		fi
	fi
	if [ -e /etc/systemd/system/macro-market-memory-options.timer ]; then
		unit_file_state=$(systemctl show -p UnitFileState --value \
			macro-market-memory-options.timer) || return 1
		case "$unit_file_state" in
			disabled|masked) ;;
			*) echo "macro-update: option-OI timer remains enabled" >&2; return 1 ;;
		esac
	fi
	if ! stop_unit_and_verify_inactive \
		macro-market-memory-options.timer \
		/etc/systemd/system/macro-market-memory-options.timer; then
		rm -f "$OPTIONS_API_FENCE_MARKER"
		echo "macro-update: FAILED to stop option-OI timer" >&2
		return 1
	fi
	if ! stop_unit_and_verify_inactive \
		macro-market-memory-options.service \
		/etc/systemd/system/macro-market-memory-options.service; then
		rm -f "$OPTIONS_API_FENCE_MARKER"
		echo "macro-update: FAILED to stop active option-OI writer" >&2
		return 1
	fi
	OPTIONS_TIMER_DISARMED=1
}
# END W1B5_TIMER_DISARM

# ConditionPathExists follows symlinks. Remove any forged/stale marker before
# fetch/reset/runtime mutation so an enabled timer cannot pass the condition in
# the window before the later full boundary reconciliation.
if { [ -e "$OPTIONS_API_FENCE_MARKER" ] || [ -L "$OPTIONS_API_FENCE_MARKER" ]; } && \
   ! mm_api_fence_marker_ready; then
	disarm_options_timer
	rm -f "$OPTIONS_API_FENCE_MARKER" "$OPTIONS_RECIPROCAL_FENCE_MARKER"
fi
if { [ -e "$OPTIONS_RECIPROCAL_FENCE_MARKER" ] || \
     [ -L "$OPTIONS_RECIPROCAL_FENCE_MARKER" ]; } && \
   ! mm_reciprocal_fence_marker_ready; then
	disarm_options_timer
	rm -f "$OPTIONS_API_FENCE_MARKER" "$OPTIONS_RECIPROCAL_FENCE_MARKER"
fi

# A prior tick may have reset the repo and crashed before self-installing this
# updater. In that version-skew state the running predecessor may reconcile but
# must not mint markers or re-arm either boundary; only a later invocation that
# began byte-identical to the reviewed repo updater may do so.
if ! cmp -s "$APP_DIR/app/deploy/update.sh" /usr/local/bin/macro-update; then
	OPTIONS_DEFER_REARM_FOR_SELF_UPDATE=1
	disarm_options_timer
	stop_reciprocal_market_memory_writers
fi

# BEGIN MACRO_UPDATE_FREE_SPACE_GUARD
# Root-disk floor before the pull writes anything (2026-10-19 and 2026-11-01
# refills). Every pull lands a new pack in $APP_DIR/.git/objects on the root
# filesystem; on a full disk the next one fails half-way and journald, Caddy
# and the API start failing with it. Below the floor, or when free space or the
# floor cannot be read as a number, this tick skips the fetch: it says why on
# stderr and in the system log, leaves a marker that names the shortfall, and
# still runs the reconciliation below against the current checkout (so a timer
# disarmed above is re-armed, as on any no-change tick), then exits 1. A refused
# pull also holds back deploys of fixes, by design: recovering space is a
# manual step (app/deploy/README.md, "Git store maintenance"), never something
# this updater improvises. The 7 GiB floor is set above what the nightly repack
# needed on a normal night (about 4 GiB measured 2026-11-01), so on most nights
# the repack can still run below a refused pull; when it cannot, it refuses and
# says so, and the recovery stays manual.
MIN_FREE_KIB="${MACRO_UPDATE_MIN_FREE_KIB:-7340032}"
DISK_REFUSED_MARKER="${MACRO_UPDATE_DISK_MARKER:-/run/macro-update-disk-refused}"
DISK_REFUSED=0
DISK_REFUSAL=""
ROOT_FREE_KIB=$(df --output=avail -k "$APP_DIR/.git/objects" 2>/dev/null | tail -n 1 | tr -d ' ') || ROOT_FREE_KIB=""
if ! [[ $ROOT_FREE_KIB =~ ^[0-9]+$ ]] || ! [[ $MIN_FREE_KIB =~ ^[0-9]+$ ]] || [ "$ROOT_FREE_KIB" -lt "$MIN_FREE_KIB" ]; then
	DISK_REFUSED=1
	DISK_REFUSAL="macro-update: REFUSED pull: ${ROOT_FREE_KIB:-unreadable} KiB free on $APP_DIR/.git/objects, floor ${MIN_FREE_KIB} KiB; nothing pulled; this tick reconciles the current checkout and exits 1 (recovery: app/deploy/README.md, 'Git store maintenance')"
	echo "$DISK_REFUSAL" >&2
	logger -p user.err -t macro-update "$DISK_REFUSAL" 2>/dev/null || true
	echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $DISK_REFUSAL" > "$DISK_REFUSED_MARKER" 2>/dev/null || true
else
	rm -f "$DISK_REFUSED_MARKER"
fi
# END MACRO_UPDATE_FREE_SPACE_GUARD

# Do not add --depth here: depth-one fetches sever the new tip from previously
# published revisions, breaking the native accepts_revision ancestry check even
# when both commit objects remain present. Ordinary fetch preserves connectivity
# for later updates. Existing shallow boundaries require a separate repair;
# this updater never deepens or rewrites them. A fetch failure still aborts
# under strict mode before OLD/NEW and reset. A disk-refused tick skips the
# fetch and pins NEW to HEAD without reading FETCH_HEAD: a fetch that failed
# part-way (as on a full disk) truncates FETCH_HEAD to empty, and reading it
# would abort the tick here before the reconciliation below. From here on a
# refused tick is a no-change tick: nothing below resets or pulls.
# BEGIN MACRO_UPDATE_PULL_SELECT
if [ "$LIVE_SOURCE_PENDING" -eq 1 ]; then
	# Recovery retains the original target and original changed-path meaning.
	# No network or FETCH_HEAD may redirect an unfinished source transaction.
	OLD=$(live_source_control get old)
	NEW=$(live_source_control get new)
else
	if [ "$DISK_REFUSED" -eq 0 ]; then
		git -C "$APP_DIR" fetch -q origin main
	fi
	OLD=$(git -C "$APP_DIR" rev-parse HEAD)
	if [ "$DISK_REFUSED" -eq 1 ]; then
		NEW=$OLD
	else
		NEW=$(git -C "$APP_DIR" rev-parse FETCH_HEAD)
	fi
fi
# END MACRO_UPDATE_PULL_SELECT
CHANGED=""
REPO_UPDATED=0
RECONCILED=0
if [ "$LIVE_SOURCE_PENDING" -eq 1 ]; then
	CHANGED=$(live_source_control get changed)
elif [ "$OLD" != "$NEW" ]; then
	CHANGED=$(git -C "$APP_DIR" diff --name-only "$OLD" "$NEW")
fi
live_source_begin

if [ "$OLD" != "$NEW" ]; then
	# BEGIN W1B5_PRE_RESET_GUARD
	# Git rewrites tracked files in place. Stop the credentialed writer before
	# replacing any byte in its exact runtime/source-contract closure.
	if grep -qE "$OPTIONS_RUNTIME_CLOSURE_REGEX" <<<"$CHANGED"; then
		disarm_options_timer
		rm -f "$OPTIONS_API_FENCE_MARKER"
	fi
	if grep -qE '^app/deploy/(update|market-memory-options-(unit-boundary|runtime-fence))\.sh$' \
		<<<"$CHANGED"; then
		# Bash keeps executing the predecessor inode after self-install. It may
		# reconcile, but only the next tick's reviewed inode may re-arm the lane.
		OPTIONS_DEFER_REARM_FOR_SELF_UPDATE=1
	fi
	if grep -qE "$OPTIONS_RECIPROCAL_CLOSURE_REGEX" <<<"$CHANGED"; then
		stop_reciprocal_market_memory_writers
	fi
	# END W1B5_PRE_RESET_GUARD
	if [ "$LIVE_SOURCE_REPLAY" -eq 1 ]; then
	live_source_control mutating
	git -C "$APP_DIR" reset --hard -q "$NEW"
	REPO_UPDATED=1

	# BEGIN MOVERS_BEFORE_MIRROR_GUARD
	# A returning older publisher may leave the plain pair stale if its soft
	# post-rebase sync fails. Once either Caddy generation trusts this route,
	# refuse to mirror that stale body over the last good served stub.
	if grep -qE '^[[:space:]]*@movers_seo_redirect[[:space:]]*\{' "$APP_DIR/app/deploy/Caddyfile" ||
	   grep -qE '^[[:space:]]*@movers_seo_redirect[[:space:]]*\{' /etc/caddy/Caddyfile; then
		for movers_page in "$APP_DIR/templates/movers.html" "$APP_DIR/site/movers.html"; do
			if [ -L "$movers_page" ] || [ ! -f "$movers_page" ] || [ ! -s "$movers_page" ]; then
				echo "macro-update: refusing site mirror — Movers page is symlink, missing or empty: $movers_page" >&2
				exit 1
			fi
		done
		if ! grep -q 'data-mmx-movers-redirect="1"' "$APP_DIR/templates/movers.html" ||
		   ! cmp -s "$APP_DIR/templates/movers.html" "$APP_DIR/site/movers.html"; then
			echo "macro-update: refusing site mirror — canonical Movers marker/pair is stale" >&2
			exit 1
		fi
	fi
	# END MOVERS_BEFORE_MIRROR_GUARD

	# Publish the served tree ATOMICALLY. `git reset --hard` above rewrites
	# changed files IN PLACE, so Caddy serves a separate rsync target whose
	# per-file temp-write + rename keeps every visible file whole.
	mkdir -p "$APP_DIR/site.served"
	reconcile_ohlc_delivery
	# Exclusion also protects a refused/foreign OHLC path from --delete.
	rsync -a --delete --min-size=1 --exclude=/ohlc "$APP_DIR/site/" "$APP_DIR/site.served/"
	live_source_control mirror site complete

	# Press properties (D14 W1.5) — same atomic-publish contract as site.served,
	# and for the same reason: `git reset --hard` above rewrites changed files IN
	# PLACE, so Caddy must serve a separate rsync target whose per-file temp-write
	# + rename keeps every visible file whole. --min-size=1 refuses to publish a
	# 0-byte file over a good one (the 2026-07-03 white-page incident).
	#
	# The [ -d ] guards are load-bearing, not defensive noise: these trees are
	# built by scripts/build_press_properties.py and may legitimately not exist
	# yet on a box that pulled main before they landed. Without the guard, rsync
	# of a missing source under `set -e` aborts the whole update run — and this
	# script is what keeps the MAIN site tracking main.
	#
	# The Caddy vhosts that serve these roots stay COMMENTED until the cutover
	# (see the marked block in app/deploy/Caddyfile), so syncing them early is
	# free: the files land, nothing serves them, and cutover day is a config flip
	# rather than a first-ever data copy.
	if [ -d "$APP_DIR/properties/news" ]; then
		mkdir -p "$APP_DIR/press_news.served"
		rsync -a --delete --min-size=1 "$APP_DIR/properties/news/" "$APP_DIR/press_news.served/"
		live_source_control mirror news complete
	else
		live_source_control mirror news absent
	fi
	if [ -d "$APP_DIR/properties/research" ]; then
		mkdir -p "$APP_DIR/press_research.served"
		rsync -a --delete --min-size=1 "$APP_DIR/properties/research/" "$APP_DIR/press_research.served/"
		live_source_control mirror research complete
	else
		live_source_control mirror research absent
	fi
	fi
	REPO_UPDATED=1
fi
live_source_finish

# Reconcile artifact selection even when the repository did not change.
# A successful later check does not erase an earlier refusal in this run.
reconcile_ohlc_delivery

# Runtime-only company-logo configuration. The committed file is deliberately
# empty; the browser-safe Logo.dev publishable token lives in the root-readable
# VPS env and is materialized only into the served tree after every rsync. The
# server-side secret key is neither required nor accepted here.
LOGO_DEV_TOKEN=""
if [ -r /etc/macro-api.env ]; then
	LOGO_DEV_TOKEN=$(sed -n 's/^LOGO_DEV_PUBLISHABLE_KEY=//p' /etc/macro-api.env | tail -n 1)
fi
case "$LOGO_DEV_TOKEN" in
	pk_*) ;;
	*) LOGO_DEV_TOKEN="" ;;
esac
case "$LOGO_DEV_TOKEN" in
	*[!A-Za-z0-9_-]*) LOGO_DEV_TOKEN="" ;;
esac
mkdir -p "$APP_DIR/site.served"
LOGO_CONFIG_TMP=$(mktemp "$APP_DIR/site.served/.logo_config.XXXXXX")
printf 'window.MMX_LOGO_DEV_TOKEN = window.MMX_LOGO_DEV_TOKEN || "%s";\n' "$LOGO_DEV_TOKEN" > "$LOGO_CONFIG_TMP"
chmod 0644 "$LOGO_CONFIG_TMP"
if ! cmp -s "$LOGO_CONFIG_TMP" "$APP_DIR/site.served/logo_config.js"; then
	mv -f "$LOGO_CONFIG_TMP" "$APP_DIR/site.served/logo_config.js"
else
	rm -f "$LOGO_CONFIG_TMP"
fi

# Do not exit just because Git is current. A prior run may have self-updated
# this script while continuing to execute its old inode, or an operator may
# have drifted an installed unit/config. Reconciliation below is deliberately
# idempotent and must also run on a repository no-op.

# Self-update: install captured, syntax-checked source with atomic rename and directory fsync.
# Any unresolved source journal (including held restoration) refuses replacement.
# The running Bash descriptor retains its predecessor inode for the rest of this tick.
if ! cmp -s "$APP_DIR/app/deploy/update.sh" /usr/local/bin/macro-update; then
	live_source_control replace-owner "$NEW"
	RECONCILED=1
	echo "macro-update: self-updated from captured source"
fi

# Caddyfile: reinstall + validate + reload ONLY when it actually changed (a bad
# config can never take the site down — reload is gated on `caddy validate`).
if ! cmp -s "$APP_DIR/app/deploy/Caddyfile" /etc/caddy/Caddyfile || [ -n "${CADDY_SOURCE_BASELINE:-}" ] || { { [ -e /var/lib/macro-caddy-publication ] || [ -L /var/lib/macro-caddy-publication ]; } && python3 "$APP_DIR/app/deploy/reconcile-caddy-autosave.py" --pending-check; }; then
	# BEGIN MOVERS_SEO_REDIRECT_CADDY_GUARD
	# Fail-closed ordering guard for the staged Movers SEO redirect. The
	# @movers_seo_redirect matcher is a FUTURE repo-side construct (no such
	# named matcher exists in the committed Caddyfile today), so this stays
	# inert for every other Caddy change and they keep the exact existing
	# validate/install/reload behavior below.
	#
	# The hazard this closes: `git reset --hard` can succeed and the rsync that
	# follows it can fail, leaving site.served/movers.html stale while
	# OLD == NEW — the next tick then takes the cheap no-op repo path, yet THIS
	# reconciliation still runs, because it is gated on the candidate-vs-
	# installed Caddy diff, not on git state. Without this guard that tick
	# would validate, install and reload a trusted SEO exception over the stale
	# body. So when the candidate carries the named matcher, require the
	# coherent Movers page first: all three copies present, nonempty and
	# byte-identical, with the redirect marker in the canonical source.
	# Anything missing, mismatched or stale refuses the update BEFORE validate,
	# install or reload — this guard only reads and refuses, with no rsync,
	# repair, retry, publisher or permission side effect. It cannot
	# retroactively protect a first run that still executes the predecessor
	# inode after a self-update, and it does not make the approved two-stage
	# rollout atomic; it only keeps a bad Caddy install from ever happening.
	if grep -qE '^[[:space:]]*@movers_seo_redirect[[:space:]]*\{' "$APP_DIR/app/deploy/Caddyfile"; then
		for movers_page in \
			"$APP_DIR/templates/movers.html" \
			"$APP_DIR/site/movers.html" \
			"$APP_DIR/site.served/movers.html"; do
			if [ -L "$movers_page" ] || [ ! -f "$movers_page" ] || [ ! -s "$movers_page" ]; then
				echo "macro-update: refusing Caddyfile update — @movers_seo_redirect needs $movers_page (symlink, missing or empty)" >&2
				exit 1
			fi
		done
		if ! grep -q 'data-mmx-movers-redirect="1"' "$APP_DIR/templates/movers.html"; then
			echo "macro-update: refusing Caddyfile update — templates/movers.html is stale (missing data-mmx-movers-redirect marker)" >&2
			exit 1
		fi
		if ! cmp -s "$APP_DIR/templates/movers.html" "$APP_DIR/site/movers.html"; then
			echo "macro-update: refusing Caddyfile update — templates/movers.html and site/movers.html disagree" >&2
			exit 1
		fi
		if ! cmp -s "$APP_DIR/site/movers.html" "$APP_DIR/site.served/movers.html"; then
			echo "macro-update: refusing Caddyfile update — site/movers.html and site.served/movers.html disagree (stale served body)" >&2
			exit 1
		fi
	fi
	# END MOVERS_SEO_REDIRECT_CADDY_GUARD
	# API-managed Caddy has a complete autosave configuration containing other
	# publishers' routes. Reconcile only qualified Macro source changes through
	# its native version fence; never reload a source-only or old autosave file.
	if systemctl show caddy -p ExecReload --value | grep -Fq -- '--config /var/lib/caddy/.config/caddy/autosave.json'; then
		if ! cmp -s "/proc/$$/fd/255" "$APP_DIR/app/deploy/update.sh"; then
			echo "macro-update: refusing Caddy adoption from a predecessor updater inode" >&2
			exit 1
		fi
		python3 "$APP_DIR/app/deploy/reconcile-caddy-autosave.py" "${CADDY_RECONCILE_ARGS[@]}"
		RECONCILED=1
	elif [ -n "${CADDY_SOURCE_BASELINE:-}" ] || { { [ -e /var/lib/macro-caddy-publication ] || [ -L /var/lib/macro-caddy-publication ]; } && python3 "$APP_DIR/app/deploy/reconcile-caddy-autosave.py" --pending-check; }; then
		echo "macro-update: pending/attended Caddy adoption requires the qualified autosave mode" >&2
		exit 1
	elif caddy validate --config "$APP_DIR/app/deploy/Caddyfile" --adapter caddyfile; then
		install -m 0644 "$APP_DIR/app/deploy/Caddyfile" /etc/caddy/Caddyfile
		systemctl reload caddy 2>/dev/null || systemctl restart caddy
		RECONCILED=1
	else
		echo "macro-update: refusing Caddyfile update — validation failed" >&2
	fi
fi

# BEGIN CONTROL_ROOM_ACTIVE_BUILDS_PUBLISH
# The Control Room projection has no credentials and cannot query GitHub.  The
# existing trusted update lane therefore publishes the canonical three-repo
# advisory document into the installer-owned source directory on every tick.
# This is a best-effort observation only: every pre-commit failure leaves the
# last-good file untouched; a post-commit durability ambiguity is separately
# reported as effect-unknown. Neither outcome may stop Macro deployment or
# authorize execution.
if /usr/bin/python3 "$APP_DIR/scripts/publish_control_room_active_builds.py"; then
	:
else
	CONTROL_ROOM_SOURCE_STATUS=$?
	if [ "$CONTROL_ROOM_SOURCE_STATUS" -eq 3 ]; then
		echo "macro-update: project active-build source publication effect unknown" >&2
	else
		echo "macro-update: project active-build source publication deferred" >&2
	fi
fi
# END CONTROL_ROOM_ACTIVE_BUILDS_PUBLISH

# Codex CLI: keep the provider runtime pinned and self-healing just like the
# reviewed systemd units below. Authentication is durable VPS state under the
# root-only /var/lib/macro-codex* stores and is never copied into git.
if ! bash "$APP_DIR/app/deploy/codex-runtime-setup.sh" --quiet; then
	echo "macro-update: Codex runtime reconciliation failed; Claude/DeepSeek fallbacks remain available" >&2
fi

# macro-api systemd sandbox: keep the installed unit aligned with the reviewed
# repo copy. Validate before installation; a broken unit never replaces the
# running one. The restart decision below includes this path.
# Provision the serving root and the disjoint private writer root before unit
# validation/restart.  Both units use non-optional path mounts, so an absent
# path fails closed instead of widening either side of the trust boundary.
install -d -m 0700 /var/lib/macro-market-memory
install -d -m 0700 /var/lib/macro-market-memory/public
install -d -m 0700 /var/lib/macro-market-memory/public/trusted-v1
install -d -m 0700 /var/lib/macro-market-memory/state
install -d -m 0700 /var/lib/macro-market-memory/state/sources
install -d -m 0700 /var/lib/macro-market-memory/state/context-projection
install -d -m 0700 /var/lib/macro-market-memory/state/context-projection/options-context-receipts
install -d -m 0700 /var/lib/macro-market-memory/state/identity-v1
install -d -m 0700 /var/lib/macro-market-memory/state/breadth-v1
install -d -m 0700 /var/lib/macro-market-memory/state/technicals-v1
install -d -m 0700 /var/lib/macro-market-memory/state/experience-v1
install -d -m 0700 /var/lib/macro-market-memory/state/production-record-options-episode-v1
install -d -m 0700 /var/lib/macro-market-memory/state/sources-spy-rest-v1
install -d -m 0700 /var/lib/macro-market-memory/state/technicals-v2
install -d -m 0700 /var/lib/macro-market-memory/state/experience-v2
# Unit verification needs the static account and empty deny anchors.  The
# service-writable profile and credential file are provisioned only after
# macro-api proves a new deny namespace.
OPTIONS_RECONCILIATION_COMPLETE=0
# BEGIN W1B5_TIMER_EXIT_GUARD
options_fail_closed_on_exit() {
	local status=$?
	trap - EXIT
	if [ "$OPTIONS_RECONCILIATION_COMPLETE" -ne 1 ]; then
		disarm_options_timer || status=1
		if [ "$status" -eq 0 ]; then
			status=1
		fi
	fi
	exit "$status"
}
trap options_fail_closed_on_exit EXIT
# END W1B5_TIMER_EXIT_GUARD
# A W2C owner-replay or attestation refusal freezes ONLY the W2C lane.  Each
# refusal keeps its exact stderr line and still fails the run with status 1,
# but the lane-independent steps after W1B5_TIMER_FINALIZATION (live-plane
# timers, press feeds, ticker news, BioCatalyst, unit reconcile, daemon
# restarts) still run: CHANGED is per-run, so a step skipped here is lost.
# BEGIN W2C_LANE_FREEZE
W2C_LANE_FROZEN=0
W2C_LANE_FROZEN_REASON=
DEPLOY_EXIT_STATUS=0
freeze_w2c_lane() {
	W2C_LANE_FROZEN=1
	DEPLOY_EXIT_STATUS=1
	if [ -z "$W2C_LANE_FROZEN_REASON" ]; then
		W2C_LANE_FROZEN_REASON=$1
	fi
}
# END W2C_LANE_FREEZE

# W1A has no scheduled context writer, so directory provisioning alone cannot
# create its manifest/genesis/HEAD. Reconcile and authenticate that metadata on
# every tick before API unit validation or restart. Any unsafe partial, tampered,
# symlinked, or unwritable store aborts readiness; no capture is fabricated.
if ! /opt/macro-api/.venv/bin/python "$APP_DIR/scripts/initialize_market_memory_w1a.py" \
	--repository-root "$APP_DIR" \
	--store /var/lib/macro-market-memory/public; then
	echo "macro-update: W1A public generation initialization failed; refusing API readiness" >&2
	exit 1
fi

# A healthy no-op updater must not cancel and recreate the nonpersistent daily
# timer.  Validate first; disarm only when identity/anchor repair is required.
if ! bash "$APP_DIR/app/deploy/market-memory-options-prereqs.sh" \
	--check-identity-only >/dev/null 2>&1; then
	disarm_options_timer
	bash "$APP_DIR/app/deploy/market-memory-options-prereqs.sh" --identity-only
fi
OPTIONS_CREDENTIAL_READY=0
API_UNIT_UPDATED=0
API_UNIT_READY=0

# macro-api binds ticker-news state read-only. Provision only the private state
# root here; this does NOT install, enable, or start the writer service.
if [ -L /var/lib/macro-ticker-news ]; then
	echo "macro-update: refusing symlinked ticker-news state root" >&2
	exit 1
fi
install -d -m 0700 /var/lib/macro-ticker-news

# BEGIN COMPANY_INTELLIGENCE_PRIVATE_ROOTS
# Empty directories only: GMI owns publication and current-generation admission.
if ! /opt/macro-api/.venv/bin/python "$APP_DIR/app/deploy/company-intelligence-private-roots.py"; then
  echo "update.sh: private Company Intelligence provisioning failed; refusing API readiness" >&2
  exit 1
fi
# END COMPANY_INTELLIGENCE_PRIVATE_ROOTS

# BEGIN MEDTECH_PRIVATE_ROOTS
# Empty identity/anchors only; dedicated refresh installation and activation stay explicit.
if ! /opt/macro-api/.venv/bin/python "$APP_DIR/app/deploy/medtech-prereqs.py"; then
  echo "update.sh: MedTech provisioning failed; refusing API readiness" >&2
  exit 1
fi
# END MEDTECH_PRIVATE_ROOTS

if ! mm_reviewed_unit_file_ready \
	"$APP_DIR/app/deploy/macro-api.service" \
	/etc/systemd/system/macro-api.service; then
	disarm_options_timer
	rm -f "$OPTIONS_API_FENCE_MARKER"
	mm_unit_repair_inputs_safe \
		"$APP_DIR/app/deploy/macro-api.service" \
		/etc/systemd/system/macro-api.service || {
		echo "macro-update: refusing unsafe macro-api unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "$APP_DIR/app/deploy/macro-api.service"; then
		install -m 0644 "$APP_DIR/app/deploy/macro-api.service" /etc/systemd/system/macro-api.service
		systemctl daemon-reload
		API_UNIT_UPDATED=1
		RECONCILED=1
		echo "macro-update: macro-api systemd sandbox updated"
	else
		echo "macro-update: refusing macro-api unit update — systemd-analyze verify failed" >&2
	fi
fi
# Production historically supplied the optional Ollama endpoint through one
# hand-installed drop-in. Migrate only after the exact reviewed macro-api
# fragment containing that same EnvironmentFile line is installed. Unknown
# overrides or a failed canonical install leave the working legacy file intact.
if [ -e "$MM_LEGACY_API_DROPIN_DIR" ] || [ -L "$MM_LEGACY_API_DROPIN_DIR" ]; then
	disarm_options_timer
	stop_reciprocal_market_memory_writers
	rm -f "$OPTIONS_API_FENCE_MARKER"
	if ! mm_remove_exact_legacy_api_ollama_dropin \
		"$APP_DIR/app/deploy/macro-api.service" \
		/etc/systemd/system/macro-api.service; then
		echo "macro-update: refusing unsafe legacy macro-api drop-in migration" >&2
		exit 1
	fi
	systemctl daemon-reload
	RECONCILED=1
	echo "macro-update: migrated reviewed legacy macro-api Ollama drop-in"
fi
if mm_reviewed_unit_file_ready \
	"$APP_DIR/app/deploy/macro-api.service" \
	/etc/systemd/system/macro-api.service && \
   ! mm_loaded_unit_ready \
	"$APP_DIR/app/deploy/macro-api.service" \
	/etc/systemd/system/macro-api.service macro-api.service; then
	disarm_options_timer
	rm -f "$OPTIONS_API_FENCE_MARKER"
	systemctl daemon-reload
fi
if mm_loaded_unit_ready \
	"$APP_DIR/app/deploy/macro-api.service" \
	/etc/systemd/system/macro-api.service macro-api.service; then
	API_UNIT_READY=1
else
	disarm_options_timer
	rm -f "$OPTIONS_API_FENCE_MARKER"
	echo "macro-update: macro-api effective unit boundary is not reviewed/current" >&2
fi

# A /run receipt proves that all six reciprocal Market Memory writers were
# stopped at least once after boot/unit drift and any later starts used the
# exact reviewed, drop-in-free unit fragments. Its absence pauses the writers
# before their legacy reconciliation blocks can install, enable, or start them.
RECIPROCAL_UNITS_READY=0
if reciprocal_market_memory_units_ready; then
	RECIPROCAL_UNITS_READY=1
fi
if ! mm_reciprocal_fence_marker_ready || \
   [ "$RECIPROCAL_UNITS_READY" -ne 1 ]; then
	disarm_options_timer
	stop_reciprocal_market_memory_writers
	# Refresh manager state only after every potentially old-namespace writer
	# is confirmed inactive. Persistent drop-ins remain visible and fail the
	# later exact attestation; this reload repairs only ordinary stale fragments.
	systemctl daemon-reload
fi

# Serving dependencies: reconcile against a content stamp on every cron pass,
# not only the first pull that changed requirements.txt. A transient PyPI error
# therefore retries next tick, and the API never restarts into code whose declared
# dependencies failed to install. api-setup.sh writes the same stamp on provision.
API_DEPS_UPDATED=0
API_DEPS_OK=1
API_REQ_STAMP=/opt/macro-api/.requirements.sha256
API_REQ_HASH=$(sha256sum "$APP_DIR/app/requirements.txt" | cut -d' ' -f1)
API_INSTALLED_REQ_HASH=$(cat "$API_REQ_STAMP" 2>/dev/null || true)
if [ "$API_REQ_HASH" != "$API_INSTALLED_REQ_HASH" ]; then
	# The option writer shares this interpreter. Never let its scheduled
	# oneshot overlap a partially-mutated environment.
	disarm_options_timer
	stop_reciprocal_market_memory_writers
	rm -f "$OPTIONS_API_FENCE_MARKER"
	if [ -x /opt/macro-api/.venv/bin/pip ] \
		&& /opt/macro-api/.venv/bin/pip install -q -r "$APP_DIR/app/requirements.txt"; then
		API_REQ_TMP=$(mktemp /opt/macro-api/.requirements.XXXXXX)
		printf '%s\n' "$API_REQ_HASH" > "$API_REQ_TMP"
		chmod 0644 "$API_REQ_TMP"
		mv -f "$API_REQ_TMP" "$API_REQ_STAMP"
		API_DEPS_UPDATED=1
		RECONCILED=1
		echo "macro-update: macro-api dependencies reconciled"
	else
		API_DEPS_OK=0
		echo "macro-update: macro-api dependency reconciliation FAILED; keeping the running API" >&2
	fi
fi

# W1B.0 trusted-source writer: credential-free, network-dark, and private. It
# is safe to install and arm automatically because its only input is the exact
# committed CPIAUCSL collector artifact and its only writable path is the
# root-only source store above. The engine intake validates the hardened
# manifest, exact bytes, and append-only generation before advancing HEAD.
MARKET_MEMORY_SOURCE_UNIT_UPDATED=0
MARKET_MEMORY_SOURCE_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-source.service"
	"$APP_DIR/app/deploy/macro-market-memory-source.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_SOURCE_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-source.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_SOURCE_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-source.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_SOURCE_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe source unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_SOURCE_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_SOURCE_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_SOURCE_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_SOURCE_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-source.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory trusted-source units updated"
		fi
	else
		echo "macro-update: refusing Market Memory source unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-source.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-source.timer could not be enabled" >&2
fi

# Run immediately when the reviewed writer, engine contract, or exact CPI bytes
# advance. A failure is visible in journald and retryable by the hourly timer;
# it must not interrupt site/API deployment or fall back to an older artifact.
MARKET_MEMORY_SOURCE_RUN_NEEDED=0
if [ "$MARKET_MEMORY_SOURCE_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/ingest_market_memory_sources\.py|engine/neuralweb/market_memory_sources\.py|contracts/market_memory/.*source.*\.schema\.json|data/fred_vintage/release_targets/(manifest\.json|CPIAUCSL_all_vintages\.parquet))$'; then
	MARKET_MEMORY_SOURCE_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_SOURCE_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Market Memory source intake until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Market Memory source intake — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-source.service; then
		echo "macro-update: Market Memory source intake failed closed; hourly timer will retry" >&2
	fi
fi

# W2C M0D v2 — SPY REST sealed daily-bar source unit.
# Credentialed, network-allowed, fires at 04:00Z.
MARKET_MEMORY_SOURCE_SPY_REST_UNIT_UPDATED=0
MARKET_MEMORY_SOURCE_SPY_REST_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-source-spy-rest.service"
	"$APP_DIR/app/deploy/macro-market-memory-source-spy-rest.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_SOURCE_SPY_REST_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-source-spy-rest.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_SOURCE_SPY_REST_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-source-spy-rest.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_SOURCE_SPY_REST_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe source-spy-rest unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_SOURCE_SPY_REST_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_SOURCE_SPY_REST_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_SOURCE_SPY_REST_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_SOURCE_SPY_REST_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-source-spy-rest.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory SPY REST source units updated"
		fi
	else
		echo "macro-update: refusing Market Memory source-spy-rest unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-source-spy-rest.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-source-spy-rest.timer could not be enabled" >&2
fi
if bash "$APP_DIR/app/deploy/market-memory-spy-rest-prereqs.sh" --check-ready >/dev/null 2>&1; then
	:
else
	SPY_REST_PREREQ_STATUS=0
	bash "$APP_DIR/app/deploy/market-memory-spy-rest-prereqs.sh" || SPY_REST_PREREQ_STATUS=$?
	if [ "$SPY_REST_PREREQ_STATUS" -eq 0 ]; then
		echo "macro-update: spy-rest credentials provisioned"
	elif [ "$SPY_REST_PREREQ_STATUS" -eq 2 ]; then
		echo "macro-update: spy-rest credential absent; source unit will fail closed until provisioned" >&2
	else
		echo "macro-update: WARNING: spy-rest credential provisioning failed (status $SPY_REST_PREREQ_STATUS)" >&2
	fi
fi


# Marketing X Catalyst SEC source writer (A3). Credentialed (R2 and its SEC
# contact through /etc/macro-api.env); the unit allows IP sockets and the code
# fetches only www.sec.gov URLs, rejects redirects and caps every response.
# It records URL, sha256, figures, clocks and receipts below
# marketing/catalyst-sec-source/v1/ and never document bytes. Arming it has no
# public effect: the public reader stays unconfigured until its operator sets
# CATALYST_PUBLIC_ENABLED on, and no other unit is restarted here.
CATALYST_SOURCE_UNIT_UPDATED=0
CATALYST_SOURCE_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-catalyst-source-cycle.service"
	"$APP_DIR/app/deploy/macro-catalyst-source-cycle.timer"
)
if ! mm_reviewed_unit_file_ready "${CATALYST_SOURCE_UNIT_SOURCES[0]}" /etc/systemd/system/macro-catalyst-source-cycle.service || \
   ! mm_reviewed_unit_file_ready "${CATALYST_SOURCE_UNIT_SOURCES[1]}" /etc/systemd/system/macro-catalyst-source-cycle.timer; then
	unit_repair_inputs_safe "${CATALYST_SOURCE_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe catalyst source unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${CATALYST_SOURCE_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${CATALYST_SOURCE_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				CATALYST_SOURCE_UNIT_UPDATED=1
			fi
		done
		if [ "$CATALYST_SOURCE_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-catalyst-source-cycle.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: Catalyst SEC source units updated"
		fi
	else
		echo "macro-update: refusing Catalyst SEC source unit update — systemd-analyze verify failed" >&2
	fi
fi
systemctl enable --now macro-catalyst-source-cycle.timer >/dev/null 2>&1 || \
	echo "macro-update: macro-catalyst-source-cycle.timer could not be enabled" >&2

# W1B.1 trusted context publisher: network-dark and credential-free. It writes
# exact raw evidence only below the API-inaccessible state tree and advances the
# separate public trusted-v1 HEAD only after that evidence and the typed feature
# object are durable.
MARKET_MEMORY_CONTEXT_UNIT_UPDATED=0
MARKET_MEMORY_CONTEXT_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-context.service"
	"$APP_DIR/app/deploy/macro-market-memory-context.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_CONTEXT_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-context.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_CONTEXT_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-context.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_CONTEXT_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe context unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_CONTEXT_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_CONTEXT_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_CONTEXT_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_CONTEXT_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-context.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory trusted-context units updated"
		fi
	else
		echo "macro-update: refusing Market Memory context unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-context.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-context.timer could not be enabled" >&2
fi

MARKET_MEMORY_CONTEXT_RUN_NEEDED=0
if [ "$MARKET_MEMORY_CONTEXT_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/project_market_memory_context\.py|engine/neuralweb/market_memory(_pit|_identity|_projection|_trusted)?\.py|contracts/market_memory/(macro_regime_snapshot|macro_regime_feature_object|trusted_capture_receipt)\.v1\.schema\.json|config/market_memory_canary\.v1\.json|engine/run\.py|data/regime/latest\.json)$'; then
	MARKET_MEMORY_CONTEXT_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_CONTEXT_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Market Memory context projection until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Market Memory context projection — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-context.service; then
		echo "macro-update: Market Memory context projection failed closed; hourly timer will retry" >&2
	fi
fi

# Options Context Audit publisher: a distinct preregistered evidence owner.
# W2C owner replay waits on trusted context, not this receipt. Its failure
# stays loud and must not relabel a successful trusted projection as failure.
MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_UPDATED=0
MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-options-context-audit.service"
	"$APP_DIR/app/deploy/macro-market-memory-options-context-audit.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-options-context-audit.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-options-context-audit.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe options-context-audit unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-options-context-audit.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory options-context-audit units updated"
		fi
	else
		echo "macro-update: refusing Market Memory options-context-audit unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-options-context-audit.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-options-context-audit.timer could not be enabled" >&2
fi

MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_RUN_NEEDED=0
if [ "$MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/audit_options_market_memory_context\.py|engine/options_market_memory_(context|receipt_store)\.py)$'; then
	MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_OPTIONS_CONTEXT_AUDIT_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Options Context Audit until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Options Context Audit — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-options-context-audit.service; then
		echo "macro-update: Options Context Audit failed closed; hourly timer will retry" >&2
	fi
fi

# W1B.2 private identity-observation publisher: network-dark, credential-free,
# and deliberately disconnected from the API-readable trusted-v1 store. It
# records legacy roster snapshots only as reconstruction and can admit a future
# observation operationally only when the collector's receipt-last contract
# authenticates the exact snapshot bytes.
MARKET_MEMORY_IDENTITY_UNIT_UPDATED=0
MARKET_MEMORY_IDENTITY_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-identity.service"
	"$APP_DIR/app/deploy/macro-market-memory-identity.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_IDENTITY_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-identity.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_IDENTITY_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-identity.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_IDENTITY_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe identity unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_IDENTITY_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_IDENTITY_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_IDENTITY_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_IDENTITY_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-identity.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory identity-observation units updated"
		fi
	else
		echo "macro-update: refusing Market Memory identity unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-identity.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-identity.timer could not be enabled" >&2
fi

MARKET_MEMORY_IDENTITY_RUN_NEEDED=0
if [ "$MARKET_MEMORY_IDENTITY_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/ingest_market_memory_identity\.py|engine/neuralweb/market_memory_identity_(observation|store)\.py|lib/symbol_directory_receipts\.py|collectors/symbol_directory\.py|contracts/(market_memory/(spy_listing_(object|observation)|identity_observation_(prepared|capture_receipt|store_receipts))\.v1\.schema\.json|symbol_directory/symbol_directory_completion_receipt\.v1\.schema\.json)|data/symbol_directory/(snapshots|cik_map|receipts)/.*)$'; then
	MARKET_MEMORY_IDENTITY_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_IDENTITY_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Market Memory identity accrual until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Market Memory identity accrual — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-identity.service; then
		echo "macro-update: Market Memory identity accrual failed closed; hourly timer will retry" >&2
	fi
fi

# W1B.3B private SPY raw-close technical actual-output publisher. The only
# network access is the fixed public R2 manifest/object transaction embedded in
# reviewed code; it has no credentials and remains disconnected from the API,
# trusted-v1, Prophet, options, outcomes, ranking, sizing, and execution.
MARKET_MEMORY_TECHNICALS_UNIT_UPDATED=0
MARKET_MEMORY_TECHNICALS_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-technicals.service"
	"$APP_DIR/app/deploy/macro-market-memory-technicals.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_TECHNICALS_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-technicals.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_TECHNICALS_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-technicals.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_TECHNICALS_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe technicals unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_TECHNICALS_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_TECHNICALS_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_TECHNICALS_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_TECHNICALS_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-technicals.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory technical actual-output units updated"
		fi
	else
		echo "macro-update: refusing Market Memory technical unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-technicals.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-technicals.timer could not be enabled" >&2
fi

MARKET_MEMORY_TECHNICALS_RUN_NEEDED=0
if [ "$MARKET_MEMORY_TECHNICALS_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/capture_market_memory_technicals\.py|engine/neuralweb/market_memory_technical_(observation|store)\.py|contracts/market_memory/(spy_daily_price_source_observation|spy_raw_close_ratio_snapshot|technicals_actual_output_capture_receipt|technicals_actual_output_store)\.v1\.schema\.json|config/market_memory_(canary|technical_price_basis)\.v1\.json|lib/nyse_calendar\.py|research/licenses/MASSIVE_ENTITLEMENT_RECORD\.md)$'; then
	MARKET_MEMORY_TECHNICALS_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_TECHNICALS_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Market Memory technical capture until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Market Memory technical capture — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-technicals.service; then
		echo "macro-update: Market Memory technical capture failed closed; hourly timer will retry" >&2
	fi
fi

# W2C M0D v2 — Keyless technicals-v2 projector (reads sealed REST source only).
MARKET_MEMORY_TECHNICALS_V2_UNIT_UPDATED=0
MARKET_MEMORY_TECHNICALS_V2_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-technicals-v2.service"
	"$APP_DIR/app/deploy/macro-market-memory-technicals-v2.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_TECHNICALS_V2_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-technicals-v2.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_TECHNICALS_V2_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-technicals-v2.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_TECHNICALS_V2_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe technicals-v2 unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_TECHNICALS_V2_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_TECHNICALS_V2_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_TECHNICALS_V2_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_TECHNICALS_V2_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-technicals-v2.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory technicals-v2 units updated"
		fi
	else
		echo "macro-update: refusing Market Memory technicals-v2 unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-technicals-v2.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-technicals-v2.timer could not be enabled" >&2
fi
# W2C M0D v2 — Experience-v2 accrual (04:32Z, separate from v1 04:30Z).
# v1 timer has NO Requires= on this unit; independent execution.
# Placed here (before W2C exit 1 at ~1516) so first-ship works on the same
# deploy tick that installs the unit. N1: NOT in reciprocal_market_memory_units_ready.
MARKET_MEMORY_EXPERIENCE_V2_UNIT_UPDATED=0
MARKET_MEMORY_EXPERIENCE_V2_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-experience-v2.service"
	"$APP_DIR/app/deploy/macro-market-memory-experience-v2.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_EXPERIENCE_V2_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-experience-v2.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_EXPERIENCE_V2_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-experience-v2.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_EXPERIENCE_V2_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe experience-v2 unit repair input" >&2
		# Non-fatal: v1 units must continue; v2 is a new parallel arm
		true
	}
	if systemd-analyze verify "${MARKET_MEMORY_EXPERIENCE_V2_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_EXPERIENCE_V2_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					continue
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_EXPERIENCE_V2_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_EXPERIENCE_V2_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-experience-v2.timer 2>/dev/null || true
			fi
			echo "macro-update: Market Memory experience-v2 units updated"
		fi
	else
		echo "macro-update: refusing Market Memory experience-v2 unit update — systemd-analyze verify failed" >&2
	fi
fi
# N2/B3: Write the v2 install marker once if absent. Runs regardless of whether
# units were updated on this tick (covers first-ship where units already match).
# Gate: service unit on disk AND marker absent AND not a symlink. Non-fatal.
V2_INSTALL_MARKER="/var/lib/macro-market-memory/state/experience-v2/.v2_install_verified"
if [ -e "/etc/systemd/system/macro-market-memory-experience-v2.service" ] && \
   [ ! -e "$V2_INSTALL_MARKER" ] && [ ! -L "$V2_INSTALL_MARKER" ]; then
	if /opt/macro-api/.venv/bin/python "$APP_DIR/scripts/accrue_market_memory_spy_experience_v2.py" \
		--write-install-marker \
		--experience-root /var/lib/macro-market-memory/state/experience-v2; then
		echo "macro-update: experience-v2 install marker written"
	else
		echo "macro-update: WARNING: failed to write experience-v2 install marker" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-experience-v2.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-experience-v2.timer could not be enabled" >&2
fi
# credential-free, and deliberately disconnected from both trusted-v1 and the
# API. It captures only the exact current Git-owned tip after frozen calendar,
# identity, constituent, and freshness checks; historical rows are never
# upgraded by this lane.
MARKET_MEMORY_BREADTH_UNIT_UPDATED=0
MARKET_MEMORY_BREADTH_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-breadth.service"
	"$APP_DIR/app/deploy/macro-market-memory-breadth.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_BREADTH_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-breadth.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_BREADTH_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-breadth.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_BREADTH_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe breadth unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_BREADTH_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_BREADTH_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_BREADTH_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_BREADTH_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-breadth.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory breadth actual-output units updated"
		fi
	else
		echo "macro-update: refusing Market Memory breadth unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-breadth.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-breadth.timer could not be enabled" >&2
fi

MARKET_MEMORY_BREADTH_RUN_NEEDED=0
if [ "$MARKET_MEMORY_BREADTH_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/capture_market_memory_breadth\.py|engine/neuralweb/market_memory_(actual_output_store|breadth_observation)\.py|contracts/market_memory/breadth_(source_observation|factors_snapshot|actual_output_capture_receipt|actual_output_store)\.v1\.schema\.json|data/breadth/(breadth|constituents)\.parquet|config/market_memory_canary\.v1\.json|lib/nyse_calendar\.py)$'; then
	MARKET_MEMORY_BREADTH_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_BREADTH_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Market Memory breadth capture until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Market Memory breadth capture — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-breadth.service; then
		echo "macro-update: Market Memory breadth capture failed closed; hourly timer will retry" >&2
	fi
fi

# W2C private prospective experience accrual.  The writer is network-dark and
# credential-free.  It reads only the exact trusted-v1 and technical owner
# generations, derives its denominator from the tracked registration/calendar,
# and writes only the disjoint experience-v1 ledger.
MARKET_MEMORY_EXPERIENCE_UNIT_UPDATED=0
MARKET_MEMORY_EXPERIENCE_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-experience.service"
	"$APP_DIR/app/deploy/macro-market-memory-experience.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_EXPERIENCE_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-experience.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_EXPERIENCE_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-experience.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_EXPERIENCE_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe experience unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_EXPERIENCE_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_EXPERIENCE_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_EXPERIENCE_UNIT_UPDATED=1
			fi
		done
			if [ "$MARKET_MEMORY_EXPERIENCE_UNIT_UPDATED" -eq 1 ]; then
				systemctl daemon-reload
				RECONCILED=1
			echo "macro-update: Market Memory SPY experience units updated"
		fi
	else
		echo "macro-update: refusing Market Memory experience unit update — systemd-analyze verify failed" >&2
	fi
fi
# API serving deploys independently of Market Memory attestation. W2C owner
# replay may still exit 1 after this transaction; experience/options stay
# fail-closed. The fence is minted here so a later W2C failure cannot strand
# the updater restarting macro-api on every cron tick.
# BEGIN MACRO_API_RESTART_TRANSACTION
# macro-api: restart ONLY when its own code changed (avoid blipping /api on every
# site/ render commit). "Its own code" = every Python module import-cached by the
# running uvicorn, because sys.modules pins the OLD module object for the life of
# the process: without a restart the new file sits on disk while the API keeps
# serving the previous code — live in git, dead in production, with no signal.
#
# INCLUSION RULE (keep the list narrow but complete). A path belongs here when the
# API process imports it, either:
#   (a) at load     — app/*.py and their module-level engine/lib closure; or
#   (b) at request  — a function-level import on a path an API endpoint reaches
#                     (cached after the first call, same trap, just later).
# Every module below was confirmed against the import graph of app/*.py, not
# guessed. When adding a lazy `from engine...` / `from lib...` import to any app/
# router or to a module already listed here, extend this list in the same commit —
# tests/test_deploy_update_self_heal.py recomputes the load-time closure and fails
# CI if it drifts out of this regex.
#
# Why each group is here:
#   Prophet observations   the entitled request lazily imports the lossless
#                          reader, B1 snapshot and intake/identity helpers. Their
#                          named module closure is cached after the first read;
#                          source JSON/parquet bytes are still read per request.
#   app/.*\.py             every router is import-cached (the old list omitted
#                          regwall.py/paywall.py: code could deploy while the
#                          running API kept the previous access policy)
#   neuralweb/*            /api/ask + /api/brain: ask_brain → cortex, llm_auth,
#                          envelope → synapse, tushare_freshness; brain_gateway →
#                          chart_perception, doctrine, key_pool (CMX W2/W4)
#   earnings evidence      brain_gateway lazily reaches earnings_context_reader,
#                          whose exact-evidence validator imports the named
#                          earnings_narrative contract closure and PRESS adapter.
#                          All become request-time cached after the first read.
#   codex_provider/runner  llm_auth's request-time Codex fallback imports both;
#                          either module stays cached after the first Codex turn
#   research_vault/        app/research.py imports catalog, corpus, download_quota,
#                          view_ratelimit, watermark (→ sidecar, r2_store) at MODULE
#                          level. Whole-package pattern on purpose: this is the
#                          vault's serving layer, so a new module added here is
#                          API-cached too and must not need a second fix. Omitting
#                          it silently froze download caps / anti-scrape limits —
#                          #3654 escaped only because it also touched app/research.py.
#   fundamental_forensics/ app/forensics.py imports private_state through the
#                          package, whose __init__ loads the pure kernel modules;
#                          all are therefore pinned in macro-api sys.modules.
#   capital_structure/*    app/capital_structure.py imports projection at module
#                          load; projection and its package __init__ pull the
#                          event spine, normalized document-term kernel, and
#                          source-identity helpers into sys.modules. The private
#                          scenario evaluate route (SPEC_U1B §4) also imports the
#                          capacity inputs bundle, scenario composition and the
#                          capacity/rule/share-basis kernels they load. All stay
#                          pinned until macro-api restarts. Named narrowly so
#                          nightly-only compilers do not blip the serving plane.
#                          U1a state-bundle API (2026-10-19): app/capital_structure.py
#                          also imports state_bundle, issuer_state_contracts, the
#                          rule-applicability and registration-integration kernels and
#                          the verified-generation reader at module load; their
#                          capacity/reference/collector helpers are pinned too.
#                          U2 saved scenarios (SPEC_U2): saved_scenarios,
#                          scenario_export and state_changes load with the module;
#                          the saved-scenario store (and through it the alert
#                          delivery drain and frozen delivery client) loads on
#                          first use and then stays cached the same way.
#   government_revenue/*   app/government_revenue.py imports workspace through
#                          the non-inert package __init__, which loads the award,
#                          dossier, exact entity-resolution, federation,
#                          freshness, metric, opportunity, PIT, budget-program,
#                          IDV-dossier, and subaward-dossier helpers.
#                          These serving-plane modules remain cached for the
#                          life of macro-api and must advance with a deploy.
#                          Their lru_cache'd validators pin the referenced
#                          contracts/government_revenue schemas in-process for
#                          the same lifetime, so those schema files are named
#                          in the trigger too; schema reads with no cache (the
#                          budget graph, the coverage builders) re-read per
#                          call, self-heal without a restart, and stay out.
#                          tests/test_deploy_update_self_heal.py derives the
#                          pinned set from the app/ import closure.
#   company_intelligence/* app/company_intelligence.py imports the verified
#                          reader's public artifact contract.  Importing this
#                          package executes its non-inert __init__, which loads
#                          contracts, health, and views; all are pinned in the
#                          API process for the lifetime of the public ticker
#                          context route.
#   integrated answer      app/integrated_answer.py (Package I v0, default-off) reads
#                          company_theme_exposure/{__init__,contracts}, expectation_state,
#                          k3e_expectation_surface, theme_context and the frozen-source
#                          loader scripts/query_k3e_expectation_surface.py at request
#                          time; each stays cached in macro-api after the first read.
#   seasonality/           app/seasonality.py's single `from engine.seasonality
#                          import screener` executes the package __init__, which
#                          eagerly re-exports contracts, event_clock, model,
#                          multiplicity, prophet_bridge, regime, screener and
#                          universe. All nine were confirmed against a live
#                          interpreter's sys.modules, not read off import lines.
#                          Named, not globbed, and the seven exclusions are
#                          load-bearing: calendar, calibration, event_study,
#                          foundation, panel, scanner and state are the
#                          numpy/pandas research modules that __init__ keeps out
#                          on purpose (calibration and event_study resolve
#                          through its PEP 562 __getattr__ only when something
#                          asks, and no app/ path asks). Globbing would blip /api
#                          on every research commit in an actively-built program.
#   context_index/         brain_gateway → packet.build_packet, which top-level
#                          imports fusion/gitinfo/lexical/structured. Named, not
#                          globbed: ingest/chunking/health/schema/sources are
#                          nightly-only builders the API never imports.
#   marketing/             brain_gateway's chart path → chart_render (load_ohlcv,
#                          render_chart_v2) + confluence_source. The other twelve
#                          are NOT optional and NOT reached by reading import
#                          lines: importing ANY engine.marketing submodule first
#                          executes the PACKAGE __init__, which imports state →
#                          authority, charter, claims, cmo, departments, economics,
#                          events, ledgers, opportunity_bus, publication. All
#                          fourteen were confirmed against a live interpreter's
#                          sys.modules, not inferred. Named, not globbed: 34 of the
#                          48 marketing modules are nightly-only, and outbox/
#                          rejections are admin-only (see the admin list below).
#   engine/live_quotes.py  app/tape.py REST quote fetch (→ lib/config.py)
#   engine/quote_resolution.py brain_gateway imports the shared read-only quote
#                          resolver at module load; its owner waterfall remains
#                          cached in macro-api until the process restarts.
#   engine/neuralweb/native_facts.py and engine/intelligence_workspace/*.py
#                          W1-B lazily imports the frozen typed fact runtime on
#                          the first native request; Python then pins those
#                          modules, the registry, and schema validators for the
#                          process lifetime. The request-time owner closure also
#                          pins Data OS identity/registry modules, Theme Graph's
#                          current-view and cached rights readers, and the equity
#                          earnings staleness helpers. Exact W1-A and transitive
#                          config/schema changes therefore require the same
#                          restart without widening to nightly Theme builders or
#                          unrelated collectors.
#   lib/*                  ai_costs + mastermind_response_log log every chat call;
#                          config.py is a module-level dep of live_quotes;
#                          us_cash_calendar imports the exchange_holidays annual
#                          slate for live_quotes; both remain cached until restart;
#                          commercial_path.py is the GATE-4 emit module reached
#                          from billing / require_user / brain_gateway (function-
#                          level, cached after the first money-path event)
#
# Deliberately NOT here (do not "fix" these — they would blip /api for nothing):
#   - Doctrine CONTENT (engine/neuralweb/doctrine/*.md AND analyst/*.md): both
#     libraries reload the .md files on mtime change, so prose-only edits go
#     live with no restart.
#   - Data/artifact files read from disk per request.
#   - The nightly-only closure behind cortex.run() (constitution → qledger →
#     ai_desk → master_brain → china_*): the API imports cortex for its tool
#     schemas/implementations only and never calls run(), so those ~90 modules are
#     NOT in the API's sys.modules. Adding them would restart /api on nearly every
#     engine commit — exactly what this narrow list exists to prevent.
#
# Theme-research (#7870): app/theme_research.py reaches the market_ontology
# registration chain, which reaches the engine/theme_graph leaves below.
# CORRECTION (shared-foundation extraction): those edges are no longer
# module-level. The registry resolves a vertical's composer, its owner-bundle
# loader and theme_node_id INSIDE the call, on the first served request that
# needs them. That makes this pinning more necessary, not less — sys.modules
# caches each module for the life of the macro-api process, so a changed file
# keeps serving its old bytes until a restart. Do not trim an entry on the
# grounds that nothing imports it at import time; the enumeration below is
# the set of modules a served request can bind, eagerly or lazily.
# The nine engine/market_ontology modules are ENUMERATED, not globbed: the
# rest of that package is nightly-only, and a wildcard would blip /api on
# every ontology commit.
API_RESTART_CONFIRMED=0
API_RESTART_NEEDED=0
# Ontology research requests cache the captured-DRL/K1/K3/K5 modules and the
# published-Radar reader's native validation closure (including its pure
# earnings validators -> quote-context -> pack imports). Names stay exact;
# nightly producers and unrelated price-pressure modules do not trigger API.
# K3 vector/slot contracts and Radar's K1 metadata validator are lru-cached too.
# Options authentication imports the retained Matrix reader through the identity
# consumer; its Python code is cached in the API process and needs a restart.
# Registered Today and pinned Research reads import these exact composition
# modules in-process. Their cached code must restart with a source-only change;
# The macro workspace schema is cached by contract.load_schema/_validator and
# needs the same restart. Served workspace/catalog bytes are read per request.
# Private Plan serving imports the exact identity/terms readers at load time and
# the incumbent expiry bridge/payoff closure on request; all remain process-cached.
# BEGIN MACRO_API_RESTART_TRIGGER
if [ "$API_UNIT_UPDATED" -eq 1 ] || ! mm_api_fence_marker_ready || grep -qE '^(app/.*\.py|app/requirements\.txt|app/deploy/macro-api\.service|config\.yml|config/(site_access|dataset_registry|theme_sources|plans)\.yml|config/intelligence_workspace/datapoints\.v1\.json|contracts/intelligence_workspace/(datapoint_(registry|value)|ai_context_envelope\.v1)\.schema\.json|collectors/(equity_earnings|sec_document_spine|sec_request_pacer)\.py|engine/neuralweb/(ask_brain|cortex|brain_gateway|brain_visuals|brain_financial_views|brain_financial_reader|rotation_risk_context|brain_native_inputs|native_facts|chart_perception|chat_plain_words|company_intelligence_reader|earnings_context_reader|doctrine|analyst_doctrine|market_packet|market_memory|market_memory_pit|market_memory_playback|market_memory_projection|market_memory_trusted|market_memory_episode_comparison|market_memory_episode_features|market_memory_episode_retrieval|market_memory_operating_cortex_service|market_memory_retained_context_cohort|market_memory_retained_use|market_memory_retained_catalog|market_memory_retained_saved|market_memory_retained_legacy_guard|brain_market_intel|brain_analogues|brain_curve|brain_user_memory|envelope|key_pool|synapse)\.py|engine/intelligence_workspace/.*\.py|engine/theme_graph/(store|rights|curation_assertion|economic_context|issuer_economic_context|native_disclosure_propagation|identity|identity_resolution|ontology|probation|security_navigation)\.py|engine/qbus_news_.*\.py|engine/qkernel\.py|engine/earnings_catalyst\.py|engine/sue\.py|engine/earnings_release/(__init__|binding|receipts|figures|filing_key)\.py|engine/earnings_narrative/(__init__|context_packets|contracts|digest|economic_interpretation|private_publication|promotion|public_wire|story|story_packets)\.py|engine/press/(__init__|earnings_adapter)\.py|engine/(codex_provider|llm_auth|news_events|ontology_explorer|ontology_portfolio|ontology_theme|ontology_scenario|ontology_scenario_runtime|transmission_chains|prophet_integrity|risk_envelope|options_issue_desk|options_matrix_retention|options_hub_retention|options_scenario_capture|options_nbbo_cohort|options_plan_expiry|options_payoff|greeks|intraday_greeks|portfolio_brief|portfolio_changes|portfolio_vocab|live_quotes|quote_resolution|tushare_freshness)\.py|engine/codex_lane/runner\.py|engine/prophet_lab/.*\.py|engine/(canon|confluence_tiers|entry_primitives|hysteresis|indicators|path_personality|path_risk_signals|prophet_early_observations|session_anchor|session_digest|stock_technicals|technicals|us_candidate_episode|us_candidate_episode_intake)\.py|engine/stock_identity/(__init__|authority|fingerprint|plane)\.py|engine/entry_radar/(__init__|c5_adapter|challengers|contracts|detectors|earnings_context|entry_events|four_hour|g0_adapter|indicator_core|indicator_ingest|live_ledger|live_pack|quote_context|readings|research_read|spool)\.py|engine/entry_radar/replay/identity_observation_snapshot\.py|engine/price_pressure/(__init__|research)\.py|lib/(options_source_receipts|quote_native_metadata|evidence_foundation|opportunity_case|opportunity_evidence|economic_propagation|economic_propagation_v2)\.py|contracts/opportunity_evidence/(vector\.v1\.schema|slot_registry\.v1)\.json|contracts/evidence_foundation/reference\.v1\.schema\.json|contracts/economic_propagation/(propagation_hypothesis\.v[12]\.schema|generator_registry\.v1)\.json|engine/prophet_live/(__init__|interval|live_states)\.py|engine/research_vault/.*\.py|engine/institutional_census/.*\.py|lib/(institutional_13f_adapter|institutional_intelligence|rotation_observation_notification)\.py|engine/fundamental_forensics/.*\.py|engine/biocatalyst/.*\.py|engine/sector_intelligence/.*\.py|engine/company_intelligence/.*\.py|engine/company_theme_exposure/(__init__|contracts)\.py|engine/market_ontology/(__init__|exposure_map|bea_gvc_current|semiconductor_owner_bundle|semiconductor_theme_research|semiconductor_witness_scope|theme_research_binding|theme_research_mounts|theme_research_registry|workspace_projection)\.py|engine/(expectation_state|k3e_expectation_surface|theme_context)\.py|scripts/query_k3e_expectation_surface\.py|engine/seasonality/(__init__|contracts|event_clock|model|multiplicity|program_watch|prophet_bridge|regime|screener|universe)\.py|engine/capital_structure/(__init__|authorized_shares|capacity|capacity_joint|document_terms|event_spine|funding|issuer_state_contracts|listing_facts|projection|reference_qualification|registration_integration|registration_lifecycle|rule_applicability|saved_scenario_store|saved_scenarios|scenario_composition|scenario_export|scenario_inputs|share_basis|source_identity|state_bundle|state_changes|supply_scenarios|transactions|variable_terms|verified_projection_generation)\.py|engine/alert_delivery_drain\.py|lib/frozen_delivery_client\.py|engine/government_revenue/(__init__|amount_semantics|award_events|budget_program|candidates|dossiers|entity_resolution|federation|fms_cases|freshness|idv_bridge|idv_dossiers|metrics|opportunities|point_in_time|sbir_progression|defense_economics|defense_interpretation|research_state|candidate_grader|program_theme_publication|program_theme_context|program_theme_disclosure|program_ontology|budget_allocation_context|identity_atlas|subaward_dossiers|workspace)\.py|contracts/government_revenue/(government_entity_coverage\.v1|government_idv_bridge\.v1|government_idv_dossiers\.v1|government_procurement_(event|workspace)\.v2|government_recipient_resolution_coverage\.v1|government_revenue_candidate(_queue|_historical_suppressions|_issuance_corrections)?\.v1|government_revenue_dossiers\.v1|government_subaward_dossiers\.v1|government_revenue_identity_atlas\.v1)\.schema\.json|contracts/theme_graph/(identity_resolution|probation_proposal)\.v1\.schema\.json|contracts/options/options\.(issue_desk(_proposal|_decision)?|issue_receipt)\.v1\.schema\.json|engine/context_index/(packet|fusion|gitinfo|lexical|structured)\.py|engine/marketing/(__init__|authority|chart_render|charter|claims|cmo|confluence_source|departments|economics|events|ledgers|opportunity_bus|publication|state|catalyst_lifecycle|catalyst_packets|catalyst_admission|catalyst_scan|catalyst_source_adapter|catalyst_source_cycle|catalyst_source_store|attribution)\.py|config/catalyst_pilot_universe\.json|lib/dataos/.*\.py|lib/(config|shared_shell|ai_costs|commercial_path|growth_registry|help_directory|mastermind_response_log|nyse_calendar|cn_calendar|hk_calendar|market_session|tsx_calendar|us_cash_calendar|exchange_holidays|user_prefs|tiers|team_membership)\.py|engine/capital_need\.py|engine/coiled\.py|engine/conditions\.py|engine/cycles\.py|engine/dannytrades\.py|engine/dannytrades_chip\.py|engine/debt_maturity\.py|engine/demand_chain\.py|engine/dispersion\.py|engine/donor\.py|engine/earnings_blackout\.py|engine/entry_signal\.py|engine/event_atlas\.py|engine/extension\.py|engine/gex_confirm\.py|engine/grading\.py|engine/hold\.py|engine/htf_durability\.py|engine/i18n\.py|engine/ledger_lane\.py|engine/mtf_upturn\.py|engine/name_score\.py|engine/name_score_grader\.py|engine/options_ivspread\.py|engine/playbook\.py|engine/pullback_zone\.py|engine/risk_sizing\.py|engine/setups\.py|engine/signal_gate\.py|engine/signal_quality\.py|engine/stock_events\.py|engine/stock_fundamentals\.py|engine/stock_macro_sensitivity\.py|engine/stock_score\.py|engine/stock_view\.py|engine/ticker_alerts\.py|engine/us_board_rank\.py|engine/valuation\.py|engine/valuation_scenario\.py|engine/vol_forecast\.py|engine/vol_squeeze\.py|engine/washout_turn\.py|lib/delisted_symbols\.py|lib/store\.py|lib/ticker_popularity\.py|scripts/build_debt_maturity\.py|scripts/build_stock_library\.py|scripts/security_state_producer\.py|engine/news_common\.py|engine/medtech/(events|publication)\.py|engine/market_os/macro_workspaces/(__init__|contract|registry)\.py|engine/qual_extraction\.py|engine/research_intelligence/(__init__|extractor|projection|schema|selection|store|vault_adapter)\.py|lib/macro_suite_(disclosure|labels|view|zh_parity)\.py|scripts/build_macro_suite_pages\.py|contracts/market_os/macro_workspace_snapshot\.v1\.schema\.json|lib/treasury_daily_history\.py|engine/sector_native_view\.py|lib/sector_(action_preview|generation_contract|generation_wire|history_contract)\.py|scripts/(check_sector_intelligence_freshness|vps_live_orchestrator)\.py)$' <<<"$CHANGED" || \
   [ "$API_DEPS_UPDATED" -eq 1 ]; then
	API_RESTART_NEEDED=1

fi
# Catalyst projection code is imported into the API process.
if grep -qE '^engine/catalyst_opportunity/.*\.py$' <<<"$CHANGED"; then
	API_RESTART_NEEDED=1
fi
# Evaluation and options modules are imported into the API process.
if grep -qE '^engine/(neuralweb/response_eval|options_hub_retention|options_scenario_capture)\.py$' <<<"$CHANGED"; then
	API_RESTART_NEEDED=1
fi
# END MACRO_API_RESTART_TRIGGER
if [ "$API_RESTART_NEEDED" -eq 1 ]; then
	disarm_options_timer
	rm -f "$OPTIONS_API_FENCE_MARKER"
	# Verified restart, not fire-and-forget: on 2026-07-30 the old one-liner
	# (`... && systemctl restart macro-api || true`) left the API on its 5-hour-old
	# PID after a matching deploy, and the `|| true` destroyed every trace of why.
	# Log the PID transition, and retry once when the restart failed or the PID
	# provably did not change — all output lands in macro-update.log.
	if [ "$API_UNIT_READY" -ne 1 ]; then
		echo "macro-update: macro-api restart skipped because the reviewed unit is not installed exactly" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: macro-api restart skipped because dependency reconciliation failed" >&2
	elif systemctl is-enabled macro-api >/dev/null 2>&1; then
		systemctl daemon-reload
		API_NEED_DAEMON_RELOAD=$(systemctl show -p NeedDaemonReload --value macro-api)
		[ "$API_NEED_DAEMON_RELOAD" = no ] || {
			echo "macro-update: macro-api manager state remains stale after daemon-reload" >&2
			exit 1
		}
		PRE_PID="$(systemctl show -p MainPID --value macro-api 2>/dev/null || echo '?')"
		API_RESTART_RC=0
		systemctl restart macro-api || API_RESTART_RC=$?
		POST_PID="$(systemctl show -p MainPID --value macro-api 2>/dev/null || echo '?')"
		if [ "$API_RESTART_RC" -eq 0 ] && [[ "$POST_PID" =~ ^[1-9][0-9]*$ ]] && [ "$POST_PID" != "$PRE_PID" ]; then
			API_RESTART_CONFIRMED=1
			echo "macro-api restarted pid $PRE_PID -> $POST_PID"
		else
			echo "macro-api restart ANOMALY rc=$API_RESTART_RC pid $PRE_PID -> $POST_PID; retrying once"
			sleep 2
			API_RETRY_RC=0
			systemctl restart macro-api || API_RETRY_RC=$?
			FINAL_PID="$(systemctl show -p MainPID --value macro-api 2>/dev/null || echo '?')"
			if [ "$API_RETRY_RC" -eq 0 ] && [[ "$FINAL_PID" =~ ^[1-9][0-9]*$ ]] && [ "$FINAL_PID" != "$PRE_PID" ]; then
				API_RESTART_CONFIRMED=1
				echo "macro-api restart retry succeeded pid $PRE_PID -> $FINAL_PID"
			else
				echo "macro-api restart RETRY FAILED rc=$API_RETRY_RC pid $PRE_PID -> $FINAL_PID" >&2
			fi
		fi
	fi
fi

# The marker attests a verified PID transition into the installed unit that
# hides both the disjoint raw store and its dedicated credential source.  It is
# removed whenever that unit changes and /run clears it on reboot, so option
# evidence cannot exist while an older API namespace remains able to read it.
if [ "$API_RESTART_CONFIRMED" -eq 1 ] && [ "$API_UNIT_READY" -eq 1 ] && \
   [ "$(systemctl show -p NeedDaemonReload --value macro-api)" = no ] && \
   cmp -s "$APP_DIR/app/deploy/macro-api.service" /etc/systemd/system/macro-api.service && \
   grep -Fxq 'InaccessiblePaths=/var/lib/macro-market-memory-options' /etc/systemd/system/macro-api.service && \
   grep -Fxq 'InaccessiblePaths=/etc/macro-market-memory-options' /etc/systemd/system/macro-api.service; then
	mm_write_api_fence_marker
fi
# END MACRO_API_RESTART_TRANSACTION

# Admin serving, like the API, deploys independently of W2C attestation.
# Keep the reviewed unit and cached catalog current even when the separate
# Market Memory lane refuses activation; its exits and timer guards remain below.
# admin console: restart ONLY when its own code changed, so the deployed panel at
# admin.mastermind-x.com tracks main automatically (config/secrets live in the
# untouched /etc/macro-admin.env, so a restart never loses them). "Its own code"
# includes the engine/lib modules the panels lazily import — cached in sys.modules
# after the first request, so without a restart an engine-side fix (e.g. a
# key_pool.py change to the Raw Key Usage join) never reaches the running panel;
# data files are read from disk per request and need no restart.
#
# INCLUSION RULE — the same one the macro-api list above uses. admin/ is ALL panel
# code, so a function-level import there is import-cached exactly like a
# module-level one, just from the first request that reaches it; both kinds seed
# this list. Each seed is then expanded through MODULE-LEVEL imports only, because
# those are what actually execute on load. A nightly-only tail hanging off a DEEP
# function-level import is not cached and stays out (see the exclusions below).
# Three seed forms count, and grepping for `from engine`/`from lib` finds only the
# first: static imports, `importlib.import_module("engine...")` string literals
# (ai_cost, orchestrator_chat, neural_web all use this form), and the PACKAGE
# __init__ that Python executes before any submodule. Keep this list in sync when
# adding any of them — tests/test_deploy_update_self_heal.py recomputes the closure
# and fails CI if it drifts.
#
# Why each group is here:
#   admin/*                every panel module is import-cached by the process
#   lib/*                  ai_cost + orchestrator_chat → ai_costs;
#                          mastermind_logs → mastermind_response_log
#   neuralweb/*            metabolism_panel + orchestrator_chat → key_pool;
#                          orchestrator_chat → ask_brain; neural_web →
#                          support_map, orchestrator_log
#   metabolism/*           metabolism_panel → throttle; server manual-run gate →
#                          budget_gate
#   engine/{codex_provider,llm_auth,prophet_integrity}.py + engine/codex_lane/runner.py
#                          orchestrator_chat Codex fallback + prophet.py
#                          deliberation-spend panel; marketing.py → copywriter imports
#                          the canonical Prophet correction projection at load time
#   marketing/             marketing.py's outbox approve/reject/decide endpoints →
#                          outbox + rejections. marketing.py's Ad Central panel →
#                          ad_central → ad_allocator, ad_arena, ad_stats. The other
#                          twelve ride the package __init__ (→ state → authority,
#                          charter, claims, cmo, departments, economics, events,
#                          ledgers, opportunity_bus, publication) — confirmed
#                          against a live interpreter's sys.modules. Named, not
#                          globbed: 30 of the 53 marketing modules are nightly-only.
#                          (ad_creative/ad_matrix are NOT here: the panel reads the
#                          creatives ledger, it does not build creatives.)
#   marketing/sentinel     marketing.py's ramp resolver (resolve_ramp) + the
#                          /api/marketing/sentinel panel endpoints — the ramp
#                          caps would deploy dead to the running panel without
#                          a restart (2026-07-28, same class as the outbox gap).
#   scripts/               marketing.py's publish dry-run → marketing_publisher
#                          → copywriter (top-level import: the post-time language
#                          gate banned_language() must fail loudly, so the publisher
#                          imports it at module scope — which puts copywriter in
#                          the panel's load-time closure too).
#   marketing/social_publisher
#                          Same edge, one module further (2026-08-08): the
#                          publisher imports subscription_locked/lock_expires_at
#                          at module scope for the same "must fail loudly" reason
#                          — a lazily-imported lock predicate that failed to
#                          import would read as "no lock", i.e. silently restore
#                          the requeue loop it exists to stop. That top-level
#                          import is what puts social_publisher in the panel's
#                          closure, so it belongs here rather than in the
#                          nightly-only list below.
#   sentinel               marketing.py's caps_by_account (#3884) → resolve_ramp:
#                          the per-account D08 ramp caps shown in the outbox +
#                          publisher payloads import sentinel into the panel.
#
# Deliberately NOT here (they would blip the panel for nothing):
#   - site/ and data/ artifacts, read from disk per request.
#   - engine/neuralweb/cortex.py and the nightly lane behind it. The panel's only
#     entry into ask_brain is _post_filter_advice() (the advice guard); the
#     tool-schema/dispatch paths that lazily import cortex are never called from
#     admin, so cortex is absent from the panel's sys.modules. admin ships its own
#     tool dispatcher.
#   - The rest of engine/marketing (breaking_feed, …) —
#     nightly-only, never imported by a panel. social_publisher WAS listed here
#     and no longer is: see its entry above. A name in this list is a claim about
#     the closure, so it has to be deleted the moment the closure disagrees.
# Admin systemd sandbox: reconcile the reviewed unit before deciding whether to
# restart, so a unit-only hardening/provider change cannot land dead on disk.
ADMIN_UNIT_UPDATED=0
if ! cmp -s "$APP_DIR/admin/deploy/admin.service" /etc/systemd/system/admin.service; then
	if systemd-analyze verify "$APP_DIR/admin/deploy/admin.service"; then
		install -m 0644 "$APP_DIR/admin/deploy/admin.service" /etc/systemd/system/admin.service
		systemctl daemon-reload
		ADMIN_UNIT_UPDATED=1
		RECONCILED=1
		echo "macro-update: admin systemd sandbox updated"
	else
		echo "macro-update: refusing admin unit update — systemd-analyze verify failed" >&2
	fi
fi

# XG-W6 added four that ARE panel imports: labels + learned_rules (the Learning
# panel), health_monitor + blind_identity (the Desk Health panel). Without them
# here, a deploy that changed a halt threshold would leave the admin serving the
# old module out of sys.modules — and the panel that reports whether a desk is
# halted is the last one that should be stale.
#
# XG-W8 adds engine/press/{__init__,desk_planner}.py. The Press panel's cadence
# block now reports the RESOLVED cap (0 while the W2R desk-note lane is dark),
# and it gets that number by calling the planner's own `_triage_cap` rather than
# re-deriving the stricter-of rule — a panel that computes its own answer is a
# panel that can disagree with the engine. That call puts both modules in the
# admin's load-time closure, so without them here a deploy that changed the cap
# resolver would leave the panel serving the old rule out of sys.modules: the
# exact class the outbox gap (2026-07-26) and the four XG-W6 panel modules fixed.
# Only these two — research_triage/research_veto/research_lane are reached solely
# through desk_planner's function-level imports on the PLANNING path, which the
# panel never calls.
#
# The Intelligence Desk approve endpoint adds engine/marketing/{story_lock,
# wire_routing}.py. That endpoint is the ONE admin path that emits a post, and
# both modules are gates on it: wire_routing decides which desk owns the emission
# and story_lock enforces one-owner-per-conversation across desks. Left out here,
# a deploy that retuned the routing table or widened the lock window would leave
# the panel queueing against the OLD rule out of sys.modules — the outbox gap
# (2026-07-26) again, but on the path where being stale means a wrong-desk or
# double-owner post rather than a stale reading.
#
# A-F05-1 (PR #6896) adds engine/chronicle/impact.py. The Chronicle panel
# (admin/chronicle.py) imports it inside the request handler, which is
# import-cached after the first hit exactly like a module-level import, so a
# deploy that changed the impact scoring would leave the panel serving the old
# module out of sys.modules. governor.py stays out: the panel never imports it.
# F05-017 (PR #8265) makes impact.py import engine/chronicle/schema.py at module
# level (the schema.SOURCES tie-break for the family-fair glance), so schema.py
# rides into the same import cache through impact: a deploy that changed the
# sources, families or row contract would otherwise leave the panel scoring
# against the old schema. The closure test
# (tests/test_deploy_update_self_heal.py) derives this; keep the two in step.
# The entitlement console lazily imports app.billing, whose plan/features
# catalog is cached for the process lifetime. Catalog and billing-writer changes
# must reload this separate issuer process as well as macro-api. The admin unit
# generation forces the initial adoption even when the installed updater began
# this cycle with the previous trigger. No entitlement rows are changed here.
# The retained GSC card imports seo_search_console and its seo_director
# classifier on request. Both stay in sys.modules after that request, so
# native builder/classifier updates must reload the panel as well. Data
# artifacts still read per request and never trigger a restart.
# A1 caches the qledger read stack and derived theme tokens.
# Preserve the current-main serving closure and A1 cached closure as an exact union.
if [ "$ADMIN_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(admin/.*|app/billing\.py|config/plans\.yml|lib/(ai_costs|mastermind_response_log|project_runtime_state|tiers)\.py|lib/dataos/(__init__|identity|nulls|price|price_views|quality|read_contract|registry|temporal)\.py|engine/(codex_provider|llm_auth|macro_thesis|prophet_integrity|intelligence_registry|output_health)\.py|engine/research_codegen/(__init__|accounting_contract|admission|bridge|contracts|evaluation|input_contract|output_contract)\.py|engine/codex_lane/runner\.py|engine/chronicle/(impact|schema)\.py|engine/neuralweb/(key_pool|ask_brain|support_map|orchestrator_log|trade_memory)\.py|engine/metabolism/(throttle|budget_gate)\.py|engine/marketing/(__init__|accounts|ad_allocator|ad_arena|ad_central|ad_stats|approval_desk|authority|cadence_resolver|charter|claims|cmo|cold_read|copywriter|departments|economics|events|ledgers|market_clock|media_publish|opportunity_bus|outbox|personas|publication|rejections|blind_identity|health_monitor|labels|learned_rules|reply_critics|reply_discovery|reply_drafter|reply_export|reply_producer|reply_queue|reply_voice|rewrite|sentinel|seo_director|seo_search_console|social_publisher|state|story_lock|wire_routing)\.py|engine/press/(__init__|desk_planner)\.py|scripts/(marketing_publisher|build_intelligence_registry|build_output_health)\.py|admin/.*|templates/theme\.css|app/billing\.py|config/plans\.yml|lib/(ai_costs|mastermind_response_log|project_runtime_state|tiers|cn_calendar|hk_calendar|nyse_calendar|exchange_holidays)\.py|lib/dataos/(__init__|identity|nulls|price|price_views|quality|read_contract|registry|temporal)\.py|engine/(codex_provider|llm_auth|macro_thesis|prophet_integrity|intelligence_registry|output_health|qledger|qledger_store|qledger_validity|qledger_desk_adapter|qledger_evidence_clock|session_anchor|ticker_shape)\.py|engine/codex_lane/runner\.py|engine/chronicle/(impact|schema)\.py|engine/neuralweb/(key_pool|ask_brain|support_map|orchestrator_log|trade_memory)\.py|engine/metabolism/(throttle|budget_gate)\.py|engine/marketing/(__init__|accounts|ad_allocator|ad_arena|ad_central|ad_stats|approval_desk|authority|cadence_resolver|charter|claims|cmo|cold_read|copywriter|departments|economics|events|ledgers|market_clock|media_publish|opportunity_bus|outbox|personas|publication|rejections|blind_identity|health_monitor|labels|learned_rules|reply_critics|reply_discovery|reply_drafter|reply_export|reply_producer|reply_queue|reply_voice|rewrite|sentinel|seo_director|seo_search_console|social_publisher|state|story_lock|wire_routing)\.py|engine/press/(__init__|desk_planner)\.py|scripts/(marketing_publisher|build_intelligence_registry|build_output_health|grade_qledger)\.py)$'; then
	systemctl is-enabled admin >/dev/null 2>&1 && systemctl restart admin || true
fi


# BEGIN W2C_RUNTIME_ATTESTATION
MARKET_MEMORY_EXPERIENCE_RUN_NEEDED=0
MARKET_MEMORY_EXPERIENCE_INSTALLATION_REQUIRED=0
MARKET_MEMORY_EXPERIENCE_ATTESTED=0
if [ ! -e "$MARKET_MEMORY_EXPERIENCE_INSTALLATION" ] && \
   [ ! -L "$MARKET_MEMORY_EXPERIENCE_INSTALLATION" ]; then
	MARKET_MEMORY_EXPERIENCE_INSTALLATION_REQUIRED=1
	MARKET_MEMORY_EXPERIENCE_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_EXPERIENCE_UNIT_UPDATED" -eq 1 ] || \
   echo "$CHANGED" | grep -qE "$MARKET_MEMORY_EXPERIENCE_RUNTIME_REGEX"; then
	MARKET_MEMORY_EXPERIENCE_RUN_NEEDED=1
fi
MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE=0
w2c_terminal_ledger_state || MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE=$?
if [ "$MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE" -eq 0 ]; then
	if ! w2c_verify_installation; then
		echo "macro-update: terminal W2C ledger has no authentic installation receipt" >&2
		freeze_w2c_lane "terminal W2C ledger has no authentic installation receipt"
	fi
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
		MARKET_MEMORY_EXPERIENCE_RUN_NEEDED=0
	fi
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && \
	   [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ] && ! w2c_reconcile_timer; then
		echo "macro-update: authenticated terminal W2C timer disarm failed" >&2
		freeze_w2c_lane "authenticated terminal W2C timer disarm failed"
	fi
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && \
	   [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
		MARKET_MEMORY_EXPERIENCE_ATTESTED=1
	fi
elif [ "$MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE" -ne 3 ]; then
	echo "macro-update: W2C terminal ledger is invalid" >&2
	freeze_w2c_lane "W2C terminal ledger is invalid"
fi
if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && \
   [ "$MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE" -eq 3 ] && \
   [ "$MARKET_MEMORY_EXPERIENCE_INSTALLATION_REQUIRED" -eq 0 ] && \
   ! w2c_verify_installation; then
	echo "macro-update: existing W2C installation receipt failed authentication" >&2
	freeze_w2c_lane "existing W2C installation receipt failed authentication"
fi
if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && \
   [ "$MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE" -eq 3 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring W2C replay and attestation until reciprocal boundary closure" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: W2C attestation unavailable — shared runtime dependencies are not current" >&2
		freeze_w2c_lane "W2C attestation unavailable — shared runtime dependencies are not current"
	else
		W2C_OWNER_REPLAY_READY=0
		if [ "$MARKET_MEMORY_EXPERIENCE_RUN_NEEDED" -eq 1 ] || \
		   ! systemctl is-enabled macro-market-memory-experience.timer >/dev/null 2>&1 || \
		   ! systemctl is-active macro-market-memory-experience.timer >/dev/null 2>&1; then
			if ! w2c_start_owner_chain; then
				echo "macro-update: refusing W2C activation before owner replay completion" >&2
				freeze_w2c_lane "refusing W2C activation before owner replay completion"
			else
				W2C_OWNER_REPLAY_READY=1
			fi
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && \
		   [ "$MARKET_MEMORY_EXPERIENCE_RUN_NEEDED" -eq 1 ] && \
		   ! systemctl start macro-market-memory-experience.service; then
			echo "macro-update: W2C accrual failed before deployment attestation" >&2
			freeze_w2c_lane "W2C accrual failed before deployment attestation"
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && ! w2c_verify_installation; then
			echo "macro-update: W2C installation attestation failed after replay" >&2
			freeze_w2c_lane "W2C installation attestation failed after replay"
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && ! w2c_reconcile_timer; then
			echo "macro-update: W2C timer reconciliation failed" >&2
			freeze_w2c_lane "W2C timer reconciliation failed"
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
			MARKET_MEMORY_EXPERIENCE_ATTESTED=1
		fi
	fi
fi
# END W2C_RUNTIME_ATTESTATION
# Everything from here through W1B5_TIMER_FINALIZATION depends on an
# authenticated W2C state (the API-fence note below: a W2C refusal must not
# reach it), so a frozen W2C lane skips it exactly as the old `exit 1` did.
if [ "$W2C_LANE_FROZEN" -eq 0 ]; then

# First admitted production-record writer: network-dark, credential-free, and
# confined to one private store. It can read only the committed owner ledger;
# it cannot see other Market Memory state, the API, Prophet, or credential
# paths. Historical owner rows remain explicitly pre-activation in the record
# contract, while the same immutable lane captures future rows on arrival.
MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_UPDATED=0
MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-production-records.service"
	"$APP_DIR/app/deploy/macro-market-memory-production-records.timer"
)
if ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_SOURCES[0]}" /etc/systemd/system/macro-market-memory-production-records.service || \
   ! mm_reviewed_unit_file_ready "${MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_SOURCES[1]}" /etc/systemd/system/macro-market-memory-production-records.timer; then
	unit_repair_inputs_safe "${MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe production-record unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				[ ! -L "/etc/systemd/system/$UNIT" ] || {
					echo "macro-update: refusing symlinked unit $UNIT" >&2
					exit 1
				}
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
				systemctl restart macro-market-memory-production-records.timer 2>/dev/null || true
			fi
			RECONCILED=1
			echo "macro-update: Market Memory production-record units updated"
		fi
	else
		echo "macro-update: refusing Market Memory production-record unit update — systemd-analyze verify failed" >&2
	fi
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 0 ]; then
	systemctl enable --now macro-market-memory-production-records.timer >/dev/null 2>&1 || \
		echo "macro-update: macro-market-memory-production-records.timer could not be enabled" >&2
fi

MARKET_MEMORY_PRODUCTION_RECORDS_RUN_NEEDED=0
if [ "$MARKET_MEMORY_PRODUCTION_RECORDS_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(scripts/capture_market_memory_options_episodes\.py|engine/options_signal_episode\.py|engine/neuralweb/market_memory_production_records\.py|contracts/market_memory/options_signal_episode_production_record\.v1\.schema\.json|contracts/options/options\.signal_episode\.v1\.schema\.json|lib/nyse_calendar\.py|data/options_signal_episode/episodes\.jsonl)$'; then
	MARKET_MEMORY_PRODUCTION_RECORDS_RUN_NEEDED=1
fi
if [ "$MARKET_MEMORY_PRODUCTION_RECORDS_RUN_NEEDED" -eq 1 ]; then
	if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ]; then
		echo "macro-update: deferring Market Memory production-record capture until reciprocal boundary attestation" >&2
	elif [ "$API_DEPS_OK" -ne 1 ]; then
		echo "macro-update: deferring Market Memory production-record capture — shared runtime dependencies are not current" >&2
	elif ! systemctl start macro-market-memory-production-records.service; then
		echo "macro-update: Market Memory production-record capture failed closed; nightly timer will retry" >&2
	fi
fi

# W1B.5 private, future-only option-OI endpoint availability canary. It makes
# exactly one bounded first-page request with a systemd credential, follows no
# pagination, and never constructs a chain, identity, OI state, GEX, replay
# input, or trading feature. The separate service identity and store root keep
# credentialed response evidence outside every existing Market Memory writer
# and the API namespace.
MARKET_MEMORY_OPTIONS_UNIT_UPDATED=0
OPTIONS_UNITS_READY=0
MARKET_MEMORY_OPTIONS_UNIT_SOURCES=(
	"$APP_DIR/app/deploy/macro-market-memory-options.service"
	"$APP_DIR/app/deploy/macro-market-memory-options.timer"
)
if ! mm_reviewed_unit_file_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[0]}" \
	/etc/systemd/system/macro-market-memory-options.service || \
   ! mm_reviewed_unit_file_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[1]}" \
	/etc/systemd/system/macro-market-memory-options.timer; then
	disarm_options_timer
	unit_repair_inputs_safe "${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[@]}" || {
		echo "macro-update: refusing unsafe option-OI unit repair input" >&2
		exit 1
	}
	if systemd-analyze verify "${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[@]}"; then
		for UNIT_SOURCE in "${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! mm_reviewed_unit_file_ready "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				MARKET_MEMORY_OPTIONS_UNIT_UPDATED=1
			fi
		done
		if [ "$MARKET_MEMORY_OPTIONS_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			RECONCILED=1
			echo "macro-update: Market Memory option-OI canary units updated"
		fi
	else
		echo "macro-update: refusing option-OI unit update — systemd-analyze verify failed" >&2
	fi
fi
if mm_reviewed_unit_file_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[0]}" \
	/etc/systemd/system/macro-market-memory-options.service && \
   mm_reviewed_unit_file_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[1]}" \
	/etc/systemd/system/macro-market-memory-options.timer && \
   { ! mm_loaded_unit_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[0]}" \
	/etc/systemd/system/macro-market-memory-options.service \
	macro-market-memory-options.service || \
     ! mm_loaded_unit_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[1]}" \
	/etc/systemd/system/macro-market-memory-options.timer \
	macro-market-memory-options.timer; }; then
	disarm_options_timer
	systemctl daemon-reload
fi
if mm_loaded_unit_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[0]}" \
	/etc/systemd/system/macro-market-memory-options.service \
	macro-market-memory-options.service && \
   mm_loaded_unit_ready \
	"${MARKET_MEMORY_OPTIONS_UNIT_SOURCES[1]}" \
	/etc/systemd/system/macro-market-memory-options.timer \
	macro-market-memory-options.timer; then
	OPTIONS_UNITS_READY=1
else
	disarm_options_timer
	echo "macro-update: option-OI effective units are not reviewed/current" >&2
fi

MARKET_MEMORY_OPTIONS_RUN_NEEDED=0
if [ "$OPTIONS_UNITS_READY" -eq 1 ] && { \
	[ "$MARKET_MEMORY_OPTIONS_UNIT_UPDATED" -eq 1 ] || \
	grep -qE "$OPTIONS_RUNTIME_CLOSURE_REGEX" <<<"$CHANGED" || \
	[ "$OPTIONS_TIMER_WAS_ENABLED" -eq 0 ]; \
}; then
	MARKET_MEMORY_OPTIONS_RUN_NEEDED=1
fi

# Consume the API fence minted with the earlier restart transaction. Do not
# rewrite it here: a W2C exit 1 must not reach this block, and the marker
# already attests the verified PID.
OPTIONS_API_FENCE_READY=0
if mm_api_fence_marker_ready && \
   [ "$API_UNIT_READY" -eq 1 ] && \
   [ "$(systemctl show -p NeedDaemonReload --value macro-api)" = no ] && \
   cmp -s "$APP_DIR/app/deploy/macro-api.service" /etc/systemd/system/macro-api.service && \
   grep -Fxq 'InaccessiblePaths=/var/lib/macro-market-memory-options' /etc/systemd/system/macro-api.service && \
   grep -Fxq 'InaccessiblePaths=/etc/macro-market-memory-options' /etc/systemd/system/macro-api.service; then
	OPTIONS_API_FENCE_READY=1
else
	rm -f "$OPTIONS_API_FENCE_MARKER"
fi

RECIPROCAL_UNITS_READY=0
if reciprocal_market_memory_units_ready; then
	RECIPROCAL_UNITS_READY=1
fi
if [ "$RECIPROCAL_UNITS_READY" -ne 1 ]; then
	disarm_options_timer
	stop_reciprocal_market_memory_writers
	echo "macro-update: reciprocal Market Memory units are not reviewed/current" >&2
fi

if [ "$OPTIONS_API_FENCE_READY" -eq 1 ] && \
   [ "$RECIPROCAL_UNITS_READY" -eq 1 ] && \
   [ "$OPTIONS_UNITS_READY" -eq 1 ]; then
	OPTIONS_STATUS=0
	bash "$APP_DIR/app/deploy/market-memory-options-prereqs.sh" \
		--check-ready >/dev/null 2>&1 || OPTIONS_STATUS=$?
	if [ "$OPTIONS_STATUS" -eq 0 ]; then
		OPTIONS_CREDENTIAL_READY=1
	else
		disarm_options_timer
		if bash "$APP_DIR/app/deploy/market-memory-options-prereqs.sh"; then
			OPTIONS_CREDENTIAL_READY=1
		else
			OPTIONS_STATUS=$?
			if [ "$OPTIONS_STATUS" -ne 2 ]; then
				echo "macro-update: option-OI private-root provisioning failed" >&2
				exit "$OPTIONS_STATUS"
			fi
			echo "macro-update: option-OI credential absent; lane remains disarmed" >&2
		fi
	fi
else
	echo "macro-update: option-OI private state not provisioned before API fence" >&2
fi

# Publish the reciprocal receipt only after the exact loaded units have been
# re-attested. If this tick paused them, no old-namespace process is alive; any
# later timer/service start therefore inherits the reviewed reciprocal denies.
if [ "$RECIPROCAL_UNITS_READY" -eq 1 ] && \
   [ "$OPTIONS_DEFER_REARM_FOR_SELF_UPDATE" -eq 0 ]; then
	mm_write_reciprocal_fence_marker
else
	rm -f "$OPTIONS_RECIPROCAL_FENCE_MARKER"
fi

OPTIONS_BOUNDARY_READY=0
if [ "$OPTIONS_CREDENTIAL_READY" -eq 1 ] && [ "$OPTIONS_UNITS_READY" -eq 1 ] && \
   [ "$OPTIONS_API_FENCE_READY" -eq 1 ] && [ "$RECIPROCAL_UNITS_READY" -eq 1 ] && \
   mm_reciprocal_fence_marker_ready && \
   [ "$OPTIONS_DEFER_REARM_FOR_SELF_UPDATE" -eq 0 ]; then
	OPTIONS_BOUNDARY_READY=1
fi

# BEGIN W1B5_TIMER_FINALIZATION
if [ "$OPTIONS_BOUNDARY_READY" -eq 1 ]; then
	# A deploy-triggered smoke capture happens once and before timer arming.  A
	# failed first capture is retried only by the weekday timer, never every
	# three-minute updater tick.
	if [ "$MARKET_MEMORY_OPTIONS_RUN_NEEDED" -eq 1 ]; then
		if [ "$API_DEPS_OK" -ne 1 ]; then
			echo "macro-update: deferring option-OI canary — shared runtime dependencies are not current" >&2
		elif ! systemctl start macro-market-memory-options.service; then
			echo "macro-update: option-OI capture failed closed; weekday timer will retry" >&2
		fi
	fi
	if [ "$OPTIONS_TIMER_WAS_ENABLED" -eq 0 ] || \
	   [ "$OPTIONS_TIMER_WAS_ACTIVE" -eq 0 ] || \
	   [ "$OPTIONS_TIMER_DISARMED" -eq 1 ]; then
		# The historical latch no longer describes current state once an enable
		# attempt begins.  Reset it so a partial enable failure is forcibly undone.
		OPTIONS_TIMER_DISARMED=0
		if ! systemctl enable --now macro-market-memory-options.timer >/dev/null 2>&1 || \
		   ! systemctl is-enabled macro-market-memory-options.timer >/dev/null 2>&1 || \
		   ! systemctl is-active macro-market-memory-options.timer >/dev/null 2>&1; then
			disarm_options_timer
			echo "macro-update: macro-market-memory-options.timer could not be enabled" >&2
		fi
	fi
else
	disarm_options_timer
	echo "macro-update: option-OI lane remains disarmed until units, credential, and API fence are verified" >&2
fi
if [ "$RECIPROCAL_TIMERS_PAUSED" -eq 1 ] && \
   [ "$RECIPROCAL_UNITS_READY" -eq 1 ] && \
   [ "$OPTIONS_DEFER_REARM_FOR_SELF_UPDATE" -eq 0 ]; then
	# A deploy in W2C's 04:30-04:45Z window must never seal stale pre-deploy
	# owner heads. Replay the dependency chain synchronously and in order; a
	# oneshot `systemctl start` returns only after that owner has completed.
	# BEGIN W2C_DEFERRED_REPLAY
	W2C_OWNER_REPLAY_READY=0
	if [ "$MARKET_MEMORY_EXPERIENCE_TERMINAL_STATE" -eq 3 ]; then
		if [ "$API_DEPS_OK" -ne 1 ]; then
			echo "macro-update: refusing deferred W2C attestation with stale dependencies" >&2
			freeze_w2c_lane "refusing deferred W2C attestation with stale dependencies"
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && ! w2c_start_owner_chain; then
			echo "macro-update: refusing deferred W2C activation before owner replay completion" >&2
			freeze_w2c_lane "refusing deferred W2C activation before owner replay completion"
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
			W2C_OWNER_REPLAY_READY=1
		fi
		if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && \
		   [ "$MARKET_MEMORY_EXPERIENCE_RUN_NEEDED" -eq 1 ] && \
		   ! systemctl start macro-market-memory-experience.service; then
			echo "macro-update: deferred W2C accrual failed before attestation" >&2
			freeze_w2c_lane "deferred W2C accrual failed before attestation"
		fi
	fi
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ] && ! w2c_verify_installation; then
		echo "macro-update: deferred W2C installation attestation failed" >&2
		freeze_w2c_lane "deferred W2C installation attestation failed"
	fi
	# END W2C_DEFERRED_REPLAY
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
		for RECIPROCAL_PROFILE in source source-spy-rest context identity breadth technicals technicals-v2 experience-v2 production-records options-context-audit; do
			if [ -e "/etc/systemd/system/macro-market-memory-$RECIPROCAL_PROFILE.timer" ]; then
				if [ "$RECIPROCAL_PROFILE" = production-records ] || [ "$RECIPROCAL_PROFILE" = options-context-audit ]; then
					systemctl enable --now "macro-market-memory-$RECIPROCAL_PROFILE.timer" || true
				else
					systemctl start "macro-market-memory-$RECIPROCAL_PROFILE.timer" || true
				fi
			fi
		done
		if ! w2c_reconcile_timer; then
			echo "macro-update: W2C timer reconciliation failed" >&2
			freeze_w2c_lane "W2C timer reconciliation failed"
		fi
	fi
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
		MARKET_MEMORY_EXPERIENCE_ATTESTED=1
		# The production-record first run was intentionally deferred while the
		# reciprocal namespace was stopped. Capture immediately after the reviewed
		# units are re-armed; do not wait for the next nightly calendar edge.
		if [ "$MARKET_MEMORY_PRODUCTION_RECORDS_RUN_NEEDED" -eq 1 ]; then
			if [ "$API_DEPS_OK" -ne 1 ]; then
				echo "macro-update: deferring Market Memory production-record capture — shared runtime dependencies are not current" >&2
			elif ! systemctl start macro-market-memory-production-records.service; then
				echo "macro-update: Market Memory production-record capture failed closed; nightly timer will retry" >&2
			fi
		fi
	fi
fi
if [ "${MARKET_MEMORY_EXPERIENCE_ATTESTED:-1}" -ne 1 ]; then
	if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
		echo "macro-update: W2C installation and terminal state were not authenticated" >&2
		freeze_w2c_lane "W2C installation and terminal state were not authenticated"
	fi
fi
# A frozen W2C lane leaves OPTIONS_RECONCILIATION_COMPLETE=0, so the EXIT trap
# stays armed: any later failure still fails closed with the option-OI timer
# disarmed, and the final exit re-runs a latched (no-op) disarm.
if [ "${W2C_LANE_FROZEN:-0}" -eq 0 ]; then
	OPTIONS_RECONCILIATION_COMPLETE=1
	trap - EXIT
fi
# END W1B5_TIMER_FINALIZATION
fi
# BEGIN W2C_LANE_FROZEN_CONTINUE
# The old `exit 1` disarmed the option-OI timer through the EXIT trap at the
# moment W2C refused.  Do the same disarm now, before any lane-independent step
# runs; if it fails, keep the old abort (the trap retries the disarm).
if [ "${W2C_LANE_FROZEN:-0}" -eq 1 ]; then
	if ! disarm_options_timer; then
		echo "macro-update: W2C lane frozen but option-OI disarm failed; aborting deploy" >&2
		exit 1
	fi
	echo "macro-update: W2C lane frozen — $W2C_LANE_FROZEN_REASON; continuing lane-independent deploy steps" >&2
fi
# END W2C_LANE_FROZEN_CONTINUE

# The fixed fast/snapshot/bars definitions are reconciled by
# LIVE_SOURCE_TRANSACTION before reset, including no-change repair ticks.
# Their independent timer intents are already restored; do not restart them here.

# PROPHET LIVE evaluator lane (research/PROPHET_LIVE_INTRADAY_SIGNALS_MASTERPLAN_BY_FABLE.md
# §4.2a). Its own block, not a fourth entry in the list above, for two reasons: the
# three lanes there are ONE orchestrator invoked with three --lane arguments, and
# widening that regex would restart all three timers whenever this unrelated unit
# changed. Same narrow allow-list discipline — exactly the two paths this lane owns.
#
# Unlike the block above it also arms itself, because go-live for this program is a
# REPO COMMIT and nothing else: the unit did not exist when live-setup.sh was last run
# on the box, so a CHANGED-only trigger would install a timer that nobody ever enables.
# `enable --now` on an already-enabled, already-active timer is a systemd no-op, and
# the absent-file clause makes the block self-healing when an earlier tick's
# systemd-analyze failed or an operator removed the unit (macro-update installing it
# twice must be, and is, a no-op).
#
# The live plane must already exist (macro-live-fast.timer enabled): this lane reads
# what those lanes publish, so on any host without them it would have nothing to read.
# That guard is also what keeps this block inert on a box that is not the VPS.
#
# The .service is NEVER restarted. It is a oneshot — `systemctl restart` would RUN a
# pass out of band, off the ET-windowed schedule, with the R2 debounce predecessor
# from whenever the last legitimate tick was. Only the timer is (re)armed.
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/macro-live-prophet\.(service|timer)$' || \
     [ ! -f /etc/systemd/system/macro-live-prophet.timer ]; }; then
	PROPHET_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-live-prophet.service"
		"$APP_DIR/app/deploy/macro-live-prophet.timer"
	)
	if systemd-analyze verify "${PROPHET_UNIT_SOURCES[@]}"; then
		PROPHET_UNIT_UPDATED=0
		for UNIT_SOURCE in "${PROPHET_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				PROPHET_UNIT_UPDATED=1
			fi
		done
		if [ "$PROPHET_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-live-prophet.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-live-prophet units updated"
		fi
		systemctl enable --now macro-live-prophet.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-live-prophet.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-live-prophet unit update — systemd-analyze verify failed" >&2
	fi
fi

# LIVE BREADTH lane (docs/live_breadth_runbook.md). Own block, same narrow
# allow-list and self-arming contract as the prophet block above: go-live is a
# REPO COMMIT, and the unit did not exist when live-setup.sh was last run on the
# box, so a CHANGED-only trigger would install a timer nobody ever enables and
# the producer would stay dark exactly as it was before this lane existed.
#
# This block is what makes live breadth OWNED. Before it, live-setup.sh armed
# five lanes and none of them was breadth, while VPS_LIVE_PRIMARY=true disabled
# the GitHub backstop — so the only repo-managed producer was switched off and
# its replacement was never installed. An operator re-running live-setup.sh by
# hand is not ownership; this is.
#
# The .service is NEVER restarted: it is a oneshot (`--once --publish`), so a
# restart would burn a Polygon snapshot out of band, off the windowed schedule
# and outside the one-snapshot-per-cycle entitlement the lane is built around.
# Only the timer is (re)armed.
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/macro-live-breadth\.(service|timer)$' || \
     [ ! -f /etc/systemd/system/macro-live-breadth.timer ]; }; then
	BREADTH_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-live-breadth.service"
		"$APP_DIR/app/deploy/macro-live-breadth.timer"
	)
	if systemd-analyze verify "${BREADTH_UNIT_SOURCES[@]}"; then
		BREADTH_UNIT_UPDATED=0
		for UNIT_SOURCE in "${BREADTH_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				BREADTH_UNIT_UPDATED=1
			fi
		done
		if [ "$BREADTH_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-live-breadth.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-live-breadth units updated"
		fi
		systemctl enable --now macro-live-breadth.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-live-breadth.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-live-breadth unit update — systemd-analyze verify failed" >&2
	fi
fi

# CN PROPHET LIVE lane (CN-PR-1). Own block — a widened regex would restart the
# US prophet timer whenever this unit changed. Same self-arming contract: go-live
# is a REPO COMMIT, so a CHANGED-only trigger would install a timer nobody ever
# enables. The live-fast guard marks the serving VPS. The .service is NEVER
# restarted (oneshot — that would run a pass off the CST-windowed schedule).
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/macro-live-cnprophet\.(service|timer)$' || \
     [ ! -f /etc/systemd/system/macro-live-cnprophet.timer ]; }; then
	CNPROPHET_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-live-cnprophet.service"
		"$APP_DIR/app/deploy/macro-live-cnprophet.timer"
	)
	if systemd-analyze verify "${CNPROPHET_UNIT_SOURCES[@]}"; then
		CNPROPHET_UNIT_UPDATED=0
		for UNIT_SOURCE in "${CNPROPHET_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				CNPROPHET_UNIT_UPDATED=1
			fi
		done
		if [ "$CNPROPHET_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-live-cnprophet.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-live-cnprophet units updated"
		fi
		systemctl enable --now macro-live-cnprophet.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-live-cnprophet.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-live-cnprophet unit update — systemd-analyze verify failed" >&2
	fi
fi

# CLOSE-PASS MIRROR lane (W-L1a). Its own block for the same reason the Prophet
# block is separate: a widened regex would restart unrelated timers whenever this
# unit changed. Same self-arming contract — go-live for this lane is a REPO COMMIT
# and nothing else, so a CHANGED-only trigger would install a timer nobody ever
# enables, and the absent-file clause self-heals a failed verify or an operator
# removal. The live-fast guard marks the serving VPS and keeps the block inert
# everywhere else.
#
# The .service is NEVER restarted — it is a oneshot, and `systemctl restart` would
# RUN a mirror pass out of band. Only the timer is (re)armed.
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/macro-live-closepass\.(service|timer)$' || \
     [ ! -f /etc/systemd/system/macro-live-closepass.timer ]; }; then
	CLOSEPASS_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-live-closepass.service"
		"$APP_DIR/app/deploy/macro-live-closepass.timer"
	)
	if systemd-analyze verify "${CLOSEPASS_UNIT_SOURCES[@]}"; then
		CLOSEPASS_UNIT_UPDATED=0
		for UNIT_SOURCE in "${CLOSEPASS_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				CLOSEPASS_UNIT_UPDATED=1
			fi
		done
		if [ "$CLOSEPASS_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-live-closepass.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-live-closepass units updated"
		fi
		systemctl enable --now macro-live-closepass.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-live-closepass.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-live-closepass unit update — systemd-analyze verify failed" >&2
	fi
fi

# FRESHNESS SENTINEL — the dead-man switch that must live OUTSIDE GitHub
# (masterplan W1). Same self-arming contract as the Prophet block above and for
# the same reason: go-live is a REPO COMMIT — the unit did not exist when
# live-setup.sh last ran, so a CHANGED-only trigger would install a timer nobody
# ever enables. The live-fast guard marks the serving VPS (the box this watch
# must run on) and keeps the block inert everywhere else. `enable --now` on an
# already-enabled timer is a systemd no-op; the absent-file clause self-heals an
# earlier failed verify or an operator removal.
#
# The .service is NEVER restarted — it is a oneshot; only the timer is (re)armed.
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/macro-sentinel\.(service|timer)$' || \
     [ ! -f /etc/systemd/system/macro-sentinel.timer ]; }; then
	SENTINEL_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-sentinel.service"
		"$APP_DIR/app/deploy/macro-sentinel.timer"
	)
	if systemd-analyze verify "${SENTINEL_UNIT_SOURCES[@]}"; then
		SENTINEL_UNIT_UPDATED=0
		for UNIT_SOURCE in "${SENTINEL_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				SENTINEL_UNIT_UPDATED=1
			fi
		done
		if [ "$SENTINEL_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-sentinel.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-sentinel units updated"
		fi
		systemctl enable --now macro-sentinel.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-sentinel.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-sentinel unit update — systemd-analyze verify failed" >&2
	fi
fi

# LIVE ENTRY RADAR lanes — the pre-open pack builder and the 5-min RTH evaluator
# (research/live_entry_radar/W4_LIVE_EVALUATOR_DESIGN.md §3b, W4_DEPLOY_PLAN.md).
# Four units in ONE block because they are one program: they go live together, they
# share a cap set, and a session evaluated against a pack built by a different code
# version is exactly the thing pack_hash exists to refuse.
#
# THE ARM GATE IS WHAT MAKES THIS BLOCK DIFFERENT FROM THE FOUR ABOVE. For Prophet,
# close-pass and the sentinel, go-live is a REPO COMMIT and nothing else. For this
# program the commissioning drew the deployment boundary at ACTIVATION (design §3b:
# build + validate, no autonomous production service state), so go-live is an
# explicit OPERATOR act — `ENTRY_RADAR_LIVE_ENABLE=1` in /etc/macro-live.env — and
# the merge alone must leave the box exactly as it found it. The code path is still
# the house self-arming shape: once the flag is set, the next macro-update tick
# installs, verifies, enables and heals with no further operator step, and the
# absent-file clause self-heals a failed verify or a removed unit.
#
# ENTRY_RADAR_LIVE_ENABLE is read by GREP, not by sourcing. update.sh reads no env
# file anywhere else and runs under `set -euo pipefail` as root: sourcing an
# operator-edited file here would execute whatever is in it, inside this script's
# shell, with its `set -e` semantics — a deploy script that can be killed (or worse)
# by a stray line in an unrelated env file. The `|| true` is load-bearing for the
# same reason: under pipefail an unmatched grep is exit 1, which `set -e` would take
# as a fatal error on the ordinary unarmed path.
#
# The ARM CHECK SITS OUTSIDE THE CHANGED TRIGGER, deliberately. A disarm has to work
# on a tick where nothing changed at all: the operator's rollback is to DELETE the
# env line, which touches no repo file, so a CHANGED-gated block would never notice
# and the timers would run on forever. So the structure is: live-plane guard →
# armed? → (CHANGED or absent) install/enable : disarm-if-installed. Only the INSTALL
# half is CHANGED-gated; both arm directions are evaluated every pass.
#
# The .service files are NEVER restarted. They are oneshots — `systemctl restart`
# would RUN a pass out of band: an evaluator pass outside the ET window against a
# stale pack, or a pack build mid-session that the stale-pack gate would then have to
# refuse. Only the timers are (re)armed.
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1; then
	ENTRY_RADAR_ARM=$(grep -E '^ENTRY_RADAR_LIVE_ENABLE=' /etc/macro-live.env 2>/dev/null \
		| tail -1 | cut -d= -f2- | tr -d "\"'[:space:]" || true)
	if [ "${ENTRY_RADAR_ARM:-}" = "1" ]; then
		if echo "$CHANGED" | grep -qE '^(app/deploy/macro-(live-entry-radar|entry-radar-pack)\.(service|timer)|scripts/entry_radar_live(_pack)?\.py|engine/entry_radar/live_.*\.py)$' || \
		   [ ! -f /etc/systemd/system/macro-live-entry-radar.timer ] || \
		   [ ! -f /etc/systemd/system/macro-entry-radar-pack.timer ]; then
			ENTRY_RADAR_UNIT_SOURCES=(
				"$APP_DIR/app/deploy/macro-live-entry-radar.service"
				"$APP_DIR/app/deploy/macro-live-entry-radar.timer"
				"$APP_DIR/app/deploy/macro-entry-radar-pack.service"
				"$APP_DIR/app/deploy/macro-entry-radar-pack.timer"
			)
			if systemd-analyze verify "${ENTRY_RADAR_UNIT_SOURCES[@]}"; then
				ENTRY_RADAR_UNIT_UPDATED=0
				for UNIT_SOURCE in "${ENTRY_RADAR_UNIT_SOURCES[@]}"; do
					UNIT=$(basename "$UNIT_SOURCE")
					if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
						install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
						ENTRY_RADAR_UNIT_UPDATED=1
					fi
				done
				if [ "$ENTRY_RADAR_UNIT_UPDATED" -eq 1 ]; then
					systemctl daemon-reload
					systemctl restart macro-live-entry-radar.timer macro-entry-radar-pack.timer 2>/dev/null || true
					RECONCILED=1
					echo "macro-update: entry-radar units updated"
				fi
				systemctl enable --now macro-live-entry-radar.timer macro-entry-radar-pack.timer >/dev/null 2>&1 || \
					echo "macro-update: entry-radar timers could not be enabled" >&2
			else
				echo "macro-update: refusing entry-radar unit update — systemd-analyze verify failed" >&2
			fi
		fi
	else
		echo "macro-update: entry-radar: staged, not armed (ENTRY_RADAR_LIVE_ENABLE unset)"
		# SYMMETRIC DISARM. Rollback is "remove the env line", so the block that
		# arms on a flag must also stand the lane down when the flag goes away —
		# otherwise the only rollback is a manual systemctl call the deploy plan
		# does not describe. `disable --now` both stops the running timer and
		# removes the timers.target wants link, so a reboot does not resurrect it.
		if [ -f /etc/systemd/system/macro-live-entry-radar.timer ] || \
		   [ -f /etc/systemd/system/macro-entry-radar-pack.timer ]; then
			systemctl disable --now macro-live-entry-radar.timer macro-entry-radar-pack.timer >/dev/null 2>&1 || true
			RECONCILED=1
			echo "macro-update: entry-radar: disarmed — both timers disabled and stopped"
		fi
	fi
fi

# MORNING ORIENTATION PREMARKET EDITION — A-MOR-2b lane B
# (DEC:MARKET-ONTOLOGY-MOR2B-PREMARKET-OWNER-AND-PLACEMENT-2026-09-24,
# research/market_intelligence_productization/MARKET_ONTOLOGY_F01_MOR2B_BUILD_PACKET_2026-09-24.md
# §3 B1–B3). The same producer that nightly `daily.yml` / `render.yml` already
# runs for `site/am_edition.{json,html}`; this unit runs a SECOND, lighter
# producer against the VPS live store during the ET premarket window so
# visitors see a fresh read between the prior close and 09:30 ET. Two writers,
# one overlay, freshest-wins (see scripts/am_edition_live.py:run decision (a)).
#
# NO ARM FLAG. The lane reads only files already on the box (`site/`, `data/`,
# the live `quotes.json` snapshot, the existing `market_packet` ladder) and
# writes only under the live store (`/var/lib/macro-live/public/am_edition.*`);
# it does NOT touch `data/`, does NOT spawn a workflow, and does NOT run git.
# A pre-open premarket refresh of the same page the nightly already writes is
# the highest-trust passive lane on the box — the merge alone is enough to
# install the timer. Stand-down is a separate operator act
# (`AM_EDITION_LIVE_DISABLE=1` in /etc/macro-live.env), symmetric to the
# entry-radar disarm: when the flag goes away the rollback removes the env
# line, which touches no repo file, so a CHANGED-gated block would never
# notice and the timer would run on forever. The disable side therefore
# evaluates every pass, independent of CHANGED.
#
# AM_EDITION_LIVE_DISABLE is read by GREP, not by sourcing — same reasoning as
# the entry-radar block above (update.sh reads no env file anywhere else and
# runs under `set -euo pipefail` as root; sourcing an operator-edited file
# here would execute whatever is in it, inside this script's shell, with its
# `set -e` semantics). The `|| true` is load-bearing: under pipefail an
# unmatched grep is exit 1, which `set -e` would take as a fatal error on the
# ordinary armed path.
#
# The .service is NEVER restarted. It is a oneshot — `systemctl restart`
# would RUN a premarket pass out of band: an evaluator pass outside the ET
# window against a stale bake, or a build mid-session that the freshest-wins
# gate would then have to refuse. Only the timer is (re)armed.
if systemctl is-enabled macro-live-fast.timer >/dev/null 2>&1; then
	AM_EDITION_DISABLE=$(grep -E '^AM_EDITION_LIVE_DISABLE=' /etc/macro-live.env 2>/dev/null \
		| tail -1 | cut -d= -f2- | tr -d "\"'[:space:]" || true)
	if [ "${AM_EDITION_DISABLE:-}" != "1" ]; then
		if echo "$CHANGED" | grep -qE '^(app/deploy/macro-am-edition\.(service|timer)|scripts/am_edition_live\.py|scripts/build_am_edition\.py)$' || \
		   [ ! -f /etc/systemd/system/macro-am-edition.timer ]; then
			AM_EDITION_UNIT_SOURCES=(
				"$APP_DIR/app/deploy/macro-am-edition.service"
				"$APP_DIR/app/deploy/macro-am-edition.timer"
			)
			if systemd-analyze verify "${AM_EDITION_UNIT_SOURCES[@]}"; then
				AM_EDITION_UNIT_UPDATED=0
				for UNIT_SOURCE in "${AM_EDITION_UNIT_SOURCES[@]}"; do
					UNIT=$(basename "$UNIT_SOURCE")
					if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
						install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
						AM_EDITION_UNIT_UPDATED=1
					fi
				done
				if [ "$AM_EDITION_UNIT_UPDATED" -eq 1 ]; then
					systemctl daemon-reload
					systemctl restart macro-am-edition.timer 2>/dev/null || true
					RECONCILED=1
					echo "macro-update: macro-am-edition units updated"
				fi
				systemctl enable --now macro-am-edition.timer >/dev/null 2>&1 || \
					echo "macro-update: macro-am-edition.timer could not be enabled" >&2
			else
				echo "macro-update: refusing macro-am-edition unit update — systemd-analyze verify failed" >&2
			fi
		fi
	else
		echo "macro-update: am-edition: staged, not armed (AM_EDITION_LIVE_DISABLE=1)"
		# SYMMETRIC DISARM. Rollback is "set the env line", so the block that
		# arms on a flag must also stand the lane down when the flag goes away —
		# otherwise the only rollback is a manual systemctl call the deploy plan
		# does not describe. `disable --now` both stops the running timer and
		# removes the timers.target wants link, so a reboot does not resurrect it.
		# The overlay files in the live store are removed in the same act so a
		# disabled timer never leaves a stale AM-edition page sitting on the wire
		# — the freshest-wins rule would re-publish on the next armed tick, but
		# during a disarm the visitor should see the canonical site/ copy
		# (the nightly's bake), not a VPS-only overlay the operator explicitly
		# told us to take down.
		if [ -f /etc/systemd/system/macro-am-edition.timer ]; then
			systemctl disable --now macro-am-edition.timer >/dev/null 2>&1 || true
			RECONCILED=1
			echo "macro-update: am-edition: disarmed — timer disabled and stopped"
		fi
		# Best-effort overlay removal — the live store may not exist on dev /
		# CI boxes; the || true keeps the block exit-0 on those paths.
		rm -f /var/lib/macro-live/public/am_edition.json \
		      /var/lib/macro-live/public/am_edition.html 2>/dev/null || true
	fi
fi

# CUSTOMER-TABLE BACKUP — MMX-001 / GATE-1. Same self-arming contract as the
# sentinel: go-live is a REPO COMMIT, so a CHANGED-only trigger would install a
# timer nobody ever enables. Gated on macro-api.service (the box that already
# holds Supabase + R2 env). The .service is a oneshot and is NEVER restarted;
# only the timer is (re)armed. Absent-file clause self-heals an earlier failed
# verify or an operator removal. The job fail-closes without
# BACKUP_ENCRYPTION_KEY — that is visible, not silent.
if systemctl is-enabled macro-api.service >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/macro-user-backup\.(service|timer)$' || \
     [ ! -f /etc/systemd/system/macro-user-backup.timer ]; }; then
	USER_BACKUP_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-user-backup.service"
		"$APP_DIR/app/deploy/macro-user-backup.timer"
	)
	if systemd-analyze verify "${USER_BACKUP_UNIT_SOURCES[@]}"; then
		USER_BACKUP_UNIT_UPDATED=0
		for UNIT_SOURCE in "${USER_BACKUP_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				USER_BACKUP_UNIT_UPDATED=1
			fi
		done
		if [ "$USER_BACKUP_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-user-backup.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-user-backup units updated"
		fi
		systemctl enable --now macro-user-backup.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-user-backup.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-user-backup unit update — systemd-analyze verify failed" >&2
	fi
fi

# GIT STORE MAINTENANCE — 2026-10-19 root-disk incident: every pull lands a new
# fetch pack and auto-gc is disabled on the box (gc.auto=0), so nothing ever
# consolidated them; /opt/macro/.git reached 41G in 263 packs and filled the
# root disk. Same self-arming contract as the backup timer above: gated on
# macro-api.service, re-armed when a source changes or an installed copy is
# absent. The script is installed BEFORE the units are verified because the
# service's ExecStart names the installed path (and a running maintenance
# keeps its old inode, as with this updater's own self-update). The .service
# is a oneshot and is never started from here; only the timer is (re)armed.
# The journald size cap rides the same block: without it the persistent
# journal may take 10% of the root filesystem.
if systemctl is-enabled macro-api.service >/dev/null 2>&1 && \
   { echo "$CHANGED" | grep -qE '^app/deploy/(macro-git-store-maintenance\.(sh|service|timer)|journald-macro-vps\.conf)$' || \
     [ ! -f /usr/local/sbin/macro-git-store-maintenance ] || \
     [ ! -f /etc/systemd/system/macro-git-store-maintenance.timer ] || \
     [ ! -f /etc/systemd/journald.conf.d/10-macro-vps-cap.conf ]; }; then
	GIT_MAINT_SOURCE="$APP_DIR/app/deploy/macro-git-store-maintenance.sh"
	GIT_MAINT_BIN=/usr/local/sbin/macro-git-store-maintenance
	if ! cmp -s "$GIT_MAINT_SOURCE" "$GIT_MAINT_BIN"; then
		if bash -n "$GIT_MAINT_SOURCE"; then
			install -m 0755 "$GIT_MAINT_SOURCE" "$GIT_MAINT_BIN"
			RECONCILED=1
			echo "macro-update: macro-git-store-maintenance script updated"
		else
			echo "macro-update: refusing macro-git-store-maintenance script update — bash -n failed" >&2
		fi
	fi
	GIT_MAINT_UNIT_SOURCES=(
		"$APP_DIR/app/deploy/macro-git-store-maintenance.service"
		"$APP_DIR/app/deploy/macro-git-store-maintenance.timer"
	)
	if [ -x "$GIT_MAINT_BIN" ] && systemd-analyze verify "${GIT_MAINT_UNIT_SOURCES[@]}"; then
		GIT_MAINT_UNIT_UPDATED=0
		for UNIT_SOURCE in "${GIT_MAINT_UNIT_SOURCES[@]}"; do
			UNIT=$(basename "$UNIT_SOURCE")
			if ! cmp -s "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"; then
				install -m 0644 "$UNIT_SOURCE" "/etc/systemd/system/$UNIT"
				GIT_MAINT_UNIT_UPDATED=1
			fi
		done
		if [ "$GIT_MAINT_UNIT_UPDATED" -eq 1 ]; then
			systemctl daemon-reload
			systemctl restart macro-git-store-maintenance.timer 2>/dev/null || true
			RECONCILED=1
			echo "macro-update: macro-git-store-maintenance units updated"
		fi
		systemctl enable --now macro-git-store-maintenance.timer >/dev/null 2>&1 || \
			echo "macro-update: macro-git-store-maintenance.timer could not be enabled" >&2
	else
		echo "macro-update: refusing macro-git-store-maintenance unit update — script not installed or systemd-analyze verify failed" >&2
	fi
	JOURNALD_CAP_SOURCE="$APP_DIR/app/deploy/journald-macro-vps.conf"
	JOURNALD_CAP=/etc/systemd/journald.conf.d/10-macro-vps-cap.conf
	if ! cmp -s "$JOURNALD_CAP_SOURCE" "$JOURNALD_CAP"; then
		install -D -m 0644 "$JOURNALD_CAP_SOURCE" "$JOURNALD_CAP"
		systemctl restart systemd-journald 2>/dev/null || \
			echo "macro-update: systemd-journald restart failed; the cap applies from its next start" >&2
		RECONCILED=1
		echo "macro-update: journald size cap updated"
	fi
fi

# PRESS-FEEDS is a long-running daemon, unlike the oneshot live-plane timers
# above. Arming remains an explicit operator choice: this block neither installs
# an absent unit nor enables/starts an inactive one. Once the operator has
# installed it, however, the reviewed unit must track main and an ACTIVE daemon
# must restart when import-cached code changes; otherwise a merged press-lane fix
# lands on disk while the old Python process runs forever.
PRESS_UNIT_UPDATED=0
if [ -f /etc/systemd/system/marketing-press-feeds.service ] && \
   ! cmp -s "$APP_DIR/app/deploy/marketing-press-feeds.service" /etc/systemd/system/marketing-press-feeds.service; then
	if systemd-analyze verify "$APP_DIR/app/deploy/marketing-press-feeds.service"; then
		install -m 0644 "$APP_DIR/app/deploy/marketing-press-feeds.service" /etc/systemd/system/marketing-press-feeds.service
		systemctl daemon-reload
		PRESS_UNIT_UPDATED=1
		RECONCILED=1
		echo "macro-update: marketing-press-feeds systemd sandbox updated"
	else
		echo "macro-update: refusing marketing-press-feeds unit update — systemd-analyze verify failed" >&2
	fi
fi

# TICKER NEWS is a long-running, operator-armed source service. Routine deploys
# never install, enable, or start an absent/inactive unit. If an operator has
# already installed it, keep the reviewed unit current and restart only an
# already-active writer when import-cached code or canonical universe inputs move.
TICKER_NEWS_RUNTIME_REGEX='^(app/requirements\.txt|scripts/run_qbus_news\.py|scripts/build_qbus_news_universe\.py|collectors/benzinga_news\.py|engine/massive_news\.py|engine/qbus_news_.*\.py|engine/news_common\.py|engine/qkernel\.py|lib/dataos/identity\.py|data/breadth/(constituents|sp1500_pit_membership)\.parquet|data/reference/(security_master|vendor_aliases)\.parquet)$'
TICKER_NEWS_UNIT_UPDATED=0
if [ -f /etc/systemd/system/macro-ticker-news.service ]; then
	if ! cmp -s "$APP_DIR/app/deploy/macro-ticker-news.service" /etc/systemd/system/macro-ticker-news.service; then
		if systemd-analyze verify "$APP_DIR/app/deploy/macro-ticker-news.service"; then
			install -m 0644 "$APP_DIR/app/deploy/macro-ticker-news.service" /etc/systemd/system/macro-ticker-news.service
			systemctl daemon-reload
			TICKER_NEWS_UNIT_UPDATED=1
			RECONCILED=1
			echo "macro-update: macro-ticker-news reviewed unit reconciled"
		else
			echo "macro-update: refusing macro-ticker-news unit update — systemd-analyze verify failed" >&2
			if systemctl is-active --quiet macro-ticker-news.service; then
				exit 1
			fi
		fi
	fi
	if [ "$TICKER_NEWS_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE "$TICKER_NEWS_RUNTIME_REGEX"; then
		if systemctl is-active --quiet macro-ticker-news.service; then
			systemctl restart macro-ticker-news.service
			systemctl is-active --quiet macro-ticker-news.service || {
				echo "macro-update: macro-ticker-news restart failed" >&2
				exit 1
			}
			RECONCILED=1
			echo "macro-update: active macro-ticker-news restarted on reviewed source"
		else
			echo "macro-update: macro-ticker-news installed but inactive; preserving operator-controlled arming"
		fi
	fi
fi

# BioCatalyst B1 is a separate source-canonical lane.  A routine production
# pull must never install, enable, or start it: doing so could turn a partially
# configured evidence collector live.  Reconcile only a fully operator-installed
# worker pair and dedicated runtime. The slower history archive and root-only
# retention heartbeat units are copied beside that pair but remain dormant
# unless separately armed. Dependencies are built in a versioned
# staging virtualenv and verified before one atomic current-symlink swap. No
# live runtime is ever pip-mutated, and a failed candidate leaves the previous
# runtime and timer arming state untouched.
BIOCATALYST_UNITS_INSTALLED=0
if [ -f /etc/systemd/system/macro-biocatalyst.service ] && \
   [ -f /etc/systemd/system/macro-biocatalyst.timer ]; then
	BIOCATALYST_UNITS_INSTALLED=1
fi

BIOCATALYST_RUNTIME_UPDATED=0
BIOCATALYST_RUNTIME_READY=0
if [ "$BIOCATALYST_UNITS_INSTALLED" -eq 1 ] && \
   [ -d /opt/macro-biocatalyst ] && \
   { [ -L /opt/macro-biocatalyst/current ] || \
     [ -x /opt/macro-biocatalyst/.venv/bin/python ]; } && \
   [ -f "$APP_DIR/app/deploy/biocatalyst-requirements.txt" ] && \
   [ -f "$APP_DIR/app/deploy/biocatalyst-runtime.sh" ]; then
	BIOCATALYST_REQUIREMENTS_HASH="$(sha256sum "$APP_DIR/app/deploy/biocatalyst-requirements.txt" | awk '{print $1}')"
	BIOCATALYST_INSTALLED_HASH=""
	if bash "$APP_DIR/app/deploy/biocatalyst-runtime.sh" --verify; then
		BIOCATALYST_INSTALLED_HASH="$(awk 'NR == 1 { print $1 }' /opt/macro-biocatalyst/current/.requirements.sha256)"
		if [ "$BIOCATALYST_REQUIREMENTS_HASH" = "$BIOCATALYST_INSTALLED_HASH" ]; then
			BIOCATALYST_RUNTIME_READY=1
		fi
	fi
	if [ "$BIOCATALYST_RUNTIME_READY" -ne 1 ]; then
		if bash "$APP_DIR/app/deploy/biocatalyst-runtime.sh" --install \
			"$APP_DIR/app/deploy/biocatalyst-requirements.txt"; then
			BIOCATALYST_RUNTIME_READY=1
			BIOCATALYST_RUNTIME_UPDATED=1
			RECONCILED=1
			echo "macro-update: BioCatalyst isolated runtime atomically reconciled without changing arming state"
		else
			echo "macro-update: BioCatalyst staged runtime failed; previous runtime remains selected" >&2
		fi
	fi
fi

# Reconcile unit files only after the runtime referenced by the reviewed service
# has passed verification. Preserve both timers' operator-controlled arming state.
BIOCATALYST_UNIT_UPDATED=0
if [ "$BIOCATALYST_UNITS_INSTALLED" -eq 1 ] && \
   { ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst.service" /etc/systemd/system/macro-biocatalyst.service || \
     ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst.timer" /etc/systemd/system/macro-biocatalyst.timer || \
     ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-history.service" /etc/systemd/system/macro-biocatalyst-history.service || \
     ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-history.timer" /etc/systemd/system/macro-biocatalyst-history.timer || \
     ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.service" /etc/systemd/system/macro-biocatalyst-activation-heartbeat.service || \
     ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.timer" /etc/systemd/system/macro-biocatalyst-activation-heartbeat.timer; }; then
	# Capture arming before copying a new unit. In particular, a newly introduced
	# auxiliary timers must remain absent/disabled after reconciliation rather than
	# becoming an accidental activation path merely because its source now exists.
	BIOCATALYST_TIMER_WAS_ENABLED=0
	BIOCATALYST_HISTORY_TIMER_WAS_ENABLED=0
	BIOCATALYST_HEARTBEAT_TIMER_WAS_ENABLED=0
	if [ -f /etc/systemd/system/macro-biocatalyst.timer ] && \
		systemctl is-enabled --quiet macro-biocatalyst.timer; then
		BIOCATALYST_TIMER_WAS_ENABLED=1
	fi
	if [ -f /etc/systemd/system/macro-biocatalyst-history.timer ] && \
		systemctl is-enabled --quiet macro-biocatalyst-history.timer; then
		BIOCATALYST_HISTORY_TIMER_WAS_ENABLED=1
	fi
	if [ -f /etc/systemd/system/macro-biocatalyst-activation-heartbeat.timer ] && \
		systemctl is-enabled --quiet macro-biocatalyst-activation-heartbeat.timer; then
		BIOCATALYST_HEARTBEAT_TIMER_WAS_ENABLED=1
	fi
	if [ "$BIOCATALYST_RUNTIME_READY" -ne 1 ]; then
		echo "macro-update: refusing BioCatalyst unit update — verified dedicated runtime unavailable" >&2
	elif systemd-analyze verify "$APP_DIR/app/deploy/macro-biocatalyst.service" \
		"$APP_DIR/app/deploy/macro-biocatalyst.timer" \
		"$APP_DIR/app/deploy/macro-biocatalyst-history.service" \
		"$APP_DIR/app/deploy/macro-biocatalyst-history.timer" \
		"$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.service" \
		"$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.timer"; then
		if ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst.service" /etc/systemd/system/macro-biocatalyst.service; then
			install -m 0644 "$APP_DIR/app/deploy/macro-biocatalyst.service" /etc/systemd/system/macro-biocatalyst.service
		fi
		if ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst.timer" /etc/systemd/system/macro-biocatalyst.timer; then
			install -m 0644 "$APP_DIR/app/deploy/macro-biocatalyst.timer" /etc/systemd/system/macro-biocatalyst.timer
		fi
		if ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-history.service" /etc/systemd/system/macro-biocatalyst-history.service; then
			install -m 0644 "$APP_DIR/app/deploy/macro-biocatalyst-history.service" /etc/systemd/system/macro-biocatalyst-history.service
		fi
		if ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-history.timer" /etc/systemd/system/macro-biocatalyst-history.timer; then
			install -m 0644 "$APP_DIR/app/deploy/macro-biocatalyst-history.timer" /etc/systemd/system/macro-biocatalyst-history.timer
		fi
		if ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.service" /etc/systemd/system/macro-biocatalyst-activation-heartbeat.service; then
			install -m 0644 "$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.service" /etc/systemd/system/macro-biocatalyst-activation-heartbeat.service
		fi
		if ! cmp -s "$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.timer" /etc/systemd/system/macro-biocatalyst-activation-heartbeat.timer; then
			install -m 0644 "$APP_DIR/app/deploy/macro-biocatalyst-activation-heartbeat.timer" /etc/systemd/system/macro-biocatalyst-activation-heartbeat.timer
		fi
		systemctl daemon-reload
		BIOCATALYST_UNIT_UPDATED=1
		RECONCILED=1
		echo "macro-update: BioCatalyst systemd lane updated without changing its arming state"
		if [ "$BIOCATALYST_TIMER_WAS_ENABLED" -eq 1 ]; then
			systemctl restart macro-biocatalyst.timer
		fi
		if [ "$BIOCATALYST_HISTORY_TIMER_WAS_ENABLED" -eq 1 ]; then
			systemctl restart macro-biocatalyst-history.timer
		fi
		if [ "$BIOCATALYST_HEARTBEAT_TIMER_WAS_ENABLED" -eq 1 ]; then
			systemctl restart macro-biocatalyst-activation-heartbeat.timer
		fi
	else
		echo "macro-update: refusing BioCatalyst unit update — systemd-analyze verify failed" >&2
	fi
fi

# The daemon imports these modules into one persistent interpreter. Config YAML
# is deliberately absent: it is re-read on every 75-second tick and needs no
# restart. Keep the engine/marketing pattern broad because every submodule import
# executes that package's non-inert __init__ first, and the press pipeline reaches
# multiple modules lazily according to the source/item path.
if [ "$PRESS_UNIT_UPDATED" -eq 1 ] || echo "$CHANGED" | grep -qE '^(app/deploy/marketing-press-feeds\.service|scripts/marketing_fastlane_daemon\.py|engine/news_translate\.py|engine/marketing/.*\.py|engine/(codex_provider|llm_auth)\.py|engine/codex_lane/runner\.py|lib/(ai_costs|config)\.py)$'; then
	if systemctl is-active --quiet marketing-press-feeds; then
		systemctl restart marketing-press-feeds
	fi
fi


if [ "$REPO_UPDATED" -eq 1 ] || [ "$RECONCILED" -eq 1 ]; then
	echo "macro-update $(date -u +%FT%TZ) ${OLD:0:8}..$(git -C "$APP_DIR" rev-parse --short HEAD)"
fi
# BEGIN OHLC_DELIVERY_EXIT_STATUS
if [ "$OHLC_DELIVERY_EXIT_STATUS" -ne 0 ]; then
	echo "macro-update: deploy finished with OHLC status $OHLC_DELIVERY_EXIT_STATUS" >&2
	if [ "${DEPLOY_EXIT_STATUS:-0}" -eq 0 ]; then
		DEPLOY_EXIT_STATUS=$OHLC_DELIVERY_EXIT_STATUS
	fi
fi
# END OHLC_DELIVERY_EXIT_STATUS
# BEGIN DISK_REFUSAL_EXIT_STATUS
if [ "${DISK_REFUSED:-0}" -eq 1 ]; then
	echo "macro-update: tick reconciled without pulling: $DISK_REFUSAL" >&2
	if [ "${DEPLOY_EXIT_STATUS:-0}" -eq 0 ]; then
		DEPLOY_EXIT_STATUS=1
	fi
fi
# END DISK_REFUSAL_EXIT_STATUS
# BEGIN DEPLOY_EXIT_STATUS
if [ "${W2C_LANE_FROZEN:-0}" -eq 1 ]; then
	echo "macro-update: deploy finished with status ${DEPLOY_EXIT_STATUS:-1} (frozen lanes: w2c)" >&2
fi
exit "${DEPLOY_EXIT_STATUS:-0}"
# END DEPLOY_EXIT_STATUS
