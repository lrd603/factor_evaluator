import pandas as pd
from data_loader.security_master import active_on,normalize_master
from universe import PointInTimeSecurityMasterProvider,UniverseConfig

def _master():
    return pd.DataFrame([{"stock_code":"000001","stock_name":"live","exchange":"SZ","listing_date":"2019-01-01","delisting_date":None,"status":"listed","source":"x","data_quality":"HIGH"},{"stock_code":"000002","stock_name":"gone","exchange":"SZ","listing_date":"2018-01-01","delisting_date":"2021-06-01","status":"delisted","source":"x","data_quality":"HIGH"}])
def _history():
    dates=pd.date_range("2018-01-01","2021-06-02",freq="D"); return pd.DataFrame([{"date":d,"stock":s,"close":1.,"volume":1.,"amount":1.} for d in dates for s in ["000001","000002"]])
def test_listing_and_delisting_boundaries():
    m=_master(); assert not active_on(m,"2018-12-31").iloc[0]; assert active_on(m,"2021-05-31").iloc[1]; assert not active_on(m,"2021-06-01").iloc[1]
def test_later_delisted_stock_appears_in_past_not_after_delisting():
    p=PointInTimeSecurityMasterProvider(_master(),_history(),UniverseConfig(min_listing_days=1)); assert "000002" in p.get_universe("2020-01-01"); assert "000002" not in p.get_universe("2021-06-01")
def test_current_list_does_not_control_historical_eligibility():
    assert "000002" in PointInTimeSecurityMasterProvider(_master(),_history(),UniverseConfig(min_listing_days=1)).get_universe("2020-01-01")
def test_forward_return_does_not_cross_last_price():
    from factor_analysis.research import calculate_forward_returns
    x=pd.DataFrame({"date":pd.date_range("2020-01-01",periods=3),"stock":["x"]*3,"close":[1,2,3]}); y=calculate_forward_returns(x,[2]); assert pd.isna(y.iloc[1].forward_return_2d)
def test_delisted_master_excludes_b_shares():
    raw=pd.DataFrame({"证券代码":["000001","200001"],"证券简称":["A","B"],"上市日期":["2000-01-01"]*2,"终止上市日期":["2020-01-01"]*2})
    assert normalize_master(raw,"SZ","delisted","test").stock_code.tolist()==["000001"]
