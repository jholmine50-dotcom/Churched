import sys, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V09.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else r"D:\project\Fê\forte_work\v09_check.js"

blocks = 0
started = False
buf = []
with open(P, "r", encoding="utf-8", errors="surrogateescape") as f:
    while True:
        line = f.readline()
        if not line:
            break
        ls = line.lstrip()
        if not started:
            if ls.startswith("<script>"):
                started = True
                # inline content after tag?
                rest = line.split("<script>", 1)[1]
                if rest.strip():
                    buf.append(rest)
            continue
        if ls.startswith("</script>"):
            started = False
            blocks += 1
            buf.append("\n;\n")
            continue
        buf.append(re.sub(r"data:audio/mpeg;base64,[A-Za-z0-9+/=]+", "x", line))

with open(OUT, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as g:
    g.write("".join(buf))
print("script blocks:", blocks, "->", OUT)
