/**
 * app.js — Frontend logic for the Asset Pipeline single-page app.
 *
 * Flow: Step 1 (Upload PDF) → Step 2 (Load Assets) → Step 3 (Review) → Step 4 (Process)
 */

"use strict";

// ── State ────────────────────────────────────────────────────────────
let config = {};          // populated from /api/config
let parsedRows = [];      // rows returned from PDF parsing
let matchedRows = [];     // rows with file-match data
let availableFiles = [];  // files found in asset folder

// ── DOM refs ─────────────────────────────────────────────────────────
const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Steps
const stepSections = { 1: $("#step-1"), 2: $("#step-2"), 3: $("#step-3"), 4: $("#step-4") };
const stepIndicators = $$(".step");

// Step 1
const dropZone   = $("#drop-zone");
const pdfInput   = $("#pdf-input");
const pdfStatus  = $("#pdf-status");
const parsedPreview = $("#parsed-preview");
const parsedHeader  = $("#parsed-header");
const parsedBody    = $("#parsed-body");
const btnNextStep2  = $("#btn-next-step2");

// Step 2
const folderPath   = $("#folder-path");
const btnLoadFolder = $("#btn-load-folder");
const folderStatus  = $("#folder-status");
const folderFiles   = $("#folder-files");
const fileList      = $("#file-list");

// Step 3
const reviewHeader = $("#review-header");
const reviewBody   = $("#review-body");
const btnBackStep2 = $("#btn-back-step2");
const btnNextStep4 = $("#btn-next-step4");

// Step 4
const sharepointToggle = $("#sharepoint-toggle");
const btnProcess    = $("#btn-process");
const processLog    = $("#process-log");
const logOutput     = $("#log-output");
const processSummary = $("#process-summary");
const summaryContent = $("#summary-content");


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
  // Hide all
  Object.values(stepSections).forEach((s) => s.classList.add("hidden"));
  stepSections[n].classList.remove("hidden");

  // Update indicators
  stepIndicators.forEach((ind) => {
    const s = parseInt(ind.dataset.step, 10);
    ind.classList.remove("active", "completed");
    if (s < n) ind.classList.add("completed");
    if (s === n) ind.classList.add("active");
  });
}

async function apiPost(url, body, isFormData = false) {
  const opts = { method: "POST" };
  if (isFormData) {
    opts.body = body;
  } else {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const resp = await fetch(url, opts);
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.detail || `Request failed (${resp.status})`);
  }
  return data;
}

function confidenceBadge(score) {
  if (score >= 80) return `<span class="badge high">${score}%</span>`;
  if (score >= 60) return `<span class="badge medium">${score}%</span>`;
  if (score > 0)   return `<span class="badge low">${score}%</span>`;
  return `<span class="badge none">No match</span>`;
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
    config = await resp.json();
  } catch {
    console.error("Failed to load config");
  }
}

init();


// ══════════════════════════════════════════════════════════════════════
// STEP 1 — PDF Upload
// ══════════════════════════════════════════════════════════════════════

// Drag & drop
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
  parsedPreview.classList.add("hidden");

  const form = new FormData();
  form.append("file", file);

  try {
    const data = await apiPost("/api/parse-pdf", form, true);
    parsedRows = data.rows;

    showStatus(pdfStatus, `Extracted ${data.count} asset(s) from "${file.name}".`, "success");
    renderParsedTable();
    parsedPreview.classList.remove("hidden");
  } catch (err) {
    showStatus(pdfStatus, `Error: ${err.message}`, "error");
  }
}

function renderParsedTable() {
  const cols = config.columns || Object.keys(parsedRows[0] || {});

  parsedHeader.innerHTML = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  parsedBody.innerHTML = parsedRows
    .map(
      (row) =>
        `<tr>${cols.map((c) => `<td>${escapeHtml(String(row[c] || ""))}</td>`).join("")}</tr>`
    )
    .join("");
}

btnNextStep2.addEventListener("click", () => goToStep(2));


// ══════════════════════════════════════════════════════════════════════
// STEP 2 — Load Asset Folder
// ══════════════════════════════════════════════════════════════════════

btnLoadFolder.addEventListener("click", loadFolder);
folderPath.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadFolder();
});

async function loadFolder() {
  const path = folderPath.value.trim();
  if (!path) {
    showStatus(folderStatus, "Please enter a folder path.", "error");
    return;
  }

  showStatus(folderStatus, "Scanning folder and matching files...", "loading");
  folderFiles.classList.add("hidden");

  try {
    const data = await apiPost("/api/load-folder", { folder_path: path });
    matchedRows = data.rows;
    availableFiles = data.files;

    // Show file list
    fileList.innerHTML = data.files
      .map((f) => `<li>${escapeHtml(f.name)}</li>`)
      .join("");
    folderFiles.classList.remove("hidden");

    showStatus(
      folderStatus,
      `Found ${data.files.length} file(s). Matched against ${data.count} row(s).`,
      "success"
    );

    // Auto-advance to review
    renderReviewTable();
    goToStep(3);
  } catch (err) {
    showStatus(folderStatus, `Error: ${err.message}`, "error");
  }
}


// ══════════════════════════════════════════════════════════════════════
// STEP 3 — Review Matches
// ══════════════════════════════════════════════════════════════════════

function renderReviewTable() {
  const cols = config.columns || [];

  // Header: data columns + Matched File + Confidence
  let headerHtml = cols.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
  headerHtml += `<th>Matched File</th><th>Confidence</th>`;
  reviewHeader.innerHTML = headerHtml;

  // Build file options HTML (for dropdown)
  const fileOptions = availableFiles
    .map((f) => `<option value="${escapeHtml(f.name)}" data-path="${escapeHtml(f.path)}">${escapeHtml(f.name)}</option>`)
    .join("");

  reviewBody.innerHTML = matchedRows
    .map((row, i) => {
      let rowHtml = cols.map((c) => `<td>${escapeHtml(String(row[c] || ""))}</td>`).join("");

      // Dropdown for file matching
      const selected = row._matched_file || "";
      rowHtml += `<td>
        <select class="review-select" data-row="${i}" onchange="onMatchChange(this)">
          <option value="">-- None --</option>
          ${fileOptions}
        </select>
      </td>`;
      rowHtml += `<td>${confidenceBadge(row._match_score)}</td>`;

      return `<tr>${rowHtml}</tr>`;
    })
    .join("");

  // Pre-select current matches in dropdowns
  reviewBody.querySelectorAll("select.review-select").forEach((sel) => {
    const idx = parseInt(sel.dataset.row, 10);
    const matched = matchedRows[idx]._matched_file || "";
    if (matched) sel.value = matched;
  });
}

// Global handler for match-change dropdowns
window.onMatchChange = async function (sel) {
  const rowIdx = parseInt(sel.dataset.row, 10);
  const fileName = sel.value;
  const option = sel.selectedOptions[0];
  const filePath = option ? option.dataset.path || "" : "";

  // Update local state
  matchedRows[rowIdx]._matched_file = fileName;
  matchedRows[rowIdx]._matched_path = filePath;
  matchedRows[rowIdx]._match_score = fileName ? 100 : 0;

  // Persist to backend
  try {
    await apiPost("/api/update-match", {
      row_index: rowIdx,
      matched_file: fileName,
      matched_path: filePath,
    });
  } catch (err) {
    console.error("Failed to update match:", err);
  }

  // Re-render confidence badge
  const badgeCell = sel.parentElement.nextElementSibling;
  if (badgeCell) {
    badgeCell.innerHTML = confidenceBadge(matchedRows[rowIdx]._match_score);
  }
};

btnBackStep2.addEventListener("click", () => goToStep(2));
btnNextStep4.addEventListener("click", () => goToStep(4));


// ══════════════════════════════════════════════════════════════════════
// STEP 4 — Process
// ══════════════════════════════════════════════════════════════════════

btnProcess.addEventListener("click", processAssets);

async function processAssets() {
  btnProcess.disabled = true;
  processLog.classList.remove("hidden");
  processSummary.classList.add("hidden");
  logOutput.textContent = "Processing...\n";

  try {
    const data = await apiPost("/api/process", {
      rows: matchedRows,
      upload_to_sharepoint: sharepointToggle.checked,
    });

    // Display log
    logOutput.textContent = data.log.join("\n");

    // Display summary
    let html = `<strong>${data.files_processed}</strong> file(s) processed.<br>`;
    html += `Output folder: <code>${escapeHtml(data.output_folder)}</code><br>`;
    html += `Tracking sheet: <code>${escapeHtml(data.tracking_sheet)}</code>`;

    if (data.sharepoint_urls && data.sharepoint_urls.length > 0) {
      html += `<br><strong>${data.sharepoint_urls.length}</strong> file(s) uploaded to SharePoint.`;
    }

    summaryContent.innerHTML = html;
    processSummary.classList.remove("hidden");
  } catch (err) {
    logOutput.textContent += `\nError: ${err.message}`;
  } finally {
    btnProcess.disabled = false;
  }
}
