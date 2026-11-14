"""Malformed concept responses are failed refreshes, not filing evidence."""
import copy
import json
import pytest
from scripts import build_debt_maturity as bdm
from engine.debt_maturity import BUCKETS

CIK = "0000999999"
ENTRY = {"end":"2025-12-31","filed":"2026-02-01","accn":"0000999999-26-000001",
         "form":"10-K","fp":"FY","fy":2025,"val":100_000_000}
FACTS = {"cik":999999,"facts":{"us-gaap":{
    tag:{"units":{"USD":[copy.deepcopy(ENTRY)]}} for _,tag,_,_ in BUCKETS}}}

class Response:
    def __init__(self, shape):
        self.shape = shape
        self.status_code = shape if isinstance(shape, int) else 200
    def json(self):
        if self.shape == "bad_json":
            raise ValueError("invalid body")
        return {"list": [], "missing_units": {}, "empty_units": {"units":{}},
                "string_units": {"units":"invalid"},
                "scalar_entries": {"units":{"USD":123}},
                "object_entries": {"units":{"USD":{"val":123}}},
                "string_entries": {"units":{"USD":"invalid"}},
                "null_entry": {"units":{"USD":[None]}},
                "mixed_entries": {"units":{"USD":[copy.deepcopy(ENTRY), 123]}},
                "valid": {"units":{"USD":[copy.deepcopy(ENTRY)]}}}[self.shape]

class Session:
    def __init__(self, specs):
        self.specs = specs
        self.calls = []
    def get(self, url, **kwargs):
        tag = url.rsplit("/",1)[-1][:-5]
        self.calls.append(tag)
        return Response(self.specs[tag])

@pytest.mark.parametrize("shape", ["bad_json", "list", "missing_units", "empty_units", "string_units", "scalar_entries", "object_entries", "string_entries", "null_entry", "mixed_entries"])
@pytest.mark.parametrize("position", range(9))
@pytest.mark.parametrize("sibling", [404, 429, "valid"])
@pytest.mark.parametrize("seeded", [False, True])
def test_invalid_200_never_creates_or_overwrites_cache(tmp_path, monkeypatch, shape, position, sibling, seeded):
    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(bdm, "_utc_now_iso", lambda: "2026-02-02T00:00:00+00:00")
    if seeded:
        assert bdm.refresh_cache_for_cik(CIK, full_companyfacts=FACTS)
    path = tmp_path / f"CIK{CIK}.json"
    before = path.read_bytes() if path.exists() else None
    specs = dict.fromkeys(bdm._ALL_TAGS, sibling)
    specs[bdm._ALL_TAGS[position]] = shape
    session = Session(specs)
    assert bdm.refresh_cache_for_cik(CIK, session=session) is False
    assert len(session.calls) == len(bdm._ALL_TAGS)
    assert (path.read_bytes() if path.exists() else None) == before
    assert not list(tmp_path.glob("*.tmp"))
    if seeded:
        assert bdm.load_cached_facts(CIK)["fetched_at"] == "2026-02-02T00:00:00+00:00"

@pytest.mark.parametrize("sibling", [404, "valid"])
def test_existing_decodable_response_contract_remains(tmp_path, monkeypatch, sibling):
    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path)
    session = Session(dict.fromkeys(bdm._ALL_TAGS, sibling))
    assert bdm.refresh_cache_for_cik(CIK, session=session)
    cached = bdm.load_cached_facts(CIK)
    assert bool(cached.get("confirmed_no_filings")) is (sibling == 404)



def test_valid_empty_unit_array_retains_existing_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(bdm, "_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(Response, "json", lambda self: {"units":{"USD":[]}})
    assert bdm.refresh_cache_for_cik(CIK, session=Session(dict.fromkeys(bdm._ALL_TAGS, "valid")))
    cached = bdm.load_cached_facts(CIK)
    assert not cached.get("confirmed_no_filings")
    assert all(row["units"] == {"USD":[]} for row in cached["facts"]["us-gaap"].values())
