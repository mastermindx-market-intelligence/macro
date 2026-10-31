#!/usr/bin/env python3
"""One reviewed activation operation; preview by default, --apply mutates.

Run on the Macro API VPS as root, only after the parent has qualified/merged PR
9846 and observed its normal deployment. This file does not merge, deploy source,
render pages, create entitlements, install/arm a writer, or certify live coverage.
An existing operation carrier is reconciled read-only, never automatically resumed.

The 31 source pins below are Git blob digests obtained from GitHub at REVIEWED_HEAD.
Receipt SHA-256 values bind the already prepared bytes, not regenerated receipts.
No environment value or subprocess error text is emitted or put in command args.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

OPERATION = "news-publisher-activation-20261020-c3"
REVIEWED_HEAD = "b82af8dae3b05e7eaea198cfe49d61fb9b8ce595"
ROOT = Path("/opt/macro")
STATE = Path("/var/lib/macro-ticker-news")
CARRIER = STATE / OPERATION
PHASE_FILE = CARRIER / "phase.json"
BACKUPS = CARRIER / "backups"
LOCK = Path("/var/lock/macro-update.lock")
PYTHON = "/opt/macro-api/.venv/bin/python"
WRITER_ENV = Path("/etc/macro-ticker-news.env")
API_ENV = Path("/etc/macro-api.env")
API_LATER_ENV = Path("/etc/macro-ollama.env")
LIVE_ENV = Path("/etc/macro-live.env")
PRIMARY_RIGHTS = Path("/etc/macro-ticker-news-rights.json")
WRITER_UNIT = "macro-ticker-news.service"
API_UNIT = "macro-api.service"
SOURCE_BLOBS = {
    "engine/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "engine/massive_news.py": "dc83c3214209968b445e39a6a3d5fd303f0d28e8",
    "engine/news_common.py": "28fa6cbad7519214bec8791cedf82ae82cc9756a",
    "engine/qbus_news_annotate.py": "50e00497d2a2a920604e82ab45c469eff18c71fb",
    "engine/qbus_news_cluster.py": "ff2300b0c55094c77d9dbacd48c2fb815d3cadec",
    "engine/qbus_news_context.py": "cf997d997d4bc913b59f883b43efe2c87b6eb590",
    "engine/qbus_news_contract.py": "e740079cc7fa702c333047ca5b4a0c6525118fd2",
    "engine/qbus_news_intake.py": "9e17bd227c24e19707466999e22b53fe124fb48e",
    "engine/qbus_news_quality.py": "aad34e4a054efd73472ffb48f35dbf862c3fada4",
    "engine/qbus_news_receipts.py": "5fe0f27f5e8336404059adefe9be374521387468",
    "engine/qbus_news_reducer.py": "06e63abc8ce0f7e58375c89f64f45ef92751b709",
    "engine/qbus_news_retrieval.py": "14712a94a8edcd7bd49bccf2e37f436d467f5158",
    "engine/qbus_news_store.py": "0edbb2a5e49a1c5aee28562061db1557aac918ca",
    "engine/qbus_news_universe.py": "6febd6b4231e0615f50170bcdb09e2c2e4139315",
    "engine/qbus_news_universe_snapshot.py": "b575e9d6a6997e49815547a0fbfec9e5f2460473",
    "engine/qbus_news_velocity.py": "11e715b41684b3a059bf312299576d5ea5ed22d4",
    "engine/qkernel.py": "4a27ef447dff97c2219ba352d61ff774cca5d533",
    "app/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "app/ticker_news.py": "bb0b72f04e73850c5a44d151ca30db42cad8526b",
    "app/ticker_news_stream.py": "6a1ffff80b81049c79df0daa47d15491ed5eb781",
    "scripts/__init__.py": "dafbbd0c3a49c56a2635c0d3d8918302d10689a6",
    "scripts/build_qbus_news_universe.py": "79dd3bc23945f97ba7b4b5a47cc252734610decd",
    "collectors/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "collectors/alpaca_news.py": "b8cd54cf3a58842f100e739580d52ec89f46cb97",
    "collectors/benzinga_news.py": "3ead9c2642547622f895f42a47c568cb7f4f6749",
    "app/deploy/macro-api.service": "191cd77f26d18ccd55465de8f30ca7c61eeb641c",
    "app/deploy/macro-ticker-news.service": "300f7eafd4f8c64abeff46070a529dcadf5110f4",
    "lib/dataos/__init__.py": "1ddadafd88a59dfc90a7d68c3ae0897da1aae661",
    "lib/dataos/identity.py": "e1a5093aec8d7d787202db077bce47f61734e01d",
    "scripts/run_qbus_news.py": "36bb42dc7ff0d1b0908172047011d630d1cf21b9",
    "lib/__init__.py": "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
}
RECEIPTS = (
    ("zacks-com", "massive:zacks.com",
     "1f31c4e95b31eb2c4826f0e733747140088525eaf8d6d114a195a2b6ac436c32"),
    ("fool-com", "massive:fool.com",
     "7066a98da3620ad2aed05e57dd9927331ed939d8a2bb1601b77ec182c24c6803"),
    ("globenewswire-com", "massive:globenewswire.com",
     "f14ca7c87d9650f68c3c26ae6017a5b146d914b7ca6100a8ae88c2274ac0dc82"),
)
RIGHTS_PATHS = [
    "/etc/macro-ticker-news-massive-" + slug + "-rights.json"
    for slug, _, _ in RECEIPTS
]
SOURCES = sorted(source for _, source, _ in RECEIPTS)
AUDIENCES = ("site_full", "internal_research", "blog_draft", "marketing_draft")
ASSIGNMENT = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
OP_KEYS = ("MM_TICKER_NEWS_MASSIVE_ENABLED", "MM_TICKER_NEWS_ADDITIONAL_RIGHTS",
           "POLYGON_API_KEY")
TRACKED_KEYS = frozenset((*OP_KEYS, "MASSIVE_API_KEY", "QBUS_NEWS_PROVIDER",
                          "ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY"))
API_PROVIDER_KEYS = ("POLYGON_API_KEY", "MASSIVE_API_KEY", "MM_TICKER_NEWS_MASSIVE_ENABLED")
CHECK_UNIT = "news-publisher-check-20261020-c3"


class Refusal(Exception):
    """Safe code only: never include a secret or an arbitrary exception message."""


def require(condition, code):
    if not condition:
        raise Refusal(code)


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def command(argv, label, timeout=30):
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True,
                                text=True, timeout=timeout, check=False,
                                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                                     "LANG": "C.UTF-8"})
    except subprocess.TimeoutExpired:
        raise Refusal(label + "_timeout_effect_requires_readback") from None
    except OSError:
        raise Refusal(label + "_exec_unavailable") from None
    require(result.returncode == 0, label + "_nonzero")
    return result.stdout


def regular_bytes(path, *, private=False):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        raise Refusal("required_regular_file_unreadable:" + str(path)) from None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), "not_regular:" + str(path))
        if private:
            require(info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o600,
                    "expected_root_0600:" + str(path))
        require(info.st_size < 8 * 1024 * 1024, "unexpected_file_size:" + str(path))
        return stream.read()


def private_directory(path):
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0
            and stat.S_IMODE(info.st_mode) == 0o700,
            "expected_root_0700_directory:" + str(path))


def env_assignments(data, name):
    # Bounded operation accepts UTF-8, LF, single-physical-line assignments only.
    # Reject continuations/multiline values instead of attempting shell evaluation.
    try:
        value = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refusal("env_not_utf8:" + name) from None
    require("\r" not in value and "\0" not in value, "env_control_format:" + name)
    out = {}
    for line in value.splitlines():
        if not line.strip() or line.lstrip().startswith(("#", ";")):
            continue
        match = ASSIGNMENT.fullmatch(line)
        require(match is not None, "env_non_single_line_assignment:" + name)
        key, rhs = match.groups()
        require(not rhs.endswith("\\"), "env_continuation_refused:" + name)
        if rhs.startswith(("'", '"')):
            require(len(rhs) >= 2 and rhs.endswith(rhs[0]),
                    "env_multiline_or_unclosed_quote:" + name)
        require(key not in out or key not in TRACKED_KEYS,
                "env_duplicate_key:" + name + ":" + key)
        out[key] = rhs
    return out


def nonempty_rhs(rhs):
    return isinstance(rhs, str) and rhs.strip() not in ("", "''", '""')


def append_assignments(data, additions):
    suffix = "".join(key + "=" + rhs + "\n" for key, rhs in additions.items())
    return data + (b"" if data.endswith(b"\n") else b"\n") + suffix.encode("utf-8")


def atomic_write(path, data, *, absent=False, previous=None):
    # /etc and the operation carrier are root-owned. The shared updater lock is
    # held across all comparisons, writes, the network-dark check and restarts.
    if previous is not None:
        require(regular_bytes(path, private=True) == previous,
                "target_changed_since_preflight:" + str(path))
    fd, temp_name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if absent:
            os.link(temp_name, path)  # atomic no-clobber creation
            os.unlink(temp_name)
        else:
            os.replace(temp_name, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def service_state(unit):
    fields = ("ActiveState", "SubState", "MainPID", "ExecMainStartTimestamp",
              "FragmentPath", "DropInPaths", "NeedDaemonReload", "EnvironmentFiles")
    raw = command(["systemctl", "show", unit] +
                  ["--property=" + field for field in fields], "service_read")
    data, environment_files = {}, []
    for line in raw.splitlines():
        if "=" not in line:
            continue
        field, value = line.split("=", 1)
        if field == "EnvironmentFiles":
            # systemctl may emit this list as repeated property lines. Preserve
            # every entry in order, including duplicates for the exact-list gate.
            environment_files.append(value)
        elif field in fields:
            require(field not in data, "duplicate_service_property:" + unit + ":" + field)
            data[field] = value
    data["EnvironmentFiles"] = " ".join(environment_files)
    return {field: data.get(field, "") for field in fields}


def sole_writer(main_pid):
    found = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = path.read_bytes().split(b"\0")
        except OSError:
            continue
        if b"--run" in args and any(
            arg == b"scripts/run_qbus_news.py"
            or arg.endswith(b"/scripts/run_qbus_news.py") for arg in args
        ):
            found.append(int(path.parent.name))
    require(sorted(found) == [int(main_pid)], "sole_writer_pid_mismatch")
    return found


def source_and_services(expected_merge):
    head = command(["git", "rev-parse", "HEAD"], "git_head").strip()
    command(["git", "merge-base", "--is-ancestor", expected_merge, head],
            "expected_merge_not_deployed")
    tree = command(["git", "ls-tree", "HEAD", "--", *SOURCE_BLOBS], "git_source_tree")
    committed = {}
    for line in tree.splitlines():
        meta, path = line.split("\t", 1)
        mode, kind, oid = meta.split()
        require(kind == "blob" and mode != "120000", "non_blob_source:" + path)
        committed[path] = oid
    require(committed == SOURCE_BLOBS, "committed_critical_source_drift")
    for path, pin in SOURCE_BLOBS.items():
        require((ROOT / path).resolve().is_relative_to(ROOT),
                "source_path_escaped:" + path)
        require(git_blob(regular_bytes(ROOT / path)) == pin,
                "working_critical_source_drift:" + path)
    services = {unit: service_state(unit) for unit in (API_UNIT, WRITER_UNIT)}
    for unit, data in services.items():
        require(data["ActiveState"] == "active" and data["MainPID"].isdigit()
                and int(data["MainPID"]) > 0, "service_not_active:" + unit)
        installed = Path("/etc/systemd/system") / unit
        require(data["FragmentPath"] == str(installed)
                and data["NeedDaemonReload"] == "no",
                "service_manager_not_qualified:" + unit)
        require(git_blob(regular_bytes(installed)) ==
                SOURCE_BLOBS["app/deploy/" + unit], "installed_unit_drift:" + unit)
        expected_files = ([str(WRITER_ENV)] if unit == WRITER_UNIT
                          else [str(API_ENV), str(API_LATER_ENV)])
        loaded_files = re.findall(r"(/[^ ]+) \(ignore_errors=(?:yes|no)\)",
                                  data["EnvironmentFiles"])
        require(loaded_files == expected_files, "loaded_environment_files_drift:" + unit)
    require(not services[WRITER_UNIT]["DropInPaths"], "writer_dropins_unreviewed")
    sole_writer(services[WRITER_UNIT]["MainPID"])
    return head, services


def prepare(expected_merge):
    head, services = source_and_services(expected_merge)
    private_directory(STATE)
    writer = regular_bytes(WRITER_ENV, private=True)
    api = regular_bytes(API_ENV, private=True)
    live = regular_bytes(LIVE_ENV, private=True)
    regular_bytes(PRIMARY_RIGHTS, private=True)
    wa = env_assignments(writer, "writer")
    aa = env_assignments(api, "api")
    la = env_assignments(live, "live")
    require(wa.get("QBUS_NEWS_PROVIDER") in ("alpaca", "'alpaca'", '"alpaca"'),
            "primary_provider_must_remain_alpaca")
    require(all(nonempty_rhs(wa.get(key)) for key in
                ("ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY")),
            "primary_credentials_missing")
    require(nonempty_rhs(la.get("MASSIVE_API_KEY")), "licensed_credential_missing")
    # API's later optional env file must not supersede the path list.
    ollama = API_LATER_ENV
    if ollama.exists() or ollama.is_symlink():
        oa = env_assignments(regular_bytes(ollama, private=True), "ollama")
        require(not any(key in oa for key in (*OP_KEYS, *API_PROVIDER_KEYS)),
                "api_later_env_override")
    json_rhs = "'" + json.dumps(RIGHTS_PATHS, separators=(",", ":")) + "'"
    additions = {
        WRITER_ENV: {"MM_TICKER_NEWS_MASSIVE_ENABLED": "1",
                     "MM_TICKER_NEWS_ADDITIONAL_RIGHTS": json_rhs,
                     "POLYGON_API_KEY": la["MASSIVE_API_KEY"]},
        API_ENV: {"MM_TICKER_NEWS_ADDITIONAL_RIGHTS": json_rhs},
    }
    require(not any(key in aa for key in API_PROVIDER_KEYS),
            "unexpected_api_provider_configuration")
    old = {WRITER_ENV: writer, API_ENV: api}
    mappings = {WRITER_ENV: wa, API_ENV: aa}
    existing = None
    if CARRIER.exists() or CARRIER.is_symlink():
        private_directory(CARRIER)
        existing = json.loads(regular_bytes(PHASE_FILE, private=True))
        require(existing.get("schema") == "shared_news.publisher_activation_operation.v1"
                and existing.get("operation") == OPERATION
                and existing.get("expected_merge") == expected_merge
                and existing.get("reviewed_head") == REVIEWED_HEAD
                and existing.get("publisher_sources") == SOURCES,
                "operation_carrier_identity_mismatch")
    proposed, changed_keys = {}, {}
    for path, added in additions.items():
        current = mappings[path]
        present = [key for key in added if key in current]
        if present:
            require(existing is not None, "optional_configuration_without_carrier")
            require(all(current[key] == added[key] for key in present),
                    "optional_configuration_disagrees:" + path.name)
        missing = {key: rhs for key, rhs in added.items() if key not in current}
        proposed[path] = append_assignments(old[path], missing) if missing else old[path]
        changed_keys[str(path)] = list(missing)
    receipts = []
    for (slug, source, pin), target_path in zip(RECEIPTS, RIGHTS_PATHS, strict=True):
        src = ROOT / ("artifacts/news-shared-integration-20261020-c3/activation/"
                      "massive-" + slug + "-rights.json")
        data = regular_bytes(src)
        require(digest(data) == pin, "prepared_receipt_digest_mismatch:" + source)
        target = Path(target_path)
        present = target.exists() or target.is_symlink()
        if present:
            require(regular_bytes(target, private=True) == data,
                    "installed_receipt_differs:" + source)
        receipts.append((target, data, present, source))
    return {
        "head": head, "services": services, "old": old, "proposed": proposed,
        "receipts": receipts, "changed_keys": changed_keys, "existing": existing,
    }


def check_code():
    # No credential is interpolated here; systemd alone parses EnvironmentFile.
    return """
import json, sys
from datetime import datetime, timezone
from websockets.sync.client import connect
from scripts.run_qbus_news import main
from engine.qbus_news_receipts import additional_rights_paths, load_rights_set, combine_news_rights
args = ["--check-activation", "--database", "/var/lib/macro-ticker-news/qbus.sqlite3",
        "--universe-snapshot", "/var/lib/macro-ticker-news/news_universe.json",
        "--rights-receipt", "/etc/macro-ticker-news-rights.json",
        "--health-path", "/var/lib/macro-ticker-news/health.json"]
rc = main(args)
if rc:
    raise SystemExit(rc)
qualified = {}
for audience in ("site_full", "internal_research", "blog_draft", "marketing_draft"):
    receipts = load_rights_set(additional_rights_paths(), now=datetime.now(timezone.utc), audience=audience)
    selected = tuple(r for r in receipts if r.provider == "massive" and r.source.startswith("massive:"))
    qualified[audience] = sorted(combine_news_rights(selected).allowed_sources)
print(json.dumps({"schema": "shared_news.activation_sources_check.v1",
                  "qualified_sources": qualified}, sort_keys=True))
"""


def network_dark_check():
    raw = command([
        "systemd-run", "--quiet", "--wait", "--pipe", "--collect",
        "--unit=" + CHECK_UNIT,
        "--property=WorkingDirectory=/opt/macro",
        "--property=EnvironmentFile=/etc/macro-ticker-news.env",
        "--property=RuntimeMaxSec=45s",
        "--property=UMask=0077",
        PYTHON, "-c", check_code(),
    ], "network_dark_check", timeout=55)
    parsed = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            parsed.append(item)
    reports = [item for item in parsed
               if item.get("schema") == "qbus.news_runner_preflight.v1"]
    sources = [item for item in parsed
               if item.get("schema") == "shared_news.activation_sources_check.v1"]
    require(len(reports) == len(sources) == 1, "preflight_payload_missing_or_ambiguous")
    report = reports[0]
    require(report.get("provider") == "alpaca"
            and report.get("run_requested") is False
            and report.get("check_requested") is True
            and report.get("additional_sources_qualified") == 3
            and report.get("database") == str(STATE / "qbus.sqlite3"),
            "preflight_contract_mismatch")
    for field in ("activation_qualified", "token_present", "universe_present",
                  "rights_receipt_present", "health_path_present",
                  "additional_sources_enabled"):
        require(report.get(field) is True, "preflight_false:" + field)
    require(type(report.get("universe_count")) is int
            and report["universe_count"] > 0
            and isinstance(report.get("universe_revision"), str)
            and bool(report["universe_revision"]), "preflight_universe_invalid")
    require(sources[0].get("qualified_sources") ==
            {audience: SOURCES for audience in AUDIENCES},
            "qualified_publisher_set_mismatch")
    # Publish an allowlist of safe output fields, never arbitrary stdout/stderr.
    return {field: report[field] for field in (
        "schema", "provider", "activation_qualified", "universe_count",
        "universe_revision", "additional_sources_enabled",
        "additional_sources_qualified")}


def persist(receipt, phase, **fields):
    receipt.update(phase=phase, updated_at=now(), **fields)
    receipt["events"].append({"phase": phase, "at": receipt["updated_at"]})
    atomic_write(PHASE_FILE, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())


def restart(unit, previous_pid):
    command(["systemctl", "restart", unit], "restart_" + unit, timeout=60)
    readback = service_state(unit)
    require(readback["ActiveState"] == "active"
            and readback["MainPID"].isdigit()
            and int(readback["MainPID"]) > 0
            and readback["MainPID"] != previous_pid,
            "restart_readback_unqualified:" + unit)
    return readback


def public_plan(plan):
    return {
        "deployed_head": plan["head"],
        "critical_source_pins_verified": len(SOURCE_BLOBS),
        "environment_keys_to_add": plan["changed_keys"],
        "receipts": [{"path": str(path), "source": source,
                      "state": "identical" if present else "absent"}
                     for path, _, present, source in plan["receipts"]],
        "services": plan["services"],
        "phase_carrier": str(PHASE_FILE),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-merge", required=True)
    parser.add_argument("--apply", action="store_true",
                        help="apply this reviewed operation once; default is read-only preview")
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_merge) is not None,
            "expected_merge_must_be_full_lowercase_sha")
    require(os.geteuid() == 0, "must_run_as_root_on_macro_vps")
    require(ROOT.is_dir() and ROOT.resolve() == ROOT, "canonical_checkout_unavailable")
    require(Path(PYTHON).is_file() and os.access(PYTHON, os.X_OK), "api_python_unavailable")
    os.umask(0o077)
    lock_fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)  # existing owner lock only
    lock_info = os.fstat(lock_fd)
    require(stat.S_ISREG(lock_info.st_mode) and lock_info.st_uid == 0
            and stat.S_IMODE(lock_info.st_mode) & 0o022 == 0,
            "update_lock_not_qualified")
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Refusal("normal_update_lock_busy") from None
        plan = prepare(args.expected_merge)
        output = public_plan(plan)
        if plan["existing"] is not None:
            old = plan["existing"]
            output.update(state="same_carrier_readback_only", recorded_phase=old.get("phase"),
                          recorded_state=old.get("state"),
                          last_effect_phase=old.get("last_effect_phase"))
            print(json.dumps(output, sort_keys=True))
            # A complete operation is a no-op, only if its configured bytes still match.
            complete = old.get("state") == "applied_awaiting_live_proof"
            exact = all(not keys for keys in plan["changed_keys"].values())
            exact = exact and all(present for _, _, present, _ in plan["receipts"])
            return 0 if complete and exact else 3
        if not args.apply:
            output.update(state="preview_qualified", production_mutated=False,
                          next="explicit --apply after parent review")
            print(json.dumps(output, sort_keys=True))
            return 0

        CARRIER.mkdir(mode=0o700)  # exclusive operation identity; never overwrite it
        receipt = {
            "schema": "shared_news.publisher_activation_operation.v1",
            "operation": OPERATION, "expected_merge": args.expected_merge,
            "reviewed_head": REVIEWED_HEAD,
            "script_sha256": digest(Path(__file__).read_bytes()),
            "deployed_head": plan["head"], "state": "in_progress", "events": [],
            "services_before": plan["services"], "preflight_unit": CHECK_UNIT,
            "environment_preimage_sha256": {str(p): digest(v) for p, v in plan["old"].items()},
            "environment_target_sha256": {str(p): digest(v) for p, v in plan["proposed"].items()},
            "publisher_sources": SOURCES,
            "receipt_installation_plan": [
                {"path": str(path), "source": source, "existed_before": present,
                 "sha256": digest(data)}
                for path, data, present, source in plan["receipts"]
            ],
            "no_automatic_replay_or_rollback": True,
        }
        try:
            persist(receipt, "begun")
            BACKUPS.mkdir(mode=0o700)
            for path, data in plan["old"].items():
                atomic_write(BACKUPS / path.name, data, absent=True)
            persist(receipt, "backups_complete")
            for target, data, present, source in plan["receipts"]:
                persist(receipt, "receipt_install_requested", last_effect_phase=source)
                if not present:
                    atomic_write(target, data, absent=True)
                require(regular_bytes(target, private=True) == data,
                        "receipt_install_readback_failed:" + source)
            persist(receipt, "receipts_installed")
            # Writer configuration first; API receives only the explicit receipt list.
            for path in (WRITER_ENV, API_ENV):
                persist(receipt, "environment_write_requested", last_effect_phase=str(path))
                atomic_write(path, plan["proposed"][path], previous=plan["old"][path])
                require(regular_bytes(path, private=True) == plan["proposed"][path],
                        "environment_write_readback_failed:" + path.name)
            persist(receipt, "environment_installed")
            persist(receipt, "network_dark_check_requested", last_effect_phase=CHECK_UNIT)
            check = network_dark_check()
            persist(receipt, "network_dark_check_passed", preflight=check)
            after = {}
            for unit in (API_UNIT, WRITER_UNIT):
                persist(receipt, "restart_requested", last_effect_phase=unit)
                after[unit] = restart(unit, plan["services"][unit]["MainPID"])
                persist(receipt, "restart_verified", services_after=after)
            final = prepare(args.expected_merge)
            require(not any(final["changed_keys"].values()), "final_configuration_incomplete")
            persist(receipt, "apply_complete", state="applied_awaiting_live_proof",
                    services_after=final["services"], production_coverage_verified=False,
                    last_effect_phase="services_restarted")
            output.update(state=receipt["state"], preflight=check,
                          services_after=final["services"],
                          production_mutated=True, live_coverage_verified=False)
            print(json.dumps(output, sort_keys=True))
            return 0
        except BaseException as exc:
            safe_code = str(exc) if isinstance(exc, Refusal) else type(exc).__name__
            try:
                persist(receipt, "stopped_requires_same_carrier_reconciliation",
                        state="effect_requires_readback", error_code=safe_code)
            except Exception:
                pass
            print(json.dumps({"state": "effect_requires_readback",
                              "error_code": safe_code, "phase_carrier": str(PHASE_FILE),
                              "last_effect_phase": receipt.get("last_effect_phase"),
                              "preflight_unit": CHECK_UNIT,
                              "automatic_rollback_or_replay": False}, sort_keys=True))
            return 3
    finally:
        os.close(lock_fd)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Refusal as exc:
        print(json.dumps({"state": "refused_before_new_effect", "error_code": str(exc),
                          "phase_carrier": str(PHASE_FILE)}, sort_keys=True))
        raise SystemExit(2)
    except Exception as exc:
        # Exception text may contain credential-bearing parser/subprocess material.
        print(json.dumps({"state": "refused_before_new_effect",
                          "error_code": type(exc).__name__,
                          "phase_carrier": str(PHASE_FILE)}, sort_keys=True))
        raise SystemExit(2)

