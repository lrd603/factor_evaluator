"""Build a survivorship-aware sample, fetch delisted histories, and rerun frozen V5."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json
from pathlib import Path
import sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from config.factor_metadata import apply_factor_directions
from factor_analysis.research import calculate_daily_ic_series
from factor_engine.factor_builder import build_factor_data
from factor_processing import preprocess_factors
from scripts.run_real_research_pilot import fetch_real_price
import scripts.run_v5_final_research as v5

CACHE=ROOT/"cache/survivorship"; OUT=ROOT/"reports/v5"; START=pd.Timestamp("2018-01-01"); END=pd.Timestamp("2025-12-31"); SEED=20240911

def _hash(code):return hashlib.sha256(f"{SEED}:{code}".encode()).hexdigest()
def classify_survivorship(coverage,bse_master_available=False):
    if coverage>=.95 and bse_master_available:return "SURVIVORSHIP_BIAS_RESOLVED"
    if coverage>0:return "SURVIVORSHIP_BIAS_PARTIALLY_RESOLVED"
    return "SURVIVORSHIP_BIAS_UNRESOLVED"
def active_bounds(row):
    return max(START,pd.Timestamp(row.listing_date)),min(END,pd.Timestamp(row.delisting_date)-pd.Timedelta(days=1) if pd.notna(row.delisting_date) else END)
def cached(code,start,end):
    own=CACHE/"prices"/f"{code}.csv"
    candidates=[own,ROOT/"cache/v4_full/prices"/f"{code}.csv"]
    for p in candidates:
        if p.exists():
            x=pd.read_csv(p,dtype={"stock":str},parse_dates=["date"])
            if len(x)>=2 and x.date.min()<=start+pd.Timedelta(days=7) and x.date.max()>=end-pd.Timedelta(days=7):return x[x.date.between(start,end)],"cache"
    return None,None
def one(row):
    code=row.stock_code; start,end=active_bounds(row); x,action=cached(code,start,end)
    if x is None:
        x=fetch_real_price(code,str(start.date()),str(end.date()));x["date"]=pd.to_datetime(x.date);action="download"
        p=CACHE/"prices"/f"{code}.csv";p.parent.mkdir(parents=True,exist_ok=True);x.to_csv(p,index=False,encoding="utf-8-sig")
        p.with_suffix(".json").write_text(json.dumps({"stock":code,"source":x.attrs.get("source"),"is_real_data":True,"active_start":str(start.date()),"active_end":str(end.date())},indent=2),encoding="utf-8")
    if len(x)<30:raise ValueError(f"only {len(x)} rows")
    return code,x,action
def acquire(rows,label):
    ok={};fail={};actions={};rows=list(rows.itertuples(index=False))
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures={ex.submit(one,r):r.stock_code for r in rows}
        for i,f in enumerate(as_completed(futures),1):
            code=futures[f]
            try:c,x,a=f.result();ok[c]=x;actions[c]=a;print(f"[{label} {i}/{len(rows)}] {code} {a}",flush=True)
            except Exception as e:fail[code]=str(e);print(f"[{label} {i}/{len(rows)}] {code} failed: {e}",flush=True)
            (CACHE/f"{label}_progress.json").write_text(json.dumps({"success":len(ok),"failed":len(fail),"failures":fail},ensure_ascii=False,indent=2),encoding="utf-8")
    return ok,fail,actions
def build_panel(histories,master):
    prices=pd.concat(histories.values(),ignore_index=True).drop_duplicates(["date","stock"]).sort_values(["stock","date"])
    prices=prices[(prices.close>0)&(prices.volume>=0)];raw=build_factor_data(prices);raw.date=pd.to_datetime(raw.date)
    meta=master.set_index("stock_code");raw["listing_date"]=raw.stock.map(meta.listing_date);raw["delisting_date"]=raw.stock.map(meta.delisting_date)
    eligible=(raw.date>=raw.listing_date+pd.Timedelta(days=120))&(raw.delisting_date.isna()|(raw.date<raw.delisting_date));raw=raw[eligible]
    panel=apply_factor_directions(preprocess_factors(raw,winsor_method="mad"));panel["directed_value"]=panel.normalized_value
    prices.to_csv(CACHE/"survivorship_price_panel.csv",index=False);raw.to_csv(CACHE/"survivorship_factor_panel.csv",index=False)
    return panel,prices
def main():
    CACHE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    master=pd.read_csv(CACHE/"security_master.csv",dtype={"stock_code":str},parse_dates=["listing_date","delisting_date"])
    period=master[(master.listing_date<=END)&(master.delisting_date.isna()|(master.delisting_date>START))].copy();period["hash"]=period.stock_code.map(_hash);period=period.sort_values(["hash","stock_code"])
    delisted=period[period.delisting_date.between(START,END,inclusive="both")]
    del_ok,del_fail,_=acquire(delisted,"delisted")
    attempts=period.head(300);sample_ok,sample_fail,actions=acquire(attempts,"sample")
    selected_codes=[c for c in period.stock_code if c in sample_ok][:200];hist={c:sample_ok[c] for c in selected_codes};selected=period[period.stock_code.isin(selected_codes)].copy();selected.to_csv(CACHE/"selected_historical_sample.csv",index=False)
    if len(hist)<100:raise RuntimeError(f"only {len(hist)} sample histories")
    panel,prices=build_panel(hist,selected);b=v5.benchmark();fs=[];ds=[]
    for model in list(v5.MODELS)[:5]:
        for method in v5.METHODS:
            f,d=v5.run_one(panel,b,model,method);fs.append(f);ds.append(d)
    folds=pd.concat(fs);daily=pd.concat(ds);comp=v5.comparison(daily);allkeys=list(comp[["model","weighting_method"]].itertuples(index=False,name=None));years=v5.yearly(daily,allkeys)
    # The repair is a frozen-model sensitivity test, not a second model-selection exercise.
    final=comp[(comp.model=="Model_B")&(comp.weighting_method=="equal_weight")].iloc[0]
    vol=panel[panel.factor_name=="volatility_20"];ric=calculate_daily_ic_series(vol,"directed_value","forward_return_5d","spearman");year_ic=vol.groupby(vol.date.dt.year).apply(lambda x:calculate_daily_ic_series(x,"directed_value","forward_return_5d","spearman").mean())
    old=pd.read_csv(OUT/"walk_forward_model_comparison.csv");oldf=old[(old.model=="Model_B")&(old.weighting_method=="equal_weight")].iloc[0];oldic=pd.read_csv(ROOT/"reports/v4/factor_decay.csv").query("factor_name=='volatility_20' and period==5").iloc[0]
    newf=final;new_positive=int((years[(years.model==final.model)&(years.weighting_method==final.weighting_method)].strategy_return>0).sum());old_years=pd.read_csv(OUT/"yearly_oos_performance.csv");old_positive=int((old_years[(old_years.model=="Model_B")&(old_years.weighting_method=="equal_weight")].strategy_return>0).sum())
    rows=[{"version":"OLD_V5","scope":"full","Vol20_5d_Rank_IC":oldic.mean_rank_ic,"positive_OOS_years":old_positive,**{k:oldf[k] for k in ["annualized_return","Sharpe","max_drawdown","annualized_excess_return","information_ratio","jensen_alpha","turnover"]}},{"version":"SURVIVORSHIP_AWARE_V5","scope":"full","Vol20_5d_Rank_IC":ric.mean(),"positive_OOS_years":new_positive,**{k:newf[k] for k in ["annualized_return","Sharpe","max_drawdown","annualized_excess_return","information_ratio","jensen_alpha","turnover"]}}]
    for y,val in year_ic.items():rows.append({"version":"SURVIVORSHIP_AWARE_V5","scope":str(y),"Vol20_5d_Rank_IC":val})
    pd.DataFrame(rows).to_csv(OUT/"survivorship_bias_comparison.csv",index=False)
    coverage=len(del_ok)/len(delisted) if len(delisted) else 0;status=classify_survivorship(coverage,bse_master_available=False)
    sizes=panel.drop_duplicates(["date","stock"]).groupby(panel.date.dt.year).apply(lambda x:x.groupby("date").stock.nunique().mean())
    contributions={str(y):int(panel[(panel.date.dt.year==y)&panel.stock.isin(set(del_ok))].stock.nunique()) for y in range(2018,2026)}
    unavailable={code:f"DELISTED_HISTORY_UNAVAILABLE: {error}" for code,error in del_fail.items()};audit={"security_master_total":len(master),"security_master_exchange_coverage":["SSE","SZSE"],"missing_exchange_coverage":["BSE"],"existed_during_2018_2025":len(period),"currently_listed":int(master.delisting_date.isna().sum()),"delisted_during_period":len(delisted),"delisted_history_available":len(del_ok),"delisted_history_unavailable":len(del_fail),"delisted_historical_coverage_ratio":coverage,"yearly_average_universe_size":{str(k):v for k,v in sizes.items()},"yearly_delisted_contribution_count":contributions,"sample_rule":"SHA256(seed:stock_code) over all securities existing during 2018-2025; first 200 successful real histories from first 300 deterministic candidates","survivorship_status":status,"remaining_bias":status!="SURVIVORSHIP_BIAS_RESOLVED","missing_delisted_histories":unavailable,"forward_return_policy":"NaN when future price is unavailable; no forward fill"}
    (OUT/"survivorship_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    (OUT/"survivorship_audit.md").write_text(f"# Survivorship Audit\n\n- Master securities: {len(master)}\n- Existed during period: {len(period)}\n- Delisted during period: {len(delisted)}\n- Delisted histories available: {len(del_ok)}\n- Coverage: {coverage:.2%}\n- Status: **{status}**\n- Survivorship-aware sample stocks: {len(hist)}\n- New Vol20 5d Rank IC: {ric.mean():.6f}\n- Frozen V5 final: {final.model}/{final.weighting_method}, annualized={final.annualized_return:.2%}, Sharpe={final.Sharpe:.3f}, MDD={final.max_drawdown:.2%}\n\nNo prices were fabricated or forward-filled. Missing delisted histories remain explicitly audited.\n",encoding="utf-8")
    folds.to_csv(OUT/"survivorship_aware_walk_forward_folds.csv",index=False);comp.to_csv(OUT/"survivorship_aware_model_comparison.csv",index=False)
    print(json.dumps({"status":status,"coverage":coverage,"sample":len(hist),"vol20_rank_ic":ric.mean(),"final_model":final.model,"method":final.weighting_method,"annualized_return":final.annualized_return,"Sharpe":final.Sharpe,"max_drawdown":final.max_drawdown},indent=2))
if __name__=="__main__":main()
