"""Reproducible negative-first tests for review-only Catalyst partner packs.

No partner outreach, real ticker event assertion, send, publishing, network,
credentials or third-party co-brand authority is exercised by this suite.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from engine.marketing.catalyst_partner_pack import (
    PackRejected, build_partner_pack, write_partner_pack,
)
from scripts.build_catalyst_partner_pack import (
    DEMO_EVENT, DEMO_NOW, DEMO_PROFILES,
)

ROOT = Path(__file__).resolve().parents[1]


class CatalystPartnerPackTests(unittest.TestCase):

    def setUp(self):
        self.event = copy.deepcopy(DEMO_EVENT)
        self.partner = copy.deepcopy(DEMO_PROFILES[0][0])
        self.tickers = ["EXA"]

    def make(self, **kwargs):
        return build_partner_pack(
            self.event, self.partner, self.tickers,
            now_utc=DEMO_NOW, **kwargs,
        )

    def refused(self, code, **kwargs):
        with self.assertRaises(PackRejected) as caught:
            self.make(**kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_three_full_demo_previews_are_generated_with_unique_audience_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" /
                                     "build_catalyst_partner_pack.py"),
                 "--demo", "--out", temp],
                cwd=ROOT, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            packs = json.loads(result.stdout)["generated"]
            self.assertEqual(len(packs), 3)
            self.assertEqual(len({p["pack_id"] for p in packs}), 3)
            self.assertEqual(len({p["partner"] for p in packs}), 3)
            analyses = set()
            for p in packs:
                self.assertEqual(p["status"], "DRAFT_HOLD")
                self.assertFalse(p["scan_destination_verified"])
                path = Path(temp) / p["partner"]
                self.assertEqual({f.name for f in path.iterdir()}, {
                    "index.html", "newsletter.md", "social.txt", "manifest.json",
                    "embed-concept.html", "intelligence-card.svg",
                })
                html = (path / "index.html").read_text()
                self.assertIn("DRAFT PREVIEW", html)
                self.assertIn("Synthetic fixture demonstration", html)
                self.assertIn("No partnership, endorsement", html)
                self.assertIn("noindex,nofollow,noarchive", html)
                self.assertIn("https://preview.invalid/", html)
                self.assertIn("public", html.lower())
                svg = (path / "intelligence-card.svg").read_text()
                self.assertIn("<svg", svg)
                self.assertIn("MASTERMIND", svg)
                self.assertNotIn("<script", svg)
                social_text = (path / "social.txt").read_text()
                self.assertIn("https://preview.invalid/", social_text)
                self.assertIn("DRAFT THREAD 1/2\n", social_text)
                self.assertIn("DRAFT THREAD 2/2\n", social_text)
                parts = social_text.strip().split("\n\n")
                self.assertEqual(len(parts), 2)
                post_one = parts[0].split("\n", 1)[1]
                post_two = parts[1].split("\n", 1)[1]
                self.assertLessEqual(len(post_one), 275)
                self.assertLessEqual(len(post_two), 275)
                manifest = json.loads((path / "manifest.json").read_text())
                self.assertTrue(manifest["event"]["demo_only"])
                self.assertEqual(manifest["publication_status"], "DRAFT_HOLD")
                self.assertNotIn("card_svg", manifest)
                self.assertEqual(set(manifest["selected_tickers"]),
                                 set(p["partner"] == "demo-earnings-letter" and ["EXA"]
                                     or p["partner"] == "demo-chip-community"
                                     and ["EXA", "EXB"] or ["EXA", "EXB", "EXC"]))
                analyses.add((path / "newsletter.md").read_text())
            self.assertEqual(len(analyses), 3)

    def test_deterministic_idempotent_outputs(self):
        a = self.make()
        b = self.make()
        self.assertEqual(a, b)
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            write_partner_pack(a, folder)
            initial = {p.name: p.read_bytes() for p in folder.iterdir()}
            write_partner_pack(b, folder)
            self.assertEqual(initial, {p.name: p.read_bytes()
                                       for p in folder.iterdir()})

    def test_deep_link_keeps_canonical_utm_and_exact_ticker_event(self):
        p = self.make()
        url = urlsplit(p["scan_link"])
        params = parse_qs(url.query)
        self.assertEqual(params["utm_source"], ["partner"])
        self.assertEqual(params["utm_medium"], ["partner-demo-earnings-letter"])
        self.assertEqual(params["utm_campaign"], ["catalyst_scan"])
        self.assertEqual(params["utm_content"], [p["pack_id"]])
        self.assertEqual(params["event_id"], ["synthetic-semis-brief"])
        self.assertEqual(params["tickers"], ["EXA"])
        self.assertEqual(len(params), 6)
        self.assertIn(p["scan_link"], p["newsletter"])
        self.assertIn(p["scan_link"], p["social"])
        self.assertIn(p["scan_link"].replace("&", "&amp;"), p["embed"])

    def test_registered_scan_requires_receipt(self):
        self.refused("SCAN_ROUTE_UNREGISTERED",
                     scan_url="https://www.mastermind-x.com/scan/")
        self.refused("SCAN_ROUTE_UNREGISTERED",
                     route_receipt="route-01")
        p = self.make(scan_url="https://www.mastermind-x.com/api/catalyst",
                      route_receipt="approved-route-01")
        self.assertFalse(p["link_is_placeholder"])
        self.assertTrue(p["scan_link"].startswith(
            "https://www.mastermind-x.com/api/catalyst?"))
        # Exact route preservation: canonical_link builds the query while
        # FastAPI expects GET /api/catalyst, not the trailing-slash variant.
        self.assertEqual(urlsplit(p["scan_link"]).path, "/api/catalyst")
        self.refused("INVALID_SCAN_ROUTE",
                     scan_url="https://www.mastermind-x.com/scan/",
                     route_receipt="approved-route-01")
        self.refused("INVALID_SCAN_ROUTE",
                     scan_url="https://untrusted.example.com/api/catalyst",
                     route_receipt="approved-route-01")
        self.assertEqual(p["publication_status"], "DRAFT_HOLD")

    def test_duplicate_utm_or_unregistered_placeholder_with_receipt_blocked(self):
        self.refused("DUPLICATE_OR_INVALID_UTM",
                     scan_url="https://www.mastermind-x.com/scan/?utm_source=x",
                     route_receipt="approved-route-01")
        self.refused("ROUTE_RECEIPT_FOR_PLACEHOLDER",
                     scan_url="https://preview.invalid/scan/",
                     route_receipt="approved-route-01")

    def test_frozen_session00_partner_consumer_signature_is_accepted(self):
        profile = copy.deepcopy(self.partner)
        profile["selected_tickers"] = ["EXA"]
        result = build_partner_pack(self.event, profile, now_utc=DEMO_NOW)
        self.assertEqual(result["selected_tickers"], ["EXA"])
        self.assertEqual(result["publication_status"], "DRAFT_HOLD")
        with self.assertRaises(PackRejected) as exc:
            build_partner_pack(self.event, profile, preview_only=False,
                               now_utc=DEMO_NOW)
        self.assertEqual(exc.exception.code, "PUBLICATION_UNAUTHORIZED")

    def test_public_packet_producer_verification_required_for_non_demo(self):
        self.event["demo_only"] = False
        self.refused("EVENT_VERIFICATION_MISSING")
        self.event["verification"] = {
            "status": "VERIFIED",
            "source_owner": "engine.marketing.catalyst_packets",
            "receipt_id": "test-receipt-not-production",
        }
        result = self.make()
        self.assertFalse(result["event"]["demo_only"])

    def test_synthetic_fixture_never_masquerades_as_verified_event(self):
        self.event["verification"]["status"] = "VERIFIED"
        self.refused("INVALID_SYNTHETIC_FIXTURE")

    def test_retracted_and_superseded_events_never_generate(self):
        for status in ("retracted", "superseded", "unknown", None):
            self.event["status"] = status
            self.refused("RETRACTED_OR_SUPERSEDED_EVENT")

    def test_expired_future_asof_and_excessive_age_blocked(self):
        self.event["expires_at_utc"] = "2026-10-09T04:30:00Z"
        self.refused("STALE_OR_FUTURE_EVENT")
        self.event["expires_at_utc"] = "2026-10-12T04:30:00Z"
        self.event["as_of_utc"] = "2026-10-10T04:00:00Z"
        self.refused("STALE_OR_FUTURE_EVENT")
        self.event["as_of_utc"] = "2026-10-03T04:00:00Z"
        self.refused("STALE_OR_FUTURE_EVENT")

    def test_headline_has_distinct_public_source_evidence_receipt(self):
        original = self.make()
        self.assertEqual(original["event"]["headline_evidence_ids"],
                         ["source-synthetic-001"])
        del self.event["headline_evidence_ids"]
        self.refused("HEADLINE_EVIDENCE_MISSING")
        self.event["headline_evidence_ids"] = ["unknown-private-source"]
        self.refused("HEADLINE_EVIDENCE_MISSING")
        self.event["headline_evidence_ids"] = ["source-synthetic-001",
                                                "source-synthetic-001"]
        self.refused("HEADLINE_EVIDENCE_MISSING")

    def test_future_source_and_unknown_source_ids_blocked(self):
        self.event["sources"][0]["published_at_utc"] = "2026-10-09T04:00:00Z"
        self.refused("FUTURE_SOURCE")
        self.event = copy.deepcopy(DEMO_EVENT)
        self.event["claims"][0]["source_ids"] = ["missing-source"]
        self.refused("UNSOURCED_OR_DUPLICATE_CLAIM")

    def test_redundant_social_card_is_withheld_by_incumbent_value_gate(self):
        # A source-backed claim repeated in full as the social post does not
        # earn a second giant-image surface. This must be a genuine veto.
        self.event["affected_tickers"][0]["evidence_ids"] = ["fixture-claim-exa"]
        p = self.make()
        self.assertEqual(p["media_status"],
                         "CARD_WITHHELD_NO_ADDITIONAL_VALUE")
        self.assertIsNone(p["card_svg"])
        with tempfile.TemporaryDirectory() as temp:
            written = write_partner_pack(p, temp)
            self.assertNotIn("intelligence-card.svg", [f.name for f in written])
            page = (Path(temp) / "index.html").read_text()
            self.assertIn("Duplicate card withheld", page)
            self.assertNotIn("Image rehosting withheld", page)

    def test_additive_card_and_canonical_style_tokens_survive_render(self):
        p = self.make()
        self.assertEqual(p["media_status"], "READY_FOR_REVIEW")
        self.assertIsNotNone(p["card_svg"])
        with tempfile.TemporaryDirectory() as temp:
            write_partner_pack(p, temp)
            page = (Path(temp) / "index.html").read_text()
            root_theme = (ROOT / "templates" / "theme.css").read_text()
            first = root_theme.index(":root {")
            last = root_theme.index("\n}\n", first)
            self.assertIn(root_theme[first:last+2], page)
            self.assertIn("font-family:var(--font-ui)", page)
            self.assertIn("var(--r-card", page)

    def test_rights_fail_closed_and_dont_rehost_without_positive_receipt(self):
        self.event["sources"][0]["rights"]["public_display"] = False
        self.refused("BLOCKED_PUBLIC_RIGHTS")
        self.event = copy.deepcopy(DEMO_EVENT)
        self.event["sources"][0]["rights"]["public_link"] = False
        self.refused("BLOCKED_PUBLIC_RIGHTS")
        self.event = copy.deepcopy(DEMO_EVENT)
        self.event["sources"][0]["rights"].pop("receipt_id")
        self.refused("RIGHTS_RECEIPT_MISSING")
        self.event = copy.deepcopy(DEMO_EVENT)
        self.event["sources"][0]["rights"]["public_rehost"] = False
        result = self.make()
        self.assertEqual(result["media_status"], "REHOST_RIGHTS_BLOCKED")
        self.assertIsNone(result["card_svg"])
        with tempfile.TemporaryDirectory() as temp:
            files = write_partner_pack(result, temp)
            self.assertNotIn("intelligence-card.svg", {f.name for f in files})
            self.assertIn("Image rehosting withheld",
                          (Path(temp) / "index.html").read_text())

    def test_unsupported_and_unknown_ticker_are_never_dressed_up(self):
        self.tickers = ["NVDA"]
        self.refused("UNSUPPORTED_TICKER")
        self.tickers = ["EXB"]
        self.event["affected_tickers"][1]["relationship"] = "UNKNOWN"
        self.refused("UNSUPPORTED_OR_UNKNOWN_RELATION")
        self.event["affected_tickers"][1]["relationship"] = "DIRECT"
        self.event["affected_tickers"][1]["evidence_ids"] = [
            "fixture-claim-exa"]
        self.refused("TICKER_EVIDENCE_MISMATCH")

    def test_duplicate_and_invalid_tickers_blocked(self):
        self.tickers = ["EXA", "exa"]
        self.refused("DUPLICATE_TICKER")
        self.tickers = ["EXA", "EXB", "EXC", "EXD"]
        self.refused("TICKER_COUNT")
        self.tickers = ["EXA&source=evil"]
        self.refused("INVALID_TICKER")

    def test_candidate_does_not_imply_real_partner_and_ignores_email(self):
        self.partner["contact_email"] = "private-demo@example.invalid"
        p = self.make()
        self.assertIn("No partnership, endorsement, or approval", p["disclosure"])
        self.assertNotIn("private-demo@example.invalid", json.dumps(p))
        self.assertNotIn("private-demo@example.invalid", p["newsletter"])
        self.assertNotIn("private-demo@example.invalid", p["social"])

    def test_brand_approval_requires_explicit_permission_receipt(self):
        self.partner["status"] = "approved"
        self.refused("PARTNER_BRAND_PERMISSION_MISSING")
        self.partner["brand_permission_receipt"] = "agreement-001"
        self.partner["name"] = "Research Desk"
        p = self.make()
        self.assertIn("Partner distribution preview with Research Desk",
                      p["disclosure"])
        self.assertEqual(p["publication_status"], "DRAFT_HOLD")
        self.partner["status"] = "candidate"
        self.refused("CANDIDATE_MUST_NOT_CLAIM_PERMISSION")

    def test_stale_partner_profile_or_invalid_identity_fails(self):
        self.partner["profile_verified_at_utc"] = "2026-01-01T00:00:00Z"
        self.refused("STALE_PARTNER_PROFILE")
        self.partner = copy.deepcopy(DEMO_PROFILES[0][0])
        self.partner["slug"] = "../bad"
        self.refused("INVALID_PARTNER_SLUG")

    def test_source_urls_preserve_case_and_are_rendered_escaped(self):
        self.partner["name"] = 'Research <script>alert("x")</script> Profile'
        p = self.make()
        with tempfile.TemporaryDirectory() as temp:
            write_partner_pack(p, temp)
            page = (Path(temp) / "index.html").read_text()
            self.assertNotIn('<script>alert("x")</script>', page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("CaseSensitive/Exhibit", page)
            self.assertIn("CaseSensitive/Exhibit", p["newsletter"])
        self.event["sources"][0]["url"] = "javascript:alert(1)"
        self.refused("UNSAFE_SOURCE_URL")

    def test_corrections_are_visible_and_unanchored_generation_is_blocked(self):
        self.event["correction_generation"] = 2
        self.refused("MISSING_CORRECTION_HISTORY")
        self.event["corrections"] = [{
            "generation": 2, "replaces": "fixture-claim-exa",
            "reason": "Synthetic correction only",
        }]
        p = self.make()
        self.assertIn("revised generation", p["newsletter"])
        self.assertEqual(p["event"]["correction_generation"], 2)
        self.assertEqual(p["event"]["correction_count"], 1)
        self.assertNotIn("corrections", p["event"])
        # Upstream correction objects may contain non-public operator details.
        self.event["corrections"][0]["private_contact"] = "insider@example.net"
        rendered = self.make()
        self.assertNotIn("insider@example.net", json.dumps(rendered))

    def test_social_uses_selected_ticker_anchored_fact_not_generic_clickbait(self):
        self.tickers = ["EXA", "EXB"]
        p = self.make()
        self.assertIn("EXB supplier capacity assumption", p["social"])
        self.assertNotIn("EXC reports", p["social"])
        self.assertIn("Evidenced indirect relationship: EXB", p["newsletter"])
        self.assertIn("Direct event relationship: EXA", p["newsletter"])
        self.assertIn("Evidence fixture-claim-exb", p["newsletter"])
        self.assertEqual(len(p["social"].split("DRAFT THREAD 2/2")), 2)

    def test_social_refuses_truncated_or_overlong_evidence(self):
        # A source claim selected into the thread cannot be silently clipped.
        self.event["claims"][3]["text"] = "A " * 160
        self.refused("SOCIAL_CHARACTER_BUDGET")

    def test_ai_angle_selection_may_only_reorder_existing_evidence(self):
        self.tickers = ["EXA", "EXB"]
        p = self.make(angle_plan={
            "selected_claim_ids": ["fixture-claim-exb", "fixture-claim-exa"]
        })
        self.assertEqual([c["claim_id"] for c in p["claims"]],
                         ["fixture-claim-exb", "fixture-claim-exa"])
        self.refused("AI_UNGROUNDED_CLAIM_SELECTION",
                     angle_plan={"selected_claim_ids": ["model-invented-cause"]})
        self.refused("AI_DROPPED_TICKER_EVIDENCE",
                     angle_plan={"selected_claim_ids": ["fixture-claim-exa"]})

    def test_editorial_blocklist_rejects_promotional_advice_in_verified_claim(self):
        # Social-specific validator catches the actually selected lead claim.
        self.event["claims"][3]["text"] = "Guaranteed profits. Buy now."
        self.refused("SOCIAL_COPY_REJECTED")
        # Press validator also checks every other included claim, not just the
        # one selected for the short social message.
        self.event = copy.deepcopy(DEMO_EVENT)
        self.event["claims"][0]["text"] = "Guaranteed profits. Buy now."
        self.tickers = ["EXA", "EXB"]
        self.refused("EDITORIAL_COPY_REJECTED")

    def test_different_event_identity_and_generation_change_pack_id(self):
        initial = self.make()
        self.event["event_id"] = "synthetic-semis-brief-v2"
        changed = self.make()
        self.assertNotEqual(initial["pack_id"], changed["pack_id"])
        self.event["correction_generation"] = 1
        self.event["corrections"] = [{"generation": 1, "reason": "fixture"}]
        corrected = self.make()
        self.assertNotEqual(changed["pack_id"], corrected["pack_id"])

    def test_session05_research_only_profiles_preserve_triplets_and_refuse_fake_coverage(self):
        root = ROOT / "examples" / "catalyst_partner_previews" / "session05_candidate_profiles"
        expected = {
            "stockopine": ("MU", "AMD", "NVDA"),
            "potential_multibaggers": ("NVDA", "MSFT", "AMD"),
            "mbi_deep_dives": ("MSFT", "META", "NVDA"),
            "scuttleblurb": ("NVDA", "AVGO", "SNPS"),
            "the_canadian_investor": ("ORCL", "MSFT", "TSM"),
        }
        self.assertEqual({p.stem for p in root.glob("*.json")}, set(expected))
        for slug, tickers in expected.items():
            profile = json.loads((root / (slug + ".json")).read_text())
            self.assertEqual(tuple(profile["selected_tickers"]), tickers)
            self.assertEqual(profile["status"], "candidate")
            self.assertTrue(profile["research_only"])
            self.assertEqual(profile["publication_permission"], "NOT_GRANTED")
            self.assertIsNone(profile["brand_permission_receipt"])
            self.assertIn("8681", profile["research_ref"])
            self.assertEqual(profile["channel"],
                             "podcast" if slug == "the_canadian_investor" else "newsletter")
            with self.assertRaises(PackRejected) as ctx:
                build_partner_pack(self.event, profile, now_utc=DEMO_NOW)
            self.assertEqual(ctx.exception.code, "UNSUPPORTED_TICKER")
            self.assertNotIn("contact_email", profile)

    def test_public_text_and_source_urls_refuse_email_addresses(self):
        self.event["claims"][0]["text"] = "Contact insider@example.net about EXA."
        self.refused("EMPTY_CLAIM")
        self.event = copy.deepcopy(DEMO_EVENT)
        self.event["sources"][0]["url"] += "?ref=insider@example.net"
        self.refused("UNSAFE_SOURCE_URL")
        self.event = copy.deepcopy(DEMO_EVENT)
        self.partner["name"] = "Contact insider@example.net"
        self.refused("INVALID_PARTNER_NAME")

    def test_public_export_contains_only_allowlisted_claim_and_event_fields(self):
        self.event["claims"][0]["internal_source_excerpt"] = "PRIVATE_RESEARCH_TOKEN"
        self.event["claims"][0]["topics"] = ["PRIVATE_TOPIC_TOKEN"]
        self.event["private_raw_feed"] = "PRIVATE_FEED_TOKEN"
        p = self.make()
        serialized = json.dumps(p)
        self.assertNotIn("PRIVATE_RESEARCH_TOKEN", serialized)
        self.assertNotIn("PRIVATE_TOPIC_TOKEN", serialized)
        self.assertNotIn("PRIVATE_FEED_TOKEN", serialized)

    def test_no_real_outbound_or_publishing_capability(self):
        p = self.make()
        self.assertTrue(p["link_is_placeholder"])
        self.assertEqual(p["publication_status"], "DRAFT_HOLD")
        self.assertNotIn("sent_at", p)
        self.assertNotIn("published_at", p)


if __name__ == "__main__":
    unittest.main()
