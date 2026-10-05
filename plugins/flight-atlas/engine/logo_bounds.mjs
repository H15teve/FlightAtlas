// Measure the rendered artwork; retain the original vector asset for placement.
import sharp from 'sharp';
const {data, info} = await sharp(process.argv[2], {density: 144})
  .resize({width: 2048, height: 2048, fit: 'inside', withoutEnlargement: true})
  .ensureAlpha().raw().toBuffer({resolveWithObject: true});
let left=info.width, top=info.height, right=0, bottom=0;
for(let y=0;y<info.height;y++)for(let x=0;x<info.width;x++){
  if(data[(y*info.width+x)*info.channels+info.channels-1]>10){
    left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x+1);bottom=Math.max(bottom,y+1);
  }
}
if(right<=left || bottom<=top)throw new Error('Logo has no visible artwork');
console.log(JSON.stringify({width:info.width,height:info.height,bounds:[left,top,right,bottom]}));
