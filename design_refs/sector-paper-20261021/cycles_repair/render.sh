#!/bin/zsh
# Render the Cycles corrections specimen boards 28–31 with headless Chrome at 1x.
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
B="file://$here/cycles.html"
M="file://$here/mobile_frame.html?src=cycles.html"  # headless Chrome clamps window width to >=500: mobile boards render inside a 390px iframe host
shot 28-cycles-desktop-light-en 1440 "${H28:-$(measure 1440 "$B?theme=light&lang=en")}" "$B?theme=light&lang=en"
shot 29-cycles-desktop-dark-en  1440 "${H29:-$(measure 1440 "$B?theme=dark&lang=en")}" "$B?theme=dark&lang=en"
shot 30-cycles-mobile-dark-zh    390 "${H30:-$(measure 390 "$M&theme=dark&lang=zh")}" "$M&theme=dark&lang=zh"
shot 31-cycles-mobile-light-en   390 "${H31:-$(measure 390 "$M&theme=light&lang=en&state=incompatible_generation")}" "$M&theme=light&lang=en&state=incompatible_generation"
# wave 2 (SIC-V2-C12): Cycles ZH desktop both themes + light ZH mobile
shot 34-cycles-desktop-light-zh 1440 "${H34:-$(measure 1440 "$B?theme=light&lang=zh")}" "$B?theme=light&lang=zh"
shot 35-cycles-desktop-dark-zh  1440 "${H35:-$(measure 1440 "$B?theme=dark&lang=zh")}" "$B?theme=dark&lang=zh"
shot 36-cycles-mobile-light-zh   390 "${H36:-$(measure 390 "$M&theme=light&lang=zh")}" "$M&theme=light&lang=zh"
