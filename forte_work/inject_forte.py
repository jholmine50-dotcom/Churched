#!/usr/bin/env python3
"""Inject forte set into a target HTML (default: clean pre-inject backup)."""
import argparse
import glob
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SET_KEY = "forte"
LABEL = "Oração Forte"
SUB = "9 camadas instrumentais"
REQUIRED = ["Drums", "Bass", "Keyboard", "Percussion", "Strings", "Synth", "FX", "Brass", "Woodwinds"]


def find_html_arg(arg):
    if arg:
        if not os.path.isfile(arg):
            raise SystemExit("html not found: " + arg)
        return arg
    hits = [
        h for h in glob.glob(r"C:\Users\*\Desktop\PREACH_FLOW_V08*.html")
        if "pre_inject" in os.path.basename(h).lower()
    ]
    if not hits:
        hits = [
            h for h in glob.glob(r"C:\Users\*\Desktop\PREACH_FLOW_V08*.html")
            if not h.endswith(".tmp") and not h.endswith(".bak")
        ]
    if not hits:
        raise SystemExit("html not found")
    # prefer clean backup (smaller) when no arg — caller should pass explicit path
    return min(hits, key=os.path.getsize)


def find_data():
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "DATA_Forte.js")
    if os.path.isfile(p) and os.path.getsize(p) > 1000:
        return p
    hits = glob.glob(r"D:\project\*\forte_work\DATA_Forte.js")
    hits = [h for h in hits if os.path.getsize(h) > 1000]
    if not hits:
        raise SystemExit("DATA_Forte.js not found or empty")
    return max(hits, key=os.path.getsize)


def redact(s):
    return re.sub(r"data:audio/mpeg;base64,[A-Za-z0-9+/=]+", "x", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=None, help="target HTML path")
    ap.add_argument("--data", default=None, help="DATA_Forte.js path")
    ap.add_argument("--out", default=None, help="output HTML (default: overwrite --html)")
    args = ap.parse_args()

    html_path = find_html_arg(args.html)
    data_path = args.data or find_data()
    out_path = args.out or html_path
    print("HTML", html_path, os.path.getsize(html_path))
    print("DATA", data_path, os.path.getsize(data_path))
    print("OUT", out_path)

    # refuse if already injected
    with open(html_path, "r", encoding="utf-8", errors="surrogateescape") as f:
        for i, line in enumerate(f):
            if f"{SET_KEY}:{{label:" in line or f'data-set="{SET_KEY}"' in line:
                raise SystemExit(f"already injected at line {i+1}")
            if i > 5000:
                break

    with open(data_path, "r", encoding="ascii", errors="strict") as f:
        tracks = f.read().strip()
    if not (tracks.startswith("{") and tracks.endswith("}")):
        raise SystemExit("DATA_Forte not an object")
    for k in REQUIRED:
        if f'"{k}":"data:' not in tracks:
            raise SystemExit(f"missing key {k}")

    tmp = out_path + ".tmp"
    btn = (
        f'  <button class="music-opt" data-set="{SET_KEY}">{LABEL}'
        f'<span class="mo-sub">{SUB}</span></button>\n'
    )
    entry_prefix = f'  {SET_KEY}:{{label:"{LABEL}",tracks:'
    entry_suffix = "},\n"

    done_btn = False
    done_oceans_comma = False
    done_entry = False
    in_musics = False

    with open(html_path, "r", encoding="utf-8", errors="surrogateescape", newline="") as fin, \
         open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as fout:
        for line in fin:
            if line.startswith("const MUSICS="):
                in_musics = True
                fout.write(line)
                continue

            if not done_btn and 'data-set="oceans"' in line:
                fout.write(line)
                fout.write(btn)
                done_btn = True
                continue

            if in_musics and not done_entry:
                if line.startswith("  oceans:{label:"):
                    stripped = line.rstrip("\r\n")
                    eol = line[len(stripped):]
                    if not stripped.endswith(","):
                        stripped = stripped + ","
                    fout.write(stripped + eol)
                    done_oceans_comma = True
                    continue
                if done_oceans_comma and line.rstrip("\r\n") == "};":
                    fout.write(entry_prefix)
                    fout.write(tracks)
                    fout.write(entry_suffix)
                    fout.write(line)
                    done_entry = True
                    in_musics = False
                    continue

            fout.write(line)

    del tracks

    if not (done_btn and done_oceans_comma and done_entry):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise SystemExit(
            f"incomplete btn={done_btn} comma={done_oceans_comma} entry={done_entry}"
        )

    os.replace(tmp, out_path)
    size = os.path.getsize(out_path)
    print(f"injected set={SET_KEY} label={LABEL} size={size}")

    # extract light JS for node --check
    js_path = os.path.join(os.path.dirname(os.path.abspath(data_path)), "v08_check.js")
    in_script = False
    with open(out_path, "r", encoding="utf-8", errors="surrogateescape") as fin, \
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

    found = {"btn": False, "entry": False, "musics": False, "switch": False}
    with open(out_path, "r", encoding="utf-8", errors="surrogateescape") as f:
        for i, line in enumerate(f):
            if i < 100 and f'data-set="{SET_KEY}"' in line:
                found["btn"] = True
            if f'{SET_KEY}:{{label:"{LABEL}"' in line:
                found["entry"] = True
            if line.startswith("const MUSICS="):
                found["musics"] = True
            if "function switchMusic" in line:
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

    if "srcMap={...MUSICS[id].tracks}" not in light:
        raise SystemExit("switchMusic pattern missing")

    print("ALL_OK")


if __name__ == "__main__":
    main()
