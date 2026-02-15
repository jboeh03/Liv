"""
main.py — FastAPI application entry point for the Asset Pipeline.

Run with:  python main.py
Or:        uvicorn main:app --reload
"""

from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from services import pdf_parser, file_matcher, sheet_writer, sharepoint

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("asset-pipeline")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Asset Pipeline", version="1.0.0")

# Serve the frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ---------------------------------------------------------------------------
# In-memory session state (single-user local app)
# ---------------------------------------------------------------------------
_state: dict[str, Any] = {
    "parsed_rows": [],       # list[dict] from PDF parsing
    "folder_path": "",       # user-provided asset folder
    "matched_rows": [],      # rows with _matched_file etc.
    "available_files": [],   # files found in folder
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class FolderRequest(BaseModel):
    folder_path: str


class ProcessRequest(BaseModel):
    rows: list[dict[str, Any]]
    upload_to_sharepoint: bool = False


class MatchUpdateRequest(BaseModel):
    row_index: int
    matched_file: str
    matched_path: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("frontend/index.html")


@app.get("/api/config")
async def get_config():
    """Return current configuration for the frontend."""
    return {
        "columns": config.TRACKING_SHEET_COLUMNS,
        "naming_convention": config.NAMING_CONVENTION,
        "output_folder": config.LOCAL_OUTPUT_FOLDER,
    }


# ---- Step 1: PDF Upload + Parsing ----------------------------------------

@app.post("/api/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    """Upload a PDF brief and extract structured asset rows via Claude."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    try:
        file_bytes = await file.read()
        rows = await pdf_parser.parse_pdf(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("PDF parsing failed")
        raise HTTPException(status_code=500, detail=f"PDF parsing error: {exc}")

    _state["parsed_rows"] = rows
    return {"rows": rows, "count": len(rows)}


# ---- Step 2: Asset Folder Ingestion + Matching ---------------------------

@app.post("/api/load-folder")
async def load_folder(req: FolderRequest):
    """Scan a local folder and fuzzy-match files to parsed rows."""
    folder = req.folder_path.strip()
    if not folder:
        raise HTTPException(status_code=400, detail="Folder path is required.")

    if not _state["parsed_rows"]:
        raise HTTPException(
            status_code=400,
            detail="No parsed rows. Upload and parse a PDF first (Step 1).",
        )

    try:
        result = file_matcher.match_files(_state["parsed_rows"], folder)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    _state["folder_path"] = folder
    _state["matched_rows"] = result["rows"]
    _state["available_files"] = result["files"]

    return {
        "rows": result["rows"],
        "files": result["files"],
        "count": len(result["rows"]),
    }


@app.post("/api/update-match")
async def update_match(req: MatchUpdateRequest):
    """Manually update a file match for a specific row."""
    if req.row_index < 0 or req.row_index >= len(_state["matched_rows"]):
        raise HTTPException(status_code=400, detail="Invalid row index.")

    _state["matched_rows"][req.row_index]["_matched_file"] = req.matched_file
    _state["matched_rows"][req.row_index]["_matched_path"] = req.matched_path
    _state["matched_rows"][req.row_index]["_match_score"] = 100  # manual = full confidence

    return {"ok": True}


# ---- Step 3: Process -----------------------------------------------------

def _build_filename(row: dict[str, Any], original_ext: str) -> str:
    """
    Build a renamed filename from the NAMING_CONVENTION template and row data.

    Placeholders like {asset_name} are matched to column values by
    lowercasing column names and replacing spaces with underscores.
    """
    template = config.NAMING_CONVENTION
    # Build a lookup: "asset_name" -> row["Asset Name"]
    lookup: dict[str, str] = {}
    for col in config.TRACKING_SHEET_COLUMNS:
        key = col.lower().replace(" ", "_")
        value = str(row.get(col, "unknown")).strip() or "unknown"
        lookup[key] = value

    # Replace placeholders
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return lookup.get(key, "unknown")

    name = re.sub(r"\{(\w+)\}", replacer, template)

    # Sanitise: keep alphanumerics, hyphens, underscores
    name = re.sub(r"[^\w\-]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")

    return f"{name}{original_ext}"


@app.post("/api/process")
async def process_assets(req: ProcessRequest):
    """
    Process confirmed assets:
    1. Rename files per naming convention
    2. Copy to output folder
    3. Generate Excel tracking sheet
    4. Optionally upload to SharePoint
    """
    rows = req.rows
    if not rows:
        raise HTTPException(status_code=400, detail="No rows to process.")

    output_dir = Path(config.LOCAL_OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)

    log: list[str] = []
    processed_files: list[Path] = []

    for i, row in enumerate(rows):
        source_path = row.get("_matched_path", "")
        if not source_path or not Path(source_path).is_file():
            log.append(f"Row {i + 1}: Skipped — no matched file.")
            continue

        source = Path(source_path)
        new_name = _build_filename(row, source.suffix)
        dest = output_dir / new_name

        # Avoid overwrites by appending a counter
        counter = 1
        base_dest = dest
        while dest.exists():
            dest = base_dest.with_stem(f"{base_dest.stem}_{counter}")
            counter += 1

        shutil.copy2(source, dest)
        processed_files.append(dest)

        # Update the row's File Name to the final renamed name
        row["File Name"] = dest.name

        log.append(f"Row {i + 1}: {source.name} → {dest.name}")

    # Generate tracking spreadsheet
    sheet_path = output_dir / "tracking_sheet.xlsx"
    # Strip internal fields before writing
    clean_rows = [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in rows
    ]
    sheet_writer.write_tracking_sheet(clean_rows, sheet_path)
    log.append(f"Tracking sheet saved → {sheet_path}")
    processed_files.append(sheet_path)

    # SharePoint upload
    sharepoint_urls: list[str] = []
    if req.upload_to_sharepoint:
        try:
            sharepoint_urls = await sharepoint.upload_files(
                processed_files,
                log_callback=lambda msg: log.append(msg),
            )
            log.append(f"SharePoint upload complete — {len(sharepoint_urls)} files uploaded.")
        except Exception as exc:
            logger.exception("SharePoint upload failed")
            log.append(f"SharePoint upload failed: {exc}")

    return {
        "log": log,
        "output_folder": str(output_dir.resolve()),
        "files_processed": len(processed_files) - 1,  # exclude the spreadsheet
        "tracking_sheet": str(sheet_path.resolve()),
        "sharepoint_urls": sharepoint_urls,
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Asset Pipeline on http://%s:%s", config.HOST, config.PORT)
    uvicorn.run(app, host=config.HOST, port=config.PORT)
