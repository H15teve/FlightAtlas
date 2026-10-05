import fs from 'node:fs/promises';
import path from 'node:path';
import vm from 'node:vm';
import * as echarts from 'echarts';
import {placeAirportLabels} from './airport_labels.mjs';
vm.runInNewContext(await fs.readFile(new URL('../assets/data/china.cjs',import.meta.url),'utf8'),{echarts,console});
const features=echarts.getMap('china').geoJSON.features;
if(!features.some(f=>f.properties.name==='台湾省')||!features.some(f=>f.properties.adchar==='JD'))throw Error('Incomplete China map geometry');
// ECharts injects a schematic South China Sea box specifically for the name
// "china". We already render a geographic inset, so use the unchanged native
// geometry under an alias to avoid a second inset (including its frame).
const nativeChina=echarts.getMap('china');
echarts.registerMap('flightatlas-china',nativeChina.geoJSON,nativeChina.specialAreas);
const out=process.argv[2],layout=JSON.parse(await fs.readFile(path.join(out,'map_layout.json'),'utf8'));
const addText=(options,x,y,text,font='600 18px Arial',align='left',fill='#173552')=>options.graphic.push({type:'text',silent:true,z:100,x,y,style:{text,font,fill,align,verticalAlign:'middle'}});
for(const [name,width,height] of [['南海诸岛',220,320],['国内航线',layout.width,layout.height]]){
 const chart=echarts.init(null,null,{renderer:'svg',ssr:true,width,height});
 // Only generated options are parsed. Workbook cells and user JavaScript are never evaluated.
 const options=vm.runInNewContext('('+await fs.readFile(path.join(out,name+'_pyecharts.json'),'utf8')+')',{}, {timeout:1000});
 options.geo.map='flightatlas-china';
 chart.setOption(options);
 const renderedRegions=chart.getModel().getComponent('geo').coordinateSystem.regions;
 if(renderedRegions.length!==features.length)throw Error('Native map feature set changed during rendering');
 const coords=chart.getModel().getComponent('geo').coordinateSystem;
 const geoRect=coords.getViewRect();
 const geometryAudit={geo_view_rect:{x:geoRect.x,y:geoRect.y,width:geoRect.width,height:geoRect.height},aspect_scale:coords.aspectScale,proportional_layout:true,source_feature_count:features.length,rendered_region_count:renderedRegions.length,synthetic_inset_regions:0,source_geometry_unchanged:true,renderer:'ECharts SVG SSR; no screenshot'};
 if(name==='南海诸岛')await fs.writeFile(path.join(out,'南海附图核验.json'),JSON.stringify(geometryAudit,null,2));
 if(name==='国内航线'){
  const scatter=options.series.find(s=>s.type==='scatter'),solution=scatter?.data.length?placeAirportLabels(echarts,chart,scatter,width,height):[];
  options.graphic=[];const labels=[];
  for(const p of solution){
   labels.push({airport:p.airport,point:p.point,box:p.box,font_size:p.fontSize,point_label_gap:p.own,nearest_other_point_gap:p.nearestOther});
   options.graphic.push({type:'rect',silent:true,z:99,shape:{x:p.box[0],y:p.box[1],width:p.box[2]-p.box[0],height:p.box[3]-p.box[1]},style:{fill:'#f8f5ec'}});
   addText(options,(p.box[0]+p.box[2])/2,p.y,p.airport,`600 ${p.fontSize}px Arial`,'center');
  }
  const rankingBox=layout.ranking_box;
  if(rankingBox[3]>height-15||labels.some(p=>{const b=p.box;return b[0]<rankingBox[2]&&b[2]>rankingBox[0]&&b[1]<rankingBox[3]&&b[3]>rankingBox[1];}))throw Error('Route/flight-number rankings no longer fit clear map area; raise route_min or adjust layout.');
  addText(options,55,62,'FREQUENT ROUTES / 常飞航线','600 22px Microsoft YaHei');
  addText(options,55,94,`单向次数 ≥${layout.route_min} · 不合并往返`,'400 15px Microsoft YaHei','left','#64757e');
  for(const [i,r] of layout.frequent_routes.entries()){
   const y=138+i*29;addText(options,55,y,String(i+1).padStart(2,'0'),'400 16px Arial','left','#64757e');
   addText(options,120,y,r.airports[0],'600 18px Arial','center');addText(options,162,y,'→','600 18px Arial','center');addText(options,205,y,r.airports[1],'600 18px Arial','center');addText(options,410,y,r.flights+' 次','600 18px Microsoft YaHei','right');
  }
  const fy=layout.flight_ranking_y;
  addText(options,55,fy,'TOP FLIGHTS / 常乘航班 TOP3','600 22px Microsoft YaHei');
  addText(options,55,fy+30,'按全表航班号统计','400 15px Microsoft YaHei','left','#64757e');
  const flightRankStyles=[{font_size:22,color:'#b78b35'},{font_size:22,color:'#7f8b97'},{font_size:22,color:'#a86c46'}];
  for(const [i,r] of layout.top_flight_numbers.entries()){
   const y=fy+65+i*29;
   const rankStyle=flightRankStyles[i];
   addText(options,55,y,String(i+1).padStart(2,'0'),`400 ${rankStyle.font_size-4}px Arial`,'left',rankStyle.color);
   const fontSize=Math.min(rankStyle.font_size,225/Math.max(1,r.flight_number.length)/.65);
   addText(options,108,y,r.flight_number,`600 ${fontSize}px Arial`,'left',rankStyle.color);
   addText(options,410,y,r.flights+' 次',`600 ${rankStyle.font_size}px Microsoft YaHei`,'right',rankStyle.color);
  }
  if(!layout.top_flight_numbers.length)addText(options,55,fy+65,'无可统计航班号','400 16px Microsoft YaHei','left','#64757e');
  chart.setOption(options,{notMerge:true});
  await fs.writeFile(path.join(out,'机场标签核验.json'),JSON.stringify({labels,leader_lines:0,max_point_label_gap:Math.max(0,...labels.map(p=>p.point_label_gap)),ranking_box:rankingBox,flight_number_ranking_box:[50,fy-16,430,rankingBox[3]],flight_number_rank_styles:flightRankStyles.slice(0,layout.top_flight_numbers.length),geometry:geometryAudit},null,2));
 }
 let svg=chart.renderToSVGString();
 if(name==='国内航线'){
  const inset=Buffer.from(await fs.readFile(path.join(out,'南海诸岛.svg'))).toString('base64');
  svg=svg.replace('</svg>',`<rect x="${width-235}" y="${height-335}" width="220" height="320" fill="#f8f5ec" stroke="#99bab2"/><image x="${width-235}" y="${height-335}" width="220" height="320" href="data:image/svg+xml;base64,${inset}"/></svg>`);
 }
 await fs.writeFile(path.join(out,name+'.svg'),svg);chart.dispose();
}
