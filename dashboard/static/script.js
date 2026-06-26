const REFRESH_MS = 3000;

const gateHeader = document.getElementById("gateHeader");
const gateStateText = document.getElementById("gateStateText");
const espOnline = document.getElementById("espOnline");
const presenceVal = document.getElementById("presenceVal");

const currentBody = document.getElementById("currentBody");
const currentCount = document.getElementById("currentCount");

const searchInput = document.getElementById("searchInput");
const searchBtn = document.getElementById("searchBtn");
const searchBody = document.getElementById("searchBody");

const manualPlate = document.getElementById("manualPlate");
const manualCheckin = document.getElementById("manualCheckin");
const manualCheckout = document.getElementById("manualCheckout");
const manualMsg = document.getElementById("manualMsg");

const logsBody = document.getElementById("logsBody");
const logsCount = document.getElementById("logsCount");

const STATE_LABEL = { closed: "CLOSED", checking: "CHECKING", open: "OPEN", unknown: "UNKNOWN" };

function emptyRow(colspan, text) {
  return `<tr class="empty-row"><td colspan="${colspan}">${text}</td></tr>`;
}

// ---------- Gate status ----------

async function refreshGateStatus() {
  try {
    const res = await fetch("/api/gate-status");
    const data = await res.json();

    const state = data.online ? data.state : "unknown";
    gateHeader.dataset.state = state;
    gateStateText.textContent = STATE_LABEL[state] || state.toUpperCase();
    espOnline.textContent = data.online ? "Online" : "Offline";
    presenceVal.textContent = data.online ? (data.presence ? "Detected" : "Empty") : "—";
  } catch {
    gateHeader.dataset.state = "unknown";
    gateStateText.textContent = STATE_LABEL.unknown;
    espOnline.textContent = "Offline";
    presenceVal.textContent = "—";
  }
}

// ---------- Current vehicles ----------

async function refreshCurrent() {
  try {
    const res = await fetch("/api/current");
    const rows = await res.json();
    currentCount.textContent = rows.length;

    if (rows.length === 0) {
      currentBody.innerHTML = emptyRow(2, "Parking lot is empty");
      return;
    }

    currentBody.innerHTML = rows.map(r => `
      <tr><td>${r.plate}</td><td>${r.checkin}</td></tr>
    `).join("");
  } catch {
    currentBody.innerHTML = emptyRow(2, "Cannot load data");
  }
}

// ---------- Search ----------

async function runSearch() {
  const plate = searchInput.value.trim();
  if (!plate) {
    searchBody.innerHTML = emptyRow(3, "Enter a plate to search");
    return;
  }
  searchBody.innerHTML = emptyRow(3, "Searching...");
  try {
    const res = await fetch(`/api/search?plate=${encodeURIComponent(plate)}`);
    const rows = await res.json();
    if (rows.length === 0) {
      searchBody.innerHTML = emptyRow(3, "No results found");
      return;
    }
    searchBody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.plate}</td>
        <td>${r.checkin}</td>
        <td>${r.checkout || "Still in lot"}</td>
      </tr>
    `).join("");
  } catch {
    searchBody.innerHTML = emptyRow(3, "Search error");
  }
}

searchBtn.addEventListener("click", runSearch);
searchInput.addEventListener("keydown", e => { if (e.key === "Enter") runSearch(); });

// ---------- Manual checkin/checkout ----------

function showManualMsg(text, ok) {
  manualMsg.textContent = text;
  manualMsg.className = "manual-msg " + (ok ? "ok" : "err");
}

async function manualAction(endpoint) {
  const plate = manualPlate.value.trim();
  if (!plate) {
    showManualMsg("Please enter a plate.", false);
    return;
  }
  try {
    const res = await fetch(`/api/vehicle/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plate })
    });
    const data = await res.json();
    if (data.ok) {
      showManualMsg(`${plate.toUpperCase()} succeeded.`, true);
      manualPlate.value = "";
      refreshCurrent();
      refreshLogs();
    } else {
      showManualMsg(data.error || "Something went wrong.", false);
    }
  } catch {
    showManualMsg("Cannot connect to server.", false);
  }
}

manualCheckin.addEventListener("click", () => manualAction("add"));
manualCheckout.addEventListener("click", () => manualAction("remove"));

// ---------- Logs ----------

async function refreshLogs() {
  try {
    const res = await fetch("/api/logs?limit=50");
    const rows = await res.json();
    logsCount.textContent = rows.length;

    if (rows.length === 0) {
      logsBody.innerHTML = emptyRow(3, "No history yet");
      return;
    }

    logsBody.innerHTML = rows.map(r => `
      <tr>
        <td>${r.plate}</td>
        <td class="${r.action === 'checkin' ? 'action-checkin' : 'action-checkout'}">
          ${r.action === 'checkin' ? 'Check-in' : 'Check-out'}
        </td>
        <td>${r.timestamp}</td>
      </tr>
    `).join("");
  } catch {
    logsBody.innerHTML = emptyRow(3, "Cannot load history");
  }
}

// ---------- Polling loop ----------

function refreshAll() {
  refreshGateStatus();
  refreshCurrent();
  refreshLogs();
}

refreshAll();
setInterval(refreshAll, REFRESH_MS);