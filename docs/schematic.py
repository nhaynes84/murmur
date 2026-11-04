"""MURMUR circuit diagram -> docs/murmur-schematic.png (schemdraw). Matches WIRING.md.
Explicit coordinates throughout: auto-routing drew the THR/TRG wire up the plant's own line
in the first draft, which reads as the plant being shorted out."""
import os
import schemdraw
import schemdraw.elements as elm

schemdraw.config(fontsize=11, lw=1.4)
RED, GREEN, GREY = "#c0392b", "#2e7d32", "#444444"
VCC_Y, GND_Y = 11.4, 1.4
RAIL_X0, RAIL_X1 = 0.6, 17.4

with schemdraw.Drawing(show=False) as d:
    d += elm.Label().at((0.4, 13.2)).label("MURMUR — plant → TLC555 → CrowPanel", fontsize=16, halign="left")

    # rails
    d += elm.Line().at((RAIL_X0, VCC_Y)).to((RAIL_X1, VCC_Y)).color(RED)
    d += elm.Label().at((RAIL_X0, VCC_Y + 0.45)).label("3V3  — from CrowPanel UART1-OUT", halign="left", color=RED)
    d += elm.Line().at((RAIL_X0, GND_Y)).to((RAIL_X1, GND_Y))
    d += elm.Label().at((RAIL_X0, GND_Y - 0.5)).label("GND  — from CrowPanel UART1-OUT", halign="left")

    # the chip (pins: DIS 7 @ y8.0, THR 6 @ 6.5, TRG 2 @ 5.0 on x=5; Vcc 8 / RST 4 on top; GND 1 bottom)
    ic = elm.Ic555().at((6, 4))
    d += ic
    d += elm.Label().at((9.0, 2.6)).label("U1 = TLC555 (DIP-8)", halign="left", fontsize=10, color=GREY)
    for pin in (ic.Vcc, ic.RST):
        d += elm.Line().at(pin).toy(VCC_Y)
        d += elm.Dot().at((pin[0], VCC_Y))
    d += elm.Line().at(ic.GND).toy(GND_Y)
    d += elm.Dot().at((ic.GND[0], GND_Y))
    d += elm.Line().at(ic.CTL).right(0.7)
    d += elm.Label().label("5: not connected", loc="right", fontsize=10, color=GREY)

    # R1: 3V3 -> DIS (node A)
    A = (3.6, ic.DIS[1])
    d += elm.Line().at(ic.DIS).to(A)
    d += elm.Dot().at(A)
    d += elm.Resistor().at(A).up().toy(VCC_Y).label("R1  10k", loc="bottom")
    d += elm.Dot().at((A[0], VCC_Y))

    # node A -> R2 -> TIP -> PLANT -> SLEEVE  (its own column at x = 1.6)
    PX = 1.6
    d += elm.Line().at(A).tox(PX)
    d += elm.Resistor().down().length(1.6).label("R2  1k\n(static guard)", loc="bottom")
    d += elm.Line().down(0.3)
    d += elm.Dot(open=True).label("jack TIP", loc="left")
    d += elm.ResistorVar().down().length(2.2).color(GREEN).label("PLANT\n100k – 10M", loc="bottom", color=GREEN)
    d += elm.Dot(open=True).label("jack SLEEVE", loc="left")
    SLV = d.here

    # THR (6) + TRG (2) tied on a bus at x = 4.4, down to the sleeve's level, back to the sleeve
    BX = 4.4
    d += elm.Line().at(ic.THR).tox(BX)
    d += elm.Dot()
    d += elm.Line().at(ic.TRG).tox(BX)
    d += elm.Dot()
    d += elm.Line().at((BX, ic.THR[1])).toy(SLV[1])
    B = (BX, SLV[1])
    d += elm.Dot().at(B)
    d += elm.Line().at(SLV).to(B)
    d += elm.Label().at((BX + 0.2, (ic.THR[1] + ic.TRG[1]) / 2)).label("pins 2 + 6\ntied", loc="right", fontsize=9, color=GREY)

    # C1 timing: node B -> GND
    d += elm.Capacitor(polar=True).at(B).down().toy(GND_Y).label("C1  0.1µ  timing", loc="bottom")
    d += elm.Dot()

    # OUT (3) -> IO17
    d += elm.Line().at(ic.OUT).tox(12.6)
    d += elm.Dot(open=True)
    d += elm.Label().at((12.6, ic.OUT[1] + 0.55)).label("→ IO17\n(CrowPanel UART1-OUT)", halign="center", fontsize=10)

    # decoupling, far right
    for x, lab in ((14.6, "C2\n0.1µ"), (16.4, "C3\n10µ")):
        d += elm.Dot().at((x, VCC_Y))
        d += elm.Capacitor(polar=True).at((x, VCC_Y)).down().toy(GND_Y).label(lab, loc="bottom")
        d += elm.Dot().at((x, GND_Y))
    d += elm.Label().at((15.5, 9.9)).label("decoupling — keep\nclose to the chip", fontsize=9, color=GREY)

    # power
    PY = -1.8
    d += elm.Label().at((0.4, PY + 1.2)).label("POWER", fontsize=13, halign="left")
    # ⚠️ schemdraw's cell draws its LONG (+) plate at the START: reversed so + faces the switch
    bat = elm.BatteryCell().at((1.0, PY)).right().reverse().label("ROAM LiPo 1050 mAh", loc="bottom")
    d += bat
    d += elm.Label().at((bat.end[0] - 0.1, PY + 0.55)).label("+", fontsize=13)
    d += elm.Label().at((bat.start[0] + 0.1, PY + 0.55)).label("−", fontsize=13)
    d += elm.Line().right(0.8)
    d += elm.Switch().right().label("SW  12D00G", loc="bottom")
    d += elm.Line().tox(9.0)
    d += elm.Dot(open=True)
    d += elm.Label().at((9.3, PY)).label("PH2.0 +   → CrowPanel battery socket", halign="left")
    d += elm.Line().at(bat.start).down(1.2)
    d += elm.Line().tox(9.0)
    d += elm.Dot(open=True)
    d += elm.Label().at((9.3, PY - 1.2)).label("PH2.0 −", halign="left")

    notes = ("•  Jack SLEEVE is NOT ground — it is one side of the plant.\n"
             "•  Electrolytics: stripe = minus.   U1 pin 1 is beside the notch.\n"
             "•  Check the PH2.0 lead's polarity against the CrowPanel's + mark first.\n"
             "•  The switch cuts the cell: it only charges with the switch ON.\n"
             "•  Upgrade later: C1 = 1–10 nF ceramic → kHz signal, easier hum rejection.")
    d += elm.Label().at((0.4, PY - 2.4)).label(notes, halign="left", valign="top", fontsize=10.5, color="#222")
    d.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "murmur-schematic.png"), dpi=170)
print("ok")
