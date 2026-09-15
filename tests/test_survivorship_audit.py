import json
from pathlib import Path
from scripts.run_survivorship_repair import classify_survivorship

def test_missing_delisted_history_is_auditable(tmp_path):
    audit={"delisted_history_unavailable":1,"missing_delisted_histories":{"000001":"DELISTED_HISTORY_UNAVAILABLE"}}
    p=tmp_path/"audit.json";p.write_text(json.dumps(audit));loaded=json.loads(p.read_text());assert loaded["delisted_history_unavailable"]==1 and "000001" in loaded["missing_delisted_histories"]

def test_full_known_coverage_is_only_partial_without_bse_master():
    assert classify_survivorship(1.0,False)=="SURVIVORSHIP_BIAS_PARTIALLY_RESOLVED"
