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
  memContent: $("memContent"),
  memRestore: $("memRestore"),
  memBackupSelect: $("memBackupSelect"),
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
  await refreshMemories();
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

/* ---------- save states (Memories) ---------- */
async function refreshMemories() {
  const root = getRoot();
  if (!root) {
    el.memContent.innerHTML = '<p class="muted pad">Select a card to see its save states.</p>';
    el.memRestore.classList.add("hidden");
    return;
  }
  let m;
  try { m = await api().list_memories(root); }
  catch (e) { el.memContent.innerHTML = '<p class="muted pad">Could not read save states.</p>'; return; }
  renderMemories(m, root);
  await refreshMemBackups();
}

function renderMemories(m, root) {
  el.memContent.innerHTML = "";
  if (!m.available) {
    el.memContent.innerHTML = '<p class="muted pad">No save states on this card.</p>';
    return;
  }
  const limit = m.limit || 20;
  m.games.forEach((g) => {
    const overCap = g.count >= limit;
    const game = document.createElement("div");
    game.className = "game";
    game.innerHTML = `
      <div class="game-head">
        <span class="game-title"></span>
        <span class="game-id"></span>
        <span class="game-meta">${g.count} state${g.count === 1 ? "" : "s"} &middot; ${humanSize(g.total_bytes)}${overCap ? ' &middot; <span class="cap-warn">at the ' + limit + ' cap</span>' : ""}</span>
        <span class="game-actions">
          <label>keep latest</label>
          <input type="number" class="keep-input" min="0" value="${limit}" />
          <button class="action" data-mem-action="trim">Trim &amp; archive</button>
        </span>
      </div>
      <div class="thumbs"></div>`;
    game.querySelector(".game-title").textContent = g.title;
    game.querySelector(".game-id").textContent = "[" + g.cart_id + "]";
    game.querySelector("[data-mem-action='trim']").dataset.folder = g.folder;
    const thumbs = game.querySelector(".thumbs");
    g.states.forEach((s, i) => {
      const t = document.createElement("div");
      t.className = "thumb" + (i === 0 ? " newest" : "");
      const img = document.createElement("img");
      img.alt = s.when;
      img.dataset.folder = g.folder;
      img.dataset.name = s.name;
      const cap = document.createElement("div");
      cap.className = "cap";
      cap.textContent = s.when;
      t.appendChild(img);
      t.appendChild(cap);
      thumbs.appendChild(t);
    });
    el.memContent.appendChild(game);
  });
  lazyThumbs(root);
}

async function lazyThumbs(root) {
  const imgs = [...el.memContent.querySelectorAll("img[data-name]")];
  for (const img of imgs) {
    try {
      const url = await api().memory_thumbnail(root, img.dataset.folder, img.dataset.name);
      if (url) img.src = url;
    } catch (e) { /* skip a bad thumbnail */ }
  }
}

async function refreshMemBackups() {
  let list = [];
  try { list = await api().list_memory_backups(); } catch (e) {}
  if (!list.length) { el.memRestore.classList.add("hidden"); return; }
  el.memRestore.classList.remove("hidden");
  el.memBackupSelect.innerHTML = "";
  list.forEach((b) => {
    const o = document.createElement("option");
    o.value = b.cart_id + "|" + b.name;
    o.textContent = `[${b.cart_id}] ${b.name}  (${humanSize(b.bytes)})`;
    el.memBackupSelect.appendChild(o);
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
  backupMem() { const r = needRoot(); if (r) run("Backing up save states", () => api().backup_memories(r)); },
  restoreMem() {
    const r = needRoot(); if (!r) return;
    const v = el.memBackupSelect.value;
    if (!v) { log("No archived save state selected.", "err"); return; }
    const sep = v.indexOf("|");
    const cart = v.slice(0, sep), name = v.slice(sep + 1);
    run("Restoring save state", () => api().restore_memory(r, cart, name));
  },
};

function init() {
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => handlers[btn.dataset.action]());
  });
  $("refreshBtn").addEventListener("click", refresh);
  $("clearBtn").addEventListener("click", () => { el.console.innerHTML = ""; });
  $("memRefresh").addEventListener("click", refreshMemories);
  el.memContent.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-mem-action='trim']");
    if (!btn) return;
    const folder = btn.dataset.folder;
    const input = btn.parentElement.querySelector(".keep-input");
    const keep = parseInt(input.value, 10);
    if (isNaN(keep) || keep < 0) { log("Enter a valid 'keep latest' number.", "err"); return; }
    const r = getRoot();
    if (!r) { log("Select a card first.", "err"); return; }
    if (!confirm(`Trim this game to its newest ${keep} save state(s)?\nThe rest are archived locally first, then removed from the card.`)) return;
    run(`Trimming to newest ${keep}`, () => api().trim_memory(r, folder, keep));
  });
  el.sdSelect.addEventListener("change", () => { syncManual(); refresh(); });
  el.manualPath.addEventListener("change", refresh);
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
