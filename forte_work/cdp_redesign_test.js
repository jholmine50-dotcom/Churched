// CDP test: open PREACH HTML headless, wait load, click forte, read status, capture console errors.
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const URL = "file:///C:/Users/Jhonatan/Desktop/PREACH_FLOW_V08_REDESIGN.html";
const PORT = 9333;
const USER_DIR = path.join(os.tmpdir(), "pf_cdp_" + Date.now());

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function getJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let d = "";
      res.on("data", c => d += c);
      res.on("end", () => { try { resolve(JSON.parse(d)); } catch (e) { reject(e); } });
    }).on("error", reject);
  });
}

async function main() {
  const chrome = spawn(CHROME, [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--disable-extensions",
    "--autoplay-policy=no-user-gesture-required",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${USER_DIR}`,
    "--window-size=1280,800",
    "about:blank",
  ], { stdio: ["ignore", "pipe", "pipe"] });

  let chromeErr = "";
  chrome.stderr.on("data", d => chromeErr += d);

  // wait for devtools
  let targets = null;
  for (let i = 0; i < 30; i++) {
    await sleep(500);
    try {
      targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`);
      break;
    } catch (e) { /* retry */ }
  }
  if (!targets) {
    console.log("FAIL: no devtools");
    chrome.kill();
    process.exit(1);
  }

  const page = targets.find(t => t.type === "page");
  if (!page) { console.log("FAIL: no page target"); chrome.kill(); process.exit(1); }

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let msgId = 0;
  const pending = new Map();
  const consoleMsgs = [];
  const pageErrors = [];

  ws.addEventListener("message", ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      pending.get(m.id)(m);
      pending.delete(m.id);
    } else if (m.method === "Runtime.consoleAPICalled") {
      const args = (m.params.args || []).map(a => a.value ?? a.description ?? a.type).join(" ");
      consoleMsgs.push(`[${m.params.type}] ${args}`);
    } else if (m.method === "Runtime.exceptionThrown") {
      const d = m.params.exceptionDetails;
      pageErrors.push((d.exception && (d.exception.description || d.exception.value)) || d.text || JSON.stringify(d));
    }
  });

  function send(method, params = {}) {
    return new Promise(resolve => {
      const id = ++msgId;
      pending.set(id, resolve);
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  await new Promise((res, rej) => {
    ws.addEventListener("open", res);
    ws.addEventListener("error", rej);
  });

  await send("Runtime.enable");
  await send("Page.enable");

  const t0 = Date.now();
  await send("Page.navigate", { url: URL });

  // wait for load event or timeout
  let loaded = false;
  for (let i = 0; i < 60; i++) {
    await sleep(1000);
    const r = await send("Runtime.evaluate", {
      expression: "document.readyState",
      returnByValue: true,
    });
    const st = r.result && r.result.result && r.result.result.value;
    if (st === "complete" || st === "interactive") { loaded = true; break; }
  }
  console.log("readyState wait:", loaded, "ms=", Date.now() - t0);

  // extra settle time for the big script
  await sleep(3000);

  async function shot(name) {
    const s = await send("Page.captureScreenshot", { format: "png" });
    const data = (s.result && s.result.data) || (s.result && s.result.result && s.result.result.data);
    if (data) {
      const out = path.join(__dirname, name);
      fs.writeFileSync(out, Buffer.from(data, "base64"));
      console.log("SHOT", out);
    } else {
      console.log("SHOT_FAIL", name, JSON.stringify(s).slice(0, 300));
    }
  }
  await shot("ui_redesign_initial.png");

  // probe UI
  const probes = [
    ["play_btn", "!!document.getElementById('play')"],
    ["forte_btn", "!!document.querySelector('[data-set=forte]')"],
    ["grid_children", "(document.getElementById('grid')||{}).children ? document.getElementById('grid').children.length : -1"],
    ["music_label", "(document.getElementById('musicLabel')||{}).textContent"],
    ["status", "(document.getElementById('status')||{}).textContent"],
    ["musics_keys", "typeof MUSICS!=='undefined' ? Object.keys(MUSICS).join(',') : 'NO_MUSICS'"],
    ["current_set", "typeof currentSet!=='undefined' ? currentSet : 'NO_VAR'"],
    ["handler_play", "document.getElementById('play') ? (typeof document.getElementById('play').onclick) : 'none'"],
  ];
  for (const [name, expr] of probes) {
    const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true });
    const v = r.result && r.result.result ? r.result.result.value : JSON.stringify(r.result);
    console.log(`PROBE ${name} =`, v);
    if (r.result && r.result.exceptionDetails) {
      console.log("  EXC", r.result.exceptionDetails.exception && r.result.exceptionDetails.exception.description);
    }
  }

  // click forte
  const clk = await send("Runtime.evaluate", {
    expression: `
      (function(){
        try {
          const b = document.querySelector('[data-set="forte"]');
          if(!b) return 'no btn';
          b.click();
          return 'clicked, currentSet=' + (typeof currentSet!=='undefined'?currentSet:'?') +
                 ' N=' + (typeof N!=='undefined'?N.length:'?') +
                 ' label=' + ((document.getElementById('musicLabel')||{}).textContent||'');
        } catch(e) { return 'ERR '+e.message; }
      })()
    `,
    returnByValue: true,
  });
  console.log("CLICK forte =>", clk.result && clk.result.result && clk.result.result.value);

  await sleep(500);

  // click play
  const play = await send("Runtime.evaluate", {
    expression: `
      (function(){
        try {
          const b = document.getElementById('play');
          if(!b) return 'no play';
          b.click();
          return 'clicked play, status=' + ((document.getElementById('status')||{}).textContent||'');
        } catch(e) { return 'ERR '+e.message; }
      })()
    `,
    returnByValue: true,
  });
  console.log("CLICK play =>", play.result && play.result.result && play.result.result.value);

  await sleep(6000);

  // final status
  const fin = await send("Runtime.evaluate", {
    expression: `JSON.stringify({
      set: typeof currentSet!=='undefined'?currentSet:null,
      n: typeof N!=='undefined'?N.length:null,
      status: (document.getElementById('status')||{}).textContent,
      started: typeof started!=='undefined'?started:null,
      musicLabel: (document.getElementById('musicLabel')||{}).textContent
    })`,
    returnByValue: true,
  });
  console.log("FINAL", fin.result && fin.result.result && fin.result.result.value);

  // screenshots (after interactions)
  await shot("ui_redesign_after.png");

  await send("Runtime.evaluate", { expression: "window.scrollTo(0, document.body.scrollHeight); 'ok'", returnByValue: true });
  await sleep(600);
  await shot("ui_redesign_bottom.png");

  console.log("PAGE_ERRORS", pageErrors.length);
  pageErrors.slice(0, 10).forEach(e => console.log("  ", String(e).slice(0, 300)));
  console.log("CONSOLE", consoleMsgs.length);
  consoleMsgs.slice(0, 15).forEach(m => console.log("  ", m.slice(0, 200)));

  ws.close();
  chrome.kill();
  process.exit(pageErrors.length > 0 ? 1 : 0);
}

main().catch(e => { console.error("FATAL", e); process.exit(1); });
