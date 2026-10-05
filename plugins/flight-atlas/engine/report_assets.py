"""Final reports need real approved assets; diagnostics are explicitly non-final."""
from carriers import AIRLINES

def requirements(data,stats,config):
    missing=[]
    for name in stats['airlines']:
        code=config.get('airline_codes',{}).get(name,AIRLINES.get(name))
        if not code:
            missing.append({'kind':'airline_code','airline':name});continue
        proof=config.get('logo_evidence',{}).get(code,{})
        if not config.get('logos',{}).get(code) or not all(proof.get(k) for k in ['source','credit','license']) or proof.get('accepted_by_user') is not True or proof.get('rights_confirmed') is not True:
            missing.append({'kind':'airline_logo','airline':name,'code':code,'search_priority':['official Chinese/English wordmark','Wikipedia / Commons license page'],'geometry':'both max height and max width; center artwork, no tail-only crop'})
    photos={p['registration']:p for p in config.get('photos',[]) if p.get('accepted_by_user') is True and p.get('rights_confirmed') is True}
    if config.get('include_repeated',True):
        repeat=[(reg,n) for reg,n in stats['registrations'].most_common() if n>=config.get('repeat_min',2)]
        if repeat and repeat[0][0] not in photos:missing.append({'kind':'featured_aircraft_photo','registration':repeat[0][0],'search_priority':['Jetphotos registration + historical MSN','licensed Commons side-on photograph'],'geometry':'side-on, entire aircraft, comparable landscape aspect; preserve watermark'})
    if config.get('include_retired',False):
        for fact in config.get('aircraft_status',[]):
            if fact.get('permanent_passenger_exit') is True and fact.get('registration') in stats['registrations'] and fact['registration'] not in photos:missing.append({'kind':'retired_aircraft_photo','registration':fact['registration']})
    return missing

def apply_aircraft_details(rows,config):
    import datetime as dt
    from reader import registration,date_text
    audit=[]
    for fact in config.get('aircraft_details',[]):
        if fact.get('user_verified') is not True or not all(fact.get(k) for k in ['registration','msn','from','through','source']):raise ValueError('飞机补充资料需注册号/MSN/有效日期区间/来源及用户核验')
        start,end=dt.date.fromisoformat(fact['from']),dt.date.fromisoformat(fact['through'])
        if start>end:raise ValueError('飞机资料有效日期区间反向')
        reg=registration(fact['registration'])
        for row in rows:
            try:day=dt.date.fromisoformat(row['date'])
            except ValueError:continue
            if row['registration']!=reg or not start<=day<=end:continue
            if row.get('msn') and str(row['msn'])!=str(fact['msn']):raise ValueError('飞机补充MSN与原表冲突')
            row['msn']=str(fact['msn'])
            if fact.get('delivery_date'):
                value=date_text(fact['delivery_date']);dt.date.fromisoformat(value)
                if row.get('delivery') and row['delivery']!=value:raise ValueError('飞机补充交付日期与原表冲突')
                row['delivery']=value
            audit.append({'row':row['row'],'registration':reg,'msn':row['msn'],'source':fact['source'],'user_verified':True})
    return audit
