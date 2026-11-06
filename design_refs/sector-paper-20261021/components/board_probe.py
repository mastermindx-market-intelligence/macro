#!/usr/bin/env python3
"""One capture.log probe line per board (SIC-V3-C06/C10/C15).

Usage: board_probe.py <png> <board_url> <current_workflow_key> [zh [allow.txt]]
  <png>        the frozen board; pixel samples at (30,300), (30,h/2), (w-40,h-60), (300,135)
  <board_url>  the URL the board was shot from. Mobile boards are shot through mobile_frame.html?src=<page>&…:
               the host <html> carries data-w/data-ovf copied from the 390px iframe document; the switcher and
               the ZH text are read from the inner document (same params) at the same width.
  key          expected aria-current="page" item of the six-link workflow switcher (brief|cycles)
  zh           also run zh_latin_grep.py (SIC-V3-C06) on the inner document, with the optional allow-file
"""
import pathlib, re, subprocess, sys
from urllib.parse import urlsplit, parse_qsl
from PIL import Image
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
def dump(url, width):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                           "--allow-file-access-from-files", f"--window-size={width},900", "--virtual-time-budget=4000", "--dump-dom", url],
                          capture_output=True, text=True).stdout
png, url, key = sys.argv[1], sys.argv[2], sys.argv[3]; zh = len(sys.argv) > 4 and sys.argv[4] == "zh"
im = Image.open(png).convert("RGB"); w, h = im.size
pts = [(30, 300), (30, h // 2), (w - 40, h - 60), (300, 135)]
px = " ".join(f"({x},{y})={im.getpixel((x, y))}".replace(" ", "") for x, y in pts)
width = 390 if w == 390 else 1440
host = dump(url, width)
u = urlsplit(url); q = dict(parse_qsl(u.query))
if u.path.endswith("mobile_frame.html") and "src" in q:
    inner_q = "&".join(f"{k}={v}" for k, v in q.items() if k != "src")
    inner_url = u._replace(path=str(pathlib.PurePosixPath(u.path).parent / q["src"]), query=inner_q).geturl()
    inner = dump(inner_url, width)
else:
    inner = host
m_w = re.search(r'data-w="(\d+)"', host); m_o = re.search(r'data-ovf="([^"]*)"', host)
links = re.findall(r'data-si-workflow="([^"]+)"', inner)
cur = re.findall(r'<a[^>]*aria-current="page"[^>]*>', inner)
cur_keys = [k for a in cur for k in re.findall(r'data-si-workflow="([^"]+)"', a)]
line = (f'{pathlib.Path(png).name} {w}x{h} {px} probe data-w="{m_w.group(1) if m_w else "?"}" data-ovf="{m_o.group(1) if m_o else "?"}" '
        f'switcher={len(links)} current={",".join(cur_keys) or "none"}{"" if cur_keys == [key] else " SWITCHER-MISMATCH"}')
if zh:
    tmp = pathlib.Path(png).with_suffix(".zh.dom.html"); tmp.write_text(inner, encoding="utf-8")
    r = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("zh_latin_grep.py")), str(tmp)] + sys.argv[5:6], capture_output=True, text=True)
    line += " " + r.stdout.strip(); tmp.unlink()
print(line)
