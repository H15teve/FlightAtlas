"""Render public README images from synthetic, optionally aggregate-informed data.

Never copy source rows, airports, dates, registrations, airline names or photos.
Private intermediate files stay in .local; only PNGs and asset provenance are public.
"""
import argparse,base64,csv,datetime as dt,hashlib,html,json,math,random,re,subprocess,sys,time
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode,quote
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/'plugins/flight-atlas'
sys.path.insert(0,str(PLUGIN/'engine'))
from data import catalog
from models import normalize_model
from reader import read_flights

ART={
    'CA':'Air China wordmark.svg',
    'CZ':'China Southern Airlines wordmark logo.svg',
    'TK':'Turkish Airlines logo 2012.svg',
    'BA':'BRITISH AIRWAYS logo.svg',
    'featured':'B-5214 Boeing 737 Air China (7183135231).jpg',
    'retired':'B-5217 Boeing 737 Air China (7183107141).jpg',
}
MODELS=['DH8D','E195','AJ27','JS41','AT76','B738','B38M','A320','A20N','C919','B752','B77W','B789','A333','A359','B744','A388']
DEFAULT_WEIGHTS=[3,3,2,1,2,40,8,25,15,2,3,12,12,10,7,2,2]
CARRIERS={'CA':'中国国航','CZ':'南方航空','TK':'土耳其航空','BA':'英国航空'}
PAIRS=[('PVG','PEK'),('PEK','PVG'),('HGH','CAN'),('CAN','HGH'),('SZX','CTU'),('CTU','SZX'),('PVG','CKG'),('CKG','PVG'),('HGH','XIY'),('XIY','HGH'),('PEK','KMG'),('PKX','SYX'),('CAN','HAK'),('SZX','WUH'),('PVG','URC'),('HGH','TAO'),('PVG','NKG'),('CAN','FOC'),('PEK','TSN'),('HGH','XMN'),('PVG','NRT'),('PVG','KIX'),('CAN','SIN'),('CAN','BKK'),('PEK','LHR'),('PVG','CDG'),('PEK','IST'),('IST','LHR'),('PVG','JFK'),('PEK','SFO'),('CAN','SYD'),('PVG','DXB')]

def get(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'FlightAtlas/0.1 (README illustration; public Commons files)'}),timeout=20) as response:return response.read()
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

def assets(folder):
    folder.mkdir(parents=True,exist_ok=True);proof={};paths={}
    for key,title in ART.items():
        sidecar=folder/(key+'.json');path=folder/(key+Path(title).suffix)
        if sidecar.exists() and path.exists():info=json.loads(sidecar.read_text(encoding='utf-8'))
        else:
            query=urlencode({'action':'query','format':'json','prop':'imageinfo','iiprop':'url|extmetadata','titles':'File:'+title})
            page=next(iter(json.loads(get('https://commons.wikimedia.org/w/api.php?'+query))['query']['pages'].values()))
            record=page['imageinfo'][0];meta=record['extmetadata']
            license=meta['LicenseShortName']['value']
            if license not in ['Public domain','CC BY-SA 3.0','CC BY-SA 4.0','CC BY 4.0']:raise ValueError('Unapproved license: '+license)
            clean=lambda value:html.unescape(re.sub('<[^>]+>','',value)).strip()
            info={'title':title,'source':'https://commons.wikimedia.org/wiki/File:'+quote(title.replace(' ','_')),'credit':clean(meta.get('Artist',{}).get('value','')),'license':license,'license_url':meta.get('LicenseUrl',{}).get('value','https://commons.wikimedia.org/wiki/Template:PD-textlogo'),'download':record['url'].split('?')[0]}
            path.write_bytes(get(info['download']));info['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            sidecar.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        assert info['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
        proof[key]=info;paths[key]=str(path.resolve())
    # Complete horizontal symbol+wordmark variants, from separately licensed
    # geometry and original wordmark paths; not a wordmark-only crop.
    revision='98820a4dc8c363ca72fa2c0d294ea4a0a9bba75d'
    for key,slug,color in [('CA','airchina','#e30e17'),('CZ','chinasouthernairlines','#0093d0'),('BA','britishairways','#002e5f')]:
        url=f'https://raw.githubusercontent.com/simple-icons/simple-icons/{revision}/icons/{slug}.svg'
        symbol=folder/(key+'-symbol.svg')
        if not symbol.exists():symbol.write_bytes(get(url))
        shape=symbol.read_text(encoding='utf-8')
        wordmark=Path(paths[key]).read_bytes();data=base64.b64encode(wordmark).decode()
        if key=='CZ':
            d=re.search(r'<path d="([^"]+)"',shape)[1]
            flower,tail=d.rsplit('M24 ',1)
            shape='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#0093d0" d="M24 '+tail+'"/><path fill="#ed1b2f" d="'+flower+'"/></svg>'
            data=base64.b64encode(wordmark.replace(b'#02204f',b'#002052')).decode()
        elif key=='BA':
            d=re.search(r'<path d="([^"]+)"',shape)[1]
            blue,red=d.split('M24 ',1)
            shape='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 9 24 6"><path fill="#002e5f" d="'+blue+'"/><path fill="#d71920" d="M24 '+red+'"/></svg>'
            data=base64.b64encode(wordmark.replace(b'#2E5C99',b'#002e5f')).decode()
        else:shape=shape.replace('<path ',f'<path fill="{color}" ',1)
        symbol_data=base64.b64encode(shape.encode()).decode()
        width,height=(480,120) if key=='CA' else (320,32) if key=='BA' else (1030,284)
        mark_box=(120,34,344,52) if key=='CA' else (0,9,207,19) if key=='BA' else (210,0,820,277)
        symbol_box=(4,12,96,96) if key=='CA' else (220,0,96,24) if key=='BA' else (0,42,200,200)
        images=''.join(f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/svg+xml;base64,{uri}"/>' for (x,y,w,h),uri in [(symbol_box,symbol_data),(mark_box,data)])
        combined=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">{images}</svg>'
        path=folder/(key+'-complete.svg');path.write_text(combined,encoding='utf-8')
        # Rasterize generated vector artwork; final input disallows nested SVG URIs.
        raster=path.with_suffix('.png')
        code="require(process.argv[1]+'/node_modules/sharp')(process.argv[2],{density:192}).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exit(1)})"
        subprocess.run(['node','-e',code,str(PLUGIN),str(path),str(raster)],check=True)
        paths[key]=str(raster.resolve())
        proof[key]={**proof[key],'license':'Public domain + CC0-1.0','variant':'complete horizontal symbol + original wordmark','components':[{'source':f'https://github.com/simple-icons/simple-icons/blob/{revision}/icons/{slug}.svg','credit':'Simple Icons contributors','license':'CC0-1.0','license_url':f'https://github.com/simple-icons/simple-icons/blob/{revision}/LICENSE.md','sha256':hashlib.sha256(symbol.read_bytes()).hexdigest()}],'composition_note':'Air China red symbol; China Southern blue tail and red kapok; British Airways navy wordmark with red/blue speedmarque. Original path geometry retained, no symbol cropping. These are licensed-component compositions, not certified official lockup proportions.','composition_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    proof['CA']['demo_exception']={'scope':'public-readme-demo','selected_variant':'English AIR CHINA wordmark with phoenix symbol','user_approved':True,'affects_user_report_selection':False}
    return paths,proof

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path);parser.add_argument('--work',type=Path,default=ROOT/'.local/readme-demo');parser.add_argument('--render',action='store_true')
    args=parser.parse_args();work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
    rng=random.Random(94721);weights=DEFAULT_WEIGHTS[:];source_hash=None
    if args.source:
        raw=args.source.read_bytes();source_hash=hashlib.sha256(raw).hexdigest()
        rows,_=read_flights(args.source)
        counts=Counter(normalize_model(r['model']) for r in rows)
        # Use noisy relative model frequencies only; even the record count is new.
        weights=[max(1,round((counts.get(model,0)+base)*rng.uniform(.65,1.45))) for model,base in zip(MODELS,DEFAULT_WEIGHTS)]
    paths,proof=assets(work/'assets');registry,_=catalog({})
    demo_pairs=[(a,'NNG' if b=='URC' else b) for a,b in PAIRS]
    model_sequence=MODELS+rng.choices(MODELS,weights=weights,k=240-len(MODELS));rng.shuffle(model_sequence)
    dates=sorted(rng.sample(range(2500),240));pool={};records=[]
    for i,model in enumerate(model_sequence):
        dep,arr=rng.choices(demo_pairs,weights=[14,12,12,9,9,7,8,7,6,5,4,4]+[1]*20,k=1)[0]
        carrier='CA' if i<15 else ('BA' if i in [22,188] else rng.choices(['CA','CZ','TK'],weights=[10,7,2])[0])
        # Make two explicit fictional aircraft for photo-card layout examples.
        if i<15 or i in [40,80,120]:model='B737';carrier='CA'
        if i<15:reg='DEMO-001'
        elif i in [40,80,120]:reg='DEMO-002'
        else:
            pool.setdefault((carrier,model),[f'DEMO-{100+len(pool)*4+j:03d}' for j in range(4)])
            reg=rng.choice(pool[(carrier,model)])
        a,b=registry[dep],registry[arr];la,lb=map(math.radians,[a['lat'],b['lat']]);lo=math.radians(b['lon']-a['lon'])
        gc=6371*2*math.asin(min(1,math.sqrt(math.sin((lb-la)/2)**2+math.cos(la)*math.cos(lb)*math.sin(lo/2)**2)))
        km=round(gc*rng.uniform(1.01,1.13));minutes=round(gc/720*60+rng.uniform(35,75))
        day=(dt.date(2018,1,1)+dt.timedelta(days=dates[i])).isoformat()
        number=carrier+str(1100+demo_pairs.index((dep,arr))*7)
        records.append([day,number,'否',dep,arr,'','','','',minutes+10,minutes,km,model,reg,'','','','','',CARRIERS[carrier],f'SYNTH-{reg}', '2012-06-15'])
    headers=['日期','航班号','是否共享航班','出发机场','到达机场','表定出发','实际起飞','表定到达','实际降落','表定飞行时长','实际飞行时长','里程(公里)','机型','注册号','舱位等级','座位号','含税票价','登机方式','下机方式','实际承运航司','MSN','首次交付日期']
    with (work/'synthetic.csv').open('w',encoding='utf-8',newline='') as output:writer=csv.writer(output);writer.writerow(headers);writer.writerows(records)
    config={'distance_source':'export','report_kind':'diagnostic','name':'Demo Traveller','include_repeated':True,'include_retired':True,'bar_min':4,'route_min':4,'repeat_min':4,'png_scale':.7,'report_date':'2026-10-05','identity_confirmed':False,'airline_codes':{v:k for k,v in CARRIERS.items()},'logos':{k:paths[k] for k in CARRIERS},'logo_evidence':{k:{**proof[k],'accepted_by_user':True,'rights_confirmed':True} for k in CARRIERS},'photos':[{**proof[key],'file':paths[key],'registration':reg,'msn':'SYNTH-'+reg,'accepted_by_user':True,'rights_confirmed':True} for key,reg in [('featured','DEMO-001'),('retired','DEMO-002')]],'aircraft_status':[{'registration':'DEMO-002','msn':'SYNTH-DEMO-002','checked_on':'2026-10-05','permanent_passenger_exit':True,'last_passenger_date':'2024（演示）','status':'演示：改装货机','source':'Synthetic layout example, not a real aircraft lifecycle assertion'}]}
    config['alliance_memberships']=[{'carrier':'英国航空','alliance':'寰宇一家','from':'1999-02-01','through':'2026-10-03','checked_on':'2026-10-05','source':'https://www.oneworld.com/members/british-airways'}]
    config['airport_display_names']={'PVG':'上海浦东','HGH':'杭州萧山','SYX':'三亚凤凰','SIN':'新加坡樟宜','LHR':'伦敦希思罗','KIX':'大阪关西','NRT':'东京成田','BKK':'曼谷素万那普','CDG':'巴黎戴高乐','IST':'伊斯坦布尔','DXB':'迪拜国际','NNG':'南宁吴圩','NKG':'南京禄口','WUH':'武汉天河','URC':'乌鲁木齐地窝堡'}
    (work/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    if args.source:assert hashlib.sha256(args.source.read_bytes()).hexdigest()==source_hash
    (work/'privacy-check.json').write_text(json.dumps({'source_unchanged':True,'source_sha256':source_hash,'rows':240,'original_row_fields_copied':[],'source_information_used':'noisy model histogram only','synthetic_fields':headers,'original_photos_used':False},ensure_ascii=False,indent=2),encoding='utf-8')
    if args.render:
        subprocess.run([sys.executable,str(PLUGIN/'scripts/generate_report.py'),'--input',str(work/'synthetic.csv'),'--config',str(work/'config.json'),'--output',str(work/'report'),'--overwrite'],check=True)
        from PIL import Image
        public=PLUGIN/'docs/previews';public.mkdir(parents=True,exist_ok=True)
        for source,target in [('01_MY_FLIGHT_PASSPORT.png','flight-passport.png'),('02_FLIGHT_ATLAS.png','flight-atlas.png')]:
            # Decode/re-encode to strip text chunks, EXIF and filesystem metadata.
            with Image.open(work/'report'/source) as image:image.convert('RGB').save(public/target,optimize=True)
        manifest={'kind':'synthetic randomized demonstration','records':240,'original_row_fields_copied':[],'source_information_used':'noisy aircraft-model frequencies only','photos_note':'Real licensed aircraft photos illustrate layout only; fictional DEMO registrations and lifecycle labels do not identify the pictured aircraft.','report_images_license':'CC BY-SA 4.0','license_url':'https://creativecommons.org/licenses/by-sa/4.0/','assets':proof,'images':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in public.glob('*.png')}}
        (public/'provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'synthetic_records':len(records),'source_unchanged':True,'work':str(work),'rendered':args.render}))

if __name__=='__main__':main()
