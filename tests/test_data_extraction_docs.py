"""Packaged onboarding remains usable without the author's private notebook."""
import csv,hashlib,json,re
from pathlib import Path
from PIL import Image
from build import BASE

ROOT=BASE.parents[1]
REF=BASE/'skills/flight-report/references'

def test_user_tutorial_and_packaged_prompt_match_and_preserve_non_duration_text():
    prompt=(REF/'extraction-prompt.txt').read_text(encoding='utf-8').strip()
    tutorial=(BASE/'docs/data-extraction.md').read_text(encoding='utf-8')
    block=tutorial.split('<!-- extraction-prompt:start -->')[1].split('<!-- extraction-prompt:end -->')[0]
    embedded=block.split('```text\n')[1].rsplit('```',1)[0].strip()
    assert embedded==prompt
    unchanged='\n'.join(line for line in prompt.splitlines() if not line.startswith(('- 表定飞行时长','- 实际飞行时长','所有时间字段')))
    # Original user prompt except the two duration calculations and duration format.
    assert hashlib.sha256(unchanged.encode()).hexdigest()=='7272ae69571a6a40a63dfefcfa359058d9053e696d6eb5172e19a18a26d91533'
    assert all(example in prompt for example in ['2小时30分','0小时35分','2小时0分'])
    header=next(line for line in prompt.splitlines() if line.startswith('日期,航班号,'))
    assert len(next(csv.reader([header])))==19
    for line in prompt.splitlines():
        if line.startswith(('- 表定飞行时长','- 实际飞行时长')):
            assert all(term in line for term in ['完整日期','夏令时','UTC','Python','禁止猜测'])

def test_onboarding_local_links_and_tutorial_assets():
    for document in [ROOT/'README.md',*sorted((BASE/'docs').glob('*.md')),REF/'data-extraction.md',REF/'first-run.md',REF/'input-and-options.md']:
        text=document.read_text(encoding='utf-8')
        targets=re.findall(r'\[[^\]]*\]\(([^)]+)\)',text)+re.findall(r'<img\b[^>]*src="([^"]+)"',text)
        for target in targets:
            if '://' in target or target.startswith('#'):continue
            assert (document.parent/target.split('#')[0]).resolve().is_file(),(document.name,target)
    folder=BASE/'assets/tutorial'
    proof=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    assert not proof['originals_in_distribution'] and len(proof['assets'])==4
    for asset in proof['assets']:
        path=folder/asset['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==asset['sha256']
        with Image.open(path) as image:assert image.width>=800 and image.height>=1000
    assert not list(folder.glob('*.jpg'))
