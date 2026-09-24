// Mode test: BASE default (grid/tracks/master/footer hidden), switch to FULL shows all, back to BASE.
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const http = require("http");

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const URL = "file:///C:/Users/Jhonatan/Desktop/PREACH_FLOW_V09.html";
const PORT = 9341;
const USER_DIR = path.join(os.tmpdir(), "pf_mode_" + Date.now());
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJSON = url => new Promise((res, rej) => {
  http.get(url, r => { let d = ""; r.on("data", c => d += c); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } }); }).on("error", rej);
});

(async () => {
  const chrome = spawn(CHROME, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
    "--autoplay-policy=no-user-gesture-required",
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${USER_DIR}`,
    "--window-size=1280,900", "about:blank",
  ], { stdio: ["ignore", "pipe", "pipe"] });

  let targets = null;
  for (let i = 0; i < 30; i++) { await sleep(500); try { targets = await getJSON(`http://127.0.0.1:${PORT}/json/list`); break; } catch (e) {} }
  if (!targets) { console.log("FAIL: no devtools"); chrome.kill(); process.exit(1); }
  const page = targets.find(t => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let msgId = 0; const pending = new Map(); const errs = [];
  ws.addEventListener("message", ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
    else if (m.method === "Runtime.exceptionThrown") {
      const d = m.params.exceptionDetails;
      errs.push((d.exception && (d.exception.description || d.exception.value)) || d.text);
    }
  });
  const send = (method, params = {}) => new Promise(res => { const id = ++msgId; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); });
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  await send("Runtime.enable"); await send("Page.enable");

  await send("Page.navigate", { url: URL });
  for (let i = 0; i < 60; i++) {
    await sleep(1000);
    const r = await send("Runtime.evaluate", { expression: "document.readyState", returnByValue: true });
    const st = r.result && r.result.result && r.result.result.value;
    if (st === "complete" || st === "interactive") break;
  }
  await sleep(2500);

  const vis = expr => send("Runtime.evaluate", { expression: expr, returnByValue: true }).then(r => r.result && r.result.result ? r.result.result.value : JSON.stringify(r.result));

  const checks = {};
  checks.bodyClass = await vis("document.body.className");
  checks.base_grid_hidden = await vis("getComputedStyle(document.querySelector('.grid-card')).display === 'none'");
  checks.base_tracks_hidden = await vis("getComputedStyle(document.querySelector('.tracks-card')).display === 'none'");
  checks.base_master_hidden = await vis("getComputedStyle(document.querySelector('.master-card')).display === 'none'");
  checks.base_footer_hidden = await vis("getComputedStyle(document.querySelector('.footer')).display === 'none'");
  checks.base_transport_visible = await vis("getComputedStyle(document.querySelector('.transport-panel')).display !== 'none'");
  checks.base_timeline_visible = await vis("getComputedStyle(document.querySelector('.timeline-card')).display !== 'none'");
  checks.base_expr_visible = await vis("getComputedStyle(document.querySelector('.expression-card')).display !== 'none'");
  checks.base_fala_visible = await vis("getComputedStyle(document.querySelector('.action-card:not(.master-card)')).display !== 'none'");
  checks.modeBtns = await vis("document.querySelectorAll('.mode-opt').length");
  checks.base_btn_active = await vis("document.querySelector('.mode-opt[data-mode=base]').classList.contains('active')");
  // merged block check: no margin between transport/timeline/expr
  checks.stack_margins = await vis("JSON.stringify(['.transport-panel','.timeline-card','.expression-card'].map(s=>getComputedStyle(document.querySelector(s)).marginTop))");

  await send("Page.captureScreenshot", { format: "png" }).then(s => { if (s.result && s.result.data) fs.writeFileSync(path.join(__dirname, "shot_base_1790285010.png"), Buffer.from(s.result.data, "base64")); });

  // switch to FULL
  await vis("document.querySelector('.mode-opt[data-mode=full]').click(); 'ok'");
  await sleep(400);
  checks.full_bodyClass = await vis("document.body.className");
  checks.full_grid_visible = await vis("getComputedStyle(document.querySelector('.grid-card')).display !== 'none'");
  checks.full_tracks_visible = await vis("getComputedStyle(document.querySelector('.tracks-card')).display !== 'none'");
  checks.full_master_visible = await vis("getComputedStyle(document.querySelector('.master-card')).display !== 'none'");
  checks.full_footer_visible = await vis("getComputedStyle(document.querySelector('.footer')).display !== 'none'");
  checks.full_btn_active = await vis("document.querySelector('.mode-opt[data-mode=full]').classList.contains('active')");
  await send("Page.captureScreenshot", { format: "png" }).then(s => { if (s.result && s.result.data) fs.writeFileSync(path.join(__dirname, "shot_full_1790285010.png"), Buffer.from(s.result.data, "base64")); });

  // interactions in FULL: play + duck
  await vis("document.getElementById('play').click(); 'ok'");
  await sleep(2500);
  checks.play_started = await vis("typeof started!=='undefined' && started");
  await vis("document.getElementById('duckBtn').click(); 'ok'");
  await sleep(300);
  checks.duck_active = await vis("document.getElementById('duckBtn').classList.contains('active')");
  await vis("document.getElementById('duckBtn').click(); 'ok'");

  // back to BASE
  await vis("document.querySelector('.mode-opt[data-mode=base]').click(); 'ok'");
  await sleep(400);
  checks.back_bodyClass = await vis("document.body.className");
  checks.back_grid_hidden = await vis("getComputedStyle(document.querySelector('.grid-card')).display === 'none'");
  checks.back_still_playing = await vis("typeof started!=='undefined' && started");
  checks.back_master_hidden = await vis("getComputedStyle(document.querySelector('.master-card')).display === 'none'");

  console.log(JSON.stringify(checks, null, 1));
  console.log("PAGE_ERRORS", errs.length);
  errs.slice(0, 8).forEach(e => console.log("  ", String(e).slice(0, 250)));

  const bad = Object.entries(checks).filter(([k, v]) => {
    if (k.endsWith("_hidden") || k.startsWith("base_") && k.endsWith("_hidden")) return v !== true;
    return false;
  });
  let fail = errs.length > 0;
  const expectTrue = ["modeBtns>0", "base_grid_hidden", "base_tracks_hidden", "base_master_hidden", "base_footer_hidden", "base_transport_visible", "base_timeline_visible", "base_expr_visible", "base_fala_visible", "base_btn_active", "full_grid_visible", "full_tracks_visible", "full_master_visible", "full_footer_visible", "full_btn_active", "play_started", "duck_active", "back_grid_hidden", "back_still_playing", "back_master_hidden"];
  for (const k of expectTrue) {
    const v = checks[k];
    const ok = (k === "modeBtns>0") ? checks.modeBtns === 2 : v === true;
    if (!ok) { console.log("CHECK_FAIL", k, "=", v); fail = true; }
  }
  if (checks.bodyClass !== "mode-base") { console.log("CHECK_FAIL default mode =", checks.bodyClass); fail = true; }
  if (checks.full_bodyClass !== "mode-full") { console.log("CHECK_FAIL full mode =", checks.full_bodyClass); fail = true; }
  if (checks.back_bodyClass !== "mode-base") { console.log("CHECK_FAIL back mode =", checks.back_bodyClass); fail = true; }

  ws.close(); chrome.kill();
  console.log(fail ? "RESULT: FAIL" : "RESULT: PASS");
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error("FATAL", e); process.exit(1); });
