"""Shared vector primitives and report statistics."""
import json,math
from pathlib import Path
from collections import Counter
from html import escape
from models import FAMILIES,SHORT,manufacturer
BASE=Path(__file__).resolve().parents[1]
NAVY='#173552';TEAL='#438d91';GOLD='#b98b43';ORANGE='#cf713c';PAPER='#f8f5ec';MUTED='#64757e'
FONT='Microsoft YaHei, Noto Sans CJK SC, Arial, sans-serif';MONO='Consolas, Courier New, monospace'
class SVG:
    def __init__(self,w,h):
        self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs><pattern id="landHatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(24)"><path d="M0 0V7" stroke="#5daca8" stroke-width="2" opacity=".42"/></pattern></defs>']
    def add(self,s):self.parts.append(s)
    def rect(self,x,y,w,h,fill,rx=0,stroke='none',sw=1):self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def text(self,x,y,t,size=24,fill=NAVY,weight=400,anchor='start',spacing=0,font=None):self.add(f'<text x="{x}" y="{y}" font-family="{font or FONT}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}">{escape(str(t))}</text>')
    def line(self,x,y,x2,y2,color=TEAL,width=1,opacity=1,dash=''):self.add(f'<path d="M{x:.2f},{y:.2f}L{x2:.2f},{y2:.2f}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}" stroke-dasharray="{dash}"/>')
    def circle(self,x,y,r,fill,stroke='none',sw=1):self.add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    def save(self,path):path.write_text(''.join(self.parts)+'</svg>',encoding='utf-8')
def greatcircle(a,b):
    def xyz(p):la,lo=map(math.radians,[p['lat'],p['lon']]);return [math.cos(la)*math.cos(lo),math.cos(la)*math.sin(lo),math.sin(la)]
    p,q=xyz(a),xyz(b);angle=math.acos(max(-1,min(1,sum(x*y for x,y in zip(p,q)))));points=[];n=max(10,int(angle*35))
    for i in range(n+1):
        t=i/n;v=[(math.sin((1-t)*angle)*x+math.sin(t*angle)*y)/math.sin(angle) for x,y in zip(p,q)] if abs(math.sin(angle))>.00001 else p
        points.append([math.degrees(math.atan2(v[1],v[0])),math.degrees(math.atan2(v[2],math.hypot(v[0],v[1])))])
    return points
def stats(data):
    rows,reg=data['rows'],data['airports'];man=Counter();models=Counter();air=Counter();dep=Counter();arr=Counter();regs=Counter();regmodels={}
    for r in rows:
        code=r['N'];man[manufacturer(code)]+=1;models[code]+=1;air[r['AD']]+=1;dep[r['_dep']]+=1;arr[r['_arr']]+=1
        if r['K']:regs[r['K']]+=1;regmodels.setdefault(r['K'],code)
    groups={k:[] for k in ['AB','CD','EF','unknown']};covered=set()
    for key,title,codes,group,kind,length in FAMILIES:
        parts=[(c,models[c]) for c in codes.split() if models[c]];count=sum(n for c,n in parts)
        if count:groups[group].append((key,title,parts,count,kind));covered.update(c for c,n in parts)
    for c,n in models.items():
        if c not in covered:groups['unknown'].append((c,c,[(c,n)],n,'jet'))
    group_counts={k:sum(g[3] for g in v) for k,v in groups.items()};assert sum(group_counts.values())==len(rows)
    domestic=sum(all(reg[r[k]]['country']=='CN' for k in ['_dep','_arr']) for r in rows)
    regional=sum(all(reg[r[k]]['country'] in ['CN','HK','MO','TW'] for k in ['_dep','_arr']) and not all(reg[r[k]]['country']=='CN' for k in ['_dep','_arr']) for r in rows)
    unknown_carrier=air.pop('未记录',0)
    return dict(flights=len(rows),distance=sum(r['H'] for r in rows),manufacturers=man,models=models,airlines=air,unknown_carrier_flights=unknown_carrier,dep=dep,arr=arr,groups=groups,group_counts=group_counts,countries=sorted({reg[a]['country'] for a in dep|arr}),domestic=domestic,regional=regional,international=len(rows)-domestic-regional,registrations=regs,registration_models=regmodels)
