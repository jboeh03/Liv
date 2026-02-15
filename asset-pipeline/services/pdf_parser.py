"""
pdf_parser.py — Extract text from a PDF creative brief and use Claude
to return structured asset data as a JSON array.

HOW THE CLAUDE PROMPT WORKS
---------------------------
1. pdfplumber extracts every page of the uploaded PDF as plain text.
2. The concatenated text is sent to Claude along with a system prompt
   that lists the exact column names from config.TRACKING_SHEET_COLUMNS.
3. Claude returns a JSON array where each element is one asset row.

To adjust what Claude extracts, edit the SYSTEM_PROMPT and USER_PROMPT
templates below.  The {columns_json} placeholder is automatically
replaced with the current column list from config.py.
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any

import pdfplumber
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, TRACKING_SHEET_COLUMNS

logger = logging.getLogger(__name__)

# ---- Claude prompts (edit these to change extraction behaviour) ----------

# System prompt — tells Claude its role and the exact output format.
SYSTEM_PROMPT = """\
You are a marketing data extraction assistant.  You will receive the raw
text of a creative brief PDF.  Your job is to extract every individual
asset/ad described in the brief and return them as a JSON array.

Each object in the array MUST use the following keys (exactly as shown):
{columns_json}

Rules:
- Return ONLY valid JSON — no markdown fences, no commentary.
- If a field cannot be determined from the text, use an empty string "".
- Each object represents one distinct asset/ad placement.
- Dates should be in YYYY-MM-DD format when possible.
- "Asset Name" should be a short, descriptive label for the asset.
- "File Name" should be your best guess at the original file name
  referenced in the brief (or "" if not mentioned).
"""

# User prompt — wraps the extracted PDF text.
USER_PROMPT = """\
Extract all assets from the following creative brief text.
Return a JSON array of objects.

--- BEGIN BRIEF TEXT ---
{pdf_text}
--- END BRIEF TEXT ---
"""


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Use pdfplumber to pull plain text from every page of a PDF."""
    pages: list[str] = []
    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def parse_with_claude(pdf_text: str) -> list[dict[str, Any]]:
    """
    Send extracted PDF text to Claude and get back structured asset rows.

    Returns a list of dicts whose keys match TRACKING_SHEET_COLUMNS.
    """
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    columns_json = json.dumps(TRACKING_SHEET_COLUMNS, indent=2)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT.format(columns_json=columns_json),
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT.format(pdf_text=pdf_text),
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Claude sometimes wraps JSON in ```json ... ``` fences — strip them.
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]  # drop opening fence line
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    try:
        rows: list[dict[str, Any]] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Claude returned invalid JSON: %s", raw[:500])
        raise ValueError("Claude did not return valid JSON. Try again.") from exc

    # Ensure every row has all expected columns (fill missing with "").
    normalised: list[dict[str, Any]] = []
    for row in rows:
        normalised.append({col: row.get(col, "") for col in TRACKING_SHEET_COLUMNS})
    return normalised


async def parse_pdf(file_bytes: bytes) -> list[dict[str, Any]]:
    """
    High-level entry point: extract text then parse with Claude.

    Returns a list of dicts ready for the review table.
    """
    pdf_text = extract_text_from_pdf(file_bytes)
    if not pdf_text.strip():
        raise ValueError("Could not extract any text from the PDF.")
    return parse_with_claude(pdf_text)
