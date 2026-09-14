import pandas as pd
from scripts.run_v5_final_research import relative_metrics

def test_jensen_alpha_is_regression_intercept_not_return_difference():
 b=pd.Series([.01,-.01,.02,-.02]*20); r=2*b+.001
 m=relative_metrics(r,b)
 assert abs(m["beta"]-2)<1e-10
 assert abs(m["jensen_alpha"]-.252)<1e-10
