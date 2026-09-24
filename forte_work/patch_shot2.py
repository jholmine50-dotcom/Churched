import io

f = r"D:\project\Fê\forte_work\cdp_redesign_test.js"
s = io.open(f, "r", encoding="utf-8").read()

old = 'await shot("ui_redesign_after.png");'
new = '''await shot("ui_redesign_after.png");

  await send("Runtime.evaluate", { expression: "window.scrollTo(0, document.body.scrollHeight); 'ok'", returnByValue: true });
  await sleep(600);
  await shot("ui_redesign_bottom.png");'''

assert old in s, "marker not found"
s = s.replace(old, new, 1)
io.open(f, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
