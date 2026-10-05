import math,json,base64,datetime,subprocess,os,random,re
from pathlib import Path
from collections import Counter
from html import escape
from PIL import ImageFont,Image
from build import SVG,BASE,NAVY,TEAL,GOLD,ORANGE,PAPER,MUTED,SHORT,greatcircle,MONO,FONT
from fonts import font,font_path
from models import representative
PURPLE='#8371ae';BLUE='#326f9b'
from carriers import AIRLINES as AIRLINE_SEED
AIRLINES={**AIRLINE_SEED,'全日空':'NH','中国联合':'KN'}
AIRLINES.update({'中国联合航空':'KN','全日空航空':'NH'})
CACHE={}

def iata_metrics(name,size,weight=600,font=FONT):
    f=ImageFont.truetype(font_path(weight>=600,font.startswith('Arial')),size)
    return f.getlength(name),[f.getlength(name[:i]) for i in range(3)]

def iata(g,x,y,name,size=24,fill=NAVY,weight=600,anchor='start',font=FONT,central=False):
    width,positions=iata_metrics(name,size,weight,font)
    baseline=' dominant-baseline="central"' if central else ''
    g.add(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}" data-iata="{name}" data-width="{width}"{baseline}>{name}</text>')
def uri(path):
    path=Path(path)
    if path not in CACHE:
        mime={'.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}[path.suffix.lower()]
        CACHE[path]='data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()
    return CACHE[path]
def img(g,path,x,y,w,h,aspect='xMidYMid meet'):
    g.add(f'<image href="{uri(path)}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="{aspect}"/>')
def airline_logo(g,code,x,y,w,h):
    local=CACHE.get('logos',{}).get(code)
    if local:
        path=Path(local)
        limit=min(h,32 if h<=43 else 48)
        if path.suffix.lower()=='.svg':
            from defusedxml import ElementTree
            root=ElementTree.parse(path).getroot();box=root.get('viewBox')
            if box:bw,bh=list(map(float,box.replace(',',' ').split()))[2:]
            else:bw,bh=[float(re.match(r'[0-9.]+',root.get(k,'1')).group()) for k in ['width','height']]
        else:
            with Image.open(path) as source:bw,bh=source.size
        scale=min(limit/bh,w/bw)
        img(g,path,x+(w-bw*scale)/2,y+(h-bh*scale)/2,bw*scale,bh*scale)
        g.parts[-1]=g.parts[-1].replace('/>',f' data-airline-logo="{code}" data-max-height="{limit}" data-max-width="{w}"/>',1)
        return
    path=BASE/'assets/logos'/('4O_reference.png' if code=='4O' else f'{code}.png')
    chinese=BASE/'assets/logos'/f'{code}_cn.png'
    if chinese.exists():path=chinese
    wikipedia=BASE/'assets/logos'/f'{code}_wiki_v5.svg'
    if not path.exists() and not wikipedia.exists():
        g.rect(x,y,w,h,'#fffdf7',5)
        g.text(x+w/2,y+h/2+8,code,22,NAVY,600,'middle')
        return
    limit=min(h,32 if h<=43 else 48)
    if wikipedia.exists():
        raw=wikipedia.read_text(encoding='utf-8');root=re.search(r'<svg\b[^>]*>',raw).group()
        match=re.search(r'viewBox=[\"\x27]([^\"\x27]+)',root)
        if match:bw,bh=list(map(float,match.group(1).split()))[2:]
        else:bw,bh=[float(re.search(k+r'=[\"\x27]([0-9.]+)',root).group(1)) for k in ['width','height']]
        scale=min(limit/bh,w/bw)
        img(g,wikipedia,x+(w-bw*scale)/2,y+(h-bh*scale)/2,bw*scale,bh*scale)
    else:
        with Image.open(path) as source:
            iw,ih=source.size
            alpha=source.convert('RGBA').getchannel('A').point(lambda a:255 if a>10 else 0)
            left,top,right,bottom=alpha.getbbox()
        pad=2;bw=right-left+2*pad;bh=bottom-top+2*pad;scale=min(limit/bh,w/bw)
        g.add(f'<svg x="{x+(w-bw*scale)/2}" y="{y+(h-bh*scale)/2}" width="{bw*scale}" height="{bh*scale}" viewBox="{left-pad} {top-pad} {bw} {bh}" preserveAspectRatio="xMidYMid meet"><image href="{uri(path)}" x="0" y="0" width="{iw}" height="{ih}"/></svg>')
    closing='/>' if g.parts[-1].startswith('<image ') else '>'
    g.parts[-1]=g.parts[-1].replace(closing,f' data-airline-logo="{code}" data-max-height="{limit}" data-max-width="{w}"'+closing,1)
def alliance_logo(g,name,x,y,w,h):
    path=Path(CACHE.get('alliance_logos',{}).get(name) or BASE/'assets/alliances'/('star_vertical.svg' if name=='star' else f'{name}.svg'))
    if not path.exists():
        labels={'star':'STAR ALLIANCE','skyteam':'SKYTEAM','oneworld':'ONEWORLD'}
        g.text(x+w/2,y+h/2,labels[name],24,NAVY,600,'middle')
        return
    return img(g,path,x,y,w,h)
def borderless_world(g,data,x,y,w,h):
    sx=w/360;sy=h/142
    def pr(lo,la):return x+(lo+180)*sx,y+(84-la)*sy
    g.add(f'<defs><clipPath id="worldClipV2"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs><g clip-path="url(#worldClipV2)">')
    for f in json.loads((BASE/'assets/data/world.geojson').read_text(encoding='utf-8'))['features']:
        if f['properties'].get('ADMIN')=='Antarctica':continue
        geom=f['geometry'];polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            d=''.join('M'+'L'.join(f'{a:.2f},{b:.2f}' for a,b in (pr(*p[:2]) for p in ring))+'Z' for ring in poly if ring)
            g.add(f'<path d="{d}" fill="url(#landHatch)" fill-rule="evenodd" stroke="none"/>')
    routes=Counter(tuple(sorted((r['_dep'],r['_arr']))) for r in data['rows'])
    for (a,b),n in sorted(routes.items(),key=lambda q:q[1]):
        chunks=[];chunk=[];last=None
        for lo,la in greatcircle(data['airports'][a],data['airports'][b]):
            if last is not None and abs(lo-last)>180:
                if chunk:chunks.append(chunk)
                chunk=[]
            chunk.append(pr(lo,la));last=lo
        if chunk:chunks.append(chunk)
        d=''.join('M'+'L'.join(f'{x:.2f},{y:.2f}' for x,y in ch) for ch in chunks)
        g.add(f'<path d="{d}" fill="none" stroke="#c66d30" stroke-width="{1.4+.35*math.log1p(n):.2f}" opacity=".70"/>')
    for a in sorted({a for pair in routes for a in pair}):
        px,py=pr(data['airports'][a]['lon'],data['airports'][a]['lat']);g.circle(px,py,7,'#df5148','#a7222d',2)
    g.add('</g>')
def passport_v2(data,s,c,out):
    g=SVG(1600,2200)
    g.parts[0]=g.parts[0].replace('stroke="#5daca8"','stroke="#349ba4"').replace('stroke-width="2" opacity=".42"','stroke-width="2.5" opacity=".74"')
    g.rect(0,0,1600,2200,'#08277a',50);g.rect(1,30,1598,2140,'#fbfaf0',46)
    for y in range(70,2130,18):
        d='M'+'L'.join(f'{x},{y+7*math.sin(x/80+y/100):.2f}' for x in range(5,1600,12))
        g.add(f'<path d="{d}" fill="none" stroke="#a9c5b3" stroke-width="1" opacity=".17"/>')
    # Repeated pastel icons and IATA codes form the reference-style security ribbon.
    colors=['#bcb0db','#9fc9df','#97dace','#edc9c6']
    popular=[a for a,n in (s['dep']+s['arr']).most_common()]
    ribbon=[c[k] if c[k]!='—' else popular[min(i,len(popular)-1)] for i,k in enumerate(['place_of_birth','place_of_issue'])]
    for i in range(22):
        x=50+i*70;color=colors[(i//4)%4]
        if i%6==4:iata(g,x+40,120,ribbon[0] if i%12==4 else ribbon[1],32,color,600,'middle',central=True)
        elif i%6!=5:
            g.add(f'<g transform="translate({x},120) rotate(-12) scale(.7)" fill="{color}"><path d="M-22,-3L-4,-3L-8,-20L-3,-20L8,-3L22,-2Q30,0 22,2L8,3L-3,20L-8,20L-4,3L-22,3L-26,10L-30,10L-28,0L-30,-10L-26,-10Z"/></g>')
    borderless_world(g,data,15,205,1570,820)
    countries=s['countries'];step=min(79,1430/max(1,len(countries)));start=800-(len(countries)-1)*step/2
    for i,cc in enumerate(countries):
        x=start+i*step;path=BASE/'assets/round-flags'/f'{cc}.svg'
        g.circle(x,1104,33,'white')
        # Purpose-designed circular artwork: no extra clipping or shifted viewport.
        if path.exists():img(g,path,x-31,1073,62,62)
        else:g.text(x,1114,cc,24,TEAL,600,'middle')
    g.line(65,1170,1535,1170,TEAL,1,.2,dash='10 10')
    g.text(65,1282,c['title'],66,'#122478',400,spacing=2)
    if c.get('signature_svg'):img(g,Path(c['signature_svg']),1035,1216,500,134)
    elif c.get('name'):
        g.text(1535,1316,c['name'],min(108,560/max(1,len(c['name']))*1.4),'#122478',400,'end',font='Vivaldi, URW Chancery L, cursive')
    g.rect(66,1312,54,31,'#444d48',3);g.circle(93,1327,10,'none','#fbfaf0',2);g.line(67,1327,119,1327,'#fbfaf0',2)
    g.text(136,1338,'PASSPORT • PASS • PASAPORTE',30,'#4f5550',600)
    g.text(65,1564,s['flights'],220,'#222724',600);g.text(68,1693,'flights',112,'#5661a1',300)
    fields=[('Place of birth',c['place_of_birth']),('Place of issue',c['place_of_issue']),('Date of issue',datetime.date.fromisoformat(c['date_of_issue']).strftime('%d %b %Y').upper()),('Valid until',datetime.date.fromisoformat(c['valid_until']).strftime('%d %b %Y').upper())]
    for i,(label,value) in enumerate(fields):
        yy=1466+i*81;g.text(585,yy,label,34,'#5965a7')
        if label in ['Place of birth','Place of issue']:
            iata(g,994,yy,value,35,'#454b49',400,'start')
            g.parts[-1]=g.parts[-1].replace('<text ','<text data-passport-field-code="true" ',1)
        else:g.text(994,yy,value,35,'#454b49')
    minutes=s['duration']['total_minutes'];days=minutes//1440;hours=minutes%1440//60;mins=minutes%60
    numberfont=font(67,True)
    unitfont=font(67)
    def mixed(x,segments):
        for value,unit in segments:
            g.text(x,1934,value,67,'#222724',600)
            x+=numberfont.getlength(str(value))+10
            g.text(x,1934,unit,67,'#454b49',300)
            x+=unitfont.getlength(unit)+16
    for x,label in [(65,'Distance'),(653,'Flight Time'),(1080,'Airports'),(1330,'Airlines')]:g.text(x,1850,label,34,'#5965a7')
    mixed(65,[(f"{s['distance']:,}",'km')])
    if s['duration'].get('complete',True) or s['duration'].get('display_available_sum'):mixed(653,[(days,'d'),(hours,'h')])
    else:g.text(653,1934,'—',67,'#222724',600)
    g.text(1080,1934,len(s['dep']|s['arr']),76,'#222724',600);g.text(1330,1934,len(s['airlines']) if not s.get('unknown_carrier_flights') else '—',76,'#222724',600)
    g.line(65,2010,1535,2010,TEAL,1,.18)
    issued=datetime.date.fromisoformat(c['date_of_issue']).strftime('%d%b%y').upper();valid=datetime.date.fromisoformat(c['valid_until']).strftime('%d%b%y').upper()
    name=re.sub('[^A-Z ]','',c.get('name','').upper()).split();mrzname='<'.join(name)[:24]
    groups=[['ALLTIME',mrzname,'BORN<'+c['place_of_birth'],'MY<FLIGHT<PASSPORT'],['ISSUE<'+issued,'PLACE<'+c['place_of_issue'],'VALID<'+valid,mrzname]]
    lines=[]
    for fields in groups:
        # Spread filler BETWEEN information groups, not in a trailing block.
        slots=max(9,64-sum(map(len,fields)));q,r=divmod(slots,len(fields)-1)
        lines.append(''.join(t+('<'*(q+(j<r)) if j<len(fields)-1 else '') for j,t in enumerate(fields)))
    s['passport_layout']={'mrz_lines':lines,'flag_count':len(countries),'flag_size':62,'flag_y':1073,'flag_bottom':1135,'flag_extra_clip':False,'world_map_box':[15,205,1570,820],'world_map_projection_scales':[1570/360,820/142],'signature':c.get('name',''),'signature_box':[1035,1216,500,134],'unit_font_size':67}
    for i,t in enumerate(lines):
        chars=''.join(f'<tspan x="{65+j*1450/(len(t)-1):.2f}">{escape(ch)}</tspan>' for j,ch in enumerate(t))
        g.add(f'<text y="{2078+i*53}" font-family="Consolas, monospace" font-size="31" fill="#657371">{chars}</text>')
    g.save(out/'01_MY_FLIGHT_PASSPORT.svg')

def plane(g,item,x,y,w,h,color,layout):
    key,title,parts,n,kind=item
    g.rect(x,y,w,h,'#fffdf7',12,'#e3e7df',1)
    spec=layout[key];vx,vy,vw,vh=spec['viewBox'];iw=w-34;ih=h-87
    physical=json.loads((BASE/'assets/data/aircraft_dimensions.json').read_text(encoding='utf-8'))
    length=representative(key,parts)['length_m'];target=physical['pixels_per_metre']*length
    scale=min(target/vw,iw/vw,ih/vh)
    ix=x+17+(iw-vw*scale)/2;iy=y+17+(ih-vh*scale)/2
    # One approximate physical length scale across every category; no stretching.
    clip=f'<defs><clipPath id="planeClip_{key}"><path d="{spec["clip"]}"/></clipPath></defs>' if spec.get('clip') else ''
    attr=f' clip-path="url(#planeClip_{key})"' if clip else ''
    g.add(f'<svg x="{ix}" y="{iy}" width="{vw*scale}" height="{vh*scale}" viewBox="{vx} {vy} {vw} {vh}" overflow="hidden" data-plane="{key}">{clip}<use href="#atlas_{spec["file"]}" filter="url(#alphaClean)"{attr}/></svg>')
    title={'E195':'Embraer E190','DH8D':'Dash 8'}.get(key,title)
    g.text(x+18,y+h-51,title,22,color,600);g.text(x+w-18,y+h-49,n,39,color,600,'end')
    labels=[f'{SHORT.get(code,code)} ×{count}' for code,count in parts]
    line=' · '.join(labels);labelfont=font(17)
    size=min(17,17*(w-36)/max(1,labelfont.getlength(line)))
    g.text(x+18,y+h-15,line,round(size,2),MUTED)
    g.parts[-1]=g.parts[-1].replace('<text ',f'<text data-model-subtypes="{key}" ',1)

def wordcloud(g,rank,x,y,w,h):
    boxes=[];rng=random.Random(200);placements=[];draw=[]
    fontpath=font_path(True,True)
    for i,(name,n) in enumerate(rank):
        size=round(35*math.log2(n+1));angle=90 if i%7==5 and i>5 else 0
        for attempt in range(1):
            font=ImageFont.truetype(str(fontpath),size);bb=font.getbbox(name);tw=bb[2]-bb[0]+8;th=bb[3]-bb[1]+12
            if angle:tw,th=th,tw
            chosen=None
            for step in range(9000):
                t=step*.11;radius=1.6*math.sqrt(step)*5
                cx=x+w/2+radius*math.cos(t);cy=y+h/2+radius*1.1*math.sin(t)
                box=(cx-tw/2-8,cy-th/2-8,cx+tw/2+8,cy+th/2+8)
                if box[0]<x or box[2]>x+w or box[1]<y or box[3]>y+h:continue
                if any(box[0]<b[2] and box[2]>b[0] and box[1]<b[3] and box[3]>b[1] for b in boxes):continue
                chosen=(cx,cy,box);break
            if chosen:break
        if not chosen:
            # The spiral has a fixed radius. Wider fonts can fill that area
            # while leaving usable space elsewhere in a growing panel.
            half_w=tw/2+8;half_h=th/2+8
            xs={x+half_w,x+w-half_w};ys={y+half_h,y+h-half_h}
            for b in boxes:
                xs.update((b[0]-half_w,b[2]+half_w))
                ys.update((b[1]-half_h,b[3]+half_h))
            candidates=sorted(((cx,cy) for cx in xs for cy in ys
                if x+half_w<=cx<=x+w-half_w and y+half_h<=cy<=y+h-half_h),
                key=lambda p:((p[0]-x-w/2)**2+(p[1]-y-h/2)**2,p[1],p[0]))
            for cx,cy in candidates:
                box=(cx-half_w,cy-half_h,cx+half_w,cy+half_h)
                if any(box[0]<b[2] and box[2]>b[0] and box[1]<b[3] and box[3]>b[1] for b in boxes):continue
                chosen=(cx,cy,box);break
        if not chosen:raise ValueError('词云空间不足：'+name)
        cx,cy,box=chosen;boxes.append(box);color=[NAVY,BLUE,TEAL,GOLD,PURPLE][i%5]
        draw.append((cx,cy,color,name,size,angle))
        placements.append({'airport':name,'visits':n,'font_size':size,'angle':angle,'box':box})
    # Fill the same vertical span as the adjacent bars by spacing centers only.
    # Font sizes stay logarithmic; expanding center distances cannot add overlaps.
    target=h-18
    def span(scale):
        lo=min(scale*cy-(b[3]-b[1])/2 for (_,cy,*_),b in zip(draw,boxes))
        hi=max(scale*cy+(b[3]-b[1])/2 for (_,cy,*_),b in zip(draw,boxes))
        return lo,hi
    low,high=1,1
    # One word cannot be expanded by spacing its center; avoid an infinite loop.
    if len(draw)>1:
        while span(high)[1]-span(high)[0]<target and high<1000:high*=1.1
    if span(1)[1]-span(1)[0]<=target:
        for _ in range(40):
            mid=(low+high)/2
            if span(mid)[1]-span(mid)[0]<target:low=mid
            else:high=mid
    else:high=1
    if len(draw)==1:high=1
    offset=y-span(high)[0]
    for p,(cx,cy,color,name,size,angle),box in zip(placements,draw,boxes):
        ny=high*cy+offset;delta=ny-cy
        p['box']=[box[0],box[1]+delta,box[2],box[3]+delta]
        g.add(f'<g transform="translate({cx:.2f},{ny:.2f}) rotate({angle})"><text text-anchor="middle" dominant-baseline="central" font-family="Arial" font-weight="700" font-size="{size}" fill="{color}">{name}</text></g>')
    return placements

def airport_panel(rank,bar_rank):
    """Compact shared columns without shrinking v3 words or dropping airports."""
    count=len(bar_rank);code_size=30 if count<=12 else 28 if count<=24 else 25
    pitch=62 if count<=24 else 56
    height=max(360,(count-1)*pitch+60)
    class Layer:
        def __init__(self):self.parts=[]
        def add(self,text):self.parts.append(text)
    for _ in range(100):
        layer=Layer()
        try:
            placements=wordcloud(layer,rank,1190,0,1110,height)
            return {'height':height,'code_size':code_size,'name_size':code_size-3,'pitch':pitch,'layer':layer.parts,'placements':placements}
        except ValueError as error:
            if not str(error).startswith('词云空间不足'):raise
            height+=80
    raise ValueError('机场数量超出词云排版容量')

def airline_bar_geometry(counts):
    count_x=790;bar_x=430;gap=20
    label_width=max((font(26,True).getlength(str(n)) for n in counts),default=0)
    width=min(270,count_x-bar_x-label_width-gap)
    if width<=0:raise ValueError('航司次数超出排版容量')
    return {'bar_x':bar_x,'bar_width':width,'count_x':count_x,'count_left':count_x-label_width,'minimum_gap':gap}

def airline_panel(repeated_count,single_count,unknown=False):
    """Keep the logo grid near the bars; let large inventories grow downward."""
    pitch=64 if repeated_count<=8 else 52
    caption=104+repeated_count*pitch+24+(48 if unknown else 0)
    grid_top=caption+52;rows=math.ceil(single_count/4)
    bottom=grid_top+(rows-1)*90+76 if rows else caption+28
    return {'row_pitch':pitch,'grid_caption':caption,'grid_top':grid_top,
            'single_rows':rows,'content_bottom':bottom,'height':max(1300,bottom+52)}

def atlas_v2(data,s,c,out):
    from domestic_map import build_map
    from airframe_cards import load_cards
    facts,retired,lifecycle=load_cards(data,c)
    CACHE['logos']=c.get('logos',{});CACHE['alliance_logos']=c.get('alliance_logos',{})
    airport_names=json.loads((BASE/'assets/data/airport_display_names.json').read_text(encoding='utf-8'));airport_names.update(c.get('airport_display_names',{}))
    bar_min=c.get('bar_min',3);air_min=c.get('airline_bar_min',bar_min)
    repeated_air=[(a,n) for a,n in s['airlines'].most_common() if n>=air_min];single_air=[a for a,n in s['airlines'].most_common() if n<air_min]
    for a in s['airlines']:
        AIRLINES[a]=c.get('airline_codes',{}).get(a,AIRLINES.get(a,a[:8]))
    repeats=[(a,n) for a,n in s['registrations'].most_common() if n>=c.get('repeat_min',2)] if c.get('include_repeated',True) else []
    if not c.get('include_retired',False):retired=[]
    rank=(s['dep']+s['arr']).most_common();bar_rank=[(a,n) for a,n in rank if n>=c.get('airport_bar_min',bar_min)]
    airport_panel_layout=airport_panel(rank,bar_rank)
    airport_height=airport_panel_layout['height']+80
    regional_rows=math.ceil(len(s['groups']['AB'])/5);narrow_rows=math.ceil(len(s['groups']['CD'])/4);wide_rows=math.ceil(len(s['groups']['EF'])/3)
    model_end=470+regional_rows*228+76+narrow_rows*256+76+wide_rows*316+76+(80 if s['groups']['unknown'] else 0)
    # Both columns share an exact top and bottom; the map grows with logo rows.
    airline_panel_layout=airline_panel(len(repeated_air),len(single_air),bool(s.get('unknown_carrier_flights')))
    airline_height=airline_panel_layout['height']
    map_height=airline_height-145
    s['map']=build_map(data,out,height=map_height,route_min=c.get('route_min',bar_min))
    map_height=s['map']['height'];airline_height=map_height+145
    subprocess.run([c.get('node','node'),str(BASE/'engine/render_map.mjs'),str(out)],check=True)
    alliance_start=model_end+airline_height+70
    airport_start=alliance_start+340;repeat_start=airport_start+airport_height+130
    # The most-used airframe spans two vertical card slots; remaining cards
    # use all other slots, including the second row beside its photograph.
    # Reserve the entire first column for a vertically centered featured card.
    # Otherwise a third row's col-0 card overlaps its photograph after centering.
    repeat_slots=[1+i%6+(i//6)*7 for i in range(len(repeats)-1)]
    repeat_rows=max(2,math.ceil((max(repeat_slots,default=0)+1)/7)) if repeats else 0
    def photo_height(f):
        if not f.get('photo'):return 178
        with Image.open(BASE/'assets/photos'/f['photo']['file']) as source:return 274*source.height/source.width
    featured_height=118+photo_height(facts[repeats[0][0]])+12 if repeats else 0
    repeat_height=max(featured_height,repeat_rows*134-12)
    repeat_offset=max(0,(featured_height-(repeat_rows*134-12))/2)
    featured_offset=max(0,((repeat_rows*134-12)-featured_height)/2)
    retired_start=repeat_start+96+repeat_height+60 if repeats else repeat_start
    retired_height=max((147+photo_height(f)+12 for f in retired),default=338)
    height=math.ceil(retired_start+(96+math.ceil(len(retired)/7)*(retired_height+16)+80 if c.get('include_retired',False) else 80))
    g=SVG(2400,height);g.rect(0,0,2400,height,PAPER);g.rect(0,0,2400,15,NAVY)
    layout=json.loads((BASE/'assets/silhouettes/layout_v7.json').read_text(encoding='utf-8'))
    g.add('<defs><filter id="alphaClean" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="discrete" tableValues="0 0 0 0 0 0 0 0 0 1"/></feComponentTransfer></filter>')
    active={item[0] for group in ['AB','CD','EF'] for item in s['groups'][group]}
    s['aircraft_representatives']={item[0]:representative(item[0],item[2]) for group in ['AB','CD','EF'] for item in s['groups'][group]}
    for file in sorted(set(layout[key]['file'] for key in active)):
        spec=next(e for e in layout.values() if e['file']==file)
        g.add(f'<image id="atlas_{file}" href="{uri(BASE/"assets/silhouettes"/file)}" width="{spec["width"]}" height="{spec["height"]}"/>')
    g.add('</defs>')
    titlefont=font(124)
    atlas_x=80+titlefont.getlength('FLIGHT')+5*2+42
    atlas_width=titlefont.getlength('ATLAS')*1.055+4*7
    g.add(f'<text x="80" y="160" font-family="{FONT}" font-size="124" font-weight="400" fill="#122478" data-custom-title="flight-atlas"><tspan letter-spacing="2">FLIGHT </tspan><tspan x="{atlas_x}" letter-spacing="7" textLength="{atlas_width}" lengthAdjust="spacingAndGlyphs" stroke="#122478" stroke-width=".6" stroke-linejoin="round">ATLAS</tspan></text>')
    g.line(80,212,2320,212,NAVY,1,.25)
    g.text(80,268,'AIRCRAFT MANUFACTURERS / 客机制造商',33,NAVY,600)
    manufacturers=s['manufacturers'].most_common();mw=2240/len(manufacturers)
    mfont=min(29,min(29*(mw-18)/max(1,font(29,True).getlength(m)) for m,n in manufacturers))
    for i,(m,n) in enumerate(manufacturers):
        x=80+i*mw;g.text(x,324,m,mfont,NAVY,600);g.text(x,390,n,52,TEAL,600)
    cursor=440
    for key,title,color,cols in [('AB','REGIONAL / 支线客机',PURPLE,5),('CD','NARROW-BODY / 窄体干线客机',BLUE,4),('EF','WIDE-BODY / 宽体干线客机',GOLD,3)]:
        g.text(80,cursor+36,f"{title}    {s['group_counts'][key]} 次",29,color,600);cursor+=58
        cw=2240/cols
        step,card_height=(316,300) if key=='EF' else (256,240) if key=='CD' else (228,212)
        for i,item in enumerate(s['groups'][key]):plane(g,item,80+i%cols*cw,cursor+i//cols*step,cw-15,card_height,color,layout)
        cursor+=math.ceil(len(s['groups'][key])/cols)*step+18
    if s['groups']['unknown']:
        missing=' · '.join(f'{item[0]} ×{item[3]}' for item in s['groups']['unknown'])
        g.text(80,cursor+25,'机型未记录或待匹配：'+missing,23,MUTED)
    top=model_end;g.line(80,top,2320,top,NAVY,1,.25)
    g.text(80,top+63,'OPERATING AIRLINES / 实际承运航司',33,NAVY,600)
    g.text(850,top+63,'DOMESTIC ROUTES / 国内航线',33,NAVY,600)
    g.text(850,top+109,f"{s['domestic']+s['regional']} 次飞行  ·  {s['map']['domestic_route_count']} 条航线",25,MUTED)
    maxcount=max(s['airlines'].values(),default=1)
    airline_geometry=airline_bar_geometry([n for _,n in repeated_air])
    s['airline_bar_layout']=airline_geometry
    s['airline_panel_layout']=airline_panel_layout
    pitch=airline_panel_layout['row_pitch']
    if s.get('unknown_carrier_flights'):g.text(80,top+104+len(repeated_air)*pitch+26,f"{s['unknown_carrier_flights']} 次飞行的承运航司未记录",24,MUTED)
    for i,(name,n) in enumerate(repeated_air):
        yy=top+104+i*pitch;airline_logo(g,AIRLINES[name],80,yy-5,135,43)
        g.text(228,yy+24,name,min(21,21*190/max(1,font(21).getlength(name))),NAVY,500)
        g.rect(airline_geometry['bar_x'],yy+5,airline_geometry['bar_width']*n/maxcount,24,TEAL,4)
        g.parts[-1]=g.parts[-1].replace('<rect ',f'<rect data-airline-bar-index="{i}" ',1)
        g.text(airline_geometry['count_x'],yy+26,n,26,NAVY,600,'end')
        g.parts[-1]=g.parts[-1].replace('<text ',f'<text data-airline-count-index="{i}" ',1)
    # Follow the bars instead of leaving a map-sized gap above sparse logos.
    sy=top+airline_panel_layout['grid_caption']
    if single_air:g.text(80,sy+26,'以下航司均仅搭乘过一次' if all(s['airlines'][a]==1 for a in single_air) else f'以下航司搭乘次数均少于{air_min}次',24,MUTED,500)
    for i,name in enumerate(single_air):
        xx=80+i%4*176;yy=sy+52+i//4*90;code=AIRLINES[name]
        g.rect(xx,yy,160,76,'#fffdf7',9)
        airline_logo(g,code,xx+8,yy+6,144,64)
    # Same paper background as the poster, highlight the China landmass only.
    img(g,out/'国内航线.svg',835,top+145,1485,map_height,'none')
    from alliances import alliance_stats
    s['alliances']=alliance_stats(data)
    g.line(80,alliance_start,2320,alliance_start,NAVY,1,.18)
    g.text(80,alliance_start+54,'AIRLINE ALLIANCES / 航空联盟',31,NAVY,600)
    alliance_items=[('星空联盟','star',NAVY),('天合联盟','skyteam',BLUE),('寰宇一家','oneworld',PURPLE),('未加入三大联盟',None,MUTED)]
    if s['alliances']['counts']['归属待核验']:alliance_items.append(('归属待核验',None,MUTED))
    for i,(label,logo,color) in enumerate(alliance_items):
        cx=80+(i+.5)*2240/len(alliance_items);n=s['alliances']['counts'][label]
        if logo=='star':alliance_logo(g,logo,cx-125,alliance_start+78,250,146)
        elif logo:alliance_logo(g,logo,cx-60,alliance_start+85,120,120)
        else:
            g.add(f'<g transform="translate({cx},{alliance_start+131}) rotate(-28) scale(1.5)" fill="{color}"><path d="M-22,-3L-4,-3L-8,-20L-3,-20L8,-3L22,-2Q30,0 22,2L8,3L-3,20L-8,20L-4,3L-22,3L-26,10L-30,10L-28,0L-30,-10L-26,-10Z"/></g>')
            g.text(cx,alliance_start+205,'待核验' if label=='归属待核验' else '未入盟',21,MUTED,400,'middle')
        g.text(cx,alliance_start+272,f'{n} 次',48,color,600,'middle')
    g.line(80,airport_start,2320,airport_start,NAVY,1,.25)
    g.text(80,airport_start+64,'AIRPORT VISITS / 出发与到达机场',33,NAVY,600)
    g.text(2320,airport_start+64,f"{len(rank)} AIRPORTS · {sum(n for a,n in rank)} VISITS",29,TEAL,600,'end')
    g.rect(82,airport_start+97,25,17,BLUE,2);g.text(119,airport_start+113,'出发',23,MUTED);g.rect(215,airport_start+97,25,17,GOLD,2);g.text(252,airport_start+113,'到达',23,MUTED)
    g.text(1250,airport_start+114,'全部机场 · 字号按总次数对数缩放',25,MUTED)
    g.text(410,airport_start+113,f"柱状图仅列总次数 ≥{c.get('airport_bar_min',bar_min)} 的机场",22,MUTED)
    maxvisits=rank[0][1]
    body_y=airport_start+145;body_height=airport_height-80
    code_size=airport_panel_layout['code_size'];name_size=airport_panel_layout['name_size']
    row_pitch=min(airport_panel_layout['pitch'],(body_height-48)/max(1,len(bar_rank)-1))
    row_start=body_y+body_height/2-(len(bar_rank)-1)*row_pitch/2
    for i,(a,n) in enumerate(bar_rank):
        yy=row_start+i*row_pitch
        iata(g,140,yy-8,a,code_size,NAVY,600,'end',central=True)
        g.parts[-1]=g.parts[-1].replace('<text ',f'<text data-airport-code="{a}" ',1)
        airport_name=airport_names.get(a,data['airports'][a]['cn'])
        fitted=min(name_size,name_size*246/max(1,font(name_size).getlength(airport_name)))
        if fitted<14:
            # Preserve the full name in two lines, not a clipped abbreviation.
            split=min(range(1,len(airport_name)),key=lambda n:abs(font(18).getlength(airport_name[:n])-font(18).getlength(airport_name[n:])))
            for j,line in enumerate([airport_name[:split],airport_name[split:]]):g.text(154,yy-18+j*22,line,min(18,18*246/max(1,font(18).getlength(line))),MUTED)
        else:g.text(154,yy-8,airport_name,fitted,MUTED)
        g.parts[-1]=g.parts[-1].replace('<text ',f'<text dominant-baseline="central" data-airport-cn="{a}" ',1)
        dep,arr=s['dep'][a],s['arr'][a];dw=600*dep/maxvisits;aw=600*arr/maxvisits
        bar_height=25 if code_size>=28 else 21
        g.rect(410,yy-8-bar_height/2,dw,bar_height,BLUE,0);g.rect(410+dw,yy-8-bar_height/2,aw,bar_height,GOLD,0)
        if dw>29:g.text(410+dw/2,yy-3,dep,15,'white',600,'middle')
        if aw>29:g.text(410+dw+aw/2,yy-3,arr,15,'white',600,'middle')
        g.text(1050,yy-8,n,code_size,NAVY,600,'middle')
        g.parts[-1]=g.parts[-1].replace('<text ',f'<text dominant-baseline="central" data-airport-total="{a}" ',1)
        if dw<=29 or aw<=29:
            g.text(1100,yy-8,f'{dep}/{arr}',16,MUTED,400,'middle')
            g.parts[-1]=g.parts[-1].replace('<text ',f'<text dominant-baseline="central" data-airport-split="{a}" ',1)
    g.add(f'<g transform="translate(0,{body_y})">'+''.join(airport_panel_layout['layer'])+'</g>')
    s['wordcloud_layout']=[{**p,'box':[p['box'][0],p['box'][1]+body_y,p['box'][2],p['box'][3]+body_y]} for p in airport_panel_layout['placements']]
    if repeats:
        g.line(80,repeat_start,2320,repeat_start,NAVY,1,.25);g.text(80,repeat_start+63,'FAMILIAR AIRCRAFTS / 重复乘坐的飞机',33,NAVY,600)
        g.text(2320,repeat_start+62,f"{len(repeats)} REGISTRATIONS · {sum(n for a,n in repeats)} FLIGHTS",27,TEAL,600,'end')
    registration_carriers={}
    for r in data['rows']:
        reg=str(r.get('K','')).strip().upper().replace(' ','')
        if reg.startswith('B') and '-' not in reg:reg='B-'+reg[1:]
        if reg in s['registrations']:registration_carriers.setdefault(reg,Counter())[r['AD']]+=1
    s['registration_carriers']={reg:dict(counts) for reg,counts in registration_carriers.items() if s['registrations'][reg]>1}
    s['airframe_cards']={'age_as_of':c.get('age_as_of'),'age_basis':'首次交付日期至统计截止日','repeated':[],'retired':retired,'status_checked_on':lifecycle['as_of'],'screening_coverage':lifecycle['coverage']}
    def age_label(f,xx,yy):
        value=f"{f['age']:.1f}" if f.get('age') is not None else '—'
        g.text(xx+208,yy+100,'机龄',14,MUTED,400,'end')
        g.text(xx+268,yy+100,value,23,NAVY,600,'end')
        g.text(xx+288,yy+100,'年',14,MUTED,400,'end')
    def photo(f,xx,yy,offset):
        p=f.get('photo')
        if p:
            path=BASE/'assets/photos'/p['file']
            with Image.open(path) as source:iw,ih=source.size
            ph=274*ih/iw;img(g,path,xx+16,yy+offset,274,ph)
            f['photo_box']=[xx+16,yy+offset,274,ph];f['photo_aspect_ratio']=iw/ih
        else:g.text(xx+153,yy+220,'待补充照片',19,MUTED,400,'middle')
    for i,(a,n) in enumerate(repeats):
        slot=0 if i==0 else repeat_slots[i-1]
        xx=80+slot%7*320;yy=repeat_start+96+slot//7*134+(repeat_offset if i else featured_offset);ch=featured_height if i==0 else 122
        g.rect(xx,yy,306,ch,'#fffdf7',10,'#e3e7df',1)
        g.text(xx+16,yy+36,a,29,NAVY,600);g.text(xx+288,yy+37,f'{n}×',30,TEAL,600,'end');g.text(xx+16,yy+68,SHORT.get(s['registration_models'][a],s['registration_models'][a]),22,MUTED)
        names=list(registration_carriers[a]);label=' / '.join(names)
        g.text(xx+16,yy+100,label,min(19,19*170/max(1,font(19).getlength(label))),NAVY,500)
        age_label(facts[a],xx,yy)
        if i==0:photo(facts[a],xx,yy,118)
        s['airframe_cards']['repeated'].append(dict(facts[a],flights=n,box=[xx,yy,306,ch],featured=i==0))
    if c.get('include_retired',False):
        g.line(80,retired_start,2320,retired_start,NAVY,1,.25)
        g.text(80,retired_start+63,'RETIRED FROM PASSENGER SERVICE / 已退役的飞机',33,NAVY,600)
        g.text(2320,retired_start+62,f"已核验 {len(retired)} 架 · 状态覆盖 {lifecycle['coverage']['verified_registrations']}/{len(facts)}",23,TEAL,600,'end')
        if not retired:g.text(80,retired_start+100,'未提供已确认永久退出客运的机体资料；这不代表没有退役飞机。',21,MUTED)
    for i,f in enumerate(retired):
        a=f['registration'];xx=80+i%7*320;yy=retired_start+96+i//7*(retired_height+16)
        ch=retired_height
        g.rect(xx,yy,306,ch,'#fffdf7',10,'#e3e7df',1)
        g.text(xx+16,yy+36,a,29,NAVY,600)
        g.text(xx+288,yy+37,f"{s['registrations'][a]}×",30,TEAL,600,'end')
        g.text(xx+16,yy+68,SHORT.get(f['model'],f['model']),21,MUTED)
        g.text(xx+16,yy+100,' / '.join(f['carriers']),19,NAVY,500)
        status=f["last_passenger_date"]+'退出客运 · '+f['status']
        g.text(xx+16,yy+129,status,min(16,16*274/max(1,font(16).getlength(status))),MUTED)
        age_label(f,xx,yy);photo(f,xx,yy,147+(retired_height-159-photo_height(f))/2)
        f['box']=[xx,yy,306,ch]
    actualheight=height
    s['airport_panel_typography']={'code_and_total_size':code_size,'name_size':name_size,'row_pitch':row_pitch,'shared_body_height':body_height,'all_airport_count':len(rank),'bar_airport_count':len(bar_rank)}
    s['layout']={'model_columns':{'regional':5,'narrow':4,'wide':3},'airline_column_top':top,'airline_column_bottom':top+airline_height,'map_column_top':top,'map_column_bottom':top+145+map_height,'map_height':map_height,'alliance_start':alliance_start,'airport_start':airport_start,'airport_bar_body':[body_y,body_height],'wordcloud_body':[body_y,body_height],'repeat_start':repeat_start,'repeat_group_offset':repeat_offset,'retired_start':retired_start,'height':actualheight,'aircraft_scale_px_per_metre':9,'wordcloud_style':'v3','title_style':{'flight_tracking':2,'atlas_tracking':7,'atlas_width_multiplier':1.055,'atlas_weight_stroke':.6},'airport_cn_font_size':22,'retired_common_card_height':retired_height}
    s['layout']['airport_cn_font_size']=name_size
    g.text(80,actualheight-47,'MY FLIGHT PASSPORT',20,TEAL,600,spacing=3);g.text(2320,actualheight-47,'AIRCRAFT · AIRLINES · AIRPORTS',20,TEAL,600,'end',2)
    # Final dynamic canvas height accounts for a growing airline list.
    g.parts[0]=g.parts[0].replace(f'height="{height}"',f'height="{actualheight}"').replace(f'0 0 2400 {height}',f'0 0 2400 {actualheight}')
    g.parts[1]=g.parts[1].replace(f'height="{height}"',f'height="{actualheight}"')
    g.save(out/'02_FLIGHT_ATLAS.svg')
