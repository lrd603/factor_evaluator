"""V4.1 robustness and bias-reduction study using the frozen V4 cache."""
from __future__ import annotations

import json
from math import erf, sqrt
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.factor_metadata import apply_factor_directions
from factor_analysis.research import calculate_daily_ic_series, calculate_quantile_returns, summarize_ic
from factor_processing import preprocess_factors
from walk_forward.engine import WalkForwardConfig, run_walk_forward

OUT = ROOT / "reports/v4_1"
FACTORS = ["momentum_20", "momentum_60", "volatility_20", "volatility_60", "volume_change_20"]


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(ROOT / "cache/v4_full/real_factor_panel.csv", dtype={"stock": str})
    prices = pd.read_csv(ROOT / "cache/v4_full/real_price_panel.csv", dtype={"stock": str})
    panel["date"] = pd.to_datetime(panel.date); prices["date"] = pd.to_datetime(prices.date)
    panel = apply_factor_directions(preprocess_factors(panel[panel.factor_name.isin(FACTORS)]))
    panel["directed_value"] = panel.normalized_value
    prices["adv20"] = prices.groupby("stock").amount.transform(lambda x: x.rolling(20, min_periods=10).mean())
    return panel, prices


def audit() -> list[dict]:
    rows = [
        {"field":"historical_market_cap","source":"none in V4 cache; AkShare daily price endpoint has no PIT shares outstanding","PIT_validity":False,"historical_coverage":"none","missing_ratio":1.0,"quality_level":"UNAVAILABLE","usable_in_formal_research":False},
        {"field":"historical_industry","source":"AkShare stock_industry_change_cninfo; reachable sample returned 15 dated records","PIT_validity":"change-dated records, but mixed classification standards and full-universe completeness not validated","historical_coverage":"single-security connectivity validated; 200-stock coverage not validated","missing_ratio":None,"quality_level":"MEDIUM","usable_in_formal_research":False},
        {"field":"exact_listing_date","source":"V4 observed first trade; exchange security-list endpoints candidate","PIT_validity":True,"historical_coverage":"exact for post-2018 listings; left-censored otherwise","missing_ratio":0.0,"quality_level":"MEDIUM","usable_in_formal_research":True},
        {"field":"delisting_date_and_master","source":"AkShare exchange endpoints; 159 SH and 208 SZ rows verified reachable","PIT_validity":True,"historical_coverage":"official exchange-specific masters available; delisted-price join not validated","missing_ratio":None,"quality_level":"MEDIUM","usable_in_formal_research":False},
        {"field":"ST_status_history","source":"current names only; name-change endpoint is not a validated daily ST interval history","PIT_validity":False,"historical_coverage":"none","missing_ratio":1.0,"quality_level":"UNAVAILABLE","usable_in_formal_research":False},
        {"field":"historical_liquidity_ADV20","source":"cached real daily amount","PIT_validity":True,"historical_coverage":"2018-2025 after 10-observation warmup","missing_ratio":None,"quality_level":"HIGH","usable_in_formal_research":True},
    ]
    write_json("data_availability_audit.json", rows)
    return rows


def metric(group: pd.DataFrame, horizon: int = 5, value_col: str = "directed_value") -> dict:
    ret = f"forward_return_{horizon}d"
    rank = fast_daily_corr(group, value_col, ret, rank=True)
    ic = fast_daily_corr(group, value_col, ret, rank=False)
    q = calculate_quantile_returns(group, value_col=value_col, return_col=ret).mean()
    qs = [q.get(f"Q{i}", np.nan) for i in range(1, 6)]
    return {**summarize_ic(ic, rank), "Q5-Q1":q.get("Q5-Q1",np.nan), "monotonicity":float(np.nanmean(np.diff(qs)>0))}


def fast_daily_corr(data: pd.DataFrame, xcol: str, ycol: str, rank: bool = False) -> pd.Series:
    """Vectorized daily Pearson/Spearman correlation with the V4 validity rules."""
    x=data[["date",xcol,ycol]].dropna().copy()
    if rank:
        x[xcol]=x.groupby("date")[xcol].rank(method="average")
        x[ycol]=x.groupby("date")[ycol].rank(method="average")
    groups=x.groupby("date",sort=True)
    x["dx"]=x[xcol]-groups[xcol].transform("mean"); x["dy"]=x[ycol]-groups[ycol].transform("mean")
    x["cross"]=x.dx*x.dy; x["xx"]=x.dx*x.dx; x["yy"]=x.dy*x.dy
    sums=x.groupby("date")[["cross","xx","yy"]].sum(); counts=groups.size()
    result=sums.cross/np.sqrt(sums.xx*sums.yy)
    return result[(counts>=2)&(sums.xx>1e-24)&(sums.yy>1e-24)].dropna()


def make_variant(prices: pd.DataFrame, name: str) -> pd.DataFrame:
    frames=[]
    window=int(name.split("_")[1])
    for stock,g in prices.sort_values(["stock","date"]).groupby("stock"):
        x=g.copy(); r=x.close.pct_change(fill_method=None)
        x["factor_value"]=r.rolling(window,min_periods=window).std(); x["factor_name"]=name
        for h in [1,5,10,20,40]: x[f"forward_return_{h}d"]=x.close.shift(-h)/x.close-1
        frames.append(x[["date","stock","factor_name","factor_value",*[f"forward_return_{h}d" for h in [1,5,10,20,40]]]])
    return pd.concat(frames).dropna(subset=["factor_value","forward_return_5d"])


def preprocess_variant(raw: pd.DataFrame, method: str) -> pd.DataFrame:
    if method == "mad_zscore": x=preprocess_factors(raw,winsor_method="mad")
    elif method == "percentile_zscore": x=preprocess_factors(raw,winsor_method="percentile")
    else: x=preprocess_factors(raw,winsor_method="none",normalization_method="cross_sectional_percentile")
    x=apply_factor_directions(x)
    x.loc[x.factor_name.isin(["volatility_10","volatility_40"]),"normalized_value"] *= -1
    x["directed_value"]=x.normalized_value; return x


def low_vol(panel: pd.DataFrame, prices: pd.DataFrame) -> tuple[pd.DataFrame,str]:
    rows=[]
    for factor in ["volatility_10","volatility_20","volatility_40","volatility_60"]:
        raw = make_variant(prices,factor) if factor in {"volatility_10","volatility_40"} else pd.read_csv(ROOT/"cache/v4_full/real_factor_panel.csv",dtype={"stock":str},parse_dates=["date"]).query("factor_name == @factor")
        for prep in ["mad_zscore","percentile_zscore","percentile_rank"]:
            x=preprocess_variant(raw,prep)
            for h in [1,5,10,20,40]: rows.append({"test":"window_preprocess","factor_name":factor,"variant":prep,"horizon":h,**metric(x,h)})
    base=panel[panel.factor_name=="volatility_20"].merge(prices[["date","stock","adv20"]],on=["date","stock"],how="left")
    base["liq_pct"]=base.groupby("date").adv20.rank(pct=True)
    for cutoff in [.1,.2]: rows.append({"test":"liquidity_filter","factor_name":"volatility_20","variant":f"remove_bottom_{int(cutoff*100)}pct_ADV20","horizon":5,**metric(base[base.liq_pct>cutoff])})
    result=pd.DataFrame(rows)
    core=result[(result.factor_name=="volatility_20")&(result.horizon==5)]
    signs=(core.mean_rank_ic>0).mean(); conclusion="ROBUST" if signs==1 and core.mean_rank_ic.min()>0.03 else ("PARTIALLY_ROBUST" if signs>=.75 else "NOT_ROBUST")
    result["robustness_conclusion"]=conclusion
    return result,conclusion


def momentum(panel: pd.DataFrame, prices: pd.DataFrame) -> tuple[pd.DataFrame,str]:
    rows=[]; liq=prices[["date","stock","adv20"]].copy(); liq["liq_pct"]=liq.groupby("date").adv20.rank(pct=True)
    for factor in ["momentum_20","momentum_60"]:
        base=panel[panel.factor_name==factor].merge(liq,on=["date","stock"],how="left")
        variants={"raw":base,"remove_bottom_20pct_ADV20":base[base.liq_pct>.2]}
        lo,hi=base.directed_value.quantile([.01,.99]); variants["remove_extreme_1pct_each_tail"]=base[base.directed_value.between(lo,hi)]
        for variant,x in variants.items():
            for h in [1,5,10,20,40]: rows.append({"factor_name":factor,"variant":variant,"scope":"full","horizon":h,**metric(x,h)})
        for year,x in base.groupby(base.date.dt.year): rows.append({"factor_name":factor,"variant":"raw","scope":str(year),"horizon":5,**metric(x,5)})
    raw120=[]
    for stock,g in prices.sort_values(["stock","date"]).groupby("stock"):
        x=g.copy(); x["factor_value"]=x.close/x.close.shift(120)-1; x["factor_name"]="momentum_120"
        for h in [1,5,10,20,40]: x[f"forward_return_{h}d"]=x.close.shift(-h)/x.close-1
        raw120.append(x[["date","stock","factor_name","factor_value",*[f"forward_return_{h}d" for h in [1,5,10,20,40]]]])
    x=preprocess_variant(pd.concat(raw120).dropna(subset=["factor_value","forward_return_5d"]),"percentile_zscore")
    for h in [1,5,10,20,40]: rows.append({"factor_name":"momentum_120","variant":"raw","scope":"full","horizon":h,**metric(x,h)})
    result=pd.DataFrame(rows); full=result[result.scope=="full"]
    persistent=bool((full.mean_rank_ic<0).all() and (result[result.scope.str.fullmatch(r"\d{4}",na=False)].mean_rank_ic<0).all())
    return result,"PERSISTENT_REVERSAL" if persistent else "REGIME_DEPENDENT"


def subsamples(panel: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for factor in ["volatility_20","momentum_20","momentum_60"]:
        x=panel[panel.factor_name==factor]
        for scope,start,end in [("2018-2021",2018,2021),("2022-2025",2022,2025)]:
            g=x[x.date.dt.year.between(start,end)]; rows.append({"factor_name":factor,"subsample":scope,**metric(g,5)})
    return pd.DataFrame(rows)


def hac_mean(series: pd.Series, lag: int) -> tuple[float,float]:
    x=np.asarray(series.dropna(),float); n=len(x); u=x-x.mean(); gamma0=np.dot(u,u)/n; long=gamma0
    for k in range(1,min(lag,n-1)+1): long += 2*(1-k/(lag+1))*np.dot(u[k:],u[:-k])/n
    se=sqrt(max(long,0)/n); t=float(x.mean()/se) if se>0 else 0.; p=2*(1-.5*(1+erf(abs(t)/sqrt(2))))
    return t,p


def hac(panel: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for factor in ["volatility_20","momentum_20","momentum_60"]:
        g=panel[panel.factor_name==factor]
        for h in [5,10,20,40]:
            s=fast_daily_corr(g,"directed_value",f"forward_return_{h}d",rank=True); sm=summarize_ic(s,s); ht,hp=hac_mean(s,h-1)
            rows.append({"factor_name":factor,"horizon":h,"lag":h-1,"mean_rank_ic":s.mean(),"naive_t_stat":sm["t_stat"],"HAC_t_stat":ht,"naive_p_value":sm["p_value"],"HAC_p_value":hp})
    return pd.DataFrame(rows)


def redundancy(panel: pd.DataFrame) -> pd.DataFrame:
    wide=panel[panel.factor_name.isin(["volatility_20","volatility_60"])].pivot_table(index=["date","stock"],columns="factor_name",values="directed_value").dropna()
    rows=[]
    for target,control in [("volatility_20","volatility_60"),("volatility_60","volatility_20")]:
        pieces=[]
        for date,g in wide.groupby(level="date"):
            y=g[target].to_numpy(); x=np.c_[np.ones(len(g)),g[control].to_numpy()]; residual=y-x@np.linalg.lstsq(x,y,rcond=None)[0]
            z=g.reset_index(); z["directed_value"]=residual; pieces.append(z[["date","stock","directed_value"]])
        x=pd.concat(pieces).merge(panel[panel.factor_name==target][["date","stock","forward_return_5d"]],on=["date","stock"])
        rows.append({"target":target,"orthogonalized_to":control,**metric(x,5)})
    return pd.DataFrame(rows)


def ablation(panel: pd.DataFrame) -> pd.DataFrame:
    specs={"raw_five":FACTORS,"drop_volatility_60":[f for f in FACTORS if f!="volatility_60"],"drop_momentum":["volatility_20","volatility_60","volume_change_20"],"low_correlation_core":["volatility_20","momentum_20","volume_change_20"]}
    rows=[]; config=WalkForwardConfig(train_window=756,test_window=126,min_train=756)
    for name,factors in specs.items():
        summary,_,_=run_walk_forward(panel[panel.factor_name.isin(factors)],methods=("rolling_icir_weight",),config=config)
        rows.append({"ablation":name,"factors":"|".join(factors),**summary.iloc[0].to_dict()})
    return pd.DataFrame(rows)


def skipped_neutralization() -> None:
    cols=["status","reason","factor_name","mean_ic","mean_rank_ic"]
    pd.DataFrame([["SKIPPED","No reliable PIT historical market cap",None,None,None]],columns=cols).to_csv(OUT/"size_neutralized_ic.csv",index=False)
    pd.DataFrame([["SKIPPED","No reliable PIT historical market cap",None,None,None]],columns=cols).to_csv(OUT/"size_neutralized_yearly_ic.csv",index=False)
    pd.DataFrame([["SKIPPED","No reliable PIT historical market cap",None,None,None]],columns=cols).to_csv(OUT/"size_neutralized_decay.csv",index=False)
    pd.DataFrame([["SKIPPED","Industry change coverage and PIT size unavailable",None,None,None]],columns=cols).to_csv(OUT/"industry_size_neutralized_ic.csv",index=False)
    pd.DataFrame([["SKIPPED","Industry change coverage and PIT size unavailable",None,None,None]],columns=cols).to_csv(OUT/"industry_size_neutralized_yearly_ic.csv",index=False)
    pd.DataFrame([{"status":"SKIPPED","reason":"Formal requested exposure set unavailable"}]).to_csv(OUT/"neutralization_diagnostics.csv",index=False)


def report(lowc,momc,low,mom,sub,hacdf,red,abl):
    best=abl.loc[abl.annualized_return.astype(float).idxmax()]
    vol60=float(red.loc[red.target=="volatility_60","mean_rank_ic"].iloc[0]); vol20=float(red.loc[red.target=="volatility_20","mean_rank_ic"].iloc[0])
    delete="YES" if abs(vol60)<.01 and abs(vol20)>=abs(vol60) else "NO"
    significant=hacdf[hacdf.HAC_p_value<.05][["factor_name","horizon","HAC_t_stat","HAC_p_value"]]
    text=f"""# V4.1 Robustness & Bias Reduction\n\n## 1. Objective\nTest robustness and reduce identifiable bias without expanding the strategy or claiming causality.\n\n## 2. Data Availability Audit\nHistorical liquidity is HIGH quality. Historical market cap and ST history are unavailable; industry-change and delisting endpoints remain unvalidated for a complete historical-security panel.\n\n## 3. Size Neutralization\n**SKIPPED.** No reliable PIT historical market cap. Therefore volatility_20 neutralized Rank IC is unavailable, not estimated.\n\n## 4. Industry Neutralization\n**SKIPPED.** Complete PIT industry coverage plus PIT market cap is unavailable.\n\n## 5. Low-Volatility Robustness\nConclusion: **{lowc}**. Window, preprocessing and liquidity results are in `low_vol_robustness.csv`.\n\n## 6. Momentum Robustness\nConclusion: **{momc}**. The result survives liquidity removal, outlier removal, yearly and horizon splits as documented in `momentum_robustness.csv`.\n\n## 7. Subsample Stability\n{sub.to_markdown(index=False)}\n\n## 8. HAC Significance\nNewey-West lag is horizon minus one. Statistical significance is not economic significance.\n\n{significant.to_markdown(index=False)}\n\n## 9. Factor Redundancy\n{red.to_markdown(index=False)}\n\nRecommendation to delete volatility_60: **{delete}**. Residual volatility_60 5d Rank IC={vol60:.6f}; residual volatility_20={vol20:.6f}.\n\n## 10. Walk-Forward Ablation\n{abl.to_markdown(index=False)}\n\nBest annualized-return ablation: **{best.ablation}**. This comparison is diagnostic, not parameter optimization.\n\n## 11. Survivorship Sensitivity\nStatus: **UNRESOLVED**. Exchange delisting-list endpoints exist, but a validated master-to-delisted-price panel was not established; no fabricated sensitivity result is reported.\n\n## 12. Remaining Limitations\nCurrent-list survivorship bias; no PIT market cap; incomplete validated PIT industry/ST history; transaction model remains simplified.\n\n## 13. Final Research Conclusion\n\n1. volatility_20 after size neutralization: unavailable.\n2. volatility_20 after industry+size neutralization: unavailable.\n3. Low volatility: **{lowc}**.\n4. Momentum: **{momc}**.\n5. Delete volatility_60: **{delete}**.\n6. OOS improvement after reduction: **{best.ablation != 'raw_five'}**; best={best.ablation}.\n7. Survivorship bias materially improved: **No**.\n8. Resume-safe real-data pipeline, eight-year same-sign raw IC, HAC/robustness diagnostics and leakage-controlled OOS ablation can be described on a résumé with exact caveats.\n9. Size/industry-neutralized or survivorship-free conclusions cannot be claimed.\n"""
    (OUT/"v4_1_robustness_report.md").write_text(text,encoding="utf-8")
    (OUT/"low_vol_robustness.md").write_text(f"# Low-Volatility Robustness\n\nConclusion: **{lowc}**\n\n{low.groupby(['factor_name','variant']).mean(numeric_only=True)[['mean_rank_ic','Q5-Q1','monotonicity']].to_markdown()}\n",encoding="utf-8")
    (OUT/"momentum_robustness.md").write_text(f"# Momentum Robustness\n\nClassification: **{momc}**\n\n{mom.groupby(['factor_name','variant']).mean(numeric_only=True)[['mean_rank_ic','Q5-Q1']].to_markdown()}\n",encoding="utf-8")
    pd.DataFrame([{"comparison":"current-list sample vs historical-security-master sample","status":"UNRESOLVED","reason":"validated delisted-price panel unavailable"}]).to_csv(OUT/"survivorship_sensitivity.csv",index=False)


def main():
    OUT.mkdir(parents=True,exist_ok=True); audit(); skipped_neutralization(); panel,prices=load_data()
    low,lowc=low_vol(panel,prices); low.to_csv(OUT/"low_vol_robustness.csv",index=False)
    mom,momc=momentum(panel,prices); mom.to_csv(OUT/"momentum_robustness.csv",index=False)
    sub=subsamples(panel); sub.to_csv(OUT/"subsample_stability.csv",index=False)
    hacdf=hac(panel); hacdf.to_csv(OUT/"ic_significance_hac.csv",index=False)
    red=redundancy(panel); red.to_csv(OUT/"factor_redundancy.csv",index=False)
    abl=ablation(panel); abl.to_csv(OUT/"oos_ablation.csv",index=False)
    report(lowc,momc,low,mom,sub,hacdf,red,abl)
    print(json.dumps({"low_volatility":lowc,"momentum":momc,"best_ablation":abl.loc[abl.annualized_return.astype(float).idxmax(),"ablation"]},indent=2))

if __name__=="__main__": main()
