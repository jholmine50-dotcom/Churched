import os, re, json, wave, numpy as np

W = r"D:\project\Fê\archive\oceans_work\wavs"
for n in ["_mix_ref", "FX", "Keyboard", "Strings", "Brass", "Drums"]:
    with wave.open(os.path.join(W, n + ".wav")) as w:
        d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        sr = w.getframerate()
    wins = []
    for t0 in [0, 20, 50, 80, 110, 140, 170]:
        i = int(t0 * sr)
        j = min(len(d), i + int(5 * sr))
        if i >= len(d):
            break
        wins.append((t0, round(float(np.sqrt(np.mean(d[i:j] ** 2))), 4)))
    print(n, wins)

html_path = r"D:\project\Fê\archive\PREACH_FLOW_STANDALONE_V09_MULTI_SONG.html"
size = os.path.getsize(html_path)
needles = [
    b"const DATA_A={",
    b"const DATA_B={",
    b'data-song="contemplative"',
    b'data-song="oceans"',
    b"__DATA_",
    b"async function switchSong",
]
pos = {n: None for n in needles}
with open(html_path, "rb") as f:
    window = b""
    off = 0
    while True:
        data = f.read(4_000_000)
        if not data:
            break
        buf = window + data
        for n in needles:
            if pos[n] is None:
                i = buf.find(n)
                if i >= 0:
                    pos[n] = off - len(window) + i
        window = data[-80:]
        off += len(data)
        if all(v is not None for v in pos.values()):
            break
print("size", size)
for n, p in pos.items():
    print(n.decode(), p)

# external URLs outside data:uris in shell + assembled light JS
shell = r"C:\Users\Jhonatan\AppData\Local\Temp\opencode\preach_flow_v09_shell.html"
with open(shell, "r", encoding="utf-8") as f:
    sc = f.read()
print("shell_urls", re.findall(r"https?://[^\s\"']+", sc))

js = r"D:\project\Fê\archive\oceans_work\v09_assembled.js"
with open(js, "r", encoding="utf-8") as f:
    light = f.read()
light = re.sub(r"data:audio/mpeg;base64,[A-Za-z0-9+/=]+", "x", light)
print("js_urls", re.findall(r"https?://[^\s\"']+", light))
m = re.search(r"const DATA_A=(\{.*?\});\nconst DATA_B=(\{.*?\});\n", light, re.S)
print("AB_match", bool(m))
if m:
    A = json.loads(m.group(1))
    B = json.loads(m.group(2))
    N = ["Backing_Vocals", "Drums", "Bass", "Keyboard", "Percussion",
         "Strings", "Synth", "FX", "Brass", "Woodwinds"]
    print("A10", len(A) == 10 and all(k in A for k in N))
    print("B10", len(B) == 10 and all(k in B for k in N))
    print("A_prefix", A["Keyboard"][:48])
    print("B_prefix", B["Keyboard"][:48])
print("switchSong", "async function switchSong" in light)
print("no_placeholder_in_js", "__DATA_" not in light)

# HTML body has pills (outside huge DATA strings) — check via positions already
print("pills_ok", pos[b'data-song="contemplative"'] is not None and pos[b'data-song="oceans"'] is not None)
print("DATA_order", pos[b"const DATA_A={"] is not None and pos[b"const DATA_B={"] is not None
          and pos[b"const DATA_A={"] < pos[b"const DATA_B={"])
print("ALL_OK", all(pos[n] is not None for n in needles if n != b"__DATA_")
      and pos[b"__DATA_"] is None
      and size > 70_000_000)
