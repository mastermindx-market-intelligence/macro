"""Actual builder/controller/client in Chromium with a synthetic account owner.

These are UI and transport integration tests. Terminal's companion SQL tests own
database/RLS enforcement. HTTP(S), production auth and notifications are absent.
"""
from copy import deepcopy
from pathlib import Path
import re

import pytest
from playwright.sync_api import sync_playwright, expect
from tests.test_forex_r26_workspace import render_case

ROOT = Path(__file__).resolve().parents[1]
AUTH_FIXTURE = ROOT / "tests" / "fixtures" / "forex_account_owner.js"
A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
ID = "11111111-1111-4111-8111-111111111111"


def saved_row():
    return {"id": ID, "user_id": A, "symbol": "USDJPY", "active": False,
            "created_at": "2026-10-21T11:00:00Z",
            "condition": {"type": "forex_price_close", "schema_version": 1,
                "condition_id": ID, "revision": 1, "kind": "price_close",
                "pair": "USDJPY", "quote_basis": "literal", "interval": "4H",
                "calendar": "fx-utc-4h/v1", "operator": "lt", "threshold": 145.6,
                "consecutive": 2, "expires_at": "2099-10-23T16:00:00.000Z",
                "feed": None, "origin_snapshot_id": "fixture"}}


class AccountOwner:
    """Scriptable remote boundary; production enforcement is never claimed here."""
    def __init__(self, seed=False):
        self.rows = {ID: saved_row()} if seed else {}
        self.writes = []
        self.fail_read = False
        self.drop_save = False
        self.drop_delete = False
        self.defer_save = False
        self.delayed_rows = {}

    @staticmethod
    def error(message):
        return {"data": None, "error": {"code": "P0001", "message": message}}

    def call(self, _source, request):
        if request["kind"] == "read":
            assert request["table"] == "alerts"
            if self.fail_read:
                return self.error("synthetic_read_failure")
            filters = dict(request["filters"])
            assert filters["user_id"] == request["user"]
            assert filters["condition->>type"] == "forex_price_close"
            rows = [deepcopy(row) for row in self.rows.values()
                    if row["user_id"] == request["user"] and
                    ("id" not in filters or row["id"] == filters["id"])]
            return {"data": rows, "error": None}
        self.writes.append(deepcopy(request))
        args = request["args"]
        if request["user"] != args["p_expected_user_id"]:
            return self.error("forex_watch_owner_changed")
        identity, revision = args["p_id"], args["p_expected_revision"]
        current = self.rows.get(identity)
        if current and current["user_id"] != request["user"]:
            return self.error("forex_watch_not_found")
        if request["name"] == "save_forex_watch":
            if (current and current["condition"]["revision"] != revision) or (not current and revision):
                return self.error("forex_watch_revision_conflict")
            rule = deepcopy(args["p_rule"])
            record = {"id": identity, "user_id": request["user"], "symbol": rule["pair"],
                "active": False, "created_at": "2026-10-21T11:00:00Z",
                "condition": {**rule, "type": "forex_price_close", "schema_version": 1,
                              "condition_id": identity, "revision": revision + 1}}
            if self.defer_save:
                self.defer_save = False
                self.delayed_rows[identity] = record
                return self.error("synthetic_response_lost_before_commit_visible")
            self.rows[identity] = record
            if self.drop_save:
                self.drop_save = False
                return self.error("synthetic_response_lost_after_commit")
            return {"data": deepcopy(record), "error": None}
        assert request["name"] == "delete_forex_watch"
        if current and current["condition"]["revision"] != revision:
            return self.error("forex_watch_revision_conflict")
        existed = current is not None
        self.rows.pop(identity, None)
        if self.drop_delete:
            self.drop_delete = False
            return self.error("synthetic_delete_response_lost")
        return {"data": {"id": identity, "deleted": existed}, "error": None}


@pytest.fixture
def browser_page(tmp_path, monkeypatch):
    _, path, _ = render_case(tmp_path / "render", monkeypatch)
    html = path.read_text()
    for asset in set(re.findall(r'(?:src|href)="([^"?#]+)(?:[^"]*)"', html)):
        source = ROOT / "templates" / asset
        if "/" not in asset and asset.endswith((".css", ".js")) and source.is_file():
            (path.parent / asset).write_bytes(source.read_bytes())
    (path.parent / "forex_account_owner.js").write_bytes(AUTH_FIXTURE.read_bytes())
    html = html.replace('<script src="theme.js"></script>',
                        '<script src="theme.js"></script><script src="forex_account_owner.js"></script>')
    path.write_text(html)
    contexts, errors, external = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        def open_page(owner, width=1440, lang="en", theme="light"):
            context = browser.new_context(viewport={"width": width, "height": 1050 if width > 400 else 844},
                                          reduced_motion="reduce")
            contexts.append(context)
            def block(route):
                external.append(route.request.url)
                route.abort()
            context.route("http://**/*", block)
            context.route("https://**/*", block)
            context.expose_binding("__fxOwner", owner.call)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(path.as_uri(), wait_until="load")
            page.evaluate("([lang,theme]) => {document.documentElement.setAttribute('data-lang',lang);document.documentElement.setAttribute('data-theme',theme)}",
                          [lang, theme])
            page.locator("#fxr-nav-my_watches").click()
            expect(page.locator("#fxr-account-title")).not_to_have_attribute("data-account-status", "checking")
            return page

        yield open_page
        for context in contexts:
            context.close()
        browser.close()
    assert not errors, errors
    assert not external, external


def ready(page):
    expect(page.locator("#fxr-account-title")).to_have_attribute("data-account-status", "ready")


def prepare(page):
    page.locator("#fxr-nav-explore").click()
    page.locator("[data-fxr-view='explore'] [data-fxr-open-pair='USDJPY']").click()
    page.locator("[data-fxr-pair='USDJPY'] .fxr-pair-header [data-fxr-prepare]").click()
    page.locator("#fxr-rule-form [name='threshold']").fill("145.6")
    page.locator("#fxr-rule-form [name='operator']").select_option("lt")
    page.locator("#fxr-rule-form [name='expires_at']").fill("2099-10-23T16:00")
    page.locator("#fxr-rule-form button[type='submit']").click()
    page.locator("#fxr-keep-rule").click()
    expect(page.locator("#fxr-prepared-list article")).to_have_count(1)


def edit(page, value):
    page.locator("#fxr-saved-list article button").first.click()
    page.locator("#fxr-edit-rule").click()
    page.locator("#fxr-rule-form [name='threshold']").fill(str(value))
    page.locator("#fxr-rule-form button[type='submit']").click()


@pytest.mark.parametrize("width,lang,theme", [(1440, "en", "light"), (1440, "zh", "dark"),
                                             (390, "en", "dark"), (390, "zh", "light")])
def test_save_reload_edit_delete_inactive_condition(browser_page, tmp_path, width, lang, theme):
    owner = AccountOwner()
    page = browser_page(owner, width, lang, theme)
    ready(page)
    prepare(page)
    page.locator("#fxr-prepared-list article button").nth(1).click()
    expect(page.locator("#fxr-saved-list article")).to_have_count(1)
    expect(page.locator("#fxr-prepared-list article")).to_have_count(0)
    identity, row = next(iter(owner.rows.items()))
    assert row["active"] is False and row["condition"]["revision"] == 1
    assert len(owner.writes) == 1
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    page.screenshot(path=str(tmp_path / f"saved-{width}-{lang}-{theme}.png"), full_page=False)
    page.reload(wait_until="load")
    ready(page)
    expect(page.locator("#fxr-saved-list article")).to_have_count(1)
    assert len(owner.writes) == 1, "reload must only read"
    edit(page, 144.7)
    page.locator("#fxr-keep-rule").click()
    expect(page.locator("#fxr-watch-dialog")).not_to_be_visible()
    ready(page)
    assert owner.rows[identity]["condition"]["revision"] == 2
    assert owner.rows[identity]["condition"]["threshold"] == 144.7
    assert owner.rows[identity]["active"] is False and len(owner.rows) == 1
    page.locator("#fxr-saved-list article button").nth(1).click()
    ready(page)
    expect(page.locator("#fxr-saved-list article")).to_have_count(0)
    assert not owner.rows and len(owner.writes) == 3


def test_failed_read_is_distinct_from_an_empty_account(browser_page):
    owner = AccountOwner(); owner.fail_read = True
    page = browser_page(owner)
    expect(page.locator("#fxr-account-title")).to_have_attribute("data-account-status", "unavailable")
    assert "No saved Forex" not in page.locator("#fxr-account-title").inner_text()
    owner.fail_read = False
    page.locator("#fxr-account-refresh").click()
    ready(page)
    expect(page.locator("#fxr-account-title")).to_have_text("No saved Forex conditions")
    assert not owner.writes


def test_lost_save_response_uses_readback_without_replay(browser_page):
    owner = AccountOwner(); owner.drop_save = True
    page = browser_page(owner); ready(page); prepare(page)
    page.locator("#fxr-prepared-list article button").nth(1).click()
    expect(page.locator("#fxr-account-title")).to_have_attribute("data-account-status", "unconfirmed")
    expect(page.locator("#fxr-pending-list article button")).to_be_visible()
    assert "No saved Forex" not in page.locator("#fxr-account-title").inner_text()
    assert len(owner.writes) == 1 and len(owner.rows) == 1
    page.locator("#fxr-pending-list article button").click()
    expect(page.locator("#fxr-saved-list article")).to_have_count(1)
    expect(page.locator("#fxr-pending-list article")).to_have_count(0)
    assert len(owner.writes) == 1


def test_two_tabs_conflict_requires_loading_saved_revision(browser_page):
    owner = AccountOwner(seed=True)
    first, second = browser_page(owner), browser_page(owner)
    ready(first); ready(second)
    edit(first, 144); edit(second, 143)
    first.locator("#fxr-keep-rule").click()
    expect(first.locator("#fxr-watch-dialog")).not_to_be_visible()
    second.locator("#fxr-keep-rule").click()
    expect(second.locator("#fxr-reload-saved")).to_be_visible()
    expect(second.locator("#fxr-keep-rule")).to_be_disabled()
    assert owner.rows[ID]["condition"]["revision"] == 2
    assert owner.rows[ID]["condition"]["threshold"] == 144
    second.locator("#fxr-reload-saved").click()
    expect(second.locator("#fxr-reload-saved")).not_to_be_visible()
    second.locator("#fxr-edit-rule").click()
    expect(second.locator("#fxr-rule-form [name='threshold']")).to_have_value("144")
    second.locator("#fxr-rule-form [name='threshold']").fill("142")
    second.locator("#fxr-rule-form button[type='submit']").click()
    second.locator("#fxr-keep-rule").click()
    expect(second.locator("#fxr-watch-dialog")).not_to_be_visible()
    assert owner.rows[ID]["condition"]["revision"] == 3
    assert owner.rows[ID]["condition"]["threshold"] == 142


def test_account_switch_removes_rows_editor_and_late_acknowledgment(browser_page):
    owner = AccountOwner(seed=True)
    page = browser_page(owner); ready(page); edit(page, 144)
    page.evaluate("window.__fxHoldWrites = true")
    page.locator("#fxr-keep-rule").click()
    page.wait_for_function("window.__fxHeldWrites.length === 1")
    page.evaluate("(id) => window.__fxAuth.emit(id)", B)
    ready(page)
    expect(page.locator("#fxr-watch-dialog")).not_to_be_visible()
    expect(page.locator("#fxr-saved-list article")).to_have_count(0)
    expect(page.locator("#fxr-pending-list article")).to_have_count(0)
    page.evaluate("window.__fxHeldWrites.splice(0).forEach(resolve => resolve())")
    expect(page.locator("#fxr-account-title")).to_have_text("No saved Forex conditions")
    assert owner.rows[ID]["user_id"] == A and owner.rows[ID]["condition"]["revision"] == 2
    assert not any(row["user_id"] == B for row in owner.rows.values())
    assert "Saved inactive." not in page.locator("#fxr-account-message").inner_text()
    assert page.locator("#fxr-rule-json").text_content() == ""
    assert page.locator("#fxr-rule-form [name='threshold']").input_value() == ""


def test_uncertain_delete_survives_failed_readback(browser_page):
    owner = AccountOwner(seed=True); owner.drop_delete = True
    page = browser_page(owner); ready(page)
    page.locator("#fxr-saved-list article button").nth(1).click()
    expect(page.locator("#fxr-pending-list article button")).to_be_visible()
    owner.fail_read = True
    page.locator("#fxr-pending-list article button").click()
    expect(page.locator("#fxr-pending-list article button")).to_be_enabled()
    expect(page.locator("#fxr-account-title")).to_have_attribute("data-account-status", "unconfirmed")
    assert len(owner.writes) == 1
    owner.fail_read = False
    page.locator("#fxr-pending-list article button").click()
    expect(page.locator("#fxr-pending-list article")).to_have_count(0)
    ready(page)
    assert not owner.rows and len(owner.writes) == 1



def test_sign_in_preserves_anonymous_draft_without_automatically_saving(browser_page):
    owner = AccountOwner()
    page = browser_page(owner); ready(page)
    page.evaluate("window.__fxAuth.emit(null, 'SIGNED_OUT')")
    expect(page.locator("#fxr-account-title")).to_have_attribute("data-account-status", "signed_out")
    prepare(page)
    page.locator("#fxr-prepared-list article button").nth(1).click()
    assert page.evaluate("window.__fxSignInOpened") is True
    assert not owner.writes
    page.evaluate("(id) => window.__fxAuth.emit(id)", A)
    ready(page)
    expect(page.locator("#fxr-prepared-list article")).to_have_count(1)
    assert not owner.writes, "sign-in alone is not authorization to save the draft"
    page.locator("#fxr-prepared-list article button").nth(1).click()
    expect(page.locator("#fxr-saved-list article")).to_have_count(1)
    assert len(owner.writes) == 1


def test_same_account_session_confirmation_preserves_draft_and_editor(browser_page):
    owner = AccountOwner()
    page = browser_page(owner); ready(page); prepare(page)
    page.locator("#fxr-prepared-list article button").first.click()
    expect(page.locator("#fxr-watch-dialog")).to_be_visible()
    before = page.locator("#fxr-rule-json").text_content()
    epoch = page.evaluate("window.ForexWatchClient.authState().epoch")
    # The incumbent SDK emits this on visible-tab session recovery without logout.
    page.evaluate("(id) => window.__fxAuth.emit(id, 'SIGNED_IN')", A)
    expect(page.locator("#fxr-prepared-list article")).to_have_count(1)
    expect(page.locator("#fxr-watch-dialog")).to_be_visible()
    assert page.locator("#fxr-rule-json").text_content() == before
    assert page.evaluate("window.ForexWatchClient.authState().epoch") == epoch
    assert not owner.writes


def test_same_account_confirmation_keeps_unconfirmed_save_reconciliation(browser_page):
    owner = AccountOwner(); owner.defer_save = True
    page = browser_page(owner); ready(page); prepare(page)
    page.locator("#fxr-prepared-list article button").nth(1).click()
    expect(page.locator("#fxr-pending-list article")).to_have_count(1)
    page.evaluate("(id) => window.__fxAuth.emit(id, 'SIGNED_IN')", A)
    expect(page.locator("#fxr-pending-list article")).to_have_count(1)
    expect(page.locator("#fxr-prepared-list article")).to_have_count(1)
    expect(page.locator("#fxr-account-title")).to_have_text("Change awaiting confirmation")
    assert not owner.rows and len(owner.writes) == 1
    owner.rows.update(owner.delayed_rows)
    page.locator("#fxr-pending-list article button").click()
    expect(page.locator("#fxr-saved-list article")).to_have_count(1)
    expect(page.locator("#fxr-pending-list article")).to_have_count(0)
    assert len(owner.writes) == 1


def test_empty_reload_cannot_resolve_an_unconfirmed_save(browser_page):
    owner = AccountOwner(); owner.defer_save = True
    page = browser_page(owner); ready(page); prepare(page)
    page.locator("#fxr-prepared-list article button").nth(1).click()
    expect(page.locator("#fxr-account-title")).to_have_text("Change awaiting confirmation")
    page.locator("#fxr-account-refresh").click()
    expect(page.locator("#fxr-account-title")).to_have_text("Change awaiting confirmation")
    expect(page.locator("#fxr-pending-list article")).to_have_count(1)
    page.locator("#fxr-pending-list article button").click()
    expect(page.locator("#fxr-pending-list article button")).to_be_enabled()
    expect(page.locator("#fxr-account-title")).to_have_text("Change awaiting confirmation")
    assert not owner.rows and len(owner.writes) == 1
    owner.rows.update(owner.delayed_rows)
    page.locator("#fxr-pending-list article button").click()
    expect(page.locator("#fxr-saved-list article")).to_have_count(1)
    expect(page.locator("#fxr-pending-list article")).to_have_count(0)
    assert len(owner.writes) == 1
