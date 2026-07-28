// Generic CRUD UI: works for any table exposed by /api/tables*, driven
// entirely by the schema the backend returns (no per-table frontend code).

const tableMenuEl = document.getElementById("tableMenu");
const crudEmptyState = document.getElementById("crudEmptyState");
const crudPanel = document.getElementById("crudPanel");
const crudTableTitle = document.getElementById("crudTableTitle");
const crudAddBtn = document.getElementById("crudAddBtn");
const crudFormWrap = document.getElementById("crudFormWrap");
const crudForm = document.getElementById("crudForm");
const crudFormFields = document.getElementById("crudFormFields");
const crudCancelBtn = document.getElementById("crudCancelBtn");
const crudMsg = document.getElementById("crudMsg");
const crudTableHead = document.getElementById("crudTableHead");
const crudTableBody = document.getElementById("crudTableBody");
const crudEmptyRows = document.getElementById("crudEmptyRows");

let manageInitialized = false;
let currentTableKey = null;
let currentSchema = null; // { key, label, pk, columns }
let editingPk = null; // null = creating a new row

function humanize(col) {
  return col.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function showCrudMsg(text, isError) {
  crudMsg.textContent = text;
  crudMsg.hidden = !text;
  crudMsg.classList.toggle("crud-msg--error", !!isError);
}

async function loadTableMenu() {
  tableMenuEl.innerHTML = "";
  const res = await fetch("/api/tables");
  const tables = await res.json();

  tables.forEach((t, idx) => {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "aisle-item";
    btn.dataset.key = t.key;
    btn.innerHTML = `<span class="aisle-item__num">${String(idx + 1).padStart(2, "0")}</span><span>${t.label}</span>`;
    btn.addEventListener("click", () => selectTable(t.key, btn));
    li.appendChild(btn);
    tableMenuEl.appendChild(li);
  });
}

async function selectTable(key, btnEl) {
  document.querySelectorAll("#tableMenu .aisle-item").forEach((b) => b.classList.remove("active"));
  btnEl.classList.add("active");

  currentTableKey = key;
  editingPk = null;
  crudEmptyState.hidden = true;
  crudPanel.hidden = false;
  crudFormWrap.hidden = true;
  showCrudMsg("", false);

  crudTableTitle.textContent = "Loading\u2026";

  try {
    const schemaRes = await fetch(`/api/tables/${key}/schema`);
    const schema = await schemaRes.json();
    if (!schemaRes.ok) throw new Error(schema.error || "Could not load schema");
    currentSchema = schema;
    crudTableTitle.textContent = schema.label;
    await loadRows();
  } catch (err) {
    crudTableTitle.textContent = "Error";
    showCrudMsg(err.message || "Could not load this table.", true);
  }
}

async function loadRows() {
  const res = await fetch(`/api/tables/${currentTableKey}`);
  const data = await res.json();
  if (!res.ok) {
    showCrudMsg(data.error || "Could not load rows.", true);
    return;
  }
  renderRows(data.rows);
}

function renderRows(rows) {
  crudTableHead.innerHTML = "";
  crudTableBody.innerHTML = "";

  const pk = currentSchema.pk;
  const columns = [pk, ...currentSchema.columns.map((c) => c.key)];

  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = humanize(col);
    crudTableHead.appendChild(th);
  });
  const actionsTh = document.createElement("th");
  actionsTh.textContent = "Actions";
  crudTableHead.appendChild(actionsTh);

  if (!rows || rows.length === 0) {
    crudEmptyRows.hidden = false;
    return;
  }
  crudEmptyRows.hidden = true;

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      let val = row[col];
      if (val === null || val === undefined) val = "\u2014";
      td.textContent = val;
      tr.appendChild(td);
    });

    const actionsTd = document.createElement("td");
    actionsTd.className = "crud-actions";

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "btn btn--small";
    editBtn.textContent = "Edit";
    editBtn.addEventListener("click", () => openForm(row));

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "btn btn--small btn--danger";
    delBtn.textContent = "Delete";
    delBtn.addEventListener("click", () => deleteRow(row[pk]));

    actionsTd.appendChild(editBtn);
    actionsTd.appendChild(delBtn);
    tr.appendChild(actionsTd);

    crudTableBody.appendChild(tr);
  });
}

function fieldInput(col, value) {
  const id = `crud-field-${col.key}`;
  let input;

  if (col.type === "fk" || col.type === "enum") {
    input = document.createElement("select");
    input.id = id;
    input.name = col.key;

    if (!col.required) {
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "\u2014 none \u2014";
      input.appendChild(blank);
    }

    const options = col.type === "fk"
      ? col.options.map((o) => ({ value: o.value, label: o.label }))
      : col.options.map((o) => ({ value: o, label: o }));

    options.forEach((opt) => {
      const optionEl = document.createElement("option");
      optionEl.value = opt.value;
      optionEl.textContent = opt.label;
      if (value !== undefined && String(value) === String(opt.value)) optionEl.selected = true;
      input.appendChild(optionEl);
    });
  } else {
    input = document.createElement("input");
    input.id = id;
    input.name = col.key;
    if (col.type === "int") {
      input.type = "number";
      input.step = "1";
    } else if (col.type === "float") {
      input.type = "number";
      input.step = "any";
    } else if (col.type === "date") {
      input.type = "date";
    } else {
      input.type = "text";
    }
    if (value !== undefined && value !== null) input.value = value;
  }

  input.required = !!col.required;
  return input;
}

function openForm(row) {
  editingPk = row ? row[currentSchema.pk] : null;
  crudFormFields.innerHTML = "";
  showCrudMsg("", false);

  currentSchema.columns.forEach((col) => {
    const wrap = document.createElement("label");
    wrap.className = "crud-form__field";
    wrap.textContent = col.label + (col.required ? " *" : "");
    const input = fieldInput(col, row ? row[col.key] : undefined);
    wrap.appendChild(input);
    crudFormFields.appendChild(wrap);
  });

  document.getElementById("crudSaveBtn").textContent = row ? "Save changes" : "Add row";
  crudFormWrap.hidden = false;
}

crudAddBtn.addEventListener("click", () => openForm(null));
crudCancelBtn.addEventListener("click", () => {
  crudFormWrap.hidden = true;
  showCrudMsg("", false);
});

crudForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {};
  currentSchema.columns.forEach((col) => {
    const el = document.getElementById(`crud-field-${col.key}`);
    body[col.key] = el.value;
  });

  const isEdit = editingPk !== null;
  const url = isEdit
    ? `/api/tables/${currentTableKey}/${editingPk}`
    : `/api/tables/${currentTableKey}`;

  try {
    const res = await fetch(url, {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong saving this row.");

    crudFormWrap.hidden = true;
    showCrudMsg(isEdit ? "Row updated." : "Row added.", false);
    await loadRows();
  } catch (err) {
    showCrudMsg(err.message, true);
  }
});

async function deleteRow(pkValue) {
  if (!confirm("Delete this row? This can't be undone.")) return;

  try {
    const res = await fetch(`/api/tables/${currentTableKey}/${pkValue}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not delete this row.");
    showCrudMsg("Row deleted.", false);
    await loadRows();
  } catch (err) {
    showCrudMsg(err.message, true);
  }
}

// Called by script.js the first time the "Manage Data" tab is opened.
window.initManageData = function initManageData() {
  if (manageInitialized) return;
  manageInitialized = true;
  loadTableMenu();
};
