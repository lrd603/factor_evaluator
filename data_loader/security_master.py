"""Historical A-share security master built from exchange records."""
from __future__ import annotations
import pandas as pd

MASTER_COLUMNS=["stock_code","stock_name","exchange","listing_date","delisting_date","status","source","data_quality"]

def _pick(frame,names):
    for name in names:
        if name in frame:return name
    raise ValueError(f"none of columns {names} found in {list(frame.columns)}")

def normalize_master(frame,exchange,status,source):
    code=_pick(frame,["公司代码","证券代码","A股代码","股票代码"]); name=_pick(frame,["公司简称","证券简称","A股简称","股票简称"]); listing=_pick(frame,["上市日期","A股上市日期"])
    delist=next((x for x in ["终止上市日期","暂停上市日期","退市日期"] if x in frame),None)
    out=pd.DataFrame({"stock_code":frame[code].astype(str).str.extract(r"(\d{6})",expand=False),"stock_name":frame[name].astype(str),"exchange":exchange,"listing_date":pd.to_datetime(frame[listing],errors="coerce"),"delisting_date":pd.to_datetime(frame[delist],errors="coerce") if delist else pd.NaT,"status":status,"source":source})
    a_share_pattern=r"^(600|601|603|605|688)" if exchange=="SH" else r"^(000|001|002|003|300|301)"
    out=out[out.stock_code.str.match(a_share_pattern,na=False)]
    out["data_quality"]=out.apply(lambda r:"HIGH" if pd.notna(r.listing_date) and (status=="listed" or pd.notna(r.delisting_date)) else "LOW",axis=1)
    return out[MASTER_COLUMNS].dropna(subset=["stock_code","listing_date"])

def merge_security_masters(frames):
    x=pd.concat(frames,ignore_index=True); x["_delisted"]=x.delisting_date.notna(); x=x.sort_values(["stock_code","_delisted"],ascending=[True,False]).drop_duplicates("stock_code",keep="first")
    return x.drop(columns="_delisted").sort_values("stock_code").reset_index(drop=True)

def active_on(master,date):
    t=pd.Timestamp(date); listing=pd.to_datetime(master.listing_date); delisting=pd.to_datetime(master.delisting_date)
    return listing.le(t)&(delisting.isna()|delisting.gt(t))

def fetch_security_master():
    import akshare as ak
    return merge_security_masters([
        normalize_master(ak.stock_info_sh_name_code(symbol="主板A股"),"SH","listed","SSE_current_A"),
        normalize_master(ak.stock_info_sh_name_code(symbol="科创板"),"SH","listed","SSE_current_STAR"),
        normalize_master(ak.stock_info_sz_name_code(symbol="A股列表"),"SZ","listed","SZSE_current_A"),
        normalize_master(ak.stock_info_sh_delist(symbol="全部"),"SH","delisted","SSE_delisting_master"),
        normalize_master(ak.stock_info_sz_delist(symbol="终止上市公司"),"SZ","delisted","SZSE_delisting_master")])
