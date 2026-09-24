import sys, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"D:\project\Fê\forte_work\PREACH_FLOW_V08_REDESIGN.html"
OUT = r"D:\project\Fê\forte_work\v08_recheck.js"

started = False
with open(P, "r", encoding="utf-8", errors="surrogateescape") as f, \
     open(OUT, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as g:
    while True:
        line = f.readline()
        if not line:
            break
        if not started:
            if line.lstrip().startswith("<script>"):
                started = True
            continue
        if line.lstrip().startswith("</script>"):
            break
        # replace huge base64 data URIs with a small placeholder
        line = re.sub(r'data:audio/mpeg;base64,[A-Za-z0-9+/=]+', 'x', line)
        g.write(line)
print("extracted", OUT)
