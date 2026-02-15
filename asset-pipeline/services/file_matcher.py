"""
file_matcher.py — Scan a local folder of asset files and fuzzy-match
them to parsed rows from the PDF brief.

Matching strategy
-----------------
For each parsed row, we compare the row's "Asset Name" and "File Name"
fields against every file in the folder using token-based fuzzy matching
(thefuzz library).  The best match above a confidence threshold is
assigned; anything below the threshold is flagged as "unmatched" so the
user can correct it in the review UI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from thefuzz import fuzz

# Minimum score (0-100) for a match to be considered.  Lower = more
# permissive; higher = stricter.  80 is a reasonable starting point.
MATCH_THRESHOLD = 60


def list_files(folder_path: str) -> list[dict[str, str]]:
    """
    Return a list of dicts describing every file in *folder_path*.

    Each dict: {"name": "photo.jpg", "path": "/abs/path/to/photo.jpg"}
    Skips hidden files (starting with '.') and directories.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    files: list[dict[str, str]] = []
    for entry in sorted(folder.iterdir()):
        if entry.is_file() and not entry.name.startswith("."):
            files.append({"name": entry.name, "path": str(entry.resolve())})
    return files


def _score(row: dict[str, Any], filename: str) -> int:
    """
    Compute a fuzzy match score between a parsed row and a filename.

    Combines the best of:
      - Asset Name vs filename (without extension)
      - File Name field vs filename
    """
    stem = Path(filename).stem.lower()

    candidates: list[str] = []
    if row.get("Asset Name"):
        candidates.append(str(row["Asset Name"]).lower())
    if row.get("File Name"):
        candidates.append(str(row["File Name"]).lower())

    if not candidates:
        return 0

    best = 0
    for candidate in candidates:
        # token_sort_ratio handles word-order differences well
        score = fuzz.token_sort_ratio(candidate, stem)
        best = max(best, score)
        # Also try partial ratio for substring matches
        partial = fuzz.partial_ratio(candidate, stem)
        best = max(best, partial)
    return best


def match_files(
    rows: list[dict[str, Any]], folder_path: str
) -> dict[str, Any]:
    """
    Match parsed asset rows to files in the given folder.

    Returns a dict with:
      - "files": list of file dicts from the folder
      - "rows": the original rows augmented with:
            "_matched_file"  — filename of best match (or "")
            "_matched_path"  — absolute path of best match (or "")
            "_match_score"   — 0-100 confidence score
    """
    files = list_files(folder_path)
    file_names = [f["name"] for f in files]
    file_map = {f["name"]: f["path"] for f in files}

    used: set[str] = set()  # track already-assigned files
    augmented_rows: list[dict[str, Any]] = []

    # Build a list of (row_index, file_name, score) for all combinations
    all_scores: list[tuple[int, str, int]] = []
    for i, row in enumerate(rows):
        for fname in file_names:
            s = _score(row, fname)
            all_scores.append((i, fname, s))

    # Sort descending by score so the best matches are assigned first
    all_scores.sort(key=lambda x: x[2], reverse=True)

    assignments: dict[int, tuple[str, int]] = {}  # row_idx -> (filename, score)

    for row_idx, fname, score in all_scores:
        if row_idx in assignments:
            continue
        if fname in used:
            continue
        if score >= MATCH_THRESHOLD:
            assignments[row_idx] = (fname, score)
            used.add(fname)

    for i, row in enumerate(rows):
        row_copy = dict(row)
        if i in assignments:
            fname, score = assignments[i]
            row_copy["_matched_file"] = fname
            row_copy["_matched_path"] = file_map[fname]
            row_copy["_match_score"] = score
        else:
            row_copy["_matched_file"] = ""
            row_copy["_matched_path"] = ""
            row_copy["_match_score"] = 0
        augmented_rows.append(row_copy)

    return {"files": files, "rows": augmented_rows}
