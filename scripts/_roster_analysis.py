"""Throwaway analysis: classify every indicator by why it is / isn't predicted,
to size the coverage-extension options. Prints a table + counts. No network."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lenses import config, narrative
from predictions import roster

rostered = {e.key for e in roster.build_roster()}

rows = []
for cat in config.CATEGORIES:
    for lens in cat["lenses"]:
        neutral = lens.id in narrative.NEUTRAL_LENSES
        for ind in lens.indicators:
            key = f"{cat['id']}/{lens.id}/{ind.id}"
            info = roster._is_info_rule(ind.rule)
            rows.append(dict(
                key=key, cat=cat["id"], source=ind.source,
                eia_route=bool(ind.eia_route) if ind.source == "eia" else "-",
                neutral=neutral, info=info, rostered=key in rostered))

def count(pred):
    return sum(1 for r in rows if pred(r))

print(f"TOTAL indicators: {len(rows)}")
print(f"Currently rostered (predicted): {len(rostered)}")
print()
# Reasons for exclusion (in roster.py order; first matching reason wins)
def reason(r):
    if r["cat"] == "banking": return "banking (quarterly FDIC)"
    if r["neutral"]: return "neutral lens (asset prices)"
    if r["source"] not in ("fred", "eia"): return f"source={r['source']}"
    if r["source"] == "eia" and not r["eia_route"]: return "eia computed (no route)"
    if r["info"]: return "info-only rule"
    return "(rostered)"

from collections import Counter
c = Counter(reason(r) for r in rows)
print("Exclusion reason breakdown:")
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print(f"  {v:3d}  {k}")
print()

# The uncontested-extension candidates: info-only, fred/eia w/ route, non-banking, non-neutral
print("=== INFO-ONLY FRED/EIA series (the UNCONTESTED extension candidates) ===")
for r in rows:
    if reason(r) == "info-only rule":
        print(f"  {r['key']}  [{r['source']}]")
print()
print("=== NEUTRAL-LENS (asset price) series — CONTESTED ===")
for r in rows:
    if reason(r) == "neutral lens (asset prices)":
        print(f"  {r['key']}  [{r['source']}]")
print()
print("=== NON-FRED/EIA source series — CONTESTED (needs fetch plumbing) ===")
for r in rows:
    if reason(r).startswith("source="):
        print(f"  {r['key']}  {reason(r)}")
print()
print("=== BANKING series — needs FDIC fetch + quarterly viability ===")
for r in rows:
    if reason(r) == "banking (quarterly FDIC)":
        print(f"  {r['key']}")
print()
print("=== EIA computed (no route) ===")
for r in rows:
    if reason(r) == "eia computed (no route)":
        print(f"  {r['key']}")
