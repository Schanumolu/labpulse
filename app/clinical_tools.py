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

"""Clinical tools for LabPulse: biomarker lookups, lab history recording, and doctor discussion prompts."""

from __future__ import annotations

import datetime
from typing import Any


# Standard reference ranges and clinical interpretations
BIOMARKER_CATALOG: dict[str, dict[str, Any]] = {
    "fasting_glucose": {
        "name": "Fasting Blood Glucose",
        "aliases": ["glucose", "fasting blood sugar", "fbs", "blood sugar"],
        "panel": "Basic Metabolic Panel (BMP) / Comprehensive Metabolic Panel (CMP)",
        "unit": "mg/dL",
        "reference_range": {"min": 70, "max": 99},
        "description": "Measures the amount of glucose (sugar) in your blood after an overnight fast of at least 8 hours.",
        "interpretations": {
            "low": "Hypoglycemia (< 70 mg/dL). Can cause shakiness, dizziness, sweating, confusion.",
            "normal": "Normal fasting blood glucose (70 - 99 mg/dL).",
            "elevated": "Prediabetes (100 - 125 mg/dL) or Impaired Fasting Glucose.",
            "high": "Diabetes threshold (>= 126 mg/dL on two separate tests).",
        },
    },
    "hba1c": {
        "name": "Hemoglobin A1c (Glycated Hemoglobin)",
        "aliases": ["a1c", "glycated hemoglobin", "estimated average glucose"],
        "panel": "Diabetes Screening / Monitoring",
        "unit": "%",
        "reference_range": {"min": 4.0, "max": 5.6},
        "description": "Reflects your average blood sugar level over the past 2 to 3 months by measuring the percentage of hemoglobin coated with sugar.",
        "interpretations": {
            "normal": "Normal (< 5.7%).",
            "elevated": "Prediabetes (5.7% - 6.4%). Suggests elevated risk of progression to Type 2 diabetes.",
            "high": "Diabetes (>= 6.5%). Most diabetic treatment goals aim for < 7.0% or individualized targets.",
        },
    },
    "total_cholesterol": {
        "name": "Total Cholesterol",
        "aliases": ["cholesterol", "tc"],
        "panel": "Lipid Panel",
        "unit": "mg/dL",
        "reference_range": {"min": 125, "max": 199},
        "description": "The total amount of cholesterol in your blood, including LDL, HDL, and VLDL.",
        "interpretations": {
            "normal": "Desirable (< 200 mg/dL).",
            "elevated": "Borderline high (200 - 239 mg/dL).",
            "high": "High (>= 240 mg/dL). Increases risk of coronary artery disease and atherosclerosis.",
        },
    },
    "ldl": {
        "name": "Low-Density Lipoprotein Cholesterol (LDL-C)",
        "aliases": ["ldl-c", "bad cholesterol", "low density lipoprotein"],
        "panel": "Lipid Panel",
        "unit": "mg/dL",
        "reference_range": {"min": 0, "max": 99},
        "description": "Often called 'bad cholesterol'. High levels lead to plaque buildup in arteries (atherosclerosis).",
        "interpretations": {
            "optimal": "Optimal (< 100 mg/dL). For patients with heart disease or diabetes, < 70 mg/dL or lower is often targeted.",
            "elevated": "Near optimal / Borderline high (100 - 159 mg/dL).",
            "high": "High to very high (>= 160 mg/dL).",
        },
    },
    "hdl": {
        "name": "High-Density Lipoprotein Cholesterol (HDL-C)",
        "aliases": ["hdl-c", "good cholesterol", "high density lipoprotein"],
        "panel": "Lipid Panel",
        "unit": "mg/dL",
        "reference_range": {"min": 40, "max": 80},
        "description": "Known as 'good cholesterol'. It transports excess cholesterol from tissues back to the liver for disposal.",
        "interpretations": {
            "low": "Low (< 40 mg/dL in men, < 50 mg/dL in women). Associated with higher cardiovascular risk.",
            "normal": "Acceptable (40 - 59 mg/dL).",
            "optimal": "Optimal / Protective (>= 60 mg/dL). Considered cardioprotective.",
        },
    },
    "triglycerides": {
        "name": "Triglycerides",
        "aliases": ["tg", "blood fats"],
        "panel": "Lipid Panel",
        "unit": "mg/dL",
        "reference_range": {"min": 0, "max": 149},
        "description": "A type of fat (lipid) found in blood converted from unused calories. High levels increase risk of metabolic syndrome and pancreatitis.",
        "interpretations": {
            "normal": "Normal (< 150 mg/dL).",
            "elevated": "Borderline high (150 - 199 mg/dL).",
            "high": "High (200 - 499 mg/dL); Very high (>= 500 mg/dL, risk of acute pancreatitis).",
        },
    },
    "egfr": {
        "name": "Estimated Glomerular Filtration Rate (eGFR)",
        "aliases": ["gfr", "glomerular filtration rate", "kidney filtration"],
        "panel": "Renal Function Panel / Comprehensive Metabolic Panel (CMP)",
        "unit": "mL/min/1.73m²",
        "reference_range": {"min": 90, "max": 130},
        "description": "Calculated indicator of how efficiently your kidneys filter waste from your blood.",
        "interpretations": {
            "normal": "Normal kidney function (>= 90 mL/min/1.73m²).",
            "mildly_decreased": "Mildly decreased (60 - 89 mL/min/1.73m²). Common with aging or early kidney disease if proteinuria is present.",
            "moderate_to_severe": "Moderate to severe decline (< 60 mL/min/1.73m² for > 3 months indicates chronic kidney disease).",
        },
    },
    "creatinine": {
        "name": "Serum Creatinine",
        "aliases": ["blood creatinine", "cr"],
        "panel": "Basic Metabolic Panel (BMP) / CMP / Renal Panel",
        "unit": "mg/dL",
        "reference_range": {"min": 0.6, "max": 1.3},
        "description": "A breakdown product of creatine phosphate from muscle metabolism, excreted entirely by the kidneys.",
        "interpretations": {
            "low": "Low (< 0.6 mg/dL). May indicate low muscle mass or severe liver disease.",
            "normal": "Normal kidney clearance (0.6 - 1.3 mg/dL).",
            "high": "Elevated (> 1.3 mg/dL). Suggests impaired renal filtration, acute kidney injury, or chronic kidney disease.",
        },
    },
    "tsh": {
        "name": "Thyroid Stimulating Hormone (TSH)",
        "aliases": ["thyrotropin"],
        "panel": "Thyroid Function Panel",
        "unit": "mIU/L",
        "reference_range": {"min": 0.4, "max": 4.0},
        "description": "Produced by the pituitary gland to regulate thyroid hormone production.",
        "interpretations": {
            "low": "Low (< 0.4 mIU/L). Suggests hyperthyroidism (overactive thyroid).",
            "normal": "Normal euthyroid function (0.4 - 4.0 mIU/L).",
            "high": "High (> 4.0 mIU/L). Suggests hypothyroidism (underactive thyroid).",
        },
    },
    "hemoglobin": {
        "name": "Hemoglobin (Hgb)",
        "aliases": ["hgb", "hb"],
        "panel": "Complete Blood Count (CBC)",
        "unit": "g/dL",
        "reference_range": {"min": 12.0, "max": 17.5},
        "description": "Iron-rich protein in red blood cells that transports oxygen from your lungs to your body tissues.",
        "interpretations": {
            "low": "Low (< 12.0 g/dL). Indicates anemia, blood loss, nutritional deficiencies (iron, B12), or bone marrow disorders.",
            "normal": "Normal adult oxygen carrying capacity (12.0 - 17.5 g/dL).",
            "high": "Elevated (> 17.5 g/dL). Polycythemia, chronic hypoxia (smoking, COPD), or dehydration.",
        },
    },
    "wbc": {
        "name": "White Blood Cell Count (WBC)",
        "aliases": ["leukocyte count", "white blood cells"],
        "panel": "Complete Blood Count (CBC)",
        "unit": "10^3/uL",
        "reference_range": {"min": 4.5, "max": 11.0},
        "description": "Cells of the immune system involved in defending the body against infections and foreign materials.",
        "interpretations": {
            "low": "Leukopenia (< 4.5). Weakened immune defenses, viral infections, or bone marrow suppression.",
            "normal": "Normal immune baseline (4.5 - 11.0 10^3/uL).",
            "high": "Leukocytosis (> 11.0). Infection, physiological stress, inflammation, or hematologic conditions.",
        },
    },
    "alt": {
        "name": "Alanine Aminotransferase (ALT)",
        "aliases": ["sgpt", "alanine transaminase"],
        "panel": "Hepatic (Liver) Function Panel / CMP",
        "unit": "U/L",
        "reference_range": {"min": 7, "max": 56},
        "description": "An enzyme primarily concentrated in the liver. Released into the bloodstream when liver cells are damaged.",
        "interpretations": {
            "normal": "Normal liver baseline (7 - 56 U/L).",
            "high": "Elevated (> 56 U/L). Suggests hepatitis, fatty liver disease, medication side effects, or bile duct issues.",
        },
    },
}

# In-memory storage for recorded lab history
_LAB_HISTORY_STORE: list[dict[str, Any]] = []


def _resolve_biomarker_key(name: str) -> str | None:
    cleaned = name.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in BIOMARKER_CATALOG:
        return cleaned

    # First pass: exact matches
    for key, data in BIOMARKER_CATALOG.items():
        if cleaned == key or cleaned == data["name"].lower():
            return key
        for alias in data.get("aliases", []):
            if cleaned == alias.lower().replace("-", "_").replace(" ", "_"):
                return key

    # Second pass: token/substring match
    for key, data in BIOMARKER_CATALOG.items():
        for alias in data.get("aliases", []):
            alias_clean = alias.lower().replace("-", "_").replace(" ", "_")
            if alias_clean in cleaned or cleaned in alias_clean:
                return key
    return None


def lookup_biomarker(biomarker_name: str) -> dict[str, Any]:
    """Looks up standard clinical definitions, reference ranges, and diagnostic panel associations for a biomarker.

    Args:
        biomarker_name: Name, acronym, or common term of the biomarker (e.g. 'A1C', 'fasting glucose', 'LDL', 'eGFR', 'Hemoglobin').

    Returns:
        A dictionary containing the official name, standard diagnostic panel, conventional unit,
        clinical reference ranges, and diagnostic interpretation guide.
    """
    key = _resolve_biomarker_key(biomarker_name)
    if not key:
        return {
            "query": biomarker_name,
            "found": False,
            "message": f"Biomarker '{biomarker_name}' was not found in the primary catalog. Available markers include: {', '.join(sorted(BIOMARKER_CATALOG.keys()))}.",
        }

    info = BIOMARKER_CATALOG[key]
    return {
        "query": biomarker_name,
        "found": True,
        "biomarker_id": key,
        "name": info["name"],
        "panel": info["panel"],
        "unit": info["unit"],
        "reference_range": info["reference_range"],
        "description": info["description"],
        "interpretations": info["interpretations"],
    }


def record_lab_entry(
    biomarker_name: str,
    value: float,
    unit: str,
    test_date: str = "",
    notes: str = "",
) -> dict[str, Any]:
    """Records a patient's lab test result into their tracked lab history, evaluating clinical range status.

    Args:
        biomarker_name: The name or acronym of the tested biomarker (e.g., 'HbA1c', 'LDL', 'Fasting Glucose').
        value: The numerical value obtained on the test.
        unit: The measurement unit (e.g., 'mg/dL', '%', 'U/L').
        test_date: The date of the lab test (e.g., '2026-09-15'). Defaults to today if not provided.
        notes: Any clinical notes, fasting status, or lab context (e.g., '12-hour fast', 'post-medication').

    Returns:
        A dictionary with the stored entry, reference comparison, status badge (NORMAL, HIGH, LOW, or UNRANGED),
        and confirmation.
    """
    key = _resolve_biomarker_key(biomarker_name)
    date_str = test_date if test_date else datetime.date.today().isoformat()

    status = "RECORDED"
    reference_info = None

    if key:
        catalog_entry = BIOMARKER_CATALOG[key]
        canonical_name = catalog_entry["name"]
        ref_min = catalog_entry["reference_range"]["min"]
        ref_max = catalog_entry["reference_range"]["max"]
        reference_info = f"{ref_min} - {ref_max} {catalog_entry['unit']}"

        if value < ref_min:
            status = "LOW"
        elif value > ref_max:
            status = "HIGH"
        else:
            status = "NORMAL"
    else:
        canonical_name = biomarker_name

    entry = {
        "id": len(_LAB_HISTORY_STORE) + 1,
        "biomarker_id": key or biomarker_name.lower().replace(" ", "_"),
        "biomarker_name": canonical_name,
        "value": value,
        "unit": unit,
        "test_date": date_str,
        "status": status,
        "reference_range": reference_info or "Not established in local catalog",
        "notes": notes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    _LAB_HISTORY_STORE.append(entry)

    return {
        "success": True,
        "entry": entry,
        "summary": f"Successfully recorded {canonical_name}: {value} {unit} ({status}) on {date_str}.",
    }


def get_lab_history(biomarker_name: str = "") -> list[dict[str, Any]]:
    """Retrieves the patient's recorded lab test entries, optionally filtered by a specific biomarker.

    Args:
        biomarker_name: Optional biomarker name or acronym to filter for (e.g., 'glucose', 'ldl').
                        If empty, returns all historical entries.

    Returns:
        A list of recorded lab entries sorted chronologically.
    """
    if not biomarker_name:
        return list(_LAB_HISTORY_STORE)

    key = _resolve_biomarker_key(biomarker_name)
    filtered = []
    for item in _LAB_HISTORY_STORE:
        if (key and item.get("biomarker_id") == key) or (biomarker_name.lower() in item.get("biomarker_name", "").lower()):
            filtered.append(item)
    return filtered


def formulate_doctor_discussion_prompts(
    topics_or_abnormalities: list[str],
    patient_concerns: str = "",
) -> dict[str, Any]:
    """Formulates structured, clinically meaningful discussion prompts and questions for the patient's next doctor appointment.

    Args:
        topics_or_abnormalities: List of biomarker names, abnormal test results, or symptoms to address (e.g. ['elevated LDL 145 mg/dL', 'fasting glucose 118']).
        patient_concerns: Specific personal concerns, symptoms, or medication side effects the patient has noticed.

    Returns:
        A dictionary containing categorized questions for the doctor: clarifying questions,
        lifestyle/treatment questions, and next steps / retesting timelines.
    """
    clarifying_questions = []
    lifestyle_and_treatment = []
    next_steps = []

    for topic in topics_or_abnormalities:
        clarifying_questions.append(
            f"Given that my {topic} is outside the standard reference range, what specific underlying factors or risk profile does this indicate for me personally?"
        )
        lifestyle_and_treatment.append(
            f"Are there targeted nutritional adjustments, exercise modifications, or medications recommended to help manage my {topic}?"
        )
        next_steps.append(
            f"When should we retest my {topic} to evaluate if changes are having the desired effect?"
        )

    if patient_concerns:
        clarifying_questions.append(
            f"I have also noticed: '{patient_concerns}'. Could this be related to these test results or current medications?"
        )

    lifestyle_and_treatment.append(
        "Are there any specific symptoms or warning signs I should watch out for before my next follow-up?"
    )
    next_steps.append(
        "Would any supplementary panels (such as hs-CRP, Coronary Calcium score, or microalbuminuria) provide helpful additional context?"
    )

    return {
        "topics_addressed": topics_or_abnormalities,
        "patient_concerns": patient_concerns,
        "suggested_agenda": {
            "1_understanding_the_numbers": clarifying_questions,
            "2_treatment_and_lifestyle_plan": lifestyle_and_treatment,
            "3_retesting_and_monitoring": next_steps,
        },
        "patient_tip": "Bring your prior lab printouts or this list to your appointment. Don't hesitate to take notes during the discussion.",
    }


DIAGNOSTIC_PANELS: dict[str, dict[str, Any]] = {
    "lipid_panel": {
        "title": "Lipid Panel",
        "aliases": ["lipid", "cholesterol panel", "lipids", "lipid profile"],
        "description": "Comprehensive cholesterol and cardiovascular lipid risk profile.",
        "biomarkers": [
            {"id": "total_cholesterol", "name": "Total Cholesterol", "target": "< 200 mg/dL", "min": 125, "max": 199, "unit": "mg/dL"},
            {"id": "ldl", "name": "LDL-C (Bad Cholesterol)", "target": "< 100 mg/dL", "min": 0, "max": 99, "unit": "mg/dL"},
            {"id": "hdl", "name": "HDL-C (Good Cholesterol)", "target": "> 40 (M) / > 50 (F) mg/dL", "min": 40, "max": 80, "unit": "mg/dL"},
            {"id": "triglycerides", "name": "Triglycerides", "target": "< 150 mg/dL", "min": 0, "max": 149, "unit": "mg/dL"},
        ],
        "visit_checklist": [
            "Fasted for 9 to 12 hours prior to blood draw (water permitted)",
            "Documented all current statins, fibrates, or omega-3 supplements",
            "Prepared questions on 10-year atherosclerotic cardiovascular disease (ASCVD) risk score",
            "Discussed dietary lifestyle modifications (soluble fiber, limiting saturated fats)",
        ],
    },
    "metabolic_panel": {
        "title": "Comprehensive Metabolic Panel (CMP)",
        "aliases": ["cmp", "bmp", "metabolic", "basic metabolic panel", "comprehensive metabolic"],
        "description": "Evaluates kidney function, liver health, fluid/electrolyte balance, and blood glucose.",
        "biomarkers": [
            {"id": "fasting_glucose", "name": "Fasting Blood Glucose", "target": "70 - 99 mg/dL", "min": 70, "max": 99, "unit": "mg/dL"},
            {"id": "bun", "name": "Blood Urea Nitrogen (BUN)", "target": "7 - 20 mg/dL", "min": 7, "max": 20, "unit": "mg/dL"},
            {"id": "creatinine", "name": "Serum Creatinine", "target": "0.6 - 1.3 mg/dL", "min": 0.6, "max": 1.3, "unit": "mg/dL"},
            {"id": "egfr", "name": "Estimated GFR (Kidney Filtration)", "target": ">= 90 mL/min/1.73m²", "min": 90, "max": 130, "unit": "mL/min/1.73m²"},
            {"id": "alt", "name": "ALT (Liver Enzyme)", "target": "7 - 56 U/L", "min": 7, "max": 56, "unit": "U/L"},
            {"id": "sodium", "name": "Sodium (Electrolyte)", "target": "135 - 145 mmol/L", "min": 135, "max": 145, "unit": "mmol/L"},
            {"id": "potassium", "name": "Potassium (Electrolyte)", "target": "3.5 - 5.0 mmol/L", "min": 3.5, "max": 5.0, "unit": "mmol/L"},
        ],
        "visit_checklist": [
            "Maintained consistent hydration before the blood draw",
            "Noted timing of blood pressure and diabetes medications",
            "Prepared to ask if dosage adjustments are needed based on kidney clearance (eGFR)",
            "Flagged any symptoms of electrolyte imbalance (muscle cramps, swelling, fatigue)",
        ],
    },
    "cbc": {
        "title": "Complete Blood Count (CBC)",
        "aliases": ["cbc", "blood count", "complete blood panel", "hemogram"],
        "description": "Quantifies circulating cellular components: oxygen carriers, immune defense, and clotting cells.",
        "biomarkers": [
            {"id": "hemoglobin", "name": "Hemoglobin (Hgb)", "target": "12.0 - 17.5 g/dL", "min": 12.0, "max": 17.5, "unit": "g/dL"},
            {"id": "hematocrit", "name": "Hematocrit (Hct)", "target": "36.0 - 50.0 %", "min": 36.0, "max": 50.0, "unit": "%"},
            {"id": "wbc", "name": "White Blood Cells (WBC)", "target": "4.5 - 11.0 10^3/uL", "min": 4.5, "max": 11.0, "unit": "10^3/uL"},
            {"id": "platelets", "name": "Platelets", "target": "150 - 450 10^3/uL", "min": 150, "max": 450, "unit": "10^3/uL"},
        ],
        "visit_checklist": [
            "No fasting required for CBC alone",
            "Noted any recent colds, viral infections, or dental work",
            "Logged any unusual easy bruising, bleeding gums, or persistent fatigue",
            "Prepared to ask doctor if iron, ferritin, or vitamin B12 testing is warranted if red counts are borderline",
        ],
    },
}


def get_diagnostic_panel(
    panel_name: str,
    patient_values: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Retrieves a structured diagnostic panel (Lipid Panel, Metabolic Panel, or CBC) with reference ranges, status badges, and visit checklists.

    Args:
        panel_name: Name or acronym of the panel ('lipid', 'metabolic', 'cmp', 'bmp', 'cbc').
        patient_values: Optional mapping of biomarker name/id to measured values (e.g. {'ldl': 145, 'hdl': 42}).

    Returns:
        Structured panel dictionary with evaluated status badges, out-of-range indicators, and appointment visit checklists.
    """
    clean_name = panel_name.strip().lower().replace("-", "_").replace(" ", "_")
    matched_panel_key = None

    for key, data in DIAGNOSTIC_PANELS.items():
        if clean_name == key or clean_name in data["aliases"] or any(clean_name in alias for alias in data["aliases"]):
            matched_panel_key = key
            break

    if not matched_panel_key:
        return {
            "query": panel_name,
            "found": False,
            "message": f"Panel '{panel_name}' not found. Supported panels: Lipid Panel ('lipid'), Metabolic Panel ('metabolic'/'cmp'/'bmp'), Complete Blood Count ('cbc').",
        }

    panel_def = DIAGNOSTIC_PANELS[matched_panel_key]
    patient_vals = patient_values or {}

    # Check local store for any matching values if not explicitly provided
    if not patient_vals:
        for entry in _LAB_HISTORY_STORE:
            b_id = entry.get("biomarker_id")
            if b_id:
                patient_vals[b_id] = entry.get("value")

    evaluated_biomarkers = []
    out_of_range_count = 0

    for marker in panel_def["biomarkers"]:
        val = patient_vals.get(marker["id"]) or patient_vals.get(marker["name"].lower())
        status_badge = "PENDING / NOT RECORDED"
        indicator = "⚪"

        if val is not None:
            val_float = float(val)
            if val_float < marker["min"]:
                status_badge = "LOW [OUT OF RANGE]"
                indicator = "🔻 LOW"
                out_of_range_count += 1
            elif val_float > marker["max"]:
                status_badge = "HIGH [OUT OF RANGE]"
                indicator = "🔺 HIGH"
                out_of_range_count += 1
            else:
                status_badge = "NORMAL [IN RANGE]"
                indicator = "✅ NORMAL"

        evaluated_biomarkers.append({
            "biomarker": marker["name"],
            "patient_value": f"{val} {marker['unit']}" if val is not None else "Not provided",
            "target_range": marker["target"],
            "status_badge": status_badge,
            "indicator": indicator,
        })

    return {
        "panel_title": panel_def["title"],
        "panel_description": panel_def["description"],
        "out_of_range_count": out_of_range_count,
        "biomarkers": evaluated_biomarkers,
        "visit_checklist": panel_def["visit_checklist"],
    }
