import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HTML = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V08_ADD_TRACKS.html"
PART = r"D:\project\Fê\forte_work\new_ui.html.part"
OUT = r"D:\project\Fê\forte_work\PREACH_FLOW_V08_REDESIGN.html"

with open(PART, "r", encoding="utf-8", errors="surrogateescape") as f:
    part = f.read()
if not part.endswith("\n"):
    part += "\n"

with open(HTML, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
    pre = []
    while True:
        line = f.readline()
        if not line:
            raise SystemExit("style not found")
        if line.lstrip().startswith("<style>"):
            break
        pre.append(line)

    while True:
        line = f.readline()
        if not line:
            raise SystemExit("script not found")
        if line.lstrip().startswith("<script>"):
            post = [line]
            break

    with open(OUT, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as out:
        out.write("".join(pre))
        out.write(part)
        out.write("".join(post))
        while True:
            chunk = f.read(1 << 22)
            if not chunk:
                break
            out.write(chunk)

print("OK", OUT)
