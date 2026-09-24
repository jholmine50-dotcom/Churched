#!/usr/bin/env python3
"""WAV → MP3 (balance) → DATA_OCEANS.js base64 object."""
import base64
import json
import os
import subprocess
import sys

OUT = os.path.dirname(os.path.abspath(__file__))
WAVS = os.path.join(OUT, "wavs")
MP3 = os.path.join(OUT, "mp3")
os.makedirs(MP3, exist_ok=True)

STEMS = [
    "Backing_Vocals", "Drums", "Bass", "Keyboard", "Percussion",
    "Strings", "Synth", "FX", "Brass", "Woodwinds",
]

# match prior balance so preset gates feel musical
GAINS = {
    "Backing_Vocals": 1.0,
    "Drums": 1.0,
    "Bass": 1.0,
    "Keyboard": 1.0,
    "Percussion": 1.0,
    "Strings": 1.0,
    "Synth": 1.0,
    "FX": 1.15,
    "Brass": 1.0,
    "Woodwinds": 0.55,
}
# amp multipliers previously used (Woodwinds 0.55, Percussion 2.0 etc.)
AMP = {
    "Backing_Vocals": 1.0,
    "Drums": 1.0,
    "Bass": 1.0,
    "Keyboard": 1.0,
    "Percussion": 2.0,
    "Strings": 1.0,
    "Synth": 1.0,
    "FX": 1.0,
    "Brass": 1.0,
    "Woodwinds": 1.0,
}


def ffmpeg_bin():
    for cand in ("ffmpeg", "ffmpeg.exe"):
        try:
            subprocess.run([cand, "-version"], capture_output=True, check=True)
            return cand
        except Exception:
            continue
    raise RuntimeError("ffmpeg not found")


def convert(ffmpeg):
    for name in STEMS:
        src = os.path.join(WAVS, f"{name}.wav")
        dst = os.path.join(MP3, f"{name}.mp3")
        g = GAINS.get(name, 1.0)
        a = AMP.get(name, 1.0)
        vol = g * a
        # old ffmpeg: no -hide_banner; use classic flags
        cmd = [
            ffmpeg, "-y", "-i", src,
            "-filter:a", f"volume={vol:.4f}",
            "-ac", "1", "-ar", "44100", "-b:a", "128k",
            dst,
        ]
        print(" ", " ".join(cmd[-6:]))
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"    {name}.mp3 {os.path.getsize(dst)} bytes")


def encode():
    data = {}
    for name in STEMS:
        path = os.path.join(MP3, f"{name}.mp3")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        data[name] = f"data:audio/mpeg;base64,{b64}"
        print(f"    {name} b64={len(b64)}")
    # Write as bare object (same shape as extracted V07 DATA)
    out_js = os.path.join(OUT, "DATA_OCEANS.js")
    with open(out_js, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        items = list(data.items())
        for i, (k, v) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            f.write(f'"{k}":"{v}"{comma}\n')
        f.write("}\n")
    print(f"wrote {out_js} size={os.path.getsize(out_js)}")


def main():
    ff = ffmpeg_bin()
    print("converting...")
    convert(ff)
    print("encoding base64...")
    encode()
    print("OK")


if __name__ == "__main__":
    main()
