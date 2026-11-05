"""Check exact public Today binding, complete Plan partitions, and published lifecycle totals."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from bs4 import BeautifulSoup
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--workspace",type=Path,required=True)
p.add_argument("--source-head",required=True)
p.add_argument("--output",type=Path,required=True)
a=p.parse_args()
root=a.workspace.resolve()
assert not a.output.exists(),"Reconcile the existing evidence operation."
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()==a.source_head
sys.path.insert(0,str(root))
from scripts.build_site import _read_us_prophet_book
from scripts.build_stock_library import today_selection_source_binding
raw=(root/"site/factordata/us_standouts.json").read_bytes()
source=json.loads(raw)
binding=today_selection_source_binding(raw)
pubbytes=(root/"site/us_stocks.html").read_bytes()
payloadbytes=(root/"site/premiumdata/us_stocks.json").read_bytes()
pub=BeautifulSoup(pubbytes,"html.parser")
payload=json.loads(payloadbytes)
book,error=_read_us_prophet_book(root/"site/prophet/index.json")
assert book and not error
section=pub.select_one("#us-today")
checks={}
for field in ("source_sha256","pair_id","selection_receipt"):
    checks["public_today_"+field]=section.get("data-today-"+field.replace("_","-"))==binding[field]
checks["protected_today_full_binding"]=payload.get("today_source_binding")==binding
checks["public_roster_size"]=int(section["data-today-roster-size"])==len(binding["ordered_rows"])
cards=pub.select("#us-today-grid > article.po-card")
served=[item for item in section.get("data-today-served","").split(";") if item]
served_rows=[]
for item in served:
    index,receipt=item.split("~")
    index=int(index)
    assert 0<=index<len(binding["ordered_rows"])
    assert binding["ordered_rows"][index]=={"selection_index":index,"row_receipt":receipt}
    served_rows.append({"selection_index":index,"row_receipt":receipt,"ticker":source["buy"][index]["ticker"]})
checks["public_today_served_count"]=len(served_rows)==len(cards)==int(section["data-today-visible"])
checks["public_today_served_identity"]=[r["ticker"] for r in served_rows]==[n["data-ticker"] for n in cards]
checks["public_today_served_unique"]=len({r["selection_index"] for r in served_rows})==len(served_rows)
private=BeautifulSoup(payload["plan_cards_html"],"html.parser")
public_plans=[n["id"] for n in pub.select('article[data-record-only="1"]')]
private_plans=[n["id"] for n in private.select('article[data-record-only="1"]')]
expected=["pv-"+r["id"] for r in book["plans"]]
positions={value:i for i,value in enumerate(expected)}
actual=public_plans+private_plans
checks["plan_membership_complete"]=set(actual)==set(expected)
checks["plan_ids_unique"]=len(actual)==len(set(actual))==len(expected)
checks["plan_partitions_disjoint"]=not(set(public_plans)&set(private_plans))
checks["plan_public_order_preserved"]=[positions[x] for x in public_plans]==sorted(positions[x] for x in public_plans)
checks["plan_protected_order_preserved"]=[positions[x] for x in private_plans]==sorted(positions[x] for x in private_plans)
checks["main_published_air_plan_retained"]="pv-AIR-BULL-20261103" in actual
counts=book.get("lifecycle_counts") or {}
displayed={}
for cell in pub.select("#us-life-ladder [data-life]"):
    state=cell["data-life"]
    node=cell.select_one(".mx-cell-n")
    value=node.get_text(strip=True)
    absent=state=="watch" and "early_turn_watch" not in (book.get("intake") or {})
    expected_value="—" if absent else str(counts.get(state) or 0)
    displayed[state]=value
    checks["lifecycle_"+state+"_published_value"]=value==expected_value
headline=pub.select_one(".ladder-headline .ladder-n")
checks["lifecycle_headline_published_value"]=headline.get_text(strip=True)==str(book.get("lifecycle_live_total") or 0)
report={"source_head":a.source_head,"public_html_sha256":hashlib.sha256(pubbytes).hexdigest(),"protected_payload_sha256":hashlib.sha256(payloadbytes).hexdigest(),"checks":checks,"today":{"source_binding":binding,"public_served_rows":served_rows},"plans":{"book_rows":len(expected),"public":len(public_plans),"protected":len(private_plans),"published_order_sha256":hashlib.sha256(json.dumps(expected,separators=(",",":")).encode()).hexdigest(),"missing":sorted(set(expected)-set(actual)),"extra":sorted(set(actual)-set(expected))},"published_lifecycle_counts":counts,"displayed_lifecycle_counts":displayed,"published_lifecycle_live_total":book.get("lifecycle_live_total"),"scope":"Exact native public/protected artifact integrity; no authenticated or production acceptance."}
a.output.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"checks":checks,"plans":report["plans"],"lifecycle_counts":displayed,"today_public":len(served_rows)},indent=2),flush=True)
assert all(checks.values()),[k for k,v in checks.items() if not v]
print("INTEGRATION_PAIR_COMPLETE",flush=True)
