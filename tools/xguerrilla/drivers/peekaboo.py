"""Runtime activation and cleanup are unavailable until incumbent binding.

The retained method bodies support isolated fake-object regressions.
They do not provide a supported way to attach a real browser or profile.

OS-level driver: keystrokes posted at the window server by the ``peekaboo`` CLI.

This is the preferred backend on the runtime box because the site sees what a
Mac sees: real key events arriving at a real Chrome window, not synthesized
DevTools protocol frames. The cost is that every interaction is a subprocess,
so this module is deliberate about two things:

* **Chunked typing.** One ``peekaboo type`` per key would spend more time in
  ``fork/exec`` than a human spends typing the sentence. One call for the whole
  post would land as a single instantaneous word — the exact signature of an
  automation. So ``type_plan`` asks :func:`..segment.segment` for bursts of
  4–10 keys, types each burst in one call with ``--delay`` set to that burst's
  own median interval, and sleeps the planned pause between bursts itself.

* **A timeout on every single call.** A wedged accessibility query would
  otherwise hang a worker slot forever, holding the profile lock with it. Every
  ``subprocess.run`` here carries an explicit limit, scaled up for long bursts.

Deletions travel as ``peekaboo press delete --count N`` (batched, since the CLI
supports a repeat count); set ``press_supports_count = False`` on the instance
for a build without it and they are pressed one at a time instead.

Everything is namespaced per profile: ``start()`` launches Chrome with
``--user-data-dir=PROFILE_DIR`` so two slots never share cookies, and ``stop()``
kills only the process tree rooted at that directory."""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

from ..runtime_boundary import refuse_runtime

from .base import DriverError, Key, collapse, is_challenge, parse_coords
from .segment import chunk_delay_ms, median, segment

__all__ = ["PeekabooDriver"]

DEFAULT_APP = "Google Chrome"

# Markers a ``peekaboo`` call leaves behind when it handed the keystrokes to the
# window server and only then failed to *prove* delivery. They differ per build
# and per verb: 4.6 emits ``dispatched_unverified`` / ``mutation_dispatched`` on
# one path and ``state: indeterminate`` / ``effect: unverifiable`` /
# ``candidateFieldTooLarge`` on another. All of them mean "look, don't retry",
# so the driver counts them in ``self.unverified`` and lets the caller read the
# field back; anything else still raises.
DISPATCHED_UNVERIFIED = (
    "dispatched_unverified",
    '"mutation_dispatched":true',
    '"state":"indeterminate"',
    '"effect":"unverifiable"',
    "outcomeisindeterminate",
    "candidatefieldtoolarge",
)

_URL_RE = re.compile(r"https?://[^\s\"'<>\\]+")

#: Key names as they appear in step files, mapped to peekaboo chord tokens.
_KEY_ALIASES = {
    "enter": "return",
    "return": "return",
    "tab": "tab",
    "escape": "escape",
    "esc": "escape",
    "space": "space",
    "backspace": "delete",
    "delete": "delete",
    "forwarddelete": "forward_delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "cmd": "cmd",
    "command": "cmd",
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "option",
    "opt": "option",
    "option": "option",
    "shift": "shift",
}

#: Roles that mean "a person can press this", used to break label ties.
_CLICKABLE_HINTS = ("button", "link", "menuitem", "tab", "checkbox", "radio", "text field", "textfield", "searchfield")


class PeekabooDriver:
    """Chrome driven through the ``peekaboo`` CLI, one subprocess call at a time."""

    name = "peekaboo"

    #: Executable name, resolved on PATH (tests monkeypatch ``shutil.which``).
    binary = "peekaboo"
    #: The app every call targets.
    app = DEFAULT_APP
    #: macOS launcher used by ``start()``; ``open -n`` forces a second instance.
    launcher = "open"
    #: peekaboo >= 4.2 accepts ``press delete --count N``.
    press_supports_count = True

    def __init__(
        self,
        *,
        app: str = DEFAULT_APP,
        binary: str = "peekaboo",
        timeout_s: float = 45.0,
        launch_timeout_s: float = 30.0,
        focus_timeout_s: float = 30.0,
        capture_timeout_s: float = 30.0,
        press_supports_count: bool | None = None,
    ) -> None:
        self.app = app or DEFAULT_APP
        self.binary = binary or "peekaboo"
        self.timeout_s = float(timeout_s)
        self.launch_timeout_s = float(launch_timeout_s)
        self.focus_timeout_s = float(focus_timeout_s)
        self.capture_timeout_s = float(capture_timeout_s)
        if press_supports_count is not None:
            self.press_supports_count = bool(press_supports_count)

        self.profile_dir = ""
        self.proxy_url = ""
        self.headless = False
        self.focused = False
        self.url = ""
        self.typed_keys = 0
        self.unverified = 0
        self.pid: int | None = None
        self.last_snapshot: dict = {}
        self._elements: list[dict] = []
        self._started = False

    # ------------------------------------------------------------------ lifecycle

    def start(self, profile_dir: str, proxy_url: str = "", headless: bool | None = None) -> None:
        """Refuse unbound activation before import, launch or cleanup."""
        refuse_runtime("PeekabooDriver.start")

    def stop(self) -> None:
        """Unbound cleanup cannot close or kill an original owner."""
        refuse_runtime("PeekabooDriver.stop")

    # ----------------------------------------------------------------- navigation

    def goto(self, url: str) -> None:
        """Focus the omnibox, type ``url`` and press return."""
        self._require_started()
        target = str(url or "").strip()
        if not target:
            raise DriverError("goto() needs a url")
        self._peekaboo(
            "app", "focus", *self._target(), "--foreground", timeout=min(self.timeout_s, 20.0)
        )
        self._peekaboo("press", "cmd+l", *self._target(), "--foreground", timeout=min(self.timeout_s, 20.0))
        self._peekaboo("press", "cmd+a", *self._target(), "--foreground", timeout=min(self.timeout_s, 20.0))
        self._type_text(target, 25)
        self._peekaboo("press", "return", *self._target(), "--foreground", timeout=min(self.timeout_s, 20.0))
        self.url = target
        self._sleep_ms(400.0)

    # ---------------------------------------------------------------- observation

    def snapshot(self) -> dict:
        """Return ``{url, title, signed_in, challenge}`` plus the window's elements.

        Uses a real capture — ``peekaboo see --json -o <file>`` — because
        ``--no-screenshot --tree`` is broken on Peekaboo 4.6 through the remote
        bridge: it answers ``success: false`` with a ResolutionError and
        ``data: null`` (1,116 bytes) while the same call with ``-o`` returns the
        whole 652-element tree. Capture by PID, and an empty envelope is never
        reported as a clean page: the call is retried once after a fresh
        ``app focus --pid`` and then raises, because a silent empty snapshot is
        how a child types into a wall believing it is home.
        """
        self._require_started()
        shot = os.path.join(self._capture_dir(), f"see-{os.getpid()}.png")
        problem = ""
        # Four attempts, not two. On 4.6 the observer fails with "inconsistent
        # response evidence: window-context window title" on roughly one capture
        # in four to six (measured: 6 failures in 40 back-to-back calls, in runs
        # of at most two in a row), and the failure clears on its own. A fresh
        # ``app focus --pid`` helps but is itself refused often enough that it
        # must not gate the retry; the backoff is what actually wins.
        for attempt in (1, 2, 3, 4):
            # check=False: a failing ``see`` is the *expected* flake here, so the
            # loop must own the decision — ``_run``'s raise would abort attempt 1.
            proc = self._run(
                [self.binary, "see", *self._target(), "--json", "-o", shot],
                timeout=max(self.timeout_s, self.capture_timeout_s),
                check=False,
            )
            raw_text = proc.stdout or ""
            data = _load_json(raw_text)
            payload = _payload(data)
            elements = _elements(payload)
            if payload and elements:
                break
            problem = (
                _error_message(raw_text)
                or _error_message(proc.stderr or "")
                or (proc.stderr or "").strip()[:200]
                or f"see exited {proc.returncode} with no AX payload"
            )
            if attempt < 4:
                if attempt % 2:
                    self._peekaboo(
                        "app",
                        "focus",
                        *self._target(),
                        "--foreground",
                        timeout=min(self.timeout_s, 20.0),
                        check=False,
                    )
                time.sleep(0.4 + 0.4 * attempt)
        else:
            raise DriverError(
                f"peekaboo see returned no elements for {self.app!r} four times: {problem[:200]}"
            )
        try:
            os.unlink(shot)
        except OSError:
            pass
        blob = _text_blob(payload) or raw_text
        snap = {
            "url": _find_url(payload, elements, blob),
            "title": _find_title(payload, elements),
            "signed_in": _signed_in(blob),
            "challenge": is_challenge(blob),
            "elements": elements,
        }
        self._elements = elements
        self.last_snapshot = snap
        if snap["url"]:
            self.url = snap["url"]
        return snap

    def _capture_dir(self) -> str:
        """A place for throwaway captures: the profile dir, else the temp dir."""
        base = self.profile_dir or tempfile.gettempdir()
        try:
            os.makedirs(base, exist_ok=True)
            return base
        except OSError:
            return tempfile.gettempdir()

    def find(self, target: str) -> dict:
        """Resolve a label (or ``'x,y'``) to a box: ``{id, role, label, value, x, y, ...}``.

        Matching folds case and whitespace and prefers clickable roles, so
        ``'post'`` lands on the Post button rather than on a stray text
        occurrence. Raises :class:`DriverError` with a short role list when
        nothing matches — a driver reports, the worker decides.
        """
        self._require_started()
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
                "score": 3.0,
            }
        want = collapse(str(target or ""))
        if not want:
            raise DriverError("find() needs a label or 'x,y'")
        elements = self.snapshot()["elements"]
        best: dict | None = None
        best_score = 0.0
        for element in elements:
            score = _match_score(element, want)
            if score > best_score:
                best, best_score = element, score
        if best is None or best_score <= 0:
            raise DriverError(_miss_hint(target, elements))
        return dict(best, target=str(target).strip(), score=best_score)

    # -------------------------------------------------------------------- actions

    def click(self, target: str) -> None:
        """Click raw ``'x,y'`` coordinates, or an element resolved by label."""
        self._require_started()
        coords = parse_coords(target)
        if coords:
            self._peekaboo(
                "click",
                "--at",
                f"{coords[0]:g},{coords[1]:g}",
                *self._target(),
                "--foreground",
                timeout=min(self.timeout_s, 20.0),
            )
            return
        hit = self.find(target)
        if hit.get("id"):
            self._peekaboo(
                "click", "--on", str(hit["id"]), *self._target(), "--foreground",
                timeout=min(self.timeout_s, 20.0),
            )
        else:
            self._peekaboo(
                "click", str(target).strip(), *self._target(), "--foreground",
                timeout=min(self.timeout_s, 20.0),
            )

    def type_plan(self, keys: list[Key]) -> None:
        """Type a planned keystroke sequence, one burst per ``peekaboo type`` call.

        Each chunk is typed with ``--delay`` equal to its own median interval and
        the pause before it is slept by this process, so the gaps the persona
        planned survive the batching. Consecutive backspaces inside a chunk go
        out as a single batched ``peekaboo press delete``.
        """
        self._require_started()
        keys = list(keys or [])
        if not keys:
            return
        plan_delay = chunk_delay_ms(keys)
        for chunk, pre_delay in segment(keys):
            self._sleep_ms(pre_delay)
            delay = chunk_delay_ms(chunk, plan_delay)
            for kind, run in _runs(chunk):
                if kind == "backspace":
                    self._press_delete(len(run), delay)
                else:
                    self._type_text("".join(getattr(k, "text", "") or "" for k in run), delay)
            self.typed_keys += len(chunk)

    def paste(self, text: str, target: str | None = None) -> str:
        """Put ``text`` on the clipboard (``pbcopy``) and press ``cmd+v``.

        This backend drives a real window through the accessibility CLI, which
        cannot read a field back, so a caller that wants proof must use the CDP
        driver: asked to verify, this raises instead of pretending.
        """
        if target is not None:
            raise DriverError(
                "peekaboo cannot read a field back; verify with the cdp driver or a screenshot"
            )
        self._require_started()
        payload = str(text or "")
        if payload:
            self._run(["pbcopy"], input_text=payload, timeout=15.0)
        self._peekaboo("press", "cmd+v", *self._target(), "--foreground", timeout=min(self.timeout_s, 20.0))

    def key(self, name: str) -> None:
        """Press one key or chord: ``enter``, ``tab``, ``cmd+enter``, ``cmd+a``."""
        self._require_started()
        chord = _chord(name)
        if not chord:
            raise DriverError("key() needs a key name")
        self._peekaboo("press", chord, *self._target(), "--foreground", timeout=min(self.timeout_s, 20.0))

    def screenshot(self, path: str) -> str:
        """Write a PNG of ``self.app``'s active window to ``path``; return the path.

        Primary path is one frame from ``peekaboo capture live`` (which writes to
        a directory); the newest frame is copied to ``path``. If the recorder
        yields nothing, a single-shot ``peekaboo see --no-elements --path`` is
        used instead. Either way a zero-byte or missing file is an error.
        """
        self._require_started()
        dest = os.path.abspath(os.path.expanduser(str(path or "")))
        if not dest:
            raise DriverError("screenshot() needs a path")
        parent = os.path.dirname(dest)
        if parent:
            os.makedirs(parent, exist_ok=True)
        staging = tempfile.mkdtemp(prefix="xg-shot-", dir=self.profile_dir or None)
        try:
            self._peekaboo(
                "capture",
                "live",
                "--mode",
                "window",
                "--app",
                self.app,
                "--path",
                staging,
                "--duration",
                "900ms",
                "--max-frames",
                "1",
                "--idle-fps",
                "0.5",
                "--active-fps",
                "0.5",
                "--resolution-cap",
                "1440",
                "--json",
                timeout=self.capture_timeout_s,
                check=False,
            )
            frames = sorted(
                glob.glob(os.path.join(staging, "**", "*.png"), recursive=True),
                key=lambda p: os.path.getmtime(p),
            )
            if frames:
                shutil.copyfile(frames[-1], dest)
            else:
                self._peekaboo(
                    "see", *self._target(), "--no-elements", "--path", dest, "--json",
                    timeout=self.capture_timeout_s, check=False,
                )
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
            raise DriverError(f"peekaboo produced no screenshot at {dest}")
        return dest

    # ------------------------------------------------------------------- internals

    def _binary_available(self) -> bool:
        if os.path.isabs(self.binary):
            return os.path.exists(self.binary)
        return shutil.which(self.binary) is not None

    def _require_started(self) -> None:
        if not self._started:
            raise DriverError("driver.start() has not run; call it before driving the browser")

    def _proxy_server(self) -> str:
        """Chrome's ``--proxy-server`` spelling: scheme + host + port, no credentials."""
        split = urlsplit(self.proxy_url)
        if not split.hostname:
            return self.proxy_url
        scheme = split.scheme or "http"
        port = f":{split.port}" if split.port else ""
        return f"{scheme}://{split.hostname}{port}"

    def _pid(self) -> int | None:
        """The PID of the Chrome launched for THIS profile, if it is up yet.

        Focusing by name right after launch fails on Peekaboo 4.6 with
        ``INTERACTION_FAILED: Application inventory was unavailable while
        resolving 'Google Chrome'``; an exact PID sidesteps the inventory.
        """
        if not self.profile_dir:
            return None
        try:
            proc = subprocess.run(
                # ``--`` matters: the pattern itself starts with a dash and
                # pgrep would otherwise parse it as an option and print nothing.
                ["pgrep", "-f", "--", f"--user-data-dir={self.profile_dir}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        pids = [int(part) for part in (proc.stdout or "").split() if part.isdigit()]
        return min(pids) if pids else None

    def _await_focus(self) -> None:
        """Poll ``peekaboo app focus`` until it reports success, or give up loudly."""
        deadline = time.monotonic() + self.focus_timeout_s
        detail = "no output"
        while time.monotonic() < deadline:
            pid = self._pid()
            target = ["--pid", str(pid)] if pid else [self.app]
            proc = self._run(
                [self.binary, "app", "focus", *target, "--foreground", "--json"],
                timeout=min(self.timeout_s, 20.0),
                check=False,
            )
            if proc.returncode == 0 and _json_ok(proc.stdout):
                self.focused = True
                self.pid = pid
                return
            detail = (proc.stderr or proc.stdout or f"rc={proc.returncode}").strip()
            if pid is None:
                detail = f"chrome for {self.profile_dir} is not up yet ({detail[:200]})"
            time.sleep(0.5)
        raise DriverError(
            f"peekaboo app focus {self.app!r} did not succeed within {self.focus_timeout_s:g}s: {detail[:300]}"
        )

    def _target(self) -> list[str]:
        """Addressing args for a peekaboo subcommand: ``--pid`` when known.

        ``--app "Google Chrome"`` fails on this box with
        ``Application target 'Google Chrome' matched more than one running
        process`` because several jobs keep Chrome instances alive; an exact PID
        is the only unambiguous handle. The PID is cached once it is known (a
        fresh fork per keystroke would be wasteful) and re-resolved from the
        profile's ``--user-data-dir`` when it is not. ``--app`` survives only as
        the fallback for a dead profile.
        """
        pid = self.pid or self._pid()
        if pid:
            self.pid = pid
            return ["--pid", str(pid)]
        return ["--app", self.app]

    def _peekaboo(self, *args: str, timeout: float | None = None, check: bool = True):
        return self._run([self.binary, *args], timeout=timeout, check=check)

    def _run(self, argv, *, timeout: float | None = None, check: bool = True, input_text: str | None = None):
        """Run ``argv`` with a hard timeout; raise :class:`DriverError` on failure."""
        limit = float(timeout or self.timeout_s)
        try:
            proc = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=limit,
                input=input_text,
            )
        except FileNotFoundError as exc:
            raise DriverError(f"{argv[0]!r} is not on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise DriverError(
                f"{argv[0]} timed out after {limit:g}s: {' '.join(str(a) for a in argv[1:3])}".strip()
            ) from exc
        except OSError as exc:
            raise DriverError(f"{argv[0]} could not run: {exc}") from exc
        if check and proc.returncode != 0:
            blob = ((proc.stdout or "") + (proc.stderr or "")).replace(" ", "").replace("\n", "")
            if any(marker in blob for marker in DISPATCHED_UNVERIFIED):
                # The keys went to the window server; the CLI just could not
                # prove it. The caller confirms by reading the field back, so
                # failing here would abort every burst.
                self.unverified += 1
                return proc
            raise DriverError(_failure(argv, proc))
        return proc

    def _sleep_ms(self, ms: float) -> None:
        """Sleep a planned gap. The single timing seam, so tests can record it."""
        if ms and ms > 0:
            time.sleep(float(ms) / 1000.0)

    def _typing_timeout(self, keys: int, delay_ms: float) -> float:
        """A timeout that scales with the burst, since ``type`` waits it out."""
        return max(self.timeout_s, 15.0 + (keys * float(delay_ms) / 1000.0) * 1.5)

    def _type_text(self, text: str, delay_ms: float) -> None:
        """One ``peekaboo type`` call for a whole burst."""
        payload = text or ""
        if not payload:
            return
        self._peekaboo(
            "type",
            payload,
            *self._target(),
            "--delay",
            f"{int(round(float(delay_ms)))}ms",
            "--foreground",
            timeout=self._typing_timeout(len(payload), delay_ms),
        )

    def _press_delete(self, count: int, delay_ms: float) -> None:
        """Delete ``count`` characters, batched with ``--count`` where supported."""
        if count <= 0:
            return
        limit = self._typing_timeout(count, delay_ms)
        if self.press_supports_count and count > 1:
            self._peekaboo(
                "press",
                "delete",
                "--count",
                str(int(count)),
                *self._target(),
                "--foreground",
                "--delay",
                f"{int(round(float(delay_ms)))}ms",
                timeout=limit,
            )
            return
        for _ in range(int(count)):
            self._peekaboo(
                "press",
                "delete",
                *self._target(),
                "--foreground",
                "--delay",
                f"{int(round(float(delay_ms)))}ms",
                timeout=limit,
            )


# ------------------------------------------------------------------ module helpers


def _load_json(text: str) -> dict:
    """Parse the CLI's JSON envelope; a non-JSON body becomes ``{"text": ...}``."""
    body = (text or "").strip()
    if not body:
        return {}
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return {"text": body}
    return data if isinstance(data, dict) else {"data": data}


def _payload(data) -> dict:
    """Unwrap ``{"success": ..., "data": {...}}`` to the payload it carries."""
    if isinstance(data, dict) and isinstance(data.get("data"), (dict, list)):
        return data["data"] if isinstance(data["data"], dict) else {"elements": data["data"]}
    return data if isinstance(data, dict) else {}


def _json_ok(text: str) -> bool:
    """True unless the envelope says ``success: false`` (empty output is fine)."""
    body = (text or "").strip()
    if not body:
        return True
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return True
    return not (isinstance(data, dict) and data.get("success") is False)


def _failure(argv, proc) -> str:
    """A one-line failure, preferring the CLI's own ``error.message``."""
    detail = _error_message(proc.stdout) or _error_message(proc.stderr)
    if not detail:
        detail = (proc.stderr or proc.stdout or "").strip()
    detail = re.sub(r"\s+", " ", detail)[:400]
    what = " ".join(str(a) for a in argv[:3])
    return f"{what} failed (rc={proc.returncode})" + (f": {detail}" if detail else "")


def _error_message(text: str) -> str:
    body = (text or "").strip()
    if not body.startswith("{"):
        return ""
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        return ""
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or "")
    return str(error or "")


def _text_blob(value, _depth: int = 0) -> str:
    """Every string in a decoded payload, joined with newlines.

    The challenge test must run over *decoded* text. Scanning the raw JSON
    source misses the most common wall of all: a banner that wraps in the AX
    tree arrives in the source as ``"Unusual\\nActivity"`` — a backslash and an
    ``n`` — which no ``\\s+`` can match, so a real challenge reads as clean and
    the child keeps typing into a verification page.
    """
    if _depth > 24:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return "\n".join(_text_blob(item, _depth + 1) for item in value.values())
    if isinstance(value, (list, tuple)):
        return "\n".join(_text_blob(item, _depth + 1) for item in value)
    return ""


def _as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _elements(payload) -> list[dict]:
    """Every accessibility node in the payload, flattened to uniform boxes."""
    found: list[dict] = []

    def walk(node, depth: int = 0) -> None:
        if depth > 60:
            return
        if isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
            return
        if not isinstance(node, dict):
            return
        role = node.get("role")
        if isinstance(role, str) and role.strip():
            found.append(_element(node))
        for key, value in node.items():
            if key in ("raw", "debug_logs", "image", "metadata"):
                continue
            if isinstance(value, (dict, list)):
                walk(value, depth + 1)

    walk(payload)
    return found


def _element(node: dict) -> dict:
    """Normalize one AX node into ``{id, role, label, value, x, y, width, height}``."""
    label = ""
    for key in ("label", "title", "description", "role_description", "placeholder", "text"):
        value = node.get(key)
        if isinstance(value, str) and value.strip():
            label = value.strip()
            break
    value = node.get("value")
    if isinstance(value, dict):
        value = value.get("label") or value.get("title") or json.dumps(value)[:200]
    elif isinstance(value, (list, tuple)):
        value = json.dumps(value)[:200]
    x, y, width, height = _frame(node)
    ident = ""
    for key in ("id", "element_id", "elementId", "peekaboo_id", "AXIdentifier"):
        raw = node.get(key)
        if isinstance(raw, (str, int)) and str(raw).strip():
            ident = str(raw).strip()
            break
    return {
        "id": ident or None,
        "role": str(node.get("role") or "").strip(),
        "label": label,
        "value": str(value).strip() if value is not None else "",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def _frame(node: dict) -> tuple[float, float, float, float]:
    """Pull ``(x, y, w, h)`` out of whichever shape the CLI used this release."""
    for key in ("frame", "bounds", "rect", "box"):
        raw = node.get(key)
        if isinstance(raw, (list, tuple)) and len(raw) >= 4:
            try:
                return tuple(float(v) for v in raw[:4])  # type: ignore[return-value]
            except (TypeError, ValueError):
                pass
        if isinstance(raw, dict):
            try:
                return (
                    float(raw.get("x", raw.get("left", 0)) or 0),
                    float(raw.get("y", raw.get("top", 0)) or 0),
                    float(raw.get("width", raw.get("w", 0)) or 0),
                    float(raw.get("height", raw.get("h", 0)) or 0),
                )
            except (TypeError, ValueError):
                pass
    position, size = _as_dict(node.get("position")), _as_dict(node.get("size"))
    try:
        return (
            float(position.get("x", position.get("left", 0)) or 0),
            float(position.get("y", position.get("top", 0)) or 0),
            float(size.get("width", size.get("w", 0)) or 0),
            float(size.get("height", size.get("h", 0)) or 0),
        )
    except (TypeError, ValueError):
        return (0.0, 0.0, 0.0, 0.0)


def _find_url(payload: dict, elements: list[dict], blob: str) -> str:
    """Best-effort current URL: explicit fields, then the omnibox, then a literal."""
    for container in (payload, _as_dict(payload.get("window")), _as_dict(payload.get("page"))):
        if not isinstance(container, dict):
            continue
        for key in ("url", "current_url", "href", "address"):
            value = container.get(key)
            if isinstance(value, str) and _URL_RE.match(value.strip()):
                return value.strip()
    for element in elements:
        role = element.get("role", "").lower()
        value = (element.get("value") or "").strip()
        if "text field" in role or "textfield" in role or "combobox" in role:
            if _URL_RE.match(value):
                return value
    match = _URL_RE.search(blob or "")
    return match.group(0).rstrip(").,;'\"") if match else ""


def _find_title(payload: dict, elements: list[dict]) -> str:
    """Window title: explicit fields first, then the AX window node."""
    for container in (payload, _as_dict(payload.get("window"))):
        for key in ("title", "window_title"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for element in elements:
        if "window" in element.get("role", "").lower() and element.get("label"):
            return element["label"]
    return ""


def _signed_in(blob: str) -> bool:
    """Heuristic: a session shows a sign-out affordance and no sign-in wall."""
    low = (blob or "").lower()
    if re.search(r"sign\s*out|log\s*out|logout|signout", low):
        return True
    if re.search(r"sign\s*in|log\s*in|signin|login", low):
        return False
    return False


def _match_score(element: dict, want: str) -> float:
    """Score one element against a folded label; 0 means no match."""
    best = 0.0
    for field in ("label", "value"):
        have = collapse(element.get(field) or "")
        if not have:
            continue
        if have == want:
            best = max(best, 3.0)
        elif len(have) >= 3 and (have.startswith(want) or (len(want) >= 3 and want.startswith(have))):
            best = max(best, 2.0)
        elif len(want) >= 3 and want in have:
            best = max(best, 1.5)
    if best and any(hint in element.get("role", "").lower() for hint in _CLICKABLE_HINTS):
        best += 0.5
    return best


def _miss_hint(target: str, elements: list[dict], limit: int = 8) -> str:
    """Explain a failed lookup with the labels that were actually on screen."""
    seen: list[str] = []
    for element in elements:
        label = (element.get("label") or "").strip()
        if label and label not in seen:
            seen.append(label)
        if len(seen) >= limit:
            break
    tail = ", ".join(repr(s) for s in seen) if seen else "no labelled elements"
    return f"no element matched {target!r}; on screen: {tail}"


def _runs(chunk) -> list[tuple[str, list]]:
    """Group a chunk into consecutive same-kind runs (chars / backspaces)."""
    runs: list[tuple[str, list]] = []
    for key in chunk:
        kind = "backspace" if getattr(key, "kind", "char") == "backspace" else "char"
        if runs and runs[-1][0] == kind:
            runs[-1][1].append(key)
        else:
            runs.append((kind, [key]))
    return runs


def _chord(name: str) -> str:
    """Normalize a key or chord name to peekaboo's spelling, e.g. ``CMD+Enter``."""
    raw = str(name or "").strip()
    if not raw:
        return ""
    parts = [p for p in re.split(r"\s*\+\s*", raw) if p]
    mapped = [_KEY_ALIASES.get(p.strip().lower(), p.strip().lower()) for p in parts]
    return "+".join(mapped)
