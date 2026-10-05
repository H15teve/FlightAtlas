"""Integration tests use only synthetic flight records; no private workbook is packaged."""
import csv,hashlib,json,subprocess,sys
from pathlib import Path
from xml.etree import ElementTree as ET
import pytest
from build import BASE
from models import FAMILIES
ROOT=BASE.parents[1]
CLI=BASE/'scripts/generate_report.py'
NS={'s':'http://www.w3.org/2000/svg'}

def execute(source,out,*extra):
    result=subprocess.run([sys.executable,str(CLI),'--input',str(source),'--output',str(out),'--config',str(BASE/'examples/config.json'),*extra],capture_output=True,text=True,encoding='utf-8',timeout=180)
    assert result.returncode==0,result.stderr
    return json.loads((out/'统计核验.json').read_text(encoding='utf-8'))

def test_png_and_options(tmp_path):
    from PIL import Image
    source=BASE/'examples/sample.csv';before=hashlib.sha256(source.read_bytes()).hexdigest()
    out=tmp_path/'report';s=execute(source,out,'--no-include-repeated','--include-retired','--bar-min','5','--route-min','4')
    assert s['flights']==10 and len(s['wordcloud_layout'])==6
    assert s['options']['bar_min']==5 and s['map']['route_min']==4 and not s['map']['frequent_routes']
    assert len(s['map']['top_flight_numbers'])==3
    assert [r['flight_number'] for r in s['map']['top_flight_numbers']]==['DEMO001','DEMO002','DEMO003']
    map_svg=(out/'国内航线.svg').read_text(encoding='utf-8')
    assert '常乘航班 TOP3' in map_svg and 'DEMO001' in map_svg
    labels=json.loads((out/'机场标签核验.json').read_text(encoding='utf-8'))
    assert labels['flight_number_rank_styles']==[
        {'font_size':22,'color':'#b78b35'},
        {'font_size':22,'color':'#7f8b97'},
        {'font_size':22,'color':'#a86c46'},
    ]
    for number,size,color in [('DEMO001',22,'#b78b35'),('DEMO002',22,'#7f8b97'),('DEMO003',22,'#a86c46')]:
        texts=ET.parse(out/'国内航线.svg').findall('.//s:text',NS)
        assert any(t.text==number and t.get('fill')==color and f'{size}px' in t.get('style','') for t in texts)
    assert not s['airframe_cards']['repeated'] and not s['airframe_cards']['retired']
    for name in ['01_MY_FLIGHT_PASSPORT','02_FLIGHT_ATLAS']:
        with Image.open(out/(name+'.png')) as image:assert image.width>1000 and image.height>1000
        ET.parse(out/(name+'.svg'))
    assert '未提供已确认永久退出客运' in (out/'02_FLIGHT_ATLAS.svg').read_text(encoding='utf-8')
    assert before==hashlib.sha256(source.read_bytes()).hexdigest()

def test_all_families_and_directed_routes(tmp_path):
    source=tmp_path/'all.csv'
    with source.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['date','flight','origin','destination','distance','aircraft_type','operator','duration_minutes'])
        for i,family in enumerate(FAMILIES):w.writerow(['2025-01-02','DEMO'+str(i),'PEK' if i%2 else 'XMN','XMN' if i%2 else 'PEK',1700,family[2].split()[0],'示例航空',150])
    out=tmp_path/'all';s=execute(source,out,'--svg-only','--no-include-repeated')
    assert sum(s['manufacturers'].values())==28
    svg=ET.parse(out/'02_FLIGHT_ATLAS.svg');assert len(svg.findall('.//s:svg[@data-plane]',NS))==28
    assert len(s['map']['frequent_routes'])==2 and all(r['flights']==14 for r in s['map']['frequent_routes'])
    assert s['layout']['model_columns']=={'regional':5,'narrow':4,'wide':3}
    assert s['layout']['airport_bar_body']==s['layout']['wordcloud_body']
    labels=json.loads((out/'机场标签核验.json').read_text(encoding='utf-8'))
    assert labels['leader_lines']==0
    assert labels['flight_number_ranking_box'][3]<=s['map']['height']-15
    assert all(x['nearest_other_point_gap']>x['point_label_gap'] for x in labels['labels'])
    assert 'data:image/svg+xml;base64,' in (out/'国内航线.svg').read_text(encoding='utf-8')
    geometry=json.loads((out/'南海附图核验.json').read_text(encoding='utf-8'))
    assert geometry['synthetic_inset_regions']==0 and geometry['source_geometry_unchanged']
    assert geometry['rendered_region_count']==geometry['source_feature_count']

def test_refuse_overwrite(tmp_path):
    out=tmp_path/'occupied';out.mkdir();(out/'keep.txt').write_text('user content')
    result=subprocess.run([sys.executable,str(CLI),'--input',str(BASE/'examples/sample.csv'),'--output',str(out)],capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==2 and (out/'keep.txt').read_text()=='user content'

@pytest.mark.parametrize('bar_count,single_count',[(1,0),(3,3),(12,9),(30,21),(0,13)])
def test_airline_quantity_layout_in_rendered_svg(tmp_path,bar_count,single_count):
    from fonts import font
    config=json.loads((BASE/'examples/config.json').read_text(encoding='utf-8'))
    config.update({'include_repeated':False,'bar_min':4,'airline_codes':{},'logos':{}})
    records=[]
    for i in range(bar_count+single_count):
        name=f'布局测试航空{i:02d}';code=f'T{i:02d}'
        # Vary aspect ratios to exercise both logo width and height limits.
        w,h=[(240,30),(120,90),(80,80)][i%3]
        logo=tmp_path/f'{code}.svg'
        logo.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="#326f9b"/></svg>',encoding='utf-8')
        config['airline_codes'][name]=code;config['logos'][code]=str(logo)
        count=max(4,136-i*3) if i<bar_count else 1
        records.extend([['2025-01-02',f'DEMO{i:02d}','PEK','XMN',1700,'B738',name,150]]*count)
    source=tmp_path/'quantity.csv'
    with source.open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['date','flight','origin','destination','distance','aircraft_type','operator','duration_minutes']);writer.writerows(records)
    cfg=tmp_path/'config.json';cfg.write_text(json.dumps(config),encoding='utf-8')
    out=tmp_path/'report';s=execute(source,out,'--svg-only','--config',str(cfg))
    assert len(s['airlines'])==bar_count+single_count
    panel=s['airline_panel_layout'];assert panel['content_bottom']<panel['height']
    svg=ET.parse(out/'02_FLIGHT_ATLAS.svg')
    bars=svg.findall('.//s:rect[@data-airline-bar-index]',NS)
    labels=svg.findall('.//s:text[@data-airline-count-index]',NS)
    logos=[element for element in svg.getroot().iter() if element.get('data-airline-logo')]
    assert len(bars)==len(labels)==bar_count
    assert len(logos)==bar_count+single_count
    for bar,label in zip(bars,labels):
        label_left=float(label.get('x'))-font(26,True).getlength(label.text)
        assert float(bar.get('x'))+float(bar.get('width'))<=label_left-20
    for logo in logos:
        assert float(logo.get('width'))<=float(logo.get('data-max-width'))+.01
        assert float(logo.get('height'))<=float(logo.get('data-max-height'))+.01
    if bar_count and single_count:
        assert float(logos[bar_count].get('y'))>float(logos[bar_count-1].get('y'))+float(logos[bar_count-1].get('height'))+30


@pytest.mark.parametrize('signature',['ALL UPPERCASE SIGNATURE','A VERY LONG UPPERCASE SIGNATURE THAT MUST FIT THE SAME BOX'])
def test_uppercase_signature_is_allowed_and_preserved_in_cli(tmp_path,signature):
    s=execute(BASE/'examples/sample.csv',tmp_path/'report','--svg-only','--signature-name',signature)
    layout=s['passport_layout']
    assert layout['signature']==signature
    assert layout['signature_layout']['text']==signature
    assert layout['signature_layout']['proportional_fit']
    assert layout['signature_box']==[1065,1226,470,112]

def test_native_csv_unknown_carriers_and_partial_duration(tmp_path):
    source=tmp_path/'synthetic.csv'
    source.write_text('日期,航班号,出发机场,到达机场,里程(公里),实际飞行时长,机型\n2026-01-01,DEMO1,PEK,XMN,1700,2小时30分,330/343(X)\n2026-01-02,DEMO2,XMN,PEK,1700,-,-\n',encoding='utf-8')
    out=tmp_path/'report';s=execute(source,out,'--svg-only','--include-retired')
    assert s['flights']==2 and s['distance']==3400
    assert not s['airlines'] and s['unknown_carrier_flights']==2
    assert s['models']=={'A333':1,'未记录':1}
    assert not s['duration']['complete'] and s['duration']['total_minutes']==150
    svg=(out/'02_FLIGHT_ATLAS.svg').read_text(encoding='utf-8')
    assert '2 次飞行的承运航司未记录' in svg
    assert '以下航司均仅搭乘过一次' not in svg
    assert s['alliances']['counts']['归属待核验']==2

def test_growing_repeated_cards_do_not_overlap(tmp_path):
    source=tmp_path/'repeat.csv'
    with source.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['date','flight','origin','destination','distance','aircraft_type','operator','registration','duration_minutes'])
        for i in range(21):
            for j in range(2):w.writerow(['2025-01-02','DEMO'+str(i*2+j),'PEK','XMN',1700,'B738','示例航空','B-D'+str(i).zfill(3),150])
    s=execute(source,tmp_path/'report','--svg-only')
    cards=s['airframe_cards']['repeated'];assert len(cards)==21
    boxes=[c['box'] for c in cards]
    for i,a in enumerate(boxes):
        for b in boxes[i+1:]:assert not (a[0]<b[0]+b[2] and a[0]+a[2]>b[0] and a[1]<b[1]+b[3] and a[1]+a[3]>b[1])

def test_local_authorized_photos_and_equal_retired_cards(tmp_path):
    from PIL import Image
    config=json.loads((BASE/'examples/config.json').read_text(encoding='utf-8'));config['include_retired']=True
    config['photos']=[];config['aircraft_status']=[]
    for i,(reg,msn,size) in enumerate([('B-DE01','DEMO-001',(400,200)),('B-DE03','DEMO-003',(400,260))]):
        # Plain colored test fixtures, not aircraft photographs or edited user assets.
        p=tmp_path/f'fixture{i}.jpg';Image.new('RGB',size,'#438d91').save(p)
        config['photos'].append({'registration':reg,'msn':msn,'file':str(p),'source':'synthetic test fixture','credit':'test generator','license':'CC0 test data'})
        config['aircraft_status'].append({'registration':reg,'msn':msn,'source':'synthetic lifecycle evidence','checked_on':'2025-12-31','permanent_passenger_exit':True,'last_passenger_date':'2020 (year precision)','status':'converted to cargo'})
    cfg=tmp_path/'private-config.json';cfg.write_text(json.dumps(config),encoding='utf-8')
    out=tmp_path/'report';s=execute(BASE/'examples/sample.csv',out,'--svg-only','--config',str(cfg))
    cards=s['airframe_cards']['retired'];assert len(cards)==2
    assert cards[0]['box'][3]==cards[1]['box'][3]
    assert cards[0]['photo_aspect_ratio']==2 and cards[1]['photo_aspect_ratio']==400/260
    assert all(card['photo_box'][0]==card['box'][0]+16 and card['photo_box'][2]==274 for card in cards)
