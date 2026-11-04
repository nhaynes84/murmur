"""
MURMUR — the housing, pass 2: built around the CrowPanel Advance 2.4 touchscreen.

    ~/Projects/synth-case/.venv/bin/python housing.py
        -> ~/Collab/CAD/murmur/murmur.step   (assembly + Elecrow's real board as ghost)
        -> ~/Collab/CAD/murmur/murmur.stl    (printed parts only)

★ PASS 2 (2026-11-01). Pass 1 (S3 dev board + 2.42" OLED + 4 buttons, housing_pass1.py) is
superseded by his calls: "why buttons" -> settings are MENUS ON A TOUCHSCREEN, and he gave one
Warble CrowPanel to it. The CrowPanel is an ESP32-S3 + 2.4" 320x240 capacitive touch + TP4059
charger + PH2.0 battery socket on one board: it replaces the dev board, the OLED, the DFR1026
and the buttons.

ORIENTATION (cad-nautical-orientation): portrait slab, FACE +Z, BOW = top edge (+Y, USB-C),
STERN = bottom edge (-Y, plant jack), SB = +X, PORT = -X. X/Y centred, Z = 0 at the back.

★★ ALL BOARD GEOMETRY IS READ OUT OF ELECROW'S OWN STEP (v1.4,
ref/models/crowpanel24-advance-hmi2_4-20260126.stp) through ONE transform, BOARD(), so the
holes, ports and the ghost board can never disagree: face-down, long axis on Y, USB edge at bow.

FACE: the touch glass sits FLUSH in a through-opening, the way Elecrow's own front frame holds it
(their frame opening 61.86 x 42.82; the glass module 60.26 x 42.72). Nothing else on the face.
⛔ NO TOUCH PLATE (his call, 2026-11-01): "it's not honest to the plant-as-synth idea — if a
person can touch to add to the mix, that's kind of dumb". The music is the PLANT's, only.
★★ PARTS (his call, 2b): the BODY is the face AND all four sides in one piece — seamless front.
The BACK is a flat PLATE with the screws: 4 x M3 countersunk into pillars merged into the walls.
The board screws to 4 bosses on the inside of the face (M3 x 5, from its component side), so
it is fixed to the glass side and the back plate only closes the box. Face unbroken.

⚠️ OPEN (README): which USB-C is native vs CH340 (both exposed); what Elecrow's case opening on
the PORT long edge is for (probably BOOT/RESET); PJ-392 size (MEASURE). Sides carry NOTHING.
"""
import copy
import math
import os

from build123d import (Align, Axis, Box, Compound, Cone, Cylinder, Plane, Pos, Rectangle, Rot,
                       SlotOverall, Text, chamfer, export_step, export_stl, extrude, fillet,
                       import_step)
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN, TopAbs_ON

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "..", "ref", "models", "crowpanel24-advance-hmi2_4-20260126.stp")
out = os.path.expanduser(os.environ.get("MURMUR_OUT", "~/Collab/CAD/murmur"))   # set MURMUR_OUT to write elsewhere
# ★ POLICY (his): the project ROOT holds only the ASSEMBLY files; every per-part print file goes
#   in prints/.
prints = os.path.join(out, "prints")
os.makedirs(prints, exist_ok=True)
C = (Align.CENTER, Align.CENTER, Align.MIN)
MINS = (Align.MIN, Align.MIN, Align.MIN)

# ------------------------------------------------------------------ the board (Elecrow STEP, mm)
# model frame: PCB x 0..72.8 (long), y -0.55..47.5, PCB z -1.6..0, glass front at z -6.9,
# tallest parts (HY2.0 sockets) top at z 8.0
PCB_X, PCB_Y0, PCB_Y1 = 72.8, -0.55, 47.5
GLASS = (6.27, 66.53, 2.39, 45.11)           # LCD+CTP module footprint, model x0, x1, y0, y1
GLASS_FRONT, PCB_BOT, PCB_TOP, PARTS_TOP = -6.9, -1.6, 0.0, 8.0
HOLES = [(3.0, 3.0), (69.8, 3.0), (3.0, 44.5), (69.8, 44.5)]   # M3, Elecrow's corner screws
USB_V = [13.45, 34.05]                        # port centres along model y (both on the +x edge)
USB_ZC = 1.1                                  # model z of the port centres
VC = (PCB_Y0 + PCB_Y1) / 2                    # board centreline -> box x = 0

# ------------------------------------------------------------------ the rest (MEASURE)
LIPO = (55.0, 34.0, 5.5)                      # ★ 1050 mAh harvested from ROAM, lying ACROSS the bay
                                              #   (his call 2026-11-01: "grow the box" rather than buy a cell)
JACK_HOLE, JACK_BODY_D, JACK_BODY_L = 6.2, 8.0, 11.0     # PJ-392 ⚠️ MEASURE
# ★ power switch: 12D00G-4mm from his assortment (ref/slide-switch-assortment.png). Body 8.7 x 3.7
#   x 3.7, lever 1.5 x 1.5 x 4.0. Chosen because it is the only one shallow enough for the 5.5 mm
#   channel between the board edge and the SB wall (SS12F15 / SS12D10 stand 6-9 mm deep).
#   Mounted lever-out against the wall's inside face: lever stands 4.0 - WALL = 2 mm proud.
SW_LEVER, SW_TRAVEL = 1.5, 2.0               # ⚠️ TRAVEL not in the listing — check on the part
SW_BODY = (8.7, 3.7, 3.7)                     # (along the wall X, into the box Y, Z)
SW_SLOT = (4.0, SW_LEVER + 0.5)               # (X, Z). ★ 4 mm, his call — a little long is no big deal
SW_CRADLE_T = 1.2
PERF = (30.0, 20.0, 9.0)                      # 555 perfboard incl. DIP-8 (ghost only)

# ------------------------------------------------------------------ box
WALL, FLOOR_T, FACE_T = 2.0, 2.0, 2.0
CORNER_R, EDGE_CHAM, BED_CHAM, FIT = 6.0, 1.2, 1.0, 0.4
GLASS_FIT, GLASS_CHAM = 0.2, 0.4
PLUG_CLEAR = 4.0                              # above the HY2.0 sockets: mated plug + wire bend
BOARD_FIT = 0.5

# ★ DEPTH IS AN IDENTITY: floor + plug room + (socket tops -> glass front) = DEPTH, glass flush.
DEPTH = FLOOR_T + PLUG_CLEAR + (PARTS_TOP - GLASS_FRONT)
SHELL_H = DEPTH - FACE_T
FENCE = FIT + 1.2                             # cradle wall + its clearance, per side
# ★ W is now set by the CELL, not the board: 55 mm across + fences > the 48 mm board
W = float(math.ceil(max((PCB_Y1 - PCB_Y0) + 2 * BOARD_FIT, LIPO[0] + 2 * FENCE + 0.6) + 2 * WALL))

# ★ LAYOUT ALONG Y, derived: bow wall | board (USB-C at the wall) | plate | stern edge
# ★ H is set by the BAY: stern wall | jack body | cell | board.
BAY_NEED = JACK_BODY_L + 0.8 + LIPO[1] + 2 * FENCE + 0.5
H = float(math.ceil(WALL + 0.2 + PCB_X + BOARD_FIT + BAY_NEED + WALL))
STERN, BOW = -H / 2, H / 2
BOARD_Y0 = BOW - WALL - 0.2 - PCB_X           # model x = 0 lands here


def BOARD():
    """model (x, y, z) -> box. Face-down, long axis on Y, USB edge at the bow."""
    return Pos(-VC, BOARD_Y0, DEPTH + GLASS_FRONT) * Rot(0, 0, 90) * Rot(180, 0, 0)


def bxy(mx, my):
    """model x/y -> box x/y: the same mapping as BOARD(), for numbers."""
    return (my - VC, mx + BOARD_Y0)


def bz(mz):
    return DEPTH + GLASS_FRONT - mz


GLASS_X0, GLASS_Y0 = bxy(GLASS[0], GLASS[2])
GLASS_X1, GLASS_Y1 = bxy(GLASS[1], GLASS[3])
GLASS_W, GLASS_H = GLASS_X1 - GLASS_X0, GLASS_Y1 - GLASS_Y0
GLASS_C = ((GLASS_X0 + GLASS_X1) / 2, (GLASS_Y0 + GLASS_Y1) / 2)

HOLE_PTS = [bxy(*h) for h in HOLES]
BOSS_D, BOSS_PILOT = 5.4, 2.8                 # ⚠️ boss holes sit only ~0.3 off the glass edge. 2.8: printed
                                              #   holes shrink ~0.3, a 2.5 pilot bound M3 (tested 2026-11-03)
POST_D, SCREW_CLR, CS_D, CS_H = 6.0, 3.4, 6.4, 1.6
# ★ BACK-PLATE SCREWS go into PILLARS MERGED INTO THE WALLS (full height, so they are part of the
# wall, not posts floating in the cavity): two in the stern corners, two on the side walls
# beside the board, in the 5 mm channel between the board edge and the wall.
PIL_D, PIL_PILOT = 5.0, 2.8                   # M3 self-tap; 2.8 because printed holes shrink
PIL_X = W / 2 - WALL - 1.5                    # centre 1.5 inside the wall face -> merges with it
PIL_PTS = [(sx * (W / 2 - WALL - 2.5), STERN + WALL + 2.5) for sx in (-1, 1)] + \
          [(sx * PIL_X, BOW - WALL - 12.0) for sx in (-1, 1)]
LEG_PTS = PIL_PTS[:2]                         # (name kept for the stern clearance checks)
LEG_D = PIL_D

USB_PTS = [bxy(PCB_X, v)[0] for v in USB_V]
USB_Z = bz(USB_ZC)
USB_SLOT = (9.3, 3.6)

# the lower bay: stern wall up to the board's model-x=0 edge
BAY_Y0, BAY_Y1 = STERN + WALL, BOARD_Y0 - BOARD_FIT
JACK_X = -10.0
JACK_Z = FLOOR_T + JACK_BODY_D / 2 + 1.0
LIPO_Y0 = STERN + WALL + JACK_BODY_L + 0.8 + FENCE     # just bow-side of the jack body
# ★ STERN EDGE, mirroring the jack (his call: "so the sides don't have shit on them, just top
#   and bottom"). Jack at -x, switch at +x: the bottom edge reads as a pair; the sides are clean.
SW_X = -JACK_X                                 # provisional — re-derived into a high pulse once the wave exists
SW_Z = FLOOR_T + 5.0

PROJECT = "murmur"

# ------------------------------------------------------------------ the name
# ★★ RECESSED FIELD, RAISED LETTERS (the HELM badge) — and here the LETTERS ARE THEIR OWN PART,
# so his multicolour printer gives them a second filament. Letter tops land dead level with the
# face; the field around them drops BADGE_D. Face-down print: letter tops and face are both
# layer 1, and the pocket floor only bridges the few mm between strokes (the letters, printed
# at the same time in the other colour, hold it up).
BADGE = "MURMUR"
FONT = "Futura"                               # geometric: reads electronic, not corporate
BADGE_SIZE = 6.0                              # font size (mm); ~4.8 mm caps
# ★ TRACKING IS DERIVED: the pocket is exactly as wide as the glass opening above it, so the
#   name and the screen share both edges. Tracking takes up whatever the glyphs leave.
BADGE_D, BADGE_PAD, BADGE_R = 0.8, 3.5, 1.5   # pocket depth, air round the word, pocket corners
# centred in the blank lower face: between the glass opening and the stern edge
BADGE_YC = ((GLASS_Y0 - GLASS_FIT) + STERN) / 2


def kids(*shapes):
    """⚠️⚠️ COPIES for Compound(children=...). A build123d shape has ONE parent: putting it in a
    second Compound silently REMOVES it from the first. That is how the MURMUR letters vanished
    from the body's accent part (the assembly export took them). Every Compound gets copies."""
    return [copy.copy(x) for x in shapes]


def rplate(w, h, t, r):
    return fillet(Box(w, h, t, align=C).edges().filter_by(Axis.Z), r)


def cyl(d, h, align=C):
    return Cylinder(d / 2, h, align=align)


def cut(part, tool, name):
    """⚠️ a cut that removes nothing is the silent failure (cad-tooling-2)."""
    v0 = part.volume
    part = part - tool
    assert part.volume < v0 - 1e-3, f"cut '{name}' removed nothing"
    return part


def add(part, tool, name):
    v0 = part.volume
    part = part + tool
    assert part.volume > v0 + 1e-3, f"add '{name}' added nothing"
    assert len(part.solids()) == 1, f"add '{name}' left {len(part.solids())} solids — it floats"
    return part


def wordmark(txt, size, track):
    """Flat sketch laid out glyph by glyph so it can be TRACKED (from the HELM).
    ⚠️ advances come from PREFIX widths so real kerning survives; a space has no ink."""
    assert " " not in txt
    def ink(t):
        return Text(t, font_size=size, font=FONT, align=(Align.MIN, Align.CENTER)).bounding_box().max.X
    widths, prev = [], 0.0
    for i in range(1, len(txt) + 1):
        w = ink(txt[:i])
        widths.append(w - prev)
        prev = w
    cur, sk = -(prev + track * (len(txt) - 1)) / 2, None
    for ch, adv in zip(txt, widths):
        g = Pos(cur, 0, 0) * Text(ch, font_size=size, font=FONT, align=(Align.MIN, Align.CENTER))
        sk = g if sk is None else sk + g
        cur += adv + track
    return sk


_ink0 = wordmark(BADGE, BADGE_SIZE, 0.0).bounding_box().size.X
BADGE_TRACK = ((GLASS_W + 2 * GLASS_FIT - 2 * BADGE_PAD) - _ink0) / (len(BADGE) - 1)
assert BADGE_TRACK >= 1.0, f"word too wide to track open ({BADGE_TRACK:.2f}) — drop BADGE_SIZE"
MARK = wordmark(BADGE, BADGE_SIZE, BADGE_TRACK)
_mb = MARK.bounding_box()
MARK = Pos(-(_mb.min.X + _mb.max.X) / 2, -(_mb.min.Y + _mb.max.Y) / 2) * MARK   # true ink centre
BADGE_W = _mb.size.X + 2 * BADGE_PAD          # ★ the pocket is sized BY the word, not typed
BADGE_H = _mb.size.Y + 2 * BADGE_PAD


def letters():
    """The name as its OWN SOLID: pocket floor up to the face plane. Second filament."""
    return Pos(0, BADGE_YC, DEPTH - BADGE_D) * extrude(MARK, BADGE_D)


# ------------------------------------------------------------------ the side band: the signal
# ★★ A VARIABLE SQUARE WAVE ALL THE WAY ROUND (his idea): it is what MURMUR actually hears —
#   the 555 puts out square pulses and the plant changes them. One CLOSED signal round the
#   whole perimeter, corners included; the ports simply cut through it ("fine if the holes cut
#   it off"). BOTH timing and amplitude vary (his call): every pulse has its own length AND its
#   own height, from the same slow drift + jitter. Square, not sine: honest, and prints clean.
#   Flush inlay in the walls, sharing the body's second-colour part with the letters.
# ★ HOW IT WRAPS: the wave lives in (s, z) where s = arc length round the OUTER perimeter. Each
#   stroke = (thin outer skin) ∩ (z slab) ∩ (perimeter sector s_a..s_b). Sectors are boxes on the
#   flats and pie wedges on the R6 corners, so square edges stay square as they bend round.
WAVE_STROKE, WAVE_D = 2.0, 0.8                  # line width, inlay depth
WAVE_PROUD = 0.4                                # ★ stands proud of the sides: visible + tactile in ANY
                                                #   colour (flush, it vanished in a grey preview). Face-
                                                #   down print: the sides never touch the bed, so fine.
WAVE_MIN_SEG, WAVE_MAX_SEG = 5.0, 13.0          # pulse/gap length along the wall (mm)
WAVE_AMP_MIN, WAVE_AMP_MAX = 4.5, 10.0          # pulse height (mm, stroke centre to centre)
WAVE_LO = FLOOR_T + 4.5                         # baseline (stroke centre)
_FL_X, _FL_Y = W / 2 - CORNER_R, H / 2 - CORNER_R   # half-lengths of the flats
PERIM = 4 * _FL_X + 4 * _FL_Y + 2 * math.pi * CORNER_R


def _perim_pieces():
    """Perimeter as ordered pieces from s = 0 at mid-stern, running SB-ward (CCW from the face):
    ('line', s0, s1, p0, p1) or ('arc', s0, s1, centre, a0, a1)."""
    R, pcs, s0 = CORNER_R, [], 0.0
    def line(p0, p1):
        nonlocal s0
        L = math.dist(p0, p1); pcs.append(("line", s0, s0 + L, p0, p1)); s0 += L
    def arc(c, a0, a1):
        nonlocal s0
        L = R * math.radians(a1 - a0); pcs.append(("arc", s0, s0 + L, c, a0, a1)); s0 += L
    line((0, -H / 2), (_FL_X, -H / 2));        arc((_FL_X, -_FL_Y), -90, 0)
    line((W / 2, -_FL_Y), (W / 2, _FL_Y));     arc((_FL_X, _FL_Y), 0, 90)
    line((_FL_X, H / 2), (-_FL_X, H / 2));     arc((-_FL_X, _FL_Y), 90, 180)
    line((-W / 2, _FL_Y), (-W / 2, -_FL_Y));   arc((-_FL_X, -_FL_Y), 180, 270)
    line((-_FL_X, -H / 2), (0, -H / 2))
    assert abs(s0 - PERIM) < 1e-6
    return pcs


PIECES = _perim_pieces()


def _sector(sa, sb):
    """A prism covering the perimeter between arc lengths sa..sb (sa < sb, may wrap)."""
    from build123d import Polygon as BPoly
    if sb > PERIM:
        return _sector(sa, PERIM) + _sector(0.0, sb - PERIM)
    parts = []
    for pc in PIECES:
        lo, hi = max(sa, pc[1]), min(sb, pc[2])
        if hi - lo < 1e-6:
            continue
        if pc[0] == "line":
            _, a, b, p0, p1 = pc
            t0, t1 = (lo - a) / (b - a), (hi - a) / (b - a)
            q0 = (p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0)
            q1 = (p0[0] + (p1[0] - p0[0]) * t1, p0[1] + (p1[1] - p0[1]) * t1)
            dx, dy = q1[0] - q0[0], q1[1] - q0[1]
            n = math.hypot(dx, dy); nx, ny = dy / n, -dx / n          # outward normal (CCW path)
            pts = [(q0[0] - 3 * nx, q0[1] - 3 * ny), (q1[0] - 3 * nx, q1[1] - 3 * ny),
                   (q1[0] + 3 * nx, q1[1] + 3 * ny), (q0[0] + 3 * nx, q0[1] + 3 * ny)]
        else:
            _, a, b, c, a0, a1 = pc
            g0 = a0 + (a1 - a0) * (lo - a) / (b - a)
            g1 = a0 + (a1 - a0) * (hi - a) / (b - a)
            k = max(2, int(abs(g1 - g0) / 5) + 1)
            rim = [(c[0] + (CORNER_R + 3) * math.cos(math.radians(g0 + (g1 - g0) * t / k)),
                    c[1] + (CORNER_R + 3) * math.sin(math.radians(g0 + (g1 - g0) * t / k)))
                   for t in range(k + 1)]
            pts = [c] + rim
        # ⚠️ winding decides extrude direction (cad-tooling-5): extrude symmetric, then place
        parts.append(Pos(0, 0, DEPTH / 2) * extrude(BPoly(*pts, align=None), DEPTH, both=True))
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


def wave_timing(seed=7):
    """Deterministic 'plant': slow drift (its mood) x jitter (its noise) for BOTH the length and
    the height of every pulse. Lengths sum EXACTLY to the perimeter; even count so it closes."""
    import random
    rnd = random.Random(seed)
    lens, amps, t = [], [], 0.0
    while PERIM - sum(lens) > WAVE_MAX_SEG + WAVE_MIN_SEG:
        drift = 0.5 + 0.5 * math.sin(2 * math.pi * t / 90.0 + 0.8)
        L = WAVE_MIN_SEG + (WAVE_MAX_SEG - WAVE_MIN_SEG) * (0.25 + 0.6 * drift) * rnd.uniform(0.7, 1.3)
        lens.append(min(WAVE_MAX_SEG, max(WAVE_MIN_SEG, L)))
        mood = 0.5 + 0.5 * math.sin(2 * math.pi * t / 130.0 + 2.1)
        A = WAVE_AMP_MIN + (WAVE_AMP_MAX - WAVE_AMP_MIN) * (0.2 + 0.7 * mood) * rnd.uniform(0.75, 1.25)
        amps.append(min(WAVE_AMP_MAX, max(WAVE_AMP_MIN, A)))
        t += lens[-1]
    rest = PERIM - sum(lens)
    extra = [rest / 2, rest / 2] if rest > WAVE_MAX_SEG else [rest]
    lens += extra
    amps += [amps[-1]] * len(extra)
    if len(lens) % 2:                                 # high/low must alternate round a closed loop
        a, b = lens.pop(), lens.pop(); amps.pop()
        lens.append(a + b)
        assert lens[-1] <= WAVE_MAX_SEG + WAVE_MIN_SEG
    return lens, amps


def wave_strokes():
    """(s_a, s_b, z_a, z_b) rectangles in (s, z) — the whole wave, before wrapping."""
    lens, amps = wave_timing()
    h = WAVE_STROKE / 2
    rects, s_acc = [], 0.0
    levels = [WAVE_LO if k % 2 == 0 else WAVE_LO + amps[k] for k in range(len(lens))]
    for k, L in enumerate(lens):
        z = levels[k]
        rects.append((s_acc - h, s_acc + L + h, z - h, z + h))                      # the level
        zn = levels[(k + 1) % len(lens)]
        sr = s_acc + L
        rects.append((sr - h, sr + h, min(z, zn) - h, max(z, zn) + h))               # the edge
        s_acc += L
    return rects, lens, amps


def wave_inlay():
    """The band: one solid (or a few, where nothing joins them) wrapped round the perimeter."""
    skin = rplate(W + 2 * WAVE_PROUD, H + 2 * WAVE_PROUD, DEPTH, CORNER_R + WAVE_PROUD) - Pos(0, 0, -1) * rplate(
        W - 2 * WAVE_D, H - 2 * WAVE_D, DEPTH + 2, CORNER_R - WAVE_D)
    rects, lens, amps = wave_strokes()
    band = None
    for sa, sb, za, zb in rects:
        sa_w = sa % PERIM
        piece = skin & (Pos(0, 0, za) * Box(W + 20, H + 20, zb - za, align=C)) & _sector(sa_w, sa_w + (sb - sa))
        band = piece if band is None else band + piece
    return band, lens, amps


_band, WAVE_LENS, WAVE_AMPS = wave_inlay()
WAVES = [_band]


def high_windows():
    """Open windows UNDER the high pulses on the stern's SB flat: (x0, x1, z_top) in x, where
    x = s for s in 0.._FL_X. Under a high pulse the line is up top, so the space below is clear."""
    out, s_acc, h = [], 0.0, WAVE_STROKE / 2
    for k, L in enumerate(WAVE_LENS):
        a, b = s_acc + h, s_acc + L - h
        if k % 2 and a < _FL_X:
            out.append((a, min(b, _FL_X), WAVE_LO + WAVE_AMPS[k] - h))
        s_acc += L
    return out


# ★★ THE SWITCH SITS INSIDE A HIGH PULSE, like the jack does (his catch: on a low stretch its slot
#   cut the baseline). It goes to the centre of the first high-pulse window on the stern's SB half
#   that fits the slot with PORT_MARGIN each side, within the cradle's limits (clear of the jack
#   and the SB stern pillar). Derived, so a reseeded wave moves it with the pulse.
PORT_MARGIN = 1.0
_sw_lo = JACK_X + JACK_BODY_D / 2 + 3.0 + (SW_BODY[0] / 2 + FIT + SW_CRADLE_T)
_sw_hi = (PIL_PTS[1][0] - PIL_D / 2) - 0.5 - (SW_BODY[0] / 2 + FIT + SW_CRADLE_T)
_fits = []
for x0, x1, zt in high_windows():
    lo, hi = max(x0 + PORT_MARGIN + SW_SLOT[0] / 2, _sw_lo), min(x1 - PORT_MARGIN - SW_SLOT[0] / 2, _sw_hi)
    if lo <= hi and SW_Z + SW_SLOT[1] / 2 + PORT_MARGIN <= zt:
        _fits.append(min(max((x0 + x1) / 2, lo), hi))
assert _fits, "no high pulse on the stern can hold the switch — reseed the wave"
SW_X = _fits[0]


def openings():
    """Every through-hole in the walls — used on the body AND on the wave (the holes cut it off)."""
    slot = Rot(90, 0, 0) * extrude(SlotOverall(*USB_SLOT), WALL + 2, both=True)
    t = [Pos(ux, BOW, USB_Z) * slot for ux in USB_PTS]
    t.append(Pos(JACK_X, STERN, JACK_Z) * Rot(90, 0, 0) * cyl(
        JACK_HOLE, WALL * 4, (Align.CENTER, Align.CENTER, Align.CENTER)))
    t.append(Pos(SW_X, STERN, SW_Z) * Box(SW_SLOT[0], WALL * 4, SW_SLOT[1], align=(Align.CENTER,) * 3))
    return t


# ★ both stern ports must sit INSIDE high-pulse windows, clear of every line (x and z)
def _port_clear(xc, half_w, z_top_port):
    best = -99.0
    for x0, x1, zt in high_windows() + [(-b, -a, z) for a, b, z in _mirror_windows()]:
        if x0 <= xc <= x1:
            best = max(best, min(xc - half_w - x0, x1 - (xc + half_w), zt - z_top_port))
    return best


def _mirror_windows():
    """High-pulse windows on the stern's PORT half (s from PERIM-_FL_X to PERIM), as (a, b, z_top)
    in -x so _port_clear can mirror them to x."""
    out, s_acc, h = [], 0.0, WAVE_STROKE / 2
    for k, L in enumerate(WAVE_LENS):
        a, b = s_acc + h, s_acc + L - h
        if k % 2 and b > PERIM - _FL_X:
            out.append((PERIM - min(b, PERIM), PERIM - max(a, PERIM - _FL_X), WAVE_LO + WAVE_AMPS[k] - h))
        s_acc += L
    return out


for _t in openings():                             # ★ the holes cut the band off
    _band = _band - _t
WAVES = [_band]


def body():
    """★ FACE + ALL FOUR SIDES IN ONE PIECE (his call: "the front should be seamless with the
    sides and the back is a plate with the screws"). Open at the back. Prints FACE-DOWN.
    Inside: 4 bosses the board screws to, 4 wall pillars the back plate screws to."""
    b = Pos(0, 0, FLOOR_T) * rplate(W, H, DEPTH - FLOOR_T, CORNER_R)
    b = chamfer(b.edges().filter_by(Plane.XY).group_by(Axis.Z)[-1], EDGE_CHAM)
    b = cut(b, Pos(0, 0, FLOOR_T - 1) * rplate(W - 2 * WALL, H - 2 * WALL,
                                              (DEPTH - FACE_T) - FLOOR_T + 1, CORNER_R - WALL), "cavity")
    gw, gh = GLASS_W + 2 * GLASS_FIT, GLASS_H + 2 * GLASS_FIT
    b = cut(b, Pos(*GLASS_C, DEPTH - FACE_T - 1) * Box(gw, gh, FACE_T + 2, align=C), "glass opening")
    b = cut(b, Pos(*GLASS_C, DEPTH - GLASS_CHAM) * extrude(Rectangle(gw, gh), GLASS_CHAM + 0.5,
                                                           taper=-45), "glass chamfer")
    # the name's pocket, then the letters' footprint cleared out of the body (they are a
    # separate part; the body must not occupy the same space or the slicer double-prints it)
    b = cut(b, Pos(0, BADGE_YC, DEPTH - BADGE_D) * rplate(BADGE_W, BADGE_H, BADGE_D + 1, BADGE_R), "badge pocket")
    for i, w in enumerate(WAVES):              # the signal band, cleared out for its own colour
        b = cut(b, w, f"wave {i}")
    # board bosses: face underside down to the PCB's glass side. M3 x 5 from the component side.
    boss_h = (DEPTH - FACE_T) - bz(PCB_BOT)
    for i, (px, py) in enumerate(HOLE_PTS):
        b = add(b, Pos(px, py, bz(PCB_BOT)) * cyl(BOSS_D, boss_h), f"boss {i}")
        b = cut(b, Pos(px, py, bz(PCB_BOT) - 0.5) * cyl(BOSS_PILOT, boss_h), f"boss pilot {i}")
    # wall pillars for the back plate: full height, merged into the wall
    pil_h = (DEPTH - FACE_T) - FLOOR_T
    for i, (px, py) in enumerate(PIL_PTS):
        b = add(b, Pos(px, py, FLOOR_T) * cyl(PIL_D, pil_h), f"pillar {i}")
        b = cut(b, Pos(px, py, FLOOR_T - 0.5) * cyl(PIL_PILOT, 10.5), f"pillar pilot {i}")
    # edges: USB-C x2 (bow), plant jack + power switch (stern). ⛔ Nothing on the sides.
    for i, tool in enumerate(openings()):
        b = cut(b, tool, f"opening {i}")
    # switch cradle: a frame on the wall's inside face that the body presses into, lever through
    # the slot. Friction + a dot of glue. Open toward the box so the pins come straight out.
    iw = STERN + WALL                          # inside face of the stern wall
    so = (SW_BODY[0] + 2 * FIT + 2 * SW_CRADLE_T, SW_BODY[1], SW_BODY[2] + 2 * FIT + 2 * SW_CRADLE_T)
    si = (SW_BODY[0] + 2 * FIT, SW_BODY[1] + 1, SW_BODY[2] + 2 * FIT)
    cradle = Pos(SW_X, iw, SW_Z) * (Box(*so, align=(Align.CENTER, Align.MIN, Align.CENTER))
                                    - Pos(0, -0.5, 0) * Box(*si, align=(Align.CENTER, Align.MIN, Align.CENTER)))
    b = add(b, cradle, "switch cradle")
    return b, boss_h, pil_h


# ------------------------------------------------------------------ the back: a money plant
# ★ A CHINESE MONEY PLANT (Pilea) — his pick: round coin leaves on stalks, in a pot, is the
#   silhouette people recognise. ⛔ No pixels any more ("kill the pixelation"): true circles, a
#   3 mm stem and stalks, a tapered pot with a rim — same layout and size as the pixel version.
# ★★ THE PLANT IS ITS OWN PLATE (his call: "a separate plate I print and glue in — cleaner").
#   The PLANT PLATE is a small rounded panel with the plant inlaid flush in its face (two-colour,
#   printed flat on its own); it glues into a matching POCKET in the back plate, flush with the
#   back. The back plate itself is now one colour.
# ★ PRINTABILITY IS ASSERTED, not hoped: nothing in the plant, and no gap between its parts,
#   is narrower than MIN_FEATURE (an inward then outward offset must give back the same shape).
# Symmetric about X, so it reads the same seen from behind.
INLAY_D, MIN_FEATURE = 0.6, 2.5              # default extrude depth; min stroke/gap
PLANT_T, PLANT_FIT = 1.0, 0.15                # the plant piece: thickness = pocket depth; glue gap per side
LEAF_D, STALK_W = 15.0, 3.0
LEAVES = [(0.0, 30.0), (-15.0, 18.0), (15.0, 18.0), (-15.0, -3.0), (15.0, -3.0)]
STEM_TOP, STEM_BOT = 30.0, -20.5              # into the top leaf, and 1 mm INTO the rim (touching is not joined)
PETIOLES = [((0.0, 11.0), LEAVES[1]), ((0.0, 11.0), LEAVES[2]),   # Pilea is PELTATE: the stalk
            ((0.0, -10.0), LEAVES[3]), ((0.0, -10.0), LEAVES[4])] # runs to the coin's centre
RIM = (34.0, 3.5, -21.25)                     # width, height, centre y
POT_TOP_W, POT_BOT_W, POT_TOP_Y, POT_BOT_Y = 28.0, 18.0, -23.0, -37.5
POT_R = 1.5
ART_YC = 0.0                                  # centred on the plate


def _plant_shapely():
    """Same outline in shapely — used only to PROVE the minimum feature size."""
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union
    parts = [Point(c).buffer(LEAF_D / 2, 64) for c in LEAVES]
    parts.append(LineString([(0, STEM_BOT), (0, STEM_TOP)]).buffer(STALK_W / 2, cap_style=2))
    parts += [LineString([a, b]).buffer(STALK_W / 2, cap_style=2) for a, b in PETIOLES]
    w, h, yc = RIM
    parts.append(Polygon([(-w / 2, yc - h / 2), (w / 2, yc - h / 2), (w / 2, yc + h / 2), (-w / 2, yc + h / 2)]))
    parts.append(Polygon([(-POT_TOP_W / 2, POT_TOP_Y + 0.6), (POT_TOP_W / 2, POT_TOP_Y + 0.6),
                          (POT_BOT_W / 2, POT_BOT_Y), (-POT_BOT_W / 2, POT_BOT_Y)]))
    return unary_union(parts)


def money_plant(depth=INLAY_D, grow=0.0):
    """The plant, extruded `depth`; `grow` offsets the outline outward (pocket = plant + fit)."""
    from build123d import Circle, Polygon as BPoly, Rectangle as BRect, SlotCenterPoint, fillet as f2d
    sk = None
    def acc(x):
        nonlocal sk
        sk = x if sk is None else sk + x
    for cx, cy in LEAVES:
        acc(Pos(cx, cy) * Circle(LEAF_D / 2))
    acc(Pos(0, (STEM_TOP + STEM_BOT) / 2) * BRect(STALK_W, STEM_TOP - STEM_BOT))
    for (ax, ay), (bx, by) in PETIOLES:
        length = math.hypot(bx - ax, by - ay)
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        acc(Pos((ax + bx) / 2, (ay + by) / 2) * Rot(0, 0, ang) * BRect(length, STALK_W))
    w, h, yc = RIM
    acc(Pos(0, yc) * BRect(w, h))
    # ⚠️ COUNTER-CLOCKWISE: a clockwise polygon's face points -Z and extrudes DOWN, out of the
    # plate (cad-tooling-5 — it did exactly that here first time). Z range asserted below.
    acc(BPoly((-POT_BOT_W / 2, POT_BOT_Y), (POT_BOT_W / 2, POT_BOT_Y),
              (POT_TOP_W / 2, POT_TOP_Y + 0.6), (-POT_TOP_W / 2, POT_TOP_Y + 0.6), align=None))
    if grow:
        from build123d import Kind, offset
        sk = offset(sk, grow, kind=Kind.ARC)
    solid = Pos(0, ART_YC, 0) * extrude(sk, depth)
    zb = solid.bounding_box()
    assert abs(zb.min.Z) < 1e-6 and abs(zb.max.Z - depth) < 1e-6, f"plant extruded wrong way {zb.min.Z:.2f}"
    assert len(solid.solids()) == 1, f"money plant is {len(solid.solids())} pieces — must be one"
    # ★ minimum feature, both ways: thin STROKES vanish under an inward offset; thin GAPS close
    #   under an outward one. Either changes the area -> the shape is not printable as drawn.
    g = _plant_shapely()
    r = MIN_FEATURE / 2
    opened, closed = g.buffer(-r).buffer(r), g.buffer(r).buffer(-r)
    assert opened.geom_type == "Polygon", "a stroke thinner than MIN_FEATURE splits the plant"
    thin = g.difference(opened).area
    narrow = closed.difference(g).area
    assert thin < 0.02 * g.area, f"{thin:.1f} mm2 of stroke is thinner than {MIN_FEATURE} mm"
    assert narrow < 0.02 * g.area, f"{narrow:.1f} mm2 of gap is narrower than {MIN_FEATURE} mm"
    return solid, thin, narrow


_g = None


def backplate():
    """Flat back plate: 4 countersunk screws into the wall pillars, the LiPo cradle inside.
    Same footprint as the body, so it CAPS the walls — one hairline seam at the back edge."""
    p = rplate(W, H, FLOOR_T, CORNER_R)
    p = chamfer(p.edges().filter_by(Plane.XY).group_by(Axis.Z)[0], BED_CHAM)
    for i, (px, py) in enumerate(PIL_PTS):
        p = cut(p, Pos(px, py, -1) * cyl(SCREW_CLR, FLOOR_T + 2), f"screw {i}")
        p = cut(p, Pos(px, py, 0) * Cone(CS_D / 2, SCREW_CLR / 2, CS_H, align=C), f"csk {i}")
    # ⛔ NO battery cradle (his call): the back plate is FLAT so it prints flat. Foam tape holds the cell.
    # ★ PLANT-SHAPED pocket, open on the outer (back) face: the plant itself drops in and is
    #   glued flush (his call: "just put the plant into the back, embed and glue"). No panel.
    p = cut(p, Pos(0, 0, -1) * money_plant(depth=PLANT_T + 1, grow=PLANT_FIT)[0], "plant pocket")
    return p


# ------------------------------------------------------------------ checks
checks, _fail = [], []


def clear(name, got, want):
    ok = got >= want - 1e-9
    checks.append(f"  {'OK  ' if ok else 'FAIL'} {name:40s} {got:6.2f}  (>= {want})")
    if not ok:
        _fail.append(name)


hx = sorted({round(p[0], 3) for p in HOLE_PTS})
clear("board -> side walls", (W / 2 - WALL) - (PCB_Y1 - PCB_Y0) / 2, BOARD_FIT - 0.01)
hy = sorted({round(p[1], 3) for p in HOLE_PTS})
# ★ the holes clear the glass along its LONG axis (box Y), and overlap it across (box X)
clear("boss -> glass end (Y)", min(GLASS_Y0 - (hy[0] + BOSS_D / 2),
                                   (hy[-1] - BOSS_D / 2) - GLASS_Y1), 0.3)
clear("glass opening -> side edge", W / 2 - (GLASS_W / 2 + GLASS_FIT), 3.0)
clear("glass opening -> bow edge", BOW - (GLASS_Y1 + GLASS_FIT), 3.0)
clear("bay length (stern wall -> board)", BAY_Y1 - BAY_Y0, 30.0)
clear("jack body -> LiPo fence", (LIPO_Y0 - FIT - 1.2) - (STERN + WALL + JACK_BODY_L), 0.3)
clear("LiPo fence -> board edge", BAY_Y1 - (LIPO_Y0 + LIPO[1] + FIT + 1.2), 0.0)
clear("LiPo fence -> side walls", (W / 2 - WALL) - (LIPO[0] / 2 + FIT + 1.2), 0.3)
clear("jack body -> port stern pillar (X)", (JACK_X - JACK_BODY_D / 2) - (PIL_PTS[0][0] + PIL_D / 2), 0.5)
clear("side pillars -> board edge (X)", (PIL_X - PIL_D / 2) - ((PCB_Y1 - PCB_Y0) / 2 + BOARD_FIT), 0.5)
clear("side pillars -> USB-C slots (Y)", (BOW - WALL) - (PIL_PTS[2][1] + PIL_D / 2), 0.0)
clear("pillar pilot depth", 10.0, 8.0)
SW_HALF = SW_BODY[0] / 2 + FIT + SW_CRADLE_T  # cradle half-width along X
clear("switch slot inside its high pulse", _port_clear(SW_X, SW_SLOT[0] / 2, SW_Z + SW_SLOT[1] / 2), PORT_MARGIN)
clear("jack hole inside its high pulse", _port_clear(JACK_X, JACK_HOLE / 2, JACK_Z + JACK_HOLE / 2), PORT_MARGIN)
clear("switch cradle -> jack body (X)", (SW_X - SW_HALF) - (JACK_X + JACK_BODY_D / 2), 3.0)
clear("switch cradle -> SB stern pillar (X)", (PIL_PTS[1][0] - PIL_D / 2) - (SW_X + SW_HALF), 0.5)
clear("switch pins -> LiPo fence (Y)", (LIPO_Y0 - FENCE) - (STERN + WALL + SW_BODY[1] + 5.0), 0.5)
clear("switch cradle -> back plate (Z)", SW_Z - (SW_BODY[2] / 2 + FIT + SW_CRADLE_T) - FLOOR_T, 0.3)
clear("LiPo fence -> stern legs (Y)", (LIPO_Y0 - FENCE) - (LEG_PTS[0][1] + LEG_D / 2), 0.5)
clear("USB-C slots apart", abs(USB_PTS[1] - USB_PTS[0]) - USB_SLOT[0], 4.0)
clear("USB-C slot -> side edge", W / 2 - max(abs(x) for x in USB_PTS) - USB_SLOT[0] / 2, 5.0)
clear("countersink leaves floor", FLOOR_T - CS_H, 0.3)
clear("555 board over LiPo (Z room)", (DEPTH - FACE_T) - (FLOOR_T + LIPO[2] + 0.5 + PERF[2]), 1.0)

face, boss_h, pil_h = body()
plant, _thin, _narrow = money_plant(depth=PLANT_T)    # ★ ONE piece, one colour, glued in
_pb = plant.bounding_box()
_hw, _hh = _pb.size.X / 2 + PLANT_FIT, _pb.size.Y / 2 + PLANT_FIT  # pocket half-extents
clear("plant pocket -> side edges", W / 2 - _hw, 5.0)
clear("plant pocket -> bow/stern edges", H / 2 - (abs(ART_YC) + _hh), 8.0)
clear("plant pocket -> countersinks", min(max(abs(px) - CS_D / 2 - _hw, abs(py) - CS_D / 2 - _hh)
                                          for px, py in PIL_PTS), 2.0)
clear("back plate floor under the pocket", FLOOR_T - PLANT_T, 0.8)
clear("back-plate web between plant parts", MIN_FEATURE - 2 * PLANT_FIT, 2.0)
name = letters()
# ★ printability, measured directly on the orthogonal (s, z) wave
clear("wave gap between pulse edges", min(WAVE_LENS) - WAVE_STROKE, 2.5)
clear("wave gap on a corner (inner skin)", min(WAVE_LENS) * (CORNER_R - WAVE_D) / CORNER_R - WAVE_STROKE, 2.5)
clear("wave gap between high and low", min(WAVE_AMPS) - WAVE_STROKE, 2.5)
clear("wave longest pulse <= max", -(max(WAVE_LENS) - (WAVE_MAX_SEG + WAVE_MIN_SEG) - 1e-6), 0.0)
clear("wave amplitude varies (max - min)", max(WAVE_AMPS) - min(WAVE_AMPS), 3.0)
clear("wave -> face chamfer (Z)", (DEPTH - EDGE_CHAM) - (WAVE_LO + max(WAVE_AMPS) + WAVE_STROKE / 2), 1.5)
clear("wave -> back seam (Z)", (WAVE_LO - WAVE_STROKE / 2) - FLOOR_T, 1.5)
clear("wave inlay leaves wall", WALL - WAVE_D, 1.0)
clear("wave -> side pillars (X)", (W / 2 - WAVE_D) - (PIL_X + PIL_D / 2), 0.1)
clear("badge pocket -> side edge", (W - BADGE_W) / 2, 6.0)
clear("badge pocket width == glass opening", -abs(BADGE_W - (GLASS_W + 2 * GLASS_FIT)), -0.05)
clear("badge pocket -> glass opening", (GLASS_Y0 - GLASS_FIT) - (BADGE_YC + BADGE_H / 2), 15.0)
clear("badge pocket -> stern edge", (BADGE_YC - BADGE_H / 2) - STERN, 15.0)
clear("badge pocket leaves face", FACE_T - BADGE_D, 1.0)
back = backplate()


def inside(solid, x, y, z):
    c = BRepClass3d_SolidClassifier(solid.wrapped)
    c.Perform(gp_Pnt(x, y, z), 1e-7)
    return c.State() in (TopAbs_IN, TopAbs_ON)


assert not inside(face, *GLASS_C, DEPTH - FACE_T / 2), "glass opening not open"
assert inside(face, W / 2 - WALL / 2, 0, DEPTH / 2), "side wall missing"
assert not inside(face, 0, 0, FLOOR_T + 1), "body is not open at the back"
for ux in USB_PTS:
    assert not inside(face, ux, BOW - WALL / 2, USB_Z), "USB-C opening blocked"
assert not inside(face, JACK_X, STERN + WALL / 2, JACK_Z), "jack hole blocked"
assert not inside(face, SW_X, STERN + WALL / 2, SW_Z), "switch slot blocked"
assert not inside(face, SW_X, STERN + WALL + SW_BODY[1] / 2, SW_Z), "switch cradle is solid inside"
assert inside(face, SW_X + SW_BODY[0] / 2 + FIT + SW_CRADLE_T / 2, STERN + WALL + 0.5, SW_Z), "cradle wall missing"
for x in (-W / 2 + WALL / 2, W / 2 - WALL / 2):          # ★ the sides are CLEAN, full stop
    for y in range(int(STERN) + 8, int(BOW) - 8, 2):
        for z in (FLOOR_T + 1.0, SW_Z, USB_Z, DEPTH - FACE_T - 1.0):
            assert inside(face, x, y, z), f"something cut into a side wall at y={y}, z={z:.1f}"
for px, py in PIL_PTS:
    assert not inside(back, px, py, FLOOR_T / 2), "back-plate screw hole blocked"
for nm, sol in (("body", face), ("back plate", back)):
    assert len(sol.solids()) == 1, f"{nm} is {len(sol.solids())} solids"
# ★ the name: letters reach the face plane, sit on the pocket floor, and never overlap the body
nb = name.bounding_box()
assert abs(nb.max.Z - DEPTH) < 1e-6 and abs(nb.min.Z - (DEPTH - BADGE_D)) < 1e-6, "letters not flush"
assert (face & name).volume < 1e-3, "body and letters overlap — the slicer would double-print"
for w in WAVES:
    assert (face & w).volume < 1e-3, "body and wave overlap — the slicer would double-print"
accent = Compound(children=kids(name, *WAVES))   # ★ the body's whole second colour, one part
assert abs((face + name).volume - (face.volume + name.volume)) < 1e-5 * face.volume   # relative: OCC volume noise
probe = Pos(0, BADGE_YC, DEPTH - 0.2) * Box(BADGE_W - 2 * BADGE_R, BADGE_H - 2 * BADGE_R, 0.2, align=C)  # inside the rounded corners
assert (name & probe).volume > 1.0, "no letter material at the face plane"
assert (face & probe).volume < 1e-3, "body material left inside the pocket at the face plane"
# ★ the plant plate: flush with the back, a glue gap all round, the plant flush in ITS face
assert abs(_pb.min.Z) < 1e-6 and abs(_pb.max.Z - PLANT_T) < 1e-6, "plant not flush with the back"
assert (back & plant).volume < 1e-3, "plant collides with its pocket"
assert len(plant.solids()) == 1, "plant is not one piece"
assert not inside(back, LEAVES[0][0], ART_YC + LEAVES[0][1], PLANT_T / 2), "pocket missing under a leaf"
assert inside(back, LEAVES[0][0], ART_YC + LEAVES[0][1], PLANT_T + 0.3), "pocket goes through the back plate"
assert inside(back, 9.0, ART_YC + 28.0, PLANT_T / 2), "pocket is a box, not plant-shaped"   # between two coins
assert len(back.solids()) == 1
fb, bb = face.bounding_box(), back.bounding_box()
assert abs(fb.size.X - bb.size.X) < 1e-6 and abs(fb.size.Y - bb.size.Y) < 1e-6, "body/back plate not flush"
# ★ the sandwich closes: post top = PCB component side, boss bottom = PCB glass side
assert abs(fb.min.Z - FLOOR_T) < 1e-6, "body does not land on the back plate"
assert abs(bb.min.Z) < 1e-6
assert abs((DEPTH - FACE_T - boss_h) - bz(PCB_BOT)) < 1e-9, "bosses do not reach the board"
assert abs(bz(GLASS_FRONT) - DEPTH) < 1e-9, "glass is not flush with the face"

# ghost: Elecrow's real board through the SAME transform — if anything is placed wrong, this
# is where it shows (and the asserts below catch it before he does)
_m = import_step(MODEL).children[0]
KEEP = ("ESP32_DISPLAY", "DG-01", "GROVE", "PRT0003", "JST-XH", "TYPE_C", "ASM0004",
        "7-PIN", "PRT0004", "ASM0007", "ASM0008")
board = [BOARD() * c for c in _m.children if any(k in (c.label or "") for k in KEEP)]
gb = Compound(children=kids(*board)).bounding_box()
assert abs(gb.max.Z - DEPTH) < 0.3, f"ghost glass not at the face ({gb.max.Z:.2f} vs {DEPTH:.2f})"
assert gb.min.Z >= FLOOR_T + PLUG_CLEAR - 0.3, f"board parts reach the plug room ({gb.min.Z:.2f})"
assert gb.max.Y <= BOW - WALL + 0.05, f"board through the bow wall ({gb.max.Y:.2f})"
assert gb.min.X >= -W / 2 + WALL - 1e-3 and gb.max.X <= W / 2 - WALL + 1e-3, "board through a side wall"
for i, (px, py) in enumerate(HOLE_PTS):       # the hole really is under the post: no part there
    assert not any(inside(p.solids()[0], px, py, bz(PCB_TOP) + 0.5) for p in board
                   if p.solids() and p.bounding_box().min.Z > bz(PCB_TOP) - 0.1), f"part over hole {i}"

ghosts = board + [
    Pos(-LIPO[0] / 2, LIPO_Y0, FLOOR_T) * Box(*LIPO, align=MINS),
    Pos(-PERF[0] / 2, LIPO_Y0 + 2, FLOOR_T + LIPO[2] + 0.5) * Box(*PERF, align=MINS),
    Pos(JACK_X, STERN + WALL, JACK_Z) * Rot(-90, 0, 0) * cyl(JACK_BODY_D, JACK_BODY_L),
]
printed = [face, back]
export_step(Compound(children=kids(*printed, name, *WAVES, plant, *ghosts)), os.path.join(out, f"{PROJECT}.step"))
# ★ the root preview mesh carries the accents too — without them the text and wave were invisible
export_stl(Compound(children=kids(*printed, name, *WAVES, plant)), os.path.join(out, f"{PROJECT}.stl"))
# ★ multicolour: the body and the letters as two STLs in the SAME frame — load both into the
# slicer as ONE object with two parts and give the letters the second filament
# ★★ MULTICOLOUR = ONE FILE, SEPARATE BODIES (his rule) — as a STEP. ⛔ Not STL: touching bodies
#   (flush inlays) weld in an STL — the merged one split into 2,819 fragments. ⛔ Not 3MF (his
#   call). A STEP keeps every solid separate and labelled: "body" + "accent" (letters + wave).
_acc = Compound(children=kids(name, *WAVES), label="accent")
_bod = copy.copy(face)
_bod.label = "body"
# ★ the body file must carry ALL of its colours — asserted, because the letters went missing once
assert len(_acc.solids()) == len(name.solids()) + sum(len(w.solids()) for w in WAVES), "accent lost a part"
assert abs(_acc.volume - (name.volume + sum(w.volume for w in WAVES))) < 1e-3, "accent volume wrong"
export_step(Compound(children=[_bod, _acc], label=f"{PROJECT}-body"),
            os.path.join(prints, f"{PROJECT}-body.step"))
export_stl(back, os.path.join(prints, f"{PROJECT}-backplate.stl"))
export_stl(plant, os.path.join(prints, f"{PROJECT}-plant.stl"))
b = Compound(children=kids(*printed)).bounding_box()
assert abs(b.size.X - W) < 0.01 and abs(b.size.Y - H) < 0.01 and abs(b.size.Z - DEPTH) < 0.01

print(f"\nMURMUR housing — pass 2, CrowPanel Advance 2.4\n")
print(f"  overall        {W:.0f} x {H:.0f} x {DEPTH:.1f} mm   (Pocket SCÍON: 71 x 105 x 17)")
print(f"  face           flush touch glass {GLASS_W:.1f} x {GLASS_H:.1f} · nothing else (no touch plate)")
print(f"  bow edge       2 x USB-C {USB_SLOT[0]} x {USB_SLOT[1]} at x {USB_PTS[0]:+.1f} / {USB_PTS[1]:+.1f}")
print(f"  stern edge     plant jack O{JACK_HOLE} at x {JACK_X:+.0f} · power switch {SW_SLOT[0]} x {SW_SLOT[1]} "
      f"at x {SW_X:+.0f}   ·   sides: NOTHING")
print(f"  depth          floor {FLOOR_T} + plug room {PLUG_CLEAR} + board (sockets->glass) "
      f"{PARTS_TOP - GLASS_FRONT:.1f} = {DEPTH:.1f}")
print(f"  parts          BODY (face + sides, one piece) + flat BACK PLATE")
print(f"  name           {BADGE} in {FONT}, {_mb.size.X:.1f} x {_mb.size.Y:.1f}, pocket {BADGE_W:.1f} x "
      f"{BADGE_H:.1f} x {BADGE_D}, tracked {BADGE_TRACK:.2f} — letters a SEPARATE part (second colour), flush with the face")
print(f"  back           money plant {_pb.size.X:.0f} x {_pb.size.Y:.0f} x {PLANT_T}: ONE piece, glued flush into "
      f"a plant-shaped pocket (+{PLANT_FIT}/side); strokes/gaps >= {MIN_FEATURE} mm")
print(f"  side band      variable square wave ALL ROUND, holes cut it: {WAVE_STROKE} mm stroke,"
      f" heights {min(WAVE_AMPS):.1f}-{max(WAVE_AMPS):.1f} mm, lengths {min(WAVE_LENS):.1f}-{max(WAVE_LENS):.1f} mm,"
      f" {len(WAVE_LENS)} pulses round {PERIM:.0f} mm, inlaid {WAVE_D} (2nd colour)")
print(f"  fixings        board: 4 x M3 x 5 into face bosses ({boss_h:.1f} tall) · back plate: "
      f"4 x M3 x 10 c'sunk into wall pillars")
print("\nCLEARANCES:\n" + "\n".join(checks))
assert not _fail, "clearance failure: " + ", ".join(_fail)
print(f"\nPARTS:")
for nm, sol in (("body", face), ("back plate", back)):
    bx = sol.bounding_box()
    print(f"  {nm:6s}  {bx.size.X:5.1f} x {bx.size.Y:5.1f} x {bx.size.Z:4.1f}   {sol.volume/1000:5.1f} cm3")
print(f"\n★ {out}/{PROJECT}.step")
