"""ROR-1 retrospective issue-time replay: controls, never live notification.

All fixtures are synthetic. The source-native current Git ledger is tested only
after the pure algorithm passes these intentionally adversarial cases.
"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from audit_radar_issue_timeline import (
    ReplayInputError, read_ledger, as_recorded_at, as_recorded_matrix,
    recorded_alert_transitions, summarize_recorded_runs, weekday_cutoff_sweep,
)


def row(session, issued, *, state="caution", alert=False, score=71.5, market="cn", **fields):
    return dict(asof=session, logged_at=issued, market=market,
                state=state, alert=alert, top_score=score, graded=None, **fields)


class IssueTimelineTests(unittest.TestCase):
    def test_no_record_before_issuance_is_unknown_not_calm(self):
        rows = [row("2026-10-13", "2026-10-13T15:53:13Z",state="risk-off",alert=True)]
        x = as_recorded_at(rows, "cn", "2026-10-13T15:53:12+00:00")
        self.assertEqual(x["record_status"], "NO_RECORDED_ISSUE")
        self.assertIsNone(x["state"])
        self.assertNotIn("risk_verdict", x)
        y = as_recorded_at(rows, "cn", "2026-10-13T15:53:13+00:00")
        self.assertEqual(y["record_status"], "RECORDED_SOURCE_ISSUE")
        self.assertEqual(y["state"], "risk-off")
        self.assertEqual(y["source_session"], "2026-10-13")
        self.assertFalse(y["independent_expected_session_verified"])

    def test_the_us_older_session_does_not_become_oct13_forecast(self):
        logs = {
            "cn": [row("2026-10-12","2026-10-12T15:40:00Z",market="cn"),
                   row("2026-10-13","2026-10-13T15:53:13Z",market="cn",state="risk-off",alert=True,score=98)],
            "hk": [row("2026-10-12","2026-10-12T16:00:00Z",market="hk",state="watch"),
                   row("2026-10-13","2026-10-13T16:23:07Z",market="hk",state="elevated",alert=True,score=90)],
            "us": [row("2026-10-12","2026-10-13T06:38:33Z",market="us"),
                   row("2026-10-13","2026-10-14T06:02:59Z",market="us")],
        }
        x = as_recorded_matrix(logs,"2026-10-13T17:00:00Z")
        self.assertEqual([(k,x[k]["source_session"],x[k]["state"]) for k in ("cn","hk","us")],
                         [("cn","2026-10-13","risk-off"),("hk","2026-10-13","elevated"),("us","2026-10-12","caution")])
        self.assertFalse(any(v["customer_delivery_verified"] for v in x.values()))

    def test_cutoff_filter_prevents_hidden_late_revision(self):
        rows = [row("2026-10-12","2026-10-12T10:00:00Z",alert=False),
                row("2026-10-13","2026-10-15T10:00:00Z",alert=True,state="risk-off")]
        a = as_recorded_at(rows,"cn","2026-10-14T20:00:00Z")
        self.assertEqual(a["source_session"],"2026-10-12")
        self.assertFalse(a["model_alert"])
        b = as_recorded_at(rows,"cn","2026-10-15T11:00:00Z")
        self.assertEqual(b["source_session"],"2026-10-13")

    def test_market_local_day_rejects_not_yet_happened_session(self):
        rows=[row("2026-10-14","2026-10-13T15:00:00Z",state="elevated",alert=True,market="hk")]
        at = as_recorded_at(rows,"hk","2026-10-13T15:30:00Z")  # HK 23:30 on 13th
        self.assertEqual(at["record_status"],"NO_RECORDED_ISSUE")
        after = as_recorded_at(rows,"hk","2026-10-13T17:00:00Z")  # HK 01:00 on 14th
        self.assertEqual(after["source_session"],"2026-10-14")
        self.assertFalse(after["independent_expected_session_verified"])

    def test_preexisting_alert_true_stays_unknown_onset(self):
        a=[row("2026-10-13","2026-10-13T13:00:00Z",state="risk-off",alert=True)]
        result=recorded_alert_transitions(a,"cn")
        self.assertEqual(result[0]["observed_transition"],"LEFT_CENSORED_ACTIVE_BASELINE")
        self.assertFalse(result[0]["is_confirmed_natural_episode_onset"])

    def test_persistent_alert_is_not_everyday_new_onset(self):
        z=[row("2026-10-12","2026-10-12T11:00:00Z",state="watch"),
           row("2026-10-13","2026-10-13T11:00:00Z",state="elevated",alert=True),
           row("2026-10-14","2026-10-14T11:00:00Z",state="elevated",alert=True),
           row("2026-10-15","2026-10-15T11:00:00Z",state="risk-off",alert=True)]
        events=recorded_alert_transitions(z,"cn")
        self.assertEqual([e["observed_transition"] for e in events],
                         ["QUIET_BASELINE","ALERT_ONSET_IN_RECORDS","ALERT_CONTINUED","ALERT_SEVERITY_UPGRADE"])
        self.assertEqual(sum(e["observed_transition"]=="ALERT_ONSET_IN_RECORDS" for e in events),1)
        s=summarize_recorded_runs(z,"cn")
        self.assertEqual(s["runs"][0]["observed_rows"],3)
        self.assertEqual(s["runs"][0]["first_source_session"],"2026-10-13")
        self.assertEqual(s["runs"][0]["last_source_session"],"2026-10-15")
        self.assertEqual(s["runs"][0]["continuity"],"CONTIGUOUS_RECORDED_ROWS_NOT_TRADING_SESSIONS")
        self.assertFalse(s["runs"][0]["user_notification_claim"])

    def test_quiet_does_not_license_recovery_trade_or_publication(self):
        z=[row("2026-10-12","2026-10-12T11:00:00Z",state="risk-off",alert=True),
           row("2026-10-13","2026-10-13T11:00:00Z",state="caution",alert=False)]
        ev=recorded_alert_transitions(z,"cn")
        self.assertEqual(ev[-1]["observed_transition"],"MODEL_ALERT_CEASED_IN_RECORDS")
        self.assertFalse(ev[-1]["user_recovery_authorized"])
        self.assertFalse(ev[-1]["customer_delivery_verified"])

    def test_duplicate_market_future_nan_missing_issue_and_naive_issue_rejected(self):
        good=row("2026-10-13","2026-10-13T11:00:00Z")
        invalids=[
            [good,good],
            [row("2026-10-14","2026-10-14T11:00:00Z"),good],
            [row("2026-10-13","2026-10-13T11:00:00Z",market="hk")],
            [row("2026-10-13","2026-10-13T11:00:00Z",score=float("nan"))],
            [row("2026-10-13","2026-10-13T11:00:00")],
            [row("2026-13-99","2026-10-13T11:00:00Z")],
            [{**good,"alert":"true"}],
        ]
        for case in invalids:
            with self.subTest(case=str(case)[:100]), self.assertRaises(ReplayInputError):
                as_recorded_at(case,"cn","2026-10-13T17:00:00Z")

    def test_duplicate_json_keys_and_nonfinite_literals_are_closed(self):
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/"source.jsonl"
            f.write_text('{"asof":"2026-10-13","asof":"2026-10-13"}\n')
            with self.assertRaises(ReplayInputError):
                read_ledger(f,"cn")
            f.write_text('{"asof":"2026-10-13","top_score":NaN}\n')
            with self.assertRaises(ReplayInputError):
                read_ledger(f,"cn")

    def test_bad_cutoff_is_not_a_today_override(self):
        a=[row("2026-10-13","2026-10-13T11:00:00Z")]
        for value in ("2026-10-13","2026-10-13T11:00:00", "bad"):
            with self.subTest(value=value),self.assertRaises(ReplayInputError):
                as_recorded_at(a,"cn",value)

    def test_no_policy_or_alert_side_effects_in_results(self):
        z=[row("2026-10-13","2026-10-13T11:00:00Z",state="risk-off",alert=True)]
        result=as_recorded_at(z,"cn","2026-10-13T12:00:00Z")
        self.assertEqual(result["evidence_role"],"RETROSPECTIVE_ISSUE_TIME_CUTOFF_PROXY")
        self.assertNotIn("action",result)
        self.assertNotIn("trade",result)
        self.assertNotIn("probability",result)
        self.assertFalse(result["customer_delivery_verified"])
        self.assertFalse(result["forecast_efficacy_verified"])

    def test_exploratory_weekday_grid_does_not_invent_missing_market_flags(self):
        x={
            "cn": [row("2026-10-13","2026-10-13T15:53:13Z",market="cn",state="risk-off",alert=True)],
            "hk": [row("2026-10-13","2026-10-13T16:23:07Z",market="hk",state="elevated",alert=True)],
        }
        study=weekday_cutoff_sweep(x,"2026-10-12","2026-10-14",hour_utc=17,
                                   joint_markets=("cn","hk"))
        self.assertEqual(study["n_weekday_cutoffs"],3)
        self.assertEqual(study["n_joint_source_flags_true"],2)
        self.assertEqual(study["n_unknown_due_to_missing_issued_source"],1)
        self.assertEqual(study["snapshots"][0]["joint_status"],"UNAVAILABLE")
        self.assertEqual(study["snapshots"][1]["joint_status"],"ALL_MODEL_FLAGS_TRUE")
        self.assertFalse(study["forecast_precision_established"])
        self.assertFalse(study["customer_delivery_established"])

    def test_weekday_grid_is_issue_clock_not_old_source_cache_sla(self):
        x={
            "cn": [row("2026-10-09","2026-10-09T12:00:00Z",market="cn",state="risk-off",alert=True)],
            "hk": [row("2026-10-09","2026-10-09T13:00:00Z",market="hk",state="elevated",alert=True)],
        }
        report=weekday_cutoff_sweep(x,"2026-10-12","2026-10-13",hour_utc=17)
        self.assertEqual(report["n_joint_source_flags_true"],2)
        self.assertEqual(report["n_weekday_cutoffs"],2)
        self.assertTrue(all(
            x["source_session"]=="2026-10-09" for d in report["snapshots"]
            for x in d["selected_source_records"].values()
        ))
        self.assertTrue(all(not d["expected_exchange_sessions_verified"] for d in report["snapshots"]))

    def test_weekday_grid_range_and_profile_are_bounded(self):
        rows={"cn":[row("2026-10-13","2026-10-13T10:00:00Z")]}
        for a,b,h,j in [
            ("2026-10-14","2026-10-13",17,("cn",)),
            ("2026-01-01","2026-10-14",17,("cn",)),
            ("2026-10-13","2026-10-14",25,("cn",)),
            ("2026-10-13","2026-10-14",17,("xx",)),
            ("2026-10-13","2026-10-14",17,()),
        ]:
            with self.subTest(a=a,b=b,h=h,j=j),self.assertRaises(ReplayInputError):
                weekday_cutoff_sweep(rows,a,b,hour_utc=h,joint_markets=j)

    def test_cli_end_to_end_is_hash_bound_and_never_overwrites(self):
        import subprocess
        import hashlib
        def git_blob(data: bytes) -> str:
            return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            raw = (json.dumps(row("2026-10-13","2026-10-13T15:53:13Z",
                                  state="risk-off",alert=True)) + "\n").encode()
            src = root/"source_forward_cn_9b255a5.jsonl"
            src.write_bytes(raw)
            manifest = root/"sources.json"
            manifest.write_text(json.dumps({"cn": {"filename": src.name, "git_blob": git_blob(raw)}}))
            dst = root/"out.json"
            cmd = [sys.executable,str(pathlib.Path(__file__).with_name("audit_radar_issue_timeline.py")),
                   "--source-dir",str(root),"--expected-source-blobs",str(manifest),
                   "--output",str(dst),"--cutoff","2026-10-13T17:00:00Z",
                   "--weekday-grid-start","2026-10-13",
                   "--weekday-grid-end","2026-10-13",
                   "--weekday-grid-joint","cn"]
            first = subprocess.run(cmd, capture_output=True,text=True,timeout=6)
            self.assertEqual(first.returncode,0,first.stderr)
            report = json.loads(dst.read_text())
            self.assertFalse(report["actual_customer_delivery_proven"])
            self.assertEqual(report["exploratory_weekday_grid"]["n_joint_source_flags_true"],1)
            self.assertEqual(report["as_recorded_views"]["2026-10-13T17:00:00Z"]["cn"]["state"],"risk-off")
            result_bytes=dst.read_bytes()
            second=subprocess.run(cmd,capture_output=True,text=True,timeout=6)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual(dst.read_bytes(),result_bytes)
            self.assertIn("refusing to overwrite",second.stderr)
            dst.unlink()
            src.write_bytes(raw.replace(b"risk-off",b"elevated"))
            bad=subprocess.run(cmd,capture_output=True,text=True,timeout=6)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn("original Git source content differs",bad.stderr)
            self.assertFalse(dst.exists())

    def test_cli_rejects_source_filename_spoofing(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            manifest=root/"sources.json"
            manifest.write_text(json.dumps({"cn":{
                "filename":"../outside.jsonl","git_blob":"a"*40
            }}))
            run=subprocess.run([
                sys.executable,str(pathlib.Path(__file__).with_name("audit_radar_issue_timeline.py")),
                "--source-dir",str(root),"--expected-source-blobs",str(manifest),
                "--output",str(root/"out.json"),"--cutoff","2026-10-13T17:00:00Z"
            ],capture_output=True,text=True,timeout=6)
        self.assertNotEqual(run.returncode,0)
        self.assertIn("unrecognized or unsafe source identity",run.stderr)


if __name__ == "__main__":
    unittest.main()
