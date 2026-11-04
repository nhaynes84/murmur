// MURMUR — Bluetooth LE MIDI (the standard Apple/MMA BLE-MIDI service), so her phone sees "MURMUR"
// as a MIDI device: iOS natively (GarageBand: Settings > Advanced > Bluetooth MIDI Devices).
// Written against the Arduino-ESP32 BLE library directly — no third-party MIDI lib to drift.
#pragma once
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLE2902.h>

namespace blemidi {
static const char* SERVICE = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700";
static const char* CHARACTERISTIC = "7772E5DB-3868-4112-A1A9-F2669D106BF3";

static BLECharacteristic* ch = nullptr;
static volatile bool connected = false;

class ServerCb : public BLEServerCallbacks {
  void onConnect(BLEServer*) override { connected = true; }
  void onDisconnect(BLEServer* s) override {
    connected = false;
    s->getAdvertising()->start();  // stay discoverable
  }
};

inline void begin(const char* name) {
  BLEDevice::init(name);
  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new ServerCb());
  BLEService* svc = server->createService(SERVICE);
  ch = svc->createCharacteristic(CHARACTERISTIC, BLECharacteristic::PROPERTY_READ |
                                                     BLECharacteristic::PROPERTY_WRITE_NR |
                                                     BLECharacteristic::PROPERTY_NOTIFY);
  ch->addDescriptor(new BLE2902());
  svc->start();
  BLEAdvertising* adv = server->getAdvertising();
  adv->addServiceUUID(SERVICE);
  adv->setScanResponse(true);
  adv->start();
}

// One MIDI message in a BLE-MIDI packet: header + timestamp + status + data.
inline void send(uint8_t status, uint8_t d1, uint8_t d2) {
  if (!connected || !ch) return;
  uint16_t ts = millis() & 0x1FFF;
  uint8_t pkt[5] = {(uint8_t)(0x80 | (ts >> 7)), (uint8_t)(0x80 | (ts & 0x7F)), status, d1, d2};
  ch->setValue(pkt, 5);
  ch->notify();
}
}  // namespace blemidi
