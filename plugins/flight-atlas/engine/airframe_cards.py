import datetime as dt
from collections import Counter
from build import BASE
def load_cards(data,config):
    facts={};asof=dt.date.fromisoformat(config['age_as_of'])
    for r in data['rows']:
        reg=r['K']
        if not reg:continue
        try:age=round((asof-dt.date.fromisoformat(r['Y'])).days/365.2425,1)
        except (ValueError,TypeError):age=None
        if age is not None and age<0:raise ValueError('交付日期晚于统计截止日')
        f=facts.setdefault(reg,{'registration':reg,'msn':r['Q'],'delivery_date':r['Y'],'age':age,'age_as_of':config['age_as_of'],'model':r['N'],'carriers':[]})
        if r['Q'] and f['msn'] and r['Q']!=f['msn']:raise ValueError('同一注册号对应多个MSN，不能按注册号合并')
        if r['Q'] and not f['msn']:f['msn']=r['Q']
        if r['Y'] and f['delivery_date'] and r['Y']!=f['delivery_date']:raise ValueError('同一机体首次交付日期不一致')
        if age is not None and f['age'] is None:f.update(delivery_date=r['Y'],age=age)
        if r['AD'] not in f['carriers']:f['carriers'].append(r['AD'])
    ranges={}
    for evidence in config.get('aircraft_details', []):
        reg=evidence.get('registration');f=facts.get(reg)
        if not f or not evidence.get('delivery_date_range'):continue
        if evidence.get('user_verified') is not True or not evidence.get('delivery_source'):
            raise ValueError('交付日期区间需来源和用户核验')
        if str(evidence.get('msn'))!=str(f['msn']):raise ValueError('交付区间MSN不匹配')
        bounds=evidence['delivery_date_range']
        if not isinstance(bounds,list) or len(bounds)!=2:raise ValueError('交付日期区间需要两个日期边界')
        start,end=map(dt.date.fromisoformat,bounds)
        if not start<=end<=asof:raise ValueError('交付区间无效或晚于截止日')
        if reg in ranges and ranges[reg]!=(start,end):raise ValueError('同一机体交付区间不一致；先核验冲突')
        ranges[reg]=(start,end)
        if f['delivery_date']:
            if not start<=dt.date.fromisoformat(f['delivery_date'])<=end:
                raise ValueError('精确交付日期与交付区间冲突')
            continue
        low=round((asof-end).days/365.2425,1);high=round((asof-start).days/365.2425,1)
        f.update(delivery_date_range=[start.isoformat(),end.isoformat()],
                 delivery_source=evidence['delivery_source'],age_approximate=True,
                 age_interval=[low,high],age=low if low==high else None,
                 age_display=f'≈{low:.1f}' if low==high else f'{low:.1f}–{high:.1f}')
    for p in config.get('photos',[]):
        reg=p.get('registration')
        if reg not in facts:continue
        if not p.get('msn') or str(p['msn'])!=facts[reg]['msn']:raise ValueError('照片MSN与机体不匹配')
        facts[reg]['photo']=p
    retired=[];verified=set()
    for e in config.get('aircraft_status',[]):
        reg=e.get('registration')
        if reg not in facts:continue
        if not e.get('source') or not e.get('checked_on') or not e.get('msn') or str(e['msn'])!=facts[reg]['msn']:raise ValueError('机体状态需要匹配MSN、来源、核验日期')
        checked=dt.date.fromisoformat(e['checked_on'])
        if checked>asof:raise ValueError('状态核验日期晚于报告截止日')
        if e.get('permanent_passenger_exit') is True and e.get('status','').lower() in ['stored','封存','停场','active','在役']:raise ValueError('封存或停场不能据此确认永久退出客运')
        verified.add(reg)
        if e.get('permanent_passenger_exit') is True:
            if not e.get('last_passenger_date') or not e.get('status'):raise ValueError('退出客运记录缺少日期/日期精度或现状')
            retired.append({**facts[reg],**e})
    counts=Counter(r['K'] for r in data['rows'])
    repeated={reg for reg in facts if counts[reg]>=config.get('repeat_min',2)} if config.get('include_repeated',True) else set()
    selected=repeated|({r['registration'] for r in retired} if config.get('include_retired',False) else set())
    exact={reg for reg,f in facts.items() if f['delivery_date'] and f['age'] is not None}
    approximate={reg for reg,f in facts.items() if f.get('age_display')}
    missing=sorted(set(facts)-exact-approximate)
    age_coverage={'known_registrations':len(facts),'exact_delivery_registrations':len(exact),'approximate_delivery_registrations':len(approximate),'missing_delivery_registrations':missing,'selected_card_registrations':len(selected),'selected_cards_with_age':len(selected&(exact|approximate)),'selected_cards_missing_age':sorted(selected-set(exact)-approximate)}
    return facts,retired,{'as_of':config['age_as_of'],'coverage':{'known_registrations':len(facts),'verified_registrations':len(verified),'unverified_registrations':len(facts)-len(verified)},'age_coverage':age_coverage}
