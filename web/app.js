"use strict";

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const el = {
  version: $("version"),
  sdLed: $("sdLed"), sdValue: $("sdValue"),
  padLed: $("padLed"), padValue: $("padValue"),
  sdSelect: $("sdSelect"), manualPath: $("manualPath"),
  artSource: $("artSource"), artUrl: $("artUrl"),
  backupSelect: $("backupSelect"),
  console: $("console"),
  busy: $("busy"), busyText: $("busyText"),
};

const MANUAL = "__manual__";

function humanSize(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(0) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}

/* ---------- console helpers ---------- */
function log(text, cls) {
  if (text == null || text === "") return;
  const span = document.createElement("span");
  if (cls) span.className = cls;
  span.textContent = text.endsWith("\n") ? text : text + "\n";
  el.console.appendChild(span);
  el.console.scrollTop = el.console.scrollHeight;
}

/* ---------- busy state ---------- */
function setBusy(on, text) {
  el.busyText.textContent = text || "Working…";
  el.busy.classList.toggle("hidden", !on);
  document.querySelectorAll("button, select, input").forEach((n) => { n.disabled = on; });
}

/* ---------- SD target ---------- */
function getRoot() {
  const v = el.sdSelect.value;
  if (v === MANUAL) return el.manualPath.value.trim();
  return v || "";
}

function syncManual() {
  const manual = el.sdSelect.value === MANUAL;
  el.manualPath.classList.toggle("hidden", !manual);
  if (manual) el.manualPath.focus();
}

/* ---------- refresh detected state ---------- */
async function refresh() {
  let data;
  try {
    data = await api().detect();
  } catch (e) {
    log("Could not query devices: " + e, "err");
    return;
  }

  // SD cards
  const cards = data.cards || [];
  const prev = getRoot();
  el.sdSelect.innerHTML = "";
  cards.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.path;
    const label = c.label ? ` [${c.label}]` : "";
    o.textContent = `${c.path}${label}  (${c.free_gb} GB free)${c.strong ? "  ★" : ""}`;
    el.sdSelect.appendChild(o);
  });
  const manualOpt = document.createElement("option");
  manualOpt.value = MANUAL;
  manualOpt.textContent = "Enter a path manually…";
  el.sdSelect.appendChild(manualOpt);

  const strong = cards.find((c) => c.strong);
  if (prev && [...el.sdSelect.options].some((o) => o.value === prev)) {
    el.sdSelect.value = prev;
  } else if (strong) {
    el.sdSelect.value = strong.path;
  } else if (cards.length) {
    el.sdSelect.value = cards[0].path;
  } else {
    el.sdSelect.value = MANUAL;
  }
  syncManual();

  // status LEDs
  if (strong) {
    el.sdLed.className = "led on";
    el.sdValue.textContent = `${strong.path}${strong.label ? " [" + strong.label + "]" : ""}`;
  } else if (cards.length) {
    el.sdLed.className = "led off";
    el.sdValue.textContent = `${cards.length} drive(s) - pick the right one`;
  } else {
    el.sdLed.className = "led off";
    el.sdValue.textContent = "not detected (enter a path)";
  }

  const n = data.controllers || 0;
  el.padLed.className = n > 0 ? "led on" : "led off";
  el.padValue.textContent = n === 0 ? "none connected" : `${n} connected`;

  await refreshBackups();
}

async function refreshBackups() {
  let list = [];
  try { list = await api().list_backups(); } catch (e) { /* ignore */ }
  el.backupSelect.innerHTML = "";
  if (!list.length) {
    const o = document.createElement("option");
    o.value = ""; o.textContent = "No backups found";
    el.backupSelect.appendChild(o);
    return;
  }
  list.forEach((b) => {
    const o = document.createElement("option");
    o.value = b.name;
    const empty = b.bytes < 2048 ? "  - empty" : "";
    o.textContent = `${b.name}  (${humanSize(b.bytes)})${empty}`;
    el.backupSelect.appendChild(o);
  });
}

/* ---------- run an action ---------- */
async function run(busyText, fn) {
  setBusy(true, busyText);
  log("\n> " + busyText, "sys");
  try {
    const res = await fn();
    if (res && typeof res === "object") {
      log(res.log, res.ok ? null : "err");
      if (!res.ok && res.error) log("Failed: " + res.error, "err");
      else log("Done.", "ok");
    }
  } catch (e) {
    log("Unexpected error: " + e, "err");
  } finally {
    setBusy(false);
    await refresh();
  }
}

function needRoot() {
  const root = getRoot();
  if (!root) {
    log("Select or enter your SD card path first.", "err");
    return null;
  }
  return root;
}

/* ---------- wire up ---------- */
const handlers = {
  auto() { const r = needRoot(); if (r) run("Auto - doing everything", () => api().auto(r)); },
  backup() { const r = needRoot(); if (r) run("Backing up SD card", () => api().backup(r)); },
  firmware() { const r = needRoot(); if (r) run("Updating console firmware", () => api().update_firmware(r)); },
  art() {
    const r = needRoot(); if (!r) return;
    const source = el.artSource.value === "url" ? el.artUrl.value.trim() : null;
    if (el.artSource.value === "url" && !source) { log("Enter the art pack URL.", "err"); return; }
    run("Installing cartridge art", () => api().install_art(r, source));
  },
  controllers() { run("Updating controllers", () => api().update_controllers()); },
  restore() {
    const r = needRoot(); if (!r) return;
    const name = el.backupSelect.value;
    if (!name) { log("No backup selected.", "err"); return; }
    run("Restoring " + name, () => api().restore(r, name));
  },
};

function init() {
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => handlers[btn.dataset.action]());
  });
  $("refreshBtn").addEventListener("click", refresh);
  $("clearBtn").addEventListener("click", () => { el.console.innerHTML = ""; });
  el.sdSelect.addEventListener("change", syncManual);
  el.artSource.addEventListener("change", () => {
    el.artUrl.classList.toggle("hidden", el.artSource.value !== "url");
  });

  api().version().then((v) => { el.version.textContent = "v" + v; }).catch(() => {});
  log("Analogue 3D Studio ready.", "sys");
  refresh();
}

if (window.pywebview && window.pywebview.api) {
  init();
} else {
  window.addEventListener("pywebviewready", init);
}
