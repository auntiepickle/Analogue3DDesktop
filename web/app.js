"use strict";

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;

const el = {
  version: $("version"), appUpdate: $("appUpdate"),
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
  // Minimal mode mirrors of the status surface above. Populated from the same
  // detect()/versions()/list_backups() data via _syncMinimal* so both views stay
  // in lockstep. New layout has separate LED-row status (one mono word) and
  // value (the actual version / label).
  minVersion: $("minVersion"), minAppUpdate: $("minAppUpdate"),
  minSdLed: $("minSdLed"), minSdStatus: $("minSdStatus"), minSdValue: $("minSdValue"),
  minFwLed: $("minFwLed"), minFwStatus: $("minFwStatus"), minFwValue: $("minFwValue"),
  minCtrlLed: $("minCtrlLed"), minCtrlStatus: $("minCtrlStatus"), minCtrlValue: $("minCtrlValue"),
  minLastState: $("minLastState"),
};

const MANUAL = "__manual__";
const MODE_KEY = "a3d:mode";
const THEME_KEY = "a3d:theme";
const CLEAR_KEY = "a3d:clear";
const LAUNCH_TINKER_KEY = "a3d:launchTinker";

/* Mirrors Analogue 3D (Gold, White), Pocket (Glow), and N64 Funtastic
   accents. Each id maps to a `.theme-<id>` body class that overrides the
   gold tokens, so all `var(--gold)` references re-theme automatically. */
const THEMES = [
  { id: "gold",      name: "Gold",      dot: "#e8b923" },
  { id: "white",     name: "White",     dot: "#f0eee6" },
  { id: "glow",      name: "Glow",      dot: "#c4f070" },
  { id: "ice",       name: "Ice",       dot: "#58c7e3" },
  { id: "jungle",    name: "Jungle",    dot: "#3fcb6b" },
  { id: "watermelon",name: "Watermelon",dot: "#ff5b6b" },
  { id: "grape",     name: "Grape",     dot: "#a663ff" },
  { id: "fire",      name: "Fire",      dot: "#ff7430" },
  { id: "atomic",    name: "Atomic",    dot: "#b066ff" },
  { id: "smoke",     name: "Smoke",     dot: "#cfd1d5" },
];

function getMode() {
  // URL hash override (set by app.py when A3D_MODE env is present) — used for
  // screenshot capture in advanced mode without flipping localStorage. Only
  // honoured if the user hasn't picked a theme/mode this session.
  const m = (location.hash || "").match(/[#&]mode=([a-z]+)/);
  if (m) return m[1];
  return localStorage.getItem(MODE_KEY) || "minimal";
}
/* When the user explicitly picks something, drop any A3D_* hash override so
   subsequent getX() calls reflect the click instead of re-applying the env. */
function _clearHashOverride() {
  if (location.hash && /theme=|mode=/.test(location.hash)) {
    try { history.replaceState(null, "", location.pathname + location.search); }
    catch (e) { location.hash = ""; }
  }
}
function setMode(m, persist) {
  document.body.classList.remove("mode-minimal", "mode-tinker");
  document.body.classList.add("mode-" + m);
  // Update aria-checked on BOTH mode toggles (More Controls in minimal +
  // Minimal in advanced) so screen readers announce the current state for
  // whichever toggle the user reaches (a11y + code review).
  const toTinker = document.getElementById("toTinker");
  const toMinimal = document.getElementById("toMinimal");
  if (toTinker) toTinker.setAttribute("aria-checked", m === "tinker" ? "true" : "false");
  if (toMinimal) toMinimal.setAttribute("aria-checked", m === "minimal" ? "true" : "false");
  if (persist !== false) {
    _clearHashOverride();    // user-initiated pick beats any A3D_MODE env override
    try { localStorage.setItem(MODE_KEY, m); }
    catch (e) { console.warn("Mode persistence failed:", e); }
  }
}

function getTheme() {
  // URL hash override (set by app.py when A3D_THEME env is present) — used to
  // render screenshots in each colorway without manipulating localStorage.
  const m = (location.hash || "").match(/[#&]theme=([a-z]+)/);
  if (m) return m[1];
  return localStorage.getItem(THEME_KEY) || "gold";
}
function setTheme(id) {
  _clearHashOverride();    // user-initiated pick beats any A3D_THEME env override
  THEMES.forEach((t) => document.body.classList.remove("theme-" + t.id));
  document.body.classList.add("theme-" + id);
  try { localStorage.setItem(THEME_KEY, id); } catch (e) {}
  _renderThemePicker();
}

function getLaunchTinker() {
  return localStorage.getItem(LAUNCH_TINKER_KEY) === "1";
}
function setLaunchTinker(on) {
  try { localStorage.setItem(LAUNCH_TINKER_KEY, on ? "1" : "0"); } catch (e) {}
  const cb = $("launchTinkerToggle");
  if (cb) cb.checked = !!on;
}

function getClear() {
  // Funtastic translucent finish is the default - it's THE look. If the user
  // explicitly opts out we honor that, but a fresh launch should land on the
  // best version of the design.
  const v = localStorage.getItem(CLEAR_KEY);
  return v === null ? true : v === "1";
}
function setClear(on) {
  document.body.classList.toggle("clear", !!on);
  try { localStorage.setItem(CLEAR_KEY, on ? "1" : "0"); } catch (e) {}
  const cb = $("clearToggle");
  if (cb) cb.checked = !!on;
}

function _renderThemePicker() {
  const host = $("themePicker");
  if (!host) return;
  const cur = getTheme();
  host.innerHTML = "";
  THEMES.forEach((t) => {
    const sw = document.createElement("button");
    sw.className = "theme-swatch" + (t.id === cur ? " active" : "");
    sw.dataset.theme = t.id;
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.background = t.dot;
    dot.style.boxShadow = `0 0 10px ${t.dot}66`;
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = t.name;
    sw.appendChild(dot); sw.appendChild(name);
    sw.addEventListener("click", () => setTheme(t.id));
    host.appendChild(sw);
  });
}

/* Light up the N64-front 4-port indicator according to how many controllers
   are detected. The SVG sits in minimal mode's CONTROLLER instrument; lit
   ports use the .lit class which CSS handles for glow + theme color. */
/* Per-port renderer. Takes a list of device dicts from versions().controller_devices
   (or synthesises one from detect()'s counts when versions() hasn't been called
   yet) and lights the SVG ports + populates the status row beneath them.

   Per-port status:
     mode=app, up_to_date=true       → green dot, version string
     mode=app, up_to_date=false      → amber dot, version string (update available)
     mode=app, version_int=null      → grey dot, "?" (version read failed)
     mode=switch                     → red dot, "S MODE"
     empty slot                      → off dot, "—" */
function renderControllerPorts(devs) {
  const svg = document.getElementById("minCtrlPorts");
  const row = document.getElementById("minPortStatus");
  const hint = document.getElementById("minPortHint");
  if (!svg || !row) return;
  devs = (devs || []).slice(0, 4);
  // When nothing is plugged in, surface a one-liner instead of four dashes —
  // a real user assumed they had to plug the pad into the Analogue 3D itself
  // to update. Empty-state hint nudges them to the PC instead.
  if (hint) hint.classList.toggle("hidden", devs.length > 0);
  const ports = svg.querySelectorAll(".port");
  const cells = row.querySelectorAll(".min-port-cell");
  for (let i = 0; i < ports.length; i++) {
    const d = devs[i];
    const port = ports[i];
    const cell = cells[i];
    const dot = cell.querySelector(".min-port-dot");
    const text = cell.querySelector(".min-port-text");
    port.classList.remove("lit", "port-warn", "port-bad");
    dot.classList.remove("ok", "warn", "bad");
    if (!d) {                                               // empty slot
      text.textContent = "—";
      continue;
    }
    if (d.mode === "switch") {
      port.classList.add("lit", "port-bad");
      dot.classList.add("bad");
      // Just "S" — the red dot already conveys the alarm and "S MODE"
      // overflowed the cell at narrow widths, blurring sibling labels into
      // a "S MODE S MODE S MODE" run-on. The tooltip below carries the long form.
      text.textContent = "S";
      cell.title = "Switch-emulation (S) mode — flip the back switch to D to update";
      continue;
    }
    cell.title = "";
    // mode === "app"
    port.classList.add("lit");
    if (d.version_str) {
      if (d.up_to_date === false) {
        port.classList.add("port-warn");
        dot.classList.add("warn");
      } else {
        dot.classList.add("ok");
      }
      text.textContent = d.version_str;
    } else {
      text.textContent = "?";
    }
  }
}

// Sync the port row to whatever's known right now. Prefers the cached rich
// per-device list from versions(); falls back to count-only synthesis from
// detect()'s controllers + controllers_switch_mode if versions() hasn't fired
// yet (or if hardware just changed).
function updateControllerPorts(n) {
  if (controllerDevs && controllerDevs.length === (n + controllerSwitchModeCount)) {
    renderControllerPorts(controllerDevs);
    return;
  }
  const devs = [];
  for (let i = 0; i < (n || 0); i++) devs.push({ mode: "app" });
  for (let i = 0; i < controllerSwitchModeCount; i++) devs.push({ mode: "switch" });
  renderControllerPorts(devs);
}

/* Mirror the tinker-view status into the minimal instruments so a user who
   switches modes mid-session sees a coherent screen. Reads from the tinker
   DOM rather than threading data through every call site - prototype-level,
   intentionally light-touch. Each instrument has a small status word (e.g.
   "CONNECTED" / "UPDATE" / "NONE") and a bigger value line below it. */
function _syncMinimal() {
  if (!el.minSdLed) return;
  updateControllerPorts(controllerCount);

  // -- SD CARD --
  el.minSdLed.className = el.sdLed.className;
  const sdText = (el.sdValue.textContent || "").toLowerCase();
  if (el.sdLed.className.indexOf("on") !== -1) {
    el.minSdStatus.textContent = "connected";
  } else if (sdText.indexOf("not detected") !== -1 || sdText.indexOf("no analogue") !== -1) {
    el.minSdStatus.textContent = "not found";
  } else {
    el.minSdStatus.textContent = "pick a drive";
  }
  // Mirror the advanced sdSelect options into minSdValue (the minimal-mode
  // selector). Closed-state text stays short — just the volume label — so
  // it never truncates. The stats line below carries path + free space.
  if (el.minSdValue && el.minSdValue.tagName === "SELECT") {
    const upstream = Array.from(el.sdSelect.options).map(o => o.value + "\t" + o.textContent);
    const current = Array.from(el.minSdValue.options).map(o => o.value + "\t" + o.textContent);
    if (upstream.join("|") !== current.join("|")) {
      el.minSdValue.innerHTML = "";
      Array.from(el.sdSelect.options).forEach((src) => {
        const o = document.createElement("option");
        o.value = src.value;
        // Just the [label] for the closed value. Source text is now "path [label]".
        if (src.value && src.value !== MANUAL) {
          // Match the LAST bracket pair — paths can contain brackets themselves
          // (e.g. "E:\[Backup]\... [ANALOGUE 3D]"), and the volume label is at
          // the end of the picker option string.
          const matches = src.textContent.match(/\[([^\]]+)\](?!.*\[)/);
          o.textContent = matches ? matches[1] : src.textContent;
        } else {
          o.textContent = src.textContent;     // "Enter a path manually..." kept verbatim
        }
        el.minSdValue.appendChild(o);
      });
    }
    el.minSdValue.value = el.sdSelect.value;
  }
  // Stats line beneath the minimal SD value: drive path + free space.
  const minStats = document.getElementById("minSdStats");
  if (minStats) {
    const sel = el.sdSelect.options[el.sdSelect.selectedIndex];
    const free = sel && sel.dataset.freeGb ? `${sel.dataset.freeGb} GB free` : "";
    const path = sel ? sel.value : "";
    minStats.textContent = path && free ? `${path}  ·  ${free}` : (path || "");
  }

  // -- CONSOLE FIRMWARE --
  const okBadge = el.consoleVer.querySelector(".badge.ok");
  const updBadge = el.consoleVer.querySelector(".badge.upd");
  if (okBadge) {
    el.minFwLed.className = "led on";
    el.minFwStatus.textContent = "up to date";
  } else if (updBadge) {
    el.minFwLed.className = "led warn";          // theme accent: attention
    el.minFwStatus.textContent = "update";
  } else if (el.consoleVer.querySelector(".muted")) {
    el.minFwLed.className = "led off";
    el.minFwStatus.textContent = "—";
  } else {
    el.minFwLed.className = "led off";
    el.minFwStatus.textContent = "no fw";
  }
  // Render the version line; strip the badge (status is shown separately).
  el.minFwValue.innerHTML = el.consoleVer.innerHTML;
  const fwBadge = el.minFwValue.querySelector(".badge");
  if (fwBadge) fwBadge.remove();

  // -- CONTROLLER --
  // (The per-port status row beneath the SVG carries the actual versions
  // now; #minCtrlValue is hidden and we stopped writing to it. The .status
  // span above the SVG is the only one that still gets a label.)
  el.minCtrlLed.className = el.padLed.className;
  if (controllerCount > 0) {
    el.minCtrlStatus.textContent = "connected";
  } else if (controllerSwitchModeCount > 0) {
    el.minCtrlStatus.textContent = "in S mode";
  } else {
    el.minCtrlStatus.textContent = "none";
  }
}

/* The LAST state line: when's the most recent backup, and how big. Reads from
   the same `backups` array refreshBackups() populates. */
function _syncMinimalLast() {
  if (!el.minLastState) return;
  if (!backups || !backups.length) {
    el.minLastState.textContent = "no backup yet";
    return;
  }
  const newest = backups[0];
  el.minLastState.textContent =
    `backup ${_relativeWhen(newest.when)}  ·  ${humanSize(newest.bytes)}`;
}

function _relativeWhen(whenStr) {
  // when format is "YYYY-MM-DD HH:MM" (see api.list_backups).
  if (!whenStr) return "—";
  const parts = whenStr.split(" ");
  const d = parts[0]; const t = parts[1] || "00:00";
  if (!d || d.split("-").length !== 3) return whenStr;
  const [y, mo, da] = d.split("-").map(Number);
  const [h, mi] = t.split(":").map(Number);
  const then = new Date(y, mo - 1, da, h || 0, mi || 0);
  const diff = Date.now() - then.getTime();
  if (diff < 0) return whenStr;
  const hour = 3600000, day = 86400000;
  if (diff < hour) return "just now";
  if (diff < day) return "today";
  const days = Math.floor(diff / day);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return whenStr;   // exact for older
}

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
let controllerSwitchModeCount = 0;     // pads stuck in S-mode (Nintendo emulation)
// Cached rich per-device list from the last versions() call — has mode,
// version_int, up_to_date per controller. Stays around between polls so the
// 2.5s status refresh doesn't clobber it with count-only data.
let controllerDevs = null;

/* Status text for the controller surface. A pad in the S position on the
   back switch reports as a Nintendo N64 controller and the flash protocol
   can't reach it — when N == 0 but switch-mode > 0, tell the user instead
   of silently saying "none connected." */
function _ctrlStatusText(n, switchN) {
  if (n > 0) return `${n} connected`;
  if (switchN > 0) {
    const pl = switchN === 1 ? "controller" : "controllers";
    return `${switchN} ${pl} in S mode — flip the back switch to D to update`;
  }
  return "none connected";
}
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

window.deskProgress = function (pct, block, nblocks) {
  el.busyProg.classList.remove("hidden");
  el.busyProgLabel.classList.remove("hidden");
  el.busySpin.classList.add("hidden");
  el.busyBar.style.width = pct + "%";
  const prefix = flashTarget && flashTarget.total > 1
    ? `controller ${flashTarget.idx}/${flashTarget.total}  ·  ` : "";
  // After the last block flashes the engine sits in _wait_until_ready(),
  // polling each controller for a response before re-enumerating. Without
  // a label swap the busy overlay stayed frozen at "100% (block 35/35)"
  // and looked stuck. Tell the user we're waiting on the controller now.
  if (block >= nblocks && pct >= 100) {
    el.busyProgLabel.textContent = `${prefix}flashed — verifying controller…`;
    el.busySpin.classList.remove("hidden");
  } else {
    el.busyProgLabel.textContent = `${prefix}${pct}%  (block ${block}/${nblocks})`;
  }
};

window.deskFlashTarget = function (idx, total) {
  flashTarget = { idx: idx, total: total };
};

window.deskSteps = function (labels) {
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

window.deskStepStatus = function (i, status) {
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

window.deskStepNote = function (i, note) {
  const li = el.busySteps.children[i];
  if (!li) return;
  let n = li.querySelector(".note");
  if (!n) { n = document.createElement("span"); n.className = "note"; li.appendChild(n); }
  n.textContent = note ? "  - " + note : "";
};

window.deskDownload = function (pct) {
  el.busyProg.classList.remove("hidden");
  el.busyProgLabel.classList.remove("hidden");
  el.busySpin.classList.add("hidden");
  el.busyBar.style.width = pct + "%";
  el.busyProgLabel.textContent = `Downloading update… ${pct}%`;
};

window.deskBackup = function (pct) {
  el.busyProg.classList.remove("hidden");
  el.busyProgLabel.classList.remove("hidden");
  el.busySpin.classList.add("hidden");
  el.busyBar.style.width = pct + "%";
  el.busyProgLabel.textContent = `Backing up… ${pct}%`;
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

/* Stats line under the advanced TARGET SD CARD picker — free space + a
   "best-match" marker — surfaced beneath the dropdown instead of inline so
   the selected-option text stays short and stops truncating. */
function renderSdPickerStats() {
  const stats = document.getElementById("sdPickerStats");
  if (!stats) return;
  const sel = el.sdSelect.options[el.sdSelect.selectedIndex];
  if (!sel || !sel.dataset.freeGb) { stats.textContent = ""; return; }
  const free = `${sel.dataset.freeGb} GB free`;
  const star = sel.dataset.strong ? "  ·  best match ★" : "";
  stats.textContent = `${free}${star}`;
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
    // Short option text: path + label only. Free space + strong-match marker
    // are listed beneath the picker (#sdPickerStats) so the selected-state
    // doesn't truncate.
    o.textContent = `${c.path}${label}`;
    o.dataset.freeGb = c.free_gb;
    o.dataset.strong = c.strong ? "1" : "";
    el.sdSelect.appendChild(o);
  });
  const manualOpt = document.createElement("option");
  manualOpt.value = MANUAL;
  manualOpt.textContent = "Enter a path manually…";
  el.sdSelect.appendChild(manualOpt);

  const strong = cards.find((c) => c.strong);
  const prevIsStrongCard = prev && cards.some((c) => c.path === prev && c.strong);
  const prevIsAvailable = prev && [...el.sdSelect.options].some((o) => o.value === prev);
  // Strong (auto-detected) match beats a stale weak prev pick — so plugging
  // in a real Analogue 3D card after the app was sitting on some other drive
  // actually switches the picker. A strong prev still wins, though, so a
  // multi-card scenario keeps the user's explicit choice.
  if (prevIsStrongCard) {
    el.sdSelect.value = prev;
  } else if (strong) {
    el.sdSelect.value = strong.path;
  } else if (prevIsAvailable) {
    el.sdSelect.value = prev;
  } else if (cards.length) {
    el.sdSelect.value = cards[0].path;
  } else {
    el.sdSelect.value = MANUAL;
  }
  syncManual();
  renderSdPickerStats();

  // status LEDs
  if (strong) {
    el.sdLed.className = "led on";
    el.sdValue.textContent = `${strong.path}${strong.label ? " [" + strong.label + "]" : ""}`;
  } else if (cards.length) {
    el.sdLed.className = "led off";
    el.sdValue.textContent = "no Analogue 3D SD card detected";
  } else {
    el.sdLed.className = "led off";
    el.sdValue.textContent = "not detected (enter a path)";
  }

  const n = data.controllers || 0;
  const sn = data.controllers_switch_mode || 0;
  controllerCount = n;
  controllerSwitchModeCount = sn;
  el.padLed.className = n > 0 ? "led on" : (sn > 0 ? "led warn" : "led off");
  el.padValue.textContent = _ctrlStatusText(n, sn);

  await refreshBackups();
  await refreshMemories();
  await refreshArt();
  _syncMinimal();
}

/* Lightweight background poll: keep the status strip (controllers / SD) live
   without rebuilding the whole UI. A full refresh only runs if the set of cards
   actually changed (memories/art depend on the card). Skipped while busy. */
async function pollStatus() {
  if (busyNow) return;
  let data;
  try { data = await api().detect(); } catch (e) { return; }

  const n = data.controllers || 0;
  const sn = data.controllers_switch_mode || 0;
  const controllerChanged = n !== controllerCount || sn !== controllerSwitchModeCount;
  controllerCount = n;
  controllerSwitchModeCount = sn;
  // Cached rich device list goes stale the moment counts shift — discard
  // so the next paint synthesises from counts until versions() refills it.
  if (controllerChanged) controllerDevs = null;
  el.padLed.className = n > 0 ? "led on" : (sn > 0 ? "led warn" : "led off");
  el.padValue.textContent = _ctrlStatusText(n, sn);

  const cardSig = (data.cards || []).map((c) => c.path).join(",");
  if (lastCardSig !== null && cardSig !== lastCardSig) {
    await refresh();
  }
  // a controller was plugged/unplugged: refresh the Updates section's version line
  if (controllerChanged) {
    await refreshVersions();
  }
  _syncMinimal();
}

let backups = [];
async function refreshBackups() {
  try { backups = await api().list_backups(); } catch (e) { backups = []; }
  _syncMinimalLast();   // keep the minimal-mode LAST line in lockstep
  const prev = el.backupSelect.value;
  el.backupSelect.innerHTML = "";
  if (!backups.length) {
    const o = document.createElement("option");
    o.value = ""; o.textContent = "No backups found";
    el.backupSelect.appendChild(o);
    return;
  }
  backups.forEach((b) => {
    const o = document.createElement("option");
    o.value = b.name;
    const empty = b.bytes < 2048 ? "  - empty" : "";
    const lbl = b.label ? "  ·  " + b.label : "";
    o.textContent = `${b.when || b.name}${lbl}  (${humanSize(b.bytes)})${empty}`;
    el.backupSelect.appendChild(o);
  });
  if (prev && [...el.backupSelect.options].some((o) => o.value === prev)) {
    el.backupSelect.value = prev;
  }
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
let memKeepDefault = 5;
let memPage = 0;
const MEM_PAGE_SIZE = 16;   /* was 8 - sparse on ultrawide where the thumb grid fits ~23 across */
let selectedStates = new Set();   // keys: "<folder><name>"
let selectAnchor = null;          // {folder, idx} for shift-range selection

function renderMemories(m, root) {
  selectedStates.clear();
  selectAnchor = null;
  memGames = m.available ? m.games : [];
  memKeepDefault = m.keep_default || 5;
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
  selectedStates.clear();
  selectAnchor = null;
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
  refreshThumbSelection();
}

function buildGameRow(g, root, autoExpand) {
  const game = document.createElement("div");
  game.className = "game" + (autoExpand ? " expanded" : "");
  game.innerHTML = `
    <div class="game-head">
      <span class="chev">&#9656;</span>
      <img class="cover" alt="" />
      <span class="game-title"></span>
      <span class="game-id"></span>
      <span class="game-meta">${g.count} state${g.count === 1 ? "" : "s"} &middot; ${humanSize(g.total_bytes)}</span>
      <span class="game-actions">
        <label>keep latest</label>
        <input type="number" class="keep-input" min="0" value="${memKeepDefault}" />
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
    t.dataset.folder = g.folder;
    t.dataset.name = s.name;
    t.dataset.idx = i;
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
    if (!cur) {
      // Current version is unknown but we know what's available - offer to install,
      // never claim "up to date" without something to compare against.
      html += ` <span class="arrow">&rarr;</span> <span class="latest">${latest}</span> <span class="badge upd">install</span>`;
    } else if (update) {
      html += ` <span class="arrow">&rarr;</span> <span class="latest">${latest}</span> <span class="badge upd">update available</span>`;
    } else {
      html += ` <span class="badge ok">up to date</span>`;
    }
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
  // Multi-controller-aware: when versions() returns a per-device list with
  // more than one app-mode pad, render a line per pad so the user can see
  // which one is behind. Falls back to the single ctrl_current/ctrl_latest
  // line when only one pad is connected (the most common case).
  const appDevs = (v.controller_devices || []).filter((d) => d.mode === "app");
  if (!v.controllers) {
    el.ctrlVer.innerHTML = '<span class="muted">no controller connected</span>'
      + ' <span class="muted hint">— plug a controller into the PC</span>';
  } else if (appDevs.length > 1) {
    // The #1/#2 numbering is USB-enumeration order, NOT physical-port
    // position on the Analogue 3D — Windows can re-order pads between
    // sessions or hub plug-ins. Surfaced as a tooltip on each row so a
    // user doesn't try to map #2 to "the pad in port 2".
    const tip = "USB-enumeration order, not physical port — Windows may re-order between sessions.";
    el.ctrlVer.innerHTML = appDevs.map((d, i) => {
      const cur = d.version_str || "unknown";
      const upd = d.version_int != null && v.ctrl_latest && d.up_to_date === false;
      return `<div class="ver-multi" title="${tip}"><span class="muted">#${i + 1}</span> `
        + verLine(cur, v.ctrl_latest, upd, "unknown") + `</div>`;
    }).join("");
  } else {
    el.ctrlVer.innerHTML = verLine(v.ctrl_current, v.ctrl_latest, v.ctrl_update, "unknown");
  }
  consoleUpToDate = !!(v.console_current && v.console_latest && !v.console_update);
  applyGating();
  await populateCtrlVersions();
  // Drive the per-port LEDs + version labels off the rich per-device list when
  // we have it (versions() opens each controller to read its firmware). detect()'s
  // 2.5s poll only gives counts, so this fills in green/amber state once on demand.
  if (v.controller_devices) {
    controllerDevs = v.controller_devices;
    renderControllerPorts(controllerDevs);
  } else {
    controllerDevs = null;
  }
  _syncMinimal();
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
const ART_PAGE_SIZE = 24;   /* was 18 - sparse rows on ultrawide where 26+ tiles fit per row */

async function syncCustomPackOption() {
  let has = false;
  try { has = await api().has_custom_pack(); } catch (e) {}
  const sel = el.artSource;
  let opt = sel.querySelector('option[value="custom"]');
  if (has && !opt) {
    opt = document.createElement("option");
    opt.value = "custom";
    opt.textContent = "My custom labels";
    sel.insertBefore(opt, sel.firstChild);
  } else if (!has && opt) {
    opt.remove();
  }
}

async function refreshArt() {
  const root = getRoot();
  const hideControls = () => $("artControls").classList.add("hidden");
  await syncCustomPackOption();
  if (!root) {
    el.artGallery.innerHTML = '<p class="muted pad">Select a card to see its cartridge art.</p>';
    hideControls(); return;
  }
  let data;
  try { data = await api().cart_art_games(root, el.artSource.value); }
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
  const actions = document.createElement("div");
  actions.className = "art-actions";
  const setb = document.createElement("button");
  setb.className = "action sm setart";
  setb.textContent = "Set art";
  setb.dataset.artAction = "set";
  setb.dataset.cart = g.cart_id;
  actions.appendChild(setb);
  // "Revert" only on carts the user actually overrode
  if (g.overridden) {
    const delb = document.createElement("button");
    delb.className = "ghost sm artreset";
    delb.textContent = "Revert";
    delb.title = "Remove your custom art and revert this cart to the standard art";
    delb.dataset.artAction = "reset";
    delb.dataset.cart = g.cart_id;
    delb.dataset.title = g.title;
    actions.appendChild(delb);
  }
  tile.appendChild(img);
  tile.appendChild(cap);
  tile.appendChild(id);
  tile.appendChild(actions);
  return tile;
}

async function lazyArt(root) {
  const source = el.artSource.value;
  const imgs = [...el.artGallery.querySelectorAll("img[data-cart]")];
  for (const img of imgs) {
    try {
      const url = await api().cart_art(root, img.dataset.cart, source);
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
    el.backupRoot.title = s.backup_root;  // hover shows the full path when truncated
    return s;
  } catch (e) { return null; }
}

let _modalOpener = null;
function _trapTab(modal, e) {
  if (e.key !== "Tab") return;
  const all = modal.querySelectorAll(
    'button, [href], input:not([type=hidden]), select, textarea, [tabindex]:not([tabindex="-1"])');
  const visible = [...all].filter(el => !el.disabled && el.offsetParent !== null);
  if (!visible.length) return;
  const first = visible[0], last = visible[visible.length - 1];
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}
function openSettings() {
  _modalOpener = document.activeElement;     // remember focus for return-on-close (a11y)
  refreshSettings();
  _renderThemePicker();
  const cb = $("clearToggle");
  if (cb) {
    cb.checked = getClear();
    cb.onchange = (e) => setClear(e.target.checked);
  }
  const lt = $("launchTinkerToggle");
  if (lt) {
    lt.checked = getLaunchTinker();
    lt.onchange = (e) => setLaunchTinker(e.target.checked);
  }
  const modal = $("settingsModal");
  modal.classList.remove("hidden");
  modal.onkeydown = (e) => _trapTab(modal, e);
  // Move focus into the modal so Tab cycles inside it from the first stop.
  setTimeout(() => {
    const f = modal.querySelector('button:not([disabled]), input:not([disabled])');
    if (f) f.focus();
  }, 0);
}
function closeSettings() {
  const modal = $("settingsModal");
  modal.classList.add("hidden");
  modal.onkeydown = null;
  if (_modalOpener && _modalOpener.focus) _modalOpener.focus();
}

/* ---------- styled confirm modal ---------- */
/* Tiny GitHub-flavoured-markdown subset → HTML for the release-notes block.
   Handles: headings (#…######), bullets (-/*), fenced code blocks (```), inline
   `code`, **bold**, *italic*, blank lines as paragraph breaks. The release body
   is trusted (only repo maintainers can write it), but we still escape ALL HTML
   in the source before applying our own narrow set of tags, so a stray
   `<script>` in a note can never execute. */
function renderMarkdown(md) {
  if (!md) return "";
  // 1) Escape all HTML in the source — we only inject the tags we generate.
  let s = md.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // 2) Inline transforms — apply per line so they don't span blocks. Italic
  //    uses lookarounds so chained `*a* *b*` and adjacent `*a**b*` both work:
  //    no stray `*` allowed immediately before or after the matched pair.
  const inline = (t) => t
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
  // 3) Block parse — fenced code first (everything inside is literal), then
  //    headings, bullets, paragraphs.
  const out = [];
  let inList = false;
  let inCode = false;
  const codeBuf = [];
  const closeList = () => { if (inList) { out.push("</ul>"); inList = false; } };
  const closeCode = () => {
    if (inCode) { out.push(`<pre><code>${codeBuf.join("\n")}</code></pre>`);
      codeBuf.length = 0; inCode = false; }
  };
  for (const raw of s.split(/\r?\n/)) {
    if (/^\s*```/.test(raw)) {
      if (inCode) { closeCode(); } else { closeList(); inCode = true; }
      continue;
    }
    if (inCode) { codeBuf.push(raw); continue; }
    const line = raw.replace(/\s+$/, "");
    if (!line) { closeList(); continue; }
    const head = line.match(/^(#{1,6})\s+(.*)$/);
    if (head) {
      closeList();
      const level = Math.min(6, Math.max(4, head[1].length + 2));   // h3 -> h5, h4 -> h6, capped
      out.push(`<h${level}>${inline(head[2])}</h${level}>`);
      continue;
    }
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (bullet) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${inline(bullet[1])}</li>`);
      continue;
    }
    closeList();
    out.push(`<p>${inline(line)}</p>`);
  }
  closeList();
  closeCode();   // tolerate an unclosed fence at EOF
  return out.join("");
}

function confirmDialog(message, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    const modal = $("modal"), ok = $("modalOk"), cancel = $("modalCancel");
    $("modalMsg").textContent = message;
    $("modalTitle").textContent = opts.title || "Confirm";   /* pillar #4 — assume competence, no "Please" */
    ok.textContent = opts.okText || "Confirm";
    ok.classList.toggle("danger", !!opts.danger);
    // Optional release-notes / detail block (textContent so any markdown is
    // shown verbatim — no HTML injection risk from upstream).
    const notesEl = $("modalNotes");
    if (notesEl) {
      const notes = (opts.notes || "").trim();
      if (notes) {
        // renderMarkdown escapes input first then re-emits a narrow tag set,
        // so this innerHTML write is safe against scripted release bodies.
        notesEl.innerHTML = renderMarkdown(notes);
        notesEl.classList.remove("hidden");
      } else {
        notesEl.innerHTML = "";
        notesEl.classList.add("hidden");
      }
    }
    modal.classList.remove("hidden");
    ok.focus();
    const close = (val) => {
      modal.classList.add("hidden");
      if (notesEl) { notesEl.classList.add("hidden"); notesEl.innerHTML = ""; }
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

/* ---------- styled text prompt ---------- */
function promptDialog(message, opts) {
  opts = opts || {};
  return new Promise((resolve) => {
    const modal = $("promptModal"), ok = $("promptOk"), cancel = $("promptCancel"), input = $("promptInput");
    $("promptTitle").textContent = message;
    ok.textContent = opts.okText || "OK";
    input.value = opts.value || "";
    input.placeholder = opts.placeholder || "";
    modal.classList.remove("hidden");
    input.focus();
    input.select();
    const close = (val) => {
      modal.classList.add("hidden");
      ok.removeEventListener("click", onOk);
      cancel.removeEventListener("click", onCancel);
      input.removeEventListener("keydown", onKey);
      resolve(val);
    };
    const onOk = () => close(input.value.trim());
    const onCancel = () => close(null);
    const onKey = (e) => {
      if (e.key === "Enter") { e.preventDefault(); close(input.value.trim()); }
      else if (e.key === "Escape") { e.preventDefault(); close(null); }
    };
    ok.addEventListener("click", onOk);
    cancel.addEventListener("click", onCancel);
    input.addEventListener("keydown", onKey);
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
  async backup() {
    const r = needRoot(); if (!r) return;
    const label = await promptDialog("Label this backup (optional):", { okText: "Back up", placeholder: "e.g. before-firmware" });
    if (label === null) return;
    run("Backing up SD card", () => api().backup(r, label));
  },
  firmware() { const r = needRoot(); if (r) run("Updating console firmware", () => api().update_firmware(r), true); },
  art() {
    const r = needRoot(); if (!r) return;
    const sel = el.artSource.value;
    let source = null;
    if (sel === "url") {
      source = el.artUrl.value.trim();
      if (!source) { log("Enter the art pack URL.", "err"); return; }
    } else if (sel === "custom") {
      source = "custom";  // install_art resolves this to your saved custom_labels.db
    }
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
  async archiveMem() {
    const r = needRoot(); if (!r) return;
    const label = await promptDialog("Label this archive (optional):", { okText: "Archive", placeholder: "e.g. before-trim" });
    if (label === null) return;
    run("Archiving all save states", () => api().archive_memories(r, label));
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
    run("Restoring " + game.replace(/\s*\(\d+\)\s*$/, ""), () => api().restore_memories_game(r, name, cart));
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
  async renameSnapshot() {
    const name = el.memSnapshotSelect.value;
    if (!name) { log("No snapshot selected.", "err"); return; }
    const s = snapshots.find((x) => x.name === name);
    const label = await promptDialog("Snapshot label (blank to clear):",
      { okText: "Save", value: s ? s.label || "" : "", placeholder: "e.g. before-trim" });
    if (label === null) return;
    run("Relabeling snapshot", () => api().rename_snapshot(name, label));
  },
  async renameBackup() {
    const name = el.backupSelect.value;
    if (!name) { log("No backup selected.", "err"); return; }
    const b = backups.find((x) => x.name === name);
    const label = await promptDialog("Backup label (blank to clear):",
      { okText: "Save", value: b ? b.label || "" : "", placeholder: "e.g. pre-firmware" });
    if (label === null) return;
    run("Relabeling backup", () => api().rename_backup(name, label));
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
  delSelected() { deleteSelectedStates(); },
  clearSel() { selectedStates.clear(); selectAnchor = null; refreshThumbSelection(); },
};

/* ---------- save-state multi-select (Shift/Ctrl click + Del) ---------- */
function thumbKey(folder, name) { return folder + "" + name; }

function refreshThumbSelection() {
  el.memContent.querySelectorAll(".thumb").forEach((t) => {
    t.classList.toggle("selected", selectedStates.has(thumbKey(t.dataset.folder, t.dataset.name)));
  });
  const n = selectedStates.size;
  $("memSelBar").classList.toggle("hidden", n === 0);
  if (n) $("memSelCount").textContent = `${n} save state${n === 1 ? "" : "s"} selected`;
}

function handleThumbSelect(tile, e) {
  const folder = tile.dataset.folder, name = tile.dataset.name;
  const idx = parseInt(tile.dataset.idx, 10);
  const key = thumbKey(folder, name);
  if (e.shiftKey && selectAnchor && selectAnchor.folder === folder) {
    if (!(e.ctrlKey || e.metaKey)) selectedStates.clear();
    const lo = Math.min(idx, selectAnchor.idx), hi = Math.max(idx, selectAnchor.idx);
    tile.closest(".thumbs").querySelectorAll(".thumb").forEach((t) => {
      const i = parseInt(t.dataset.idx, 10);
      if (i >= lo && i <= hi) selectedStates.add(thumbKey(t.dataset.folder, t.dataset.name));
    });
  } else if (e.ctrlKey || e.metaKey) {
    if (selectedStates.has(key)) selectedStates.delete(key);
    else selectedStates.add(key);
    selectAnchor = { folder, idx };
  } else {
    selectedStates.clear();
    selectedStates.add(key);
    selectAnchor = { folder, idx };
  }
  refreshThumbSelection();
}

async function deleteSelectedStates() {
  const r = getRoot();
  if (!r) { log("Select a card first.", "err"); return; }
  const items = [...selectedStates].map((k) => {
    const i = k.indexOf("");
    return { folder: k.slice(0, i), name: k.slice(i + 1) };
  });
  if (!(await confirmDialog(`Delete ${items.length} selected save state(s)?\nA full snapshot is saved first, then they're removed from the card.`, { danger: true, okText: "Delete" }))) return;
  selectedStates.clear();
  selectAnchor = null;
  run("Deleting selected save states", () => api().delete_memories(r, items));
}

async function checkAppUpdate(force) {
  let info = null;
  try { info = await api().update_check(!!force); } catch (e) {}
  // Two pills: el.appUpdate sits in the narrow Tinker rail (compact text),
  // el.minAppUpdate sits in the wider Minimal header (full text). The CSS
  // shrinks the rail pill, but the SHORT TEXT here is what keeps the layout
  // from overflowing — even after shrink, "Update available:" alone is
  // ~70-100px of pill before ellipsis can kick in.
  const pills = [
    { btn: el.appUpdate,    text: info ? `↑ v${info.latest}` : "" },
    { btn: el.minAppUpdate, text: info ? `Update available: v${info.latest}` : "" },
  ].filter((p) => p.btn);
  if (info && info.update_available) {
    pills.forEach(({ btn, text }) => {
      btn.textContent = text;
      btn.title = `You have v${info.current} — v${info.latest} is out. Click to download and install it.`;
      btn.onclick = () => startSelfUpdate(info);
      btn.classList.remove("hidden");
    });
    log(`A newer version is available: v${info.latest} (you have v${info.current}).`, "sys");
  } else {
    pills.forEach(({ btn }) => btn.classList.add("hidden"));
    if (force && info) {
      log(`v${info.current} — up to date.`, "sys");
    } else if (force) {
      log("Couldn't check for updates (offline?).", "err");
    }
  }
}

async function startSelfUpdate(info) {
  const notes = (info && info.notes || "").trim();
  if (!(await confirmDialog(
    `Update to v${info.latest}?\nThe app will download it and restart itself.`,
    { okText: "Update now", notes: notes }))) return;
  setBusy(true, `Downloading update v${info.latest}…`);
  log(`\n> Updating to v${info.latest}`, "sys");
  let res;
  try { res = await api().self_update(); }
  catch (e) { res = { ok: false, error: String(e) }; }

  if (res && res.restarting) {
    el.busyText.textContent = "Restarting into the new version…";
    return;  // the app is about to exit and relaunch
  }
  setBusy(false);
  const why = (res && res.error) || "Couldn't update in-app.";
  log("Update failed: " + why, "err");
  if (info.url && await confirmDialog(why + "\n\nOpen the releases page instead?",
                                      { okText: "Open page" })) {
    api().open_url(info.url);
  }
}

function init() {
  $("toTinker").addEventListener("click", () => setMode("tinker"));
  $("toMinimal").addEventListener("click", () => setMode("minimal"));
  $("minSettingsBtn").addEventListener("click", openSettings);

  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => handlers[btn.dataset.action]());
  });
  // kebab menus: toggle on the button, close on any other click. Each panel
  // (.block) creates its own stacking context in Funtastic mode (backdrop-
  // filter), so an open menu would be painted over by a sibling block;
  // .menu-open on the parent block raises its z-index above siblings.
  document.addEventListener("click", (e) => {
    const menuBtn = e.target.closest(".menu-btn");
    let toOpen = null;
    if (menuBtn) {
      const menu = menuBtn.parentElement.querySelector(".menu");
      if (menu && menu.classList.contains("hidden")) toOpen = menu;
    }
    document.querySelectorAll(".menu:not(.hidden)").forEach((m) => m.classList.add("hidden"));
    document.querySelectorAll(".block.menu-open").forEach((b) => b.classList.remove("menu-open"));
    if (toOpen) {
      toOpen.classList.remove("hidden");
      const block = toOpen.closest(".block");
      if (block) block.classList.add("menu-open");
    }
  });
  $("refreshBtn").addEventListener("click", refresh);
  const minRefresh = $("minRefreshBtn");
  if (minRefresh) minRefresh.addEventListener("click", refresh);
  // Click either version pill to force-recheck for a new release (bypasses
  // the engine's 1h cache). Useful when the user just cut a release and
  // wants to see the update-available pill appear right away.
  const onVersionClick = () => { log("Checking for updates…", "sys"); checkAppUpdate(true); };
  [el.version, el.minVersion].filter(Boolean).forEach((v) => {
    v.style.cursor = "pointer";
    v.title = "Click to check for a newer release";
    v.setAttribute("role", "button");
    v.setAttribute("tabindex", "0");
    v.addEventListener("click", onVersionClick);
    v.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onVersionClick(); } });
  });
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
  $("settingsBtn").addEventListener("click", openSettings);
  $("settingsClose").addEventListener("click", closeSettings);
  $("settingsModal").addEventListener("click", (e) => { if (e.target === $("settingsModal")) closeSettings(); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".menu:not(.hidden)").forEach((m) => m.classList.add("hidden"));
      document.querySelectorAll(".block.menu-open").forEach((b) => b.classList.remove("menu-open"));
      if ($("modal").classList.contains("hidden")) closeSettings();
    }
  });
  el.artGallery.addEventListener("click", async (e) => {
    const setb = e.target.closest("[data-art-action='set']");
    if (setb) {
      const r = getRoot();
      if (!r) { log("Select a card first.", "err"); return; }
      await run("Setting cart art", () => api().set_cart_art(r, setb.dataset.cart));
      // surface the result: jump to the "My custom labels" pack and preview it
      await syncCustomPackOption();
      if (el.artSource.querySelector('option[value="custom"]')) {
        el.artSource.value = "custom";
        el.artUrl.classList.add("hidden");
      }
      refreshArt();
      return;
    }
    const delb = e.target.closest("[data-art-action='reset']");
    if (delb) {
      const r = getRoot();
      if (!r) { log("Select a card first.", "err"); return; }
      const title = delb.dataset.title || delb.dataset.cart;
      if (!(await confirmDialog(
        `Remove your custom art for ${title}?\nIt reverts to the standard community art (first time downloads the pack).`,
        { danger: true, okText: "Remove" }))) return;
      run("Removing custom art", () => api().delete_cart_art(r, delb.dataset.cart));
      return;
    }
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
    const tile = e.target.closest(".thumb");
    if (tile && tile.dataset.name) {
      handleThumbSelect(tile, e);
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
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Delete") return;
    const tag = (document.activeElement && document.activeElement.tagName) || "";
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
    if (!selectedStates.size) return;
    e.preventDefault();
    deleteSelectedStates();
  });
  // When "Enter a path manually..." is picked, open the native folder picker
  // so the user can browse to a drive rather than typing. The picked path
  // populates the manualPath input + fires refresh; cancel reverts to whatever
  // card was selected before.
  function revertSdSelection(prev) {
    if (!prev) return;
    el.sdSelect.value = prev;
    if (el.minSdValue && el.minSdValue.tagName === "SELECT") el.minSdValue.value = prev;
    syncManual();
    renderSdPickerStats();
  }
  async function handleManualPick(prev) {
    try {
      const picked = await api().pick_sd_folder();
      if (picked) {
        el.manualPath.value = picked;
        refresh();
      } else {
        revertSdSelection(prev);      // user cancelled — restore previous on BOTH selects
      }
    } catch (e) {
      log("Folder picker failed: " + e, "err");
      revertSdSelection(prev);
    }
  }
  let _lastSdValue = el.sdSelect.value;
  el.sdSelect.addEventListener("change", () => {
    syncManual();
    renderSdPickerStats();
    if (el.sdSelect.value === MANUAL) {
      handleManualPick(_lastSdValue);
    } else {
      _lastSdValue = el.sdSelect.value;
      refresh();
    }
  });
  if (el.minSdValue && el.minSdValue.tagName === "SELECT") {
    el.minSdValue.addEventListener("change", () => {
      el.sdSelect.value = el.minSdValue.value;
      syncManual();
      renderSdPickerStats();
      if (el.minSdValue.value === MANUAL) {
        handleManualPick(_lastSdValue);
      } else {
        _lastSdValue = el.minSdValue.value;
        refresh();
      }
    });
  }
  el.manualPath.addEventListener("change", refresh);
  el.artSource.addEventListener("change", () => {
    el.artUrl.classList.toggle("hidden", el.artSource.value !== "url");
    refreshArt();  // preview the selected pack's icons + recompute Revert visibility
  });

  api().version().then((v) => {
    el.version.textContent = "v" + v;
    if (el.minVersion) el.minVersion.textContent = "v" + v;
  }).catch(() => {});
  checkAppUpdate();
  log("Analogue 3D Desktop ready.", "sys");
  refreshSettings().then((s) => {
    if (s && s.legacy_root && !s.is_custom) {
      log(`Older backups remain at ${s.legacy_root}.\nNew backups now go to ${s.backup_root}.\nUse the settings cog (top right) to change the location.`, "sys");
    }
  });
  refresh().then(refreshVersions);
  setInterval(pollStatus, 2500);  // keep the status strip live (plug/unplug)
}

// Apply saved mode + theme + clear at script-load time so the chosen view +
// accent + finish paint on the first frame. Priority: URL hash (screenshot
// capture) > "Always start with full controls" setting > stored MODE_KEY >
// default. When the setting forces tinker, we do NOT persist — so toggling
// the setting off later still lands on the user's actual last pick.
(function _bootMode() {
  const hash = (location.hash || "").match(/[#&]mode=([a-z]+)/);
  if (hash) { setMode(hash[1], false); return; }     // ephemeral — for screenshot capture
  if (getLaunchTinker()) { setMode("tinker", false); return; }
  setMode(getMode());
})();
setTheme(getTheme());
setClear(getClear());

if (window.pywebview && window.pywebview.api) {
  init();
} else {
  window.addEventListener("pywebviewready", init);
}
