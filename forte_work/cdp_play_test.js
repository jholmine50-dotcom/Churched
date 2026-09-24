// CDP play test: navigate, call playAll, inspect state.
const { spawn } = require("child_process");
const os = require("os");
const path = require("path");
const http = require("http");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const URL = "file:///C:/Users/Jhonatan/Desktop/PREACH_FLOW_V08_ADD_TRACKS.html";
const PORT = 9335;
const USER_DIR = path.join(os.tmpdir(), "pf_cdp_play_" + Date.now());
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = url => new Promise((res, rej) => {
  http.get(url, r => { let d = ""; r.on("data", c => d += c); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on("error", rej);
});

(async () => {
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
    "--autoplay-policy=no-user-gesture-required",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${USER_DIR}`,
    "about:blank",
  ], { stdio: ["ignore", "pipe", "pipe"] });

  let targets;
  for (let i = 0; i < 30; i++) {
    await sleep(500);
    try { targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`); break; } catch (e) { /* retry */ }
  }
  const page = targets.find(t => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 0;
  const pend = new Map();
  const errs = [];
  const cons = [];
  ws.addEventListener("message", ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); }
    else if (m.method === "Runtime.exceptionThrown") errs.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
    else if (m.method === "Runtime.consoleAPICalled") cons.push(`[${m.params.type}] ${(m.params.args || []).map(a => a.value ?? a.description).join(" ")}`);
  });
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  await send("Runtime.enable");
  await send("Page.enable");
  await send("Page.navigate", { url: URL });
  for (let i = 0; i < 40; i++) {
    await sleep(1000);
    const r = await send("Runtime.evaluate", { expression: "document.readyState", returnByValue: true });
    if (r.result?.result?.value === "complete") break;
  }
  await sleep(2000);

  const r1 = await send("Runtime.evaluate", {
    expression: `
      (async()=>{
        try {
          await playAll();
          return JSON.stringify({started, status: document.getElementById('status').textContent, state: ctx?ctx.state:'no-ctx', media: Object.keys(media).length, n: N.length, set: currentSet});
        } catch(e) { return 'THROW '+e.message; }
      })()
    `,
    awaitPromise: true,
    returnByValue: true,
  });
  console.log("playAll =>", r1.result?.result?.value ?? JSON.stringify(r1.result));

  await sleep(3000);
  const r2 = await send("Runtime.evaluate", {
    expression: `JSON.stringify({started, status:document.getElementById('status').textContent, t: N.map(n=>media[n]?+media[n].currentTime.toFixed(1):null), paused: N.map(n=>media[n]?media[n].paused:null), meta: metadataReady, dur: totalDuration})`,
    returnByValue: true,
  });
  console.log("after 3s =>", r2.result?.result?.value);

  // switch to forte then play
  const r3 = await send("Runtime.evaluate", {
    expression: `
      (async()=>{
        try {
          switchMusic('forte');
          await playAll();
          await new Promise(r=>setTimeout(r,1500));
          return JSON.stringify({started, set:currentSet, status:document.getElementById('status').textContent, t:N.map(n=>media[n]?+media[n].currentTime.toFixed(1):null), paused:N.map(n=>media[n]?media[n].paused:null), meta:metadataReady, dur:totalDuration});
        } catch(e) { return 'THROW '+e.message; }
      })()
    `,
    awaitPromise: true,
    returnByValue: true,
  });
  console.log("forte+play =>", r3.result?.result?.value ?? JSON.stringify(r3.result));

  console.log("errors", errs.length);
  errs.slice(0, 5).forEach(e => console.log(" ", String(e).slice(0, 250)));
  console.log("console", cons.length);
  cons.slice(0, 10).forEach(c => console.log(" ", c.slice(0, 250)));

  ws.close();
  chrome.kill();
  process.exit(errs.length > 0 ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
