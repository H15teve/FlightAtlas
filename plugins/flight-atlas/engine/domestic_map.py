"""pyecharts option generation, entirely offline."""
import json,math
from collections import Counter
from pyecharts.charts import Geo
from pyecharts import options as opts
from pyecharts.globals import ChartType
def top_flight_numbers(rows,limit=3):
    """Count exported flight numbers across all routes; do not infer operating numbers."""
    counts=Counter()
    for row in rows:
        number=''.join(str(row.get('C') or '').upper().split())
        if number and number not in {'-','—','N/A','UNKNOWN','未知'}:
            counts[number]+=1
    return [{'flight_number':number,'flights':n} for number,n in sorted(counts.items(),key=lambda item:(-item[1],item[0]))[:limit]]

def build_map(data,out,height=1200,route_min=3):
    directional=Counter((r['_dep'],r['_arr']) for r in data['rows'] if all(data['airports'][r[k]]['country'] in ['CN','HK','MO','TW'] for k in ['_dep','_arr']))
    frequent=[{'airports':list(pair),'flights':n} for pair,n in sorted(directional.items(),key=lambda r:(-r[1],r[0])) if n>=route_min]
    top_flights=top_flight_numbers(data['rows'])
    flight_ranking_y=154+len(frequent)*29
    ranking_bottom=flight_ranking_y+66+len(top_flights)*29 if top_flights else flight_ranking_y+95
    height=max(height,ranking_bottom+15)
    routes=Counter();visits=Counter()
    for pair,n in directional.items():routes[tuple(sorted(pair))]+=n;visits.update({a:n for a in pair})
    geo=Geo(init_opts=opts.InitOpts(width='1460px',height=f'{height}px',renderer='svg',bg_color='#f8f5ec'))
    geo.add_schema(maptype='china',is_roam=False,itemstyle_opts=opts.ItemStyleOpts(color='#dce8e1',border_color='#99bab2',border_width=.65),label_opts=opts.LabelOpts(is_show=False))
    geo.options['geo'].update({'layoutCenter':['50%','50%'],'layoutSize':min(1430,height-30),'aspectScale':.75,'boundingCoords':[[73,54],[136,17.5]],'silent':True})
    for a,p in data['airports'].items():geo.add_coordinate(a,p['lon'],p['lat'])
    for pair,n in routes.items():geo.add('routes',[pair],type_=ChartType.LINES,symbol=['none','none'],effect_opts=opts.EffectOpts(is_show=False),linestyle_opts=opts.LineStyleOpts(color='#c5683a',width=1.1+math.log1p(n)*.8,opacity=.65,curve=.16),label_opts=opts.LabelOpts(is_show=False))
    geo.add('airports',list(visits.items()),type_=ChartType.SCATTER,symbol_size=6,color='#b95339',label_opts=opts.LabelOpts(is_show=False),itemstyle_opts=opts.ItemStyleOpts(border_color='#fffdf7',border_width=1))
    geo.set_global_opts(legend_opts=opts.LegendOpts(is_show=False),tooltip_opts=opts.TooltipOpts(is_show=False));geo.options['animation']=False
    (out/'国内航线_pyecharts.json').write_text(geo.dump_options(),encoding='utf-8')
    (out/'map_layout.json').write_text(json.dumps({'width':1460,'height':height,'route_min':route_min,'frequent_routes':frequent,'top_flight_numbers':top_flights,'flight_number_scope':'all exported records','flight_ranking_y':flight_ranking_y,'ranking_box':[50,35,430,ranking_bottom]}),encoding='utf-8')
    inset=Geo(init_opts=opts.InitOpts(width='220px',height='320px',renderer='svg',bg_color='#f8f5ec'))
    inset.add_schema(maptype='china',is_roam=False,itemstyle_opts=opts.ItemStyleOpts(color='#e2eee7',border_color='#739b91',border_width=1),label_opts=opts.LabelOpts(is_show=False))
    inset.options['geo'].update({'layoutCenter':['50%','50%'],'layoutSize':204,'aspectScale':.75,'boundingCoords':[[105,26],[126,2.5]],'silent':True})
    inset.set_global_opts(legend_opts=opts.LegendOpts(is_show=False));inset.options['animation']=False
    (out/'南海诸岛_pyecharts.json').write_text(inset.dump_options(),encoding='utf-8')
    return {'map_library':'pyecharts / ECharts SVG SSR','source':'https://assets.pyecharts.org/assets/maps/china.js','domestic_route_count':len(routes),'frequent_routes':frequent,'route_min':route_min,'top_flight_numbers':top_flights,'flight_number_scope':'all exported records','height':height,'airport_count':len(visits),'boundary_review':'contains Taiwan, maritime geometry and South China Sea inset; not a certified standard map'}
