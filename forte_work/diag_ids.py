#!/usr/bin/env python3
"""Check element IDs used by JS vs defined in HTML, and handler wiring."""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V08_ADD_TRACKS.html"

# Read only non-data regions
chunks = []
with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
    for i, line in enumerate(f, 1):
        if i <= 70 or i >= 86:
            s = line.rstrip("\r\n")
            if len(s) > 1000:
                s = s[:300] + "...[redacted]..."
            chunks.append(s)
        if i >= 520:
            break

text = "\n".join(chunks)

ids_used = set(re.findall(r"getElementById\('([^']+)'\)", text))
ids_used |= set(re.findall(r"byId\('([^']+)'\)", text))
ids_def = set(re.findall(r'id="([^"]+)"', text))

print("IDs used by JS:", sorted(ids_used))
print("IDs defined in HTML:", sorted(ids_def))
missing = sorted(x for x in ids_used if x not in ids_def)
print("MISSING IDs:", missing)

# Handlers
for pat in [
    r"byId\('play'\)\.onclick",
    r"byId\('stop'\)\.onclick",
    r"music-opt",
    r"switchMusic",
    r"function playAll",
    r"function switchMusic",
    r"function applyMix",
    r"fader\.oninput",
    r"timeline\.oninput",
    r"addEventListener\('change'",
]:
    found = bool(re.search(pat, text))
    print(f"  {pat}: {'OK' if found else 'MISSING'}")

# Duplicate id check
all_ids = re.findall(r'id="([^"]+)"', text)
from collections import Counter
dups = {k: v for k, v in Counter(all_ids).items() if v > 1}
print("duplicate ids:", dups or "none")
