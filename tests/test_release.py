import importlib.util,json
from pathlib import Path
from build import BASE
ROOT=BASE.parents[1]
def test_allowlisted_distribution():
    spec=importlib.util.spec_from_file_location('release',ROOT/'scripts/package_release.py');release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
    files=release.public_files()
    assert BASE/'plugin.json' in files and BASE/'LICENSE' in files
    assert ROOT/'.agents/plugins/marketplace.json' in files
    for name in ['data-extraction.md','agent-guide.md','development.md']:
        assert BASE/'docs'/name in files
    assert all(not any(x in release.EXCLUDED for x in p.relative_to(ROOT).parts) for p in files)
    assert not any(p.suffix.lower() in ['.xls','.xlsx'] for p in files)

def test_private_history_cannot_enter_public_package(tmp_path):
    spec=importlib.util.spec_from_file_location('release',ROOT/'scripts/package_release.py');release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
    release.ROOT=tmp_path
    plugin=tmp_path/'plugins/flight-atlas';plugin.mkdir(parents=True)
    import pytest
    for filename in release.PRIVATE_STATE:
        path=plugin/filename;path.write_text('{}',encoding='utf-8')
        with pytest.raises(ValueError,match='Private reporting state'):release.public_files()
        path.unlink()
def test_art_hashes_and_notices():
    import hashlib
    folder=BASE/'assets/silhouettes';hashes=json.loads((folder/'checksums.json').read_text(encoding='utf-8'))
    for name,digest in hashes.items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
    assert (BASE/'assets/data/pyecharts-assets-LICENSE').is_file()

def test_orthographic_assets_and_review_hashes():
    from models import FAMILIES
    folder=BASE/'assets/silhouettes'
    layout=json.loads((folder/'layout_v7.json').read_text(encoding='utf-8'))
    hashes=json.loads((folder/'checksums.json').read_text(encoding='utf-8'))
    provenance=json.loads((folder/'provenance.json').read_text(encoding='utf-8'))
    keys={family[0] for family in FAMILIES}
    assert set(layout)==set(provenance['assets'])==keys
    assert {p.name for p in folder.glob('*.png')}==set(hashes)=={k+'.png' for k in keys}
    assert 'orthographic' in provenance['projection']
    for key in keys:
        assert layout[key]['file']==key+'.png'
        assert provenance['assets'][key]['sha256']==hashes[key+'.png']
        assert provenance['assets'][key]['wheel_edit_prompt']

def test_uniform_aircraft_palette_and_alpha_audit():
    import hashlib
    import numpy as np
    from PIL import Image
    from models import FAMILIES
    folder=BASE/'assets/silhouettes'
    audit=json.loads((folder/'palette-audit.json').read_text(encoding='utf-8'))
    expected={'AB':[120,69,164],'CD':[22,92,145],'EF':[194,131,22]}
    assert audit['body_colors']==expected
    assert set(audit['assets'])=={f[0] for f in FAMILIES}
    for key,_,_,group,_,_ in FAMILIES:
        record=audit['assets'][key]
        raw=(folder/(key+'.png')).read_bytes()
        assert record['sha256']==hashlib.sha256(raw).hexdigest()
        with Image.open(folder/(key+'.png')) as image:rgba=np.array(image)
        assert record['alpha_unchanged']
        assert record['alpha_sha256']==hashlib.sha256(rgba[:,:,3].tobytes()).hexdigest()
        assert record['body_rgb']==expected[group] and record['body_pixels']>1000
        rgb=rgba[:,:,:3].astype('float32');body=np.array(expected[group],dtype='float32')
        vector=255-body
        t=np.clip(((rgb-body)*vector).sum(2)/(vector*vector).sum(),0,1)
        on_body_white_edge=(np.abs(rgb-(body+vector*t[:,:,None])).max(2)<=1.1)
        eyes=np.zeros(rgba.shape[:2],dtype=bool)
        x0,y0,x1,y1=record['cockpit_box'];eyes[y0:y1,x0:x1]=True
        visible=rgba[:,:,3]>0
        assert on_body_white_edge[visible & ~eyes].all(),key
        is_gray=(rgb==133).all(2);is_black=(rgb==0).all(2)
        assert not (is_gray & ~eyes & visible).any(),key
        assert not (is_black & ~eyes & visible).any(),key
        assert is_gray[eyes & visible].any(),key
        if key in {'A339','A350'}:assert is_black[eyes & visible].any(),key
        else:assert not is_black[visible].any(),key
