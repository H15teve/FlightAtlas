"""Public preview artwork must not carry private records or hidden metadata."""
import csv,hashlib,importlib.util,json
from pathlib import Path
from PIL import Image
from build import BASE

ROOT=BASE.parents[1]

def test_preview_hashes_licenses_and_no_hidden_image_metadata():
    folder=BASE/'docs/previews'
    proof=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    assert proof['records']==240 and proof['original_row_fields_copied']==[]
    assert proof['report_images_license']=='CC BY-SA 4.0'
    assert set(proof['images'])=={'flight-passport.png','flight-atlas.png'}
    for name,digest in proof['images'].items():
        path=folder/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
        with Image.open(path) as image:
            assert image.width>=1000 and image.height>=1500
            assert not image.getexif() and not image.info
    for asset in proof['assets'].values():
        assert asset['source'].startswith('https://commons.wikimedia.org/wiki/File:')
        assert asset['credit'] and asset['license'] in {'Public domain','Public domain + CC0-1.0','CC BY-SA 3.0'}
    for code in ['CA','CZ','BA']:
        assert proof['assets'][code]['variant']=='complete horizontal symbol + original wordmark'
        assert proof['assets'][code]['components'][0]['license']=='CC0-1.0'
    exception=proof['assets']['CA']['demo_exception']
    assert exception['scope']=='public-readme-demo' and exception['user_approved']
    assert exception['affects_user_report_selection'] is False
    assert exception['selected_variant']=='English AIR CHINA wordmark with phoenix symbol'
    assert not list(folder.glob('*.csv')) and not list(folder.glob('*.jpg'))
    assert 'C:' not in json.dumps(proof) and '.local' not in json.dumps(proof)

def test_demo_does_not_copy_private_row_fields(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('demo_builder',ROOT/'scripts/build_readme_demo.py')
    demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)
    source=tmp_path/'source.csv'
    original='日期,航班号,出发机场,到达机场,机型,注册号,座位号\n2005-07-01,MF9999,ADL,CNS,B738,PRIVATE-001,12A\n'
    source.write_text(original,encoding='utf-8')
    work=tmp_path/'work'
    monkeypatch.setattr(demo,'assets',lambda folder:({k:'fake.svg' for k in demo.ART},{k:{'source':'synthetic test','credit':'test','license':'Public domain'} for k in demo.ART}))
    monkeypatch.setattr(demo.sys,'argv',['demo','--source',str(source),'--work',str(work)])
    demo.main()
    public_candidate=(work/'synthetic.csv').read_text(encoding='utf-8')
    assert all(value not in public_candidate for value in ['2005-07-01','MF9999','ADL','CNS','PRIVATE-001','12A'])
    assert source.read_text(encoding='utf-8')==original
    rows=list(csv.DictReader(public_candidate.splitlines()))
    assert len(rows)==240 and all(r['注册号'].startswith('DEMO-') for r in rows)
    assert all(r['座位号']==r['含税票价']==r['舱位等级']=='' for r in rows)
