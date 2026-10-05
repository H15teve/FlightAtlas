"""Source-derived passport proposals. Dates are never expanded from partial dates."""
import datetime as dt
import re
from collections import Counter

def _departure_order(row):
    match=re.fullmatch(r'(\d{1,2}):(\d{2})(?::\d{2})?',str(row.get('scheduled_departure') or '').strip())
    return int(match[1])*60+int(match[2]) if match and int(match[1])<24 and int(match[2])<60 else 1440

def identity_defaults(rows,today):
    dt.date.fromisoformat(today)
    dated=[r for r in rows if str(r.get('date',''))[:4].isdigit()]
    warnings=[];first=None
    if dated:
        first=min(dated,key=lambda r:(r['date'],_departure_order(r),r['row']))
    issue_date=None
    if first:
        try:issue_date=dt.date.fromisoformat(first['date']).isoformat()
        except ValueError:warnings.append('最早航班日期不完整；请用户提供Date of issue，不扩展为虚构日期。')
    else:warnings.append('没有可排序的航班日期；请用户指定首次飞行及日期。')
    if any(not r.get('date') for r in rows):warnings.append('部分航班无日期，最早航班候选需要用户核验。')
    visits=Counter(a for r in rows for a in [r['_dep'],r['_arr']])
    busiest=sorted(visits,key=lambda a:(-visits[a],a))[0] if visits else None
    return {'values':{'place_of_birth':first['_dep'] if first else None,'place_of_issue':busiest,'date_of_issue':issue_date,'valid_until':today},'basis':{'first_flight_row':first['row'] if first else None,'busiest_visits':visits.get(busiest),'airport_tie_break':'IATA alphabetical; user may override','same_day_first_flight':'scheduled departure then source row; user may override'},'warnings':warnings,'confirmation_required':True}
