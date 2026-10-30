"""Exercise live SSE delivery of the shipped ticker-news consumer on a local fixture.

A localhost HTTP/SSE server pushes projected change frames to the real browser
consumer, so upsert/correction/remove latency, snapshot-GET avoidance, revocation
purge, replay/stale-frame guards, fencing and pagination caps are observed end to
end. No provider, production auth, or external network calls. Screenshots and
latencies are interaction proof on fictional fixtures, not live-data proof, and
no production behavior is claimed.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import parse_qs, unquote, urlsplit

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "fixture-only"


def snapshot_row(sequence, story, title, *, low=False, count=1):
    return {
        "sequence": sequence, "source": "benzinga", "publisher": "Benzinga",
        "source_item_id": str(story), "story_id": "story-" + str(story),
        "source_count": count, "item_count": count, "title": title,
        "url": "https://example.test/report/" + str(story),
        "teaser": "Preview fixture: reporting stays readable with room for context, source attribution and the underlying reports.",
        "published_at": "2026-10-20T10:00:00Z", "updated_at": None,
        "received_at": "2026-10-20T10:00:01Z", "universe_revision": "fixture",
        "quality": {"score": 35 if low else 85, "low_value": low,
                    "reason": "routine_options_template" if low else None},
        "annotation": None, "provider": None, "reporting_state": "not_compared",
        "observed_at": "2026-10-20T10:00:02Z",
    }


def change_row(sequence, story, title, *, kind="upsert", observed="2026-10-20T11:00:00Z",
               count=1, projection_sequence=None, reporting_state="not_compared"):
    """Complete current API projection, with distinct delivery and display clocks."""
    row = snapshot_row(sequence if projection_sequence is None else projection_sequence,
                       story, title, count=count)
    row.update(kind=kind, sequence=sequence,
               projection_sequence=sequence if projection_sequence is None else projection_sequence,
               security_ids=["fixture-security"], observed_at=observed,
               reporting_state=reporting_state,
               teaser="Live fixture projection of the current eligible representative.",
               quality={"score": 88, "low_value": False, "reason": None})
    if kind == "remove":
        row.update(title="", url="", teaser="", source_count=None, item_count=None,
                   published_at=None, updated_at=None, received_at=None,
                   quality=None, projection_sequence=None)
    return row


def base_snapshot(ticker="NVDA", rows=None, *, has_more=True, next_cursor=None,
                  change_sequence=None):
    rows = default_rows() if rows is None else rows
    return {
        "schema": "ticker_news.snapshot.v1", "ticker": ticker,
        "security_id": "fixture-" + ticker, "state": "live", "rows": rows,
        "change_sequence": max((r["sequence"] for r in rows), default=0)
                           if change_sequence is None else change_sequence,
        "next_cursor": (min(r["sequence"] for r in rows) if next_cursor is None and rows
                        else next_cursor) if has_more else None,
        "has_more": has_more,
        "source_health": {"state": "live",
                          "additional_sources": [{"provider": "massive", "state": "available"}]},
    }


def story_detail(story_id):
    member = snapshot_row(13, 1, "Nvidia announces a new data-center accelerator")
    second = deepcopy(member)
    second.update(source="massive:reuters.com", publisher="Reuters",
                  source_item_id="wire-1", title="Second publisher's report on the same event")
    return {"schema": "ticker_news.story.v1", "story_id": story_id,
            "source_count": 2, "item_count": 2, "members": [member, second]}


def default_rows():
    return [
        snapshot_row(13, 1, "Nvidia announces a new data-center accelerator", count=2),
        snapshot_row(12, 2, "Nvidia receives regulatory approval for a new facility"),
        snapshot_row(11, 3, "Nvidia whale alerts from today's trading session", low=True),
    ]


def document_html(js_bytes):
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    env.globals["t"] = lambda en, zh="": Markup('<span class="l-en">') + escape(en) + Markup('</span><span class="l-zh">') + escape(zh or en) + Markup("</span>")
    markup = env.get_template("ticker_news_panel.html.j2").render(ticker="", nav_prefix="")
    css = (ROOT / "templates/ticker_news.css").read_text()
    return ("<!doctype html><html lang=\"en\" data-theme=\"dark\" data-lang=\"en\"><head>\n"
            "<meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<style>\n"
            "*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font-family:system-ui}\n"
            ":root{--bg:#080e19;--panel:#101927;--panel2:#192639;--line:#2a384c;--text:#edf3fd;--muted:#a4b2c7;--link:#98bcff;--up:#72ddb7;--warn:#f1c77d}\n"
            ".l-zh{display:none}[data-lang=zh] .l-en{display:none}[data-lang=zh] .l-zh{display:inline}\n"
            "main{max-width:1180px;margin:auto}.fixture{font:12px/1.6 system-ui;color:var(--muted);margin:0}\n"
            "</style><style>" + css + "</style></head><body><main>"
            "<p class=\"fixture\">STREAM TIMING PREVIEW · FICTIONAL NEWS FIXTURES · NO PRODUCTION DATA</p>"
            + markup + "</main><script>\n"
            "window.MDXAuth={client:async()=>({auth:{getSession:async()=>({data:{session:{access_token:\"" + TOKEN + "\"}}})}})};\n"
            "window.__fix={first:{},last:{}};\n"
            "new MutationObserver(function(muts){muts.forEach(function(m){m.addedNodes.forEach(function(n){\n"
            "if(n.nodeType!==1)return;\n"
            "var rows=n.matches&&n.matches('.tn-row[data-story]')?[n]:Array.prototype.slice.call(n.querySelectorAll?n.querySelectorAll('.tn-row[data-story]'):[]);\n"
            "rows.forEach(function(r){var id=r.dataset.story,w=Date.now();if(window.__fix.first[id]===undefined)window.__fix.first[id]=w;window.__fix.last[id]=w;});\n"
            "});});}).observe(document.documentElement,{childList:true,subtree:true});\n"
            "</script><script>" + js_bytes.decode() + "</script></body></html>")


class StreamConn:
    def __init__(self, ticker, after_sequence):
        self.ticker = ticker
        self.after_sequence = after_sequence
        self.queue: asyncio.Queue = asyncio.Queue()
        self.closed = False

    async def put(self, event, payload):
        await self.queue.put((event, json.dumps(payload, ensure_ascii=False, separators=(",", ":"))))

    async def put_raw(self, event, raw):
        await self.queue.put((event, raw))


class Fixture:
    """Shared mutable fixture state the scenario driver manipulates."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.snapshot_payload = base_snapshot()
        self.snapshot_count = 0
        self.detail_count = 0
        self.stream_count = 0
        self.requests: list[dict] = []
        self.hold_snapshot: asyncio.Event | None = None
        self.hold_detail: asyncio.Event | None = None
        self.streams: dict[str, StreamConn] = {}
        self.journal: list[tuple[str, dict]] = []

    def note(self, path, authorized):
        self.requests.append({"path": path, "authorized": authorized})

    async def wait_released(self, event: asyncio.Event | None):
        if event is not None:
            try:
                await asyncio.wait_for(event.wait(), 20)
            except asyncio.TimeoutError:
                pass


async def read_request(reader):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = await reader.read(4096)
        if not chunk:
            return None
        data += chunk
        if len(data) > 65536:
            return None
    head = data.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    lines = head.split("\r\n")
    method, target, _ = lines[0].split(" ", 2)
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
    return method, target, headers


async def respond(writer, status, content_type, body):
    writer.write(("HTTP/1.1 %d X\r\n" % status).encode())
    writer.write(("Content-Type: " + content_type + "\r\nContent-Length: " +
                  str(len(body)) + "\r\nConnection: close\r\n\r\n").encode())
    writer.write(body)
    await writer.drain()


async def respond_json(writer, status, payload):
    await respond(writer, status, "application/json", json.dumps(payload).encode())


async def monitor_client(reader, conn: StreamConn):
    try:
        while await reader.read(4096):
            pass
    except Exception:
        pass
    conn.closed = True


async def handle_client(reader, writer, fixture: Fixture, html: str):
    try:
        request = await read_request(reader)
        if request is None:
            return
        _method, target, headers = request
        parts = urlsplit(target)
        path = unquote(parts.path)
        query = parse_qs(parts.query)
        authorized = headers.get("authorization") == "Bearer " + TOKEN
        fixture.note(path + ("?" + parts.query if parts.query else ""), authorized)

        if path != "/" and not authorized:
            await respond_json(writer, 401, {"detail": "fixture auth required"})
            return

        if path == "/":
            await respond(writer, 200, "text/html; charset=utf-8", html.encode())
        elif path.endswith("/stream"):
            ticker = path[len("/api/ticker-news/"):-len("/stream")]
            fixture.stream_count += 1
            conn = StreamConn(ticker, int(query.get("after_sequence", ["0"])[0]))
            fixture.streams[ticker] = conn
            for event, payload in fixture.journal:
                if payload["sequence"] > conn.after_sequence:
                    await conn.put(event, payload)
            writer.write(b"HTTP/1.1 200 X\r\nContent-Type: text/event-stream\r\n"
                         b"Cache-Control: no-store\r\nConnection: close\r\n\r\n")
            await writer.drain()
            monitor = asyncio.create_task(monitor_client(reader, conn))
            try:
                while True:
                    event, data = await conn.queue.get()
                    writer.write(("event: " + event + "\ndata: " + data + "\n\n").encode())
                    await writer.drain()
            except (ConnectionError, RuntimeError):
                pass
            finally:
                conn.closed = True
                monitor.cancel()
        elif "/stories/" in path:
            story_id = path.rsplit("/stories/", 1)[1]
            fixture.detail_count += 1
            await fixture.wait_released(fixture.hold_detail)
            await respond_json(writer, 200, story_detail(story_id))
        elif path.startswith("/api/ticker-news/"):
            ticker = path[len("/api/ticker-news/"):]
            fixture.snapshot_count += 1
            payload = deepcopy(fixture.snapshot_payload)
            payload["ticker"] = ticker
            await fixture.wait_released(fixture.hold_snapshot)
            if "cursor" in query:
                payload = base_snapshot(ticker, [snapshot_row(int(query["cursor"][0])-1, 4, "Earlier reporting remains accessible")],
                                        has_more=False, next_cursor=None)
            await respond_json(writer, 200, payload)
        else:
            await respond_json(writer, 404, {"detail": "fixture route unknown"})
    except (ConnectionError, RuntimeError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def start_fixture_server(fixture: Fixture, html: str):
    tasks: set[asyncio.Task] = set()

    async def handler(reader, writer):
        await handle_client(reader, writer, fixture, html)

    def tracked(reader, writer):
        task = asyncio.create_task(handler(reader, writer))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    server = await asyncio.start_server(tracked, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1], tasks


class Driver:
    def __init__(self, page, fixture: Fixture, port: int, shots: Path | None = None):
        self.page = page
        self.fixture = fixture
        self.shots = shots
        self.base = "http://127.0.0.1:%d/" % port

    async def shot(self, name):
        if self.shots is not None:
            await self.page.screenshot(path=str(self.shots / name), full_page=True)

    async def load(self, ticker="NVDA"):
        await self.page.goto(self.base + "#" + ticker)
        await self.page.wait_for_function("document.querySelectorAll('.tn-row').length>0")
        await self.page.wait_for_timeout(250)

    async def rows(self):
        return await self.page.locator(".tn-row").count()

    async def push(self, event, payload):
        """Push one SSE frame; returns the server write epoch in ms."""
        epoch = time.time() * 1000.0
        if (event in ("upsert", "remove") and payload.get("kind") == event
                and isinstance(payload.get("sequence"), int) and payload["sequence"] > 0
                and 0 < len(payload.get("story_id", "")) <= 256 and "source_item_id" in payload):
            self.fixture.journal.append((event, deepcopy(payload)))
        await self.fixture.streams["NVDA"].put(event, payload)
        return epoch


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    return label


# --- scenarios ---------------------------------------------------------------

async def scenario_live_apply(drv: Driver):
    f = drv.fixture
    await drv.load()
    assert f.snapshot_count == 1 and f.stream_count == 1
    latencies = {}
    checks = []

    epoch = await drv.push("upsert", change_row(100, 50, "Live accelerator shipment confirmed by two publishers"))
    await drv.page.wait_for_function("document.querySelector('.tn-row[data-story=\"story-50\"]')")
    latencies["upsert"] = (await drv.page.evaluate("window.__fix.first['story-50']||null")) - epoch
    checks.append(check(f.snapshot_count == 1, "valid live upsert renders without a snapshot GET"))
    checks.append(check(await drv.rows() == 3, "live upsert joins existing rows"))
    checks.append(check(await drv.page.locator(".tn-row").first.get_attribute("data-story") == "story-50",
                        "newest sequence leads the live page like a snapshot would"))

    epoch = await drv.push("upsert", change_row(101, 50, "Live accelerator shipment corrected after publisher update"))
    await drv.page.get_by_text("Live accelerator shipment corrected after publisher update", exact=True).wait_for()
    latencies["correction"] = (await drv.page.evaluate("window.__fix.last['story-50']||null")) - epoch
    checks.append(check(f.snapshot_count == 1, "correction applies in place without a snapshot GET"))

    epoch = await drv.push("remove", change_row(102, 50, "", kind="remove"))
    await drv.page.wait_for_function("!document.querySelector('.tn-row[data-story=\"story-50\"]')")
    latencies["remove"] = time.time() * 1000.0 - epoch
    checks.append(check(f.snapshot_count == 1, "remove applies without a snapshot GET"))
    await drv.shot("stream-live.png")
    return checks, latencies


async def scenario_gap_and_replay(drv: Driver):
    f = drv.fixture
    await drv.load()
    checks = []

    await drv.push("upsert", change_row(100, 60, "Gap-separated story still delivered"))
    await drv.page.wait_for_function("document.querySelector('.tn-row[data-story=\"story-60\"]')")
    checks.append(check(f.snapshot_count == 1 and f.stream_count == 1,
                        "global sequence gap is not treated as a lost event (no reload)"))
    checks.append(check(await drv.page.locator(".tn-row").first.get_attribute("data-story") == "story-60",
                        "gap-separated story still orders by sequence, newest first"))

    await drv.push("upsert", change_row(100, 60, "Gap-separated story still delivered"))
    await drv.page.wait_for_timeout(80)
    checks.append(check(await drv.rows() == 3 and f.snapshot_count == 1,
                        "duplicate replayed frame is idempotent without reload"))

    await drv.push("upsert", change_row(99, 60, "Stale rewrite of the same story"))
    await drv.page.wait_for_timeout(80)
    checks.append(check(await drv.page.get_by_text("Stale rewrite of the same story", exact=True).count() == 0
                        and f.snapshot_count == 1,
                        "stale lower-sequence rewrite is ignored without reload"))

    await drv.push("remove", change_row(103, 60, "", kind="remove"))
    await drv.page.wait_for_function("!document.querySelector('.tn-row[data-story=\"story-60\"]')")
    await drv.push("upsert", change_row(102, 60, "Resurrection from a stale frame"))
    await drv.page.wait_for_timeout(80)
    checks.append(check(await drv.page.get_by_text("Resurrection from a stale frame", exact=True).count() == 0,
                        "upsert older than the applied remove stays removed"))
    await drv.push("upsert", change_row(104, 60, "Story accessible again after re-add"))
    await drv.page.wait_for_function("document.querySelector('.tn-row[data-story=\"story-60\"]')")
    checks.append(check(await drv.page.get_by_text("Story accessible again after re-add", exact=True).count() == 1,
                        "higher-sequence re-add after remove restores the story"))
    return checks


async def scenario_hold_and_group(drv: Driver):
    f = drv.fixture
    page = drv.page
    await drv.load()
    checks = []
    base_detail = f.detail_count

    await page.locator(".tn-group summary").focus()
    await page.keyboard.press("Enter")
    await page.get_by_text("Second publisher's report on the same event", exact=True).wait_for()
    checks.append(check(f.detail_count == base_detail + 1, "group detail fetched once"))

    await drv.push("upsert", change_row(110, 70, "Held headline while the reader is inside the panel"))
    await page.wait_for_function("document.querySelector('[data-tn-updates]')&&!document.querySelector('[data-tn-updates]').hidden")
    checks.append(check(await page.locator(".tn-row[data-story=\"story-70\"]").count() == 0,
                        "new story held as pending notice while a group is open"))
    checks.append(check("Show 1 new story" in (await page.locator("[data-tn-updates]").text_content() or ""),
                        "pending notice names the held story count"))
    await drv.shot("stream-hold.png")

    await drv.push("upsert", change_row(111, 1, "Nvidia announces a REVISED data-center accelerator", count=2))
    await page.get_by_text("Nvidia announces a REVISED data-center accelerator", exact=True).wait_for()
    checks.append(check(await page.locator(".tn-row[data-story=\"story-1\"] details[open]").count() == 0
                        and not await page.get_by_text("Second publisher's report on the same event", exact=True).count(),
                        "correction replaces the open group card and clears cached detail"))
    await page.locator(".tn-row[data-story=\"story-1\"] summary").focus()
    await page.keyboard.press("Enter")
    await page.get_by_text("Second publisher's report on the same event", exact=True).wait_for()
    checks.append(check(f.detail_count == base_detail + 2, "re-opening the corrected group refetches detail"))

    await page.locator("[data-tn-updates]").click()
    await page.locator(".tn-row[data-story=\"story-70\"]").wait_for()
    checks.append(check(await page.locator('.tn-row[data-story="story-70"]').is_visible(),
                        "releasing the notice reveals the held story"))
    return checks


async def scenario_restricted_purge(drv: Driver):
    f, page = drv.fixture, drv.page
    await drv.load()
    checks = []
    f.hold_detail = asyncio.Event()
    await page.locator(".tn-group summary").focus()
    await page.keyboard.press("Enter")
    await page.get_by_text("Loading reports…", exact=True).wait_for()
    await drv.push("upsert", change_row(110, 70, "Pending row before permission reset"))
    await drv.push("restricted", {"schema": "ticker_news.restricted.v1", "ticker": "NVDA",
                                  "detail": "ticker news rights unavailable"})
    await page.wait_for_function("document.querySelector('[data-tn-status]').dataset.state==='restricted'")
    checks.append(check(await drv.rows() == 0, "restricted event immediately purges rows and queued changes"))
    checks.append(check(await page.locator(".tn-member").count() == 0, "open group content is purged"))
    f.hold_detail.set()
    await page.wait_for_timeout(300)
    checks.append(check(await drv.rows() == 0 and await page.locator(".tn-member").count() == 0,
                        "late group response and queued upsert cannot repopulate after restriction"))
    await drv.shot("stream-restricted.png")
    f.snapshot_payload = base_snapshot(change_sequence=110)
    f.journal = []
    await page.wait_for_function("document.querySelectorAll('.tn-row').length>0", timeout=8000)
    checks.append(check(f.snapshot_count == 2, "one fresh qualified snapshot follows the permission reset"))
    return checks


async def scenario_auth_snapshot_fence(drv: Driver):
    f, page = drv.fixture, drv.page
    await drv.load()
    f.hold_snapshot = asyncio.Event()
    await page.locator("[data-tn-retry]").evaluate("(node)=>{node.hidden=false;node.click()}")
    await page.wait_for_timeout(150)
    await page.evaluate("""() => {
      window.MDXAuth={client:async()=>({auth:{getSession:async()=>({data:{session:null}})}})};
      window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{event:'SIGNED_OUT'}}));
    }""")
    await page.wait_for_function("document.querySelector('[data-tn-status]').dataset.state==='restricted'")
    f.hold_snapshot.set()
    await page.wait_for_timeout(300)
    return [check(await drv.rows() == 0, "sign-out fences a held successful snapshot and purges all rows")]


async def scenario_snapshot_race(drv: Driver):
    f, page = drv.fixture, drv.page
    await drv.load()
    old = f.streams["NVDA"]
    f.snapshot_payload = base_snapshot(rows=[snapshot_row(180, 80, "Authoritative current projection")],
                                       change_sequence=200)
    f.hold_snapshot = asyncio.Event()
    await drv.push("resync", {"schema": "ticker_news.resync.v1", "ticker": "NVDA"})
    await page.wait_for_timeout(150)
    checks = [check(f.snapshot_count == 2, "unknown frame schedules one authoritative snapshot")]
    await old.put("upsert", change_row(150, 80, "Older buffered projection must not render"))
    await page.wait_for_timeout(80)
    checks.append(check(await page.get_by_text("Older buffered projection must not render", exact=True).count() == 0,
                        "refresh aborts and fences old-stream callbacks before accepting its snapshot"))
    f.hold_snapshot.set()
    await page.get_by_text("Authoritative current projection", exact=True).wait_for()
    await page.wait_for_timeout(150)
    conn = f.streams["NVDA"]
    checks.append(check(conn is not old and conn.after_sequence == 200,
                        "stream reconnects from atomic global watermark, including non-visible changes"))
    await drv.push("upsert", change_row(201, 80, "Current projection of first event", projection_sequence=220))
    await drv.push("upsert", change_row(202, 90, "Next delivery still appears", projection_sequence=210))
    await page.get_by_text("Next delivery still appears", exact=True).wait_for()
    checks.append(check(await page.locator(".tn-row").first.get_attribute("data-story") == "story-80",
                        "delivery 201 with projection 220 orders ahead of delivery 202 with projection 210"))
    checks.append(check(await drv.rows() == 2 and f.snapshot_count == 2,
                        "projection ordering does not skip the next unconsumed journal event"))
    return checks


async def scenario_ticker_fence(drv: Driver):
    f = drv.fixture
    page = drv.page
    await drv.load("NVDA")
    checks = []

    # Snapshot issued for NVDA, held past the ticker switch, then released.
    f.snapshot_payload = base_snapshot("NVDA", [snapshot_row(200, 99, "Stale Nvidia frame after ticker switch")])
    f.hold_snapshot = asyncio.Event()
    await page.locator("[data-tn-retry]").evaluate("(node)=>{node.hidden=false;node.click()}")
    await page.wait_for_timeout(150)
    f.snapshot_payload = base_snapshot("AAPL", [snapshot_row(50, 9, "Apple reporting after a ticker change")])
    await page.evaluate("location.hash='AAPL'")
    await page.wait_for_timeout(150)
    stale_seen = await page.get_by_text("Stale Nvidia frame after ticker switch", exact=True).count()
    f.hold_snapshot.set()
    f.hold_snapshot = None
    await page.get_by_text("Apple reporting after a ticker change", exact=True).wait_for()
    await page.wait_for_timeout(300)
    checks.append(check(stale_seen == 0 and await page.get_by_text("Stale Nvidia frame after ticker switch", exact=True).count() == 0,
                        "in-flight snapshot for the previous ticker is fenced out"))
    checks.append(check(await drv.rows() == 1, "new ticker renders exactly its own snapshot"))
    return checks


async def scenario_history_isolation(drv: Driver):
    f = drv.fixture
    page = drv.page
    await drv.load()
    checks = []
    base_streams = f.stream_count

    await page.locator("[data-tn-more]").click()
    await page.get_by_text("Earlier reporting remains accessible", exact=True).wait_for()
    checks.append(check(f.stream_count == base_streams, "history view opens no stream"))
    conn = f.streams.get("NVDA")
    if conn is not None:
        await conn.put("upsert", change_row(130, 90, "Late live frame during history"))
    await page.wait_for_timeout(150)
    checks.append(check(await page.get_by_text("Late live frame during history", exact=True).count() == 0,
                        "live frames never touch the read-only history view"))

    await page.locator("[data-tn-latest]").click()
    await page.locator(".tn-row").first.wait_for()
    await page.wait_for_timeout(250)
    conn = f.streams.get("NVDA")
    checks.append(check(f.stream_count == base_streams + 1 and conn is not None and not conn.closed,
                        "returning to live reconnects the stream"))
    checks.append(check(conn.after_sequence == 13, "stream resumes from the snapshot's newest sequence"))
    return checks


async def scenario_cap_and_bounds(drv: Driver):
    f = drv.fixture
    page = drv.page
    rows = [snapshot_row(41 - i, 100 + i, "Filler story number %d" % (41 - i)) for i in range(40)]
    f.snapshot_payload = base_snapshot(rows=rows, has_more=False, next_cursor=None)
    await drv.load()
    checks = []

    for seq, story in ((42, 200), (43, 201), (44, 202)):
        await drv.push("upsert", change_row(seq, story, "Overflow story %d" % seq))
    await page.wait_for_function("document.querySelector('.tn-row[data-story=\"story-202\"]')")
    await page.wait_for_timeout(150)
    count_text = await page.locator("[data-tn-count]").text_content()
    checks.append(check(count_text == "40" and await drv.rows() == 40,
                        "live page stays capped at the requested 40 rows"))
    checks.append(check(await page.locator(".tn-row[data-story=\"story-139\"]").count() == 0,
                        "cap drops the oldest row from the live page"))
    checks.append(check(await page.locator("[data-tn-more]").is_visible(),
                        "overflow marks older reporting as still available"))
    await page.locator("[data-tn-more]").click()
    await page.get_by_text("Earlier reporting remains accessible", exact=True).wait_for()
    cursor_request = [r for r in f.requests if "cursor=" in r["path"]]
    checks.append(check(bool(cursor_request) and cursor_request[-1]["path"].split("cursor=")[1].split("&")[0] == "5",
                        "pagination uses the last kept row so the first dropped report remains reachable"))
    boundary = json.loads(await page.locator(".tn-row").first.get_attribute("data-revision"))
    checks.append(check(boundary["sequence"] == 4, "exclusive pagination returns the first dropped boundary report"))
    await page.locator("[data-tn-latest]").click()
    await page.locator(".tn-row").first.wait_for()
    await page.wait_for_timeout(150)

    base = f.snapshot_count
    await drv.push("upsert", {"kind": "upsert", "story_id": "story-x"})
    await drv.push("upsert", change_row(50, "x" * 300, "oversized story id"))
    await drv.push("upsert", {"kind": "upsert", "sequence": 0, "story_id": "story-y",
                              "source": "benzinga", "source_item_id": "y", "title": "t",
                              "url": "", "teaser": ""})
    await page.wait_for_timeout(250)
    checks.append(check(f.snapshot_count == base + 1, "malformed frames reconcile once, debounced"))
    checks.append(check(await drv.rows() == 40, "malformed frames never corrupt the packet"))
    conn = f.streams.get("NVDA")
    checks.append(check(conn is not None and not conn.closed, "stream survives malformed frames"))
    return checks


async def scenario_stream_reset(drv: Driver):
    f = drv.fixture
    page = drv.page
    await drv.load()
    checks = []
    base = f.snapshot_count

    conn = f.streams["NVDA"]
    await conn.put_raw("upsert", "this is not json")
    await page.wait_for_function("document.querySelector('[data-tn-status]').dataset.state==='degraded'")
    checks.append(check(await page.locator("[data-tn-status]").get_attribute("data-state") == "degraded",
                        "unparseable stream frame degrades instead of failing silently"))
    await page.wait_for_timeout(5600)
    checks.append(check(f.snapshot_count >= base + 1, "client reconnects with an authoritative snapshot after stream reset"))
    await page.locator(".tn-row").first.wait_for()
    return checks


async def scenario_projection_replacement(drv: Driver):
    f, page = drv.fixture, drv.page
    await drv.load()
    await drv.push("upsert", change_row(100, 1, "Reporting with a material difference",
                                      count=2, reporting_state="reports_differ"))
    await page.get_by_text("Reports differ", exact=True).wait_for()
    revised = change_row(101, 1, "Current permission-qualified headline", count=1)
    revised.update(teaser="", quality=None, annotation=None, updated_at=None)
    await drv.push("upsert", revised)
    await page.get_by_text("Current permission-qualified headline", exact=True).wait_for()
    row = page.locator('.tn-row[data-story="story-1"]')
    value = json.loads(await row.get_attribute("data-revision"))
    return [
        check(await row.locator(".tn-comparison,.tn-teaser,details").count() == 0,
              "complete projection removes prior comparison, teaser and group instead of merging omitted state"),
        check(value["quality"] is None and value["annotation"] is None and value["item_count"] == 1,
              "current authorized counts and null annotations replace the prior row as a unit"),
        check(f.snapshot_count == 1, "complete projection replacement needs no snapshot GET"),
    ]


async def scenario_legacy_and_partial(drv: Driver):
    f, page = drv.fixture, drv.page
    f.snapshot_payload.pop("change_sequence")
    await drv.load()
    legacy = base_snapshot(rows=[snapshot_row(100, 50, "Legacy contract reconciled")], has_more=False)
    legacy.pop("change_sequence")
    f.snapshot_payload = legacy
    await drv.push("upsert", change_row(100, 50, "Legacy contract reconciled"))
    await page.get_by_text("Legacy contract reconciled", exact=True).wait_for()
    await page.wait_for_timeout(200)
    checks = [check(f.snapshot_count == 2 and f.streams["NVDA"].after_sequence == 100,
                    "old snapshot contracts reconcile and preserve consumed delivery progress")]
    f.hold_snapshot = asyncio.Event()
    updated = snapshot_row(101, 50, "Partial event replaced by a complete snapshot")
    updated.update(teaser="", quality=None, annotation=None)
    f.snapshot_payload = base_snapshot(rows=[updated], has_more=False)
    partial = change_row(101, 50, "Partial event replaced by a complete snapshot")
    for key in ("projection_sequence", "teaser", "item_count"):
        partial.pop(key)
    await drv.push("upsert", partial)
    await page.wait_for_timeout(150)
    checks.append(check(await page.get_by_text("Legacy contract reconciled", exact=True).count() == 0,
                        "partial event cannot retain the prior row's permission-dependent display fields"))
    f.hold_snapshot.set()
    await page.get_by_text("Partial event replaced by a complete snapshot", exact=True).wait_for()
    checks.append(check(await page.locator(".tn-teaser").count() == 0 and f.snapshot_count == 3,
                        "authoritative snapshot resolves partial change with its complete current projection"))
    return checks


# --- harness -----------------------------------------------------------------

SCENARIOS = [
    ("live_apply", scenario_live_apply),
    ("gap_and_replay", scenario_gap_and_replay),
    ("hold_and_group", scenario_hold_and_group),
    ("restricted_purge", scenario_restricted_purge),
    ("auth_snapshot_fence", scenario_auth_snapshot_fence),
    ("snapshot_race", scenario_snapshot_race),
    ("ticker_fence", scenario_ticker_fence),
    ("history_isolation", scenario_history_isolation),
    ("cap_and_bounds", scenario_cap_and_bounds),
    ("stream_reset", scenario_stream_reset),
    ("projection_replacement", scenario_projection_replacement),
    ("legacy_and_partial", scenario_legacy_and_partial),
]


async def verify(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    js_bytes = (ROOT / "templates/ticker_news.js").read_bytes()
    site_bytes = (ROOT / "site/ticker_news.js").read_bytes()
    paired = js_bytes == site_bytes
    html = document_html(js_bytes)
    fixture = Fixture()
    server, port, tasks = await start_fixture_server(fixture, html)
    checks: list = []
    latencies: dict = {}
    errors: list = []
    failures: list = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)

        async def run(name, scenario):
            fixture.reset()
            page = await context.new_page()
            page.on("pageerror", lambda error: errors.append(name + ": " + str(error)))
            drv = Driver(page, fixture, port, shots=destination)
            try:
                result = await scenario(drv)
                if isinstance(result, tuple):
                    got_checks, got_latencies = result
                    checks.extend(got_checks)
                    latencies.update(got_latencies)
                else:
                    checks.extend(result)
            except AssertionError as failure:
                failures.append(name + ": " + str(failure))
            except Exception as failure:  # keep other scenarios observable
                failures.append(name + ": " + repr(failure))
            finally:
                await page.close()

        for name, scenario in SCENARIOS:
            await run(name, scenario)
        await context.close()
        await browser.close()
    server.close()
    for task in list(tasks):
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    report = {
        "schema": "ticker_news_stream.ui_verification.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "proof_scope": "headless browser against a localhost fictional SSE fixture and the shipped consumer bytes; "
                       "latency and request counts are fixture measurements, not production claims",
        "paired_source_site_identical": paired,
        "checks": checks,
        "scenario_failures": failures,
        "page_errors": errors,
        "fixture_latency_ms": {name: round(value, 1) for name, value in sorted(latencies.items())},
        "source_sha256": {
            "templates/ticker_news.js": hashlib.sha256(js_bytes).hexdigest(),
            "site/ticker_news.js": hashlib.sha256(site_bytes).hexdigest(),
            "templates/ticker_news.css": hashlib.sha256((ROOT / "templates/ticker_news.css").read_bytes()).hexdigest(),
        },
    }
    (destination / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not paired or failures or errors or len(checks) < 45:
        raise SystemExit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    asyncio.run(verify(parser.parse_args().evidence_dir))
