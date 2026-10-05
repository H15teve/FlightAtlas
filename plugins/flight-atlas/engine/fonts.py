"""Portable font discovery; no proprietary fonts are redistributed."""
import os
from pathlib import Path
from PIL import ImageFont

def font_path(bold=False,latin=False):
    override=os.environ.get('FLIGHT_ATLAS_FONT_BOLD' if bold else 'FLIGHT_ATLAS_FONT')
    roots=[Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts',Path('/usr/share/fonts/truetype'),Path('/usr/share/fonts/opentype/noto'),Path('/Library/Fonts')]
    names=(['arialbd.ttf','arial.ttf'] if latin else ['msyhbd.ttc' if bold else 'msyh.ttc','NotoSansCJK-Bold.ttc' if bold else 'NotoSansCJK-Regular.ttc','NotoSansSC-Regular.ttf'])
    if override and Path(override).is_file():return override
    for root in roots:
        for name in names:
            p=root/name
            if p.is_file():return str(p)
    if latin:
        for p in [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
            if p.is_file():return str(p)
    raise ValueError('需要中文字体：安装 Noto Sans CJK，或设置 FLIGHT_ATLAS_FONT / FLIGHT_ATLAS_FONT_BOLD。')

def font(size,bold=False,latin=False):return ImageFont.truetype(font_path(bold,latin),size)
