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

from app.clinical_calculator import (
    calculate_biomarker_percentage_change,
    calculate_cholesterol_ratios,
    calculate_egfr_ckd_epi,
    calculate_hba1c_to_eag,
)


def test_calculate_cholesterol_ratios():
    res = calculate_cholesterol_ratios(total_cholesterol=200, hdl=50, triglycerides=150)
    assert res["success"] is True
    assert res["total_to_hdl_ratio"] == 4.0
    assert res["risk_level"] == "MODERATE"
    assert res["triglyceride_to_hdl_ratio"] == 3.0


def test_calculate_hba1c_to_eag():
    res = calculate_hba1c_to_eag(7.0)
    assert res["success"] is True
    assert res["estimated_average_glucose_mg_dl"] == 154.2
    assert res["clinical_category"] == "DIABETES_TARGET_MET"


def test_calculate_egfr_ckd_epi():
    res_m = calculate_egfr_ckd_epi(serum_creatinine=1.0, age=50, sex="male")
    assert res_m["success"] is True
    assert res_m["egfr_value"] > 80
    assert "Stage" in res_m["stage"]

    res_f = calculate_egfr_ckd_epi(serum_creatinine=0.8, age=50, sex="female")
    assert res_f["success"] is True
    assert res_f["sex"] == "female"


def test_calculate_biomarker_percentage_change():
    res_ldl = calculate_biomarker_percentage_change("LDL", baseline_value=160, current_value=120, unit="mg/dL")
    assert res_ldl["percentage_change"] == -25.0
    assert "FAVORABLE" in res_ldl["clinical_trend"]

    res_hdl = calculate_biomarker_percentage_change("HDL", baseline_value=40, current_value=30, unit="mg/dL")
    assert res_hdl["percentage_change"] == -25.0
    assert "UNFAVORABLE" in res_hdl["clinical_trend"]
