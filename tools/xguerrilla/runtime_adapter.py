"""Source-qualified runtime adapter: registry-bound activation of the CDP driver.

This module is the *only* sanctioned way to turn :class:`CdpDriver`'s retained
op bodies into a live browser. It never patches the drivers, the CLI, or the
boundary: ``CdpDriver.start``/``stop`` keep their refusal stubs forever, and
this adapter subclasses them behind a complete five-binding registry gate.

The gate binds, before any import, launch or cleanup effect:

1. **Account**      — ``registry.launchable(doc, handle)`` is ``[]``: the entry
                      exists and its state is ``admitted``.
2. **Approved item** — the entry's ``domain`` record is itself ``admitted``;
                      an admitted identity pointing at an unadmitted domain is
                      a launch without an approved destination.
3. **Original holders** — the entry's ``binding`` block is fully provisioned:
                      ``email_mailbox``, ``proxy_slot``, ``cdp_port`` and
                      ``totp_custodian`` are all non-null. A null slot means
                      the incumbent owner of that surface was never recorded.
4. **Receipts**     — both admission receipts are content-pinned, not just
                      shape-checked: the file at ``receipt.path`` must exist
                      and hash to ``receipt.sha256``. The registry validates
                      shape at write time; the runtime authorizer verifies
                      the evidence itself.
5. **Profile owner** — ``recovery_owner`` is non-null on the entry (and on the
                      domain, which the registry already requires).

Any failure is ``RuntimeBindingUnavailable`` — the same envelope, exit code and
audit shape as every other refusal in this package. With today's registry
(every entry ``state: proposed``, every receipt ``null``) this module refuses
unconditionally, which is the intended fail-closed posture until an admission
ceremony records real receipts.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from . import registry
from .drivers import cdp as cdp_mod
from .drivers.base import DriverError
from .runtime_boundary import RuntimeBindingUnavailable, refuse_runtime

__all__ = ["AuthorizedCdpDriver", "build_authorized_driver", "factory"]

#: Binding slots whose incumbent owner must be recorded before launch.
_BINDING_SLOTS = ("email_mailbox", "proxy_slot", "cdp_port", "totp_custodian")

_RECEIPT_KEYS = {"path", "sha256"}


def _verify_receipt_pinned(where: str, receipt: Any, receipt_root: Path) -> None:
    """Refuse unless the receipt is ``{path, sha256}`` and the file hashes to it.

    Shape comes first (mirroring ``registry._validate_receipt``), then the
    content pin: the digest is the evidence, so the runtime checks it against
    the actual bytes rather than trusting the field.
    """
    if not isinstance(receipt, dict):
        refuse_runtime(f"runtime_adapter.receipt[{where}]")
    extra = set(receipt) - _RECEIPT_KEYS
    missing = _RECEIPT_KEYS - set(receipt)
    if extra or missing:
        refuse_runtime(f"runtime_adapter.receipt[{where}]")
    path_field = receipt.get("path")
    sha_field = receipt.get("sha256")
    if not isinstance(path_field, str) or not path_field.strip():
        refuse_runtime(f"runtime_adapter.receipt[{where}].path")
    if not isinstance(sha_field, str) or len(sha_field) != 64:
        refuse_runtime(f"runtime_adapter.receipt[{where}].sha256")
    candidate = Path(path_field)
    if not candidate.is_absolute():
        candidate = receipt_root / candidate
    try:
        material = candidate.read_bytes()
    except OSError:
        refuse_runtime(f"runtime_adapter.receipt[{where}] unreadable: {path_field}")
    digest = hashlib.sha256(material).hexdigest()
    if digest != sha_field.lower():
        refuse_runtime(
            f"runtime_adapter.receipt[{where}] digest mismatch: "
            f"{path_field} hashes to {digest}, registry pins {sha_field.lower()}"
        )


def _entry_for(doc: dict, handle: str) -> dict | None:
    for row in doc.get("entries") or []:
        if isinstance(row, dict) and row.get("handle") == handle:
            return row
    return None


def _domain_for(doc: dict, name: Any) -> dict | None:
    for row in doc.get("domains") or []:
        if isinstance(row, dict) and row.get("domain") == name:
            return row
    return None


class AuthorizedCdpDriver(cdp_mod.CdpDriver):
    """A ``CdpDriver`` whose lifecycle is bound to one admitted registry entry.

    Construction happens only through :func:`build_authorized_driver`, after
    the five-binding gate has passed. ``start``/``stop`` are the real launch
    and cleanup paths (authored here; the base stubs remain untouched), and
    every retained op body — ``goto``, ``snapshot``, ``find``, ``click``,
    ``type_plan``, ``paste``, ``key``, ``screenshot`` — works unchanged on
    the handles this lifecycle mounts.
    """

    def __init__(self, *, entry: dict, domain: dict, profile_dir: str,
                 proxy_url: str = "", cdp_port: int = 0,
                 headless: bool = False, timeout_ms: int = 30_000,
                 viewport=(1280, 900), channel: str | None = None) -> None:
        super().__init__(timeout_ms=timeout_ms, viewport=viewport, channel=channel)
        self.entry = entry
        self.domain = domain
        self.handle = str(entry.get("handle", ""))
        self.authorized_profile_dir = str(profile_dir)
        self.authorized_proxy_url = str(proxy_url or "")
        self.authorized_cdp_port = int(cdp_port or 0)
        self.authorized_headless = bool(headless)

    # ------------------------------------------------------------------ lifecycle

    def start(self, profile_dir: str = "", proxy_url: str = "",
              headless: bool | None = None) -> None:
        """Launch the bound identity's browser: persistent context + CDP session.

        The arguments must agree with the authorized binding — the driver may
        only launch the profile, proxy and port the registry admission covers.
        ``headless`` is presentation, not identity, and may be overridden.
        """
        if profile_dir and str(profile_dir) != self.authorized_profile_dir:
            raise DriverError(
                f"start() profile_dir {profile_dir!r} is not the authorized "
                f"profile {self.authorized_profile_dir!r}")
        if proxy_url and str(proxy_url) != self.authorized_proxy_url:
            raise DriverError(
                f"start() proxy_url is not the authorized proxy slot "
                f"(slot {self.entry.get('binding', {}).get('proxy_slot')!r})")
        effective_headless = self.authorized_headless if headless is None else bool(headless)

        # Lazy import, exactly as the base class documents: a missing optional
        # dependency must never take down anything that imports this module.
        from playwright.sync_api import sync_playwright  # noqa: PLC0415

        os.makedirs(self.authorized_profile_dir, exist_ok=True)
        launch_args = list(cdp_mod._LAUNCH_ARGS)
        if self.authorized_cdp_port:
            # A port is part of identity: two identities on one port is a
            # collision, so the admitted port is pinned into the launch.
            launch_args.append(f"--remote-debugging-port={self.authorized_cdp_port}")
        proxy_setting = ({"server": self.authorized_proxy_url}
                         if self.authorized_proxy_url else None)

        self._pw = sync_playwright().start()
        try:
            self._ctx = self._pw.chromium.launch_persistent_context(
                user_data_dir=self.authorized_profile_dir,
                headless=effective_headless,
                args=launch_args,
                proxy=proxy_setting,
                channel=self.channel or None,
                viewport=self.viewport,
            )
        except Exception:
            self._pw.stop()
            self._pw = None
            raise
        self._ctx.set_default_timeout(self.timeout_ms)
        self._page = (self._ctx.pages[0] if self._ctx.pages
                      else self._ctx.new_page())
        self._cdp = self._ctx.new_cdp_session(self._page)
        self.profile_dir = self.authorized_profile_dir
        self.proxy_url = self.authorized_proxy_url
        self.headless = effective_headless
        self.url = self._page.url or "about:blank"
        self._started = True

    def stop(self) -> None:
        """Close only what this lifecycle launched; a stale flag closes nothing."""
        if not self._started or self._page is None:
            return
        ctx, pw, cdp = self._ctx, self._pw, self._cdp
        self._started = False
        self._page = self._ctx = self._cdp = None
        self._pw = None
        for closer in (getattr(cdp, "detach", None),
                       getattr(ctx, "close", None),
                       getattr(pw, "stop", None)):
            if callable(closer):
                closer()


def build_authorized_driver(registry_path: str | os.PathLike, handle: str, *,
                            profile_dir: str, proxy_url: str = "",
                            headless: bool = False,
                            timeout_ms: int = 30_000,
                            viewport=(1280, 900),
                            channel: str | None = None) -> AuthorizedCdpDriver:
    """Construct the authorized driver for ``handle`` or refuse, binding all five.

    Reads the registry (a read is not an effect), runs the five-binding gate,
    and only then returns a driver whose ``start()`` is the real launch path.
    With no admission on disk this always refuses — fail-closed by design.
    """
    root = Path(registry_path)
    try:
        doc, errors = registry.load_registry(str(root))
    except RuntimeBindingUnavailable:
        raise
    except Exception as exc:  # unreadable yaml, missing file: no binding
        refuse_runtime(f"runtime_adapter.registry[{root}] unreadable: {exc}")
    if doc is None or errors:
        refuse_runtime(
            f"runtime_adapter.registry[{root}] refused: "
            + ("; ".join(errors) if errors else "no document"))
    receipt_root = root.parent

    # 1. Account: entry exists and is admitted.
    problems = registry.launchable(doc, handle)
    if problems:
        refuse_runtime(f"runtime_adapter.launch[{handle}]")
    entry = _entry_for(doc, handle)
    if entry is None:  # unreachable when launchable is consistent; belt and braces
        refuse_runtime(f"runtime_adapter.launch[{handle}]")

    # 2. Approved item: the destination domain is admitted too.
    domain = _domain_for(doc, entry.get("domain"))
    if domain is None:
        refuse_runtime(
            f"runtime_adapter.domain[{entry.get('domain')!r}] has no record")
    if domain.get("state") != "admitted":
        refuse_runtime(
            f"runtime_adapter.domain[{entry.get('domain')!r}] is "
            f"{domain.get('state')!r}, not admitted")

    # 3. Original holders: every binding slot names its incumbent owner.
    binding = entry.get("binding") or {}
    for slot in _BINDING_SLOTS:
        value = binding.get(slot)
        if value is None or (isinstance(value, str) and not value.strip()):
            refuse_runtime(
                f"runtime_adapter.binding[{handle}].{slot} is unbound — the "
                "incumbent owner of this surface was never recorded")

    # 4. Receipts: content-pinned, entry and domain.
    _verify_receipt_pinned(f"entry:{handle}", entry.get("admission_receipt"),
                           receipt_root)
    _verify_receipt_pinned(f"domain:{entry.get('domain')}",
                           domain.get("admission_receipt"), receipt_root)

    # 5. Profile owner: someone holds recovery for this identity.
    if not str(entry.get("recovery_owner") or "").strip():
        refuse_runtime(f"runtime_adapter.owner[{handle}] recovery_owner is null")

    cdp_port_raw = binding.get("cdp_port")
    if isinstance(cdp_port_raw, bool) or not isinstance(cdp_port_raw, int):
        refuse_runtime(
            f"runtime_adapter.binding[{handle}].cdp_port {cdp_port_raw!r} is not a port")
    cdp_port: int = cdp_port_raw
    if proxy_url and not str(proxy_url).strip():
        proxy_url = ""

    return AuthorizedCdpDriver(
        entry=entry, domain=domain, profile_dir=str(profile_dir),
        proxy_url=str(proxy_url or ""), cdp_port=cdp_port,
        headless=bool(headless), timeout_ms=int(timeout_ms),
        viewport=viewport, channel=channel,
    )


def factory(registry_path: str | os.PathLike, handle: str, *,
            profile_dir: str, **kwargs: Any) -> AuthorizedCdpDriver:
    """``module:factory`` seam target (``shadow --driver`` / ``XG_DRIVER_FACTORY``).

    Thin alias over :func:`build_authorized_driver`; the CLI seam imports the
    named module and calls the named attribute, and this is that attribute.
    """
    return build_authorized_driver(registry_path, handle,
                                   profile_dir=profile_dir, **kwargs)
