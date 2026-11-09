"""Driver-layer contracts: burst segmentation, the peekaboo argv shape, backend choice.

The peekaboo tests never touch a real browser or a real CLI. ``subprocess.run``
is replaced by a recorder, so the assertions are about the *exact* thing the
driver would have executed — argv, order and the pause it slept between bursts —
which is the part that has to be right before anything is pointed at a live
window.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib  # noqa: E402

from tools.xguerrilla import typing as xg_typing  # noqa: E402
from tools.xguerrilla.drivers import peekaboo as peekaboo_mod  # noqa: E402

# ``drivers/__init__`` re-exports the *function* named ``choose``, which shadows
# the submodule of the same name on the package, so ``import ...choose as m``
# hands back the function. Resolve the real module through importlib.
choose_mod = importlib.import_module("tools.xguerrilla.drivers.choose")
from tools.xguerrilla.drivers.base import (  # noqa: E402
    Driver,
    DriverError,
    Key,
    is_challenge,
    parse_coords,
)
from tools.xguerrilla.runtime_boundary import RuntimeBindingUnavailable
from tools.xguerrilla.drivers.cdp import CdpDriver  # noqa: E402
from tools.xguerrilla.drivers.choose import choose  # noqa: E402
from tools.xguerrilla.drivers.peekaboo import PeekabooDriver  # noqa: E402
from tools.xguerrilla.drivers.segment import (  # noqa: E402
    MAX_CHUNK,
    MIN_CHUNK,
    chunk_delay_ms,
    segment,
)
from tools.xguerrilla.persona import Persona  # noqa: E402

APP = "Google Chrome"
# A pinned pid: on this box four Chrome instances are alive, so the driver must
# address the window by pid (see PeekabooDriver._target) and never by name.
PID = "4321"


# --------------------------------------------------------------------------- fakes


class Proc:
    """Stand-in for ``subprocess.CompletedProcess``."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


SEE_PAYLOAD = {
    "success": True,
    "data": {
        "window": {"title": "Home / X", "url": "https://x.com/home"},
        "elements": [
            {
                "id": "pb_1",
                "role": "AXButton",
                "label": "Post",
                "frame": {"x": 1100, "y": 220, "width": 80, "height": 36},
            },
            {
                "id": "pb_2",
                "role": "AXStaticText",
                "label": "Unusual\nActivity",
                "frame": [10, 20, 300, 20],
            },
        ],
    },
}


class FakeRunner:
    """Records every argv; answers the CLI subcommands the driver issues."""

    def __init__(self, see: dict | None = None, see_rc: int = 0, pgrep_stdout: str = "") -> None:
        self.calls: list[dict] = []
        self.see = SEE_PAYLOAD if see is None else see
        self.see_rc = see_rc
        self.pgrep_stdout = pgrep_stdout

    def __call__(self, argv, **kwargs):
        argv = list(argv)
        self.calls.append(
            {
                "argv": argv,
                "timeout": kwargs.get("timeout"),
                "input": kwargs.get("input"),
            }
        )
        if argv[:1] == ["pgrep"]:
            # no live pid in tests -> focus falls back to the app name
            return Proc(stdout=self.pgrep_stdout)
        if argv[:3] == ["peekaboo", "app", "focus"]:
            return Proc(stdout=json.dumps({"success": True, "data": {"focused": True}}))
        if argv[:2] == ["peekaboo", "see"]:
            if self.see_rc:
                return Proc(stderr="boom: window not found", returncode=self.see_rc)
            return Proc(stdout=json.dumps(self.see))
        if argv[:1] == ["pbcopy"]:
            return Proc()
        return Proc(stdout=json.dumps({"success": True, "data": {}}))

    # -- assertions helpers -------------------------------------------------
    def argvs(self, prefix: tuple[str, ...]) -> list[list[str]]:
        return [c["argv"] for c in self.calls if tuple(c["argv"][: len(prefix)]) == prefix]


class Shim:
    """A ``shutil`` stand-in: the driver needs ``which``, ``copyfile`` and ``rmtree``."""

    def __init__(self, which_result: str | None) -> None:
        import shutil as real

        self.which = lambda name: which_result if name == "peekaboo" else None
        self.copyfile = real.copyfile
        self.rmtree = real.rmtree


def _synthetic_started(driver, profile):
    """Private test state only; every process seam is replaced by FakeRunner.

    No production activation method is called, unlocked or monkeypatched.
    """
    driver.profile_dir = str(profile)
    driver._started = True
    driver.focused = True
    driver.pid = int(PID)
    return driver


@pytest.fixture()
def runner(monkeypatch, tmp_path):
    """A PeekabooDriver wired to a fake CLI, already started on a temp profile."""
    fake = FakeRunner()
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", fake)
    monkeypatch.setattr(peekaboo_mod, "shutil", Shim("/opt/homebrew/bin/peekaboo"))
    driver = PeekabooDriver()
    sleeps: list[float] = []
    monkeypatch.setattr(driver, "_sleep_ms", lambda ms: sleeps.append(float(ms)))
    _synthetic_started(driver, str(tmp_path / "profile"))
    driver.pid = int(PID)  # as _await_focus would leave it on a live box
    fake.calls.clear()
    return driver, fake, sleeps, str(tmp_path / "profile")


def keys_from(text: str, *, step: float = 65.0, start: float = 300.0) -> list[Key]:
    """A literal keystroke plan: one char per ``step`` ms from ``start``."""
    out: list[Key] = []
    clock = start
    for ch in text:
        out.append(Key(t=clock, kind="char", text=ch))
        clock += step
    return out


# ------------------------------------------------------------------ segment invariants


def test_segment_invariants_on_a_real_plan():
    """A plan from typing.plan() survives segmentation with every invariant intact."""
    persona = Persona(handle="child7", cell="cell7", seed=11)  # type: ignore[call-arg]
    keys = xg_typing.plan("gm, shipping the driver layer today. more soon", persona)
    assert len(keys) > 20

    chunks = segment(keys)
    assert chunks, "a non-empty plan must produce at least one burst"

    sizes = [len(chunk) for chunk, _ in chunks]
    assert all(size <= MAX_CHUNK for size in sizes), f"chunk over {MAX_CHUNK}: {sizes}"
    assert all(size >= MIN_CHUNK for size in sizes[:-1]), f"short non-tail chunk: {sizes}"
    assert all(size >= 1 for size in sizes)

    # pre_delay is strictly positive for every chunk, including the first
    assert all(pre > 0 for _, pre in chunks)

    # nothing lost, nothing reordered
    flat = [key for chunk, _ in chunks for key in chunk]
    assert flat == keys

    # the pause before each later chunk is the real gap in the plan
    for (prev_chunk, _), (chunk, pre) in zip(chunks, chunks[1:]):
        gap = chunk[0].t - prev_chunk[-1].t
        assert pre == pytest.approx(gap, abs=0.11)


def test_segment_is_pure_and_idempotent():
    """Same plan in, same chunks out; the caller's list is untouched."""
    keys = keys_from("a" * 37)
    before = list(keys)
    first = segment(keys)
    second = segment(keys)
    assert [len(c) for c, _ in first] == [len(c) for c, _ in second]
    assert [p for _, p in first] == [p for _, p in second]
    assert keys == before
    assert segment([]) == []


def test_segment_splits_on_a_pause_longer_than_three_times_the_median():
    """A 900 ms hesitation ends the burst and becomes that chunk's pre_delay."""
    keys = keys_from("a" * 8, step=80.0, start=200.0)
    keys += [Key(t=keys[-1].t + 900.0 + 80.0 * i, kind="char", text="b") for i in range(8)]
    chunks = segment(keys)
    starts = [chunk[0].t for chunk, _ in chunks]
    assert keys[8].t in starts, "the burst must break at the hesitation"
    jump_index = starts.index(keys[8].t)
    assert chunks[jump_index][1] == pytest.approx(900.0, abs=0.11)
    assert all(not (c[0].t <= keys[7].t < c[-1].t) for c, _ in chunks), "no chunk straddles the pause"


def test_segment_splits_where_a_backspace_run_starts():
    """Revisions are their own act: a delete run never shares a burst with a keypress."""
    keys = keys_from("a" * 8)
    keys += [Key(t=keys[-1].t + 60.0, kind="backspace", text="") for _ in range(5)]
    keys += keys_from("b" * 8, start=keys[-1].t + 60.0)
    chunks = segment(keys)
    holding_deletes = [c for c, _ in chunks if any(k.kind == "backspace" for k in c)]
    assert holding_deletes, "the deletes must land somewhere"
    assert all(all(k.kind == "backspace" for k in c) for c in holding_deletes)


def test_chunk_delay_is_the_rounded_median():
    """``--delay`` comes from the burst's own intervals, not from a global constant."""
    keys = keys_from("abcde", step=70.0)
    assert chunk_delay_ms(keys) == 70
    assert chunk_delay_ms([keys[0]]) >= 1, "a one-key burst still needs a positive delay"
    assert chunk_delay_ms([], 42.0) == 42


# ---------------------------------------------------------------- peekaboo argv shape


def test_start_refuses_before_launch_or_profile_creation(monkeypatch, tmp_path):
    fake = FakeRunner()
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", fake)
    monkeypatch.setattr(peekaboo_mod, "shutil", Shim("/synthetic/peekaboo"))
    profile = tmp_path / "profile-3"
    with pytest.raises(RuntimeBindingUnavailable, match="runtime_binding_unavailable"):
        PeekabooDriver().start(str(profile), proxy_url="http://fake.invalid:8000")
    assert fake.calls == []
    assert not profile.exists()


def test_unbound_start_never_uses_headless_or_missing_cli_as_a_fallback(monkeypatch, tmp_path):
    fake = FakeRunner()
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", fake)
    for available in ("/synthetic/peekaboo", None):
        monkeypatch.setattr(peekaboo_mod, "shutil", Shim(available))
        for headless in (False, True):
            with pytest.raises(RuntimeBindingUnavailable, match="runtime_binding_unavailable"):
                PeekabooDriver().start(str(tmp_path / "p"), headless=headless)
    assert fake.calls == []
    assert not (tmp_path / "p").exists()


def test_type_plan_types_bursts_with_exact_argv_and_paced_sleeps(runner):
    """Each burst is one ``type`` call at its own median delay, with the pause slept."""
    driver, fake, sleeps, _ = runner
    keys = keys_from("a" * 40, step=65.0, start=300.0)

    driver.type_plan(keys)

    types = fake.argvs(("peekaboo", "type"))
    assert 1 < len(types) < 40, "never one call per key, never one call for the post"
    assert len(types) == 4, f"40 keys at one interval should be four bursts, got {len(types)}"
    assert types[0] == [
        "peekaboo",
        "type",
        "a" * 10,
        "--pid",
        PID,
        "--delay",
        "65ms",
        "--foreground",
    ]

    # every key is typed exactly once, in order
    typed = "".join(call[2] for call in types)
    assert typed == "a" * 40

    # the sleep before each burst is the delay segment() planned
    assert sleeps == [pre for _, pre in segment(keys)]
    assert sleeps[0] == pytest.approx(300.0)
    assert all(pre > 0 for pre in sleeps)
    assert driver.typed_keys == 40


def test_type_plan_batches_a_delete_run_into_one_press(runner):
    """Consecutive backspaces go out as ``press delete --count N``, not N presses."""
    driver, fake, _, _ = runner
    keys = keys_from("a" * 8)
    keys += [Key(t=keys[-1].t + 60.0, kind="backspace") for _ in range(3)]
    keys += keys_from("b" * 8, start=keys[-1].t + 60.0)

    driver.type_plan(keys)

    presses = fake.argvs(("peekaboo", "press"))
    assert presses, "the delete run must be pressed"
    assert any("--count" in argv and argv[argv.index("--count") + 1] == "3" for argv in presses)
    assert not any(argv[2] == "backspace" for argv in presses), "delete is spelled 'delete'"


def test_type_plan_loops_deletes_when_the_cli_has_no_count(runner):
    """``press_supports_count = False`` degrades to one press per delete."""
    driver, fake, _, _ = runner
    driver.press_supports_count = False
    keys = keys_from("a" * 8)
    keys += [Key(t=keys[-1].t + 60.0, kind="backspace") for _ in range(3)]

    driver.type_plan(keys)

    deletes = [argv for argv in fake.argvs(("peekaboo", "press")) if argv[2] == "delete"]
    assert len(deletes) == 3
    assert not any("--count" in argv for argv in deletes)


def test_goto_focuses_the_omnibox_types_and_presses_return(runner):
    """``goto`` is the omnibox dance: focus, cmd+l, cmd+a, type, return."""
    driver, fake, _, _ = runner
    driver.goto("https://example.com/login")

    argvs = [call["argv"] for call in fake.calls]
    assert argvs[0][:4] == ["peekaboo", "app", "focus", "--pid"]
    assert argvs[0][4] == PID
    assert argvs[1] == ["peekaboo", "press", "cmd+l", "--pid", PID, "--foreground"]
    assert argvs[2] == ["peekaboo", "press", "cmd+a", "--pid", PID, "--foreground"]
    assert argvs[3][:3] == ["peekaboo", "type", "https://example.com/login"]
    assert argvs[-1] == ["peekaboo", "press", "return", "--pid", PID, "--foreground"]
    assert driver.url == "https://example.com/login"


def test_snapshot_reads_the_ax_tree_and_flags_a_challenge(runner):
    """``snapshot`` returns url/title/signed_in/challenge from ``peekaboo see``.

    The capture flag is load-bearing: on Peekaboo 4.6 ``--no-screenshot --tree``
    answers ``success: false`` with a ResolutionError and no elements, so a page
    that is really a wall would read as clean.
    """
    driver, fake, _, _ = runner
    snap = driver.snapshot()

    argv = fake.calls[0]["argv"]
    assert argv[:5] == ["peekaboo", "see", "--pid", PID, "--json"]
    assert "-o" in argv, "must capture for real, not ask for a screenshot-free tree"
    assert "--no-screenshot" not in argv
    assert snap["url"] == "https://x.com/home"
    assert snap["title"] == "Home / X"
    assert snap["challenge"] is True, "'Unusual\\nActivity' must trip the detector"
    assert "signed_in" in snap
    assert driver.url == "https://x.com/home"


def test_snapshot_never_reports_an_empty_envelope_as_a_clean_page(monkeypatch, tmp_path):
    """``success: false`` with ``data: null`` must raise, not return a blank snapshot."""
    empty = {"success": False, "error": {"message": "ResolutionError"}, "data": None}
    fake = FakeRunner(see=empty)
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", fake)
    monkeypatch.setattr(peekaboo_mod, "shutil", Shim("/opt/homebrew/bin/peekaboo"))
    driver = PeekabooDriver()
    _synthetic_started(driver, str(tmp_path / "p"))
    with pytest.raises(DriverError, match="no elements"):
        driver.snapshot()
    sees = [c for c in fake.calls if c["argv"][:2] == ["peekaboo", "see"]]
    assert len(sees) == 4, "three retries, then give up"
    # Fake started state performs no activation focus; retries 1 and 3 focus.
    assert sum(c["argv"][:3] == ["peekaboo", "app", "focus"] for c in fake.calls) == 2


def test_run_tolerates_the_dispatched_unverified_exit(monkeypatch, tmp_path):
    """``type --foreground`` exits 1 once delivered; that is not a failure."""

    class Runner(FakeRunner):
        def __call__(self, argv, **kwargs):
            if argv[:2] == ["peekaboo", "type"]:
                self.calls.append({"argv": list(argv), "kwargs": kwargs})
                return Proc(stdout='{"state": "dispatched_unverified"}', returncode=1)
            return super().__call__(argv, **kwargs)

    fake = Runner()
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", fake)
    monkeypatch.setattr(peekaboo_mod, "shutil", Shim("/opt/homebrew/bin/peekaboo"))
    driver = PeekabooDriver()
    _synthetic_started(driver, str(tmp_path / "p"))
    driver._type_text("hi", 60.0)
    assert driver.unverified == 1

    class Bad(Runner):
        def __call__(self, argv, **kwargs):
            if argv[:2] == ["peekaboo", "type"]:
                self.calls.append({"argv": list(argv), "kwargs": kwargs})
                return Proc(stderr="boom", returncode=1)
            return FakeRunner.__call__(self, argv, **kwargs)

    driver2 = PeekabooDriver()
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", Bad())
    _synthetic_started(driver2, str(tmp_path / "p2"))
    with pytest.raises(DriverError, match="boom"):
        driver2._type_text("hi", 60.0)


@pytest.mark.parametrize(
    "payload",
    [
        # 4.6, type after foreground setup changed focus
        '{\n  "outcome" : {\n    "state" : "indeterminate",\n'
        '    "mutation_dispatched" : true,\n    "evidence" : "completion_unknown"\n  },\n'
        '  "success" : false\n}\n',
        # 4.6, the same call when the AX candidate field is oversized
        '{\n  "success" : false,\n  "effect" : "unverifiable",\n  "data" : null,\n'
        '  "error" : {\n    "message" : "Action outcome is indeterminate; observe the'
        ' target before retrying",\n    "code" : "UNKNOWN_ERROR",\n'
        '    "details" : "candidateFieldTooLarge"\n  }\n}\n',
    ],
    ids=["state-indeterminate", "effect-unverifiable"],
)
def test_run_tolerates_the_dispatched_but_unverified_shapes(monkeypatch, tmp_path, payload):
    """Both 4.6 shapes mean delivered-but-unproven, so neither may abort a burst."""

    class Runner(FakeRunner):
        def __call__(self, argv, **kwargs):
            if argv[:2] == ["peekaboo", "type"]:
                self.calls.append({"argv": list(argv), "kwargs": kwargs})
                return Proc(stdout="", stderr=payload, returncode=1)
            return super().__call__(argv, **kwargs)

    monkeypatch.setattr(peekaboo_mod.subprocess, "run", Runner())
    monkeypatch.setattr(peekaboo_mod, "shutil", Shim("/opt/homebrew/bin/peekaboo"))
    driver = PeekabooDriver()
    _synthetic_started(driver, str(tmp_path / "p"))
    driver._type_text("hi", 60.0)
    assert driver.unverified == 1


def test_snapshot_raises_driver_error_with_the_cli_words(monkeypatch, tmp_path):
    """A failing backend becomes a DriverError carrying stderr, never a bare exception."""
    fake = FakeRunner(see_rc=1)
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", fake)
    monkeypatch.setattr(peekaboo_mod, "shutil", Shim("/opt/homebrew/bin/peekaboo"))
    driver = PeekabooDriver()
    _synthetic_started(driver, str(tmp_path / "p"))
    with pytest.raises(DriverError, match="boom"):
        driver.snapshot()


def test_click_accepts_coordinates_or_a_label(runner):
    """``'x,y'`` goes out as ``--at``; a label is resolved to a clickable element."""
    driver, fake, _, _ = runner
    driver.click("120,240")
    assert fake.calls[-1]["argv"] == [
        "peekaboo",
        "click",
        "--at",
        "120,240",
        "--pid",
        PID,
        "--foreground",
    ]

    driver.click("post")
    assert fake.calls[-1]["argv"][:3] == ["peekaboo", "click", "--on"]
    assert fake.calls[-1]["argv"][3] == "pb_1", "the Post button, not the text node"


def test_key_normalizes_names_and_chords(runner):
    """Step files say ``ENTER``, ``cmd+Enter``; the CLI wants ``return``."""
    driver, fake, _, _ = runner
    driver.key("ENTER")
    driver.key("cmd+Enter")
    assert fake.calls[-2]["argv"][2] == "return"
    assert fake.calls[-1]["argv"][2] == "cmd+return"


def test_methods_refuse_to_run_before_start(monkeypatch):
    """A driver without a browser fails loudly instead of shelling out blindly."""
    monkeypatch.setattr(peekaboo_mod.subprocess, "run", FakeRunner())
    with pytest.raises(DriverError, match="start"):
        PeekabooDriver().snapshot()


# ------------------------------------------------------------------------- shared bits


def test_challenge_regex_is_case_insensitive_and_whitespace_tolerant():
    """A wrapped banner is still a banner."""
    assert is_challenge("Unusual\nActivity")
    assert is_challenge("WE NEED TO VERIFY YOUR ACCOUNT")
    assert is_challenge("arkose labs")
    assert not is_challenge("posted successfully")


def test_parse_coords_accepts_the_three_written_shapes():
    """Coordinates in step files come comma-separated, spaced, or both."""
    assert parse_coords("120,240") == (120.0, 240.0)
    assert parse_coords("120, 240") == (120.0, 240.0)
    assert parse_coords("120 240") == (120.0, 240.0)
    assert parse_coords("Post") is None


def test_both_backends_satisfy_the_protocol():
    """Method shape only: both runtime activation paths remain unavailable."""
    assert isinstance(PeekabooDriver(), Driver)
    assert isinstance(CdpDriver(), Driver)
    assert PeekabooDriver.name == "peekaboo"
    assert CdpDriver.name == "cdp"


def test_cdp_does_not_import_playwright_at_module_import():
    """A box without Playwright must still import the package and run these tests."""
    assert "playwright.sync_api" not in sys.modules


def test_choose_refuses_without_probing_or_constructing_a_backend(monkeypatch):
    calls = []
    monkeypatch.setattr(choose_mod.shutil, "which", lambda name: calls.append(name))
    for backend, headless in (("auto", False), ("auto", True),
                              ("cdp", False), ("peekaboo", False)):
        with pytest.raises(RuntimeBindingUnavailable, match="runtime_binding_unavailable"):
            choose(backend, headless)
    assert calls == []


def test_resolve_remains_descriptive_without_activating_a_backend(monkeypatch):
    monkeypatch.setattr(choose_mod.shutil, "which", lambda name: "/synthetic/peekaboo")
    assert choose_mod.resolve("auto") == "peekaboo"
    assert choose_mod.resolve("auto", True) == "cdp"
    monkeypatch.setattr(choose_mod.shutil, "which", lambda name: None)
    assert choose_mod.resolve("auto") == "cdp"
    with pytest.raises(DriverError):
        choose_mod.resolve("selenium")


# ---------------------------------------------------------------- paste contract


class _Store:
    """A page field that only changes when something really writes into it."""

    def __init__(self, value: str = "") -> None:
        self.value = value
        self.reads = 0

    def locator(self, target: str):
        store = self

        class _Loc:
            def input_value(self, timeout=None):
                store.reads += 1
                return store.value

        return _Loc()


class _Cdp:
    """Records CDP sends; optionally honours ``Input.insertText`` like a page would."""

    def __init__(self, store: _Store | None = None, lands: bool = True) -> None:
        self.sent: list[tuple[str, dict]] = []
        self.store = store
        self.lands = lands

    def send(self, method, params=None):
        self.sent.append((method, params or {}))
        if method == "Input.insertText" and self.store is not None and self.lands:
            self.store.value += params["text"]
        return {}


class _Keyboard:
    def __init__(self) -> None:
        self.pressed: list[str] = []

    def press(self, chord: str) -> None:
        self.pressed.append(chord)


class _Page:
    def __init__(self) -> None:
        self.keyboard = _Keyboard()


def _cdp_driver(store: _Store, cdp: _Cdp) -> CdpDriver:
    driver = CdpDriver()
    driver._started = True
    driver._page = _Page()
    driver._cdp = cdp
    driver._locate = store.locator  # type: ignore[assignment]
    return driver


def test_cdp_paste_inserts_the_text_and_reads_it_back():
    """insertText is the route that lands: the page's own value proves it."""
    store = _Store()
    cdp = _Cdp(store)
    driver = _cdp_driver(store, cdp)

    assert driver.paste("guerrilla bootstrap 4711", target="#q") == "guerrilla bootstrap 4711"
    assert cdp.sent == [("Input.insertText", {"text": "guerrilla bootstrap 4711"})]
    assert store.reads == 1


def test_cdp_paste_raises_when_the_field_stays_empty():
    """The clipboard route's silent failure mode: the page takes nothing, nobody notices."""
    store = _Store()
    driver = _cdp_driver(store, _Cdp(store, lands=False))

    with pytest.raises(DriverError, match="holds 0"):
        driver.paste("this never arrives", target="#q")


def test_cdp_paste_without_a_target_does_not_read_back():
    """Legacy callers keep the old shape: paste, no verification, no surprise."""
    store = _Store()
    driver = _cdp_driver(store, _Cdp(store))

    assert driver.paste("plain") == ""
    assert store.reads == 0


def test_clipboard_paste_reports_what_the_field_really_holds(monkeypatch):
    """``pbcopy`` + Meta+V fires a paste the page may ignore; never claim it landed."""
    from tools.xguerrilla.drivers import cdp as cdp_mod

    seen: list[dict] = []

    class _Run:
        def __init__(self, argv, **kw):
            seen.append({"argv": list(argv), **kw})

    monkeypatch.setattr(cdp_mod.subprocess, "run", _Run)
    store = _Store()
    driver = _cdp_driver(store, _Cdp(store))

    assert driver.clipboard_paste("anything", target="#q") == ""
    assert seen and seen[0]["check"] is True
    assert driver._page.keyboard.pressed == ["Meta+V"]


def test_peekaboo_paste_refuses_to_pretend_it_verified():
    """A GUI backend cannot read a field back, so it raises instead of guessing."""
    with pytest.raises(DriverError, match="cdp driver"):
        PeekabooDriver().paste("text", target="#q")
