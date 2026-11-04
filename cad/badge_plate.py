"""MURMUR — the badge FIELD PLATE (2026-11-04, his call): the body's pocket floor printed stringy,
so this alt-colour plate drops into the well AROUND the existing letters and glues flush with the
face — the name reads as inset lettering.
★ PRINT FACE UP (his call: the top surface matches the body's top-surface texture). Face up means
  the word reads RIGHT WAY ROUND as modelled — no mirroring (that is only for face-down prints).
★ Geometry is DERIVED from housing.py (pocket + wordmark), never retyped: we exec housing.py up to
  its side-band section, so a change to the badge there flows here.
Islands: the counters inside each R come out ~0.7 x 0.9 mm — too small to print or place, so they
are DROPPED; the R counters show the pocket floor (a sub-mm dot, not visible at arm's length)."""
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "housing.py")
src = open(SRC).read()
cutoff = src.index("# ------------------------------------------------------------------ the side band")
g = {"__name__": "badge_geom", "__file__": SRC}
exec(compile(src[:cutoff], SRC, "exec"), g)
from build123d import Kind, export_step, export_stl, extrude, offset, Pos, Compound

FIT_EDGE = 0.10      # per side, plate outline inside the pocket wall
FIT_LETTER = 0.12    # per side, hole round each letter (letters are the body's, already printed)

T = g["BADGE_D"]
outline = g["rplate"](g["BADGE_W"] - 2 * FIT_EDGE, g["BADGE_H"] - 2 * FIT_EDGE, T, g["BADGE_R"] - FIT_EDGE)
holes = extrude(offset(g["MARK"], amount=FIT_LETTER, kind=Kind.ARC), T + 2)
holes = Pos(0, 0, -1) * holes
plate = outline - holes

solids = plate.solids()
main = max(solids, key=lambda s: s.volume)
specks = [s for s in solids if s is not main]
print(f"plate {g['BADGE_W'] - 2 * FIT_EDGE:.2f} x {g['BADGE_H'] - 2 * FIT_EDGE:.2f} x {T} mm; "
      f"{len(specks)} counter specks: " + ", ".join(f"{s.bounding_box().size.X:.1f}x{s.bounding_box().size.Y:.1f}" for s in specks))
assert all(s.volume < 1.0 for s in specks), "a real piece split off — not just the R counters"
bb = main.bounding_box()
assert abs(bb.max.Z - T) < 1e-6 and abs(bb.min.Z) < 1e-6, "plate not z 0..T"

prints = os.path.join(os.path.expanduser(os.environ.get("MURMUR_OUT", "~/Collab/CAD/murmur")), "prints")
os.makedirs(prints, exist_ok=True)
export_stl(main, os.path.join(prints, "murmur-badge-plate.stl"))
export_step(Compound(children=[main], label="murmur-badge-plate"),
            os.path.join(prints, "murmur-badge-plate.step"))
print("wrote", prints)
