"""
pdf_parser.py — Extract text from a PDF creative brief and use Claude
to return structured, multi-tab asset data as JSON.

HOW THE CLAUDE PROMPT WORKS
---------------------------
1. pdfplumber extracts every page of the uploaded PDF as plain text.
2. The concatenated text is sent to Claude along with a system prompt
   that describes all available tab templates from config.TAB_TEMPLATES.
3. Claude decides which tabs are relevant to the brief, then returns
   a JSON object keyed by tab name, each containing "headers" and "rows".

To adjust what Claude extracts, edit the SYSTEM_PROMPT and USER_PROMPT
templates below.
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any

import pdfplumber
from anthropic import Anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, TAB_TEMPLATES

logger = logging.getLogger(__name__)

# ---- Claude prompts (edit these to change extraction behaviour) ----------

SYSTEM_PROMPT = """\
You are a marketing data extraction assistant.  You will receive the raw
text of a creative brief PDF.  Your job is to:

1. Determine which of the available spreadsheet tabs are relevant to this
   brief based on its content (e.g., if the brief describes paid social
   assets, include the "Paid Social Trafficking" tab; if it has
   programmatic display, include "Prog", etc.).

2. For each relevant tab, extract every individual asset/ad described in
   the brief and populate the rows using that tab's column headers.

AVAILABLE TAB TEMPLATES (tab name → column headers):
{templates_json}

OUTPUT FORMAT — return ONLY valid JSON (no markdown fences, no commentary)
with this structure:

{{
  "tabs": {{
    "<TabName>": {{
      "headers": ["col1", "col2", ...],
      "rows": [
        {{"col1": "value", "col2": "value", ...}},
        ...
      ]
    }},
    ...
  }}
}}

Rules:
- Only include tabs that are relevant to this brief.
- Use the exact header names from the template for each tab.
- If a field cannot be determined from the text, use an empty string "".
- Each row represents one distinct asset/ad placement.
- Dates should be in YYYY-MM-DD format when possible.
- Extract ALL copy text, headlines, descriptions, CTAs, landing pages,
  disclaimers, etc. exactly as written in the brief — do not summarise.
- For the "Paid Social Trafficking" tab, populate character count fields
  by counting the characters in the corresponding text field.
- If the brief contains asset file names, include them in the appropriate
  file name column.
- Be thorough — capture every asset variation and placement mentioned.
"""

USER_PROMPT = """\
Extract all assets from the following creative brief text.
Return a JSON object with only the relevant tabs populated.

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


def parse_with_claude(pdf_text: str) -> dict[str, Any]:
    """
    Send extracted PDF text to Claude and get back multi-tab structured data.

    Returns a dict like:
    {
        "tabs": {
            "Prog": {"headers": [...], "rows": [...]},
            "Paid Social Trafficking": {"headers": [...], "rows": [...]},
            ...
        }
    }
    """
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    templates_json = json.dumps(TAB_TEMPLATES, indent=2)

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT.format(templates_json=templates_json),
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
        result: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Claude returned invalid JSON: %s", raw[:500])
        raise ValueError("Claude did not return valid JSON. Try again.") from exc

    # Normalise: ensure every tab has headers + rows, and every row has all
    # header keys filled (at least with "").
    tabs = result.get("tabs", result)  # handle both {tabs: {...}} and flat
    normalised: dict[str, Any] = {}
    for tab_name, tab_data in tabs.items():
        headers = tab_data.get("headers", TAB_TEMPLATES.get(tab_name, []))
        rows = tab_data.get("rows", [])

        clean_rows = []
        for row in rows:
            clean_rows.append({h: row.get(h, "") for h in headers})

        normalised[tab_name] = {"headers": headers, "rows": clean_rows}

    return {"tabs": normalised}


async def parse_pdf(file_bytes: bytes) -> dict[str, Any]:
    """
    High-level entry point: extract text then parse with Claude.

    Returns multi-tab structured data ready for the review UI.
    """
    pdf_text = extract_text_from_pdf(file_bytes)
    if not pdf_text.strip():
        raise ValueError("Could not extract any text from the PDF.")
    return parse_with_claude(pdf_text)
