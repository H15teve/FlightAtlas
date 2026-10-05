"""Developer-only: index built-in art and optionally copy openly licensed flag assets.

No runtime image generation or private files. Derived metadata only; never edits PNG pixels.
"""
import argparse,hashlib,io,json,sys,urllib.request,zipfile
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PLUGIN=ROOT/'plugins/flight-atlas'
sys.path.insert(0,str(PLUGIN/'engine'))
from models import FAMILIES
NEW=['A339','A340','A380','B767','E170','E290','AT42','AT72','BA46','CRJ7','CRJ9','F100']
def index():
    path=PLUGIN/'assets/silhouettes/layout_v7.json';layout=json.loads(path.read_text(encoding='utf-8'))
    # Orthographic releases use one PNG per family; older sprite releases remain
    # indexable until every replacement has been generated and reviewed.
    keys=[f[0] for f in FAMILIES] if all((path.parent/(f[0]+'.png')).is_file() for f in FAMILIES) else NEW
    for key in keys:
        with Image.open(path.parent/(key+'.png')) as image:
            if image.mode!='RGBA':raise ValueError('Transparent icon missing: '+key)
            bbox=image.getchannel('A').point(lambda n:255 if n>220 else 0).getbbox()
            if not bbox:raise ValueError('Empty aircraft: '+key)
            x,y,right,bottom=bbox;pad=5
            layout[key]={'file':key+'.png','width':image.width,'height':image.height,'viewBox':[max(0,x-pad),max(0,y-pad),min(image.width,right+pad)-max(0,x-pad),min(image.height,bottom+pad)-max(0,y-pad)]}
    path.write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    references={'Airbus':'https://www.airbus.com/en/products-services/commercial-aircraft','Boeing':'https://www.boeing.com/commercial','Embraer':'https://www.embraercommercialaviation.com/','ATR':'https://www.atr-aircraft.com/regional-mobility/regional-aircraft/','Fokker':'https://www.fokkerservicesgroup.com/media/emccsdnm/fsg_fokker-100.pdf'}
    families={k:{'length_m':length,'profile':title,'basis':'illustrative representative overall length, not a measured technical drawing'} for k,title,codes,group,kind,length in FAMILIES}
    dimensions={'pixels_per_metre':9,'families':families,'references':references,'limits':'Profile art is fixed and approximate; not an engineering scale drawing. Other subtypes remain in count labels.'}
    if len(keys)==len(FAMILIES):dimensions['projection']='left orthographic side elevation; far-side engines may be hidden'
    (PLUGIN/'assets/data/aircraft_dimensions.json').write_text(json.dumps(dimensions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.parent.glob('*.png'))}
    (PLUGIN/'assets/silhouettes/checksums.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
def vendor():
    url='https://github.com/HatScripts/circle-flags/archive/refs/heads/gh-pages.zip'
    with urllib.request.urlopen(url,timeout=60) as r:raw=r.read(20000000)
    flags=PLUGIN/'assets/round-flags'
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in archive.namelist():
            p=Path(name)
            if p.parent.name=='flags' and len(p.stem)==2 and p.suffix=='.svg':(flags/(p.stem.upper()+'.svg')).write_bytes(archive.read(name))
            if p.name in ['LICENSE','LICENSE.md'] and len(p.parts)==2:(flags/'LICENSE.md').write_bytes(archive.read(name))
    with urllib.request.urlopen('https://raw.githubusercontent.com/pyecharts/pyecharts-assets/master/LICENSE',timeout=30) as r:(PLUGIN/'assets/data/pyecharts-assets-LICENSE').write_bytes(r.read(10000))
    print(json.dumps({'flags':len(list(flags.glob('*.svg'))),'circle_flags_archive_sha256':hashlib.sha256(raw).hexdigest()}))

def palette(audit_file,prompt_file):
    """Refresh derived color-review metadata; preserve prior generation prompts."""
    folder=PLUGIN/'assets/silhouettes'
    audit=json.loads(audit_file.read_text(encoding='utf-8'))
    provenance_path=folder/'provenance.json'
    provenance=json.loads(provenance_path.read_text(encoding='utf-8'))
    prompts=json.loads(prompt_file.read_text(encoding='utf-8')) if prompt_file else {'assets':{}}
    hashes=json.loads((folder/'checksums.json').read_text(encoding='utf-8'))
    if set(audit['assets'])!=set(provenance['assets']):raise ValueError('Palette family set mismatch')
    for key,record in audit['assets'].items():
        if record['sha256']!=hashes[key+'.png']:raise ValueError('Stale palette audit: '+key)
        entry=provenance['assets'][key]
        entry['sha256']=record['sha256']
        if key in prompts['assets']:entry['color_edit_prompt']=prompts['assets'][key]
        entry['visual_review']['scope']='side-facing silhouette, white contours/windows, uniform group body fill including gear and engines; correct cockpit mask treatment'
        entry['palette_review']={'audit':'palette-audit.json','alpha_unchanged':record['alpha_unchanged'],'body_rgb':record['body_rgb'],'cockpit_box':record['cockpit_box'],'neutral_pixels_outside_cockpit':record['neutral_pixels_outside_cockpit']}
    provenance['revision']='2026-10-04-flat-palette'
    provenance['style']='Three color roles: fixed group body fill; white contours/edges/cabin windows; gray glass and black A350/A330neo cockpit mask. Original alpha retained; boundary antialiasing may blend these role colors.'
    provenance['palette_normalization']={'authorization':audit['authorization'],'method':'scripts/normalize_aircraft_palette.py, developer-only deterministic color normalization','audit':'palette-audit.json','body_colors':audit['body_colors'],'mask_profiles':['A350','A339'],'no_mask_profile':'C919','prompt_mode':prompts.get('mode')}
    provenance_path.write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (folder/'palette-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--vendor-public-flags',action='store_true');p.add_argument('--palette-audit',type=Path);p.add_argument('--palette-prompts',type=Path);a=p.parse_args()
    index()
    if a.palette_audit:palette(a.palette_audit,a.palette_prompts)
    if a.vendor_public_flags:vendor()
