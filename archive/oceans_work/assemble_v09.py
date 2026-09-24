#!/usr/bin/env python3
"""Assemble V09 HTML from shell + contemplative (V07) + oceans DATA_OCEANS.js."""
import os
import re
import sys

SHELL = r"C:\Users\Jhonatan\AppData\Local\Temp\opencode\preach_flow_v09_shell.html"
V07 = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_STANDALONE_V07_INTERFACE_STOP.html"
OCEANS = r"D:\project\Fê\archive\oceans_work\DATA_OCEANS.js"
OUT = r"D:\project\Fê\archive\PREACH_FLOW_STANDALONE_V09_MULTI_SONG.html"


def extract_contemplative(path):
    with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
        head = f.read(8_000_000)  # DATA is near start (~line 54)
    m = re.search(r"const DATA=(\{.*?\});", head, re.S)
    if not m:
        # fallback: larger read
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            data = f.read(50_000_000)
        m = re.search(r"const DATA=(\{.*?\});", data, re.S)
    if not m:
        raise SystemExit("DATA not found in V07")
    obj = m.group(1)
    # validate keys
    for k in ["Backing_Vocals", "Drums", "Bass", "Keyboard", "Percussion",
              "Strings", "Synth", "FX", "Brass", "Woodwinds"]:
        if f'"{k}"' not in obj:
            raise SystemExit(f"missing key {k} in contemplative DATA")
    return obj


def main():
    print("reading shell...")
    with open(SHELL, "r", encoding="utf-8") as f:
        shell = f.read()
    if "__DATA_CONTEMPLATIVE__" not in shell or "__DATA_OCEANS__" not in shell:
        raise SystemExit("shell placeholders missing")

    print("extracting contemplative from V07...")
    a = extract_contemplative(V07)
    print(f"  contemplative bytes={len(a)}")

    print("reading oceans DATA...")
    with open(OCEANS, "r", encoding="utf-8") as f:
        b = f.read().strip()
    if not (b.startswith("{") and b.endswith("}")):
        raise SystemExit("OCEANS DATA not an object")
    for k in ["Backing_Vocals", "Drums", "Bass", "Keyboard", "Percussion",
              "Strings", "Synth", "FX", "Brass", "Woodwinds"]:
        if f'"{k}"' not in b:
            raise SystemExit(f"missing key {k} in OCEANS DATA")
    print(f"  oceans bytes={len(b)}")

    html = shell.replace("__DATA_CONTEMPLATIVE__", a).replace("__DATA_OCEANS__", b)
    if "__DATA_" in html:
        raise SystemExit("unreplaced placeholder remains")

    # extract JS for syntax check
    m = re.search(r"<script>\n(.*)\n</script>\s*</body>", html, re.S)
    if not m:
        raise SystemExit("script block not found")
    js_path = os.path.join(os.path.dirname(OCEANS), "v09_assembled.js")
    with open(js_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(m.group(1))
    print(f"js check file {js_path} ({os.path.getsize(js_path)} bytes)")

    print(f"writing {OUT}...")
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"done size={os.path.getsize(OUT)}")


if __name__ == "__main__":
    main()
