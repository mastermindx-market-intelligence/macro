"""AI Brief -> incumbent Fabric owner: one exclusive route, no bypass.

Offline only. The actual closed owner, workload policy and capability broker
use an isolated synthetic qualified transport record. The outbound transport
is substituted; the incumbent strict adapter (llm_auth's Fabric
wrapper), the response validation, the per-turn uncertainty latch, the usage
owner and the health ledger are the REAL ones. No credential, provider,
endpoint, gateway or network is used.

Run: python -m unittest discover -s tests -p test_master_brain_fabric_composition.py -v
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import yaml
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from engine import llm_auth, master_brain
from engine import provider_production_modes as owner
from engine import fabric_inference_client as client_module


#: The repo's autouse conftest fixture neutralises the reply cache for every
#: test (so a unit test can never write the REAL data/master_brain/reply_cache
#: tree). This suite exercises the cache contract itself, so it restores the
#: REAL functions captured at import time — and isolates them under a tmp root,
#: exactly the isolation the guard's own allow-list requires. The real tree is
#: never touched.
_REAL_CACHE_GET = master_brain._mb_reply_cache_get
_REAL_CACHE_PUT = master_brain._mb_reply_cache_put


MODE = "shared_fabric"
MODEL = "fabric-brief-v1"
PROVIDER = "minimax"
CAP_ID = "fabric_brief_pool"


def _brief_reply(summary="Measured conditions remain mixed.", **extra):
    payload = {"summary": summary, "tldr": ["Growth is steady."],
               "confidence": "medium"}
    payload.update(extra)
    return json.dumps(payload)


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text

    def model_dump(self):
        return {"type": "text", "text": self.text}


def _response(text=_brief_reply(), *, model=MODEL, stop="end_turn", tokens=(41, 13)):
    """One Anthropic-shaped response the incumbent strict adapter accepts."""
    blocks = [_TextBlock(text)] if text is not None else []
    return SimpleNamespace(
        model=model,
        content=blocks,
        stop_reason=stop,
        usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1])
        if tokens else None,
    )


class _UncertainFailure(RuntimeError):
    """A post-dispatch failure whose effect is unknown."""

    effect_unknown = True


class _RotatingResponse:
    """A response that rotates the served binding identity when the owner reads
    its usage — AFTER the owner has already validated the model and content.

    The rotation point matters: rotating BEFORE the owner's model check would
    fail the call for a different reason (a model mismatch) and would never
    exercise the post-dispatch identity comparison this test is about.
    """

    def __init__(self, base, holder, rotated_model):
        self._base = base
        self._holder = holder
        self._rotated = rotated_model

    def __getattr__(self, name):
        return getattr(self._base, name)

    @property
    def usage(self):
        provider = self._holder.get("provider")
        if provider is not None:
            provider["model"] = self._rotated
        return self._base.usage


class _Transport:
    """One turn-scoped client handed out by the owner."""

    def __init__(self, wire):
        self._wire = wire
        self.messages = self

    def create(self, **kwargs):
        self._wire.calls.append(kwargs)
        step = self._wire.steps.pop(0) if self._wire.steps else _response()
        if isinstance(step, BaseException):
            raise step
        return step


class _Wire:
    """Shared outbound state: the steps to return and the calls that happened."""

    def __init__(self):
        self.steps = []
        self.calls = []

    def client(self):
        return _Transport(self)


_REAL_OWNER_MAKER = owner.make_application_fabric_factory
_SOURCE_ROOT = Path(owner.__file__).resolve().parents[1]


class _ControlledOwner:
    """Stands in for provider_production_modes.make_application_fabric_factory.

    It records the call arguments, so the consumer's contract is observable,
    and yields a FRESH five-field binding per invocation, like the incumbent.
    """

    def __init__(self, wire):
        self.wire = wire
        self.calls = []
        self.invocations = 0
        self.refusal = None

    def make_application_fabric_factory(self, *, mode_id, lane, workload_cfg, root):
        self.calls.append({
            "mode_id": mode_id,
            "lane": lane,
            "workload_cfg": dict(workload_cfg),
            "root": Path(root),
        })
        if self.refusal is not None:
            raise self.refusal

        return _REAL_OWNER_MAKER(mode_id=mode_id, lane=lane,
                                 workload_cfg=workload_cfg, root=root)

    def client(self, **kwargs):
        self.invocations += 1
        return self.wire.client()



class MasterBrainFabricCompositionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.wire = _Wire()
        self.owner = _ControlledOwner(self.wire)
        self.state = {"macro": {"date": "2026-11-04", "summary": "Observed state."}}
        self.cfg = {"max_tokens": 1000, "emit_theses": False,
                    "usage_lane": "master-brain"}
        cfgdir = self.root / "config"
        cfgdir.mkdir()
        (cfgdir / "provider_workloads.v1.json").write_text(
            (_SOURCE_ROOT / "config/provider_workloads.v1.json").read_text())
        transport = owner._ApplicationFabricTransport(
            "http://127.0.0.1:8311/v1", "TEST_BRIEF_FABRIC_TOKEN", PROVIDER,
            MODEL, "subscription", CAP_ID, "fixture_brief_capability",
            qualified=True, application_allowed=True)
        row = {key: getattr(transport, key) for key in owner._APPLICATION_IDENTITY_FIELDS}
        row.update(transport_id="fixture_brief", enabled=True, application_allowed=True,
                   qualification=owner.PROFILE_QUALIFIED_CANARY,
                   qualification_ref="fixture:source-composition-only", qualified_until=time.time()+3600)
        document = json.loads((_SOURCE_ROOT / "config/provider_production_modes.v1.json").read_text())
        document["application_fabric_modes"] = {MODE: row}
        (cfgdir / "provider_production_modes.v1.json").write_text(json.dumps(document))
        (cfgdir / "capability_manifest.yml").write_text(yaml.safe_dump({"capabilities": [{
            "capability_id": "fixture_brief_capability", "secret_ref": "TEST_BRIEF_FABRIC_TOKEN",
            "kill_state": "active", "allowed_lanes": ["master-brain"]}]}))

        def start(patcher):
            self.addCleanup(patcher.stop)
            return patcher.start()

        start(patch.dict(os.environ, {
            "MM_PROVIDER_APPLICATION_MODE": MODE,
            "TEST_BRIEF_FABRIC_TOKEN": "synthetic-offline-brief-token",
            "PROVIDER_HEALTH_PATH": str(self.root / "health.jsonl"),
            "AI_COSTS_STATE_ROOT": str(self.root / "costs"),
        }, clear=True))
        start(patch.dict(owner._APPLICATION_FABRIC_TRANSPORTS, {"fixture_brief": transport}))
        start(patch.object(owner, "__file__", str(self.root / "engine/provider_production_modes.py")))
        start(patch.object(client_module, "FabricInferenceClient", self.owner.client))
        start(patch.object(owner, "make_application_fabric_factory",
                           self.owner.make_application_fabric_factory, create=True))
        # Restore the real reply cache under a tmp root (see the module note).
        start(patch.object(master_brain, "_mb_reply_cache_get", _REAL_CACHE_GET))
        start(patch.object(master_brain, "_mb_reply_cache_put", _REAL_CACHE_PUT))

    # -- helpers ----------------------------------------------------------- #
    def synthesize(self, **overrides):
        return master_brain.synthesize(
            self.state, cfg={**self.cfg, **overrides}, root=self.root)

    def caches(self):
        return sorted((self.root / "data/master_brain/reply_cache").glob("*.txt"))

    def cost_rows(self):
        return [json.loads(line) for path in (self.root / "costs").rglob("*.jsonl")
                for line in path.read_text().splitlines()]

    def health_rows(self):
        path = self.root / "health.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    # -- 1. the custom endpoint never becomes a second client --------------- #
    def test_custom_endpoint_never_reaches_the_legacy_client_secret_or_discovery(self):
        with patch.object(master_brain, "_client",
                          side_effect=AssertionError("legacy client reached")), \
             patch.object(master_brain, "_is_deepseek_lane",
                          side_effect=AssertionError("legacy ladder reached")), \
             patch.object(llm_auth, "build_providers",
                          side_effect=AssertionError("provider discovery reached")), \
             patch.object(llm_auth, "mark_dead",
                          side_effect=AssertionError("mark_dead reached")), \
             patch("lib.config.secret",
                   side_effect=AssertionError("legacy secret read")):
            brief = self.synthesize(llm_base_url="https://custom.invalid/anthropic",
                                    api_key_env="CUSTOM_ENDPOINT_KEY",
                                    llm_model="custom-v9")
        self.assertIsNone(brief["degraded_reason"])
        self.assertEqual(brief["model"], MODEL)
        self.assertEqual(brief["served_by"], PROVIDER)
        self.assertEqual(len(self.wire.calls), 1)
        call = self.wire.calls[0]
        # ONLY the arguments the transport supports, plus the owner's own
        # request identity. Never a seed, never a hidden ignored kwarg.
        self.assertEqual(set(call) - {"request_id"},
                         {"model", "max_tokens", "system", "messages"})
        self.assertNotIn("seed", call)
        self.assertEqual(call["model"], MODEL)
        self.assertEqual(call["max_tokens"], 1000)
        self.assertEqual(call["messages"][0]["role"], "user")

    # -- 2. the caches are separate, and a hit costs no provider call ------- #
    def test_legacy_cache_cannot_satisfy_the_application_route(self):
        legacy = _brief_reply("Legacy cached text.")
        legacy_cfg = {"emit_theses": False, "max_tokens": 1000}
        # The legacy route needs the host selection ABSENT; the application
        # route below must not be able to read what the legacy route cached.
        with patch.dict(os.environ):
            os.environ.pop("MM_PROVIDER_APPLICATION_MODE", None)
            with patch.object(master_brain, "_call_model",
                              lambda system, user, cfg: (legacy, None)):
                old = master_brain.synthesize(self.state, cfg=legacy_cfg, root=self.root)
                cached_legacy = master_brain.synthesize(self.state, cfg=legacy_cfg, root=self.root)
        self.assertEqual(old["summary"], "Legacy cached text.")
        self.assertEqual(cached_legacy["served_by"], "cache")
        brief = self.synthesize()
        self.assertNotEqual(brief["summary"], "Legacy cached text.")
        self.assertEqual(brief["served_by"], PROVIDER)
        self.assertEqual(len(self.wire.calls), 1)
        # the legacy entry and the application entry are DIFFERENT files
        self.assertEqual(len(self.caches()), 2)

    def test_eligible_application_cache_hit_performs_no_provider_call(self):
        first = self.synthesize()
        self.assertEqual(len(self.wire.calls), 1)
        before = len(self.wire.calls)
        second = self.synthesize()
        self.assertEqual(second["served_by"], "cache")
        self.assertEqual(second["summary"], first["summary"])
        self.assertEqual(second["model"], MODEL)
        self.assertEqual(len(self.wire.calls), before)
        self.assertEqual(len(self.cost_rows()), 1)

    # -- 3. a revoked owner refuses BEFORE the cached result ----------------- #
    def test_revoked_owner_refuses_before_the_cached_result(self):
        good = self.synthesize()
        self.assertEqual(good["summary"], "Measured conditions remain mixed.")
        self.assertEqual(len(self.wire.calls), 1)
        self.owner.refusal = owner.ProductionModeConfigError("mode disabled")
        with patch.object(master_brain, "_mb_reply_cache_get",
                          side_effect=AssertionError("cache read reached")):
            brief = self.synthesize()
        self.assertIsNone(brief["summary"])
        self.assertIsNone(brief["served_by"])
        self.assertIsNone(brief["model"])
        self.assertEqual(brief["degraded_reason"], "application_fabric_owner_refused")
        self.assertEqual(len(self.wire.calls), 1)
        self.assertEqual(len(self.caches()), 1)

    def test_an_unqualified_binding_refuses_closed_and_never_reads_the_cache(self):
        self.synthesize()
        before = len(self.wire.calls)
        bindings_before = self.owner.invocations
        config = self.root / "config/provider_production_modes.v1.json"
        document = json.loads(config.read_text())
        document["application_fabric_modes"][MODE]["qualification"] = owner.PROFILE_UNQUALIFIED_PENDING_CANARY
        config.write_text(json.dumps(document))
        with patch.object(owner, "_resolve_credential",
                          side_effect=AssertionError("credential read reached")), \
             patch.object(master_brain, "_mb_reply_cache_get",
                          side_effect=AssertionError("cache read reached")):
            brief = self.synthesize()
        self.assertIsNone(brief["summary"])
        self.assertEqual(brief["degraded_reason"], "application_fabric_binding_unavailable")
        self.assertEqual(len(self.wire.calls), before)
        self.assertEqual(self.owner.invocations, bindings_before)

    # -- 4. a post-dispatch failure never retries, marks dead or falls back -- #
    def test_post_dispatch_failures_never_retry_mark_dead_or_fall_back(self):
        for failure in (TypeError("wire detail"), TimeoutError("wire detail"),
                        RuntimeError("wire detail"), _UncertainFailure()):
            with self.subTest(failure=type(failure).__name__):
                self.wire.calls.clear()
                self.wire.steps = [failure]
                with patch.object(llm_auth, "mark_dead",
                                  side_effect=AssertionError("mark_dead reached")):
                    brief = self.synthesize()
                self.assertIsNone(brief["summary"])
                self.assertTrue(brief["degraded_reason"].startswith("application_fabric_"))
                self.assertNotIn("wire detail", brief["degraded_reason"])
                self.assertEqual(len(self.wire.calls), 1)

    def test_an_empty_response_is_refused_without_a_second_request(self):
        self.wire.steps = [_response(text=None)]
        brief = self.synthesize()
        self.assertIsNone(brief["summary"])
        # the owner collapses an empty reply into its own bounded refusal
        self.assertEqual(brief["degraded_reason"], "application_fabric_unavailable")
        self.assertEqual(len(self.wire.calls), 1)
        self.assertEqual(self.caches(), [])

    # -- 5. the rewrite is a second intentional step of the SAME operation --- #
    def test_accepted_rewrite_is_a_second_intentional_step_of_the_same_operation(self):
        self.wire.steps = [_response(_brief_reply("neural_web conditions.")),
                           _response(_brief_reply("Plain conditions."))]
        brief = self.synthesize()
        self.assertEqual(brief["summary"], "Plain conditions.")
        self.assertEqual(brief["style_flags"], [])
        self.assertEqual(brief["served_by"], PROVIDER)
        self.assertEqual(brief["model"], MODEL)
        self.assertEqual(len(self.wire.calls), 2)
        ids = [call["request_id"] for call in self.wire.calls]
        self.assertNotEqual(ids[0], ids[1])
        # same operation, distinct intentional steps
        self.assertEqual(ids[0].rsplit(":", 1)[0], ids[1].rsplit(":", 1)[0])
        self.assertTrue(ids[0].endswith(":brain:0"))
        self.assertTrue(ids[1].endswith(":brain:1"))
        rows = self.cost_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0]["provider"], rows[0]["key_id"]), (PROVIDER, CAP_ID))
        self.assertEqual(rows[0]["input_tokens"], 41)
        self.assertEqual(rows[0]["lane"], "master-brain")
        self.assertEqual(len(self.health_rows()), 2)

    # -- 6. an uncertain rewrite keeps the draft without a third request ---- #
    def test_uncertain_rewrite_keeps_the_draft_without_a_third_request_or_clean_cache(self):
        self.wire.steps = [_response(_brief_reply("neural_web conditions.")),
                           _UncertainFailure()]
        brief = self.synthesize()
        self.assertEqual(brief["summary"], "neural_web conditions.")
        self.assertTrue(brief["style_flags"])
        self.assertTrue(brief["degraded_reason"])
        self.assertNotIn("sensitive", brief["degraded_reason"])
        self.assertEqual(len(self.wire.calls), 2)
        # a degraded rewrite is not a clean success: nothing is cached
        self.assertEqual(self.caches(), [])

    # -- 7. a changed served identity cannot poison the cache -------------- #
    def test_changed_served_identity_cannot_poison_the_cache(self):
        holder = {}
        real_build = llm_auth.build_fabric_provider

        def capturing_build(factory, *, request_id, workload_cfg=None):
            provider = real_build(factory, request_id=request_id, workload_cfg=workload_cfg)
            holder["provider"] = provider
            return provider

        self.wire.steps = [_RotatingResponse(_response(), holder, "rotated-model")]
        with patch.object(llm_auth, "build_fabric_provider", capturing_build):
            brief = self.synthesize()
        self.assertEqual(brief["model"], "rotated-model")
        self.assertEqual(self.caches(), [])

    # -- 8. the incumbent's own guards keep their force --------------------- #
    def test_the_incumbent_unqualified_workload_floor_is_preserved(self):
        os.environ["MM_PROVIDER_WORKLOAD_PROFILE"] = "production"
        brief = self.synthesize()
        self.assertIsNone(brief["summary"])
        self.assertIn("binding_unavailable", brief["degraded_reason"])
        self.assertEqual(len(self.wire.calls), 0)
        self.assertEqual(self.owner.invocations, 0)

    def test_the_workload_profile_travels_unchanged_to_the_owner_gate(self):
        for profile in (None, "", "site_inference"):
            with self.subTest(profile=profile):
                self.owner.calls.clear()
                self.synthesize(workload_profile=profile)
                self.assertEqual(len(self.owner.calls), 1)
                call = self.owner.calls[0]
                self.assertEqual(call["mode_id"], MODE)
                self.assertEqual(call["lane"], "master-brain")
                self.assertEqual(call["root"], self.root.resolve())
                # an invalid null/empty profile is passed through unchanged —
                # the owner's gate decides, not this consumer
                self.assertEqual(call["workload_cfg"]["workload_profile"], profile)
                self.assertEqual(call["workload_cfg"]["provider_order"],
                                 ["fabric"])

    def test_a_conflicting_explicit_mode_refuses_instead_of_weakening_the_host_choice(self):
        brief = self.synthesize(production_mode="minimax_payg_api")
        self.assertEqual(brief["degraded_reason"], "application_fabric_conflicting_mode")
        self.assertIsNone(brief["summary"])
        self.assertIsNone(brief["model"])
        self.assertIsNone(brief["served_by"])
        self.assertEqual(len(self.wire.calls), 0)
        self.assertEqual(self.caches(), [])

    def test_the_same_mode_in_the_explicit_config_is_not_a_contradiction(self):
        brief = self.synthesize(production_mode=MODE)
        self.assertIsNone(brief["degraded_reason"])
        self.assertEqual(len(self.wire.calls), 1)

    def test_an_empty_host_selection_refuses_closed(self):
        os.environ["MM_PROVIDER_APPLICATION_MODE"] = "   "
        brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "application_fabric_invalid_mode")
        self.assertIsNone(brief["summary"])
        self.assertEqual(len(self.wire.calls), 0)

    def test_the_shared_call_entry_point_honours_the_mandatory_selection(self):
        text, reason = master_brain._call_model("system", "user", dict(self.cfg))
        self.assertIsNotNone(text)
        self.assertIsNone(reason)
        self.assertEqual(len(self.wire.calls), 1)

    def test_a_missing_companion_owner_refuses_closed_instead_of_falling_back(self):
        with patch.object(owner, "make_application_fabric_factory", None):
            brief = self.synthesize()
        self.assertEqual(brief["degraded_reason"], "application_fabric_owner_unavailable")
        self.assertIsNone(brief["summary"])
        self.assertEqual(len(self.wire.calls), 0)


if __name__ == "__main__":
    unittest.main()
