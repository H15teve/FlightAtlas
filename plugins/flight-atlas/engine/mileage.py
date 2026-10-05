"""Opt-in public JAL TPM-based lookup; never fallback to geographic distance."""
import datetime as dt,hashlib,json,math,re,time,urllib.request,urllib.parse
from pathlib import Path
from xml.etree import ElementTree as ET
PAGE='https://www121.jal.co.jp/JmbWeb/JR/SectionMile_en.do'
ENDPOINT='https://www121.jal.co.jp/JmbWeb/JR/SectionMileCalc_en.do'
CITIES={'PEK':'BJS','PKX':'BJS','NAY':'BJS','PVG':'SHA','TFU':'CTU','XIY':'SIA','HND':'TYO','NRT':'TYO','JFK':'NYC','EWR':'NYC','LGA':'NYC','ICN':'SEL','GMP':'SEL','KIX':'OSA','ITM':'OSA','CTS':'SPK','LHR':'LON','LGW':'LON','LCY':'LON','CDG':'PAR','ORY':'PAR','DME':'MOW','SVO':'MOW','VKO':'MOW','TXL':'BER','SXF':'BER','DMK':'BKK','DWC':'DXB'}
def km(miles):return math.floor(float(miles)*1.609344+.5)
def validate_record(record):
    if not record.get('source') or not record.get('queried_on'):raise ValueError('TPM记录必须有来源与查询日期')
    v=record.get('tpm_miles')
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('TPM英里值无效')
    if record.get('basis')!='IATA TPM':raise ValueError('距离记录未明确IATA TPM依据')
    return record
def parse_response(raw,index):
    root=ET.fromstring(raw);mile=next((n for n in root.iter('MILE') if n.get('INDEX')==str(index)),None)
    if mile is None or mile.get('STATE')!='0' or not (mile.text or '').strip():return None
    text=(mile.text or '').replace(',','').strip()
    if not re.fullmatch('[0-9]+',text):return None
    names=[n.text for n in root.iter('CITY-NAME') if n.get('INDEX')==str(index)]
    return int(text),names
def apply_mileage(rows,mode,cache_path=None,online=False,city_overrides=None):
    if mode=='export-then-tpm':
        # Only absent values fall back. Malformed populated cells remain errors.
        missing=[r for r in rows if r.get('distance') is None or str(r.get('distance')).strip() in {'','-','—'}]
        present=[r for r in rows if r not in missing]
        audit=apply_mileage(present,'export')
        if missing:
            audit.extend({**record,'fallback_reason':'export mileage missing'} for record in apply_mileage(missing,'tpm',cache_path,online,city_overrides))
        order={r['row']:i for i,r in enumerate(rows)}
        return sorted(audit,key=lambda record:order[record['row']])
    if mode=='export':
        audit=[]
        for r in rows:
            raw=r.get('distance');match=re.fullmatch(r'\s*([0-9]+(?:\.[0-9]+)?)\s*(?:km|公里|千米)?\s*',str(raw if raw is not None else ''),re.I)
            if not match:raise ValueError(f"行{r['row']}原导出里程缺失/无效；请补充或选择TPM，不改用大圆距离。")
            v=float(match[1]);r['distance_km']=math.floor(v+.5);audit.append({'row':r['row'],'km':r['distance_km'],'basis':'user export'})
        return audit
    cities={**CITIES,**(city_overrides or {})};cache=Path(cache_path) if cache_path else None
    if not all(re.fullmatch('[A-Z]{3}',str(a)) and re.fullmatch('[A-Z]{3}',str(b)) for a,b in cities.items()):raise ValueError('机场和TPM城市代码均需大写三字码')
    records=json.loads(cache.read_text(encoding='utf-8')).get('records',{}) if cache and cache.exists() else {}
    if not isinstance(records,dict):raise ValueError('TPM缓存需为城市对索引对象；不能直接使用旧的航段查询缓存')
    pairs={tuple(sorted((cities.get(r['_dep'],r['_dep']),cities.get(r['_arr'],r['_arr'])))) for r in rows}
    missing=[p for p in sorted(pairs) if '-'.join(p) not in records]
    if missing and not online:raise ValueError('缺少城市TPM：'+', '.join('-'.join(p) for p in missing)+'；显式使用 --online-tpm 或提供带来源的缓存。')
    for pair in missing:
        body=urllib.parse.urlencode({'dep1':pair[0],'arr1':pair[1],**{f'{k}{i}':'' for i in range(2,10) for k in ['dep','arr']}}).encode()
        req=urllib.request.Request(ENDPOINT,data=body,headers={'Content-Type':'application/x-www-form-urlencoded','Referer':PAGE,'User-Agent':'FlightAtlas/0.1 (personal mileage query)'})
        try:
            with urllib.request.urlopen(req,timeout=20) as response:raw=response.read(256000)
            hit=parse_response(raw,1)
        except Exception as e:raise ValueError('TPM服务查询失败；保留缺失，不估算。') from e
        if hit is None:raise ValueError('TPM服务未返回有效城市距离：'+'-'.join(pair))
        miles,names=hit
        records['-'.join(pair)]={'tpm_miles':miles,'basis':'IATA TPM','source':PAGE,'queried_on':dt.date.today().isoformat(),'edition':'calculator revision not disclosed; not historical edition','returned_cities':names,'response_sha256':hashlib.sha256(raw).hexdigest()}
        if cache:
            cache.parent.mkdir(parents=True,exist_ok=True);temp=cache.with_suffix(cache.suffix+'.tmp');temp.write_text(json.dumps({'records':records},ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(cache)
        time.sleep(.7)
    audit=[]
    for r in rows:
        pair=tuple(sorted((cities.get(r['_dep'],r['_dep']),cities.get(r['_arr'],r['_arr']))));e=validate_record(records['-'.join(pair)])
        r['distance_km']=km(e['tpm_miles']);audit.append({'row':r['row'],'city_pair':list(pair),'km':r['distance_km'],**e})
    return audit
