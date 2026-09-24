#!/usr/bin/env python3
"""Replace existing forte entry in PREACH HTML with new DATA_Forte.js content."""
import argparse
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SET_KEY = "forte"
LABEL = "Oração Forte"
REQUIRED = ["Drums", "Bass", "Keyboard", "Percussion", "Strings", "Synth", "FX", "Brass", "Woodwinds"]


def redact(s):
    return re.sub(r"data:audio/mpeg;base64,[A-Za-z0-9+/=]+", "x", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--data", required=True)
    args = ap.parse_args()

    html_path = args.html
    data_path = args.data
    print("HTML", html_path, os.path.getsize(html_path))
    print("DATA", data_path, os.path.getsize(data_path))

    with open(data_path, "r", encoding="ascii", errors="strict") as f:
        tracks = f.read().strip()
    if not (tracks.startswith("{") and tracks.endswith("}")):
        raise SystemExit("DATA not an object")
    for k in REQUIRED:
        if f'"{k}":"data:' not in tracks:
            raise SystemExit(f"missing key {k}")

    entry_prefix = f'  {SET_KEY}:{{label:"{LABEL}",tracks:'
    entry_suffix = "},\n"

    # First pass: locate line numbers of forte entry and MUSICS close
    start_line = None
    close_line = None
    with open(html_path, "r", encoding="utf-8", errors="surrogateescape") as f:
        for i, line in enumerate(f, 1):
            s = line.rstrip("\r\n")
            if start_line is None and s.startswith(f"  {SET_KEY}:{{label:"):
                start_line = i
            elif start_line is not None and s == "};":
                close_line = i
                break
    if not start_line or not close_line:
        raise SystemExit(f"forte entry not found start={start_line} close={close_line}")
    print(f"forte entry lines {start_line}..{close_line - 1}, MUSICS close at {close_line}")

    tmp = html_path + ".tmp"
    with open(html_path, "r", encoding="utf-8", errors="surrogateescape", newline="") as fin, \
         open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as fout:
        for i, line in enumerate(fin, 1):
            if i == start_line:
                fout.write(entry_prefix)
                fout.write(tracks)
                fout.write(entry_suffix)
                continue
            if start_line < i < close_line:
                continue  # drop old forte lines
            fout.write(line)

    del tracks
    os.replace(tmp, html_path)
    size = os.path.getsize(html_path)
    print(f"replaced forte size={size}")

    # extract light JS
    js_path = os.path.join(os.path.dirname(os.path.abspath(data_path)), "v08_check.js")
    in_script = False
    with open(html_path, "r", encoding="utf-8", errors="surrogateescape") as fin, \
         open(js_path, "w", encoding="utf-8", newline="\n") as fout:
        for line in fin:
            if not in_script:
                if "<script>" in line:
                    in_script = True
                    after = line.split("<script>", 1)[1]
                    if "</script>" in after:
                        before = after.split("</script>", 1)[0]
                        fout.write(redact(before) + "\n")
                        in_script = False
                    elif after.strip():
                        fout.write(redact(after))
                continue
            if "</script>" in line:
                before = line.split("</script>", 1)[0]
                fout.write(redact(before))
                in_script = False
                break
            fout.write(redact(line))

    r = subprocess.run(
        ["node", "--check", js_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print("node --check", r.returncode)
    if r.returncode != 0:
        print((r.stderr or "")[:3000])
        raise SystemExit("syntax check failed")

    found = {"btn_forte": False, "entry_forte": False, "musics": False, "switch": False}
    with open(html_path, "r", encoding="utf-8", errors="surrogateescape") as f:
        for i, line in enumerate(f):
            s = line.rstrip("\r\n")
            if f'data-set="{SET_KEY}"' in s:
                found["btn_forte"] = True
            if s.startswith(f"  {SET_KEY}:{{label:"):
                found["entry_forte"] = True
            if s.startswith("const MUSICS="):
                found["musics"] = True
            if "function switchMusic" in s:
                found["switch"] = True
            if all(found.values()):
                break
    print(found)
    if not all(found.values()):
        raise SystemExit("marker missing")

    with open(js_path, "r", encoding="utf-8") as f:
        light = f.read()
    sets = re.findall(r"^\s+(\w+):\{label:", light, re.M)
    print("sets", sets)
    if set(sets) != {"original", "oceans", SET_KEY}:
        raise SystemExit(f"unexpected sets {sets}")

    # exactly one forte entry
    n = sum(1 for ln in light.splitlines() if ln.strip().startswith(f"{SET_KEY}:{{label:"))
    if n != 1:
        raise SystemExit(f"forte entry count {n}")

    print("ALL_OK")


if __name__ == "__main__":
    main()
