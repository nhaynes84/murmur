// MURMUR — CrowPanel Advance 2.4 (ESP32-S3) board support.
// Pins are Elecrow's own (ref/elecrow/, lesson-05): ST7789 on SPI2, capacitive touch on I2C 15/16,
// backlight on IO38. ⚠️ The touch chip differs between board revisions (FT6336 @0x38 or GT911 @0x5D):
// probe() finds out at boot and LGFX is built with the matching driver.
#pragma once
#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include <Wire.h>

namespace board {
constexpr int SIGNAL_PIN = 17;  // UART1-OUT socket: the 555 output (TLC555, 3.3 V)
constexpr int BACKLIGHT = 38;
constexpr int I2C_SDA = 15, I2C_SCL = 16;

enum class Touch { FT6336, GT911, NONE };

inline Touch probe() {
  // GT911 power-on timing exactly as Elecrow does it (IO1 = INT, IO2 = RST on GT911 revisions)
  pinMode(1, OUTPUT); pinMode(2, OUTPUT);
  digitalWrite(1, LOW); digitalWrite(2, LOW); delay(20);
  digitalWrite(2, HIGH); delay(100);
  pinMode(1, INPUT);
  Wire.begin(I2C_SDA, I2C_SCL, 400000);
  auto present = [](uint8_t a) { Wire.beginTransmission(a); return Wire.endTransmission() == 0; };
  Touch t = present(0x38) ? Touch::FT6336 : (present(0x5D) || present(0x14)) ? Touch::GT911 : Touch::NONE;
  Wire.end();  // LGFX owns the bus from here
  return t;
}

class LGFX : public lgfx::LGFX_Device {
  lgfx::Panel_ST7789 panel;
  lgfx::Bus_SPI bus;
  lgfx::Touch_FT5x06 ft;
  lgfx::Touch_GT911 gt;

 public:
  explicit LGFX(Touch kind) {
    {
      auto c = bus.config();
      c.spi_host = SPI2_HOST; c.spi_mode = 0;
      c.freq_write = 40000000; c.freq_read = 16000000;
      c.spi_3wire = false; c.use_lock = true; c.dma_channel = SPI_DMA_CH_AUTO;
      c.pin_sclk = 42; c.pin_mosi = 39; c.pin_miso = -1; c.pin_dc = 41;
      bus.config(c);
      panel.setBus(&bus);
    }
    {
      auto c = panel.config();
      c.pin_cs = 40; c.pin_rst = -1; c.pin_busy = -1;
      c.memory_width = 240; c.memory_height = 320; c.panel_width = 240; c.panel_height = 320;
      c.offset_x = 0; c.offset_y = 0; c.offset_rotation = 3;
      c.dummy_read_pixel = 8; c.dummy_read_bits = 1;
      c.readable = false; c.invert = true; c.rgb_order = false; c.dlen_16bit = false;
      c.bus_shared = true;
      panel.config(c);
    }
    if (kind != Touch::NONE) {
      lgfx::ITouch* t = (kind == Touch::FT6336) ? (lgfx::ITouch*)&ft : (lgfx::ITouch*)&gt;
      auto c = t->config();
      c.x_min = 0; c.x_max = 239; c.y_min = 0; c.y_max = 319;
      c.pin_int = (kind == Touch::FT6336) ? 47 : -1;
      c.bus_shared = false; c.offset_rotation = 6;
      c.i2c_port = 0; c.i2c_addr = (kind == Touch::FT6336) ? 0x38 : 0x5D;
      c.pin_sda = I2C_SDA; c.pin_scl = I2C_SCL; c.freq = 400000;
      t->config(c);
      panel.setTouch(t);
    }
    setPanel(&panel);
  }
};
}  // namespace board
