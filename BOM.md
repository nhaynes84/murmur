# MURMUR — bill of materials

Prices checked 2026-10-29 to 2026-11-04 and they move. Most electronics come in packs; the
**"per unit"** column is roughly what one MURMUR actually uses.

## Electronics

| # | Part | Qty | Notes | Source | Pack price |
|---|---|---|---|---|---|
| 1 | **Elecrow CrowPanel Advance 2.4"** (ESP32-S3-WROOM-1 N16R8, 320×240 IPS, capacitive touch, LiPo charger) | 1 | The brain, the screen and the charger. Built on hardware **v1.4** | [Elecrow](https://www.elecrow.com/crowpanel-advance-2-4-hmi-esp32-320x240-ips-ai-display-artificial-intelligent-touchscreen-1.html) | ~$17–26 |
| 2 | **TLC555CP** CMOS 555 timer, DIP-8 | 1 | ⚠️ Must be the **CMOS** TLC555 (2–15 V). An NE555 needs ≥4.5 V, and the board has no 5 V on battery | any electronics supplier | ~$1 |
| 3 | Resistor 10 kΩ (R1) | 1 | 3V3 → pin 7 | resistor kit | — |
| 4 | Resistor 1 kΩ (R2) | 1 | In series with the electrode, as static protection | resistor kit | — |
| 5 | Capacitor, timing (C1): **10 nF ceramic** (marked 103) | 1 | See note A | ceramic cap kit | — |
| 6 | Capacitor 0.1 µF (C2) + 10 µF (C3) | 1 + 1 | Supply decoupling at the 555 | cap kit | — |
| 7 | 3.5 mm panel jack **PJ-392** | 1 | Plant lead input. Not the PJ-307, which is PCB mount | [Amazon B0C68Q22KJ](https://www.amazon.com/dp/B0C68Q22KJ) | $6.49 / 10 |
| 8 | HY2.0 4-pin cable | 1 | Into the CrowPanel's **UART1-OUT** socket (3V3 · GND · IO17) | comes with the CrowPanel | — |
| 9 | Slide switch **12D00G**, 4 mm lever | 1 | Power. A body 3.7 mm deep is what fits the channel | switch assortment | — |
| 10 | 1S LiPo, ~1000 mAh, **≤ 34 × 55 × 5.5 mm** | 1 | Ours is a 1050 mAh cell salvaged from another build | — | — |
| 11 | Lead to the board's **PH2.0** battery socket | 1 | Or a cell that already has a PH2.0 plug. ⚠️ **check polarity**, see note B | — | — |
| 12 | Perfboard scrap + hookup wire | — | For the 555 board | — | — |

## The plant connection

| # | Part | Qty | Notes | Source | Pack price |
|---|---|---|---|---|---|
| 13 | TENS lead, 3.5 mm plug → 2 snaps | 1 | ⚠️ needs the **3.5 mm** plug (some TENS leads use 2.35 mm) | [Amazon B073P2SHQY](https://www.amazon.com/dp/B073P2SHQY) | $9.99 / 4 |
| 14 | 3M Red Dot 2560 ECG gel pads | 2 per session | For leaves: the snap clips onto the pad, with no clamping | [Amazon B0015TI4G2](https://www.amazon.com/dp/B0015TI4G2) | $11.40 / 50 |
| 15 | Small alligator jumpers | 2 | For stems and fruit: clip onto a **stainless** pin pushed into the flesh, not onto the plant | [Amazon B06XX25HFX](https://www.amazon.com/dp/B06XX25HFX) | $5.99 / 10 |

## Printed parts and fixings

| # | Part | Qty | Notes |
|---|---|---|---|
| 16 | `prints/murmur-body.step` | 1 | Body plus the accent colour (MURMUR letters and the square-wave band). Two-colour, **face down** |
| 17 | `prints/murmur-backplate.stl` | 1 | Flat back plate |
| 18 | `prints/murmur-plant.stl` | 1 | Money-plant inlay, glued flush into the back plate |
| 19 | `prints/murmur-badge-plate.stl` | 1 | Optional: a 0.8 mm plate that covers the badge pocket's floor around the letters. Print **face up** in the accent colour |
| 20 | M3 × 5 screws | 4 | Board to the face bosses |
| 21 | M3 × 10 countersunk screws | 4 | Back plate to the wall pillars (self-tapping into a 2.8 mm pilot) |
| 22 | PLA, two colours | ~40 g | |

## Notes

**A. The timing capacitor (C1).** Use a **10 nF ceramic** (marked 103). Tested on an apple and on
leafy houseplants: about 2–4 kHz on an apple, and steady on leaves. The first build used a 0.1 µF
electrolytic. That worked on a hand or an apple but **stalled on leafy plants after a couple of
pulses**, because the electrolytic's leakage swallowed the tiny charge current. The firmware's
listening doesn't depend on the pulse rate, so other values work too (frequency ≈ 1.44 / ((10k + 2·R_plant) · C)).

**B. Battery polarity.** Cheap PH2.0 leads ship wired either way round. Check that red goes to the
CrowPanel socket's **+** before you plug in, because reversed polarity can kill the charger chip.
The power switch disconnects the cell, so it **only charges with the switch on**.

**Not needed:** a speaker, an SD card, a separate MIDI jack. MURMUR sends **Bluetooth MIDI** (it shows
up as "MURMUR") and **USB MIDI**. The sound comes from whatever app or synth it's connected to.

**Rough cost of one unit** with parts bought in packs: ~$60. Most of that is spare pads, jacks and
leads. The parts that end up in one MURMUR come to about $30.
