"""Synthetic proxy schema, assignment and secrecy regression laws.

All slots come from explicit temporary YAML through the actual parser. These
assertions do not qualify a real pool, account identity or runtime allocation."""

from __future__ import annotations

import pytest

from xguerrilla import net

SLOT_COUNT = 16


@pytest.fixture(scope="module")
def slots(synthetic_proxy_path):
    return net.load(str(synthetic_proxy_path))


@pytest.fixture(scope="module")
def handles(slots):
    return [f"kid.{i:02d}" for i in range(len(slots))]


# ---------------------------------------------------------------------------
# 1. the pool loads whole
# ---------------------------------------------------------------------------

def test_load_returns_sixteen_slots(slots):
    """A short pool means a child cannot be placed; a long one means drift."""
    assert len(slots) == SLOT_COUNT, f"pool has {len(slots)} slots, expected {SLOT_COUNT}"


def test_ports_ascend(slots):
    """The inventory is written in port order, and load() preserves it.

    Operators bisect by eye when a single slot misbehaves; an unordered file
    makes that impossible and usually hides a copy-paste duplicate.
    """
    ports = [s.port for s in slots]
    assert ports == sorted(ports), f"ports out of order: {ports}"


def test_no_duplicate_hosts(slots):
    """Two slots on one host is two children on one address."""
    hosts = [s.host for s in slots]
    assert len(hosts) == len(set(hosts)), (
        f"{len(hosts) - len(set(hosts))} duplicated host(s) in the pool"
    )


def test_slot_names_are_unique_and_ordered(slots):
    """``pool-NN`` names are how telemetry and the runbook refer to a slot."""
    names = [s.name for s in slots]
    assert len(names) == len(set(names)), f"duplicate slot names: {names}"
    assert names == sorted(names), f"slot names out of order: {names}"


# ---------------------------------------------------------------------------
# 2. assignment is stable
# ---------------------------------------------------------------------------

def test_assign_is_stable_for_a_handle(slots, handles, synthetic_proxy_path):
    """The same handle resolves to the same slot on every call and every load.

    This is the law a restart depends on: if assign() drifted, a child would
    come back up on a stranger's address and lose months of reputation.
    """
    for handle in handles:
        first = net.assign(slots, handle)
        assert net.assign(slots, handle) is first or net.assign(slots, handle) == first
    reloaded = net.load(str(synthetic_proxy_path))
    for handle in handles:
        assert net.assign(reloaded, handle).name == net.assign(slots, handle).name


def test_assign_covers_the_whole_pool(slots, handles):
    """The hash spreads 16 handles over 16 slots — no slot is unreachable."""
    assert {net.assign(slots, h).name for h in handles} == {s.name for s in slots}


# ---------------------------------------------------------------------------
# 3. exclusivity
# ---------------------------------------------------------------------------

def test_assert_exclusive_passes_for_sixteen_handles(slots, handles):
    """One slot, one child: a full cohort is legal."""
    assert len(handles) == len(slots)
    net.assert_exclusive(handles, slots)


def test_assert_exclusive_raises_for_seventeen_handles(slots, handles):
    """Seventeen children on sixteen slots must be refused, not silently shared."""
    with pytest.raises(ValueError):
        net.assert_exclusive(handles + ["kid.99"], slots)


def test_assert_exclusive_rejects_a_duplicate_handle(slots):
    """The same handle twice would take two slots for one child."""
    with pytest.raises(ValueError):
        net.assert_exclusive(["kid.00", "kid.00"], slots)


def test_bind_gives_every_child_its_own_slot(slots, handles):
    """bind() is the allocation an operator actually runs — no collisions."""
    bound = net.bind(slots, handles)
    assert set(bound) == set(handles)
    used = [slot.name for slot in bound.values()]
    assert len(used) == len(set(used)), f"collisions: {used}"


# ---------------------------------------------------------------------------
# 4. secrets do not leak
# ---------------------------------------------------------------------------

def test_public_never_contains_the_password(slots):
    """``public()`` is what goes into logs, telemetry and a support ticket."""
    for slot in slots:
        public = slot.public()
        # kept boolean so a failure message never echoes the secret itself
        leaked = slot.password in repr(public) or slot.password in str(sorted(public.items()))
        assert not leaked, f"{slot.name} leaks its password"
        assert "password" not in public


def test_public_is_loggable_shape(slots):
    """The loggable form keeps exactly the fields an operator needs to bisect."""
    for slot in slots:
        public = slot.public()
        assert set(public) == {"slot", "host", "port", "user"}
        assert public["slot"] == slot.name
        assert public["host"] == slot.host
        assert public["port"] == slot.port
        assert public["user"] == slot.user


def test_repr_does_not_leak_the_password(slots):
    """A dataclass repr lands in tracebacks; it must not carry the secret."""
    leaking = [s.name for s in slots if s.password in repr(s)]
    assert leaking == [], f"{len(leaking)} slot(s) print their password in repr"


# ---------------------------------------------------------------------------
# 5. the URL a driver hands to the browser
# ---------------------------------------------------------------------------

def test_every_url_is_a_parseable_http_url(slots):
    """The proxy URL is passed straight to the browser: shape failures are fatal there."""
    from urllib.parse import urlsplit

    for slot in slots:
        parts = urlsplit(slot.url)
        assert parts.scheme == "http", f"{slot.name}: scheme {parts.scheme!r}"
        assert parts.hostname == slot.host, f"{slot.name}: host {parts.hostname!r}"
        assert parts.port == slot.port, f"{slot.name}: port {parts.port!r}"
        assert parts.username == slot.user
        assert (parts.password == slot.password) is True, f"{slot.name}: password not round-tripped"
        assert "@" in slot.url and slot.url.endswith(f":{slot.port}")


def test_urls_are_distinct(slots):
    """Two identical URLs means two children behind one exit address."""
    urls = [s.url for s in slots]
    assert len(urls) == len(set(urls))
