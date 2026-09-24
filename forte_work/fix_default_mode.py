import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

F = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V09.html"
TMP = r"D:\project\Fê\forte_work\V09b.html"

done = []
with open(F, "r", encoding="utf-8", errors="surrogateescape", newline="") as src, \
     open(TMP, "w", encoding="utf-8", errors="surrogateescape", newline="") as out:
    while True:
        line = src.readline()
        if not line:
            break
        if "pf_mode" in line and "setItem" in line:
            line = line.replace("    try{localStorage.setItem('pf_mode',m)}catch(e){}\n", "")
            if "setItem" in line:
                line = ""
            done.append("setItem removed")
        elif "pf_mode" in line and "getItem" in line:
            line = "  setMode('base');\n"
            done.append("default base")
        out.write(line)
        if len(done) == 2:
            while True:
                chunk = src.read(1 << 22)
                if not chunk:
                    break
                out.write(chunk)
            break

print("changes:", done)
assert len(done) == 2, done
