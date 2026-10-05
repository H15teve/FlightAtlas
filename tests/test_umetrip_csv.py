"""Synthetic fixtures for recent Umetrip CSV syntax; no private flight data."""
import hashlib
import pytest
from reader import read_flights,normalize_model
from data import adapt,elapsed,catalog
from build import stats
from preflight_report import assess
from carriers import apply_carriers


@pytest.mark.parametrize('raw,code',[
    ('330/343(X)','A333'),('350/941','A359'),('350/1041','A35K'),
    ('320/251(N)','A20N'),('319/153(N)','A19N'),('321/252(NX)','A21N'),
    ('321/253(N)(X)','A21N'),('320/214(SL)','A320'),('321/213','A321'),
    ('330/243','A332'),('330','A330F'),('737/89L(WL)','B738'),
    ('737/9B5(ER)','B739'),('737/75C(WL)','B737'),('777/39L(ER)','B77W'),
    ('777/367','B773'),('777/224(ER)','B772'),('747/4J6','B744'),
    ('747/89L','B748'),('757/25C(PCF)','B752'),('C919/700ER','C919'),
    ('ERJ195(LR)','E195'),('220/300','BCS3'),('DHC/8','DH8F'),
    ('BAE JETSTREAM 41','JS41'),('-','未记录')])
def test_model_export_syntax(raw,code):
    assert normalize_model(raw)==code


def test_native_csv_headers_duration_and_no_inferred_operator(tmp_path):
    source=tmp_path/'synthetic.csv'
    source.write_text('日期,航班号,出发机场,到达机场,表定出发,实际起飞,表定到达,实际降落,表定飞行时长,实际飞行时长,里程(公里),机型,注册号,含税票价\n'
        '2026-01-01,DEMO1,PEK,XMN,08:00,09:00,10:00,11:30,2小时,2小时30分,1700,737/800(WL),B-DEMO,PRIVATE-FARE\n'
        '2026-01-02,DEMO2,PEK,XMN,08:00,-,10:00,-,2小时,-,-,-,-,PRIVATE-FARE\n',encoding='utf-8-sig')
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    rows,audit=read_flights(source)
    assert rows[0]['model']=='B738' and rows[0]['distance']=='1700'
    assert rows[0]['departure_time']=='09:00' and rows[0]['arrival_time']=='11:30'
    assert all(r['carrier']=='未记录' for r in rows)
    assert 'PRIVATE-FARE' not in str((rows,audit))
    data=adapt(rows,{})
    assert data['duration']['total_minutes']==270
    assert data['duration']['missing_rows']==[]
    assert data['duration']['estimated_segments']==1
    assert data['duration']['segments'][0]['basis']=='input actual flight duration'
    assert data['duration']['segments'][0]['raw_value']=='2小时30分'
    result=assess(source)
    assert result['missing_field_counts']=={'model':1,'registration':1,'delivery':2,'msn':2,'carrier':2,'distance':1}
    s=stats(data)
    assert not s['airlines'] and s['unknown_carrier_flights']==2
    assert before==hashlib.sha256(source.read_bytes()).hexdigest()


@pytest.mark.parametrize('raw,minutes',[('3小时4分',184),('2小时',120),('35分钟',35),('150',150),('0小时35分',35),('2小时0分',120)])
def test_explicit_duration_priority(raw,minutes):
    registry,_=catalog({})
    row={'row':2,'minutes':raw,'minutes_header':'实际飞行时长','_dep':'FRA','_arr':'PEK','date':'2026-01-01','departure_time':'12:00','arrival_time':'13:00'}
    assert elapsed(row,registry,[])[0]==minutes


@pytest.mark.parametrize('raw',['2小时75分','invalid',0,-10,float('inf')])
def test_invalid_duration_not_silently_estimated(raw):
    with pytest.raises(ValueError):elapsed({'minutes':raw},{},[])


def test_conversion_descriptor_not_retirement_evidence(tmp_path):
    source=tmp_path/'synthetic.csv'
    source.write_text('flight,origin,destination,model\nDEMO1,PEK,XMN,757/25C(PCF)\n',encoding='utf-8')
    rows,audit=read_flights(source)
    assert rows[0]['model_source']=='757/25C(PCF)'
    assert audit['model_normalization'][0]['normalized']=='B752'
    assert any('不作为' in w['reason'] for w in audit['warnings'])
    assert 'permanent_passenger_exit' not in rows[0]


def test_explicit_scheduled_fallback_and_actual_only(tmp_path):
    p=tmp_path/'synthetic.csv'
    p.write_text('日期,航班号,出发机场,到达机场,实际起飞,实际降落,实际飞行时长,表定飞行时长\n2026-01-01,DEMO1,PEK,XMN,08:00,10:00,2小时30分,2小时\n2026-01-02,DEMO2,PEK,XMN,08:00,10:00,-,2小时45分\n',encoding='utf-8')
    rows,_=read_flights(p)
    actual=adapt(rows,{'duration_policy':'actual-only'})['duration']
    assert actual['total_minutes']==150 and actual['missing_rows']==[3]
    fallback=adapt(rows,{'duration_policy':'actual-then-scheduled'})['duration']
    assert fallback['complete'] and fallback['total_minutes']==315
    assert fallback['estimated_segments']==1
    assert fallback['segments'][1]['basis']=='input scheduled-duration fallback, not actual'
    assert fallback['segments'][1]['raw_value']=='2小时45分'


def test_prefix_inference_requires_opt_in_and_retains_evidence():
    def rows():return [{'row':2,'flight':'CA0001','carrier':'未记录'},{'row':3,'flight':'3U0001','carrier':'未记录'},{'row':4,'flight':'ZZ0001','carrier':'未记录'},{'row':5,'flight':'MF0001','carrier':'已核验航司'}]
    original=rows();apply_carriers(original,{})
    assert original[0]['carrier']=='未记录'
    inferred=rows();audit=apply_carriers(inferred,{'infer_airline_from_flight_number':True,'flight_numbers_are_operating':True})
    assert [r['carrier'] for r in inferred]==['中国国航','四川航空','未记录','已核验航司']
    assert audit[0]['basis']=='user-confirmed operating flight number prefix'
    assert audit[2]['basis']=='unknown flight prefix; not inferred'
    not_verified=rows();audit=apply_carriers(not_verified,{'infer_airline_from_flight_number':True})
    assert 'operator not verified' in audit[0]['basis']
