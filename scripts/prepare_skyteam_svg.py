"""Developer-only cleanup of the licensed Commons vector trace's black matte.

Keeps every blue path's geometry. Converts its black/white antialias mixtures
to navy plus opacity; neutral background paths are removed. Not a photo editor.
Input must be the recorded Commons source, not arbitrary user artwork.
"""
import argparse,hashlib,re
from pathlib import Path
from xml.etree import ElementTree as ET

SOURCE_SHA='2638ea2c0f55124a22a66174959d51b1c5c77133dde655bd826b9a736d4efb6c'

def prepare(source,target):
    raw=Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('Unexpected Commons source hash')
    root=ET.fromstring(raw)
    ET.register_namespace('','http://www.w3.org/2000/svg')
    for element in list(root):
        match=re.search(r'fill:#([0-9a-f]{6})',element.get('style',''),re.I)
        if not match:raise ValueError('Unexpected source paint')
        r,g,b=[int(match[1][i:i+2],16) for i in [0,2,4]]
        if r!=g:raise ValueError('Unexpected non-blue source color')
        opacity=max(0,min(1,(b-r)/102))
        if not opacity:root.remove(element);continue
        element.attrib.pop('style',None)
        element.set('fill','#000066')
        if opacity<1:element.set('fill-opacity',format(opacity,'.5f'))
    root.set('viewBox','0 0 1109 1113')
    Path(target).write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();prepare(args.input,args.output)
