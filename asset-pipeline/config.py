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
# TAB TEMPLATES
# ---------------------------------------------------------------------------
# Each key is a tab name, and the value is the list of column headers for
# that tab.  When Claude parses a PDF, it uses these as a reference to
# decide which tabs are relevant and what data to extract.
#
# To add a tab: add a new key/value pair.
# To remove a tab: delete the key/value pair.
# To change headers: edit the list for that tab.
TAB_TEMPLATES: dict[str, list[str]] = {
    "Prog": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Delivery Date",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Spec Notes",
        "Notes from M+P",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Asset File Name",
        "Link To Asset",
        "CTA",
        "Landing Page URL",
        "Dexcom Notes",
    ],
    "Endemic": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Delivery Date",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Spec Notes",
        "Notes from M+P",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Asset File Name",
        "Link To Asset",
        "CTA",
        "Landing Page",
    ],
    "Audio": [
        "Partner",
        "Platform / Tactic",
        "Campaign Objective",
        "Script Delivery Date",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Misc Notes",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Asset File Name",
        "Link To Asset",
        "Post Copy",
        "CTA",
        "Landing Page",
        "Dexcom Notes",
    ],
    "Native": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Delivery Date",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Spec Notes",
        "Notes from M+P",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Link To Asset",
        "Headline",
        "Description",
        "Landing Page",
        "Dexcom Notes",
    ],
    "Youtube": [
        "Partner",
        "Platform",
        "Placement",
        "Campaign Objective",
        "Delivery Date",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Notes",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Asset File Name",
        "Link to Asset",
        "Example",
        "Unlisted or Public YouTube Link To Asset",
        "Thumbnail",
        "Short Headline",
        "Long Headline",
        "Description",
        "CTA",
        "Landing Page URL",
        "Dexcom Notes",
    ],
    "High Impact.Contextual": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Notes",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Copy",
        "Link To Assets",
        "Landing Page",
        "Dexcom Notes",
    ],
    "CTV": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Notes",
        "Notes from M+P",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Copy",
        "Link To Assets",
        "Landing Page",
        "Dexcom Notes",
    ],
    "Retail": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Notes",
        "Notes from M+P",
        "Asset Name",
        "SFID",
        "Copy",
        "Link To Assets",
        "Landing Page",
        "Dexcom Notes",
    ],
    "Linear TV": [
        "Partner",
        "Platform",
        "Campaign Objective",
        "Flight Dates",
        "Asset Type",
        "Asset Specs",
        "Notes",
        "Notes from M+P",
        "Asset Name",
        "Campaign Name",
        "SFID",
        "Copy",
        "Link To Assets",
        "Landing Page",
        "Dexcom Notes",
    ],
    "Social": [
        "Media Channel",
        "AD FORMAT",
        "Video Length",
        "Platform / Placement",
        "Variations",
        "Resolution",
        "Aspect Ratio",
        "Max File Size",
        "File Format",
        "Audio Details",
        "Frame Rate",
        "Link to Specs",
        "Copy",
        "Notes",
    ],
    "Paid Social Trafficking": [
        "Status",
        "CAMPAIGN NAME",
        "Platform",
        "Live Date",
        "End Date",
        "Objective",
        "Ad Format",
        "Creative Name",
        "Video Length (up to 120s)",
        "Post Copy (Primary Text)",
        "Post Copy Character Count",
        "Headline",
        "Headline Character Count",
        "Description",
        "Description Character Count",
        "Disclaimer",
        "Disclaimer Character Count",
        "1:1/4:5 In Feed Asset Link",
        "9:16 Reels/Stories Asset Link",
        "CTA Button",
        "Display Link/Visual URL",
        "Landing Page",
        "Landing Page with UTMs Destination URL (Tracking Link)",
        "PREVIEW LINK",
        "MT NOTES/ APPROVAL",
        "DEXCOM NOTES/APPROVAL",
        "M+P NOTES",
        "Taxonomy Name",
    ],
    "Universal Ad Naming Convention": [
        "Advertiser",
        "Campaign Brand",
        "Site Name",
        "Campaign Name",
        "Creative Variation",
        "Dimensions / Ad Length",
        "Type / ISCI",
        "Creative File Name",
        "QA",
        "Asset link if any",
    ],
}

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
