"""
config.py — Single source of truth for Asset Pipeline settings.

This is the ONLY file you need to edit to customize the pipeline.
Non-developers: feel free to modify the values below. Each setting
has a comment explaining what it does and how to change it.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# TRACKING SHEET COLUMNS
# ---------------------------------------------------------------------------
# These are the column headers for the Excel tracking spreadsheet.
# To add a column: append a new string to the list.
# To remove a column: delete that string from the list.
# To reorder: rearrange the strings.
# The first column will always contain the final renamed file name.
TRACKING_SHEET_COLUMNS: list[str] = [
    "Asset Name",
    "File Name",
    "Platform",
    "Post Copy",
    "Description",
    "Objective",
    "CTA",
    "Ad Format",
    "Placement",
    "Start Date",
    "End Date",
]

# ---------------------------------------------------------------------------
# NAMING CONVENTION
# ---------------------------------------------------------------------------
# Template used to rename asset files during processing.
# Available placeholders (wrapped in curly braces) correspond to the
# tracking sheet columns — use any column name in lowercase with spaces
# replaced by underscores.
#
# Examples:
#   "{asset_name}_{platform}_{ad_format}"
#   "{platform}_{placement}_{asset_name}_v{version}"
#
# If a placeholder value is missing for a row, it will be replaced with
# "unknown". The original file extension is always preserved automatically.
NAMING_CONVENTION: str = "{asset_name}_{platform}_{ad_format}_{placement}"

# ---------------------------------------------------------------------------
# FOLDER PATHS
# ---------------------------------------------------------------------------
# Where renamed/processed files are saved locally before (optional) upload.
# Can be an absolute path or relative to the project root.
LOCAL_OUTPUT_FOLDER: str = os.getenv("LOCAL_OUTPUT_FOLDER", "output")

# ---------------------------------------------------------------------------
# SHAREPOINT SETTINGS
# ---------------------------------------------------------------------------
# Destination folder path on SharePoint where files will be uploaded.
SHAREPOINT_FOLDER: str = os.getenv("SHAREPOINT_FOLDER", "Marketing/Assets")

# Azure / Microsoft Graph credentials (loaded from .env)
AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
SHAREPOINT_SITE_ID: str = os.getenv("SHAREPOINT_SITE_ID", "")
SHAREPOINT_DRIVE_ID: str = os.getenv("SHAREPOINT_DRIVE_ID", "")

# ---------------------------------------------------------------------------
# ANTHROPIC / CLAUDE API
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# The Claude model to use for PDF parsing. "claude-sonnet-4-20250514" is a good
# balance of speed and quality. Change to "claude-opus-4-0-20250514" for maximum
# accuracy on complex briefs.
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# ---------------------------------------------------------------------------
# SERVER SETTINGS
# ---------------------------------------------------------------------------
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8000"))
