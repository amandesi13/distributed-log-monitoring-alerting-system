"use strict";

// Loads the Python analyzer into Pyodide and renders what web/bridge.py returns.

const $ = (id) => document.getElementById(id);
const statusEl = $("status");
const logsEl = $("logs");
const alertsEl = $("alerts");
const lanesEl = $("lanes");
const parseErrorsEl = $("parse-errors");
const SVG_NS = "http://www.w3.org/2000/svg";
const RANK = { critical: 3, high: 2, medium: 1, low: 0 };

let bridge = null;
let seed = 7;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = "status" + (cls ? " " + cls : "");
}

async function boot() {
  await loadSample();
  try {
    const pyodide = await loadPyodide();
    const manifest = await (await fetch("py/manifest.json")).json();
    for (const path of manifest) {
      const source = await (await fetch("py/" + path)).text();
      const full = "/home/pyodide/" + path;
      const dir = full.split("/").slice(0, -1).join("/");
      pyodide.FS.mkdirTree(dir);
      pyodide.FS.writeFile(full, source);
    }
    bridge = pyodide.pyimport("bridge");
    setStatus("Python ready", "ready");
    $("analyze").disabled = false;
    $("simulate").disabled = false;
    analyze();
  } catch (err) {
    console.error(err);
    setStatus("Python failed to load", "failed");
    alertsEl.innerHTML = `<div class="error">${esc(err && err.message ? err.message : err)}</div>`;
  }
}

async function loadSample() {
  logsEl.value = await (await fetch("samples/service.log")).text();
}

function settings() {
  const f = $("settings").elements;
  return [Number(f.window.value), Number(f.errors.value), Number(f.latency.value)];
}

function analyze() {
  if (!bridge) return;
  const [win, errors, latency] = settings();
  const result = JSON.parse(bridge.analyze(logsEl.value, win, errors, latency));
  if (!result.ok) {
    alertsEl.innerHTML = `<div class="error">${esc(result.error)}</div>`;
    return;
  }
  renderAlerts(result);
  renderParseErrors(result.parse_errors);
  renderLanes(result);
}

function time(iso) {
  return iso.replace(/^.*T/, "").replace(/(\.\d+)?(\+00:00|Z)$/, "");
}

function renderAlerts(result) {
  const alerts = result.alerts.slice().sort((a, b) => RANK[b.severity] - RANK[a.severity]);
  if (!result.events.length) {
    alertsEl.innerHTML = '<p class="empty">No parseable events.</p>';
    return;
  }
  const counts = {};
  for (const a of alerts) counts[a.severity] = (counts[a.severity] || 0) + 1;
  const chips = ["critical", "high", "medium", "low"]
    .filter((s) => counts[s])
    .map((s) => `<span class="sev ${s}">${counts[s]} ${s}</span>`).join("");
  const services = new Set(result.events.map((e) => e.service)).size;
  const cards = alerts.map((a) => `
    <article class="finding ${a.severity}">
      <h3><span class="sev ${a.severity}">${a.severity}</span>${esc(a.title)}</h3>
      <p>${esc(a.detail)}</p>
      <p class="rec">${esc(a.hint)}</p>
      <p class="alert-meta">${a.evidence_count} event(s), ${time(a.first_seen)} to ${time(a.last_seen)} UTC</p>
    </article>`).join("");
  alertsEl.innerHTML = `
    <div class="chips">${chips || '<span class="sev ok">all quiet</span>'}
      <span class="empty">${result.events.length} events from ${services} services</span></div>
    ${cards || '<p class="empty">No alert thresholds were crossed.</p>'}`;
}

function renderParseErrors(errors) {
  if (!errors.length) {
    parseErrorsEl.innerHTML = "";
    return;
  }
  parseErrorsEl.innerHTML = `<details class="parse-errors" open>
    <summary>${errors.length} line(s) skipped</summary>
    <ul>${errors.map((e) => `<li>line ${e.line}: ${esc(e.error)}</li>`).join("")}</ul></details>`;
}

function el(name, attrs, text) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderLanes(result) {
  const events = result.events;
  lanesEl.innerHTML = "";
  if (!events.length) {
    lanesEl.innerHTML = '<p class="empty">No events yet.</p>';
    return;
  }
  const services = [...new Set(events.map((e) => e.service))].sort();
  const ts = events.map((e) => Date.parse(e.timestamp));
  const t0 = Math.min(...ts);
  const t1 = Math.max(...ts, t0 + 1000);
  const maxLatency = Math.max(result.config.latency_threshold_ms * 1.25,
    ...events.map((e) => e.latency_ms || 0));

  const W = 1100, labelW = 130, laneH = 70, gap = 10, top = 6, axisH = 22;
  const H = top + services.length * (laneH + gap) + axisH;
  const plotW = W - labelW - 10;
  const x = (t) => labelW + ((t - t0) / (t1 - t0)) * plotW;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Latency timeline per service with alert spans" });

  services.forEach((service, i) => {
    const y0 = top + i * (laneH + gap);
    const y = (ms) => y0 + laneH - 6 - (Math.min(ms, maxLatency) / maxLatency) * (laneH - 12);
    svg.append(el("rect", { class: "lane-bg", x: labelW, y: y0, width: plotW, height: laneH, rx: 6 }));
    svg.append(el("text", { class: "lane-label", x: 0, y: y0 + laneH / 2 + 4 }, service));

    for (const a of result.alerts.filter((al) => al.service === service)) {
      const xa = x(Date.parse(a.first_seen));
      const xb = x(Date.parse(a.last_seen));
      const span = el("rect", { class: "window " + a.severity, x: Math.min(xa, xb) - 3, y: y0,
        width: Math.max(Math.abs(xb - xa), 0) + 6, height: laneH });
      span.append(el("title", {}, a.title));
      svg.append(span);
    }

    const ty = y(result.config.latency_threshold_ms);
    svg.append(el("line", { class: "threshold", x1: labelW, x2: labelW + plotW, y1: ty, y2: ty }));

    for (const e of events.filter((ev) => ev.service === service)) {
      const cy = e.latency_ms == null ? y0 + laneH / 2 : y(e.latency_ms);
      const dot = el("circle", { class: "pt " + e.severity, cx: x(Date.parse(e.timestamp)), cy,
        r: e.severity === "info" || e.severity === "debug" ? 3 : 4.5 });
      const lat = e.latency_ms == null ? "" : ` · ${Math.round(e.latency_ms)} ms`;
      dot.append(el("title", {}, `${time(e.timestamp)} ${e.severity}${lat}\n${e.message}`));
      svg.append(dot);
    }
  });

  const axisY = H - 6;
  const ticks = 6;
  for (let k = 0; k <= ticks; k++) {
    const t = t0 + ((t1 - t0) * k) / ticks;
    const anchor = k === 0 ? "start" : k === ticks ? "end" : "middle";
    svg.append(el("text", { class: "axis", x: x(t), y: axisY, "text-anchor": anchor },
      new Date(t).toISOString().slice(11, 19)));
  }
  lanesEl.append(svg);
}

$("analyze").addEventListener("click", analyze);
$("load-sample").addEventListener("click", async () => { await loadSample(); analyze(); });
$("simulate").addEventListener("click", () => {
  if (!bridge) return;
  logsEl.value = bridge.simulate(120, seed++);
  analyze();
});
$("settings").addEventListener("input", analyze);
$("settings").addEventListener("submit", (ev) => { ev.preventDefault(); analyze(); });
logsEl.addEventListener("keydown", (ev) => {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") analyze();
});

boot();
