"""Download and cache the exchange-backed historical A-share security master."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from data_loader.security_master import fetch_security_master

def main():
    out=ROOT/"cache/survivorship"; out.mkdir(parents=True,exist_ok=True)
    master=fetch_security_master(); master.to_csv(out/"security_master.csv",index=False,encoding="utf-8-sig")
    meta={"source":["SSE current/delisting masters","SZSE current/delisting masters"],"is_real_data":True,"rows":len(master),"listed":int(master.delisting_date.isna().sum()),"delisted":int(master.delisting_date.notna().sum())}
    (out/"security_master.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
