"""
main.py — FastAPI application entry point for the Asset Pipeline.

Run with:  python main.py
Or:        uvicorn main:app --reload
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from services import pdf_parser, sheet_writer

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
app = FastAPI(title="Asset Pipeline", version="2.0.0")

# Serve the frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ---------------------------------------------------------------------------
# In-memory session state (single-user local app)
# ---------------------------------------------------------------------------
_state: dict[str, Any] = {
    "tabs": {},  # multi-tab data: { "TabName": { "headers": [...], "rows": [...] }, ... }
}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class TabsData(BaseModel):
    tabs: dict[str, Any]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Serve the main HTML page."""
    return FileResponse("frontend/index.html")


@app.get("/api/config")
async def get_config():
    """Return the tab templates so the frontend knows what's available."""
    return {
        "tab_templates": config.TAB_TEMPLATES,
    }


# ---- Step 1: PDF Upload + Parsing ----------------------------------------

@app.post("/api/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    """Upload a PDF brief and extract structured multi-tab data via Claude."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    try:
        file_bytes = await file.read()
        result = await pdf_parser.parse_pdf(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("PDF parsing failed")
        raise HTTPException(status_code=500, detail=f"PDF parsing error: {exc}")

    _state["tabs"] = result["tabs"]
    return result


# ---- Step 2: Edit (handled entirely in the frontend) ----------------------
# The frontend sends the final edited data when the user downloads.


# ---- Step 3: Download ----------------------------------------------------

@app.post("/api/download-xlsx")
async def download_xlsx(data: TabsData):
    """Generate and return a multi-tab XLSX file from the provided data."""
    output_dir = Path(config.LOCAL_OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_path = output_dir / "tracking_sheet.xlsx"

    try:
        sheet_writer.write_multi_tab_xlsx(data.tabs, sheet_path)
    except Exception as exc:
        logger.exception("XLSX generation failed")
        raise HTTPException(status_code=500, detail=f"XLSX generation error: {exc}")

    return FileResponse(
        path=str(sheet_path),
        filename="tracking_sheet.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.post("/api/download-csv")
async def download_csv(data: TabsData):
    """Generate and return a ZIP of CSV files (one per tab)."""
    try:
        zip_bytes = sheet_writer.write_csv_zip(data.tabs)
    except Exception as exc:
        logger.exception("CSV generation failed")
        raise HTTPException(status_code=500, detail=f"CSV generation error: {exc}")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=tracking_sheets.zip"},
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Asset Pipeline on http://%s:%s", config.HOST, config.PORT)
    uvicorn.run(app, host=config.HOST, port=config.PORT)
