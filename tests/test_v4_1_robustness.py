import pandas as pd
from scripts.run_v4_1_robustness import fast_daily_corr, hac_mean

def test_hac_mean_detects_stable_positive_series():
    t,p=hac_mean(pd.Series([.05,.04,.06,.05,.04,.06]*20),4)
    assert t>2 and p<.05

def test_fast_rank_correlation():
    x=pd.DataFrame({"date":["2020-01-01"]*3,"x":[1,2,3],"y":[3,2,1]})
    assert fast_daily_corr(x,"x","y",rank=True).iloc[0] == -1
