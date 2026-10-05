"""Whitespace changes must not change logo artwork placement or displayed size."""
from xml.etree import ElementTree as ET
import pytest
from PIL import Image,ImageDraw
from build import SVG
from design_v2 import airline_logo,CACHE

NS={'s':'http://www.w3.org/2000/svg'}

@pytest.mark.parametrize('suffix',['.png','.svg'])
@pytest.mark.parametrize('height',[38,70])
def test_different_canvases_produce_same_center_and_artwork_size(tmp_path,suffix,height):
    geometries=[]
    for index,(width,h,left,top) in enumerate([(160,60,10,10),(500,240,270,150)]):
        p=tmp_path/(str(index)+suffix)
        if suffix=='.svg':
            p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="0 0 {width} {h}"><rect x="{left}" y="{top}" width="100" height="20" fill="#124678"/></svg>',encoding='utf-8')
        else:
            image=Image.new('RGBA',(width,h));ImageDraw.Draw(image).rectangle((left,top,left+99,top+19),fill='#124678');image.save(p)
        drawing=SVG(300,100)
        previous=CACHE.get('logos',{})
        try:
            CACHE['logos']={'TEST':str(p)};airline_logo(drawing,'TEST',20,10,200,height)
        finally:CACHE['logos']=previous
        root=ET.fromstring(''.join(drawing.parts)+'</svg>');logo=root.find('s:svg',NS)
        x,y,w,hh=map(float,[logo.get(k) for k in ['x','y','width','height']])
        assert x+w/2==pytest.approx(120)
        assert y+hh/2==pytest.approx(10+height/2)
        assert w<=200 and hh<=height
        geometries.append((w,hh))
    assert geometries[0]==pytest.approx(geometries[1],abs=1)
