"""Verify the native Prophet publication pair against its final refreshed source."""
from pathlib import Path
import argparse, hashlib, json, subprocess, sys
from bs4 import BeautifulSoup
cli=argparse.ArgumentParser()
cli.add_argument("--workspace",type=Path,required=True)
cli.add_argument("--source-head",required=True)
cli.add_argument("--output",type=Path,required=True)
a=cli.parse_args()
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=a.workspace,text=True).strip()==a.source_head
sys.path.insert(0,str(a.workspace))
from engine.us_candidate_lanes import project_candidate_visibility,load_candidate_archive_status
from scripts.build_site import _split_us_board,_us_board_group_items,_us_today_featured_preview
site=a.workspace/"site"
raw=(site/"factordata/us_standouts.json").read_bytes()
source=json.loads(raw)
view=project_candidate_visibility(source,archive=load_candidate_archive_status(source))
public_bytes=(site/"us_stocks.html").read_bytes()
private_bytes=(site/"premiumdata/us_stocks.json").read_bytes()
pub=BeautifulSoup(public_bytes,"html.parser")
payload=json.loads(private_bytes)
docs={key:BeautifulSoup(value,"html.parser") for key,value in payload.items() if key.endswith("_html") and isinstance(value,str)}
public_pool=[r["data-ticker"] for r in pub.select(".ucp-row")]
private_pool=[r["data-ticker"] for r in docs["candidate_pool_html"].select(".ucp-row")]
expected_pool=[r["ticker"] for r in view["rows"]]
positions={ticker:i for i,ticker in enumerate(expected_pool)}
public_positions=[positions[ticker] for ticker in public_pool]
private_positions=[positions[ticker] for ticker in private_pool]
shell,gate,locked=_split_us_board(source,payload["preview"],gated=True)
stage_any=any(row.get("stage") for row in source["buy"])
preview_items=_us_board_group_items(source["buy"][:payload["preview"]],stage_any,gate["stage_counts"])
locked_items=_us_board_group_items(locked,stage_any,gate["stage_counts"])
tickers=lambda rows:[r["ticker"] for r in rows if isinstance(r,dict) and r.get("ticker")]
card_tickers=lambda doc:[n.get("data-ticker") for n in doc.select("article.po-card")]
expected_today=tickers(_us_today_featured_preview(source,payload["today_preview"]))
targets={n["data-pvs-plan-target"] for doc in docs.values() for n in doc.select("[data-pvs-plan-target]")}
plan_ids={n["id"] for n in docs["plan_cards_html"].select("[id]")}|{n["id"] for n in pub.select("[id]")}
pool_digest=pub.select_one("#us-candidate-pool").get("data-source-digest")
checks={
 "pool_membership":set(public_pool+private_pool)==set(expected_pool),
 "pool_no_duplicates":len(set(public_pool+private_pool))==len(public_pool+private_pool),
 "pool_disjoint":not(set(public_pool)&set(private_pool)),
 "pool_public_subsequence":public_positions==sorted(public_positions),
 "pool_protected_subsequence":private_positions==sorted(private_positions),
 "pool_source_identity":pool_digest==payload["candidate_pool_source"]["digest"]==view["source_digest"],
 "screener_preview_order":card_tickers(docs["preview_cards_html"])==tickers(preview_items),
 "screener_protected_order":card_tickers(docs["cards_html"])==tickers(locked_items),
 "today_entitled_order":card_tickers(docs["today_cards_html"])==expected_today,
 "plan_targets_resolve":not(targets-plan_ids),
 "public_has_no_protected_plan_controls":len(pub.select("[data-pvs-plan-target]"))==0,
 "today_raw_source_binding":(payload.get("today_source_binding") or {}).get("source_sha256")=="sha256:"+hashlib.sha256(raw).hexdigest()
}
report={
 "source_head":a.source_head,"public_html_sha256":hashlib.sha256(public_bytes).hexdigest(),
 "essential_payload_sha256":hashlib.sha256(private_bytes).hexdigest(),
 "final_board_sha256":hashlib.sha256(raw).hexdigest(),"as_of":payload["as_of"],
 "screener":{"preview":len(card_tickers(docs["preview_cards_html"])),"protected":len(card_tickers(docs["cards_html"])),"total":payload["total"]},
 "today":{"public_articles":len(pub.select("#us-today-grid > article")),"entitled_preview":len(expected_today),"featured_total":payload["today_total"]},
 "eligible_pool":{"public":len(public_pool),"protected":len(private_pool),"total":len(expected_pool),"source_digest":view["source_digest"],"public_source_positions_zero_based":public_positions,
 "ordering_note":"Native withholding selects a public subsequence. Each partition preserves source order; concatenation is not the original raw order."},
 "protected_plan_targets":len(targets),"missing_plan_targets":sorted(targets-plan_ids),
 "checks":checks,"scope":"Native generated artifact and source proof; not authenticated browser, Paper or production acceptance."
}
a.output.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
assert all(checks.values()),{k:v for k,v in checks.items() if not v}
print("PUBLICATION_PAIR_VERIFIED",flush=True)
