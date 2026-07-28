const menuEl = document.getElementById("queryMenu");
const emptyState = document.getElementById("emptyState");
const receiptWrap = document.getElementById("receiptWrap");
const receiptTitle = document.getElementById("receiptTitle");
const loader = document.getElementById("loader");
const table = document.getElementById("resultTable");
const tableHead = document.getElementById("tableHead");
const tableBody = document.getElementById("tableBody");
const errorMsg = document.getElementById("errorMsg");
const emptyRows = document.getElementById("emptyRows");
const rowCount = document.getElementById("rowCount");
const dbDot = document.getElementById("dbDot");
const dbStatusText = document.getElementById("dbStatusText");

function humanizeHeader(col) {
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isNumericColumn(rows, col) {
  return rows.length > 0 && rows.every((r) => r[col] === null || typeof r[col] === "number");
}

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.status === "ok") {
      dbDot.classList.add("ok");
      dbStatusText.textContent = "Database connected";
    } else {
      throw new Error(data.detail || "unreachable");
    }
  } catch (err) {
    dbDot.classList.add("bad");
    dbStatusText.textContent = "Database unavailable";
  }
}

async function loadMenu() {
  const res = await fetch("/api/queries");
  const queries = await res.json();

  queries.forEach((q, idx) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "aisle-item";
    btn.dataset.key = q.key;
    btn.innerHTML = `<span class="aisle-item__num">${String(idx + 1).padStart(2, "0")}</span><span>${q.label}</span>`;
    btn.addEventListener("click", () => runQuery(q.key, q.label, btn));
    li.appendChild(btn);
    menuEl.appendChild(li);
  });
}

async function runQuery(key, label, btnEl) {
  document.querySelectorAll(".aisle-item").forEach((b) => b.classList.remove("active"));
  btnEl.classList.add("active");

  emptyState.hidden = true;
  receiptWrap.hidden = false;
  receiptTitle.textContent = label;

  table.hidden = true;
  errorMsg.hidden = true;
  emptyRows.hidden = true;
  loader.hidden = false;
  rowCount.textContent = "";

  try {
    const res = await fetch(`/api/query/${key}`);
    const data = await res.json();
    loader.hidden = true;

    if (!res.ok) {
      errorMsg.textContent = data.detail || data.error || "Something went wrong ringing this up.";
      errorMsg.hidden = false;
      rowCount.textContent = "0 ITEMS";
      return;
    }

    renderTable(data.columns, data.rows);
  } catch (err) {
    loader.hidden = true;
    errorMsg.textContent = "Could not reach the register (backend). Is the Flask server running?";
    errorMsg.hidden = false;
  }
}

function renderTable(columns, rows) {
  tableHead.innerHTML = "";
  tableBody.innerHTML = "";

  if (!rows || rows.length === 0) {
    emptyRows.hidden = false;
    rowCount.textContent = "0 ITEMS";
    return;
  }

  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = humanizeHeader(col);
    if (isNumericColumn(rows, col)) th.classList.add("num");
    tableHead.appendChild(th);
  });

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      let val = row[col];
      if (typeof val === "number") {
        val = Number.isInteger(val) ? val.toLocaleString() : val.toFixed(2);
        td.classList.add("num");
      } else if (val === null || val === undefined) {
        val = "\u2014";
      }
      td.textContent = val;
      tr.appendChild(td);
    });
    tableBody.appendChild(tr);
  });

  table.hidden = false;
  rowCount.textContent = `${rows.length} ITEM${rows.length === 1 ? "" : "S"}`;
}

checkHealth();
loadMenu();

// ---------- Mode tabs (Reports / Manage Data) ----------
const modeReportsBtn = document.getElementById("modeReportsBtn");
const modeManageBtn = document.getElementById("modeManageBtn");
const reportsLayout = document.getElementById("reportsLayout");
const manageLayout = document.getElementById("manageLayout");

function setMode(mode) {
  const isReports = mode === "reports";
  reportsLayout.hidden = !isReports;
  manageLayout.hidden = isReports;
  modeReportsBtn.classList.toggle("active", isReports);
  modeManageBtn.classList.toggle("active", !isReports);

  if (!isReports && window.initManageData) {
    window.initManageData();
  }
}

modeReportsBtn.addEventListener("click", () => setMode("reports"));
modeManageBtn.addEventListener("click", () => setMode("manage"));
