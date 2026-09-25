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

"""Clinical Calculator & Health Ratio Computation Engine for LabPulse.

Computes validated clinical equations and biomarkers:
1. Total Cholesterol / HDL ratio (Cardiovascular risk indicator)
2. Triglyceride / HDL ratio (Insulin resistance & atherogenic index)
3. HbA1c to Estimated Average Glucose (eAG) (ADAG ADA equation)
4. CKD-EPI 2021 Race-Free eGFR (Estimated Glomerular Filtration Rate)
5. Historical percentage change & directional trend evaluation across visits
"""

from __future__ import annotations

import math
from typing import Any


def calculate_cholesterol_ratios(
    total_cholesterol: float,
    hdl: float,
    triglycerides: float | None = None,
) -> dict[str, Any]:
    """Computes the Total Cholesterol to HDL ratio and Triglyceride to HDL ratio.

    Args:
        total_cholesterol: Total cholesterol value in mg/dL.
        hdl: HDL (high-density lipoprotein) value in mg/dL.
        triglycerides: Optional Triglycerides value in mg/dL.

    Returns:
        A dictionary with computed ratios, risk categorizations, and clinical interpretations.
    """
    if hdl <= 0:
        return {"error": "HDL value must be greater than 0 to compute ratios."}

    tc_hdl_ratio = round(total_cholesterol / hdl, 2)

    # Total/HDL Clinical Interpretation
    if tc_hdl_ratio < 3.5:
        tc_risk = "OPTIMAL"
        tc_msg = "Below 3.5: Optimal cardiovascular risk profile."
    elif tc_hdl_ratio <= 5.0:
        tc_risk = "MODERATE"
        tc_msg = "3.5 - 5.0: Average/standard cardiovascular risk."
    else:
        tc_risk = "ELEVATED"
        tc_msg = "Above 5.0: Elevated cardiovascular risk; higher proportion of atherogenic lipoproteins."

    result: dict[str, Any] = {
        "success": True,
        "total_cholesterol_mg_dl": total_cholesterol,
        "hdl_mg_dl": hdl,
        "total_to_hdl_ratio": tc_hdl_ratio,
        "risk_level": tc_risk,
        "interpretation": tc_msg,
    }

    if triglycerides is not None and triglycerides > 0:
        tg_hdl_ratio = round(triglycerides / hdl, 2)
        if tg_hdl_ratio < 2.0:
            tg_risk = "OPTIMAL"
            tg_msg = "Under 2.0: Favorable insulin sensitivity and low small dense LDL particles."
        elif tg_hdl_ratio <= 3.0:
            tg_risk = "BORDERLINE"
            tg_msg = "2.0 - 3.0: Borderline ratio; mild metabolic/insulin resistance risk."
        else:
            tg_risk = "ELEVATED"
            tg_msg = "Above 3.0: Elevated ratio; correlated with insulin resistance and atherogenic dyslipidemia."

        result["triglycerides_mg_dl"] = triglycerides
        result["triglyceride_to_hdl_ratio"] = tg_hdl_ratio
        result["tg_hdl_risk_level"] = tg_risk
        result["tg_hdl_interpretation"] = tg_msg

    return result


def calculate_hba1c_to_eag(hba1c: float) -> dict[str, Any]:
    """Converts a Hemoglobin A1c percentage into Estimated Average Glucose (eAG).

    Uses the validated ADAG (A1c-Derived Average Glucose) equation endorsed by the
    American Diabetes Association (ADA): eAG (mg/dL) = 28.7 * A1c - 46.7.

    Args:
        hba1c: Hemoglobin A1c percentage (e.g. 5.6, 6.8, 7.5).

    Returns:
        Computed eAG in mg/dL and mmol/L, with clinical glycemic control interpretation.
    """
    if hba1c < 3.0 or hba1c > 20.0:
        return {"error": f"HbA1c value {hba1c}% is outside plausible clinical range (3.0% - 20.0%)."}

    eag_mg_dl = round(28.7 * hba1c - 46.7, 1)
    eag_mmol_l = round(eag_mg_dl / 18.0182, 1)

    if hba1c < 5.7:
        category = "NORMAL"
        msg = f"Normal glycemic range. Average blood sugar over past 2-3 months was ~{int(eag_mg_dl)} mg/dL."
    elif hba1c <= 6.4:
        category = "PREDIABETES"
        msg = f"Prediabetes range (5.7% - 6.4%). Average blood sugar was ~{int(eag_mg_dl)} mg/dL. Lifestyle interventions recommended."
    elif hba1c <= 7.0:
        category = "DIABETES_TARGET_MET"
        msg = f"Common clinical target for most adults with diabetes (<= 7.0%). Average blood sugar was ~{int(eag_mg_dl)} mg/dL."
    elif hba1c <= 8.5:
        category = "SUBOPTIMAL_CONTROL"
        msg = f"Above target (7.1% - 8.5%). Average blood sugar was ~{int(eag_mg_dl)} mg/dL. Medication/lifestyle adjustments may be needed."
    else:
        category = "SIGNIFICANTLY_ELEVATED"
        msg = f"Significantly elevated (>8.5%). Average blood sugar was ~{int(eag_mg_dl)} mg/dL. Requires prompt medical attention to avoid complications."

    return {
        "success": True,
        "hba1c_percent": hba1c,
        "estimated_average_glucose_mg_dl": eag_mg_dl,
        "estimated_average_glucose_mmol_l": eag_mmol_l,
        "clinical_category": category,
        "interpretation": msg,
    }


def calculate_egfr_ckd_epi(
    serum_creatinine: float,
    age: int,
    sex: str,
) -> dict[str, Any]:
    """Calculates eGFR (Estimated Glomerular Filtration Rate) using the 2021 CKD-EPI Race-Free equation.

    Equation: eGFR = 142 * min(Scr/kappa, 1)^alpha * max(Scr/kappa, 1)^(-1.200) * 0.9938^Age [* 1.012 if female]
    Where:
      - kappa: 0.7 for female, 0.9 for male
      - alpha: -0.241 for female, -0.302 for male

    Args:
        serum_creatinine: Serum creatinine in mg/dL (e.g. 0.9, 1.3).
        age: Patient age in years (must be >= 18).
        sex: 'female' or 'male' (biological sex used for muscular mass baseline).

    Returns:
        eGFR in mL/min/1.73m2, CKD stage classification, and clinical interpretation.
    """
    if serum_creatinine <= 0:
        return {"error": "Serum creatinine must be greater than 0."}
    if age < 18 or age > 120:
        return {"error": "CKD-EPI equation is validated for adults aged 18 and older."}

    is_female = sex.strip().lower() in ["female", "f", "woman"]

    kappa = 0.7 if is_female else 0.9
    alpha = -0.241 if is_female else -0.302
    sex_factor = 1.012 if is_female else 1.0

    scr_over_kappa = serum_creatinine / kappa
    min_term = min(scr_over_kappa, 1.0) ** alpha
    max_term = max(scr_over_kappa, 1.0) ** (-1.200)
    age_term = 0.9938 ** age

    egfr = round(142 * min_term * max_term * age_term * sex_factor, 1)

    # CKD Staging
    if egfr >= 90:
        stage = "Stage 1: Normal or high kidney filtration"
        clinical_note = "Normal kidney filtration rate (>= 90 mL/min/1.73m²)."
    elif egfr >= 60:
        stage = "Stage 2: Mildly decreased kidney filtration"
        clinical_note = "Mildly decreased (60 - 89 mL/min/1.73m²); common with age, monitor annually."
    elif egfr >= 45:
        stage = "Stage 3a: Mild to moderately decreased"
        clinical_note = "Moderate reduction (45 - 59 mL/min/1.73m²); physician evaluation and medication dosing checks indicated."
    elif egfr >= 30:
        stage = "Stage 3b: Moderately to severely decreased"
        clinical_note = "Significant reduction (30 - 44 mL/min/1.73m²); nephrology consultation and kidney-sparing strategies advised."
    elif egfr >= 15:
        stage = "Stage 4: Severely decreased"
        clinical_note = "Severe reduction (15 - 29 mL/min/1.73m²); close specialist monitoring required."
    else:
        stage = "Stage 5: Kidney failure"
        clinical_note = "Kidney failure (< 15 mL/min/1.73m²); dialysis or transplant evaluation."

    return {
        "success": True,
        "serum_creatinine_mg_dl": serum_creatinine,
        "age": age,
        "sex": "female" if is_female else "male",
        "egfr_value": egfr,
        "unit": "mL/min/1.73m²",
        "stage": stage,
        "clinical_interpretation": clinical_note,
        "equation": "2021 CKD-EPI Creatinine (Race-Free)",
    }


def calculate_biomarker_percentage_change(
    biomarker_name: str,
    baseline_value: float,
    current_value: float,
    unit: str = "",
) -> dict[str, Any]:
    """Calculates absolute change, percentage change, and clinical favorability between visits.

    Args:
        biomarker_name: Name of biomarker (e.g. 'LDL', 'Fasting Glucose', 'eGFR', 'HbA1c', 'Triglycerides').
        baseline_value: Previous or baseline lab result.
        current_value: Current lab result.
        unit: Optional unit string (e.g. 'mg/dL', '%').

    Returns:
        A dictionary with absolute change, percentage change, direction, and clinical trend evaluation.
    """
    if baseline_value == 0:
        return {"error": "Baseline value cannot be 0 to compute percentage change."}

    abs_change = round(current_value - baseline_value, 2)
    pct_change = round((abs_change / baseline_value) * 100, 1)

    direction = "INCREASED" if abs_change > 0 else ("DECREASED" if abs_change < 0 else "UNCHANGED")

    # Biomarkers where a decrease is clinically favorable
    lower_is_better = [
        "ldl", "total_cholesterol", "cholesterol", "triglycerides", "glucose",
        "fasting_glucose", "blood_glucose", "hba1c", "a1c", "creatinine", "bun", "alt",
    ]
    # Biomarkers where an increase is clinically favorable
    higher_is_better = ["hdl", "hdl_cholesterol", "egfr"]

    clean_name = biomarker_name.strip().lower().replace("-", "_").replace(" ", "_")

    if abs_change == 0:
        favorability = "STABLE"
        msg = f"{biomarker_name} has remained completely stable at {current_value} {unit}."
    elif any(k in clean_name for k in higher_is_better):
        if abs_change > 0:
            favorability = "FAVORABLE (IMPROVEMENT)"
            msg = f"{biomarker_name} improved by {pct_change}% (rose from {baseline_value} to {current_value} {unit})."
        else:
            favorability = "UNFAVORABLE (DECREASE)"
            msg = f"{biomarker_name} declined by {abs(pct_change)}% (from {baseline_value} to {current_value} {unit})."
    elif any(k in clean_name for k in lower_is_better):
        if abs_change < 0:
            favorability = "FAVORABLE (IMPROVEMENT)"
            msg = f"{biomarker_name} improved by {abs(pct_change)}% (dropped from {baseline_value} to {current_value} {unit})."
        else:
            favorability = "UNFAVORABLE (INCREASE)"
            msg = f"{biomarker_name} rose by {pct_change}% (from {baseline_value} to {current_value} {unit}). Discuss with your doctor."
    else:
        favorability = "NEUTRAL"
        msg = f"{biomarker_name} changed by {pct_change}% ({baseline_value} -> {current_value} {unit})."

    return {
        "success": True,
        "biomarker_name": biomarker_name,
        "baseline_value": baseline_value,
        "current_value": current_value,
        "unit": unit,
        "absolute_change": abs_change,
        "percentage_change": pct_change,
        "direction": direction,
        "clinical_trend": favorability,
        "summary": msg,
    }
