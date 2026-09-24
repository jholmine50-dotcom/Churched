import io

f = r"D:\project\Fê\forte_work\cdp_redesign_test.js"
s = io.open(f, "r", encoding="utf-8").read()

old = '''    const data = (s.result && s.result.data) || (s.result && s.result.result && s.result.result.data);
    if (data) {
      const out = path.join(__dirname, name);
      fs.writeFileSync(out, Buffer.from(data, "base64"));
      console.log("SHOT", out);
    } else {
      console.log("SHOT_FAIL", name, JSON.stringify(s).slice(0, 300));
    }'''

# current block may differ; locate function body by markers
start = s.find("const data = (s.result")
if start == -1:
    start = s.find("if (s.result && s.result.data)")
    if start == -1:
        raise SystemExit("marker not found")
end = s.find("}", s.find("SHOT_FAIL")) + 1
# include trailing newline handling: find the else closing
# safer: find from start to the line containing only spaces + } after SHOT_FAIL block
marker = 'console.log("SHOT_FAIL", name, JSON.stringify(s).slice(0, 300));'
mi = s.find(marker)
if mi == -1:
    raise SystemExit("fail marker not found")
end = s.find("\n", mi) + 1
end = s.find("}", s.find("else", mi)) + 1

block = s[start:end]
new = '''const data = (s.result && s.result.data) || (s.result && s.result.result && s.result.result.data);
    if (data) {
      const out = path.join(__dirname, name);
      fs.writeFileSync(out, Buffer.from(data, "base64"));
      console.log("SHOT", out);
    } else {
      console.log("SHOT_FAIL", name, JSON.stringify(s).slice(0, 300));
    }'''

s = s[:start] + new + s[end:]
io.open(f, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
