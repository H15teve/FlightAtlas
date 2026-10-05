"""Developer-only, user-approved color normalization of built-in aircraft PNGs.

Never changes alpha, canvas size or gear geometry. Not used on user photos.
Cockpit bounds and window fills must be visually reviewed after processing.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'plugins/flight-atlas/engine'))
from models import FAMILIES

BODY = {'AB': (120, 69, 164), 'CD': (22, 92, 145), 'EF': (194, 131, 22)}
WHITE = (255, 255, 255)
GLASS = (133, 133, 133)
BLACK = (0, 0, 0)


def components(mask):
    """Small boolean-mask components, returning coordinates and bounding boxes."""
    work = mask.copy()
    height, width = work.shape
    for sy, sx in zip(*np.where(mask)):
        if not work[sy, sx]:
            continue
        work[sy, sx] = False
        queue = deque([(int(sy), int(sx))])
        pixels = []
        while queue:
            y, x = queue.popleft()
            pixels.append((y, x))
            for ny, nx in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                if 0 <= ny < height and 0 <= nx < width and work[ny, nx]:
                    work[ny, nx] = False
                    queue.append((ny, nx))
        ys, xs = zip(*pixels)
        yield pixels, (min(xs), min(ys), max(xs)+1, max(ys)+1)


def cockpit_box(rgba, bbox):
    """Find the contiguous neutral-gray glass cluster near the nose, not gear."""
    x0, y0, x1, y1 = bbox
    w, h = x1-x0, y1-y0
    crop = rgba[y0+int(.15*h):y0+int(.80*h), x0:x0+int(.15*w)]
    rgb = crop[:, :, :3].astype(np.int16)
    neutral = rgb.max(2)-rgb.min(2) < 26
    level = rgb.mean(2)
    mask = neutral & (level > 55) & (level < 210) & (crop[:, :, 3] > 220)
    joined = np.array(Image.fromarray(mask.astype('uint8')*255).filter(ImageFilter.MaxFilter(9))) > 0
    clusters = list(components(joined))
    if not clusters:
        raise ValueError('No cockpit glass cluster found; manual bounds required')
    _, (a, b, c, d) = max(clusters, key=lambda item: len(item[0]))
    return (x0+a, y0+int(.15*h)+b, x0+c, y0+int(.15*h)+d)


def enclosed_window_fills(rgb, alpha, bbox):
    """Fill small white-enclosed body-color cabin-window interiors, not doors.

    Neutral metal engine patches are excluded. This color-only step preserves
    original rounded window contours rather than painting rectangular boxes.
    """
    x0, y0, x1, y1 = bbox
    w, h = x1-x0, y1-y0
    region = rgb[y0+int(.22*h):y0+int(.84*h), x0+int(.15*w):x1]
    a = alpha[y0+int(.22*h):y0+int(.84*h), x0+int(.15*w):x1]
    core = (region.min(2) >= 225) & (a > 220)
    result = np.zeros(alpha.shape, dtype=bool)
    count = 0
    for _, (left, top, right, bottom) in components(core):
        bw, bh = right-left, bottom-top
        if not (3 <= bw <= .019*w and 3 <= bh <= .06*h and .35 <= bw/bh <= 1.7):
            continue
        patch = core[top:bottom, left:right]
        exterior = np.zeros(patch.shape, dtype=bool)
        queue = deque()
        for yy in range(bh):
            for xx in range(bw):
                if (yy in (0, bh-1) or xx in (0, bw-1)) and not patch[yy, xx]:
                    exterior[yy, xx] = True
                    queue.append((yy, xx))
        while queue:
            yy, xx = queue.popleft()
            for ny, nx in ((yy-1, xx), (yy+1, xx), (yy, xx-1), (yy, xx+1)):
                if 0 <= ny < bh and 0 <= nx < bw and not patch[ny, nx] and not exterior[ny, nx]:
                    exterior[ny, nx] = True
                    queue.append((ny, nx))
        holes = ~patch & ~exterior
        if not holes.any():
            continue
        interior = region[top:bottom, left:right][holes]
        # White-enclosed gray exhaust/metal parts are NOT cabin windows.
        if float((interior.max(1)-interior.min(1)).mean()) < 40:
            continue
        yy = y0+int(.22*h)+top
        xx = x0+int(.15*w)+left
        result[yy:yy+bh, xx:xx+bw] |= holes
        count += 1
    return result, count


def normalize(source, destination, key, group):
    with Image.open(source) as image:
        if image.mode != 'RGBA':
            raise ValueError('RGBA required: '+key)
        rgba = np.array(image)
        bbox = image.getchannel('A').point(lambda n: 255 if n > 220 else 0).getbbox()
    alpha = rgba[:, :, 3].copy()
    rgb = rgba[:, :, :3].astype(np.float32)
    body = np.array(BODY[group], dtype=np.float32)
    eye_box = cockpit_box(rgba, bbox)
    eyes = np.zeros(alpha.shape, dtype=bool)
    x0, y0, x1, y1 = eye_box
    eyes[y0:y1, x0:x1] = True
    white = (rgb.min(2) >= 235) & (alpha > 0)
    # Retain white-line antialiasing only immediately beside real white cores;
    # broad body gradients are flattened rather than misread as white coverage.
    near_white = np.array(Image.fromarray(white.astype('uint8')*255).filter(ImageFilter.MaxFilter(3))) > 0
    vector = 255-body
    t = np.clip(((rgb-body)*vector).sum(2)/float((vector*vector).sum()), 0, 1)
    t[~near_white | (t < .20)] = 0
    t[white] = 1
    result = np.rint(body+(255-body)*t[:, :, None]).astype('uint8')
    gray = (rgb.max(2)-rgb.min(2) < 35) & (rgb.mean(2) < 220) & eyes & (alpha > 0)
    result[gray] = GLASS
    dark = (rgb.max(2) < 65) & eyes & (alpha > 0)
    # Only the selected A350/A330neo profiles carry an external black mask.
    # Other cockpit panes use white frame contours, including C919 and B767.
    result[dark] = BLACK if key in {'A350', 'A339'} else WHITE
    # Only the A340 input retains hollow cabin-window interiors after the edits.
    # Do not mistake small outlined access panels on other models for windows.
    if key == 'A340':
        fills, window_count = enclosed_window_fills(rgba[:, :, :3], alpha, bbox)
    else:
        fills, window_count = np.zeros(alpha.shape, dtype=bool), 0
    result[fills & ~eyes] = WHITE
    result[alpha == 0] = BODY[group]
    output = np.dstack((result, alpha))
    assert np.array_equal(output[:, :, 3], rgba[:, :, 3])
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(output).save(destination)
    gray_outside = (result.max(2)-result.min(2) == 0) & (result.mean(2) < 230) & ~eyes & (alpha > 220)
    if gray_outside.any():
        raise ValueError('Neutral non-cockpit fill survived: '+key)
    return {
        'file': key+'.png', 'group': group, 'body_rgb': list(BODY[group]),
        'cockpit_box': list(eye_box), 'alpha_unchanged': True,
        'alpha_sha256': hashlib.sha256(alpha.tobytes()).hexdigest(),
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'filled_window_interiors': window_count, 'neutral_pixels_outside_cockpit': 0,
        'body_pixels': int(((result == body).all(2) & (alpha > 220)).sum()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Use a separate output folder and visually review before installation')
    audit = {'revision': '2026-10-04-flat-palette', 'authorization': 'Explicit user approval for programmatic color normalization',
             'body_colors': {k: list(v) for k, v in BODY.items()}, 'white': list(WHITE), 'glass': list(GLASS),
             'black': list(BLACK), 'antialiasing': 'Original alpha unchanged; internal white-edge coverage retained', 'assets': {}}
    for key, _, _, group, _, _ in FAMILIES:
        audit['assets'][key] = normalize(args.input/(key+'.png'), args.output/(key+'.png'), key, group)
    (args.output/'palette-audit.json').write_text(json.dumps(audit, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'normalized': len(audit['assets']), 'output': str(args.output), 'alpha_changed': False}))


if __name__ == '__main__':
    main()
