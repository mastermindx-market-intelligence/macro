"""Synthetic profile-store algorithms and an unavailable runtime interface.

SimulationProfileStore is for explicit temporary synthetic fixtures only.
Its manifests and snapshots do not establish incumbent account/profile
ownership. Store, ProfileStore and all module-level runtime wrappers refuse
before profile access; there is no runtime activation flag."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
import datetime
from pathlib import Path

try:
    from .runtime_boundary import refuse_runtime
except ImportError:  # direct-script import
    from runtime_boundary import refuse_runtime

KEEP_SNAPSHOTS = 7
MANIFEST = "manifest.json"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _safe(handle: str) -> str:
    if not handle or handle in (".", "..") or "/" in handle or "\\" in handle:
        raise ValueError(f"unsafe handle {handle!r}")
    return handle


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _tree(handle_dir: Path) -> tuple[str, dict[str, str]]:
    """Hash the live tree, excluding the manifest (it is the record, not state)."""
    files: dict[str, str] = {}
    for p in sorted(handle_dir.rglob("*")):
        if p.is_file() and p.name != MANIFEST:
            files[p.relative_to(handle_dir).as_posix()] = _sha256_file(p)
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode() + b"\0" + files[rel].encode() + b"\n")
    return h.hexdigest(), files


def _load(handle_dir: Path) -> dict:
    with open(handle_dir / MANIFEST) as fh:
        return json.load(fh)


def _save(handle_dir: Path, manifest: dict) -> None:
    tmp = handle_dir / (MANIFEST + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, handle_dir / MANIFEST)


DEFAULT_ROOT = os.environ.get("XG_PROFILE_STORE", "~/.xguerrilla/profiles")


class SimulationProfileStore:
    """Profile algorithms for explicit temporary synthetic fixtures only."""

    def __init__(self, base_dir: str | os.PathLike):
        self.base = Path(base_dir).expanduser().resolve()

    # -- paths ---------------------------------------------------------
    def handle_dir(self, handle: str) -> Path:
        return self.base / _safe(handle)

    @property
    def snapshot_dir(self) -> Path:
        return self.base / "snapshots"

    def _manifest_path(self, handle: str) -> Path:
        return self.handle_dir(handle) / MANIFEST

    # -- lifecycle -----------------------------------------------------
    def init(self, handle: str, slot: str = "", chrome_version: str = "", notes: str = "") -> str:
        hd = self.handle_dir(handle)
        (hd / "profile").mkdir(parents=True, exist_ok=True)
        if not self._manifest_path(handle).exists():
            tree_hash, files = _tree(hd)
            _save(hd, {
                "handle": handle,
                "created_at": _now(),
                "slot": slot,
                "chrome_version": chrome_version,
                "notes": notes,
                "tree_hash": tree_hash,
                "files": files,
                "snapshots": [],
            })
        return str(hd)

    def snapshot(self, handle: str) -> str:
        hd = self.handle_dir(handle)
        if not self._manifest_path(handle).exists():
            raise FileNotFoundError(f"no profile {handle!r} at {hd}")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        archive = self.snapshot_dir / f"{handle}-{_stamp()}.tar.gz"
        manifest = _load(hd)
        record = {
            "path": archive.relative_to(self.base).as_posix(),
            "sha256": "",
            "bytes": 0,
            "created_at": _now(),
        }
        # Register before archiving so the archive's own manifest lists it;
        # a restore into an empty store therefore keeps a complete ledger.
        manifest.setdefault("snapshots", []).append(record)
        manifest["snapshots"] = self._prune(handle, manifest["snapshots"])
        _save(hd, manifest)
        try:
            with tarfile.open(archive, "w:gz") as tar:
                tar.add(hd, arcname=handle)
        except Exception:
            manifest["snapshots"] = [s for s in manifest["snapshots"] if s["path"] != record["path"]]
            _save(hd, manifest)
            archive.unlink(missing_ok=True)
            raise
        record["sha256"] = _sha256_file(archive)
        record["bytes"] = archive.stat().st_size
        manifest["tree_hash"], manifest["files"] = _tree(hd)
        _save(hd, manifest)
        return str(archive)

    def _prune(self, handle: str, snaps: list[dict]) -> list[dict]:
        snaps = sorted(snaps, key=lambda s: s["created_at"])
        while len(snaps) > KEEP_SNAPSHOTS:
            old = snaps.pop(0)
            p = self.base / old["path"]
            if p.exists():
                p.unlink()
        return snaps

    def restore(self, handle: str, archive: str | os.PathLike) -> None:
        handle = _safe(handle)
        src = Path(archive)
        if not src.is_absolute():
            src = self.base / src
        if not src.exists():
            raise FileNotFoundError(str(src))
        hd = self.handle_dir(handle)
        prior: list[dict] = []
        if self._manifest_path(handle).exists():
            prior = _load(hd).get("snapshots", [])
        tmp = self.base / f".restore-{handle}-{_stamp()}"
        tmp.mkdir(parents=True, exist_ok=False)
        try:
            with tarfile.open(src, "r:gz") as tar:
                members = []
                for m in tar.getmembers():
                    name = m.name.replace("\\", "/")
                    if name.startswith("/") or ".." in Path(name).parts:
                        raise ValueError(f"unsafe archive member {m.name!r}")
                    if name != handle and not name.startswith(handle + "/"):
                        raise ValueError(f"archive member {m.name!r} outside {handle!r}")
                    members.append(m)
                try:
                    tar.extractall(tmp, members=members, filter="data")
                except TypeError:  # Python < 3.12
                    tar.extractall(tmp, members=members)
            restored = tmp / handle
            if not restored.is_dir():
                raise ValueError(f"archive has no {handle!r} directory")
            if hd.exists():
                _rmtree(hd)
            os.replace(restored, hd)
        finally:
            if tmp.exists():
                _rmtree(tmp)
        if not self._manifest_path(handle).exists():
            self.init(handle)
        manifest = _load(hd)
        # The snapshot ledger belongs to the store, not to the profile state:
        # restoring old cookies must not forget snapshots taken since.
        merged = {s["path"]: s for s in manifest.get("snapshots", [])}
        for s in prior:
            if not merged.get(s["path"], {}).get("sha256"):
                merged[s["path"]] = s
        for s in merged.values():
            path = self.base / s["path"]
            if not s.get("sha256") and path.exists():
                s["sha256"] = _sha256_file(path)
                s["bytes"] = path.stat().st_size
        manifest["snapshots"] = sorted(merged.values(), key=lambda s: s["created_at"])
        manifest["tree_hash"], manifest["files"] = _tree(hd)
        manifest["last_restore"] = _now()
        _save(hd, manifest)

    def verify(self, handle: str) -> dict:
        hd = self.handle_dir(handle)
        if not self._manifest_path(handle).exists():
            return {"ok": False, "handle": handle, "error": "no manifest", "expected": None, "actual": None}
        manifest = _load(hd)
        actual_hash, actual_files = _tree(hd)
        expected = manifest.get("tree_hash")
        expected_files = manifest.get("files", {})
        changed = sorted(f for f in expected_files if f in actual_files
                         and expected_files[f] != actual_files[f])
        missing = sorted(f for f in expected_files if f not in actual_files)
        extra = sorted(f for f in actual_files if f not in expected_files)
        return {
            "ok": actual_hash == expected and not missing,
            "handle": handle,
            "expected": expected,
            "actual": actual_hash,
            "files": len(actual_files),
            "changed": changed,
            "missing": missing,
            "extra": extra,
        }

    def needs_login(self, handle: str, last_ok: datetime.datetime | None, ttl_days: int = 21) -> bool:
        if last_ok is None:
            return True
        now = datetime.datetime.now(last_ok.tzinfo) if last_ok.tzinfo else datetime.datetime.now()
        return (now - last_ok) > datetime.timedelta(days=ttl_days)

    def describe(self, handle: str) -> dict:
        hd = self.handle_dir(handle)
        if not self._manifest_path(handle).exists():
            return {"handle": handle, "exists": False, "path": str(hd)}
        manifest = _load(hd)
        files = [p for p in hd.rglob("*") if p.is_file()]
        out = dict(manifest)
        out.update({
            "handle": handle,
            "exists": True,
            "path": str(hd),
            "files": len(files),
            "bytes": sum(p.stat().st_size for p in files),
        })
        out["snapshots"] = [
            {**s, "exists": (self.base / s["path"]).exists()}
            for s in manifest.get("snapshots", [])
        ]
        out["snapshot_count"] = len(out["snapshots"])
        return out


def _rmtree(top: Path) -> None:
    if not top.exists():
        return
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            p = Path(root) / name
            p.unlink(missing_ok=True)
        for name in dirs:
            p = Path(root) / name
            if p.is_symlink():
                p.unlink(missing_ok=True)
            else:
                p.rmdir()
    if top.is_symlink():
        top.unlink(missing_ok=True)
    else:
        top.rmdir()


# ---------------------------------------------------------------------------
# Module-level contract. A base dir may be passed explicitly; otherwise the
# store root comes from XG_PROFILE_STORE (or ~/.xguerrilla/profiles).
# ---------------------------------------------------------------------------
class Store:
    """Unavailable runtime profile interface; no path is read or resolved."""

    def __init__(self, base_dir):
        refuse_runtime("profile_store")


ProfileStore = Store


def _store(base_dir: str | os.PathLike | None = None) -> Store:
    return Store(base_dir if base_dir is not None else DEFAULT_ROOT)


def init(handle: str, base_dir: str | os.PathLike | None = None, *,
         slot: str = "", chrome_version: str = "", notes: str = "") -> str:
    return _store(base_dir).init(handle, slot=slot, chrome_version=chrome_version, notes=notes)


def snapshot(handle: str, base_dir: str | os.PathLike | None = None) -> str:
    return _store(base_dir).snapshot(handle)


def restore(handle: str, archive: str | os.PathLike,
            base_dir: str | os.PathLike | None = None) -> None:
    return _store(base_dir).restore(handle, archive)


def verify(handle: str, base_dir: str | os.PathLike | None = None) -> dict:
    return _store(base_dir).verify(handle)


def needs_login(handle: str, last_ok: datetime.datetime | None, ttl_days: int = 21) -> bool:
    return _store().needs_login(handle, last_ok, ttl_days)


def describe(handle: str, base_dir: str | os.PathLike | None = None) -> dict:
    return _store(base_dir).describe(handle)
