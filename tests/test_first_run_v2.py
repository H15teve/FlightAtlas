import hashlib,json
import subprocess,sys
from pathlib import Path
import pytest
from reader import read_flights,codeshare_flag
from data import adapt
from identity import identity_defaults
from carriers import apply_carriers,flight_key
from codeshares import candidates
from report_assets import requirements,apply_aircraft_details
from build import stats,BASE
from acquire_report_asset import acquire
from generate_report import _local_asset

HEADERS='日期,航班号,是否共享航班,出发机场,到达机场,表定出发,实际起飞,表定到达,实际降落,表定飞行时长,实际飞行时长,里程(公里),机型,注册号,舱位等级,座位号,含税票价,登机方式,下机方式\n'

def fixture(tmp_path):
    p=tmp_path/'synthetic.csv'
    p.write_text(HEADERS+'2025-01-02,CA0001,否,PEK,XMN,09:00,09:10,11:45,12:00,2小时45分,2小时50分,1700,737/800(WL),B-DEMO,PRIVATE-CABIN,PRIVATE-SEAT,PRIVATE-FARE,PRIVATE-BOARD,PRIVATE-EXIT\n2025-01-01,CA9001,是,XMN,PEK,08:00,-,10:30,-,2小时30分,-,1700,B738,B-DEMO,,,,,\n',encoding='utf-8')
    rows,audit=read_flights(p);adapt(rows,{})
    return p,rows,audit

def evidence():return {'aircraft_operations':[{'registration':'B-DEMO','msn':'DEMO-001','operator':'厦门航空','from':'2024-01-01','through':'2026-01-01','relation':'operating-carrier','source':'synthetic dated aircraft history'}],'schedules':[{'date':'2025-01-01','departure':'XMN','arrival':'PEK','scheduled_departure':'08:00','scheduled_arrival':'10:30','flight':'MF0001','operator':'厦门航空','source':'synthetic dated operating timetable'}]}

def test_full_export_headers_privacy_and_default_duration(tmp_path):
    p,rows,audit=fixture(tmp_path)
    assert rows[0]['codeshare'] is False and rows[1]['codeshare'] is True
    assert 'PRIVATE-' not in json.dumps([rows,audit])
    data=adapt(rows,{})
    assert data['duration']['total_minutes']==320 and data['duration']['estimated_segments']==1
    assert data['duration']['complete']
    for value,expected in [('是',True),('否',False),('1',True),('0',False),('',None)]:assert codeshare_flag(value) is expected
    with pytest.raises(ValueError):codeshare_flag('uncertain')

def test_identity_defaults_and_overrides_not_author_identity(tmp_path):
    _,rows,_=fixture(tmp_path)
    values=identity_defaults(rows,'2026-10-05')
    assert values['values']=={'place_of_birth':'XMN','place_of_issue':'PEK','date_of_issue':'2025-01-01','valid_until':'2026-10-05'}
    assert values['confirmation_required']
    rows[1]['date']='2005'
    assert identity_defaults(rows,'2026-10-05')['values']['date_of_issue'] is None
    rows[1]['date']=rows[0]['date'];rows[0]['scheduled_departure']='10:00';rows[1]['scheduled_departure']='8:00'
    assert identity_defaults(rows,'2026-10-05')['basis']['first_flight_row']==rows[1]['row']

def test_codeshare_candidates_only_dated_operator_and_schedule(tmp_path):
    _,rows,_=fixture(tmp_path)
    result=candidates(rows,evidence())
    assert len(result)==1 and result[0]['candidates'][0]['operating_flight']=='MF0001'
    candidate=result[0]['candidates'][0]
    assert candidate['user_verified'] is False and candidate['confirmed_on'] is None
    wrong=evidence();wrong['aircraft_operations'][0]['relation']='owner'
    assert not candidates(rows,wrong)[0]['candidates']
    wrong=evidence();wrong['schedules'][0]['date']='2025-01-02'
    assert not candidates(rows,wrong)[0]['candidates']
    wrong=evidence();wrong['schedules'][0]['scheduled_departure']='10:00'
    assert not candidates(rows,wrong)[0]['candidates']

def test_shared_prefix_never_used_before_user_confirmation(tmp_path):
    _,rows,_=fixture(tmp_path)
    apply_carriers(rows,{'infer_airline_from_flight_number':True,'flight_numbers_are_operating':True})
    assert rows[0]['carrier']=='中国国航' and rows[1]['carrier']=='未记录'
    assert rows[1]['operating_flight'] is None
    candidate=candidates(rows,evidence())[0]['candidates'][0]
    with pytest.raises(ValueError):apply_carriers(rows,{'codeshare_resolutions':[candidate]})
    accepted={**candidate,'user_verified':True,'confirmed_on':'2026-10-05'}
    apply_carriers(rows,{'codeshare_resolutions':[accepted]})
    assert rows[1]['carrier']=='厦门航空' and rows[1]['operating_flight']=='MF0001'
    assert adapt(rows,{})['rows'][1]['C']=='MF0001'
    oldkey=flight_key(rows[1]);rows[1]['scheduled_departure']='08:10'
    assert flight_key(rows[1])!=oldkey
    apply_carriers(rows,{'codeshare_resolutions':[accepted]})
    assert rows[1]['carrier']=='未记录'

def test_assets_no_final_placeholder_and_verified_metadata(tmp_path):
    _,rows,_=fixture(tmp_path);apply_carriers(rows,{})
    data=adapt(rows,{});s=stats(data)
    missing=requirements(data,s,{'include_repeated':True})
    assert {r['kind'] for r in missing}=={'airline_logo','featured_aircraft_photo'}
    fact={'registration':'B-DEMO','msn':'DEMO-001','from':'2025-01-01','through':'2025-12-31','source':'synthetic registry evidence','user_verified':True}
    apply_aircraft_details(rows,{'aircraft_details':[fact]})
    assert all(r['msn']=='DEMO-001' for r in rows)
    with pytest.raises(ValueError):apply_aircraft_details(rows,{'aircraft_details':[{**fact,'msn':'WRONG'}]})

def test_approved_asset_acquisition_preserves_bytes_and_rights(tmp_path):
    p=tmp_path/'source.svg';p.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="20"><path d="M0 0h100v20H0z"/></svg>',encoding='utf-8')
    candidate={'kind':'airline_logo','id':'ZZ','local_file':str(p),'source':'synthetic original fixture','credit':'test author','license':'CC0 synthetic fixture','accepted_by_user':True,'rights_confirmed':True}
    result=acquire(candidate,tmp_path/'private-assets')
    assert Path(result['file']).read_bytes()==p.read_bytes()
    fragment=json.loads(Path(result['config_fragment']).read_text(encoding='utf-8'))
    assert fragment['logo_evidence']['ZZ']['rights_confirmed']
    with pytest.raises(ValueError):acquire(candidate,tmp_path/'private-assets')
    with pytest.raises(ValueError):acquire({**candidate,'accepted_by_user':False},tmp_path/'rejected')

def test_builtin_alliance_logo_provenance_and_hashes():
    folder=BASE/'assets/alliances';manifest=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    assert set(manifest['assets'])=={'star','skyteam','oneworld'}
    for asset in manifest['assets'].values():
        assert asset['source'] and asset['credit'] and asset['license_url']
        assert hashlib.sha256((folder/asset['file']).read_bytes()).hexdigest()==asset['sha256']
        assert _local_asset(asset['file'],folder,True)
    from xml.etree import ElementTree as ET
    root=ET.parse(folder/'skyteam.svg').getroot()
    assert all(e.get('fill')=='#000066' for e in root)
    assert manifest['assets']['skyteam']['source_sha256'] and 'black matte' in manifest['assets']['skyteam']['changes']

def test_final_gates_and_successful_new_export_render(tmp_path):
    from PIL import Image
    source,rows,_=fixture(tmp_path);before=hashlib.sha256(source.read_bytes()).hexdigest()
    cfg=tmp_path/'config.json';out=tmp_path/'report'
    config={'report_date':'2026-10-05','valid_until':'2030-01-01','identity_confirmed':True,'include_repeated':True,'include_retired':True,'bar_min':4,'route_min':4}
    def run():
        cfg.write_text(json.dumps(config,ensure_ascii=False),encoding='utf-8')
        return subprocess.run([sys.executable,str(BASE/'scripts/generate_report.py'),'--input',str(source),'--config',str(cfg),'--output',str(out)],capture_output=True,text=True,encoding='utf-8',timeout=180)
    result=run()
    assert result.returncode==2 and '共享航班' in result.stderr and not out.exists()
    accepted={**candidates(rows,evidence())[0]['candidates'][0],'user_verified':True,'confirmed_on':'2026-10-05'}
    config['codeshare_resolutions']=[accepted]
    result=run()
    assert result.returncode==2 and '正式报告缺少已确认素材' in result.stderr and not out.exists()
    config['logos']={};config['logo_evidence']={}
    for code in ['CA','MF']:
        logo=tmp_path/(code+'.svg')
        logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="25"><path fill="#165c91" d="M0 0h100v25H0z"/></svg>',encoding='utf-8')
        config['logos'][code]=str(logo)
        config['logo_evidence'][code]={'source':'synthetic original fixture','credit':'test generator','license':'CC0 test data','accepted_by_user':True,'rights_confirmed':True}
    photo=tmp_path/'synthetic-photo.jpg';Image.new('RGB',(1200,600),'#438d91').save(photo)
    config['photos']=[{'registration':'B-DEMO','msn':'DEMO-001','file':str(photo),'source':'synthetic fixture, not an aircraft photograph','credit':'test generator','license':'CC0 test data','accepted_by_user':True,'rights_confirmed':True}]
    config['aircraft_details']=[{'registration':'B-DEMO','msn':'DEMO-001','from':'2025-01-01','through':'2025-12-31','delivery_date':'2010-01-01','source':'synthetic dated aircraft registry','user_verified':True}]
    config['aircraft_status']=[{'registration':'B-DEMO','msn':'DEMO-001','checked_on':'2026-10-05','source':'synthetic lifecycle fixture','permanent_passenger_exit':True,'last_passenger_date':'2025-12-31','status':'converted to cargo'}]
    result=run();assert result.returncode==0,result.stderr
    data=json.loads((out/'统计核验.json').read_text(encoding='utf-8'))
    assert data['flights']==2 and data['distance']==3400 and data['duration']['total_minutes']==320
    assert data['identity']['used']=={'place_of_birth':'XMN','place_of_issue':'PEK','date_of_issue':'2025-01-01','valid_until':'2026-10-05'}
    assert data['identity']['confirmed_by_user'] and not data['asset_audit']['missing']
    assert data['asset_audit']['report_kind']=='final'
    assert {r['flight_number'] for r in data['map']['top_flight_numbers']}=={'CA0001','MF0001'}
    assert len(data['airframe_cards']['retired'])==1
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    assert 'PRIVATE-' not in (out/'统计核验.json').read_text(encoding='utf-8')
    credits=json.loads((out/'素材许可与署名.json').read_text(encoding='utf-8'))
    assert len(credits['alliances']['assets'])==3 and set(credits['airline_logos'])=={'CA','MF'}
    for name in ['01_MY_FLIGHT_PASSPORT','02_FLIGHT_ATLAS']:
        with Image.open(out/(name+'.png')) as image:assert image.width>1000 and image.height>1000

def test_reject_active_asset_and_malformed_shared_confirmation(tmp_path):
    svg=tmp_path/'unsafe.svg';svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script>bad()</script></svg>',encoding='utf-8')
    with pytest.raises(ValueError):_local_asset(svg,tmp_path,True)
    _,rows,_=fixture(tmp_path)
    with pytest.raises(ValueError):apply_carriers(rows,{'codeshare_resolutions':[{}]})
