import datetime as dt,json
from collections import Counter
from build import BASE
def alliance_stats(data):
    rules=json.loads((BASE/'assets/data/alliance_rules.json').read_text(encoding='utf-8'))
    custom=data.get('alliance_memberships',[])
    for m in custom:
        if not m.get('source') or m.get('alliance') not in ['星空联盟','天合联盟','寰宇一家','未加入三大联盟']:raise ValueError('联盟补充记录需官方来源和有效归属中文名称')
    rules['memberships']+=custom
    counts=Counter();audit=[];known_none=set(rules['non_alliance_carriers'])
    for r in data['rows']:
        memberships=[m for m in rules['memberships'] if m['carrier']==r['AD']];alliance='归属待核验'
        try:
            d=dt.date.fromisoformat(r['_date']);low=high=d
        except ValueError:
            if re_date:=str(r['_date'])[:4]:
                try:low=dt.date(int(re_date),1,1);high=dt.date(int(re_date),12,31)
                except ValueError:low=high=None
            else:low=high=None
        if r['AD'] in known_none and not memberships:alliance='未加入三大联盟'
        if memberships and low:
            hits=[];partial=False
            for m in memberships:
                start=dt.date.fromisoformat(m['from']);end=dt.date.fromisoformat(m.get('through','9999-12-31'))
                if low>=start and high<=end:hits.append(m['alliance'])
                elif low<=end and high>=start:partial=True
            hits=list(set(hits))
            if len(hits)>1:raise ValueError('联盟成员区间重叠且归属冲突')
            alliance=hits[0] if len(hits)==1 else '归属待核验' if partial else '未加入三大联盟'
        if high and high>dt.date.fromisoformat(rules['checked']):
            refreshed=[m['alliance'] for m in custom if m['carrier']==r['AD'] and low>=dt.date.fromisoformat(m['from']) and high<=dt.date.fromisoformat(m.get('through','9999-12-31')) and high<=dt.date.fromisoformat(m.get('checked_on',rules['checked']))]
            refreshed=set(refreshed)
            if len(refreshed)>1:raise ValueError('更新后的联盟归属冲突')
            alliance=next(iter(refreshed)) if refreshed else '归属待核验'
        counts[alliance]+=1;audit.append({'row':r['_row'],'alliance':alliance})
    return {'counts':counts,'segments':audit,'checked_on':rules['checked'],'basis':'flight-date full membership; unknown remains unknown'}
