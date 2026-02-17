/**
 * app.js — Frontend logic for the Asset Pipeline single-page app.
 *
 * Flow: Step 1 (Upload PDF) → Step 2 (Review & Edit tabs) → Step 3 (Download)
 */

"use strict";

// ── State ────────────────────────────────────────────────────────────
let tabTemplates = {};   // from /api/config
let tabsData = {};       // { "TabName": { headers: [...], rows: [...] }, ... }
let activeTab = "";      // currently selected tab name

// ── DOM refs ─────────────────────────────────────────────────────────
const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Steps
const stepSections = { 1: $("#step-1"), 2: $("#step-2"), 3: $("#step-3") };
const stepIndicators = $$(".step");

// Step 1
const dropZone   = $("#drop-zone");
const pdfInput   = $("#pdf-input");
const pdfStatus  = $("#pdf-status");

// Step 2
const tabBar     = $("#tab-bar");
const tabContent  = $("#tab-content");
const btnAddRow   = $("#btn-add-row");
const btnBackStep1 = $("#btn-back-step1");
const btnNextStep3 = $("#btn-next-step3");

// Step 3
const btnDownloadXlsx = $("#btn-download-xlsx");
const btnDownloadCsv  = $("#btn-download-csv");
const downloadStatus  = $("#download-status");
const btnBackStep2    = $("#btn-back-step2");


// ── Helpers ──────────────────────────────────────────────────────────

function showStatus(el, text, type) {
  el.textContent = text;
  el.className = `status-message ${type}`;
  el.classList.remove("hidden");
}

function hideStatus(el) {
  el.classList.add("hidden");
}

function goToStep(n) {
  Object.values(stepSections).forEach((s) => s.classList.add("hidden"));
  stepSections[n].classList.remove("hidden");

  stepIndicators.forEach((ind) => {
    const s = parseInt(ind.dataset.step, 10);
    ind.classList.remove("active", "completed");
    if (s < n) ind.classList.add("completed");
    if (s === n) ind.classList.add("active");
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}


// ── Init ─────────────────────────────────────────────────────────────

async function init() {
  try {
    const resp = await fetch("/api/config");
    const data = await resp.json();
    tabTemplates = data.tab_templates || {};
  } catch {
    console.error("Failed to load config");
  }
}

init();


// ══════════════════════════════════════════════════════════════════════
// STEP 1 — PDF Upload
// ══════════════════════════════════════════════════════════════════════

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const files = e.dataTransfer.files;
  if (files.length > 0) uploadPdf(files[0]);
});

dropZone.addEventListener("click", () => pdfInput.click());

pdfInput.addEventListener("change", () => {
  if (pdfInput.files.length > 0) uploadPdf(pdfInput.files[0]);
});

async function uploadPdf(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showStatus(pdfStatus, "Please select a PDF file.", "error");
    return;
  }

  showStatus(pdfStatus, `Uploading and parsing "${file.name}"... This may take a moment.`, "loading");

  const form = new FormData();
  form.append("file", file);

  try {
    const resp = await fetch("/api/parse-pdf", { method: "POST", body: form });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || `Request failed (${resp.status})`);

    tabsData = data.tabs || {};

    const tabCount = Object.keys(tabsData).length;
    const rowCount = Object.values(tabsData).reduce((sum, t) => sum + (t.rows || []).length, 0);
    showStatus(pdfStatus, `Extracted ${rowCount} row(s) across ${tabCount} tab(s) from "${file.name}".`, "success");

    // Auto-advance to edit step
    renderTabs();
    goToStep(2);
  } catch (err) {
    showStatus(pdfStatus, `Error: ${err.message}`, "error");
  }
}


// ══════════════════════════════════════════════════════════════════════
// STEP 2 — Review & Edit (Tabbed Interface)
// ══════════════════════════════════════════════════════════════════════

function renderTabs() {
  const tabNames = Object.keys(tabsData);
  if (tabNames.length === 0) {
    tabBar.innerHTML = "";
    tabContent.innerHTML = '<p class="empty-state">No data extracted. Go back and try another PDF.</p>';
    return;
  }

  // Set active tab
  if (!activeTab || !tabsData[activeTab]) {
    activeTab = tabNames[0];
  }

  // Render tab bar
  tabBar.innerHTML = tabNames
    .map((name) => {
      const cls = name === activeTab ? "tab active" : "tab";
      const rowCount = (tabsData[name].rows || []).length;
      return `<button class="${cls}" data-tab="${escapeHtml(name)}">${escapeHtml(name)} <span class="tab-count">(${rowCount})</span></button>`;
    })
    .join("");

  // Tab click handlers
  tabBar.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      saveCurrentEdits();
      activeTab = btn.dataset.tab;
      renderTabs();
    });
  });

  // Render active tab's table
  renderTabTable();
}

function renderTabTable() {
  const tab = tabsData[activeTab];
  if (!tab) {
    tabContent.innerHTML = '<p class="empty-state">No data for this tab.</p>';
    return;
  }

  const headers = tab.headers || [];
  const rows = tab.rows || [];

  let html = '<div class="table-wrapper"><table>';

  // Header row
  html += "<thead><tr>";
  html += '<th class="row-actions-header">#</th>';
  headers.forEach((h) => {
    html += `<th>${escapeHtml(h)}</th>`;
  });
  html += "</tr></thead>";

  // Data rows
  html += "<tbody>";
  rows.forEach((row, rowIdx) => {
    html += `<tr data-row="${rowIdx}">`;
    html += `<td class="row-num">
      <span class="row-index">${rowIdx + 1}</span>
      <button class="btn-delete-row" data-row="${rowIdx}" title="Delete row">&times;</button>
    </td>`;
    headers.forEach((h) => {
      const val = row[h] || "";
      html += `<td class="editable" data-col="${escapeHtml(h)}" data-row="${rowIdx}">${escapeHtml(String(val))}</td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table></div>";

  tabContent.innerHTML = html;

  // Make cells editable on click
  tabContent.querySelectorAll("td.editable").forEach((td) => {
    td.addEventListener("click", () => startEditing(td));
  });

  // Delete row buttons
  tabContent.querySelectorAll(".btn-delete-row").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const rowIdx = parseInt(btn.dataset.row, 10);
      tabsData[activeTab].rows.splice(rowIdx, 1);
      renderTabs();
    });
  });
}

function startEditing(td) {
  // Don't double-edit
  if (td.querySelector("textarea")) return;

  const currentValue = tabsData[activeTab].rows[td.dataset.row][td.dataset.col] || "";

  const textarea = document.createElement("textarea");
  textarea.className = "cell-editor";
  textarea.value = currentValue;
  td.textContent = "";
  td.appendChild(textarea);
  textarea.focus();
  textarea.select();

  // Auto-resize
  autoResize(textarea);
  textarea.addEventListener("input", () => autoResize(textarea));

  // Save on blur or Enter (Shift+Enter for newline)
  const save = () => {
    const newValue = textarea.value;
    tabsData[activeTab].rows[td.dataset.row][td.dataset.col] = newValue;
    td.textContent = newValue;
    // Re-attach click handler
    td.addEventListener("click", () => startEditing(td));
  };

  textarea.addEventListener("blur", save);
  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      textarea.blur();
    }
    if (e.key === "Escape") {
      textarea.value = currentValue;
      textarea.blur();
    }
  });
}

function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
}

function saveCurrentEdits() {
  // Force-save any open textarea editors
  tabContent.querySelectorAll("textarea.cell-editor").forEach((ta) => {
    ta.blur();
  });
}

// Add row
btnAddRow.addEventListener("click", () => {
  if (!activeTab || !tabsData[activeTab]) return;
  saveCurrentEdits();
  const headers = tabsData[activeTab].headers || [];
  const emptyRow = {};
  headers.forEach((h) => (emptyRow[h] = ""));
  tabsData[activeTab].rows.push(emptyRow);
  renderTabs();

  // Scroll to bottom of table
  const wrapper = tabContent.querySelector(".table-wrapper");
  if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
});

btnBackStep1.addEventListener("click", () => goToStep(1));
btnNextStep3.addEventListener("click", () => {
  saveCurrentEdits();
  goToStep(3);
});


// ══════════════════════════════════════════════════════════════════════
// STEP 3 — Download
// ══════════════════════════════════════════════════════════════════════

async function downloadFile(url, defaultFilename) {
  hideStatus(downloadStatus);

  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tabs: tabsData }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `Download failed (${resp.status})`);
    }

    // Get filename from Content-Disposition header or use default
    const disposition = resp.headers.get("Content-Disposition");
    let filename = defaultFilename;
    if (disposition) {
      const match = disposition.match(/filename[^;=\n]*=(['""]?)([^'"";\n]*)\1/);
      if (match) filename = match[2];
    }

    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);

    showStatus(downloadStatus, `Downloaded "${filename}" successfully.`, "success");
  } catch (err) {
    showStatus(downloadStatus, `Error: ${err.message}`, "error");
  }
}

btnDownloadXlsx.addEventListener("click", () => {
  downloadFile("/api/download-xlsx", "tracking_sheet.xlsx");
});

btnDownloadCsv.addEventListener("click", () => {
  downloadFile("/api/download-csv", "tracking_sheets.zip");
});

btnBackStep2.addEventListener("click", () => goToStep(2));
