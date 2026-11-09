# MURMUR — wiring (junction list)

Diagram: `docs/murmur-schematic.png` (source `docs/schematic.py`).

Each line is ONE joint: everything listed meets there. Parts named by what they look like.

## Parts

| Ref | Part | Note |
|---|---|---|
| U1 | TLC555CP — 8-pin black chip. Pin 1 = beside the notch/dot, count anticlockwise (top view) | |
| R1 | 10k resistor (brown-black-orange) | |
| R2 | 1k resistor (brown-black-red) — static protection on the electrode | |
| C1 | **timing**: 10 nF ceramic (103), no polarity. Tested on apples and leafy plants | |
| C2 | 0.1 µF electrolytic — decoupling | |
| C3 | 10 µF electrolytic — decoupling | |
| J  | PJ-392 3.5 mm jack — plant lead | |
| SW | 12D00G slide switch — 3 pins, use middle + one outer | |
| BAT | 1S LiPo ~1000 mAh, ≤ 34 × 55 × 5.5 mm (ours: JST 1.25 plug) | |
| —  | 1.25 → PH2.0 lead (or cut/solder a PH2.0 pigtail) | |
| —  | HY2.0 4-pin cable into the CrowPanel's **UART1-OUT** socket | with the CrowPanel |

Electrolytics are polarised: the **stripe is minus**.

## 555 board (plant = the timing resistor)

1. **3V3** — CrowPanel 3V3 wire · U1 pin 8 · U1 pin 4 · R1 one end · C2 + · C3 +
2. **GND** — CrowPanel GND wire · U1 pin 1 · C1 − · C2 − · C3 −
3. **DISCHARGE** — U1 pin 7 · R1 other end · R2 one end
4. **TIP** — R2 other end · jack TIP lug
5. **THRESHOLD/TRIGGER** — U1 pin 2 · U1 pin 6 · C1 + · jack SLEEVE lug
6. **SIGNAL** — U1 pin 3 · CrowPanel **IO17** wire
7. U1 pin 5 — nothing (TLC555 is fine left open)

⚠️ The jack SLEEVE is NOT ground here — it is one side of the plant. Never tie it to GND or the box.
⚠️ Find TIP vs SLEEVE by plugging a TENS lead in and buzzing from each plug contact to the lugs.

## Power

8. Battery RED · SW middle pin
9. SW outer pin · PH2.0 lead RED (→ CrowPanel battery socket)
10. Battery BLACK · PH2.0 lead BLACK

⚠️ Before plugging in: check the PH2.0 lead's red goes to the CrowPanel socket's **+** (silkscreen).
Cheap leads ship either way round; reversed can kill the charger chip.
Note: the switch disconnects the cell, so **it only charges with the switch ON**.

## To verify on the board (not taken on trust)

- **UART1-OUT pin order** (power / GND / IO17 / IO18) — read the silkscreen, buzz to the ESP pins.
  Warble's notes (v1.2 schematic) put IO17/IO18 there; ours is v1.4.
- That connector's power pin must read **3.3 V**. If it reads 5 V, take 3V3 from the **I2C-OUT**
  socket instead — the 555's output must not exceed 3.3 V into IO17.

## Timing cap

C1 = 10 nF ceramic: about 2–4 kHz on an apple, steady on leaves. The original 0.1 µF electrolytic
stalled on leafy plants (its leakage ate the charge current), so don't use an electrolytic here.
