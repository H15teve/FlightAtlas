"""Read-only manifest, paths, skill metadata and redistribution validation."""
import argparse,json,re,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PLUGIN=ROOT/'plugins/flight-atlas'
def validate(schema_path=None):
    portable=json.loads((PLUGIN/'plugin.json').read_text(encoding='utf-8'))
    if schema_path:
        import jsonschema
        jsonschema.validate(portable,json.loads(Path(schema_path).read_text(encoding='utf-8')))
    assert set(portable)<= {'$schema','name','version','description','author','homepage','repository','license','keywords','extensions'}
    assert portable['name']=='flight-atlas' and portable['version']=='0.1.2'
    compatibility=json.loads((PLUGIN/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    assert compatibility['name']==portable['name'] and compatibility['version']==portable['version']
    skill=(PLUGIN/compatibility['skills']).resolve();assert skill.is_relative_to(PLUGIN) and skill.is_dir()
    text=(skill/'flight-report/SKILL.md').read_text(encoding='utf-8');assert text.startswith('---\n')
    import yaml
    front=yaml.safe_load(text.split('---',2)[1]);assert front['name']=='flight-report' and len(front['description'])<1024
    ui=yaml.safe_load((skill/'flight-report/agents/openai.yaml').read_text(encoding='utf-8'))
    assert 25<=len(ui['interface']['short_description'])<=64 and '$flight-report' in ui['interface']['default_prompt']
    marketplace=json.loads((ROOT/'.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
    assert (ROOT/marketplace['plugins'][0]['source']['path']).resolve()==PLUGIN
    for match in re.findall(r'`(references/[^`]+\.md)`',text):assert (skill/'flight-report'/match).is_file()
    for name in ['LICENSE','ASSET_NOTICES.md','assets/data/pyecharts-assets-LICENSE','assets/round-flags/LICENSE.md']:
        assert (PLUGIN/name).is_file(),name
    print(json.dumps({'portable_manifest':'valid','codex_compatibility_paths':'valid','skill_frontmatter':'valid','license_notices':'present','installed_in_codex':False}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--schema');a=p.parse_args();validate(a.schema)
