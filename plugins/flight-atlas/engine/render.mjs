import fs from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';
const directory=process.argv[2],scale=Number(process.argv[3]||1.5);
for(const file of ['01_MY_FLIGHT_PASSPORT.svg','02_FLIGHT_ATLAS.svg']){
 await sharp(path.join(directory,file),{density:72*scale,limitInputPixels:268402689}).png().toFile(path.join(directory,file.replace('.svg','.png')));
}
