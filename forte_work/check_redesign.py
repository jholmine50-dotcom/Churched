import sys, os, re

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"D:\project\Fê\forte_work\PREACH_FLOW_V08_REDESIGN.html"
print("size", os.path.getsize(P))

head = open(P, "r", encoding="utf-8", errors="surrogateescape").read(3_000_000)

ids = ["play","stop","fadeBtn","duckBtn","fader","num","exprPct","scene","sceneDesc",
       "masterFader","masterNum","status","pill","trackList","tracksHint","musicLabel",
       "timeline","elapsed","total","remaining","timelineState","loopBtn","grid",
       "dockCount","musicDock"]
ok = True
for i in ids:
    c = head.count('id="' + i + '"')
    if c != 1:
        print("BAD id", i, c)
        ok = False
print("ids:", "OK" if ok else "FAIL")
print("style tags:", head.count("<style>"), head.count("</style>"))
print("music-opt buttons:", head.count('class="music-opt'))
print("data-set:", head.count("data-set="))
for cls in ["music-opt","talk-btn","loop-btn","mute-btn","track-item","primary","two-col","side-stack"]:
    print(cls, head.count(cls))
print("body/app:", "app" in head, "<main" in head, "</main>" in head)
