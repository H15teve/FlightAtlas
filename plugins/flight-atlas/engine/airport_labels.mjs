export function placeAirportLabels(echarts,chart,scatter,width,height){
 const airports=scatter.data.map(p=>({name:p.name,visits:p.value[2],point:chart.convertToPixel({geoIndex:0},p.value.slice(0,2))}));
 const bay=new Set(['CAN','SZX','HKG','MFM','ZUH','HUZ']);
 const preferred={PEK:'right',PKX:'left',SJW:'left',TSN:'right',ZQZ:'left',CTU:'left',TFU:'right',CKG:'right',CAN:'top',SZX:'left',HKG:'right',MFM:'left',ZUH:'bottom',HUZ:'right'};
 const distance=(point,box)=>Math.hypot(Math.max(box[0]-point[0],0,point[0]-box[2]),Math.max(box[1]-point[1],0,point[1]-box[3]));
 const overlap=(a,b)=>a[0]<b[2]+1&&a[2]+1>b[0]&&a[1]<b[3]+1&&a[3]+1>b[1];
 function candidates(p,fontSize){
  const [px,py]=p.point,font=`600 ${fontSize}px Arial`,rect=echarts.format.getTextRect(p.name,font),bw=rect.width+6,bh=fontSize+4;
  const result=[];
  for(const side of ['right','left','top','bottom'])for(const gap of [3,5,7,10])for(const shift of [0,-3,3,-6,6,-10,10,-15,15]){
   let bx,by;
   if(side==='right'){bx=px+gap;by=py-bh/2+shift;}
   if(side==='left'){bx=px-gap-bw;by=py-bh/2+shift;}
   if(side==='top'){bx=px-bw/2+shift;by=py-gap-bh;}
   if(side==='bottom'){bx=px-bw/2+shift;by=py+gap;}
   const box=[bx,by,bx+bw,by+bh],own=distance(p.point,box);
   if(box[0]<10||box[2]>width-10||box[1]<10||box[3]>height-10||own>12)continue;
   const other=Math.min(...airports.filter(q=>q.name!==p.name).map(q=>distance(q.point,box)));
   // Each label's nearest marker must be its own airport; never cover another marker.
   if(other<own+.35||other<3.5)continue;
   result.push({box,x:bx,y:by+bh/2,fontSize,own,nearestOther:other,side,score:own*3+Math.abs(shift)*.2+(preferred[p.name]&&preferred[p.name]!==side?4:0)});
  }
  return result.sort((a,b)=>a.score-b.score);
 }
 let solution;
 for(const size of [15,14,13,12]){
  const tasks=airports.map(p=>({...p,choices:candidates(p,bay.has(p.name)?size:17)})).sort((a,b)=>a.choices.length-b.choices.length||b.visits-a.visits);
  if(tasks.some(p=>!p.choices.length))continue;
  let visits=0;
  function solve(index,chosen){
   if(index===tasks.length)return chosen;
   if(++visits>150000)return;
   const p=tasks[index];
   for(const c of p.choices){
    if(chosen.some(q=>overlap(c.box,q.box)))continue;
    const found=solve(index+1,[...chosen,{...c,airport:p.name,point:p.point}]);if(found)return found;
   }
  }
  solution=solve(0,[]);if(solution)break;
 }
 if(!solution)throw Error('Cannot place airport labels with unambiguous nearest markers.');
 return solution;
}
