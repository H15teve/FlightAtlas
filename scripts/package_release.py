"""Build an allowlisted source ZIP; never publish or include local user data."""
import hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'node_modules','__pycache__','.local','.git','.venv','reports','dist','.pytest_cache'}
TEXT={'.md','.py','.mjs','.json','.yaml','.txt','.toml','.svg','.cjs','.csv'}
PRIVATE_STATE={'flight-history.json','report-config.json','increment-audit.json'}
def public_files():
    roots=[ROOT/'plugins/flight-atlas',ROOT/'tests',ROOT/'scripts',ROOT/'.agents/plugins',ROOT/'.github']
    files=[ROOT/'README.md',ROOT/'LICENSE',ROOT/'.gitignore',ROOT/'requirements-dev.txt']
    for root in roots:
        for p in root.rglob('*'):
            if not p.is_file() or any(x in EXCLUDED for x in p.relative_to(ROOT).parts):continue
            if p.name in PRIVATE_STATE:raise ValueError('Private reporting state in public tree: '+p.name)
            if p.suffix.lower() in ['.xlsx','.xls','.pyc','.zip']:raise ValueError('Workbook or binary artifact in public tree: '+p.name)
            if p.suffix.lower()=='.csv' and p!=ROOT/'plugins/flight-atlas/examples/sample.csv':raise ValueError('Unapproved CSV: '+p.name)
            files.append(p)
    for p in files:
        if p.suffix.lower() in TEXT:
            text=p.read_text(encoding='utf-8-sig')
            patterns=r'(?i)JIAQI\s*CHEN|CHEN\s*JIAQI|C:[/\\]Users[/\\]|'+'codex'+'-'+'clipboard'
            if re.search(patterns,text):
                raise ValueError('Private path/name found: '+str(p.relative_to(ROOT)))
    return sorted(set(files))
def main():
    files=public_files();folder=ROOT/'dist';folder.mkdir(exist_ok=True);target=folder/'FlightAtlas-0.1.1.zip'
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files:z.write(p,'FlightAtlas/'+str(p.relative_to(ROOT)).replace('\\','/'))
        z.writestr('FlightAtlas/RELEASE_FILES.json',json.dumps(manifest,indent=2))
    digest=hashlib.sha256(target.read_bytes()).hexdigest()
    (folder/'FlightAtlas-0.1.1.sha256').write_text(digest+'  '+target.name+'\n',encoding='ascii')
    print(json.dumps({'files':len(files),'zip':str(target),'sha256':digest,'bytes':target.stat().st_size}))
if __name__=='__main__':main()
