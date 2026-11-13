"""Tests for the source-qualified runtime adapter.

Two batteries:

1. **Refusal battery** — every unbound condition refuses with the same
   envelope the package's other refusals use (``RuntimeBindingUnavailable``,
   operation-tagged, no partial state). The real registry on disk (all
   ``proposed``, all receipts ``null``) must refuse unconditionally.

2. **Authorized battery** — a synthetic admitted entry with content-pinned
   receipts constructs the driver and runs the real lifecycle (launch via a
   stubbed Playwright, op bodies, stop) without touching any driver stub.

These tests are stdlib-only: Playwright is never imported for real (the
stub module is installed under ``sys.modules`` first), and everything runs
against temp files, so the suite is safe on a bare box.
"""
from __future__ import annotations

import hashlib
import sys
import types
from pathlib import Path

import pytest
import yaml

from tools.xguerrilla.runtime_adapter import (AuthorizedCdpDriver,
                                               build_authorized_driver,
                                               factory)
from tools.xguerrilla.runtime_boundary import RuntimeBindingUnavailable

# ---------------------------------------------------------------- fixtures


def _write_receipt(root: Path, name: str) -> dict:
    material = f"admission evidence {name} v1\n".encode()
    path = root / "receipts" / f"{name}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(material)
    return {"path": str(path), "sha256": hashlib.sha256(material).hexdigest()}


def _admitted_registry(root: Path, *, handle: str = "wrenmp4") -> Path:
    """A registry with exactly one fully-admitted, fully-bound identity."""
    entry_receipt = _write_receipt(root, f"entry-{handle}")
    domain_receipt = _write_receipt(root, f"domain-{handle}")
    doc = {
        "schema": "identity-registry/v1",
        "domains": [
            {
                "domain": "x.com",
                "state": "admitted",
                "admission_receipt": domain_receipt,
                "recovery_owner": "secretary",
            }
        ],
        "entries": [
            {
                "handle": handle,
                "domain": "x.com",
                "state": "admitted",
                "recovery_owner": "secretary",
                "admission_receipt": entry_receipt,
                "binding": {
                    "email_mailbox": "mailbox-ops",
                    "proxy_slot": "slot-a1",
                    "cdp_port": 9333,
                    "totp_custodian": "custodian-7",
                },
            }
        ],
    }
    path = root / "registry.yml"
    path.write_text(yaml.safe_dump(doc, sort_keys=True))
    return path


def _mutated_registry(root: Path, mutate_entry=None, mutate_domain=None) -> Path:
    path = _admitted_registry(root)
    doc = yaml.safe_load(path.read_text())
    if mutate_entry:
        doc["entries"][0] = {**doc["entries"][0], **mutate_entry}
    if mutate_domain:
        doc["domains"][0] = {**doc["domains"][0], **mutate_domain}
    path.write_text(yaml.safe_dump(doc, sort_keys=True))
    return path


def _install_pw_stub(monkeypatch) -> dict:
    """Install a deterministic fake ``playwright.sync_api``; return its ledger."""
    ledger = {"launches": 0, "stops": 0}

    class FakeCDP:
        def __init__(self, page):
            self.page = page
        def detach(self):
            ledger["stops"] += 1

    class FakeCtx:
        def __init__(self):
            class FakePage:
                def __init__(self, ctx):
                    self.ctx = ctx
                    self.url = "about:blank"
            self.pages = [FakePage(self)]
            self.closed = False
        def set_default_timeout(self, ms):
            pass
        def new_cdp_session(self, page):
            return FakeCDP(page)
        def close(self):
            self.closed = True
            ledger["stops"] += 1

    class FakePW:
        def __init__(self):
            self.ctx = None
            self.chromium = self  # real API: pw.chromium is a BrowserType attribute
        def launch_persistent_context(self, **kw):
            ledger["launches"] += 1
            ledger["last_launch_kw"] = kw
            self.ctx = FakeCtx()
            return self.ctx
        def stop(self):
            ledger["stops"] += 1

    class FakePWManager:
        def start(self):
            return FakePW()

    sync_mod = types.ModuleType("playwright.sync_api")
    sync_mod.sync_playwright = lambda: FakePWManager()
    mod = types.ModuleType("playwright")
    mod.sync_api = sync_mod
    monkeypatch.setitem(sys.modules, "playwright", mod)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_mod)
    return ledger


# ---------------------------------------------------------------- refusal battery


def test_real_registry_refuses(tmp_path):
    """The shipped registry (all proposed, receipts null) must refuse unconditionally."""
    real = Path(__file__).resolve().parent.parent / "registry.yml"
    assert real.exists(), "shipped registry.yml missing from package"
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(real, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_missing_registry_file_refuses(tmp_path):
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(tmp_path / "nope.yml", "wrenmp4",
                                profile_dir=str(tmp_path / "p"))


def test_unknown_handle_refuses(tmp_path):
    path = _admitted_registry(tmp_path)
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "ghost", profile_dir=str(tmp_path / "p"))


def test_proposed_entry_refuses(tmp_path):
    path = _mutated_registry(tmp_path, mutate_entry={"state": "proposed"})
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_unadmitted_domain_refuses(tmp_path):
    path = _mutated_registry(tmp_path, mutate_domain={"state": "suspended"})
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_unbound_slot_refuses(tmp_path):
    """Each of the four slots must refuse when its incumbent owner is unrecorded."""
    for slot in ("email_mailbox", "proxy_slot", "cdp_port", "totp_custodian"):
        path = _admitted_registry(tmp_path / slot)
        doc = yaml.safe_load(path.read_text())
        doc["entries"][0]["binding"][slot] = None
        path.write_text(yaml.safe_dump(doc))
        with pytest.raises(RuntimeBindingUnavailable):
            build_authorized_driver(path, "wrenmp4",
                                    profile_dir=str(tmp_path / slot / "p"))


def test_null_entry_receipt_refuses(tmp_path):
    path = _mutated_registry(tmp_path, mutate_entry={"admission_receipt": None})
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_null_domain_receipt_refuses(tmp_path):
    path = _mutated_registry(tmp_path, mutate_domain={"admission_receipt": None})
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_receipt_digest_mismatch_refuses(tmp_path):
    """The receipt pin is content: a drifted evidence file must refuse."""
    path = _admitted_registry(tmp_path)
    doc = yaml.safe_load(path.read_text())
    receipt = doc["entries"][0]["admission_receipt"]
    Path(receipt["path"]).write_bytes(b"tampered evidence\n")
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_receipt_extra_keys_refuses(tmp_path):
    """Shape comes first: an over-keyed receipt is not the registry's contract."""
    path = _admitted_registry(tmp_path)
    doc = yaml.safe_load(path.read_text())
    doc["entries"][0]["admission_receipt"] = {
        **doc["entries"][0]["admission_receipt"], "note": "extra"}
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_missing_receipt_file_refuses(tmp_path):
    path = _admitted_registry(tmp_path)
    doc = yaml.safe_load(path.read_text())
    receipt = doc["entries"][0]["admission_receipt"]
    Path(receipt["path"]).unlink()
    path.write_text(yaml.safe_dump(doc))
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


def test_null_recovery_owner_refuses(tmp_path):
    path = _mutated_registry(tmp_path, mutate_entry={"recovery_owner": None})
    with pytest.raises(RuntimeBindingUnavailable):
        build_authorized_driver(path, "wrenmp4", profile_dir=str(tmp_path / "p"))


# ---------------------------------------------------------------- authorized battery


def test_admitted_entry_constructs(tmp_path):
    path = _admitted_registry(tmp_path)
    driver = build_authorized_driver(path, "wrenmp4",
                                     profile_dir=str(tmp_path / "p"))
    assert isinstance(driver, AuthorizedCdpDriver)
    assert driver.authorized_cdp_port == 9333
    assert driver._started is False  # construction launches nothing


def test_start_launches_bound_profile(tmp_path, monkeypatch):
    ledger = _install_pw_stub(monkeypatch)
    path = _admitted_registry(tmp_path)
    driver = build_authorized_driver(path, "wrenmp4",
                                     profile_dir=str(tmp_path / "p"),
                                     proxy_url="http://127.0.0.1:8080")
    driver.start()
    try:
        assert ledger["launches"] == 1
        kw = ledger["last_launch_kw"]
        assert kw["user_data_dir"] == str(tmp_path / "p")
        assert kw["proxy"] == {"server": "http://127.0.0.1:8080"}
        assert any(a.startswith("--remote-debugging-port=9333")
                   for a in kw["args"])
        assert driver._started is True
        assert driver._page is not None and driver._cdp is not None
    finally:
        driver.stop()
    assert driver._started is False
    assert ledger["stops"] >= 2  # cdp detach + ctx close + pw stop (any subset)


def test_start_refuses_foreign_profile(tmp_path, monkeypatch):
    _install_pw_stub(monkeypatch)
    path = _admitted_registry(tmp_path)
    driver = build_authorized_driver(path, "wrenmp4",
                                     profile_dir=str(tmp_path / "p"))
    from tools.xguerrilla.drivers.base import DriverError
    with pytest.raises(DriverError):
        driver.start(profile_dir=str(tmp_path / "other"))
    assert driver._started is False  # refused before any launch effect


def test_stop_on_never_started_is_noop(tmp_path):
    path = _admitted_registry(tmp_path)
    driver = build_authorized_driver(path, "wrenmp4",
                                     profile_dir=str(tmp_path / "p"))
    driver.stop()  # must not raise, must close nothing
    assert driver._started is False


def test_stale_started_flag_closes_nothing(tmp_path, monkeypatch):
    """A stale ``_started=True`` must never satisfy the lifecycle alone.

    Mirrors the pinned refusal semantics: the flag is derived state, not
    authority. stop() on a stale flag must be a no-op, not a cleanup guess.
    """
    ledger = _install_pw_stub(monkeypatch)
    path = _admitted_registry(tmp_path)
    driver = build_authorized_driver(path, "wrenmp4",
                                     profile_dir=str(tmp_path / "p"))
    driver._started = True  # forge the flag without launching anything
    driver.stop()
    assert ledger["stops"] == 0  # nothing was launched; nothing is closed


def test_factory_seam_matches_builder(tmp_path):
    path = _admitted_registry(tmp_path)
    via_factory = factory(str(path), "wrenmp4",
                          profile_dir=str(tmp_path / "p"))
    via_builder = build_authorized_driver(path, "wrenmp4",
                                          profile_dir=str(tmp_path / "p2"))
    assert type(via_factory) is type(via_builder) is AuthorizedCdpDriver
    assert via_factory.handle == via_builder.handle == "wrenmp4"


def test_base_driver_stubs_still_refuse(tmp_path):
    """The adapter must not weaken the shipped drivers: base CdpDriver still refuses."""
    from tools.xguerrilla.drivers import cdp as cdp_mod

    base = cdp_mod.CdpDriver()
    with pytest.raises(RuntimeBindingUnavailable):
        base.start("some-profile")
    base_stale = cdp_mod.CdpDriver()
    base_stale._started = True
    with pytest.raises(RuntimeBindingUnavailable):
        base_stale.start("some-profile")
    with pytest.raises(RuntimeBindingUnavailable):
        base.stop()
