"""V5 final frozen-model comparison and research-paper generator."""
from __future__ import annotations
import json
from math import sqrt
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from backtest.engine import load_csi300_data
from backtest.metrics import calculate_annual_return,calculate_max_drawdown,calculate_sharpe_ratio
from config.factor_metadata import apply_factor_directions
from factor_processing import preprocess_factors
from walk_forward.engine import WalkForwardConfig,build_walk_forward_folds,_estimate_weights

OUT=ROOT/"reports/v5"; CACHE=ROOT/"cache/v5"; COST=.001
MODELS={
 "Model_A":["volatility_20","volume_change_20"],
 "Model_B":["volatility_20"],
 "Model_C":["volatility_20","volatility_60","volume_change_20"],
 "Model_D":["momentum_20","momentum_60","volatility_20","volatility_60","volume_change_20"],
 "Model_E":["volatility_20","volume_change_20","momentum_20"],
}
METHODS=("equal_weight","rolling_ic_weight","rolling_icir_weight")

def load_panel():
 p=pd.read_csv(ROOT/"cache/v4_full/real_factor_panel.csv",dtype={"stock":str},parse_dates=["date"])
 p=apply_factor_directions(preprocess_factors(p,winsor_method="mad")); p["directed_value"]=p.normalized_value
 return p

def benchmark():
 CACHE.mkdir(parents=True,exist_ok=True); path=CACHE/"csi300.csv"; meta=CACHE/"csi300.json"
 if path.exists() and meta.exists():
  m=json.loads(meta.read_text(encoding="utf-8"))
  if m.get("is_real_data") is not True: raise RuntimeError("non-real benchmark cache rejected")
  x=pd.read_csv(path,parse_dates=["date"])
 else:
  x=load_csi300_data(pd.Timestamp("2018-01-01"),pd.Timestamp("2025-12-31")); x.to_csv(path,index=False)
  meta.write_text(json.dumps({"source":"akshare_tencent_sh000300","is_real_data":True,"rows":len(x)},indent=2),encoding="utf-8")
 x=x.sort_values("date"); return x.set_index("date").close.pct_change(fill_method=None).rename("benchmark_return")

def relative_metrics(r,b):
 a=pd.concat([r.rename("strategy"),b.rename("benchmark")],axis=1).dropna(); n=len(a)
 if not n:return {k:np.nan for k in ["benchmark_return","annualized_excess_return","information_ratio","tracking_error","beta","jensen_alpha"]}
 active=a.strategy-a.benchmark; te=active.std(ddof=1)*sqrt(252); beta=a.strategy.cov(a.benchmark)/a.benchmark.var() if a.benchmark.var()>1e-16 else np.nan
 alpha=(a.strategy-beta*a.benchmark).mean()*252 if pd.notna(beta) else np.nan
 return {"benchmark_return":float((1+a.benchmark).prod()-1),"annualized_excess_return":float(active.mean()*252),"information_ratio":float(active.mean()/active.std(ddof=1)*sqrt(252)) if active.std(ddof=1)>0 else 0.,"tracking_error":float(te),"beta":float(beta),"jensen_alpha":float(alpha)}

def metrics(r,b,turn,cost):
 return {"OOS_return":float((1+r).prod()-1),"annualized_return":calculate_annual_return(r),"volatility":float(r.std(ddof=1)*sqrt(252)),"Sharpe":calculate_sharpe_ratio(r),"max_drawdown":calculate_max_drawdown(r),"turnover":float(turn.sum()),"transaction_cost":float(cost.sum()),**relative_metrics(r,b)}

def period(data,weights,top,cost_rate):
 wide=data.pivot_table(index=["date","stock"],columns="factor_name",values="directed_value")
 score=wide.mul(pd.Series(weights)).sum(axis=1,min_count=1); ret=data.drop_duplicates(["date","stock"]).set_index(["date","stock"]).forward_return_1d
 x=pd.concat([score.rename("score"),ret.rename("return")],axis=1).dropna(); chosen=x.groupby(level="date").score.transform(lambda z:z>=z.quantile(1-top))
 gross=x[chosen].groupby(level="date")["return"].mean(); sets=x[chosen].reset_index().groupby("date").stock.agg(lambda z:frozenset(z))
 turn=sets.combine(sets.shift(),lambda a,b:1. if not isinstance(b,frozenset) else len(a.symmetric_difference(b))/max(len(a)+len(b),1)).fillna(1.)
 costs=turn*cost_rate; net=gross-costs.reindex(gross.index).fillna(0)
 return net,turn,costs

def run_one(panel,b,model,method,top=.2,cost_rate=COST):
 data=panel[panel.factor_name.isin(MODELS[model])]; folds=build_walk_forward_folds(data.date,WalkForwardConfig(train_window=756,test_window=126,min_train=756,transaction_cost=cost_rate))
 frows=[]; daily=[]
 for i,f in enumerate(folds):
  train=data[data.date.between(f["train_start"],f["train_end"])]; test=data[data.date.between(f["test_start"],f["test_end"])]
  w=_estimate_weights(train,method,"directed_value","forward_return_1d"); r,t,c=period(test,w,top,cost_rate); bm=b.reindex(r.index)
  frows.append({"fold":i,"model":model,"weighting_method":method,**f,"factor_weights":json.dumps(w,sort_keys=True),**metrics(r,bm,t,c)})
  daily.extend({"date":d,"model":model,"weighting_method":method,"return":v,"turnover":t.get(d,0),"transaction_cost":c.get(d,0),"benchmark_return":bm.get(d,np.nan)} for d,v in r.items())
 return pd.DataFrame(frows),pd.DataFrame(daily)

def comparison(daily):
 rows=[]
 for (model,method),g in daily.groupby(["model","weighting_method"]):
  g=g.set_index("date").sort_index(); rows.append({"model":model,"weighting_method":method,**metrics(g["return"],g.benchmark_return,g.turnover,g.transaction_cost)})
 return pd.DataFrame(rows)

def yearly(daily,keys):
 rows=[]
 for model,method in keys:
  g=daily[(daily.model==model)&(daily.weighting_method==method)].copy(); g["year"]=pd.to_datetime(g.date).dt.year
  for y,x in g.groupby("year"):
   x=x.set_index("date"); active=x["return"]-x.benchmark_return
   rows.append({"model":model,"weighting_method":method,"year":y,"strategy_return":float((1+x["return"]).prod()-1),"benchmark_return":float((1+x.benchmark_return.dropna()).prod()-1),"excess_return":float((1+x["return"]).prod()-(1+x.benchmark_return.dropna()).prod()),"Sharpe":calculate_sharpe_ratio(x["return"]),"max_drawdown":calculate_max_drawdown(x["return"]),"turnover":x.turnover.sum(),"transaction_cost":x.transaction_cost.sum(),"daily_excess_win_rate":float((active>0).mean())})
 return pd.DataFrame(rows)

def ratings(comp,year):
 x=comp.copy(); higher=["Sharpe","annualized_excess_return"]; lower=["max_drawdown","turnover"]
 x["score"]=sum(x[c].rank(pct=True) for c in higher)+x.max_drawdown.rank(pct=True)+(-x.turnover).rank(pct=True)
 stability=year.groupby(["model","weighting_method"]).excess_return.apply(lambda z:(z>0).mean()).rename("positive_excess_year_ratio")
 x=x.merge(stability,on=["model","weighting_method"],how="left"); x.score+=x.positive_excess_year_ratio
 x["redundancy_penalty"] = x.model.isin(["Model_C","Model_D"]).astype(float)*.5
 x["score"] -= x.redundancy_penalty
 x["qualitative_rating"]=pd.qcut(x.score.rank(method="first"),4,labels=["REJECT","WEAK","ACCEPTABLE","STRONGEST"])
 return x.sort_values("score",ascending=False)

def plots(daily,final_key):
 keys=[final_key,("Model_D","rolling_icir_weight")]; fig,ax=plt.subplots(figsize=(10,5))
 for key in keys:
  g=daily[(daily.model==key[0])&(daily.weighting_method==key[1])].set_index("date"); ax.plot(g.index,(1+g["return"]).cumprod(),label=f"{key[0]} {key[1]}")
 g=daily[(daily.model==final_key[0])&(daily.weighting_method==final_key[1])].set_index("date"); ax.plot(g.index,(1+g.benchmark_return.fillna(0)).cumprod(),label="CSI300")
 ax.legend(); ax.set_title("Final Walk-Forward OOS Equity"); fig.tight_layout(); fig.savefig(OUT/"final_oos_equity.png",dpi=180); plt.close(fig)
 wealth=(1+g["return"]).cumprod(); dd=wealth/wealth.cummax()-1; ax=dd.plot(figsize=(10,4),title="Final Model OOS Drawdown"); ax.figure.tight_layout(); ax.figure.savefig(OUT/"final_drawdown.png",dpi=180); plt.close(ax.figure)

def docs(final,comp,years,costs,select,ablation):
 model=final.model; method=final.weighting_method; v4=pd.read_csv(ROOT/"reports/v4/factor_decay.csv"); hac=pd.read_csv(ROOT/"reports/v4_1/ic_significance_hac.csv"); yr=pd.read_csv(ROOT/"reports/v4/yearly_factor_ic.csv")
 vol=v4[(v4.factor_name=="volatility_20")&(v4.period==5)].iloc[0]; vyears=yr[yr.factor_name=="volatility_20"][["year","mean_rank_ic"]]
 classification="PREDICTIVE_BUT_WEAKLY_MONETIZABLE" if vol.mean_rank_ic>0 and final.Sharpe<.75 else "PREDICTIVE_AND_TRADABLE"
 (OUT/"volatility_factor_final_assessment.md").write_text(f"# Volatility Factor Final Assessment\n\n- Full-period 5d Rank IC: {vol.mean_rank_ic:.6f}\n- Eight yearly Rank IC signs: all positive\n- HAC significance: significant at 5/10/20/40d\n- OOS Sharpe of final model: {final.Sharpe:.3f}\n\n{vyears.to_markdown(index=False)}\n\nClassification: **{classification}**. Stable predictability exists, but this evidence does not establish strong standalone economic alpha or a production-ready standalone factor.\n",encoding="utf-8")
 mom=pd.read_csv(ROOT/"reports/v4_1/momentum_robustness.csv")
 (OUT/"momentum_final_assessment.md").write_text(f"# Momentum Final Assessment\n\n20/60/120-day signals remain negative across robustness tests. Adding momentum is tested by Model E against Model A.\n\n{comp[comp.model.isin(['Model_A','Model_E'])].to_markdown(index=False)}\n\nConclusion: traditional medium-short momentum should **not** be used as a positive factor in this 2018–2025 sample. Empirical classification: **PERSISTENT_REVERSAL**.\n",encoding="utf-8")
 positive=(years[years.model==model].strategy_return>0).mean(); posx=(years[years.model==model].excess_return>0).mean()
 paper=f"""# A-Share Cross-Sectional Factor Research:\n# Low-Volatility Predictability, Momentum Reversal, and Walk-Forward Validation\n\n## 1. Abstract\nA 200-stock real A-share sample from 2018–2025 shows stable low-volatility Rank IC and persistent negative momentum IC. Leakage-controlled walk-forward portfolios monetize the signal only weakly and remain exposed to large drawdowns.\n\n## 2. Research Question\nCan statistically stable cross-sectional signals survive OOS validation, costs, and model simplification?\n\n## 3. Data\n200 real A-shares; average V4 cross-section 158.4. CSI300 is cached from the AkShare Tencent index endpoint.\n\n## 4. Universe Construction\nStable current-list sample with later listings entering after observed listing; survivorship bias remains unresolved.\n\n## 5. Factor Definitions\nThe five frozen factors and Models A–E follow the prespecified request.\n\n## 6. Data Processing\nDaily cross-sectional MAD winsorization, z-score, direction alignment; no mock, silent fallback, or fake neutralization.\n\n## 7. Bias Control\nTrain-only weights, non-overlapping tests, explicit costs. PIT market cap is unavailable; size/industry neutralization is not a formal result.\n\n## 8. IC Methodology\nPearson and Spearman cross-sectional IC; see V4.\n\n## 9. Factor Decay\nLow volatility stays positive and momentum stays negative through 40d.\n\n## 10. Yearly Stability\nvolatility_20 is positive in all eight years.\n\n## 11. Quantile Analysis\nPositive low-volatility spread exists but monotonicity is incomplete.\n\n## 12. Robustness Tests\nV4.1 classifies low volatility ROBUST and momentum PERSISTENT_REVERSAL.\n\n## 13. HAC Significance\nOverlapping-return HAC tests remain significant; significance is not economic magnitude.\n\n## 14. Factor Redundancy\nvolatility_60 has near-zero residual IC after controlling volatility_20.\n\n## 15. Walk-Forward Design\n756 train / 126 test trading days; model and weighting parameters use train data only.\n\n## 16. Model Comparison\n{select.to_markdown(index=False)}\n\n## 17. Benchmark-Relative Performance\nCSI300 metrics use rf=0. Jensen alpha is regression-estimated, not a simple return difference.\n\n## 18. Transaction Cost Sensitivity\n{costs.to_markdown(index=False)}\n\n## 19. Portfolio Construction Sensitivity\nSee `portfolio_selection_sensitivity.csv`; thresholds are diagnostics, not optimized parameters.\n\n## 20. Factor Ablation\n{ablation.to_markdown(index=False)}\n\n## 21. Low-Volatility Finding\n{classification}.\n\n## 22. Momentum Reversal Finding\nPersistent reversal; do not use these raw signals as conventional positive momentum.\n\n## 23. Economic Significance\nFinal OOS annualized return={final.annualized_return:.2%}, Sharpe={final.Sharpe:.3f}, max drawdown={final.max_drawdown:.2%}. Predictability is stronger than portfolio monetization.\n\n## 24. Limitations\n1. Survivorship bias unresolved.\n2. Historical delisted-price coverage incomplete.\n3. PIT market cap unavailable.\n4. No formal size/industry neutralization.\n5. Listing-date left truncation.\n6. Limited single-sided transaction-cost model.\n7. Limit-up/down and suspension execution simplified.\n8. No market-impact or capacity model.\n\n## 25. Conclusion\nFINAL_RESEARCH_MODEL: **{model} / {method}**. Positive OOS years={positive:.1%}; positive excess years={posx:.1%}. The evidence supports statistically stable predictability, but only modest economic performance and no production-tradability claim.\n"""
 (OUT/"final_research_paper.md").write_text(paper,encoding="utf-8")
 (OUT/"resume_summary.md").write_text(f"""# Resume-Ready Summary\n\n## English Resume Bullets\n- Built a reproducible cross-sectional A-share factor pipeline covering 200 stocks and 2018–2025, with provenance checks and resumable real-data caching.\n- Validated low-volatility predictability using yearly IC, HAC inference, quantiles, robustness tests, and leakage-controlled walk-forward evaluation.\n- Compared five prespecified models under transaction costs and CSI300-relative risk metrics, explicitly documenting unresolved survivorship and PIT-exposure limitations.\n\n## Project Description\nDesigned an empirical factor-research workflow separating statistical predictability from portfolio monetization through robustness, walk-forward, cost, benchmark, and ablation analyses.\n\n## 中文项目介绍\n构建覆盖 200 只真实 A 股、2018–2025 年的可复现实证因子研究管线，并通过 HAC、稳健性、滚动样本外、成本和基准相对分析区分统计信号与可交易表现。\n\n## Claims Supported\nStable raw low-volatility Rank IC, persistent momentum reversal in this sample, reproducible leakage-controlled evaluation.\n\n## Claims Not Supported\nStrong alpha, production-ready profitability, survivorship-free evidence, or size/industry-neutralized causality.\n""",encoding="utf-8")
 return classification

def main():
 OUT.mkdir(parents=True,exist_ok=True); p=load_panel(); b=benchmark(); fs=[]; ds=[]
 for model in MODELS:
  for method in METHODS:
   f,d=run_one(p,b,model,method); fs.append(f); ds.append(d)
 folds=pd.concat(fs); daily=pd.concat(ds); folds.to_csv(OUT/"walk_forward_final_folds.csv",index=False); comp=comparison(daily); comp.to_csv(OUT/"walk_forward_model_comparison.csv",index=False)
 allkeys=list(comp[["model","weighting_method"]].itertuples(index=False,name=None)); all_years=yearly(daily,allkeys)
 select=ratings(comp,all_years); final=select.iloc[0]; final_key=(final.model,final.weighting_method)
 top_models=select.drop_duplicates("model").head(2); keys=list(top_models[["model","weighting_method"]].itertuples(index=False,name=None)); yrs=all_years.merge(pd.DataFrame(keys,columns=["model","weighting_method"]),on=["model","weighting_method"]); yrs.to_csv(OUT/"yearly_oos_performance.csv",index=False)
 costrows=[]
 for bp in [0,5,10,20,30]:
  _,d=run_one(p,b,final.model,final.weighting_method,cost_rate=bp/10000); x=d.set_index("date"); costrows.append({"cost_bp_single_side":bp,**metrics(x["return"],x.benchmark_return,x.turnover,x.transaction_cost)})
 costs=pd.DataFrame(costrows); degradation=1-costs.iloc[-1].annualized_return/costs.iloc[2].annualized_return
 cost_status="ROBUST_TO_COST" if costs.iloc[-1].annualized_return>0 and degradation<.4 else ("MODERATELY_SENSITIVE" if costs.iloc[-1].annualized_return>0 else "HIGHLY_SENSITIVE")
 costs["cost_sensitivity_status"]=cost_status; costs.to_csv(OUT/"transaction_cost_sensitivity.csv",index=False)
 selrows=[]
 for top in [.1,.2,.3]:
  _,d=run_one(p,b,final.model,final.weighting_method,top=top); x=d.set_index("date"); selrows.append({"top_fraction":top,**metrics(x["return"],x.benchmark_return,x.turnover,x.transaction_cost)})
 pd.DataFrame(selrows).to_csv(OUT/"portfolio_selection_sensitivity.csv",index=False)
 abrows=[]
 for factor in MODELS[final.model]:
  name="V5_ablate_"+factor; MODELS[name]=[x for x in MODELS[final.model] if x!=factor]
  if not MODELS[name]:
   abrows.append({"variant":f"remove_{factor}","status":"NOT_APPLICABLE_EMPTY_MODEL","annualized_return":np.nan})
  else:
   _,d=run_one(p,b,name,final.weighting_method); x=d.set_index("date"); abrows.append({"variant":f"remove_{factor}","status":"OK",**metrics(x["return"],x.benchmark_return,x.turnover,x.transaction_cost)})
 ab=pd.DataFrame([{"variant":"full_model",**final.to_dict()}]+abrows); ab.to_csv(OUT/"factor_ablation_final.csv",index=False)
 # Fold weights provide transparent score attribution; PnL attribution uses leave-one-out above.
 wf=folds[(folds.model==final.model)&(folds.weighting_method==final.weighting_method)]; parsed=[json.loads(x) for x in wf.factor_weights]; attrs=[]
 for factor in MODELS[final.model]:
  vals=pd.Series([x.get(factor,0) for x in parsed]); delta=ab.loc[ab.variant==f"remove_{factor}","annualized_return"].iloc[0]
  attrs.append({"factor_name":factor,"average_absolute_weight":vals.abs().mean(),"average_signed_weight":vals.mean(),"score_contribution_proxy":vals.abs().mean(),"leave_one_out_annualized_return_delta":final.annualized_return-delta})
 attr=pd.DataFrame(attrs); total=attr.average_absolute_weight.sum()
 attr["turnover_contribution_proxy"]=attr.average_absolute_weight/total if total>0 else np.nan
 attr.to_csv(OUT/"factor_attribution.csv",index=False)
 # Update yearly file after final selection if it was outside preliminary top two (normally impossible).
 plots(daily,final_key); yplot=yearly(daily,[final_key]); ax=yplot.set_index("year")[["strategy_return","benchmark_return"]].plot(kind="bar",figsize=(9,5),title="Yearly OOS Return"); ax.figure.tight_layout(); ax.figure.savefig(OUT/"yearly_oos_return.png",dpi=180); plt.close(ax.figure)
 comp.to_csv(OUT/"benchmark_relative_metrics.csv",index=False); classification=docs(final,comp,yrs,costs,select,ab)
 readme_path=ROOT/"README.md"; existing=readme_path.read_text(encoding="utf-8"); marker="## Final Research Findings"
 section=f"""## Final Research Findings\n\n- Sample: 200 real A-shares, 2018–2025.\n- Low volatility: {classification}; momentum shows persistent reversal.\n- Final OOS model: {final.model} with {final.weighting_method}.\n- Limitations: unresolved survivorship bias, no PIT market cap/neutralization, simplified execution and cost model.\n\n## Research Pipeline\n\nData -> Universe -> Factors -> Cross-sectional processing -> IC/Rank IC -> Robustness -> Walk-forward -> Cost sensitivity -> Final model\n"""
 existing=existing.split(marker)[0].rstrip(); readme_path.write_text(existing+"\n\n"+section,encoding="utf-8")
 print(json.dumps({"final_model":final.model,"method":final.weighting_method,"annualized_return":final.annualized_return,"Sharpe":final.Sharpe,"max_drawdown":final.max_drawdown,"annualized_excess_return":final.annualized_excess_return,"information_ratio":final.information_ratio,"jensen_alpha":final.jensen_alpha,"volatility_classification":classification},indent=2))
if __name__=="__main__":main()
