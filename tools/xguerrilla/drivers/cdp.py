"""Runtime activation and cleanup are unavailable until incumbent binding.

The retained method bodies support isolated fake-object regressions.
They do not provide a supported way to attach a real browser or profile.

Headless-capable driver: Chrome through Playwright's sync API over the DevTools Protocol.

Two design notes:

* **Playwright is imported inside** :meth:`CdpDriver.start`, never at module
  import. The runtime box may not have it installed, and a missing optional
  dependency must not take down the segmentation tests, the peekaboo backend, or
  the harness's own import graph.

* **Keystrokes are dispatched one by one, at the planned time.** The point of
  this backend is volume, but not uniformity: :func:`..typing.to_cdp` has already
  turned each key into a real ``Input.dispatchKeyEvent`` with its own offset, and
  this module sleeps each offset's delta before sending it. A backspace keeps its
  own ``Backspace`` keycode, so the page's own handlers see a deletion rather
  than a text mutation.

The context is persistent and pinned to ``PROFILE_DIR``, so a slot's cookies
survive a restart exactly as they would in a real Chrome profile."""
from __future__ import annotations

import base64
import os
import re
import subprocess
import time
from urllib.parse import unquote, urlsplit

from ..runtime_boundary import refuse_runtime

from .base import DriverError, Key, collapse, is_challenge, parse_coords, to_cdp

__all__ = ["CdpDriver"]

#: ``key(name)`` spellings mapped to Playwright's key names.
PLAYWRIGHT_KEYS = {
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "escape": "Escape",
    "esc": "Escape",
    "space": "Space",
    "backspace": "Backspace",
    "delete": "Delete",
    "up": "ArrowUp",
    "down": "ArrowDown",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    "home": "Home",
    "end": "End",
    "pageup": "PageUp",
    "pagedown": "PageDown",
    "cmd": "Meta",
    "command": "Meta",
    "ctrl": "Control",
    "control": "Control",
    "alt": "Alt",
    "option": "Alt",
    "shift": "Shift",
}

#: Accessibility roles that carry no label worth matching.
_SKIP_ROLES = {
    "none", "generic", "RootWebArea", "StaticText", "InlineTextBox", "LineBreak",
    "paragraph", "list", "listitem", "image", "presentation", "none",
}
#: Ceiling on snapshot elements; a long timeline does not get to cost 4k nodes.
_MAX_ELEMENTS = 400

_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=Translate",
]


class CdpDriver:
    """Chrome driven over CDP by Playwright, headless or headful."""

    name = "cdp"

    def __init__(self, *, timeout_ms: int = 30_000, viewport=(1280, 900), channel: str | None = None) -> None:
        self.timeout_ms = int(timeout_ms)
        self.viewport = tuple(viewport) if viewport else None
        self.channel = channel
        self.profile_dir = ""
        self.proxy_url = ""
        self.headless = False
        self.url = ""
        self.status = 0
        self.typed_keys = 0
        self.last_snapshot: dict = {}
        self._pw = None
        self._ctx = None
        self._page = None
        self._cdp = None
        self._started = False

    # ------------------------------------------------------------------ lifecycle

    def start(self, profile_dir: str, proxy_url: str = "", headless: bool | None = None) -> None:
        """Refuse unbound activation before import, launch or cleanup."""
        refuse_runtime("CdpDriver.start")

    def stop(self) -> None:
        """Unbound cleanup cannot close or kill an original owner."""
        refuse_runtime("CdpDriver.stop")

    # ----------------------------------------------------------------- navigation

    def goto(self, url: str) -> None:
        """Navigate to ``url`` and wait for the document, then for quiet.

        The response status is kept on the driver, because "the dwell timer
        started" is not the same fact as "the page arrived": a proxy that
        answers ``407`` or a DNS failure still leaves a ``page`` object behind
        with an empty ``about:blank``-shaped body. A status of 400 or above, a
        Chrome error page, or a document with no markup at all raises.
        """
        page = self._require_started()
        target = str(url or "").strip()
        if not target:
            raise DriverError("goto() needs a url")
        self.status = 0
        try:
            response = page.goto(target, wait_until="domcontentloaded", timeout=self.timeout_ms)
            self.status = int(getattr(response, "status", 0) or 0) if response else 0
            page.wait_for_load_state("networkidle", timeout=min(self.timeout_ms, 15_000))
        except Exception as exc:  # a slow feed never settles; not fatal
            if not page.url or page.url == "about:blank":
                raise DriverError(f"could not open {target}: {exc}") from exc
            problem = self._load_error(page)
            if problem:
                raise DriverError(f"could not open {target}: {problem}") from exc
        self.url = page.url or target
        problem = self._load_error(page)
        if problem:
            raise DriverError(f"could not open {target}: {problem}")

    # ---------------------------------------------------------------- observation

    def snapshot(self) -> dict:
        """Return ``{url, title, signed_in, challenge, status, elements}``.

        The challenge check runs the shared regex over ``page.content()`` — the
        server-rendered markup is where an interstitial announces itself. The
        element list comes from the accessibility tree over CDP, so it is the
        same shape the peekaboo backend produces and ``find()`` can score it.

        An empty document is never reported as a clean page: the driver raises,
        the same way it does for an error page. That is the difference between
        "the child is on the timeline" and "the child typed into a wall".
        """
        page = self._require_started()
        try:
            html = page.content()
            title = page.title()
        except Exception as exc:
            raise DriverError(f"could not read the page: {exc}") from exc
        problem = self._load_error(page, html)
        if problem:
            raise DriverError(f"page did not load: {problem}")
        elements = self._elements()
        snap = {
            "url": page.url,
            "title": title or "",
            "signed_in": _signed_in(html),
            "challenge": is_challenge(html),
            "status": self.status,
            "elements": elements,
        }
        self.last_snapshot = snap
        self.url = snap["url"] or self.url
        return snap

    def find(self, target: str) -> dict:
        """Resolve a label or ``'x,y'`` to a viewport box: ``{x, y, width, height, ...}``.

        Accessibility names are tried first (button, link, textbox, label), so
        ``'Post'`` finds the control even when the visible text is split across
        spans, then plain text as a last resort.
        """
        page = self._require_started()
        coords = parse_coords(target)
        if coords:
            return {
                "id": None,
                "role": "point",
                "label": str(target).strip(),
                "value": "",
                "x": coords[0],
                "y": coords[1],
                "width": 0.0,
                "height": 0.0,
                "target": str(target).strip(),
            }
        label = str(target or "").strip()
        if not label:
            raise DriverError("find() needs a label or 'x,y'")
        locator = self._locate(label)
        try:
            box = locator.bounding_box()
        except Exception as exc:
            raise DriverError(f"could not measure {label!r}: {exc}") from exc
        if not box:
            raise DriverError(f"{label!r} matched but has no layout box (hidden?)")
        return {
            "id": None,
            "role": "element",
            "label": label,
            "value": "",
            "x": float(box["x"]),
            "y": float(box["y"]),
            "width": float(box["width"]),
            "height": float(box["height"]),
            "target": label,
        }

    # -------------------------------------------------------------------- actions

    def click(self, target: str) -> None:
        """Click raw coordinates, or the element resolved from ``target``."""
        page = self._require_started()
        coords = parse_coords(target)
        try:
            if coords:
                page.mouse.click(coords[0], coords[1])
            else:
                self._locate(str(target).strip()).click(timeout=self.timeout_ms)
        except DriverError:
            raise
        except Exception as exc:
            raise DriverError(f"could not click {target!r}: {exc}") from exc

    def type_plan(self, keys: list[Key], target: str | None = None, expect: str | None = None) -> str:
        """Replay a planned keystroke sequence as paced CDP key events.

        When ``target`` is given the page is asked what the field holds after the
        last key: a keyboard dispatch that lands on nobody's focus returns
        happily and types into the void, so "dispatched" alone is not evidence.
        An unchanged field is a :class:`DriverError`, and when ``expect`` is
        given the text must actually contain it — a partial match is what
        distinguishes "typed" from "typed somewhere else". The observed text is
        returned.
        """
        self._require_started()
        keys = list(keys or [])
        previous = 0.0
        for event in to_cdp(keys):
            at = float(event.get("at") or 0.0)
            gap = at - previous
            if gap > 0:
                time.sleep(gap / 1000.0)
            previous = at
            self._dispatch(event)
        self.typed_keys += len(keys)
        if not target:
            return ""
        observed = self._field_text(str(target))
        if not observed.strip():
            raise DriverError(
                f"typed {len(keys)} keys but {target!r} is still empty — nothing had focus"
            )
        if expect is not None and _squash(expect) not in _squash(observed):
            raise DriverError(
                f"typed text did not land in {target!r}: expected {expect!r}, field holds {observed!r}"
            )
        return observed

    def _field_text(self, target: str) -> str:
        """Current text of ``target``; refuses non-fields.

        ``inner_text`` on a submit button reads ``"Private Search"``, which is
        the trap that made a broken typing run look verified — so the tag decides
        which read is legitimate.
        """
        locator = self._locate(target)
        try:
            tag = locator.evaluate("e => e.tagName")
        except Exception as exc:
            raise DriverError(f"could not inspect {target!r}: {exc}") from exc
        if tag in ("INPUT", "TEXTAREA"):
            try:
                return locator.input_value(timeout=5_000)
            except Exception as exc:
                raise DriverError(f"could not read value of {target!r}: {exc}") from exc
        try:
            editable = locator.evaluate(
                "e => e.isContentEditable || e.getAttribute('role') === 'textbox'"
            )
        except Exception:
            editable = False
        if not editable:
            raise DriverError(f"{target!r} resolved to <{tag.lower()}>, which is not a text field")
        try:
            return locator.inner_text(timeout=5_000)
        except Exception as exc:
            raise DriverError(f"could not read text of {target!r}: {exc}") from exc

    def paste(self, text: str, target: str | None = None) -> str:
        """Insert ``text`` into the focused field, and prove it when ``target`` is given.

        ``Input.insertText`` is the default route because it is the only one
        measured to deliver the payload under headless Chromium on the worker box.
        The clipboard route (:meth:`clipboard_paste`) fires a real ``paste`` event
        whose data is empty there, so the field stays blank and nothing raises —
        the worst possible failure, because the harvester would record a post that
        never existed.

        Pass ``target`` to have the page read the field back; a mismatch raises
        :class:`DriverError` instead of being reported as a successful paste.
        """
        self._require_started()
        payload = str(text or "")
        if payload:
            if self._cdp is not None:
                try:
                    self._cdp.send("Input.insertText", {"text": payload})
                except Exception as exc:
                    raise DriverError(f"insertText failed: {exc}") from exc
            else:  # no CDP handle: the clipboard is all that is left
                self.clipboard_paste(payload)
        if target is None:
            return ""
        observed = self.read_value(target)
        if observed != payload:
            raise DriverError(
                f"pasted {len(payload)} chars but {target!r} holds {len(observed)}: {observed[:60]!r}"
            )
        return observed

    def clipboard_paste(self, text: str, target: str | None = None) -> str:
        """Put ``text`` on the system clipboard (``pbcopy``) and press ``Meta+V``.

        Kept for pages that only accept a genuine ``paste`` event. Measured on
        mini1 with headless Chromium 156: the page sees ``paste`` fire and the
        field stays empty, so this returns what the field really holds rather than
        claiming success.
        """
        page = self._require_started()
        payload = str(text or "")
        if payload:
            try:
                subprocess.run(
                    ["pbcopy"], input=payload, text=True, capture_output=True, timeout=15, check=True
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise DriverError(f"pbcopy failed: {exc}") from exc
        try:
            page.keyboard.press("Meta+V")
        except Exception as exc:
            raise DriverError(f"paste failed: {exc}") from exc
        return self.read_value(target) if target is not None else ""

    def key(self, name: str) -> None:
        """Press one key or chord: ``enter``, ``tab``, ``cmd+enter``."""
        page = self._require_started()
        chord = _playwright_chord(name)
        if not chord:
            raise DriverError("key() needs a key name")
        try:
            page.keyboard.press(chord)
        except Exception as exc:
            raise DriverError(f"could not press {name!r}: {exc}") from exc

    def screenshot(self, path: str) -> str:
        """Write a viewport PNG to ``path`` and return the path.

        Capture goes through ``Page.captureScreenshot`` first. Playwright's own
        ``page.screenshot()`` blocks on ``waiting for fonts to load`` — on a page
        reached over a proxy that has not finished its webfont fetches, the call
        spends the whole timeout there and then raises. The raw CDP capture has
        no such precondition, is answered from the compositor, and is what the
        harness needs; ``page.screenshot()`` stays as the fallback with
        animations disabled and caret hidden so a blinking cursor never salts
        the frame.
        """
        page = self._require_started()
        dest = os.path.abspath(os.path.expanduser(str(path or "")))
        if not dest:
            raise DriverError("screenshot() needs a path")
        parent = os.path.dirname(dest)
        if parent:
            os.makedirs(parent, exist_ok=True)
        png = b""
        if self._cdp is not None:
            try:
                result = self._cdp.send(
                    "Page.captureScreenshot",
                    {"format": "png", "fromSurface": True, "captureBeyondViewport": False},
                )
                png = base64.b64decode(result.get("data") or "")
            except Exception:
                png = b""
        if not png:
            try:
                page.screenshot(path=dest, full_page=False, animations="disabled", caret="hide")
            except Exception as exc:
                raise DriverError(f"screenshot failed: {exc}") from exc
        else:
            try:
                with open(dest, "wb") as handle:
                    handle.write(png)
            except OSError as exc:
                raise DriverError(f"screenshot could not be written to {dest}: {exc}") from exc
        if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
            raise DriverError(f"no screenshot was written to {dest}")
        return dest

    def read_value(self, target: str) -> str:
        """Return the current ``value`` of the input/textarea resolved from ``target``.

        Verification, not typing: the caller asks the page what it holds instead
        of trusting that a dispatch landed.
        """
        page = self._require_started()
        locator = self._locate(str(target or "").strip())
        try:
            return locator.input_value(timeout=self.timeout_ms)
        except Exception as exc:
            raise DriverError(f"could not read the value of {target!r}: {exc}") from exc

    # ------------------------------------------------------------------- internals

    def _require_started(self):
        if not self._started or self._page is None:
            raise DriverError("driver.start() has not run; call it before driving the browser")
        return self._page

    def _locate(self, label: str):
        """First *visible* element matching ``label``; a CSS selector is honoured.

        Two passes: form fields first, everything else second. Both are needed
        because a label like "Search" hits a real textarea on one page and a
        submit button on the next, and role queries are not dependable — the
        DuckDuckGo textarea is announced by placeholder and label but reports
        neither ``textbox`` nor ``searchbox`` from ``get_by_role`` (measured:
        both return 0 nodes on a loaded page).
        """
        page = self._page
        if not page:
            raise DriverError("driver.start() has not run")
        text = str(label or "").strip()
        if text and _looks_like_selector(text):
            try:
                locator = page.locator(text)
                if locator.count() > 0:
                    visible = _first_visible(locator, strict=False)
                    if visible is not None:
                        return visible
            except Exception:
                pass
        fields = (
            lambda: page.get_by_placeholder(text, exact=False),
            lambda: page.get_by_label(text, exact=False),
            lambda: page.get_by_role("textbox", name=text, exact=False),
            lambda: page.get_by_role("searchbox", name=text, exact=False),
        )
        others = (
            lambda: page.get_by_role("textbox", name=text, exact=False),
            lambda: page.get_by_role("button", name=text, exact=False),
            lambda: page.get_by_role("link", name=text, exact=False),
            lambda: page.get_by_placeholder(text, exact=False),
            lambda: page.get_by_label(text, exact=False),
            lambda: page.get_by_text(text, exact=False),
        )
        fallback = None
        for group, field_only in ((fields, True), (others, False)):
            for build in group:
                try:
                    locator = build()
                    if locator.count() == 0:
                        continue
                    found = _first_visible(locator, strict=False, field_only=field_only)
                    if found is not None:
                        return found
                    fallback = fallback or locator.first
                except Exception:  # a bad role query must not end the search
                    continue
        if fallback is not None:
            return fallback
        raise DriverError(f"no element or text matched {label!r}")

    def _load_error(self, page, html: str | None = None) -> str:
        """Return why the current document is not a page, or ``''`` when it is one.

        Three signals, cheapest first: Chrome's error-page scheme, an HTTP status
        at or above 400 (a ``407`` proxy answer and a ``502`` from a dead gateway
        both land here), and a document with no markup. Fonts and images are not
        consulted — a page that is still painting is still a page.
        """
        current = str(getattr(page, "url", "") or "")
        if current.startswith("chrome-error://"):
            title = ""
            try:
                title = page.title() or ""
            except Exception:
                pass
            return f"Chrome error page ({current}{' — ' + title if title else ''})"
        if self.status >= 400:
            return f"HTTP {self.status} (proxy refused the request)" if self.status in (407, 502, 503) else f"HTTP {self.status}"
        if html is None:
            try:
                html = page.content()
            except Exception as exc:
                return f"no document: {exc}"
        if len(html or "") < 200 and page.url and page.url != "about:blank":
            return f"document is {len(html)} bytes — the page did not load"
        return ""

    def _elements(self) -> list[dict]:
        """Flatten the accessibility tree into driver-shaped elements.

        Only named, non-generic nodes are kept — the harness matches labels, and
        an unnamed ``generic`` div is noise that costs a round-trip to measure.
        A tree that cannot be read yields ``[]`` rather than an exception: the
        page itself already succeeded, and ``find()`` reporting "nothing matched"
        is more honest than a snapshot blowing up.
        """
        if self._cdp is None:
            return []
        try:
            tree = self._cdp.send("Accessibility.getFullAXTree")
        except Exception:
            return []
        out: list[dict] = []
        for node in tree.get("nodes") or []:
            role = str((node.get("role") or {}).get("value") or "")
            if not role or role in _SKIP_ROLES:
                continue
            if node.get("ignored"):
                continue
            name = str((node.get("name") or {}).get("value") or "").strip()
            if not name:
                continue
            value = str((node.get("value") or {}).get("value") or "")
            out.append(
                {
                    "id": node.get("backendDOMNodeId"),
                    "role": role,
                    "label": name,
                    "value": value.replace("\n", " ")[:200],
                    "x": 0.0,
                    "y": 0.0,
                    "width": 0.0,
                    "height": 0.0,
                    "target": name,
                }
            )
            if len(out) >= _MAX_ELEMENTS:
                break
        return out

    def _dispatch(self, event: dict) -> None:
        """Send one key down/up pair from a :func:`..typing.to_cdp` dict."""
        if self._cdp is None:
            raise DriverError("no CDP session; call start() first")
        key = str(event.get("key") or "")
        text = str(event.get("text") or "")
        params = {
            "key": key,
            "code": str(event.get("code") or ""),
            "windowsVirtualKeyCode": int(event.get("vk") or 0),
            "nativeVirtualKeyCode": int(event.get("vk") or 0),
            "modifiers": 8 if event.get("shift") else 0,
        }
        if text and key != "Backspace":
            down = dict(params, type="keyDown", text=text, unmodifiedText=text)
        else:
            down = dict(params, type="rawKeyDown")
        try:
            self._cdp.send("Input.dispatchKeyEvent", down)
            self._cdp.send("Input.dispatchKeyEvent", dict(params, type="keyUp"))
        except Exception as exc:
            raise DriverError(f"CDP key dispatch failed for {key!r}: {exc}") from exc


_SELECTOR_HINTS = ("#", ".", "[", ">", "input", "textarea", "button", "a[", "[role=")


def _looks_like_selector(text: str) -> bool:
    """True when ``text`` reads as CSS rather than a human label."""
    raw = text.strip()
    if not raw or " " in raw and "[" not in raw:
        return raw.startswith(("#", ".", "["))
    return raw.startswith(_SELECTOR_HINTS)


_FIELD_TAGS = ("INPUT", "TEXTAREA", "SELECT")


def _squash(text: str) -> str:
    """Whitespace- and case-insensitive form, for comparing typed text."""
    return " ".join(str(text or "").split()).casefold()


def _first_visible(locator, strict: bool = True, limit: int = 8, field_only: bool = False):
    """First visible entry of ``locator`` (bounded scan), else ``None``.

    ``strict`` raises when nothing in the scan is visible; the loose mode lets
    the caller keep looking at the next candidate set. ``field_only`` narrows to
    form controls, which is how a textarea beats the label div wrapped around
    it.
    """
    try:
        count = min(locator.count(), limit)
    except Exception:
        return None
    for index in range(count):
        candidate = locator.nth(index)
        try:
            if not candidate.is_visible():
                continue
            if field_only and candidate.evaluate("e => e.tagName") not in _FIELD_TAGS:
                continue
            return candidate
        except Exception:
            continue
    if strict:
        raise DriverError("matched, but nothing visible")
    return None


def _proxy_config(proxy_url: str) -> dict:
    """Turn ``http://user:pass@host:port`` into Playwright's proxy dict.

    Chromium is launched with ``--proxy-server``, and that flag does **not**
    accept credentials in the URL — everything before the ``@`` is swallowed as
    part of the host and every CONNECT comes back ``407``. Playwright takes the
    credentials as separate ``username``/``password`` keys and installs them via
    the auth handler. Measured on the worker box: the embedded form reached
    ``HTTP 407`` with a 0-byte document, the split form reached ``HTTP 200``.
    """
    raw = str(proxy_url or "").strip()
    parts = urlsplit(raw)
    server = f"{parts.scheme or 'http'}://{parts.hostname or ''}"
    if parts.port:
        server += f":{parts.port}"
    config = {"server": server}
    if parts.username:
        config["username"] = unquote(parts.username)
    if parts.password:
        config["password"] = unquote(parts.password)
    return config


def _playwright_chord(name: str) -> str:
    """Normalize ``CMD+Enter`` into Playwright's ``Meta+Enter``."""
    raw = str(name or "").strip()
    if not raw:
        return ""
    parts = [p for p in re.split(r"\s*\+\s*", raw) if p]
    return "+".join(PLAYWRIGHT_KEYS.get(p.strip().lower(), p.strip()) for p in parts)


def _signed_in(html: str) -> bool:
    """Heuristic over the rendered markup: sign-out present means a live session."""
    low = (html or "").lower()
    if re.search(r"sign\s*out|log\s*out|logout|signout", low):
        return True
    return False
