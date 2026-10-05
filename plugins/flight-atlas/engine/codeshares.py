"""Match research evidence to codeshare rows; never accept candidates automatically."""
import datetime as dt
import re
from carriers import flight_key,flight_number
from reader import registration

def minute(value):
    match=re.fullmatch(r'(\d{1,2}):(\d{2})',str(value or '').strip())
    if not match or int(match[1])>23 or int(match[2])>59:return None
    return int(match[1])*60+int(match[2])

def clock_gap(a,b):
    a,b=minute(a),minute(b)
    if a is None or b is None:return None
    gap=abs(a-b)
    return min(gap,1440-gap)

def candidates(rows,evidence,tolerance=30):
    if not isinstance(tolerance,int) or isinstance(tolerance,bool) or not 0<=tolerance<=120:raise ValueError('时刻容差必须为0到120分钟')
    result=[]
    for row in rows:
        if row.get('codeshare') is not True:continue
        try:day=dt.date.fromisoformat(row['date'])
        except ValueError:day=None
        matches=[]
        operations=[]
        for fact in evidence.get('aircraft_operations',[]):
            if not all(fact.get(k) for k in ['registration','operator','from','through','source','msn']):continue
            if day and registration(fact['registration'])==row['registration'] and dt.date.fromisoformat(fact['from'])<=day<=dt.date.fromisoformat(fact['through']) and fact.get('relation')=='operating-carrier':operations.append(fact)
        for fact in operations:
            for schedule in evidence.get('schedules',[]):
                if not schedule.get('source') or schedule.get('date')!=row['date'] or schedule.get('operator')!=fact['operator']:continue
                if [schedule.get('departure'),schedule.get('arrival')]!=[row['_dep'],row['_arr']]:continue
                main=flight_number(schedule.get('flight'))
                if not re.fullmatch(r'[A-Z0-9]{2}\d+[A-Z]?',main) or main==flight_number(row['flight']):continue
                gaps=[clock_gap(row.get('scheduled_departure'),schedule.get('scheduled_departure')),clock_gap(row.get('scheduled_arrival'),schedule.get('scheduled_arrival'))]
                if any(gap is None or gap>tolerance for gap in gaps):continue
                matches.append({'key':flight_key(row),'operating_airline':fact['operator'],'operating_flight':main,'msn':fact['msn'],'aircraft_source':fact['source'],'schedule_source':schedule['source'],'scheduled_time_gaps_minutes':gaps,'confidence':'exact scheduled match' if max(gaps)==0 else 'near scheduled match','user_verified':False,'confirmed_on':None,'warnings':['租赁/湿租可能使机体运营人与航班承运人不同；须用户核验。']})
        unique={ (m['operating_airline'],m['operating_flight'],m['msn']):m for m in matches}
        matches=sorted(unique.values(),key=lambda m:(sum(m['scheduled_time_gaps_minutes']),m['operating_flight'],m['msn']))
        result.append({'key':flight_key(row),'row':row['row'],'date':row['date'],'exported_flight':row['flight'],'route':[row['_dep'],row['_arr']],'registration':row['registration'],'scheduled_departure':str(row.get('scheduled_departure') or ''),'scheduled_arrival':str(row.get('scheduled_arrival') or ''),'candidates':matches,'status':'requires_user_verification' if matches else 'no_sourced_match; ask user for evidence'})
    return result
