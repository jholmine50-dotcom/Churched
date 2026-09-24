import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

src = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V09.html"
tmp = r"D:\project\Fê\forte_work\V09c.html"

n = 0
with open(src, "r", encoding="utf-8", errors="surrogateescape", newline="") as f, \
     open(tmp, "w", encoding="utf-8", errors="surrogateescape", newline="") as g:
    for line in f:
        if "setMode(saved===" in line:
            n += 1
            continue
        g.write(line)
print("removed", n)
assert n == 1
