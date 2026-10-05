"""Optional airline-code inference, never silently enabled for codeshares."""
import re
import hashlib

# A small template seed, not a worldwide or historical airline-code registry.
AIRLINES={'中国国航':'CA','厦门航空':'MF','海南航空':'HU','南方航空':'CZ','深圳航空':'ZH','东方航空':'MU','国泰航空':'CX','土耳其航空':'TK','埃塞俄比亚航空':'ET','山东航空':'SC','日本航空':'JL','捷蓝航空':'B6','美国联合':'UA','赞比亚航空':'ZN','赞比亚普罗飞航空':'P0','韩亚航空':'OZ','大韩航空':'KE','西部航空':'PN','黑山航空':'4O','越捷航空':'VJ','天津航空':'GS','昆明航空':'KY','维珍澳洲航空':'VA','澳门航空':'NX','全日空航空':'NH','河北航空':'NS','四川航空':'3U','中国联合航空':'KN'}

def flight_number(value):return ''.join(str(value or '').upper().split())

def flight_key(row):
    parts=[row['date'],flight_number(row['flight']),row.get('_dep',row.get('departure','')),row.get('_arr',row.get('arrival','')),row.get('registration',''),str(row.get('scheduled_departure') or ''),str(row.get('scheduled_arrival') or '')]
    return hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()

def apply_carriers(rows,config):
    mapping={code:name for name,code in AIRLINES.items()}
    mapping.update(config.get('flight_prefix_airlines',{}))
    if any(not re.fullmatch(r'[A-Z0-9]{2}',code) or not isinstance(name,str) or not name.strip() for code,name in mapping.items()):raise ValueError('flight_prefix_airlines需两位航司代码和非空名称')
    audit=[];resolutions=config.get('codeshare_resolutions',[])
    if not isinstance(resolutions,list) or any(not isinstance(r,dict) or not isinstance(r.get('key'),str) or not r['key'] for r in resolutions):raise ValueError('共享航班核验记录需列表、非空key及完整核验信息')
    if len({r['key'] for r in resolutions})!=len(resolutions):raise ValueError('共享航班核验记录键重复')
    for row in rows:
        basis='input airline field; operator verification depends on source'
        shared=row.get('codeshare');row['operating_flight']=None
        if shared is True:
            resolution=next((r for r in resolutions if r['key']==flight_key(row)),None)
            if resolution:
                if resolution.get('user_verified') is not True or not resolution.get('confirmed_on') or not resolution.get('aircraft_source') or not resolution.get('schedule_source'):raise ValueError('共享航班候选须有飞机/时刻表来源、确认日期和用户核验')
                import datetime as dt
                dt.date.fromisoformat(resolution['confirmed_on'])
                number=flight_number(resolution.get('operating_flight'))
                if not re.fullmatch(r'[A-Z0-9]{2}\d+[A-Z]?',number) or not resolution.get('operating_airline'):raise ValueError('共享航班核验缺少有效主航班号/执飞机司')
                row['carrier']=resolution['operating_airline'];row['operating_flight']=number
                basis='user-verified codeshare operator and main flight; dated aircraft and scheduled-time evidence'
            else:
                row['carrier']='未记录';basis='codeshare pending aircraft/schedule research and user verification'
            row['carrier_basis']=basis
            audit.append({'row':row['row'],'key':flight_key(row),'exported_flight':row['flight'],'operating_flight':row['operating_flight'],'codeshare':True,'airline':row['carrier'],'basis':basis})
            continue
        if row['carrier']=='未记录':
            basis='missing airline; not inferred'
            if shared is False or config.get('infer_airline_from_flight_number',False):
                number=flight_number(row['flight'])
                match=re.fullmatch(r'([A-Z0-9]{2})(\d+)[A-Z]?',number)
                code=match[1] if match else None
                if code in mapping:
                    row['carrier']=mapping[code]
                    basis='non-codeshare flight prefix from source flag' if shared is False else 'user-confirmed operating flight number prefix' if config.get('flight_numbers_are_operating') else 'flight number prefix inference; operator not verified'
                else:basis='unknown flight prefix; not inferred'
        row['carrier']=config.get('carrier_aliases',{}).get(row['carrier'],row['carrier'])
        row['carrier_basis']=basis
        row['operating_flight']=flight_number(row['flight']) if shared is False or config.get('flight_numbers_are_operating',False) else None
        audit.append({'row':row['row'],'airline':row['carrier'],'basis':basis,'codeshare':shared,'exported_flight':row['flight'],'operating_flight':row['operating_flight']})
    return audit
