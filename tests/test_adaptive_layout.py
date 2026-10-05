"""Counts stay outside bars; sparse airport sections do not stretch rows."""
import math
from design_v2 import airline_bar_geometry,airline_panel,airport_panel
import pytest

@pytest.mark.parametrize('bars,singles',[(1,0),(3,1),(8,5),(15,12),(30,21),(0,13),(0,0)])
def test_airline_inventory_spacing_and_grid_wrapping(bars,singles):
    panel=airline_panel(bars,singles,unknown=True)
    assert panel['single_rows']==math.ceil(singles/4)
    assert panel['content_bottom']<=panel['height']-52
    last_bar_bottom=104+(bars-1)*panel['row_pitch']+38 if bars else 104
    unknown_baseline=104+bars*panel['row_pitch']+26
    assert unknown_baseline>last_bar_bottom
    assert panel['grid_caption']+26>=unknown_baseline+48
    assert panel['grid_top']>=panel['grid_caption']+26+26
    # Grid follows content, independent of the map's minimum column height.
    assert panel['grid_top']-unknown_baseline==98
    assert panel['row_pitch']>=52

def test_airline_counts_have_separate_reserved_space():
    for largest in [9,99,136,1000,10000,1000000]:
        layout=airline_bar_geometry([1,largest])
        assert layout['bar_x']+layout['bar_width']<=layout['count_left']-20
        assert layout['count_x']<835
        assert 0<layout['bar_width']<=270

def test_airport_panel_grows_only_as_needed_and_keeps_v3_words():
    panels=[]
    for count in [4,17,60]:
        rank=[(f'A{i:02d}',max(1,120//(i+1))) for i in range(count)]
        bars=[entry for entry in rank if entry[1]>=3]
        panel=airport_panel(rank,bars);panels.append(panel)
        assert len(panel['placements'])==count
        assert {p['airport'] for p in panel['placements']}=={a for a,_ in rank}
        assert panel['pitch']<=62
        for p in panel['placements']:
            assert p['font_size']==round(35*math.log2(p['visits']+1))
            assert p['box'][1]>=0 and p['box'][3]<=panel['height']
    # DejaVu's wider glyphs need slightly more room than Windows Arial.
    assert panels[0]['height']<1000
    assert panels[0]['height']<panels[1]['height']<panels[2]['height']
    assert panels[0]['code_size']>panels[2]['code_size']

def test_airport_panel_uses_space_beyond_spiral_with_wider_font(monkeypatch):
    import design_v2
    original=design_v2.ImageFont.truetype
    class WiderFont:
        def __init__(self,*args,**kwargs):self.base=original(*args,**kwargs)
        def getbbox(self,text):
            left,top,right,bottom=self.base.getbbox(text)
            return left,top,left+(right-left)*1.25,bottom
    monkeypatch.setattr(design_v2.ImageFont,'truetype',WiderFont)
    rank=[(f'A{i:02d}',max(1,120//(i+1))) for i in range(60)]
    panel=airport_panel(rank,[entry for entry in rank if entry[1]>=3])
    assert len(panel['placements'])==60
    for i,p in enumerate(panel['placements']):
        assert p['font_size']==round(35*math.log2(p['visits']+1))
        a=p['box'];assert 1190<=a[0]<a[2]<=2300 and 0<=a[1]<a[3]<=panel['height']
        for q in panel['placements'][:i]:
            b=q['box']
            assert not (a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1])
