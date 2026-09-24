#!/usr/bin/env python3
"""Final marker validation on shipped HTML."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V08_ADD_TRACKS.html"
checks = {
    "btn_forte": False,
    "btn_orig": False,
    "btn_oceans": False,
    "entry_forte": False,
    "entry_orig": False,
    "entry_oceans": False,
    "musics": False,
    "switch": False,
    "script_open": 0,
    "script_close": 0,
}
with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
    for i, line in enumerate(f, 1):
        s = line.rstrip("\r\n")
        if 'data-set="forte"' in s:
            checks["btn_forte"] = True
        if 'data-set="original"' in s:
            checks["btn_orig"] = True
        if 'data-set="oceans"' in s:
            checks["btn_oceans"] = True
        if s.startswith("  forte:{label:"):
            checks["entry_forte"] = True
        if s.startswith("  original:{label:"):
            checks["entry_orig"] = True
        if s.startswith("  oceans:{label:"):
            checks["entry_oceans"] = True
        if s.startswith("const MUSICS="):
            checks["musics"] = True
        if "function switchMusic" in s:
            checks["switch"] = True
        if "<script>" in s:
            checks["script_open"] += 1
        if "</script>" in s:
            checks["script_close"] += 1
        if i > 600:
            break
print(checks)
ok = (
    checks["btn_forte"]
    and checks["btn_orig"]
    and checks["btn_oceans"]
    and checks["entry_forte"]
    and checks["entry_orig"]
    and checks["entry_oceans"]
    and checks["musics"]
    and checks["switch"]
    and checks["script_open"] == 1
    and checks["script_close"] == 1
)
print("ALL_MARKERS_OK" if ok else "MARKERS_FAIL")
sys.exit(0 if ok else 1)
