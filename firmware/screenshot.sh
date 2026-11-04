#!/bin/sh
# Grab MURMUR's screen as a PNG on talos: firmware/screenshot.sh [out.png] [D]  (D = toggle demo first)
set -eu
OUT=${1:-/tmp/murmur-screen.png}
if [ "${2:-}" = "--wifi" ]; then                     # over Wi-Fi, no USB needed
  curl -s -m 20 -o /tmp/murmur-shot.raw http://192.168.86.65:8070/screen
else
ssh -o BatchMode=yes nicks-macbook-pro "/opt/homebrew/bin/python3 - ${2:-}" > /tmp/murmur-shot.raw <<'PY'
import serial, glob, sys, time
p = sorted(glob.glob('/dev/cu.usbmodem*'))[0]
s = serial.Serial(p, 115200, timeout=3)
if len(sys.argv) > 1 and sys.argv[1] == 'D':
    s.write(b'D'); time.sleep(4)
s.reset_input_buffer(); s.write(b's')
buf = b''
t = time.time()
while b'SHOT' not in buf and time.time() - t < 5: buf += s.read(64)
buf = buf[buf.index(b'SHOT') + 4:]
need = 240 * 320 * 2
while len(buf) < need and time.time() - t < 15: buf += s.read(need - len(buf))
sys.stdout.buffer.write(buf[:need])
PY
fi
~/Projects/synth-case/.venv/bin/python - "$OUT" <<'PY'
import sys
from PIL import Image
raw = open('/tmp/murmur-shot.raw', 'rb').read()
img = Image.new('RGB', (240, 320))
px = img.load()
for i in range(240 * 320):
    v = (raw[2 * i] << 8) | raw[2 * i + 1]          # LGFX sprites store RGB565 byte-swapped
    px[i % 240, i // 240] = (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)
img.resize((480, 640), Image.NEAREST).save(sys.argv[1])
print(sys.argv[1], len(raw))
PY
