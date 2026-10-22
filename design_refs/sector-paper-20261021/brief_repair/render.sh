#!/bin/zsh
# Render the Brief specimen boards 23–27 with headless Chrome at 1x.
# Usage: ./render.sh [out_dir]   (default: ../../../mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal)
set -eu
here="${0:A:h}"
out="${1:-$here/../../../mockups/refs/reference_integrity/sector-intelligence-cycles-20261021/proposal}"
chrome="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
measure() { # width url -> document height (+40 px)
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --allow-file-access-from-files --window-size="$1,900" --dump-dom "$2" 2>/dev/null | /usr/bin/grep -o -E 'data-h="[0-9]+"' | head -1 | /usr/bin/grep -o -E '[0-9]+' | awk '{print $1+40}'
}
shot() { # name width height url
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --allow-file-access-from-files --window-size="$2,$3" --screenshot="$out/$1.png" "$4" >/dev/null 2>&1
  python3 -c 'import struct,sys;b=open(sys.argv[1],"rb").read(24);print(sys.argv[1].split("/")[-1],struct.unpack(">II",b[16:24]))' "$out/$1.png"
}
B="file://$here/brief.html"
C="file://$here/coverage_matrix.html"
M="file://$here/mobile_frame.html?src=brief.html"  # headless Chrome clamps window width to >=500: mobile boards render inside a 390px iframe host
shot 23-brief-desktop-light-en 1440 "${H23:-$(measure 1440 "$B?theme=light&lang=en")}" "$B?theme=light&lang=en"
shot 24-brief-desktop-dark-en  1440 "${H24:-$(measure 1440 "$B?theme=dark&lang=en")}" "$B?theme=dark&lang=en"
shot 25-brief-mobile-dark-zh    390 "${H25:-$(measure 390 "$M&theme=dark&lang=zh")}" "$M&theme=dark&lang=zh"
shot 26-brief-mobile-light-en   390 "${H26:-$(measure 390 "$M&theme=light&lang=en&state=locked")}" "$M&theme=light&lang=en&state=locked"
shot 27-coverage-matrix-desktop-light-en 1440 "${H27:-$(measure 1440 "$C?theme=light&lang=en")}" "$C?theme=light&lang=en"
# wave 2 (SIC-V2-C12): the three Brief coverage-matrix GAP cells become drawn boards
shot 32-brief-desktop-light-zh 1440 "${H32:-$(measure 1440 "$B?theme=light&lang=zh")}" "$B?theme=light&lang=zh"
shot 33-brief-desktop-dark-zh  1440 "${H33:-$(measure 1440 "$B?theme=dark&lang=zh")}" "$B?theme=dark&lang=zh"
shot 37-brief-mobile-dark-en    390 "${H37:-$(measure 390 "$M&theme=dark&lang=en")}" "$M&theme=dark&lang=en"
