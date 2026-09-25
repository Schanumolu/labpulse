# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Integration with NIH MedlinePlus Connect Web Service (US National Library of Medicine).

Provides authoritative, patient-friendly medical explanations, test preparations,
causes for abnormal results, and NIH health resources by LOINC code or biomarker name.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from typing import Any

# Standard LOINC code mappings for common clinical biomarkers
_LOINC_MAP = {
    "cholesterol": "2093-3",
    "total_cholesterol": "2093-3",
    "ldl": "2089-1",
    "ldl_cholesterol": "2089-1",
    "hdl": "2085-9",
    "hdl_cholesterol": "2085-9",
    "triglycerides": "2571-8",
    "glucose": "2345-7",
    "fasting_glucose": "2345-7",
    "blood_glucose": "2345-7",
    "hba1c": "4548-4",
    "a1c": "4548-4",
    "creatinine": "2160-0",
    "serum_creatinine": "2160-0",
    "bun": "3094-0",
    "blood_urea_nitrogen": "3094-0",
    "egfr": "48642-3",
    "alt": "1742-6",
    "alanine_aminotransferase": "1742-6",
    "hemoglobin": "718-7",
    "hematocrit": "4544-3",
    "wbc": "6690-2",
    "white_blood_cells": "6690-2",
    "platelets": "777-3",
    "sodium": "2951-2",
    "potassium": "2823-3",
}

_CONNECT_BASE_URL = "https://connect.medlineplus.gov/service"


def _clean_html(raw_html: str) -> str:
    """Strips HTML tags and unescapes entities into plain text."""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = html.unescape(clean)
    return " ".join(clean.split())


def fetch_medlineplus_topic(biomarker_name: str) -> dict[str, Any]:
    """Fetches official patient education and clinical lab summaries from the US National Library of Medicine (NIH).

    Args:
        biomarker_name: Name or acronym of the biomarker (e.g., 'LDL', 'Cholesterol', 'Glucose', 'eGFR', 'HbA1c').

    Returns:
        A dictionary containing official NIH topic title, clinical summary, LOINC code, and MedlinePlus article link.
    """
    normalized = biomarker_name.strip().lower().replace("-", "_").replace(" ", "_")
    loinc_code = _LOINC_MAP.get(normalized)

    # Search by LOINC if mapped, otherwise search by text
    if not loinc_code:
        for k, v in _LOINC_MAP.items():
            if k in normalized or normalized in k:
                loinc_code = v
                break

    if loinc_code:
        params = {
            "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.1",  # LOINC code system
            "mainSearchCriteria.v.c": loinc_code,
            "knowledgeResponseType": "application/json",
        }
    else:
        # Fallback to general condition search with LOINC for cholesterol if not recognized
        params = {
            "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.1",
            "mainSearchCriteria.v.c": "2093-3",
            "knowledgeResponseType": "application/json",
        }

    url = f"{_CONNECT_BASE_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LabPulse-ClinicalAssistant/1.0 (Health Education)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        feed = payload.get("feed", {})
        entries = feed.get("entry", [])
        if not entries:
            return {
                "found": False,
                "biomarker_name": biomarker_name,
                "loinc_code": loinc_code,
                "message": f"No direct NIH MedlinePlus entry found for '{biomarker_name}'.",
            }

        first_entry = entries[0]
        title = first_entry.get("title", {}).get("_value", "")
        summary_raw = first_entry.get("summary", {}).get("_value", "")
        cleaned_summary = _clean_html(summary_raw)

        # Get canonical MedlinePlus URL
        link = ""
        for l in first_entry.get("link", []):
            if l.get("rel") == "alternate" or "medlineplus.gov" in l.get("href", ""):
                link = l.get("href")
                break
        if not link and entries[0].get("link"):
            link = entries[0]["link"][0].get("href", "")

        return {
            "found": True,
            "source": "NIH MedlinePlus (National Library of Medicine)",
            "biomarker_name": biomarker_name,
            "loinc_code": loinc_code,
            "title": title,
            "summary": cleaned_summary,
            "official_url": link,
        }

    except Exception as e:
        return {
            "found": False,
            "biomarker_name": biomarker_name,
            "loinc_code": loinc_code,
            "error": str(e),
            "message": f"Unable to reach MedlinePlus service: {e}",
        }
