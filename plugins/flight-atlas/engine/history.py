"""Private reporting history, independent of enrichment and mileage conversion."""
import copy,datetime,hashlib,json,re
from reader import HEADERS
from carriers import flight_number
from data import catalog,resolve_airport,elapsed

EXTRA=['model_source','minutes_header','scheduled_minutes_header']

def records(rows):
    result=[]
    for row in rows:
        item={k:copy.deepcopy(v) for k,v in row.items() if k in HEADERS or k in EXTRA}
        result.append(item)
    # Date/time objects become their normal textual values; numeric clocks stay numeric.
    return json.loads(json.dumps(result,ensure_ascii=False,default=str,allow_nan=False))

def snapshot(rows,sources):
    return {'kind':'flightatlas-history','version':1,'records':records(rows),'sources':sources,
            'privacy':'Private reporting fields only; no seats, fares, tickets or passenger identifiers'}

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,default=str,allow_nan=False).encode()).hexdigest()

def present(value):return value is not None and str(value).strip().upper() not in ['', '-', '—', '--', 'NONE', 'NAN', '未记录']

def comparable(field,value):
    if not present(value):return None
    if field=='flight':return flight_number(value)
    if field in ['minutes','scheduled_minutes']:
        return elapsed({'minutes':value}, {}, [])[0]
    if field=='distance':
        try:return float(value)
        except (ValueError,TypeError):return str(value).strip()
    if field in ['departure_time','arrival_time','scheduled_departure','scheduled_arrival']:
        if isinstance(value,(int,float)):
            minutes=round((value%1)*1440);return f'{minutes//60%24:02d}:{minutes%60:02d}'
        found=re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?',str(value))
        if found:return f'{int(found[1]):02d}:{found[2]}'+(':'+found[3] if found[3] not in [None,'00'] else '')
    return str(value).strip()

def merge(existing,incoming,config,decisions=None):
    """Exact airport identities only. Conflicting overlaps need human decisions."""
    registry,aliases=catalog(config);merged=copy.deepcopy(existing);audit=[];used=set()
    decisions=decisions or []
    if not isinstance(decisions,list) or any(not isinstance(d,dict) or d.get('user_verified') is not True or not isinstance(d.get('id'),str) for d in decisions):raise ValueError('增量决定需要id和user_verified:true')
    if len({d['id'] for d in decisions})!=len(decisions):raise ValueError('增量决定id重复')
    choice={d['id']:d for d in decisions}
    def identity(row):
        return (str(row.get('date') or ''),flight_number(row['flight']),resolve_airport(row['departure'],aliases,registry),resolve_airport(row['arrival'],aliases,registry))
    for n,row in enumerate(incoming,1):
        key=identity(row)
        try:datetime.date.fromisoformat(key[0])
        except ValueError:raise ValueError('增量记录需要完整日期；请先核验，不自动猜测日期')
        matches=[i for i,old in enumerate(merged) if identity(old)==key]
        # A repeated key in the older history cannot be disambiguated by row order.
        if len(matches)>1:
            clock=comparable('scheduled_departure',row.get('scheduled_departure'))
            narrowed=[i for i in matches if clock is not None and comparable('scheduled_departure',merged[i].get('scheduled_departure'))==clock]
            if len(narrowed)==1:matches=narrowed
        possible=[]
        if not matches:
            for i,old in enumerate(merged):
                oldkey=identity(old)
                if oldkey[1]==key[1] and (oldkey[0]==key[0] or (not re.fullmatch(r'\d{4}-\d{2}-\d{2}',oldkey[0]) and oldkey[0][:4]==key[0][:4])):possible.append(i)
        differences={}
        if len(matches)==1:
            old=merged[matches[0]]
            for field in HEADERS:
                if field in ['departure','arrival','flight','date','status']:continue
                if present(row.get(field)) and comparable(field,row.get(field))!=comparable(field,old.get(field)):
                    differences[field]={'existing':old.get(field),'incoming':row.get(field)}
            if not differences:
                audit.append({'incoming_index':n,'key':key,'action':'duplicate-skipped','existing_index':matches[0]});continue
        elif not matches and not possible:
            merged.append(copy.deepcopy(row));audit.append({'incoming_index':n,'key':key,'action':'added'});continue
        candidates=matches or possible
        issue={'incoming_index':n,'key':key,'kind':'field-conflict' if len(matches)==1 else 'ambiguous-identity','differences':differences,
               'candidates':[{'existing_index':i,'record':records([merged[i]])[0]} for i in candidates],'incoming_record':records([row])[0]}
        issue['id']=digest(issue);decision=choice.get(issue['id'])
        if not decision:issue['action']='pending';audit.append(issue);continue
        used.add(issue['id']);action=decision.get('action')
        if action=='add-new':merged.append(copy.deepcopy(row))
        elif action in ['keep-existing','take-incoming']:
            index=decision.get('existing_index',candidates[0] if len(candidates)==1 else None)
            if isinstance(index,bool) or index not in candidates:raise ValueError('歧义记录需指定有效existing_index')
            if action=='take-incoming':
                for field in HEADERS:
                    if present(row.get(field)):merged[index][field]=copy.deepcopy(row[field])
                if present(row.get('model')):
                    merged[index]['model_source']=row.get('model_source',row.get('model'))
                for field in ['minutes_header','scheduled_minutes_header']:
                    if row.get(field):merged[index][field]=row[field]
        else:raise ValueError('增量决定action无效')
        issue['action']=action;issue['decision']=decision;audit.append(issue)
    if set(choice)-used:raise ValueError('增量决定过期或不匹配当前输入；请重新核验')
    return merged,{'previous_count':len(existing),'incoming_count':len(incoming),'merged_count':len(merged),
                   'added_count':sum(e['action'] in ['added','add-new'] for e in audit),
                   'duplicate_count':sum(e['action']=='duplicate-skipped' for e in audit),
                   'pending_count':sum(e['action']=='pending' for e in audit),'entries':audit}
