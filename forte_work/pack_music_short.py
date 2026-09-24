#!/usr/bin/env python3
"""Pack Separado_Music stems -> 9 tracks 48k at NATURAL duration (~5min) -> DATA_Forte.js."""
import base64
import glob
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
MP3_DIR = os.path.join(OUT_DIR, "mp3_music_short")
BITRATE = "48k"

STEM_MAP = {
    "Drums": "drums",
    "Bass": "bass",
    "Keyboard": "piano",
    "Percussion": "drums",
    "Strings": "guitar",
    "Synth": "other",
    "FX": "other",
    "Brass": "other",
    "Woodwinds": "other",
}

PROCESS = {
    "Drums": {"vol": 1.0, "af": None},
    "Bass": {"vol": 1.0, "af": None},
    "Keyboard": {"vol": 1.0, "af": None},
    "Percussion": {"vol": 0.55, "af": "highpass=f=6000"},
    "Strings": {"vol": 0.85, "af": "lowpass=f=4500"},
    "Synth": {"vol": 0.7, "af": "highpass=f=200"},
    "FX": {"vol": 0.35, "af": "lowpass=f=1200"},
    "Brass": {"vol": 0.4, "af": "equalizer=f=1200:g=4:w=1.2"},
    "Woodwinds": {"vol": 0.3, "af": "highpass=f=800,lowpass=f=3500"},
}

ORDER = ["Drums", "Bass", "Keyboard", "Percussion", "Strings", "Synth", "FX", "Brass", "Woodwinds"]
NEED = ("bass", "drums", "guitar", "other", "piano")


def find_src():
    hits = glob.glob(os.path.join("D:\\", "project", "*", "Downloads", "Separado_Music", "htdemucs_6s", "*", "drums.mp3"))
    if not hits:
        hits = glob.glob("D:/**/Separado_Music/htdemucs_6s/*/drums.mp3", recursive=True)
    if not hits:
        raise SystemExit("demucs drums.mp3 not found")
    src = os.path.dirname(hits[0])
    print("SRC", src)
    return src


def duration(path):
    r = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True, errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", r.stderr or "")
    if not m:
        raise RuntimeError("no duration: " + path)
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s


def src_for(src_dir, demucs_name):
    for ext in (".mp3", ".wav"):
        p = os.path.join(src_dir, demucs_name + ext)
        if os.path.isfile(p):
            return p
    raise SystemExit("cannot find " + demucs_name)


def encode_track(name, src_path, target_sec):
    os.makedirs(MP3_DIR, exist_ok=True)
    dst = os.path.join(MP3_DIR, name + ".mp3")
    p = PROCESS[name]
    filters = []
    if p["af"]:
        filters.append(p["af"])
    filters.append("volume=%.4f" % p["vol"])
    filters.append("atrim=0:%.3f" % target_sec)
    filters.append("asetpts=PTS-STARTPTS")
    filters.append("aformat=sample_rates=44100:channel_layouts=mono")
    af = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-i", src_path,
        "-af", af,
        "-c:a", "libmp3lame", "-b:a", BITRATE,
        dst,
    ]
    print(" ", name, "<-", os.path.basename(src_path), "vol=%.2f" % p["vol"], BITRATE, flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed %s: %s" % (name, (r.stderr or "")[-800:]))
    d = duration(dst)
    print("    %s %d bytes dur=%.2fs" % (dst, os.path.getsize(dst), d), flush=True)
    if abs(d - target_sec) > 3.0:
        raise RuntimeError("bad duration %s %.2f vs %.2f" % (name, d, target_sec))
    return dst


def main():
    src = find_src()
    have = {f.lower() for f in os.listdir(src)}
    for n in NEED:
        if (n + ".mp3") not in have and (n + ".wav") not in have:
            raise SystemExit("missing stem " + n)

    target_sec = duration(src_for(src, "drums"))
    print("target duration %.2fs (natural)" % target_sec)

    os.makedirs(MP3_DIR, exist_ok=True)
    for app_name in ORDER:
        encode_track(app_name, src_for(src, STEM_MAP[app_name]), target_sec)

    data = {}
    total_b64 = 0
    for name in ORDER:
        path = os.path.join(MP3_DIR, name + ".mp3")
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        data[name] = "data:audio/mpeg;base64," + b64
        total_b64 += len(b64)
        print("    %s b64=%d" % (name, len(b64)), flush=True)

    out_js = os.path.join(OUT_DIR, "DATA_Forte.js")
    with open(out_js, "w", encoding="utf-8", newline="\n") as f:
        f.write("{\n")
        items = list(data.items())
        for i, (k, v) in enumerate(items):
            comma = "," if i < len(items) - 1 else ""
            f.write('"%s":"%s"%s\n' % (k, v, comma))
        f.write("}\n")
    print("wrote %s size=%d total_b64=%d" % (out_js, os.path.getsize(out_js), total_b64))
    print("OK")


if __name__ == "__main__":
    main()
