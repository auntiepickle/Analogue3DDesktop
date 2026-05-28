"use strict";

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const el = {
  version: $("version"),
  sdLed: $("sdLed"), sdValue: $("sdValue"),
  padLed: $("padLed"), padValue: $("padValue"),
  sdSelect: $("sdSelect"), manualPath: $("manualPath"),
  artSource: $("artSource"), artUrl: $("artUrl"),
  artGallery: $("artGallery"),
  backupSelect: $("backupSelect"),
  consoleVer: $("consoleVer"), ctrlVer: $("ctrlVer"),
  ctrlVersionSelect: $("ctrlVersionSelect"),
  backupRoot: $("backupRoot"),
  memContent: $("memContent"),
  memRestore: $("memRestore"),
  memSnapshotSelect: $("memSnapshotSelect"),
  memArchiveGame: $("memArchiveGame"),
  console: $("console"),
  busy: $("busy"), busyText: $("busyText"), busySpin: $("busySpin"),
  busySteps: $("busySteps"),
  busyProg: $("busyProg"), busyBar: $("busyBar"), busyProgLabel: $("busyProgLabel"),
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

/* ---------- busy state + live progress ---------- */
let consoleUpToDate = false;
let controllerCount = 0;
let busyNow = false;
let lastCardSig = null;
let flashTarget = null;

function applyGating() {
  const fw = document.querySelector("[data-action='firmware']");
  if (fw) fw.disabled = consoleUpToDate;
}

function setBusy(on, text) {
  busyNow = on;
  el.busyText.textContent = text || "Working…";
  el.busy.classList.toggle("hidden", !on);
  if (on) {
    el.busyProg.classList.add("hidden");
    el.busyProgLabel.classList.add("hidden");
    el.busySpin.classList.remove("hidden");
    el.busyBar.style.width = "0%";
    el.busySteps.classList.add("hidden");
    el.busySteps.innerHTML = "";
    flashTarget = null;
  }
  document.querySelectorAll("button, select, input").forEach((n) => { n.disabled = on; });
  if (!on) applyGating();
}

window.studioProgress = function (pct, block, nblocks) {
  el.busyProg.classList.remove("hidden");
  el.busyProgLabel.classList.remove("hidden");
  el.busySpin.classList.add("hidden");
  el.busyBar.style.width = pct + "%";
  const prefix = flashTarget && flashTarget.total > 1
    ? `controller ${flashTarget.idx}/${flashTarget.total}  ·  ` : "";
  el.busyProgLabel.textContent = `${prefix}${pct}%  (block ${block}/${nblocks})`;
};

window.studioFlashTarget = function (idx, total) {
  flashTarget = { idx: idx, total: total };
};

window.studioSteps = function (labels) {
  el.busySteps.innerHTML = "";
  labels.forEach((label) => {
    const li = document.createElement("li");
    const mark = document.createElement("span");
    mark.className = "mark";
    mark.textContent = "○";
    const txt = document.createElement("span");
    txt.textContent = label;
    li.appendChild(mark);
    li.appendChild(txt);
    el.busySteps.appendChild(li);
  });
  el.busySteps.classList.remove("hidden");
};

window.studioStepStatus = function (i, status) {
  const li = el.busySteps.children[i];
  if (!li) return;
  const marks = { active: "▸", done: "✓", skip: "–", fail: "✗", pending: "○" };
  li.className = status;
  const mark = li.querySelector(".mark");
  if (mark) mark.textContent = marks[status] || "○";
  // when a flash step starts, reset the bar; when it ends, hide it
  if (status !== "active") {
    el.busyProg.classList.add("hidden");
    el.busyProgLabel.classList.add("hidden");
  }
};

window.studioStepNote = function (i, note) {
  const li = el.busySteps.children[i];
  if (!li) return;
  let n = li.querySelector(".note");
  if (!n) { n = document.createElement("span"); n.className = "note"; li.appendChild(n); }
  n.textContent = note ? "  - " + note : "";
};

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
  lastCardSig = cards.map((c) => c.path).join(",");
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
  controllerCount = n;
  el.padLed.className = n > 0 ? "led on" : "led off";
  el.padValue.textContent = n === 0 ? "none connected" : `${n} connected`;

  await refreshBackups();
  await refreshMemories();
  await refreshArt();
}

/* Lightweight background poll: keep the status strip (controllers / SD) live
   without rebuilding the whole UI. A full refresh only runs if the set of cards
   actually changed (memories/art depend on the card). Skipped while busy. */
async function pollStatus() {
  if (busyNow) return;
  let data;
  try { data = await api().detect(); } catch (e) { return; }

  const n = data.controllers || 0;
  controllerCount = n;
  el.padLed.className = n > 0 ? "led on" : "led off";
  el.padValue.textContent = n === 0 ? "none connected" : `${n} connected`;

  const cardSig = (data.cards || []).map((c) => c.path).join(",");
  if (lastCardSig !== null && cardSig !== lastCardSig) {
    await refresh();
  }
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
  await refreshSnapshots();
}

let memGames = [];
let memLimit = 20;
let memPage = 0;
const MEM_PAGE_SIZE = 8;

function renderMemories(m, root) {
  memGames = m.available ? m.games : [];
  memLimit = m.limit || 20;
  if (!memGames.length) {
    el.memContent.innerHTML = '<p class="muted pad">No save states on this card.</p>';
    $("memControls").classList.add("hidden");
    return;
  }
  $("memControls").classList.remove("hidden");
  renderMemPage(root);
}

function filteredMemGames() {
  const q = $("memSearch").value.trim().toLowerCase();
  if (!q) return memGames;
  return memGames.filter((g) => g.title.toLowerCase().includes(q) || g.cart_id.includes(q));
}

function renderMemPage(root) {
  const games = filteredMemGames();
  const pages = Math.max(1, Math.ceil(games.length / MEM_PAGE_SIZE));
  memPage = Math.min(Math.max(memPage, 0), pages - 1);
  const start = memPage * MEM_PAGE_SIZE;
  const slice = games.slice(start, start + MEM_PAGE_SIZE);
  const autoExpand = slice.length === 1;
  el.memContent.innerHTML = "";
  slice.forEach((g) => el.memContent.appendChild(buildGameRow(g, root, autoExpand)));
  $("memPageInfo").textContent =
    `${games.length} game${games.length === 1 ? "" : "s"}  ·  page ${memPage + 1}/${pages}`;
  $("memPrev").disabled = memPage <= 0;
  $("memNext").disabled = memPage >= pages - 1;
  loadCovers(root);  // one small cover per visible game; full strips load on expand
}

function buildGameRow(g, root, autoExpand) {
  const overCap = g.count >= memLimit;
  const game = document.createElement("div");
  game.className = "game" + (autoExpand ? " expanded" : "");
  game.innerHTML = `
    <div class="game-head">
      <span class="chev">&#9656;</span>
      <img class="cover" alt="" />
      <span class="game-title"></span>
      <span class="game-id"></span>
      <span class="game-meta">${g.count} state${g.count === 1 ? "" : "s"} &middot; ${humanSize(g.total_bytes)}${overCap ? ' &middot; <span class="cap-warn">at the ' + memLimit + ' cap</span>' : ""}</span>
      <span class="game-actions">
        <label>keep latest</label>
        <input type="number" class="keep-input" min="0" value="${memLimit}" />
        <button class="action" data-mem-action="trim">Trim &amp; archive</button>
      </span>
    </div>
    <div class="thumbs"></div>`;
  game.querySelector(".game-title").textContent = g.title;
  game.querySelector(".game-id").textContent = "[" + g.cart_id + "]";
  game.querySelector("[data-mem-action='trim']").dataset.folder = g.folder;
  const cover = game.querySelector(".cover");
  if (g.states.length) {
    cover.dataset.folder = g.folder;
    cover.dataset.name = g.states[0].name;
  }
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
    const del = document.createElement("button");
    del.className = "del";
    del.title = "Delete this save state";
    del.textContent = "×";
    del.dataset.memAction = "del";
    del.dataset.folder = g.folder;
    del.dataset.name = s.name;
    t.appendChild(img);
    t.appendChild(cap);
    t.appendChild(del);
    if (i === 0) {
      const tag = document.createElement("span");
      tag.className = "newest-tag";
      tag.textContent = "newest";
      t.appendChild(tag);
    }
    thumbs.appendChild(t);
  });
  if (autoExpand) loadGameThumbs(game, root);
  return game;
}

async function _loadThumbs(imgs, root) {
  for (const img of imgs) {
    if (img.dataset.loaded) continue;
    try {
      const url = await api().memory_thumbnail(root, img.dataset.folder, img.dataset.name);
      if (url) { img.src = url; img.dataset.loaded = "1"; }
    } catch (e) { /* skip a bad thumbnail */ }
  }
}

function loadCovers(root) {
  return _loadThumbs([...el.memContent.querySelectorAll("img.cover[data-name]")], root);
}

function loadGameThumbs(game, root) {
  return _loadThumbs([...game.querySelectorAll(".thumbs img[data-name]")], root);
}

let snapshots = [];

async function refreshSnapshots() {
  try { snapshots = await api().list_snapshots(); } catch (e) { snapshots = []; }
  if (!snapshots.length) { el.memRestore.classList.add("hidden"); return; }
  el.memRestore.classList.remove("hidden");
  const prev = el.memSnapshotSelect.value;
  el.memSnapshotSelect.innerHTML = "";
  snapshots.forEach((s) => {
    const o = document.createElement("option");
    o.value = s.name;
    o.textContent = `${s.when}  -  ${s.count} states, ${humanSize(s.bytes)}`;
    el.memSnapshotSelect.appendChild(o);
  });
  if (prev && [...el.memSnapshotSelect.options].some((o) => o.value === prev)) {
    el.memSnapshotSelect.value = prev;
  }
  fillSnapshotGames();
}

function fillSnapshotGames() {
  const s = snapshots.find((x) => x.name === el.memSnapshotSelect.value) || snapshots[0];
  el.memArchiveGame.innerHTML = "";
  if (!s) return;
  s.games.forEach((g) => {
    const o = document.createElement("option");
    o.value = g.cart_id;
    o.textContent = `${g.title} (${g.count})`;
    el.memArchiveGame.appendChild(o);
  });
}

/* ---------- firmware versions ---------- */
function verLine(cur, latest, update, emptyText) {
  if (!cur && !latest) return `<span class="muted">${emptyText}</span>`;
  let html = `<span class="cur">${cur || "unknown"}</span>`;
  if (latest) {
    if (update) html += ` <span class="arrow">&rarr;</span> <span class="latest">${latest}</span> <span class="badge upd">update available</span>`;
    else html += ` <span class="badge ok">up to date</span>`;
  }
  return html;
}

async function refreshVersions() {
  const root = getRoot();
  el.consoleVer.innerHTML = '<span class="muted">checking&hellip;</span>';
  el.ctrlVer.innerHTML = '<span class="muted">checking&hellip;</span>';
  let v;
  try { v = await api().versions(root); }
  catch (e) {
    el.consoleVer.innerHTML = '<span class="muted">check failed</span>';
    el.ctrlVer.innerHTML = '<span class="muted">check failed</span>';
    return;
  }
  el.consoleVer.innerHTML = verLine(v.console_current, v.console_latest, v.console_update, "no firmware on card");
  el.ctrlVer.innerHTML = v.controllers
    ? verLine(v.ctrl_current, v.ctrl_latest, v.ctrl_update, "unknown")
    : '<span class="muted">no controller connected</span>';
  consoleUpToDate = !!(v.console_current && v.console_latest && !v.console_update);
  applyGating();
  await populateCtrlVersions();
}

async function populateCtrlVersions() {
  let cv;
  try { cv = await api().controller_versions(); } catch (e) { return; }
  if (!cv.ok) return;
  const sel = el.ctrlVersionSelect;
  const prev = sel.value;
  sel.innerHTML = '<option value="">latest</option>';
  cv.versions.forEach((v) => {
    const o = document.createElement("option");
    o.value = String(v.version_int);
    o.textContent = v.label;
    sel.appendChild(o);
  });
  if (prev) sel.value = prev;
}

/* ---------- cartridge art ---------- */
let artGames = [];
let artPage = 0;
const ART_PAGE_SIZE = 18;

async function refreshArt() {
  const root = getRoot();
  const hideControls = () => $("artControls").classList.add("hidden");
  if (!root) {
    el.artGallery.innerHTML = '<p class="muted pad">Select a card to see its cartridge art.</p>';
    hideControls(); return;
  }
  let data;
  try { data = await api().cart_art_games(root); }
  catch (e) { el.artGallery.innerHTML = '<p class="muted pad">Could not read cartridge art.</p>'; hideControls(); return; }
  if (!data.db_present) {
    el.artGallery.innerHTML = '<p class="muted pad">No art pack installed yet - use "Install art pack" above.</p>';
    hideControls(); return;
  }
  artGames = data.games || [];
  if (!artGames.length) {
    el.artGallery.innerHTML = '<p class="muted pad">No recognizable games on this card yet.</p>';
    hideControls(); return;
  }
  $("artControls").classList.remove("hidden");
  renderArtPage(root);
}

function filteredArtGames() {
  const q = $("artSearch").value.trim().toLowerCase();
  if (!q) return artGames;
  return artGames.filter((g) => g.title.toLowerCase().includes(q) || g.cart_id.includes(q));
}

function renderArtPage(root) {
  const games = filteredArtGames();
  const pages = Math.max(1, Math.ceil(games.length / ART_PAGE_SIZE));
  artPage = Math.min(Math.max(artPage, 0), pages - 1);
  const start = artPage * ART_PAGE_SIZE;
  el.artGallery.innerHTML = "";
  games.slice(start, start + ART_PAGE_SIZE).forEach((g) => el.artGallery.appendChild(buildArtTile(g)));
  $("artPageInfo").textContent =
    `${games.length} game${games.length === 1 ? "" : "s"}  ·  page ${artPage + 1}/${pages}`;
  $("artPrev").disabled = artPage <= 0;
  $("artNext").disabled = artPage >= pages - 1;
  lazyArt(root);
}

function buildArtTile(g) {
  const tile = document.createElement("div");
  tile.className = "art-tile";
  const img = document.createElement("img");
  img.className = "art-img";
  img.alt = g.title;
  img.dataset.cart = g.cart_id;
  const cap = document.createElement("div");
  cap.className = "art-cap";
  cap.textContent = g.title;
  const id = document.createElement("div");
  id.className = "art-id";
  id.textContent = g.cart_id;
  const setb = document.createElement("button");
  setb.className = "action sm setart";
  setb.textContent = "Set art";
  setb.dataset.artAction = "set";
  setb.dataset.cart = g.cart_id;
  tile.appendChild(img);
  tile.appendChild(cap);
  tile.appendChild(id);
  tile.appendChild(setb);
  return tile;
}

async function lazyArt(root) {
  const imgs = [...el.artGallery.querySelectorAll("img[data-cart]")];
  for (const img of imgs) {
    try {
      const url = await api().cart_art(root, img.dataset.cart);
      if (url) {
        img.src = url;
      } else {
        const ph = document.createElement("div");
        ph.className = "noart";
        ph.textContent = "no art";
        img.replaceWith(ph);
      }
    } catch (e) { /* skip */ }
  }
}

/* ---------- settings ---------- */
async function refreshSettings() {
  try {
    const s = await api().settings();
    el.backupRoot.value = s.backup_root + (s.is_custom ? "" : "   (default)");
  } catch (e) { /* ignore */ }
}

/* ---------- styled confirm modal ---------- */
function confirmDialog(message, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    const modal = $("modal"), ok = $("modalOk"), cancel = $("modalCancel");
    $("modalMsg").textContent = message;
    $("modalTitle").textContent = opts.title || "Please confirm";
    ok.textContent = opts.okText || "Confirm";
    ok.classList.toggle("danger", !!opts.danger);
    modal.classList.remove("hidden");
    ok.focus();
    const close = (val) => {
      modal.classList.add("hidden");
      ok.removeEventListener("click", onOk);
      cancel.removeEventListener("click", onCancel);
      document.removeEventListener("keydown", onKey);
      resolve(val);
    };
    const onOk = () => close(true);
    const onCancel = () => close(false);
    const onKey = (e) => {
      if (e.key === "Escape") close(false);
      else if (e.key === "Enter") close(true);
    };
    ok.addEventListener("click", onOk);
    cancel.addEventListener("click", onCancel);
    document.addEventListener("keydown", onKey);
  });
}

/* ---------- run an action ---------- */
async function run(busyText, fn, refreshVer) {
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
    if (refreshVer) await refreshVersions();
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
  auto() { const r = needRoot(); if (r) run("Auto - doing everything", () => api().auto(r), true); },
  backup() { const r = needRoot(); if (r) run("Backing up SD card", () => api().backup(r)); },
  firmware() { const r = needRoot(); if (r) run("Updating console firmware", () => api().update_firmware(r), true); },
  art() {
    const r = needRoot(); if (!r) return;
    const source = el.artSource.value === "url" ? el.artUrl.value.trim() : null;
    if (el.artSource.value === "url" && !source) { log("Enter the art pack URL.", "err"); return; }
    run("Installing cartridge art", () => api().install_art(r, source));
  },
  async flashCtrl() {
    const noun = controllerCount === 1 ? "controller" : "controllers";
    const vi = el.ctrlVersionSelect.value;
    if (!vi) { run(`Updating ${noun} to latest`, () => api().update_controllers(), true); return; }
    const label = el.ctrlVersionSelect.selectedOptions[0].textContent;
    const which = controllerCount === 1 ? "the connected controller" : `all ${controllerCount} connected controllers`;
    if (!(await confirmDialog(`Flash ${which} to ${label}?\nDowngrades are allowed.`, { okText: "Flash" }))) return;
    run(`Flashing ${noun} to ${label}`, () => api().flash_controllers(parseInt(vi, 10)), true);
  },
  restore() {
    const r = needRoot(); if (!r) return;
    const name = el.backupSelect.value;
    if (!name) { log("No backup selected.", "err"); return; }
    run("Restoring " + name, () => api().restore(r, name));
  },
  async deleteBackup() {
    const name = el.backupSelect.value;
    if (!name) { log("No backup selected.", "err"); return; }
    if (!(await confirmDialog(`Delete backup ${name}?\nThis can't be undone.`, { danger: true, okText: "Delete" }))) return;
    run("Deleting " + name, () => api().delete_backup(name));
  },
  async cleanBackups() {
    if (!(await confirmDialog("Delete all SD backups except the most recent?\nThis can't be undone.", { danger: true, okText: "Delete" }))) return;
    run("Cleaning old backups", () => api().clean_old_backups());
  },
  archiveMem() {
    const r = needRoot();
    if (r) run("Archiving all save states", () => api().archive_memories(r));
  },
  async restoreAll() {
    const r = needRoot(); if (!r) return;
    const name = el.memSnapshotSelect.value;
    if (!name) { log("No snapshot selected.", "err"); return; }
    if (!(await confirmDialog("Restore ALL save states from this snapshot onto the card?\nFiles with the same name are overwritten.", { okText: "Restore all" }))) return;
    run("Restoring whole snapshot", () => api().restore_memories(r, name));
  },
  async restoreGame() {
    const r = needRoot(); if (!r) return;
    const name = el.memSnapshotSelect.value;
    const cart = el.memArchiveGame.value;
    if (!name || !cart) { log("Pick a snapshot and a game.", "err"); return; }
    const game = el.memArchiveGame.selectedOptions[0] ? el.memArchiveGame.selectedOptions[0].textContent : cart;
    if (!(await confirmDialog(`Restore ${game} from this snapshot onto the card?`, { okText: "Restore game" }))) return;
    run("Restoring one game", () => api().restore_memories_game(r, name, cart));
  },
  async deleteSnapshot() {
    const name = el.memSnapshotSelect.value;
    if (!name) { log("No snapshot selected.", "err"); return; }
    if (!(await confirmDialog(`Delete snapshot ${name}?\nThis can't be undone.`, { danger: true, okText: "Delete" }))) return;
    run("Deleting snapshot", () => api().delete_snapshot(name));
  },
  async cleanSnapshots() {
    if (!(await confirmDialog("Delete all snapshots except the most recent?\nThis can't be undone.", { danger: true, okText: "Delete" }))) return;
    run("Cleaning old snapshots", () => api().clean_old_snapshots());
  },
  async changeBackupLoc() {
    await run("Setting backup location", () => api().set_backup_location());
    refreshSettings();
  },
  async resetBackupLoc() {
    if (!(await confirmDialog("Reset the backup location to the default?\nExisting backups in the current location won't be moved.", { okText: "Reset" }))) return;
    await run("Resetting backup location", () => api().reset_backup_location());
    refreshSettings();
  },
};

function init() {
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => handlers[btn.dataset.action]());
  });
  $("refreshBtn").addEventListener("click", refresh);
  $("clearBtn").addEventListener("click", () => { el.console.innerHTML = ""; });
  $("memRefresh").addEventListener("click", refreshMemories);
  $("checkUpdates").addEventListener("click", refreshVersions);
  el.memSnapshotSelect.addEventListener("change", fillSnapshotGames);
  $("memSearch").addEventListener("input", () => { memPage = 0; renderMemPage(getRoot()); });
  $("memPrev").addEventListener("click", () => { memPage--; renderMemPage(getRoot()); });
  $("memNext").addEventListener("click", () => { memPage++; renderMemPage(getRoot()); });
  $("artSearch").addEventListener("input", () => { artPage = 0; renderArtPage(getRoot()); });
  $("artPrev").addEventListener("click", () => { artPage--; renderArtPage(getRoot()); });
  $("artNext").addEventListener("click", () => { artPage++; renderArtPage(getRoot()); });
  el.artGallery.addEventListener("click", (e) => {
    const b = e.target.closest("[data-art-action='set']");
    if (!b) return;
    const r = getRoot();
    if (!r) { log("Select a card first.", "err"); return; }
    run("Setting cart art", () => api().set_cart_art(r, b.dataset.cart));
  });
  el.memContent.addEventListener("click", async (e) => {
    const trimBtn = e.target.closest("[data-mem-action='trim']");
    if (trimBtn) {
      const folder = trimBtn.dataset.folder;
      const input = trimBtn.parentElement.querySelector(".keep-input");
      const keep = parseInt(input.value, 10);
      if (isNaN(keep) || keep < 0) { log("Enter a valid 'keep latest' number.", "err"); return; }
      const r = getRoot();
      if (!r) { log("Select a card first.", "err"); return; }
      if (!(await confirmDialog(`Trim this game to its newest ${keep} save state(s)?\nA full snapshot is saved first, then the older ones are removed from the card.`, { okText: "Trim" }))) return;
      run(`Trimming to newest ${keep}`, () => api().trim_memory(r, folder, keep));
      return;
    }
    const delBtn = e.target.closest("[data-mem-action='del']");
    if (delBtn) {
      const r = getRoot();
      if (!r) { log("Select a card first.", "err"); return; }
      const folder = delBtn.dataset.folder, name = delBtn.dataset.name;
      if (!(await confirmDialog(`Delete this save state?\n${name}\nA full snapshot is saved first, then it's removed from the card.`, { danger: true, okText: "Delete" }))) return;
      run("Deleting save state", () => api().delete_memory(r, folder, name));
      return;
    }
    const head = e.target.closest(".game-head");
    if (head && !e.target.closest(".game-actions")) {
      const game = head.parentElement;
      const expanding = !game.classList.contains("expanded");
      game.classList.toggle("expanded");
      if (expanding) loadGameThumbs(game, getRoot());
    }
  });
  el.sdSelect.addEventListener("change", () => { syncManual(); refresh(); });
  el.manualPath.addEventListener("change", refresh);
  el.artSource.addEventListener("change", () => {
    el.artUrl.classList.toggle("hidden", el.artSource.value !== "url");
  });

  api().version().then((v) => { el.version.textContent = "v" + v; }).catch(() => {});
  log("Analogue 3D Studio ready.", "sys");
  refreshSettings();
  refresh().then(refreshVersions);
  setInterval(pollStatus, 2500);  // keep the status strip live (plug/unplug)
}

if (window.pywebview && window.pywebview.api) {
  init();
} else {
  window.addEventListener("pywebviewready", init);
}
