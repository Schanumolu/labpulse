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

"""Integration with openFDA Drug Safety & Adverse Event APIs (US FDA).

Enables LabPulse to check whether patient medications interact with, elevate,
or require ongoing laboratory monitoring for specific clinical biomarkers.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

_FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
_FDA_EVENT_URL = "https://api.fda.gov/drug/event.json"

# Common biomarker keywords to scan within FDA drug warning sections
_BIOMARKER_TERMS = {
    "alt": ["alt", "alanine aminotransferase", "liver function", "transaminase", "hepatic", "liver enzymes"],
    "glucose": ["glucose", "blood sugar", "hyperglycemia", "hypoglycemia", "diabetes"],
    "potassium": ["potassium", "hyperkalemia", "hypokalemia", "serum potassium"],
    "creatinine": ["creatinine", "renal", "kidney", "renal impairment", "glomerular"],
    "egfr": ["egfr", "gfr", "renal function", "kidney failure", "creatinine clearance"],
    "ldl": ["ldl", "cholesterol", "lipid", "hypercholesterolemia"],
    "cholesterol": ["cholesterol", "lipids", "hdl", "ldl", "triglycerides"],
    "hemoglobin": ["hemoglobin", "anemia", "hematocrit", "blood loss", "rbc"],
    "platelets": ["platelet", "thrombocytopenia", "bleeding", "clotting"],
    "sodium": ["sodium", "hyponatremia", "hypernatremia", "electrolyte"],
    "wbc": ["white blood cell", "leukopenia", "neutropenia", "infection"],
}


def _fetch_json(url: str) -> dict[str, Any] | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "LabPulse-ClinicalAssistant/1.0 (Drug-Lab Interaction)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def get_drug_safety_summary(drug_name: str) -> dict[str, Any]:
    """Retrieves FDA-approved indications, boxed warnings, and top reported adverse events for a medication.

    Args:
        drug_name: Generic or brand name of the drug (e.g., 'atorvastatin', 'lisinopril', 'metformin').

    Returns:
        A dictionary with brand name, active ingredients, boxed warnings, and frequent adverse reactions.
    """
    clean_name = drug_name.strip().lower()
    encoded = urllib.parse.quote(f'openfda.generic_name:"{clean_name}" openfda.brand_name:"{clean_name}"')
    label_url = f"{_FDA_LABEL_URL}?search=openfda.generic_name:{clean_name}+openfda.brand_name:{clean_name}&limit=1"

    label_data = _fetch_json(label_url)
    if not label_data or not label_data.get("results"):
        # Fallback to simple generic search
        label_url = f"{_FDA_LABEL_URL}?search=openfda.generic_name:{clean_name}&limit=1"
        label_data = _fetch_json(label_url)

    # Fetch top adverse reactions from MedWatch event database
    event_url = f"{_FDA_EVENT_URL}?search=patient.drug.openfda.generic_name:{clean_name}&count=patient.reaction.reactionmeddrapt.exact"
    event_data = _fetch_json(event_url)

    top_reactions = []
    if event_data and event_data.get("results"):
        top_reactions = [
            {"reaction": item.get("term"), "reported_cases": item.get("count")}
            for item in event_data["results"][:6]
        ]

    if not label_data or not label_data.get("results"):
        return {
            "found": False,
            "drug_name": drug_name,
            "top_reported_reactions": top_reactions,
            "message": f"No official FDA drug label found for '{drug_name}'.",
        }

    label = label_data["results"][0]
    openfda = label.get("openfda", {})

    brand_names = openfda.get("brand_name", [])
    boxed_warning = label.get("boxed_warning", ["None listed."])[0] if label.get("boxed_warning") else None
    lab_tests_section = label.get("laboratory_tests", [])

    return {
        "found": True,
        "source": "US Food and Drug Administration (openFDA)",
        "drug_name": drug_name,
        "brand_names": brand_names,
        "active_substance": openfda.get("substance_name", []),
        "boxed_warning": boxed_warning[:500] if boxed_warning else None,
        "laboratory_monitoring_guidelines": lab_tests_section[0][:600] if lab_tests_section else "Routine lab monitoring as clinically indicated.",
        "top_reported_reactions": top_reactions,
    }


def check_drug_lab_interactions(drug_name: str, biomarker_name: str) -> dict[str, Any]:
    """Checks whether a patient's medication is known to alter, elevate, or require laboratory monitoring for a biomarker.

    Args:
        drug_name: Name of medication (e.g. 'atorvastatin', 'lisinopril', 'metformin', 'hydrochlorothiazide').
        biomarker_name: Biomarker name or acronym (e.g. 'ALT', 'Potassium', 'Glucose', 'Creatinine').

    Returns:
        Analysis of potential interactions, FDA warning excerpts, and suggested discussion questions for their doctor.
    """
    clean_drug = drug_name.strip().lower()
    clean_marker = biomarker_name.strip().lower()

    # Identify search terms
    terms = _BIOMARKER_TERMS.get(clean_marker, [clean_marker])

    label_url = f"{_FDA_LABEL_URL}?search=openfda.generic_name:{clean_drug}&limit=1"
    label_data = _fetch_json(label_url)

    if not label_data or not label_data.get("results"):
        label_url = f"{_FDA_LABEL_URL}?search=openfda.brand_name:{clean_drug}&limit=1"
        label_data = _fetch_json(label_url)

    if not label_data or not label_data.get("results"):
        return {
            "found": False,
            "drug_name": drug_name,
            "biomarker_name": biomarker_name,
            "message": f"Could not find FDA label records for '{drug_name}' to check '{biomarker_name}'.",
        }

    label = label_data["results"][0]
    relevant_excerpts = []

    sections_to_check = [
        ("laboratory_tests", "Laboratory Tests"),
        ("warnings", "Warnings & Precautions"),
        ("warnings_and_cautions", "Warnings and Cautions"),
        ("adverse_reactions", "Adverse Reactions"),
        ("drug_interactions", "Drug & Food Interactions"),
    ]

    for section_key, section_title in sections_to_check:
        sec_content = label.get(section_key, [])
        for text in sec_content:
            text_lower = text.lower()
            if any(term in text_lower for term in terms):
                # Extract sentence snippet containing the term
                sentences = text.split(". ")
                matching_sentences = [
                    s.strip() for s in sentences if any(term in s.lower() for term in terms)
                ]
                if matching_sentences:
                    relevant_excerpts.append({
                        "section": section_title,
                        "snippet": ". ".join(matching_sentences[:2]) + ".",
                    })

    has_known_interaction = len(relevant_excerpts) > 0

    return {
        "found": True,
        "source": "US Food and Drug Administration (openFDA)",
        "drug_name": drug_name,
        "biomarker_name": biomarker_name,
        "interaction_detected": has_known_interaction,
        "findings_count": len(relevant_excerpts),
        "fda_label_excerpts": relevant_excerpts[:3],
        "clinical_guidance": (
            f"Medication '{drug_name}' has documented FDA guidance regarding '{biomarker_name}'. "
            "Patients experiencing out-of-range lab results should inform their prescriber to verify if medication dosing or timing is a contributing factor."
            if has_known_interaction
            else f"No specific prominent warnings for '{biomarker_name}' were flagged in the FDA label for '{drug_name}', but patients should always review all medications with their healthcare provider."
        ),
    }
