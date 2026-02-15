"""
sheet_writer.py — Generate an Excel .xlsx tracking spreadsheet from
processed asset rows.

The column list comes from config.TRACKING_SHEET_COLUMNS so this file
never needs editing when columns change.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from config import TRACKING_SHEET_COLUMNS


def write_tracking_sheet(
    rows: list[dict[str, Any]],
    output_path: str | Path,
) -> Path:
    """
    Create an Excel tracking spreadsheet at *output_path*.

    *rows* should be a list of dicts whose keys include the names in
    TRACKING_SHEET_COLUMNS.  The "File Name" column will contain the
    final renamed filename (set by the processing step).

    Returns the resolved Path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Asset Tracker"

    # ---- Header row styling ----
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Write header row
    for col_idx, col_name in enumerate(TRACKING_SHEET_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # ---- Data rows ----
    data_alignment = Alignment(vertical="top", wrap_text=True)

    for row_idx, row_data in enumerate(rows, start=2):
        for col_idx, col_name in enumerate(TRACKING_SHEET_COLUMNS, start=1):
            value = row_data.get(col_name, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = data_alignment
            cell.border = thin_border

    # Auto-size columns (approximate)
    for col_idx, col_name in enumerate(TRACKING_SHEET_COLUMNS, start=1):
        max_len = len(col_name)
        for row_idx in range(2, len(rows) + 2):
            val = str(ws.cell(row=row_idx, column=col_idx).value or "")
            max_len = max(max_len, min(len(val), 50))
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = max_len + 4

    # Freeze the header row
    ws.freeze_panes = "A2"

    wb.save(output_path)
    return output_path.resolve()
