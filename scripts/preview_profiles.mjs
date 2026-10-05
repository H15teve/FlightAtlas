// Render an inspection contact sheet. Never modifies the aircraft source PNGs.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const require=createRequire(path.join(root,'plugins/flight-atlas/package.json'));
const sharp=require('sharp');
const args=process.argv.slice(2);
const folder=path.resolve(args[0]??path.join(root,'plugins/flight-atlas/assets/silhouettes'));
const output=path.resolve(args[1]??path.join(root,'.local/profile-review.png'));
const layout=JSON.parse(fs.readFileSync(path.join(root,'plugins/flight-atlas/assets/silhouettes/layout_v7.json'),'utf8'));
const keys=Object.keys(layout).filter(key=>fs.existsSync(path.join(folder,key+'.png')));
if(!keys.length)throw new Error('No standalone aircraft PNGs found');
const cols=4,cw=450,ch=225,w=cols*cw,h=Math.ceil(keys.length/cols)*ch;
let svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><defs><filter id="alphaClean" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="discrete" tableValues="0 0 0 0 0 0 0 0 0 1"/></feComponentTransfer></filter></defs><rect width="${w}" height="${h}" fill="#f5f2e8"/>`;
for(let i=0;i<keys.length;i++){
  const key=keys[i],x=(i%cols)*cw,y=Math.floor(i/cols)*ch;
  const png=fs.readFileSync(path.join(folder,key+'.png'));
  svg+=`<rect x="${x+4}" y="${y+4}" width="${cw-8}" height="${ch-8}" rx="8" fill="#faf8f0" stroke="#deddd6"/><image x="${x+12}" y="${y+26}" width="${cw-24}" height="${ch-62}" preserveAspectRatio="xMidYMid meet" filter="url(#alphaClean)" href="data:image/png;base64,${png.toString('base64')}"/><text x="${x+cw/2}" y="${y+ch-18}" text-anchor="middle" font-family="Arial,sans-serif" font-size="19" fill="#12306a">${key}</text>`;
}
svg+='</svg>';
fs.mkdirSync(path.dirname(output),{recursive:true});
await sharp(Buffer.from(svg)).png().toFile(output);
console.log(JSON.stringify({review_sheet:output,aircraft:keys.length,source_assets_modified:false}));
