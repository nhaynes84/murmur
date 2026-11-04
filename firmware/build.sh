#!/bin/sh
# Build MURMUR on talos. Output: firmware/build/murmur.ino.merged.bin (+ app/bootloader/partitions).
# USB-OTG (TinyUSB) = MIDI + CDC on the native port; CDC lets a 1200-baud touch re-enter the bootloader.
set -eu
cd "$(dirname "$0")"
FQBN="esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=cdc,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,FlashMode=qio"
# the USB name must be set at BUILD time: with CDC on boot, USB enumerates before setup() runs
"$HOME/.local/bin/arduino-cli" compile --fqbn "$FQBN" --output-dir build \
  --build-property 'build.defines=-DUSB_PRODUCT="MURMUR" -DUSB_MANUFACTURER="MURMUR"' \
  murmur "$@"
