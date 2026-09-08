#!/usr/bin/env python3
# docs/win/hockey/nhl/scripts/05_final_scores/05_nhl_results_dashboard.py
#
# Builds a self-contained NHL results dashboard from Stage 05 reporting,
# calibration, and CLV outputs.
#
# Output: frontend/nhl_dashboard.html

from __future__ import annotations
from datetime import datetime, UTC
from pathlib import Path
import html, json, sys
import pandas as pd

BASE=Path("docs/win/hockey/nhl/05_final_scores")
REPORT_ROOT=BASE/"reports"
CALIBRATION_ROOT=REPORT_ROOT/"calibration"
CLV_ROOT=BASE/"clv"
OUTPUT=Path("frontend/nhl_dashboard.html")

MARKETS=[
 {"key":"moneyline","display":"Moneyline","folder":"moneyline","prefix":"nhl_moneyline","dimensions":["ev","kelly","odds","win_prob"]},
 {"key":"puck_line","display":"Puck Line","folder":"puckline","prefix":"nhl_puck_line","dimensions":["ev","kelly","odds","side","win_prob"]},
 {"key":"total","display":"Total","folder":"total","prefix":"nhl_total","dimensions":["ev","kelly","odds","side","total_range","win_prob"]},
]
CALIBRATION_FILES={
 "metrics":CALIBRATION_ROOT/"nhl_calibration_metrics.csv",
 "probability":CALIBRATION_ROOT/"nhl_probability_calibration.csv",
 "expected":CALIBRATION_ROOT/"nhl_expected_vs_realized.csv",
 "walk_forward":CALIBRATION_ROOT/"nhl_walk_forward_performance.csv",
}
CSS='\n:root{--bg:#0e1117;--panel:#161b22;--panel2:#1c232c;--text:#e6edf3;--muted:#8b949e;--good:#3fb950;--bad:#f85149;--border:#30363d}\n*{box-sizing:border-box}html,body{margin:0;padding:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}\nheader{padding:18px 24px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}\nheader h1{margin:0;font-size:20px}header .ts{font-size:12px;color:var(--muted)}main{max-width:1500px;margin:0 auto;padding:18px 24px}\nh2{font-size:16px;margin:24px 0 8px;border-bottom:1px solid var(--border);padding-bottom:4px}\n.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:10px;margin:12px 0}.kpi{background:var(--panel);border:1px solid var(--border);border-radius:6px;padding:12px}\n.kpi .label{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em}.kpi .value{font-size:22px;font-weight:600;margin-top:4px}\n.good{color:var(--good)}.bad{color:var(--bad)}.muted{color:var(--muted)}.tabs{display:flex;gap:4px;flex-wrap:wrap;margin:14px 0 0}\n.tab{background:var(--panel2);border:1px solid var(--border);color:var(--muted);padding:7px 12px;border-radius:6px 6px 0 0;cursor:pointer;font-size:13px}.tab.active{color:var(--text);border-bottom-color:var(--panel2)}\n.tab-body{background:var(--panel2);border:1px solid var(--border);border-top:none;padding:14px;border-radius:0 6px 6px 6px}\n.controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}.controls label{font-size:12px;color:var(--muted)}.controls select{background:var(--panel);border:1px solid var(--border);color:var(--text);padding:5px 8px;border-radius:4px}\n.scroll{overflow:auto;max-height:62vh;border:1px solid var(--border);border-radius:6px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:7px 8px;border-bottom:1px solid var(--border);white-space:nowrap}\nth{position:sticky;top:0;background:var(--panel2);color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.04em;text-align:left;cursor:pointer;user-select:none}td.num{text-align:right;font-variant-numeric:tabular-nums}\nfooter{padding:16px 24px;color:var(--muted);font-size:11px}.note{padding:10px 12px;border:1px solid var(--border);border-radius:6px;background:var(--panel);color:var(--muted);font-size:12px}\n'
JS='\nfunction fmtPct(v){if(v==null||isNaN(Number(v)))return "";return (Number(v)*100).toFixed(2)+"%";}\nfunction fmtNum(v,d=3){if(v==null||isNaN(Number(v)))return "";return Number(v).toFixed(d);}\nfunction fmtInt(v){if(v==null||isNaN(Number(v)))return "";return Number(v).toLocaleString();}\nfunction signedClass(v){if(v==null||isNaN(Number(v)))return "";return Number(v)>0?"good":(Number(v)<0?"bad":"");}\nfunction showTab(host,key){host.querySelectorAll(":scope > .tabs .tab").forEach(x=>x.classList.toggle("active",x.dataset.key===key));host.querySelectorAll(":scope > .tab-body > .tab-panel").forEach(x=>x.style.display=x.dataset.key===key?"":"none");}\nfunction renderTable(data,columns,container){\n if(!data||!data.length){container.innerHTML=\'<div class="muted">No rows available.</div>\';return;}\n const wrap=document.createElement("div");wrap.className="scroll";const table=document.createElement("table"),thead=document.createElement("thead"),tbody=document.createElement("tbody"),hr=document.createElement("tr");let sortKey=null,sortDir="desc";\n columns.forEach(c=>{const th=document.createElement("th");th.textContent=c.label;th.addEventListener("click",()=>{if(sortKey===c.key)sortDir=sortDir==="asc"?"desc":"asc";else{sortKey=c.key;sortDir="desc";}draw();});hr.appendChild(th);});thead.appendChild(hr);\n function draw(){const rows=data.slice();if(sortKey){rows.sort((a,b)=>{const av=a[sortKey],bv=b[sortKey];if(av==null)return 1;if(bv==null)return -1;const an=Number(av),bn=Number(bv);if(!Number.isNaN(an)&&!Number.isNaN(bn))return sortDir==="asc"?an-bn:bn-an;return sortDir==="asc"?String(av).localeCompare(String(bv)):String(bv).localeCompare(String(av));});}\n tbody.innerHTML="";rows.forEach(r=>{const tr=document.createElement("tr");columns.forEach(c=>{const td=document.createElement("td"),v=r[c.key];if(c.fmt==="int"){td.classList.add("num");td.textContent=fmtInt(v);}else if(c.fmt==="pct"){td.classList.add("num");td.textContent=fmtPct(v);}else if(c.fmt==="num"){td.classList.add("num");td.textContent=fmtNum(v,c.decimals==null?3:c.decimals);if(c.signed){const cls=signedClass(v);if(cls)td.classList.add(cls);}}else{td.textContent=v==null?"":String(v);}tr.appendChild(td);});tbody.appendChild(tr);});}\n draw();table.appendChild(thead);table.appendChild(tbody);wrap.appendChild(table);container.innerHTML="";container.appendChild(wrap);\n}\n'
HTML_TEMPLATE='<!doctype html>\n<html lang="en">\n<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NHL Dashboard</title><link rel="stylesheet" href="assets/css/matstheme.css"><style>__CSS_HTML__</style></head>\n<body>\n<div id="nav-placeholder"></div>\n<header><h1>NHL Dashboard</h1><span class="ts">Built __GENERATED__ UTC</span></header>\n<main>\n<h2>Headline KPIs</h2><div class="kpis" id="headline"></div>\n<h2>By Market</h2><div id="by-market"></div>\n\n<h2>Model Calibration</h2>\n<div id="calibration">\n  <div class="tabs">\n    <button class="tab active" data-key="metrics">Metrics</button>\n    <button class="tab" data-key="probability">Probability Buckets</button>\n    <button class="tab" data-key="expected">Expected vs Realized</button>\n    <button class="tab" data-key="walk_forward">Walk Forward</button>\n  </div>\n  <div class="tab-body">\n    <div class="tab-panel" data-key="metrics"></div>\n    <div class="tab-panel" data-key="probability" style="display:none"></div>\n    <div class="tab-panel" data-key="expected" style="display:none"></div>\n    <div class="tab-panel" data-key="walk_forward" style="display:none"></div>\n  </div>\n</div>\n\n<h2>Closing Line Value</h2>\n<div class="note">Positive implied-probability CLV and positive decimal-ratio CLV mean the selected price beat the close, matching the NHL pipeline\'s CLV definitions.</div>\n<div class="kpis" id="clv-headline"></div>\n<div id="clv-table"></div>\n\n<h2>Per Market Drilldown</h2>\n<div id="markets"><div class="tabs">__MARKET_TABS__</div><div class="tab-body">__MARKET_PANELS__</div></div>\n</main>\n<footer>Built from Stage 05 CSVs in <code>docs/win/hockey/nhl/05_final_scores</code>.</footer>\n\n<script src="assets/js/shared/nav.js"></script>\n<script>\n__JS_HTML__\nconst DATA=__DATA__;\nconst RESULT_COLUMNS=[\n{key:"variable",label:"Bucket"},{key:"side_group",label:"Side"},{key:"Win",label:"W",fmt:"int"},{key:"Loss",label:"L",fmt:"int"},{key:"Push",label:"P",fmt:"int"},{key:"Total",label:"Total",fmt:"int"},\n{key:"Win_Pct",label:"Win %",fmt:"pct"},{key:"units",label:"Units",fmt:"num",decimals:3,signed:true},{key:"roi",label:"ROI",fmt:"pct"},{key:"avg_odds",label:"Avg Odds",fmt:"num",decimals:1},\n{key:"avg_ev",label:"Avg EV",fmt:"pct"},{key:"avg_kelly",label:"Avg Kelly",fmt:"pct"},{key:"avg_win_prob",label:"Avg Win Prob",fmt:"pct"}];\nconst TALLY_COLUMNS=[\n{key:"market_type",label:"Market"},{key:"Win",label:"W",fmt:"int"},{key:"Loss",label:"L",fmt:"int"},{key:"Push",label:"P",fmt:"int"},{key:"Total",label:"Total",fmt:"int"},\n{key:"Win_Pct",label:"Win %",fmt:"pct"},{key:"units",label:"Units",fmt:"num",decimals:3,signed:true},{key:"roi",label:"ROI",fmt:"pct"},{key:"avg_odds",label:"Avg Odds",fmt:"num",decimals:1},\n{key:"avg_ev",label:"Avg EV",fmt:"pct"},{key:"avg_kelly",label:"Avg Kelly",fmt:"pct"},{key:"avg_win_prob",label:"Avg Win Prob",fmt:"pct"}];\nconst CAL_METRICS=[\n{key:"market_type",label:"Market"},{key:"bets",label:"Bets",fmt:"int"},{key:"expected_win_rate",label:"Expected",fmt:"pct"},{key:"realized_win_rate",label:"Realized",fmt:"pct"},\n{key:"calibration_gap",label:"Gap",fmt:"num",decimals:4,signed:true},{key:"brier_score",label:"Brier",fmt:"num",decimals:4},{key:"log_loss",label:"Log Loss",fmt:"num",decimals:4},\n{key:"expected_wins",label:"Expected Wins",fmt:"num",decimals:2},{key:"realized_wins",label:"Realized Wins",fmt:"num",decimals:0}];\nconst CAL_PROB=[\n{key:"market_type",label:"Market"},{key:"probability_bucket",label:"Bucket"},{key:"bets",label:"Bets",fmt:"int"},{key:"avg_model_prob",label:"Avg Model",fmt:"pct"},\n{key:"realized_win_rate",label:"Realized",fmt:"pct"},{key:"calibration_gap",label:"Gap",fmt:"num",decimals:4,signed:true},{key:"brier_score",label:"Brier",fmt:"num",decimals:4},{key:"log_loss",label:"Log Loss",fmt:"num",decimals:4}];\nconst CAL_EXPECTED=[\n{key:"market_type",label:"Market"},{key:"bets",label:"Bets",fmt:"int"},{key:"expected_probability",label:"Expected",fmt:"pct"},{key:"realized_probability",label:"Realized",fmt:"pct"},\n{key:"difference",label:"Difference",fmt:"num",decimals:4,signed:true},{key:"expected_wins",label:"Expected Wins",fmt:"num",decimals:2},{key:"realized_wins",label:"Realized Wins",fmt:"num",decimals:0}];\nconst WALK=[\n{key:"market_type",label:"Market"},{key:"through_game_date",label:"Through Date"},{key:"Win",label:"W",fmt:"int"},{key:"Loss",label:"L",fmt:"int"},{key:"Push",label:"P",fmt:"int"},\n{key:"bets_including_pushes",label:"Bets",fmt:"int"},{key:"win_pct",label:"Win %",fmt:"pct"},{key:"units",label:"Units",fmt:"num",decimals:3,signed:true},{key:"roi",label:"ROI",fmt:"pct"},\n{key:"calibration_gap",label:"Cal Gap",fmt:"num",decimals:4,signed:true},{key:"brier_score",label:"Brier",fmt:"num",decimals:4},{key:"log_loss",label:"Log Loss",fmt:"num",decimals:4}];\nconst CLV_COLUMNS=[\n{key:"game_date",label:"Date"},{key:"away_team",label:"Away"},{key:"home_team",label:"Home"},{key:"market_type",label:"Market"},{key:"bet_side",label:"Side"},\n{key:"selected_provider_name",label:"Selected Book"},{key:"dk_odds_american",label:"Selected Odds"},{key:"closing_provider_name",label:"Closing Book"},{key:"closing_odds_american",label:"Closing Odds"},\n{key:"clv_implied_probability",label:"Implied CLV",fmt:"num",decimals:4,signed:true},{key:"clv_decimal_ratio",label:"Decimal CLV",fmt:"num",decimals:4,signed:true},\n{key:"line_clv",label:"Line CLV",fmt:"num",decimals:3,signed:true},{key:"clv_status",label:"Status"}];\n\nfunction kpi(label,value,fmt){let text="—";if(value!=null&&!Number.isNaN(Number(value))){if(fmt==="pct")text=fmtPct(value);else if(fmt==="int")text=fmtInt(value);else if(fmt==="num")text=fmtNum(value,3);else if(fmt==="odds")text=fmtNum(value,1);}return \'<div class="kpi"><div class="label">\'+label+\'</div><div class="value">\'+text+\'</div></div>\';}\n\nfunction buildMarketPanel(market,panel){\n const dims=Object.keys(market.by||{}).filter(d=>((market.by[d]||[]).length||(market.by_side[d]||[]).length));\n if(!dims.length){panel.innerHTML=\'<div class="muted">No report rows available.</div>\';return;}\n panel.innerHTML=\'<div class="controls"><label>Dimension: <select class="dim">\'+dims.map(d=>\'<option value="\'+d+\'">\'+d+\'</option>\').join("")+\'</select></label><label>View: <select class="view"><option value="overall">Overall</option><option value="side">Split home/away</option></select></label></div><div class="tablehost"></div>\';\n const dim=panel.querySelector(".dim"),view=panel.querySelector(".view"),host=panel.querySelector(".tablehost");\n function refresh(){const d=dim.value;const rows=view.value==="side"?((market.by_side||{})[d]||[]):((market.by||{})[d]||[]);renderTable(rows,RESULT_COLUMNS,host);}\n dim.addEventListener("change",refresh);view.addEventListener("change",refresh);refresh();\n}\n\ndocument.addEventListener("DOMContentLoaded",()=>{\n const h=DATA.headline||{};\n document.getElementById("headline").innerHTML=[kpi("Bets",h.bets,"int"),kpi("Wins",h.wins,"int"),kpi("Losses",h.losses,"int"),kpi("Pushes",h.pushes,"int"),kpi("Win %",h.win_pct,"pct"),kpi("Units",h.units,"num"),kpi("ROI",h.roi,"pct"),kpi("Avg Odds",h.avg_odds,"odds"),kpi("Avg EV",h.avg_ev,"pct"),kpi("Avg Kelly",h.avg_kelly,"pct"),kpi("Avg Win Prob",h.avg_win_prob,"pct")].join("");\n renderTable(DATA.tally||[],TALLY_COLUMNS,document.getElementById("by-market"));\n\n const cal=document.getElementById("calibration");const calCols={metrics:CAL_METRICS,probability:CAL_PROB,expected:CAL_EXPECTED,walk_forward:WALK};\n Object.entries(DATA.calibration||{}).forEach(([key,rows])=>{const panel=cal.querySelector(\'.tab-panel[data-key="\'+key+\'"]\');if(panel)renderTable(rows||[],calCols[key]||[],panel);});\n cal.querySelectorAll(":scope > .tabs .tab").forEach(tab=>tab.addEventListener("click",()=>showTab(cal,tab.dataset.key)));\n\n const ch=(DATA.clv||{}).headline||{};\n document.getElementById("clv-headline").innerHTML=[kpi("Selections",ch.selections,"int"),kpi("Comparable",ch.comparable,"int"),kpi("Positive CLV",ch.positive,"int"),kpi("Positive CLV %",ch.positive_pct,"pct"),kpi("Avg Implied CLV",ch.avg_implied_clv,"pct"),kpi("Avg Decimal CLV",ch.avg_decimal_ratio,"pct")].join("");\n renderTable((DATA.clv||{}).rows||[],CLV_COLUMNS,document.getElementById("clv-table"));\n\n const markets=document.getElementById("markets");\n Object.entries(DATA.markets||{}).forEach(([key,market])=>{const panel=markets.querySelector(\'.market-panel-\'+key);if(panel)buildMarketPanel(market,panel);});\n markets.querySelectorAll(":scope > .tabs .tab").forEach(tab=>tab.addEventListener("click",()=>showTab(markets,tab.dataset.key)));\n});\n</script>\n</body></html>'

def read_csv(path:Path,required:bool=False)->pd.DataFrame:
    if not path.exists():
        print(f"{'ERROR' if required else 'WARNING'}: missing {path}",file=sys.stderr)
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        print(f"WARNING: unable to read {path}: {type(exc).__name__}: {exc}",file=sys.stderr)
        return pd.DataFrame()

def clean_value(value):
    if value is None:return None
    try:
        if pd.isna(value):return None
    except Exception:pass
    if hasattr(value,"item"):
        try:return value.item()
        except Exception:pass
    return value

def records(df):
    if df.empty:return []
    return [{k:clean_value(v) for k,v in row.items()} for row in df.to_dict(orient="records")]

def num(series):
    return pd.to_numeric(series,errors="coerce")

def weighted_mean(df,value_col,weight_col="Total"):
    if df.empty or value_col not in df.columns or weight_col not in df.columns:return None
    values=num(df[value_col]);weights=num(df[weight_col]);mask=values.notna()&weights.notna()&(weights>0)
    if not mask.any():return None
    return clean_value((values[mask]*weights[mask]).sum()/weights[mask].sum())

def build_headline(tally):
    if tally.empty:return {}
    for col in ["Win","Loss","Push","Total","units"]:
        if col in tally.columns:tally[col]=num(tally[col])
    wins=int(tally["Win"].sum()) if "Win" in tally.columns else 0
    losses=int(tally["Loss"].sum()) if "Loss" in tally.columns else 0
    pushes=int(tally["Push"].sum()) if "Push" in tally.columns else 0
    total=int(tally["Total"].sum()) if "Total" in tally.columns else wins+losses+pushes
    units=clean_value(tally["units"].sum(min_count=1)) if "units" in tally.columns else None
    return {
      "bets":total,"wins":wins,"losses":losses,"pushes":pushes,
      "win_pct":wins/(wins+losses) if wins+losses else None,
      "units":units,"roi":float(units)/total if units is not None and total else None,
      "avg_odds":weighted_mean(tally,"avg_odds"),"avg_ev":weighted_mean(tally,"avg_ev"),
      "avg_kelly":weighted_mean(tally,"avg_kelly"),"avg_win_prob":weighted_mean(tally,"avg_win_prob")
    }

def load_markets():
    out={}
    for spec in MARKETS:
        base=REPORT_ROOT/spec["folder"];market={"display":spec["display"],"by":{},"by_side":{}}
        for dim in spec["dimensions"]:
            root=f"{spec['prefix']}_by_{dim}"
            market["by"][dim]=records(read_csv(base/f"{root}.csv"))
            market["by_side"][dim]=records(read_csv(base/f"{root}_home_away_summary.csv"))
        out[spec["key"]]=market
    return out

def truthy(value):
    return str(value).strip().lower() in {"1","true","yes","y"}

def build_clv():
    df=read_csv(CLV_ROOT/"NHL_clv.csv")
    if df.empty:return {"headline":{},"rows":[]}
    comparable=df["price_comparable"].map(truthy) if "price_comparable" in df.columns else pd.Series(False,index=df.index)
    implied=num(df["clv_implied_probability"]) if "clv_implied_probability" in df.columns else pd.Series(float("nan"),index=df.index)
    decimal=num(df["clv_decimal_ratio"]) if "clv_decimal_ratio" in df.columns else pd.Series(float("nan"),index=df.index)
    valid=comparable&implied.notna();positive=valid&(implied>0);decimal_valid=comparable&decimal.notna()
    return {"headline":{
      "selections":len(df),"comparable":int(valid.sum()),"positive":int(positive.sum()),
      "positive_pct":float(positive.sum())/float(valid.sum()) if valid.any() else None,
      "avg_implied_clv":clean_value(implied[valid].mean()) if valid.any() else None,
      "avg_decimal_ratio":clean_value(decimal[decimal_valid].mean()) if decimal_valid.any() else None,
    },"rows":records(df)}

def build_payload():
    tally=read_csv(BASE/"nhl_market_tally.csv",True)
    calibration={key:records(read_csv(path)) for key,path in CALIBRATION_FILES.items()}
    return {"headline":build_headline(tally.copy()),"tally":records(tally),"markets":load_markets(),"calibration":calibration,"clv":build_clv()}

def build_html(payload):
    tabs="\n".join(
      '<button class="tab{}" data-key="{}">{}</button>'.format(" active" if i==0 else "",m["key"],html.escape(m["display"]))
      for i,m in enumerate(MARKETS))
    panels="\n".join(
      '<div class="tab-panel market-panel-{}" data-key="{}"{}></div>'.format(m["key"],m["key"],' style="display:none"' if i else "")
      for i,m in enumerate(MARKETS))
    data=json.dumps(payload,ensure_ascii=False,allow_nan=False).replace("</","<\\/")
    return (HTML_TEMPLATE
      .replace("__CSS_HTML__",CSS).replace("__JS_HTML__",JS)
      .replace("__GENERATED__",html.escape(datetime.now(UTC).isoformat(timespec="seconds")))
      .replace("__MARKET_TABS__",tabs).replace("__MARKET_PANELS__",panels).replace("__DATA__",data))

def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(build_html(build_payload()),encoding="utf-8")
    print(f"NHL dashboard generated: {OUTPUT}")

if __name__=="__main__":
    main()
