"""Optional real-PostgreSQL equivalence proof using only fictional, rolled-back rows.

Run with MMX_TEST_PG_SOCKET pointing to a private local test server and
MMX_TEST_PG_PORT (default 65479). No remote DSN or production tables are used.
Ordinary CI still runs the unconditional SQL-contract tests in test_analytics_exclusions.
"""
import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

import pytest

from admin import analytics_first_party as a


def _capture_pages(monkeypatch, config):
    captured = []
    monkeypatch.setattr(a, "_load_exclusions", lambda: config)
    monkeypatch.setattr(a, "status", lambda: {"configured": True})
    monkeypatch.setattr(a, "_query", lambda sql, **kw: captured.append(sql) or [])
    a.pages(days=30, limit=500)
    assert len(captured) == 1
    return captured[0]


def _literal(value):
    return "NULL" if value is None else "'" + str(value).replace("'", "''") + "'"


@pytest.mark.parametrize("private_filters", [False, True])
def test_pages_postgres_preserves_event_multiset_and_complete_metrics(monkeypatch, private_filters):
    socket = os.environ.get("MMX_TEST_PG_SOCKET")
    if not socket or not shutil.which("psql"):
        pytest.skip("Requires an explicitly supplied private local PostgreSQL test socket")
    assert Path(socket).is_absolute() and Path(socket).is_dir()
    port = int(os.environ.get("MMX_TEST_PG_PORT", "65479"))
    cfg = {"emails": [], "locations": [], "ips": [], "visitor_ids": [],
           "bots": {"fp_fanout": 3}, "geo_overrides": []}
    if private_filters:
        cfg.update(emails=["operator@example.test"], locations=[{"city": "Fictionville"}],
                   ips=["198.51.100.99"], visitor_ids=["explicit"])
        cfg["bots"]["ips"] = ["203.0.113.99"]
        cfg["geo_overrides"] = [{"ip_prefix": "203.0.113.77", "city": "Fictional"}]
    current = _capture_pages(monkeypatch, cfg)
    first = "not exists (select 1 from excluded x where x.visitor_id = e.visitor_id)"
    second = "not exists (select 1 from bots b where b.visitor_id = e.visitor_id)"
    assert current.count(first) == current.count(second) == 1
    previous = current.replace(first, a._not_excluded("e")).replace(second, a._not_a_bot("e"))
    prefix, outer = current.rsplit("select e.site", 1)
    selection = "from public.analytics_events e " + outer.split("from public.analytics_events e ", 1)[1].split("group by", 1)[0]
    new_events = prefix + "select e.id " + selection
    old_events = new_events.replace(first, a._not_excluded("e")).replace(second, a._not_a_bot("e"))

    # id, visitor, user, age(days), kind, site, path, ip, fingerprint, user agent, dwell
    operator = "00000000-0000-0000-0000-000000000001"
    customer = "00000000-0000-0000-0000-000000000002"
    rows = [
        (1, "operator", operator, 60, "pageview", "macro", "/old", "198.51.100.1", "operator-device", "Browser", None),
        (2, "operator", None, 1, "pageview", "macro", "/a", "198.51.100.1", "operator-device", "Browser", None),
        (3, "linked", None, 1, "pageview", "macro", "/a", "198.51.100.1", "operator-device", "Browser", None),
        (4, "customer", customer, 1, "pageview", "macro", "/a", "198.51.100.1", "customer-device", "Browser", None),
        # Shared household IP avoids confounding the separate fingerprint-farm case.
        (5, "historical-customer", customer, 60, "pageview", "macro", "/old", "198.51.100.1", "operator-device", "Browser", None),
        (6, "historical-customer", None, 1, "pageview", "macro", "/a", "198.51.100.1", "operator-device", "Browser", None),
        (7, "historical-bot", None, 60, "pageview", "macro", "/old", "203.0.113.10", "bot-device", "Googlebot", None),
        (8, "historical-bot", None, 1, "pageview", "macro", "/a", "203.0.113.10", "bot-device", "Browser", None),
        (9, "farm-a", None, 60, "pageview", "macro", "/old", "203.0.113.1", "farm-device", "Browser", None),
        (10, "farm-b", None, 60, "pageview", "macro", "/old", "203.0.113.2", "farm-device", "Browser", None),
        (11, "farm-c", None, 60, "pageview", "macro", "/old", "203.0.113.3", "farm-device", "Browser", None),
        (12, "farm-a", None, 1, "pageview", "macro", "/a", "203.0.113.1", "farm-device", "Browser", None),
        (13, None, None, 1, "pageview", "macro", "/a", None, None, "Browser", None),
        (14, None, None, 1, "exit", "macro", "/a", None, None, "Browser", 3000),
        (15, "repeat", None, 1, "pageview", "macro", "/b", None, None, "Browser", None),
        (16, "repeat", None, 1, "pageview", "macro", "/b", None, None, "Browser", None),
        (17, "dwell-only", None, 1, "exit", "macro", "/b", None, None, "Browser", 2000),
        (18, "loopback", None, 1, "pageview", "macro", "/a", "127.0.0.1", "local", "Browser", None),
        (19, "explicit", None, 1, "pageview", "macro", "/a", None, None, "Browser", None),
        (20, "listed-ip", None, 1, "pageview", "macro", "/a", "198.51.100.99", None, "Browser", None),
        (21, "listed-bot", None, 1, "pageview", "macro", "/a", "203.0.113.99", None, "Browser", None),
        (22, "hosting", None, 1, "pageview", "macro", "/a", "203.0.113.22", None, "Browser", None),
        (23, "vpn", None, 1, "route", "macro", "/c", "203.0.113.23", None, "Browser", None),
        (24, "curated", None, 1, "pageview", "macro", "/c", "203.0.113.77", None, "Browser", None),
        (25, "location", None, 1, "pageview", "macro", "/a", "198.51.100.25", None, "Browser", None),
        (26, "boundary", None, 30, "pageview", "macro", "/boundary", None, None, "Browser", None),
        (27, "outside", None, 31, "pageview", "macro", "/outside", None, None, "Browser", None),
        (28, "tie", None, 1, "pageview", "terminal", "/c", None, None, "Browser", None),
        (29, "no-path", None, 1, "click", None, None, None, None, "Browser", 1000),
    ]
    values = []
    for ident, visitor, user, age, kind, site, path, ip, fp, ua, dwell in rows:
        fields = [str(ident), _literal(visitor), _literal(user), f"now() - interval '{age} days'",
                  *map(_literal, (kind, site, path, ip, fp, ua)), "NULL" if dwell is None else str(dwell)]
        values.append("(" + ",".join(fields) + ")")
    schema = "fictional_pages_" + uuid.uuid4().hex
    setup = f"""BEGIN;
SET LOCAL statement_timeout='5s';
CREATE SCHEMA {schema};
CREATE TABLE {schema}.users (id uuid, email text);
CREATE TABLE {schema}.ip_geo (ip text, city text, region text, country_code text, is_hosting boolean, is_vpn boolean, org text, asn text);
CREATE TABLE {schema}.analytics_events (id bigint, visitor_id text, user_id uuid, created_at timestamptz, type text, site text, path text, ip text, fp text, ua text, dwell_ms bigint);
INSERT INTO {schema}.users VALUES ('{operator}','admin@mastermind-x.com'),('{customer}','reader@example.test');
INSERT INTO {schema}.ip_geo VALUES ('203.0.113.22',NULL,NULL,NULL,true,false,NULL,NULL),('203.0.113.23',NULL,NULL,NULL,true,true,NULL,NULL),('203.0.113.77',NULL,NULL,NULL,true,false,NULL,NULL),('198.51.100.25','Fictionville',NULL,NULL,false,false,NULL,NULL);
INSERT INTO {schema}.analytics_events VALUES {','.join(values)};
"""
    def isolated(sql):
        return sql.replace("public.analytics_events", schema + ".analytics_events").replace("public.ip_geo", schema + ".ip_geo").replace("auth.users", schema + ".users")
    def differences(old, new):
        return (f"WITH old_rows AS ({isolated(old)}), new_rows AS ({isolated(new)}) "
                "SELECT json_build_object('old_minus_new',(SELECT count(*) FROM (SELECT * FROM old_rows EXCEPT ALL SELECT * FROM new_rows) d),"
                "'new_minus_old',(SELECT count(*) FROM (SELECT * FROM new_rows EXCEPT ALL SELECT * FROM old_rows) d));\n")
    sql = setup + differences(old_events, new_events) + differences(previous, current)
    # Limited results must preserve tie ordering as well as the full aggregates.
    sql += differences(previous.rsplit("limit 500", 1)[0] + "limit 2", current.rsplit("limit 500", 1)[0] + "limit 2")
    sql += isolated(prefix) + "SELECT json_build_object('null_rhs',(SELECT count(*) FROM (SELECT visitor_id FROM excluded UNION ALL SELECT visitor_id FROM bots) s WHERE visitor_id IS NULL),'accepted_ids',(SELECT json_agg(id ORDER BY id) FROM (" + isolated(new_events) + ") s));\nROLLBACK;"
    run = subprocess.run(["psql", "-X", "-q", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-h", socket,
                          "-p", str(port), "-U", getpass.getuser(), "-d", "postgres"], input=sql,
                         text=True, capture_output=True, timeout=30, check=True)
    results = [json.loads(line) for line in run.stdout.splitlines() if line.startswith("{")]
    assert len(results) == 4
    assert all(row == {"old_minus_new": 0, "new_minus_old": 0} for row in results[:3])
    assert results[3]["null_rhs"] == 0
    ids = set(results[3]["accepted_ids"])
    assert {4, 6, 13, 14, 15, 16, 17, 23, 28, 29} <= ids
    assert not ({2, 3, 8, 12, 18, 22, 26, 27} & ids)
    if private_filters:
        assert not ({19, 20, 21, 25} & ids)
        assert 24 in ids
