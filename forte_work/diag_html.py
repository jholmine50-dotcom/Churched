#!/usr/bin/env python3
"""Diagnose HTML structure: dock buttons, MUSICS keys, line sizes."""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATHS = [
    r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V08_ADD_TRACKS.html",
    r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V08_ADD_TRACKS.pre_inject_orig.html",
]

for path in PATHS:
    if not os.path.isfile(path):
        print("MISSING", path)
        continue
    print("=" * 60)
    print(os.path.basename(path), os.path.getsize(path))
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
        for i, line in enumerate(f, 1):
            s = line.rstrip("\r\n")
            if 'class="music-opt"' in s or 'data-set=' in s and "button" in s:
                print(f"  L{i}: {s[:120]}")
            if s.startswith("  original:{label:") or s.startswith("  oceans:{label:") or s.startswith("  forte:{label:"):
                print(f"  L{i}: key_line len={len(s)} start={s[:80]!r}")
            if s.startswith("const MUSICS="):
                print(f"  L{i}: MUSICS start")
            if s == "};":
                print(f"  L{i}: MUSICS close?")
            if i <= 35 and "music-dock" in s:
                print(f"  L{i}: dock area {s[:100]!r}")
            if i > 100 and not (s.startswith("  ") and "label:" in s):
                # stop early scan after dock+musics markers
                if i > 90:
                    break
