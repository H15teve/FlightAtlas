import datetime as dt,json,math,re
from pathlib import Path
from zoneinfo import ZoneInfo
from build import BASE

def catalog(config):
    import airportsdata
    raw=airportsdata.load('IATA')
    airports={a:{'iata':a,'lat':p['lat'],'lon':p['lon'],'country':p['country'],'name':p['name'],'cn':p['name'],'tz':p['tz'],'icao':p['icao']} for a,p in raw.items()}
    old=json.loads((BASE/'assets/data/airport_registry.json').read_text(encoding='utf-8'))
    for a,p in old.items():airports[a]={**airports.get(a,{}),**p}
    # Closed/replaced airports disappear from current catalogs but remain historical destinations.
    for a,tz in {'TXL':'Europe/Berlin','SXF':'Europe/Berlin','NAY':'Asia/Shanghai','ZQZ':'Asia/Shanghai'}.items():
        if a in airports and not airports[a].get('tz'):airports[a]['tz']=tz
    aliases=json.loads((BASE/'assets/data/airport_aliases.json').read_text(encoding='utf-8'))
    names=json.loads((BASE/'assets/data/airport_display_names.json').read_text(encoding='utf-8'))
    for a,p in airports.items():
        aliases.setdefault(p['name'],a);aliases[a]=a
        p['cn']=names.get(a,p.get('cn',p['name']))
    for a,p in config.get('airports',{}).items():
        if not re.fullmatch('[A-Z]{3}',a):raise ValueError('机场补充代码无效')
        if not all(k in p for k in ['lat','lon','country','tz','cn']):raise ValueError('新增机场需要lat/lon/country/tz/cn')
        if not re.fullmatch('[A-Z]{2}',str(p['country'])):raise ValueError('机场country必须为ISO2代码')
        if not math.isfinite(float(p['lat'])) or not -90<=float(p['lat'])<=90 or not math.isfinite(float(p['lon'])) or not -180<=float(p['lon'])<=180:raise ValueError('机场经纬度无效')
        ZoneInfo(p['tz'])
        airports[a]={**airports.get(a,{}),**p,'iata':a};aliases[p['cn']]=a;aliases[a]=a
        airports[a]['lat']=float(p['lat']);airports[a]['lon']=float(p['lon'])
    aliases.update(config.get('airport_aliases',{}))
    if any(code not in airports for code in aliases.values()):raise ValueError('airport_aliases指向未定义机场；请同时补充airports元数据')
    return airports,aliases
def resolve_airport(value,aliases,airports):
    text=str(value or '').strip()
    if text in aliases:return aliases[text]
    code=text.upper()
    if code in airports:return code
    explicit=[a.upper() for a in re.findall(r'[\[(]([A-Za-z]{3})[\])]',text) if a.upper() in airports]
    if len(set(explicit))==1:return explicit[0]
    hits=[a for a in re.findall(r'(?<![A-Z])[A-Z]{3}(?![A-Z])',text) if a in airports]
    if len(set(hits))==1:return hits[0]
    raise ValueError('无法识别机场：'+text+'；在配置airport_aliases补充名称与三字码。')
def elapsed(row,registry,estimates):
    def clock(x):
        if isinstance(x,dt.datetime):return x.time()
        if isinstance(x,dt.time):return x
        if isinstance(x,(int,float)):
            n=round((x%1)*1440);return dt.time(n//60%24,n%60)
        if isinstance(x,str) and ':' in x:
            m=re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?',x)
            if m:return dt.time(*[int(v or 0) for v in m.groups()])
        return None
    explicit=row.get('minutes')
    if explicit is not None and str(explicit).strip() not in ['', '-', '—', '--']:
        text=str(explicit).strip()
        m=re.fullmatch(r'(?:(\d+)小时)?(?:(\d+)分(?:钟)?)?',text)
        if m and any(x is not None for x in m.groups()):
            hours,mins=m.groups()
            if hours is not None and mins is not None and int(mins)>=60:raise ValueError('飞行时长分钟部分无效')
            v=int(hours or 0)*60+int(mins or 0)
        else:
            v=float(explicit)
        if not math.isfinite(v) or not 0<v<3000:raise ValueError('飞行时长分钟值无效')
        proof={'basis':'input actual flight duration' if row.get('minutes_header')=='实际飞行时长' else 'input duration_minutes'}
        if row.get('minutes_header'):proof.update(header=row['minutes_header'],raw_value=explicit)
        return round(v),proof
    a,b=row['_dep'],row['_arr'];ta,tb=clock(row.get('departure_time')),clock(row.get('arrival_time'))
    if (ta and tb) and (not registry[a].get('tz') or not registry[b].get('tz')):raise ValueError('历史机场缺少IANA时区；请在配置airports提供核验后的tz')
    try:date=dt.date.fromisoformat(row['date'])
    except (ValueError,TypeError):date=None
    year=re.match(r'(\d{4})',str(row.get('date') or ''))
    if not date and year and int(year.group())>=1992 and ta and tb and registry[a].get('tz')==registry[b].get('tz')=='Asia/Shanghai':
        # China has no DST since 1992. Clock difference is valid without inventing a date.
        v=((tb.hour*60+tb.minute)-(ta.hour*60+ta.minute))%1440
        if v:return v,{'basis':'same fixed UTC+8 local times; partial date retained, no fabricated calendar date'}
    if date and ta and tb:
        def local_time(day,time,zone):
            naive=dt.datetime.combine(day,time);tz=ZoneInfo(zone)
            candidates={naive.replace(tzinfo=tz,fold=fold).astimezone(dt.timezone.utc) for fold in [0,1]}
            candidates={v for v in candidates if v.astimezone(tz).replace(tzinfo=None)==naive}
            if len(candidates)!=1:raise ValueError(f"行{row['row']}当地时间处于夏令时重复/不存在区间；需duration_minutes或核验UTC时刻。")
            return candidates.pop()
        dep=local_time(date,ta,registry[a]['tz'])
        fixed=row.get('arrival_date');days=[(dt.date.fromisoformat(fixed)-date).days] if fixed else range(-1,3)
        candidates=[]
        for day in days:
            arr=local_time(date+dt.timedelta(days=day),tb,registry[b]['tz']);minutes=round((arr-dep).total_seconds()/60)
            if 0<minutes<1440 or fixed and 0<minutes<3000:candidates.append((minutes,day))
        if len(candidates)==1:return candidates[0][0],{'basis':'airport local times, dated DST','arrival_day_offset':candidates[0][1],'departure_zone':registry[a]['tz'],'arrival_zone':registry[b]['tz']}
        raise ValueError(f"行{row['row']}跨日时长不唯一，需提供到达日期或duration_minutes。")
    matches=[x for x in estimates if x.get('date')==row['date'] and x.get('flight')==row['flight'] and x.get('route')==a+'-'+b]
    if len(matches)==1 and matches[0].get('source') and 0<float(matches[0].get('minutes',0))<3000:return round(float(matches[0]['minutes'])),{'basis':'explicit scheduled-duration estimate, not historical actual',**matches[0]}
    return None,{'basis':'missing duration; not inferred'}
def adapt(rows,config):
    registry,aliases=catalog(config);audit=[];minutes=0;missing=[];result=[]
    for r in rows:
        a=resolve_airport(r['departure'],aliases,registry);b=resolve_airport(r['arrival'],aliases,registry);r['_dep']=a;r['_arr']=b
        policy=config.get('duration_policy','actual-then-scheduled')
        has_actual=r.get('minutes') is not None and str(r['minutes']).strip() not in ['', '-', '—', '--']
        has_scheduled=r.get('scheduled_minutes') is not None and str(r['scheduled_minutes']).strip() not in ['', '-', '—', '--']
        if policy in ['actual-only','actual-then-scheduled'] and not has_actual:
            if policy=='actual-then-scheduled' and has_scheduled:
                scheduled={**r,'minutes':r['scheduled_minutes'],'minutes_header':r.get('scheduled_minutes_header','scheduled_duration_minutes')}
                n,proof=elapsed(scheduled,registry,[])
                proof.update(basis='input scheduled-duration fallback, not actual',source='input table: '+scheduled['minutes_header'])
            else:n,proof=None,{'basis':'missing provided duration; no clock reconstruction or timetable lookup'}
        else:n,proof=elapsed(r,registry,config.get('duration_estimates',[]))
        audit.append({'row':r['row'],'minutes':n,**proof})
        if n is None:missing.append(r['row'])
        else:minutes+=n
        result.append({'_row':r['row'],'_dep':a,'_arr':b,'_date':r['date'],'C':r.get('operating_flight') or r['flight'],'exported_flight':r['flight'],'N':r['model'],'AD':r['carrier'],'K':r['registration'],'Y':r['delivery'],'Q':str(r.get('msn') or ''),'H':r.get('distance_km',0)})
    visited={a for r in rows for a in [r['_dep'],r['_arr']]}
    return {'rows':result,'airports':{a:registry[a] for a in sorted(visited)},'duration':{'total_minutes':minutes,'complete':not missing,'display_available_sum':config.get('duration_policy')=='actual-only','missing_rows':missing,'estimated_segments':sum('source' in entry for entry in audit),'segments':audit}}
