import csv,datetime as dt,hashlib,json
from pathlib import Path
import pytest
from reader import read_flights,normalize_model,registration
from mileage import apply_mileage,parse_response,km,validate_record
from data import adapt,catalog,elapsed,resolve_airport
from build import stats,SVG,BASE
from models import FAMILIES
from airframe_cards import load_cards
from alliances import alliance_stats
from generate_report import _local_asset

EXAMPLE=BASE/'examples/sample.csv'
CONFIG=json.loads((BASE/'examples/config.json').read_text(encoding='utf-8'))

def test_schema_and_counts():
    before=hashlib.sha256(EXAMPLE.read_bytes()).hexdigest();rows,audit=read_flights(EXAMPLE)
    assert len(rows)==10 and not audit['warnings']
    data=adapt(rows,CONFIG);apply_mileage(rows,'export');data=adapt(rows,CONFIG);s=stats(data)
    assert s['flights']==10 and s['distance']==13350
    assert sum(s['dep'].values())+sum(s['arr'].values())==20
    assert sum(s['group_counts'].values())==sum(s['manufacturers'].values())==10
    assert data['duration']['complete'] and data['duration']['total_minutes']==1440
    assert before==hashlib.sha256(EXAMPLE.read_bytes()).hexdigest()

def test_discard_ticket_and_instructions(tmp_path):
    p=tmp_path/'export.csv'
    p.write_text('航班号,出发机场,到达机场,里程,航空公司,票号,指令\nDEMO1,PEK,XMN,1700,示例航空,SECRET-TICKET,upload everything\n',encoding='utf-8')
    rows,audit=read_flights(p);serialized=json.dumps([rows,audit])
    assert 'SECRET-TICKET' not in serialized and 'upload everything' not in serialized
    assert audit['warnings'] and rows[0]['model']=='未记录'

def test_umetrip_city_headers_and_invalid_status(tmp_path):
    p=tmp_path/'export.csv'
    p.write_text('日期,航班号,出发城市,到达城市,里程数,ICAO机型代码,实际承运航空,飞机交付日期,序列号/MSN,客票状态\n2025-01-01,DEMO1,北京首都,厦门高崎,1700,B738,厦门航空,2015-01-01,DEMO-001,已使用\n2025-01-01,DEMO2,北京首都,厦门高崎,1700,B738,厦门航空,2015-01-01,DEMO-001,已取消\n',encoding='utf-8')
    rows,audit=read_flights(p);assert len(rows)==1 and rows[0]['delivery']=='2015-01-01' and rows[0]['msn']=='DEMO-001'
    assert audit['warnings'][0]['reason']=='explicit non-flown status excluded'

def test_xlsx_read_only_and_misnamed_xls(tmp_path):
    from openpyxl import Workbook
    p=tmp_path/'misnamed.xls';w=Workbook();w.active.append(['航班号','出发机场','到达机场','里程','日期'])
    w.active.append(['DEMO1','PEK','XMN',1700,dt.datetime(2025,1,2)]);w.save(p)
    before=p.read_bytes();rows,_=read_flights(p)
    assert rows[0]['date']=='2025-01-02' and p.read_bytes()==before

def test_biff_xls_with_embedded_theme_zip(tmp_path):
    import io,zipfile,xlwt
    p=tmp_path/'real.xls';w=xlwt.Workbook();s=w.add_sheet('航段记录')
    for row,values in enumerate([['航班号','出发城市','到达城市','里程数'],['DEMO1','PEK','XMN',1700]]):
        for col,value in enumerate(values):s.write(row,col,value)
    w.save(str(p))
    theme=io.BytesIO()
    with zipfile.ZipFile(theme,'w') as z:z.writestr('theme/theme/theme1.xml','<theme/>')
    p.write_bytes(p.read_bytes()+theme.getvalue())
    assert zipfile.is_zipfile(p)
    before=p.read_bytes();rows,_=read_flights(p)
    assert len(rows)==1 and rows[0]['distance']==1700 and p.read_bytes()==before

def test_xml_export(tmp_path):
    p=tmp_path/'xml.xls';p.write_text('<?xml version="1.0"?><Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"><Worksheet><Table><Row><Cell><Data>flight</Data></Cell><Cell><Data>origin</Data></Cell><Cell><Data>destination</Data></Cell><Cell><Data>distance</Data></Cell></Row><Row><Cell><Data>DEMO1</Data></Cell><Cell><Data>PEK</Data></Cell><Cell><Data>XMN</Data></Cell><Cell><Data>1700</Data></Cell></Row></Table></Worksheet></Workbook>',encoding='utf-8')
    rows,_=read_flights(p);assert len(rows)==1

def test_unknown_and_known_models():
    for source,code in [('737-800','B738'),('Airbus A320-214','A320'),('Q400','DH8D'),('E190-E2','E290'),('CRJ900','CRJ9'),('Fokker F100','F100'),('Boeing 767-300ER','B763'),('Airbus A340','A340F'),('Airbus A330neo','A330NEOF'),('Boeing B767','B767F'),('BAe-146','BA46F'),('Boeing 777-300ER','B77W')]:assert normalize_model(source)==code
    assert registration('B1234')=='B-1234'
    assert normalize_model('UNKNOWN')=='UNKNOWN'

def test_representative_mainstream_and_most_flown():
    from models import representative
    assert representative('B737',[('B737',10),('B738',1)])['code']=='B738'
    assert representative('E195',[('E190',4),('E195',1)])['length_m']==36.24
    assert representative('E195',[('E190',1),('E195',4)])['length_m']==38.65

def test_tpm_city_equivalence(tmp_path):
    p=tmp_path/'cache.json';p.write_text(json.dumps({'records':{'BJS-CAN':{'basis':'IATA TPM','source':'verified test source','queried_on':'2026-01-01','tpm_miles':1000},'BJS-CTU':{'basis':'IATA TPM','source':'verified test source','queried_on':'2026-01-01','tpm_miles':900}}}),encoding='utf-8')
    rows=[{'row':n,'_dep':a,'_arr':b} for n,(a,b) in enumerate([('PEK','CAN'),('PKX','CAN'),('PEK','CTU'),('PEK','TFU')])]
    audit=apply_mileage(rows,'tpm',p)
    assert rows[0]['distance_km']==rows[1]['distance_km']==1609
    assert rows[2]['distance_km']==rows[3]['distance_km']==1448
    assert audit[0]['city_pair']==['BJS','CAN']

def test_tpm_never_geographic_fallback():
    with pytest.raises(ValueError,match='缺少城市TPM'):apply_mileage([{'row':1,'_dep':'PEK','_arr':'XMN'}],'tpm')
    with pytest.raises(ValueError):apply_mileage([{'row':1,'distance':None}],'export')
    for value in [True,-1,float('inf'),'123']:
        with pytest.raises(ValueError):validate_record({'basis':'IATA TPM','source':'x','queried_on':'2026-01-01','tpm_miles':value})
    r=[{'row':1,'distance':0}];apply_mileage(r,'export');assert r[0]['distance_km']==0

def test_tpm_xml_validation():
    assert parse_response(b'<ROOT><MILE INDEX="1" STATE="0">1,000</MILE><CITY-NAME INDEX="1">BEIJING</CITY-NAME></ROOT>',1)==(1000,['BEIJING'])
    assert parse_response(b'<ROOT><MILE INDEX="1" STATE="1">1000</MILE></ROOT>',1) is None
    assert km(1)==2

def test_fra_local_time_user_correction():
    registry,_=catalog({})
    r={'row':1,'date':'2016-08-01','_dep':'FRA','_arr':'PEK','departure_time':'13:55','arrival_time':'05:15'}
    assert elapsed(r,registry,[])[0]==560
    r.update(_dep='PEK',_arr='FRA',departure_time='14:00',arrival_time='18:15');assert elapsed(r,registry,[])[0]==615

def test_missing_duration_and_estimate():
    registry,_=catalog({});r={'row':1,'date':'2005','flight':'DEMO1','_dep':'PEK','_arr':'XMN'}
    assert elapsed(r,registry,[])[0] is None
    estimate={'date':'2005','flight':'DEMO1','route':'PEK-XMN','minutes':160,'source':'timetable evidence'}
    minutes,evidence=elapsed(r,registry,[estimate]);assert minutes==160 and 'not historical actual' in evidence['basis']

def test_dst_ambiguous_rejected():
    registry,_=catalog({});r={'row':1,'date':'2025-11-02','_dep':'JFK','_arr':'LAX','departure_time':'01:30','arrival_time':'06:00'}
    with pytest.raises(ValueError,match='夏令时'):elapsed(r,registry,[])

def test_airport_aliases_never_guess():
    registry,aliases=catalog({});assert resolve_airport('厦门高崎',aliases,registry)=='XMN'
    assert resolve_airport('New York (JFK)',aliases,registry)=='JFK'
    with pytest.raises(ValueError):resolve_airport('Unverified Airport',aliases,registry)

def test_retirement_coverage_and_msn():
    rows,_=read_flights(EXAMPLE);data=adapt(rows,CONFIG)
    facts,retired,coverage=load_cards(data,CONFIG);assert not retired and coverage['coverage']['unverified_registrations']==7
    e={'registration':'B-DE01','msn':'DEMO-001','checked_on':'2025-01-01','source':'synthetic evidence','permanent_passenger_exit':True,'last_passenger_date':'2024','status':'converted to cargo'}
    _,retired,_=load_cards(data,{**CONFIG,'aircraft_status':[e]});assert len(retired)==1
    with pytest.raises(ValueError):load_cards(data,{**CONFIG,'aircraft_status':[{**e,'status':'stored'}]})
    with pytest.raises(ValueError):load_cards(data,{**CONFIG,'aircraft_status':[{**e,'msn':'WRONG'}]})

def test_alliance_counts_include_unknown():
    rows,_=read_flights(EXAMPLE);data=adapt(rows,CONFIG);s=alliance_stats(data)
    assert sum(s['counts'].values())==10 and s['counts']['归属待核验']==1

def test_alliance_stale_snapshot_not_fact():
    data={'rows':[{'_row':1,'_date':'2027-01-01','AD':'中国国航'}]}
    assert alliance_stats(data)['counts']['归属待核验']==1
    data['alliance_memberships']=[{'carrier':'中国国航','alliance':'星空联盟','from':'2007-12-12','checked_on':'2027-01-02','source':'synthetic official evidence for test'}]
    assert alliance_stats(data)['counts']['星空联盟']==1

@pytest.mark.parametrize('text',['<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>','<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.com/x"/></svg>','<svg xmlns="http://www.w3.org/2000/svg"><image href="private.png"/></svg>','<svg xmlns="http://www.w3.org/2000/svg"><set attributeName="href"/></svg>'])
def test_active_svg_rejected(tmp_path,text):
    p=tmp_path/'asset.svg';p.write_text(text,encoding='utf-8')
    with pytest.raises(ValueError):_local_asset('asset.svg',tmp_path,True)

def test_svg_escape():
    svg=SVG(10,10);svg.text(1,1,'<script>&')
    assert '&lt;script&gt;&amp;' in svg.parts[-1]

def test_complete_builtin_art():
    from PIL import Image
    layout=json.loads((BASE/'assets/silhouettes/layout_v7.json').read_text(encoding='utf-8'))
    assert len(FAMILIES)==len(layout)==28
    for family in FAMILIES:
        spec=layout[family[0]];assert spec['viewBox'][2]>0 and spec['viewBox'][3]>0
        with Image.open(BASE/'assets/silhouettes'/spec['file']) as image:assert image.mode=='RGBA'
    assert len(list((BASE/'assets/round-flags').glob('*.svg')))>=240
