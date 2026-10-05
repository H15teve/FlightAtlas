import datetime as dt
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
    return facts,retired,{'as_of':config['age_as_of'],'coverage':{'known_registrations':len(facts),'verified_registrations':len(verified),'unverified_registrations':len(facts)-len(verified)}}
