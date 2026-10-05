import csv,hashlib,json
from preflight_report import assess
from mileage import apply_mileage
import pytest

def test_preflight_gaps_and_source_preserved(tmp_path):
    p=tmp_path/'raw.csv'
    p.write_text('date,flight,origin,destination,departure_time,arrival_time,distance\n2025-01-02,DEMO1,PEK,XMN,--,--,1700\n',encoding='utf-8')
    before=hashlib.sha256(p.read_bytes()).hexdigest()
    result=assess(p)
    assert result['flights']==1 and result['input_unchanged']
    assert result['missing_field_counts']=={'model':1,'registration':1,'delivery':1,'msn':1,'carrier':1,'distance':0}
    assert result['missing_duration_segments'][0]['flight']=='DEMO1'
    assert result['requires_user_decision_before_enrichment']
    assert before==hashlib.sha256(p.read_bytes()).hexdigest()

def test_export_first_queries_only_missing_pairs(tmp_path):
    cache=tmp_path/'tpm.json'
    cache.write_text(json.dumps({'records':{'BJS-XMN':{'tpm_miles':1000,'basis':'IATA TPM','source':'synthetic evidence','queried_on':'2026-01-01'}}}))
    rows=[{'row':2,'_dep':'PEK','_arr':'CAN','distance':1999},{'row':3,'_dep':'PEK','_arr':'XMN','distance':None},{'row':4,'_dep':'PEK','_arr':'CAN','distance':0}]
    audit=apply_mileage(rows,'export-then-tpm',cache)
    assert [r['distance_km'] for r in rows]==[1999,1609,0]
    assert [r['row'] for r in audit]==[2,3,4]
    assert audit[0]['basis']=='user export' and audit[1]['fallback_reason']=='export mileage missing'
    assert apply_mileage([{'row':1,'distance':100}],'export-then-tpm')[0]['km']==100
    with pytest.raises(ValueError,match='缺少城市TPM'):
        apply_mileage([{'row':1,'_dep':'PEK','_arr':'XMN','distance':'—'}],'export-then-tpm')
    with pytest.raises(ValueError,match='原导出里程'):
        apply_mileage([{'row':1,'distance':'bad'}],'export-then-tpm',cache)


def test_preflight_uses_accepted_enrichment_and_reports_card_age_gap(tmp_path):
    p=tmp_path/'repeated.csv'
    p.write_text('date,flight,origin,destination,distance,registration,model\n2025-01-02,CA1001,PEK,CAN,1700,B-DEMO,B738\n2025-01-03,CA1001,PEK,CAN,1700,B-DEMO,B738\n',encoding='utf-8')
    fact={'registration':'B-DEMO','msn':'123','from':'2025-01-01','through':'2025-12-31','source':'synthetic registry','user_verified':True}
    result=assess(p,{'age_as_of':'2026-10-06','aircraft_details':[fact]})
    assert result['missing_field_counts']['msn']==0
    assert result['aircraft_coverage']['age_coverage']['selected_cards_missing_age']==['B-DEMO']
    fact.update(delivery_date='2019-07-01',delivery_source='synthetic delivery record')
    result=assess(p,{'age_as_of':'2026-10-06','aircraft_details':[fact]})
    assert result['missing_field_counts']['delivery']==0
    assert result['aircraft_coverage']['age_coverage']['selected_cards_with_age']==1
