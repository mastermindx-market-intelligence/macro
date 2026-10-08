from __future__ import annotations
from dataclasses import dataclass
import unittest
from research.options_estate.ptse_candidate_relation import PTSECandidateRelationError, candidate_source_event_id, resolve_candidate_episode_relation
SOURCE="candidate:2026-10-02:AMD:us_prophet_v3"
EPISODE="pe:SEC:US-XNAS-AMD:epoch_0:sa:"+"a"*24+":1"
GEN="peg:"+"b"*64
@dataclass(frozen=True)
class Generation: episodes: tuple
@dataclass(frozen=True)
class Snapshot: generation_id:str; generation:Generation
def candidate(**changes):
    row={"stamp_date":"2026-10-02","ticker":"AMD","board_definition":"us_prophet_v3","score_rank":1,"prophet_score":72.0}; row.update(changes); return row
def episode(source_ids=(SOURCE,),**changes):
    row={"episode_id":EPISODE,"security_id":"SEC:US-XNAS-AMD","company_id":"ISS:US-XNAS-AMD","identity_epoch":"epoch_0","source_event_ids":list(source_ids)}; row.update(changes); return row
def snapshot(rows=None): return Snapshot(GEN,Generation(tuple(rows or (episode(),))))
class T(unittest.TestCase):
    def test_source(self): self.assertEqual(candidate_source_event_id(candidate()),SOURCE)
    def test_resolve(self):
        out=resolve_candidate_episode_relation(candidate(),snapshot(),expected_episode_id=EPISODE); self.assertEqual((out.source_event_id,out.candidate_generation_id,out.episode_id),(SOURCE,GEN,EPISODE))
    def test_noise(self): self.assertEqual(resolve_candidate_episode_relation(candidate(),snapshot()),resolve_candidate_episode_relation(candidate(score_rank=99,prophet_score=1.0),snapshot()))
    def test_no_ticker_fallback(self):
        with self.assertRaisesRegex(PTSECandidateRelationError,"CANDIDATE_B1_RELATION_UNAVAILABLE"): resolve_candidate_episode_relation(candidate(stamp_date="2026-10-03"),snapshot())
    def test_board_definition_bound(self):
        with self.assertRaisesRegex(PTSECandidateRelationError,"CANDIDATE_B1_RELATION_UNAVAILABLE"): resolve_candidate_episode_relation(candidate(board_definition="us_prophet_v2_fallback"),snapshot())
    def test_ambiguous(self):
        other=episode(episode_id="pe:SEC:US-XNAS-AMD:epoch_0:sa:"+"c"*24+":2")
        with self.assertRaisesRegex(PTSECandidateRelationError,"CANDIDATE_B1_RELATION_AMBIGUOUS"): resolve_candidate_episode_relation(candidate(),snapshot((episode(),other)))
    def test_expected_mismatch(self):
        with self.assertRaisesRegex(PTSECandidateRelationError,"CANDIDATE_PTSE_EPISODE_MISMATCH"): resolve_candidate_episode_relation(candidate(),snapshot(),expected_episode_id=EPISODE+"-other")
    def test_tuple_required(self):
        class G: episodes=[episode()]
        class S: generation_id=GEN; generation=G()
        with self.assertRaisesRegex(PTSECandidateRelationError,"B1_VALIDATED_EPISODES_REQUIRED"): resolve_candidate_episode_relation(candidate(),S())
    def test_bad_source_ids(self):
        bad = episode()
        bad["source_event_ids"] = SOURCE
        with self.assertRaisesRegex(PTSECandidateRelationError,"B1_SOURCE_EVENT_IDS_INVALID"):
            resolve_candidate_episode_relation(candidate(), snapshot((bad,)))
    def test_missing_identity(self):
        with self.assertRaisesRegex(PTSECandidateRelationError,"B1_COMPANY_ID_REQUIRED"): resolve_candidate_episode_relation(candidate(),snapshot((episode(company_id=None),)))
if __name__=='__main__': unittest.main()
