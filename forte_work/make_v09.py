import io, os, shutil

SRC = r"D:\project\Fê\forte_work\PREACH_FLOW_V08_REDESIGN.html"
DST = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V09.html"
TMP = r"D:\project\Fê\forte_work\V09_partial.html"

repls = [
    ("<title>PREACH FLOW V08 — Seletor de Música</title>",
     "<title>PREACH FLOW V09 — Interface Oficial</title>"),
    ("para pregação · V08</div>",
     "para pregação · V09</div>"),
]

# first pass: replace only in the head region (before <script>) by streaming lines
applied = [0, 0]
with open(SRC, "r", encoding="utf-8", errors="surrogateescape", newline="") as f, \
     open(TMP, "w", encoding="utf-8", errors="surrogateescape", newline="") as out:
    while True:
        line = f.readline()
        if not line:
            raise SystemExit("eof before script")
        if line.lstrip().startswith("<script>"):
            out.write(line)
            break
        for i, (a, b) in enumerate(repls):
            if a in line:
                line = line.replace(a, b)
                applied[i] += 1
        out.write(line)
    while True:
        chunk = f.read(1 << 22)
        if not chunk:
            break
        out.write(chunk)

print("applied", applied)
assert applied == [1, 1], "replacements not applied"
shutil.copyfile(TMP, DST)
print("size", os.path.getsize(DST))
