#!/bin/sh
# Flash MURMUR through the MacBook (the board's USB is on it; talos does the building).
# Uses the Mac's existing esptool only — nothing is installed there. Native USB port (/dev/cu.usbmodem*).
set -eu
H=nicks-macbook-pro
D=/tmp/murmur-flash
B0=$(find "$HOME/Library/Arduino15/packages/esp32/hardware/esp32" -name boot_app0.bin | head -1)
cd "$(dirname "$0")/build"
ssh -o BatchMode=yes $H "mkdir -p $D"
scp -q -o BatchMode=yes murmur.ino.bootloader.bin murmur.ino.partitions.bin murmur.ino.bin "$B0" $H:$D/
# ★ no buttons: a 1200-baud touch on MURMUR's own CDC port reboots it into the ROM bootloader.
# ⚠️ The bootloader's port appears a moment before it can be opened ("Device not configured"):
#   wait for it, then retry esptool a few times instead of a fixed sleep.
ssh -o BatchMode=yes $H "set -e
APP=\$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
# ⚠️ the touch MUST drop DTR (s.dtr=False) — without it the app ignores it and nothing reboots
[ -n \"\$APP\" ] && /opt/homebrew/bin/python3 -c \"import serial,time; s=serial.Serial('\$APP',1200); s.dtr=False; time.sleep(0.3); s.close()\" || true
for n in 1 2 3 4 5; do
  sleep 3
  P=\$(ls /dev/cu.usbmodem* 2>/dev/null | grep -v \"\$APP\" | head -1); [ -z \"\$P\" ] && P=\$(ls /dev/cu.usbmodem* | head -1)
  echo port \$P
  if /opt/homebrew/bin/esptool --chip esp32s3 --port \$P --baud 921600 --before default-reset --after hard-reset \
       write-flash -z 0x0 $D/murmur.ino.bootloader.bin 0x8000 $D/murmur.ino.partitions.bin \
       0xe000 $D/boot_app0.bin 0x10000 $D/murmur.ino.bin; then rm -rf $D; exit 0; fi
  echo retry \$n
done
exit 1"
