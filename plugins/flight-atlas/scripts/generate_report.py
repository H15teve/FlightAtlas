"""Local command-line entrypoint. No API key, telemetry, automatic network or writes to input."""
import argparse,copy,datetime as dt,hashlib,json,math,os,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from reader import read_flights
from data import adapt,catalog,resolve_airport
from mileage import apply_mileage
from build import stats
from design_v2 import passport_v2,atlas_v2
from carriers import apply_carriers
from identity import identity_defaults
from report_assets import requirements,apply_aircraft_details
from history import snapshot
def _local_asset(path,base,svg=False):
    p=(base/str(path)).resolve()
    if not p.is_file() or p.suffix.lower() not in (['.svg','.png','.jpg','.jpeg'] if svg else ['.png','.jpg','.jpeg']):raise ValueError('素材文件类型无效或不存在')
    if p.suffix.lower()=='.svg':
        text=p.read_text(encoding='utf-8')
        from defusedxml import ElementTree
        root=ElementTree.fromstring(text)
        if re.search(r'@import',text,re.I) or any(not ref.strip().strip('\"\x27').startswith('#') for ref in re.findall(r'url\((.*?)\)',text,re.I|re.S)):raise ValueError('SVG含外部样式引用')
        for element in root.iter():
            tag=element.tag.rsplit('}',1)[-1].lower()
            if tag in ['script','foreignobject','animate','animatetransform','set']:raise ValueError('SVG含活动内容')
            for k,v in element.attrib.items():
                k=k.rsplit('}',1)[-1].lower()
                if k.startswith('on'):raise ValueError('SVG含事件处理器')
                if k=='href' and not (v.startswith('#') or v.startswith('data:image/png;base64,') or v.startswith('data:image/jpeg;base64,')):raise ValueError('SVG含外部或嵌套活动引用')
    return str(p)
def run(args):
    config={};base=Path.cwd()
    if args.config:
        p=Path(args.config).resolve();config=json.loads(p.read_text(encoding='utf-8'));base=p.parent
        if not isinstance(config,dict):raise ValueError('配置必须是JSON对象')
    today=config.get('report_date',dt.date.today().isoformat());dt.date.fromisoformat(today)
    c={'title':'MY FLIGHT PASSPORT','name':'','valid_until':today,'age_as_of':today,'duration_policy':'actual-then-scheduled','report_kind':'final','include_repeated':True,'include_retired':False,'bar_min':3,'repeat_min':2,'png_scale':1.5,'node':'node',**config}
    for key in ['distance_source','bar_min','airport_bar_min','airline_bar_min','route_min','include_repeated','include_retired','name','signature_name','place_of_birth','place_of_issue','node']:
        value=getattr(args,key,None)
        if value is not None:c[key]=value
    c['valid_until']=today
    mode=c.get('distance_source','export')
    if mode not in ['export','tpm','export-then-tpm']:raise ValueError('distance_source必须是export、tpm或export-then-tpm')
    for key in ['bar_min','airport_bar_min','airline_bar_min','route_min','repeat_min']:
        if key in c and (isinstance(c[key],bool) or not isinstance(c[key],int) or c[key]<1):raise ValueError(key+'必须是正整数')
    for key in ['include_repeated','include_retired']:
        if not isinstance(c[key],bool):raise ValueError(key+'必须是真假值')
    for key in ['infer_airline_from_flight_number','flight_numbers_are_operating']:
        if key in c and not isinstance(c[key],bool):raise ValueError(key+'必须是真假值')
    if c.get('duration_policy','complete') not in ['complete','actual-only','actual-then-scheduled']:raise ValueError('duration_policy必须为complete、actual-only或actual-then-scheduled')
    if c['repeat_min']<2:raise ValueError('重复乘坐阈值至少为2')
    for k in ['valid_until','age_as_of']:dt.date.fromisoformat(c[k])
    if not isinstance(c['name'],str) or len(c['name'])>32:raise ValueError('身份姓名必须是至多32字符的字符串')
    if 'signature_name' in c and not isinstance(c['signature_name'],str):raise ValueError('signature_name必须是字符串；大小写按用户输入保留')
    if c['report_kind'] not in ['final','diagnostic']:raise ValueError('report_kind必须为final或diagnostic')
    if not 0.5<=float(c['png_scale'])<=3:raise ValueError('png_scale超出0.5至3范围')
    for k in ['logos','alliance_logos']:c[k]={name:_local_asset(p,base,True) for name,p in c.get(k,{}).items()}
    if c.get('signature_svg'):c['signature_svg']=_local_asset(c['signature_svg'],base,True)
    for photo in c.get('photos',[]):
        if not all(photo.get(k) for k in ['source','credit','license']):raise ValueError('照片需提供来源、作者、使用许可；不自动授权下载图片。')
        photo['file']=_local_asset(photo['file'],base)
    source=Path(args.input).resolve();before=hashlib.sha256(source.read_bytes()).hexdigest();rows,import_audit=read_flights(source,c.get('column_map'))
    if not rows:raise ValueError('没有有效航段')
    original_rows=copy.deepcopy(rows)
    adapt(rows,c)
    identity=identity_defaults(rows,today)
    for key,value in identity['values'].items():
        if key not in c:
            if value is None:raise ValueError('无法确定身份默认字段 '+key+'；请按预检建议询问用户')
            c[key]=value
    dt.date.fromisoformat(c['date_of_issue'])
    for key in ['place_of_birth','place_of_issue']:
        if c[key]!='—' and not re.fullmatch('[A-Z]{3}',c[key]):raise ValueError(key+'需机场三字码')
    carrier_audit=apply_carriers(rows,c)
    if any(e.get('codeshare') is True and not e.get('operating_flight') for e in carrier_audit):raise ValueError('共享航班尚未由用户核验执飞机司和主航班号；运行预检/候选匹配后确认')
    aircraft_audit=apply_aircraft_details(rows,c)
    cache=args.tpm_cache or c.get('tpm_cache')
    if cache:
        cache=str((base/str(cache)).resolve())
        if Path(cache)==source or Path(cache)==Path(args.config or '').resolve():raise ValueError('TPM缓存不能覆盖输入表或配置')
        c['tpm_cache']=cache
    mileage=apply_mileage(rows,mode,cache,args.online_tpm,c.get('city_codes'))
    data=adapt(rows,c);data['alliance_memberships']=c.get('alliance_memberships',[]);s=stats(data);s['duration']=data['duration']
    missing_assets=requirements(data,s,c)
    if missing_assets and c['report_kind']=='final':raise ValueError('正式报告缺少已确认素材；不可用文字或空白占位：'+json.dumps(missing_assets,ensure_ascii=False))
    output=Path(args.output).resolve()
    if output==source or source.parent==output:raise ValueError('输出目录不能与输入表目录相同，避免覆盖私人文件。')
    if output.exists() and any(output.iterdir()) and not args.overwrite:raise ValueError('输出目录非空；选择新目录或显式 --overwrite。')
    output.mkdir(parents=True,exist_ok=True)
    passport_v2(data,s,c,output);atlas_v2(data,s,c,output)
    if not args.svg_only:subprocess.run([c['node'],str(ROOT/'engine/render.mjs'),str(output),str(c['png_scale'])],check=True)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    s.pop('groups',None);s['input_sha256']=before;s['import']=import_audit;s['distance_source']=mode;s['mileage_audit']=mileage
    s['carrier_audit']=carrier_audit
    s['aircraft_enrichment_audit']=aircraft_audit
    s['identity']={'proposals':identity,'used':{k:c[k] for k in identity['values']},'confirmed_by_user':c.get('identity_confirmed',False)}
    s['asset_audit']={'report_kind':c['report_kind'],'missing':missing_assets,'logos':c.get('logo_evidence',{}),'photos':[{k:v for k,v in p.items() if k!='file'} for p in c.get('photos',[])]}
    s['data_policies']={k:c.get(k) for k in ['duration_policy','infer_airline_from_flight_number','flight_numbers_are_operating']}
    s['options']={k:c.get(k) for k in ['include_repeated','include_retired','bar_min','airport_bar_min','airline_bar_min','route_min']}
    s['notices']=['原始工作簿未修改。','内置联盟图标按单独许可分发；航司LOGO和照片仅按用户确认的来源与权利使用。','中国底图非带审图号标准地图；公开印刷需核验地图要求。']
    missing_ages=s['airframe_cards']['age_coverage']['selected_cards_missing_age']
    if missing_ages:s['notices'].append('机体状态核验不代表机龄完整；所选卡片缺交付依据：'+', '.join(missing_ages))
    if c['report_kind']=='diagnostic':s['notices'].append('诊断预览，不是正式成品；尚缺素材：'+str(len(missing_assets)))
    if not s['duration']['complete']:s['notices'].append('仅累计已提供的实际飞行时长，未计入缺失航段；不是全部飞行的完整时长。' if s['duration'].get('display_available_sum') else '起降时刻不足以累计全部飞行时长，护照显示—；请补duration_minutes或有来源的duration_estimates。')
    if s['duration']['estimated_segments']:s['notices'].append(str(s['duration']['estimated_segments'])+'个航段使用明确提供的表定时长估计，不是历史实际时长。')
    if c.get('infer_airline_from_flight_number'):s['notices'].append('缺失航司按航班号前缀识别；'+('用户确认这些均为实际承运航班号。' if c.get('flight_numbers_are_operating') else '未核验共享航班实际承运人。'))
    (output/'统计核验.json').write_text(json.dumps(s,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    credits={'alliances':json.loads((ROOT/'assets/alliances/provenance.json').read_text(encoding='utf-8')),'airline_logos':c.get('logo_evidence',{}),'photos':[{k:v for k,v in p.items() if k!='file'} for p in c.get('photos',[])]}
    (output/'素材许可与署名.json').write_text(json.dumps(credits,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    sources=import_audit.get('sources') or [{'sha256':before,'records':len(original_rows),'role':'primary input'}]
    (output/'flight-history.json').write_text(json.dumps(snapshot(original_rows,sources),ensure_ascii=False,indent=2),encoding='utf-8')
    saved_config=copy.deepcopy(c)
    (output/'report-config.json').write_text(json.dumps(saved_config,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'flights':s['flights'],'distance_km':s['distance'],'airports':len(s['wordcloud_layout']),'duration_complete':s['duration']['complete'],'report_kind':c['report_kind'],'output':str(output)},ensure_ascii=False))
def parser():
    p=argparse.ArgumentParser(description='FlightAtlas local flight-report generator')
    p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--config');p.add_argument('--distance-source',choices=['export','tpm','export-then-tpm']);p.add_argument('--tpm-cache');p.add_argument('--online-tpm',action='store_true',help='Only city pairs are sent to public JAL calculator, never rows or passenger data')
    for k in ['bar-min','airport-bar-min','airline-bar-min','route-min']:p.add_argument('--'+k,type=int)
    for k in ['include-repeated','include-retired']:p.add_argument('--'+k,action=argparse.BooleanOptionalAction,default=None)
    for k in ['name','signature-name','place-of-birth','place-of-issue','node']:p.add_argument('--'+k)
    p.add_argument('--svg-only',action='store_true');p.add_argument('--overwrite',action='store_true')
    return p
if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    try:run(parser().parse_args())
    except (ValueError,OSError,subprocess.CalledProcessError) as e:print('FlightAtlas: '+str(e),file=sys.stderr);sys.exit(2)
