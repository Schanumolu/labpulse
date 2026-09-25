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

import os
from app.external_apis.medlineplus import fetch_medlineplus_topic
from app.external_apis.openfda import check_drug_lab_interactions, get_drug_safety_summary
from app.external_apis.diagrams import generate_anatomical_diagram


def test_medlineplus_lookup():
    result = fetch_medlineplus_topic("Cholesterol")
    assert result["found"] is True
    assert "Cholesterol" in result["title"]
    assert result["loinc_code"] == "2093-3"
    assert "official_url" in result


def test_openfda_drug_interaction():
    result = check_drug_lab_interactions("atorvastatin", "ALT")
    assert result["found"] is True
    assert result["interaction_detected"] is True
    assert len(result["fda_label_excerpts"]) > 0


def test_openfda_safety_summary():
    result = get_drug_safety_summary("lisinopril")
    assert result["found"] is True
    assert "lisinopril" in str(result["brand_names"]).lower() or "lisinopril" in str(result["active_substance"]).lower()


def test_diagram_generation():
    result = generate_anatomical_diagram("Arterial Plaque LDL vs HDL")
    assert result["success"] is True
    assert os.path.exists(result["local_path"])
    with open(result["local_path"], "r") as f:
        content = f.read()
    assert "<svg" in content
    assert "Atherosclerosis" in content
