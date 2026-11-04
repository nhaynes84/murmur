// MURMUR — Wi-Fi + over-the-air updates from talos (firmware/ota.sh).
//   POST /update   raw firmware .bin in the body, header X-Murmur-Key: <OTA_KEY>  -> writes the
//                  OTHER app slot, reboots into it.
//   GET  /status   JSON: version, ip, slot, uptime, pulse rate, plant, settings.
//   POST /reboot   (keyed)
// ★ ROLLBACK: a boot-failure counter in NVS. Every boot bumps it; 60 s of healthy uptime clears it.
//   Three failed boots in a row -> boot the previous slot. A bad OTA can't brick it.
// Wi-Fi is non-blocking: no network, MURMUR still plays (Bluetooth MIDI doesn't need it).
#pragma once
#include <WiFi.h>
#include <WebServer.h>
#include <Update.h>
#include <ESPmDNS.h>
#include <esp_ota_ops.h>
#include "secrets.h"

namespace ota {
static WebServer server(8070);
static bool started = false, healthy = false;
static const char* VERSION = __DATE__ " " __TIME__;
static String (*statusExtra)() = nullptr;    // the sketch adds its own fields
static const uint8_t* (*screen)() = nullptr;  // the framebuffer, for GET /screen

inline void rollbackCheck() {
  Preferences p;
  p.begin("murmur-boot", false);
  uint8_t fails = p.getUChar("fails", 0) + 1;
  p.putUChar("fails", fails);
  p.end();
  if (fails >= 3) {
    const esp_partition_t* other = esp_ota_get_next_update_partition(nullptr);
    esp_app_desc_t d;
    if (other && esp_ota_get_partition_description(other, &d) == ESP_OK) {
      Preferences q; q.begin("murmur-boot", false); q.putUChar("fails", 0); q.end();
      esp_ota_set_boot_partition(other);
      esp_restart();
    }
  }
}

inline bool keyed() { return server.header("X-Murmur-Key") == OTA_KEY; }

inline void begin() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("murmur");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

inline void startServer() {
  static const char* hdrs[] = {"X-Murmur-Key"};
  server.collectHeaders(hdrs, 1);
  server.on("/status", HTTP_GET, []() {
    String j = String("{\"version\":\"") + VERSION + "\",\"ip\":\"" + WiFi.localIP().toString() +
               "\",\"slot\":\"" + esp_ota_get_running_partition()->label + "\",\"uptime_s\":" +
               (millis() / 1000) + (statusExtra ? statusExtra() : String("")) + "}";
    server.send(200, "application/json", j);
  });
  // GET /screen: the live framebuffer (240x320 RGB565 as stored in the sprite) — lets talos check
  //   the UI without a USB cable. firmware/screenshot.sh --wifi turns it into a PNG.
  server.on("/screen", HTTP_GET, []() {
    const uint8_t* b = screen ? screen() : nullptr;
    if (!b) { server.send(503, "text/plain", "no frame"); return; }
    server.setContentLength(240 * 320 * 2);
    server.send(200, "application/octet-stream", "");
    for (size_t off = 0; off < 240 * 320 * 2; off += 4096)
      server.sendContent((const char*)b + off, min((size_t)4096, (size_t)(240 * 320 * 2 - off)));
  });
  server.on("/reboot", HTTP_POST, []() {
    if (!keyed()) { server.send(403, "text/plain", "key"); return; }
    server.send(200, "text/plain", "rebooting");
    delay(200);
    esp_restart();
  });
  server.on("/update", HTTP_POST,
    []() {   // after the body
      if (!keyed()) { server.send(403, "text/plain", "key"); return; }
      bool ok = !Update.hasError() && Update.isFinished();
      server.send(ok ? 200 : 500, "text/plain", ok ? "ok, rebooting" : Update.errorString());
      if (ok) { delay(300); esp_restart(); }
    },
    []() {   // the body, streamed (raw --data-binary)
      if (!keyed()) return;
      HTTPRaw& r = server.raw();
      if (r.status == RAW_START) Update.begin(UPDATE_SIZE_UNKNOWN);
      else if (r.status == RAW_WRITE) Update.write(r.buf, r.currentSize);
      else if (r.status == RAW_END) Update.end(true);
      else if (r.status == RAW_ABORTED) Update.abort();
    });
  server.begin();
  MDNS.begin("murmur");
  MDNS.addService("http", "tcp", 8070);
  started = true;
  Serial.printf("ota: %s:8070 (slot %s, %s)\n", WiFi.localIP().toString().c_str(),
                esp_ota_get_running_partition()->label, VERSION);
}

// the settings toggle: off = radio fully off (saves ~30-80 mA); on = join again
inline void enable(bool on) {
  if (on) { begin(); return; }
  if (started) { server.stop(); MDNS.end(); started = false; }
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
}

inline void tick() {
  if (!healthy && millis() > 60000) {        // survived a minute: this build is good
    Preferences p; p.begin("murmur-boot", false); p.putUChar("fails", 0); p.end();
    healthy = true;
  }
  if (!started && WiFi.getMode() != WIFI_OFF && WiFi.status() == WL_CONNECTED) startServer();
  if (started) server.handleClient();
}

inline String ip() { return WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String("no wifi"); }
}  // namespace ota
