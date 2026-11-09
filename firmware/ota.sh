#!/bin/sh
# Push MURMUR firmware over Wi-Fi from talos. Usage: firmware/ota.sh [host]   (default its IP)
# Builds first. The board writes the OTHER slot and reboots into it; 3 bad boots roll it back.
set -eu
cd "$(dirname "$0")"
# ⚠️ by IP: after an OTA reboot, murmur.local can take a minute to resolve again (2026-11-03).
#   192.168.86.65 is a DHCP lease — reserve it on the router so it stays put.
# ★ find it by name: the router moves it (was .65, then .60 on 2026-11-06). Resolve murmur.local
#   ONCE to an IP, then use the IP (mDNS lags right after an OTA reboot).
HOST=${1:-$(dscacheutil -q host -a name murmur.local 2>/dev/null | awk '/ip_address/{print $2; exit}')}
HOST=${HOST:-murmur.local}
KEY=$(sed -n 's/#define OTA_KEY "\(.*\)"/\1/p' murmur/secrets.h)
./build.sh >/tmp/murmur-build.log 2>&1 || { tail -20 /tmp/murmur-build.log; exit 1; }
grep "Sketch uses" /tmp/murmur-build.log
before=$(curl -s -m 8 "http://$HOST:8070/status" | sed -n 's/.*"slot":"\([a-z0-9]*\)".*/\1/p')
echo "device slot before: ${before:-unreachable}"
curl -sS -m 180 --limit-rate 60k -H "X-Murmur-Key: $KEY" --data-binary @build/murmur.ino.bin \
     "http://$HOST:8070/update"; echo
for i in $(seq 1 30); do
  sleep 2
  st=$(curl -s -m 4 "http://$HOST:8070/status" || true)
  [ -n "$st" ] && { echo "after: $st"; exit 0; }
done
echo "device did not come back on Wi-Fi in 60 s"; exit 1
