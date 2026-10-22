#!/usr/bin/env python3
"""Render authentic v2 Canvas morph as README-embeddable GIF.

Uses headless Chromium only during generation; the GitHub README displays
an ordinary GIF with no JS, iframe, or runtime needed on the profile.

Usage:
  python scripts/update_contributions.py --demo
  python scripts/render_profile_gif.py --demo
  python scripts/update_contributions.py  # GITHUB_TOKEN and GITHUB_USERNAME required
  python scripts/render_profile_gif.py
"""
from __future__ import annotations
import argparse
import io
import json
import os
import shutil
from pathlib import Path

from update_contributions import validate_payload

ROOT = Path(__file__).resolve().parent.parent
FRAME_SIZE = (980, 780)

# The visible image has constant dimensions while the Canvas inside it
# genuinely morphs between 2D and 3D with the same world-space cuboids.
FIXED_CARD_CSS = """
html, body { width: 100%; height:auto; background:var(--background,#fff); }
.page { margin:0; width:980px; height:780px; max-width:none; min-height:0; padding:0;
        display:flex; align-items:center; justify-content:center; }
.card { width:980px; flex:none; }
.preferences { display:none; }
"""


def load_html() -> str:
    src = (ROOT / 'docs/index.html').read_text(encoding='utf8')
    css = (ROOT / 'docs/skyline.css').read_text(encoding='utf8')
    js = (ROOT / 'docs/skyline.js').read_text(encoding='utf8')
    src = src.replace('<link rel="stylesheet" href="./skyline.css">', f'<style>{css}\n{FIXED_CARD_CSS}</style>')
    src = src.replace('<script src="./skyline.js" defer></script>', f'<script>{js}</script>')
    return src


def frames_for_loop():
    # Uniform t sampling preserves the original 1300 ms easing curve and the
    # left-to-right bar-rise wave. Endpoints are held to make loop readable.
    # 26 * 50ms = 1300ms in either direction; GIF timings use 10ms units.
    # Endpoint delays include their first 50ms transition interval.
    seq = [(0.0, 1150)]
    seq += [(i/26, 50) for i in range(1,26)]
    seq += [(1.0, 2450)]
    seq += [(i/26, 50) for i in range(25,0,-1)]
    return seq


def render(*, demo=False, quality=256, light=False):
    input_path = ROOT / ('preview/contributions-demo.json' if demo else 'contributions.json')
    if not input_path.exists():
        raise SystemExit(f'Missing {input_path}; run update_contributions.py first')
    data = json.loads(input_path.read_text(encoding='utf8'))
    try:
        data = validate_payload(data, allow_demo=demo)
    except (ValueError, TypeError, KeyError) as exc:
        raise SystemExit(f'Refusing unverified contribution data: {exc}') from exc
    days = data['days']
    from PIL import Image
    from playwright.sync_api import sync_playwright

    outputs = ROOT / 'preview' if demo else ROOT
    outputs.mkdir(parents=True, exist_ok=True)
    outgif = outputs / ('sample-preview.gif' if demo else 'contribution-skyline.gif')
    outpng = outputs / ('sample-3d.png' if demo else 'contribution-skyline-3d.png')
    seq = frames_for_loop()
    ims = []
    print(f'Generating {len(seq)} browser-rendered morph frames for {data.get("username")}...')
    with sync_playwright() as pw:
        launch = {'headless': True, 'args': ['--no-sandbox']}
        if os.environ.get('SKYLINE_BROWSER_CHANNEL'):
            launch['channel'] = os.environ['SKYLINE_BROWSER_CHANNEL']
        elif shutil.which('chromium'):
            launch['executable_path'] = shutil.which('chromium')
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport={'width':FRAME_SIZE[0],'height':FRAME_SIZE[1]}, device_scale_factor=1)
        page.set_content(load_html(), wait_until='load')
        # A renderer page has no HTTP dataset; inject validated days below.
        page.wait_for_function('window.__skyline')
        page.evaluate('''({days,demo,light,generatedAt,username}) => {
          const g = window.__skyline;
          if(g.entranceObs)g.entranceObs.disconnect();
          g.setData(days, demo);
          document.querySelectorAll('.toolbar button,.toolbar select').forEach(control=>control.disabled=false);
          document.documentElement.dataset.dataState='ready';
          document.getElementById('empty-state').hidden=true;
          document.getElementById('data-status').textContent=demo?'SAMPLE DATA · appearance preview only · not trynabe activity':`@${username} · GitHub contribution snapshot · ${generatedAt.slice(0,10)} UTC`;
          document.getElementById('help').textContent = '2D → 3D · Open the linked website to rotate and explore';
          g.dark=!light;document.documentElement.dataset.theme=light?'light':'dark';
          g.yawGoal = g.yawOffset = g.elevGoal = g.elevOffset = 0;
          g.hoverIndex = g.pinnedIndex = g.focusedIndex = -1;
          g.lastTime = 0;
          g.viewTarget = g.t = 0;
          g.render(performance.now());
        }''', {'days': days, 'demo': demo, 'light': light, 'generatedAt': data['generatedAt'], 'username': data['username']})
        locator = page.locator('.page')
        for idx, (t, ms) in enumerate(seq):
            page.evaluate('''t => {
              const g = window.__skyline;
              if(g.raf) { cancelAnimationFrame(g.raf); g.raf = 0; }
              g.lastTime=0; g.t=t; g.viewTarget=t>=.5?1:0; g.setButtons();
              g.viewTarget=t; g.render(performance.now());
              document.getElementById('help').textContent='Click to explore · drag to orbit on the website';
            }''', t)
            # PNG bytes -> Pillow, no intermediate screenshots written to disk.
            png = locator.screenshot(type='png', animations='disabled', timeout=12000)
            im = Image.open(io.BytesIO(png)).convert('RGB')
            if im.size != FRAME_SIZE:
                raise RuntimeError(f'Unexpected frame size: {im.size}')
            ims.append(im)
            if t == 1.0:
                im.save(outpng, optimize=True)
            if demo and t == 0.0 and idx == 0:
                im.save(outputs / 'sample-2d.png', optimize=True)
        browser.close()

    # One common palette for all frames prevents palette flicker while morphing.
    swatches = Image.new('RGB', (490, len(ims) * 155), 'white')
    for i, im in enumerate(ims):
        swatches.paste(im.resize((490,155), Image.Resampling.BILINEAR), (0,i*155))
    master_palette = swatches.quantize(colors=quality, method=Image.Quantize.MEDIANCUT)
    # Keep the exact UI colors so thin white/muted text survives GIF quantization.
    palette = master_palette.getpalette()
    ui_colors = ['#0a0a0a','#fafafa','#a3a3a3','#262626','#39d353','#ffffff','#737373','#171717']
    for index,color in enumerate(ui_colors, start=quality-len(ui_colors)):
        palette[index*3:index*3+3] = [int(color[pos:pos+2],16) for pos in (1,3,5)]
    master_palette.putpalette(palette)
    converted = [im.quantize(palette=master_palette, dither=Image.Dither.NONE) for im in ims]
    durations = [d for _, d in seq]
    converted[0].save(outgif, save_all=True, append_images=converted[1:],
                      duration=durations, loop=0, optimize=True, disposal=2)
    print(f'Created {outgif.relative_to(ROOT)} ({outgif.stat().st_size/1024/1024:.2f} MB)')
    print(f'Created {outpng.relative_to(ROOT)} ({outpng.stat().st_size/1024:.0f} KB)')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--demo', action='store_true', help='Use simulated sample, never publish as real')
    p.add_argument('--quality', type=int, default=256, help='GIF palette colors (16..256)')
    p.add_argument('--light', action='store_true', help='Render a light card instead of the default GitHub dark theme')
    a = p.parse_args()
    render(demo=a.demo, quality=max(16,min(256,a.quality)), light=a.light)

if __name__ == '__main__':
    main()
