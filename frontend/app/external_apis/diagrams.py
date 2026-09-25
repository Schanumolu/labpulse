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

"""Clinical Explainer Diagram Generator for LabPulse.

Generates intuitive, patient-friendly anatomical and physiological diagrams
(e.g., Arterial Plaque / LDL vs HDL, Kidney Filtration & eGFR, Insulin & Glucose Uptake)
and persists them to ADK Session Artifacts, Google Cloud Storage (GCS), and local disk.
"""

from __future__ import annotations

import base64
import datetime
import os
import uuid
from typing import Any

from google.genai import types

_LOCAL_DIAGRAM_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    "diagrams",
)
os.makedirs(_LOCAL_DIAGRAM_DIR, exist_ok=True)


def _get_gcs_bucket():
    bucket_name = os.environ.get("LAB_STORAGE_BUCKET") or os.environ.get("LOGS_BUCKET_NAME")
    if not bucket_name:
        return None
    try:
        from google.cloud import storage

        client = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
        return client.bucket(bucket_name)
    except Exception:
        return None


def _generate_artery_diagram() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%" style="background:#ffffff; font-family:system-ui, -apple-system, sans-serif;">
  <rect width="800" height="450" fill="#f8fafc" rx="12"/>
  <text x="400" y="38" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a">Arterial Impact: Normal Artery vs. Atherosclerosis (LDL Plaque)</text>
  <text x="400" y="62" text-anchor="middle" font-size="14" fill="#64748b">Comparison of healthy blood flow versus lipid core plaque narrowing</text>

  <!-- Left: Healthy Artery -->
  <g transform="translate(60, 90)">
    <rect width="320" height="300" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" rx="10"/>
    <text x="160" y="35" text-anchor="middle" font-size="18" font-weight="600" fill="#16a34a">Healthy Open Artery</text>
    <circle cx="160" cy="150" r="90" fill="#fecaca" stroke="#dc2626" stroke-width="6"/>
    <circle cx="160" cy="150" r="70" fill="#fee2e2"/>
    <circle cx="140" cy="135" r="14" fill="#b91c1c"/>
    <circle cx="175" cy="130" r="14" fill="#b91c1c"/>
    <circle cx="150" cy="165" r="14" fill="#b91c1c"/>
    <circle cx="180" cy="168" r="14" fill="#b91c1c"/>
    <circle cx="120" cy="160" r="9" fill="#2563eb"/>
    <text x="120" y="163" text-anchor="middle" font-size="8" font-weight="700" fill="#ffffff">HDL</text>
    <text x="160" y="260" text-anchor="middle" font-size="13" font-weight="600" fill="#15803d">Wide Lumen (100% Flow)</text>
    <text x="160" y="280" text-anchor="middle" font-size="12" fill="#64748b">HDL clears excess cholesterol to liver</text>
  </g>

  <!-- Right: Plaque Blocked Artery -->
  <g transform="translate(420, 90)">
    <rect width="320" height="300" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" rx="10"/>
    <text x="160" y="35" text-anchor="middle" font-size="18" font-weight="600" fill="#dc2626">Atherosclerosis (High LDL)</text>
    <circle cx="160" cy="150" r="90" fill="#fecaca" stroke="#dc2626" stroke-width="6"/>
    <circle cx="160" cy="150" r="70" fill="#fee2e2"/>
    <path d="M 95 130 Q 160 85 225 130 Q 190 200 95 130 Z" fill="#facc15" stroke="#ca8a04" stroke-width="3"/>
    <text x="160" y="140" text-anchor="middle" font-size="11" font-weight="700" fill="#854d0e">Lipid &amp; Plaque Core</text>
    <circle cx="150" cy="190" r="12" fill="#b91c1c"/>
    <circle cx="175" cy="195" r="12" fill="#b91c1c"/>
    <circle cx="120" cy="115" r="7" fill="#dc2626"/>
    <text x="120" y="117" text-anchor="middle" font-size="6" font-weight="700" fill="#ffffff">LDL</text>
    <circle cx="195" cy="115" r="7" fill="#dc2626"/>
    <text x="195" y="117" text-anchor="middle" font-size="6" font-weight="700" fill="#ffffff">LDL</text>
    <text x="160" y="260" text-anchor="middle" font-size="13" font-weight="600" fill="#b91c1c">Constricted Lumen (~40% Flow)</text>
    <text x="160" y="280" text-anchor="middle" font-size="12" fill="#64748b">Elevated risk of cardiovascular events</text>
  </g>
  <text x="400" y="420" text-anchor="middle" font-size="12" fill="#94a3b8">Source: LabPulse Clinical Explainer Diagrams</text>
</svg>"""


def _generate_kidney_diagram() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%" style="background:#ffffff; font-family:system-ui, -apple-system, sans-serif;">
  <rect width="800" height="450" fill="#f8fafc" rx="12"/>
  <text x="400" y="38" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a">Kidney Nephron Filtration &amp; eGFR (Glomerular Filtration Rate)</text>
  <text x="400" y="62" text-anchor="middle" font-size="14" fill="#64748b">How blood creatinine &amp; BUN are filtered to maintain metabolic balance</text>

  <!-- Left: Nephron Anatomy Diagram -->
  <g transform="translate(60, 90)">
    <rect width="320" height="300" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" rx="10"/>
    <text x="160" y="32" text-anchor="middle" font-size="17" font-weight="600" fill="#0284c7">Glomerulus &amp; Capsule</text>
    <path d="M 80 120 C 80 70, 240 70, 240 120 C 240 190, 180 200, 180 240 L 140 240 C 140 200, 80 190, 80 120 Z" fill="#e0f2fe" stroke="#0284c7" stroke-width="4"/>
    <circle cx="160" cy="120" r="38" fill="#fecaca" stroke="#dc2626" stroke-width="4"/>
    <text x="160" y="115" text-anchor="middle" font-size="11" font-weight="700" fill="#991b1b">High Pressure</text>
    <text x="160" y="130" text-anchor="middle" font-size="10" font-weight="600" fill="#991b1b">Capillary Bed</text>
    <path d="M 160 165 L 160 215" stroke="#0284c7" stroke-width="3" stroke-dasharray="4,4"/>
    <polygon points="160,225 154,213 166,213" fill="#0284c7"/>
    <text x="160" y="270" text-anchor="middle" font-size="12" font-weight="600" fill="#0369a1">Filtrate (Urine Precursor)</text>
    <text x="160" y="288" text-anchor="middle" font-size="11" fill="#64748b">Filters ~180 Liters daily</text>
  </g>

  <!-- Right: eGFR Stages Chart -->
  <g transform="translate(420, 90)">
    <rect width="320" height="300" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" rx="10"/>
    <text x="160" y="32" text-anchor="middle" font-size="17" font-weight="600" fill="#0f172a">eGFR Stages (mL/min)</text>
    <g transform="translate(20, 55)">
      <rect x="0" y="0" width="280" height="35" rx="6" fill="#dcfce7" stroke="#16a34a" stroke-width="1.5"/>
      <text x="15" y="22" font-size="13" font-weight="700" fill="#15803d">&gt; 90: Stage 1 (Normal / Optimal)</text>
      <rect x="0" y="45" width="280" height="35" rx="6" fill="#fef9c3" stroke="#ca8a04" stroke-width="1.5"/>
      <text x="15" y="67" font-size="13" font-weight="700" fill="#854d0e">60 - 89: Stage 2 (Mildly Decreased)</text>
      <rect x="0" y="90" width="280" height="35" rx="6" fill="#ffedd5" stroke="#ea580c" stroke-width="1.5"/>
      <text x="15" y="112" font-size="13" font-weight="700" fill="#9a3412">30 - 59: Stage 3 (Moderate CKD)</text>
      <rect x="0" y="135" width="280" height="35" rx="6" fill="#fee2e2" stroke="#dc2626" stroke-width="1.5"/>
      <text x="15" y="157" font-size="13" font-weight="700" fill="#991b1b">15 - 29: Stage 4 (Severely Decreased)</text>
      <rect x="0" y="180" width="280" height="35" rx="6" fill="#f3e8ff" stroke="#7e22ce" stroke-width="1.5"/>
      <text x="15" y="202" font-size="13" font-weight="700" fill="#581c87">&lt; 15: Stage 5 (Kidney Failure)</text>
    </g>
    <text x="160" y="285" text-anchor="middle" font-size="11" fill="#64748b">Calculated via CKD-EPI race-free equation</text>
  </g>
  <text x="400" y="420" text-anchor="middle" font-size="12" fill="#94a3b8">Source: LabPulse Clinical Explainer Diagrams</text>
</svg>"""


def _generate_glucose_diagram() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 450" width="100%" height="100%" style="background:#ffffff; font-family:system-ui, -apple-system, sans-serif;">
  <rect width="800" height="450" fill="#f8fafc" rx="12"/>
  <text x="400" y="38" text-anchor="middle" font-size="22" font-weight="700" fill="#0f172a">Insulin &amp; Blood Glucose Cellular Uptake</text>
  <text x="400" y="62" text-anchor="middle" font-size="14" fill="#64748b">Mechanism of cellular glucose absorption vs. insulin resistance (HbA1c &amp; Glucose)</text>

  <!-- Left: Normal Insulin Function -->
  <g transform="translate(60, 90)">
    <rect width="320" height="300" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" rx="10"/>
    <text x="160" y="35" text-anchor="middle" font-size="18" font-weight="600" fill="#16a34a">Normal Insulin Sensitivity</text>
    <rect x="40" y="130" width="240" height="110" rx="16" fill="#dbeafe" stroke="#2563eb" stroke-width="3"/>
    <text x="160" y="195" text-anchor="middle" font-size="14" font-weight="600" fill="#1e40af">Muscle / Adipose Cell</text>
    <rect x="70" y="115" width="25" height="20" fill="#9333ea" rx="4"/>
    <circle cx="82" cy="95" r="8" fill="#a855f7"/>
    <text x="82" y="78" text-anchor="middle" font-size="10" font-weight="700" fill="#6b21a8">Insulin</text>
    <rect x="180" y="115" width="40" height="20" fill="#16a34a" rx="4"/>
    <text x="200" y="78" text-anchor="middle" font-size="10" font-weight="700" fill="#15803d">Glucose (In)</text>
    <circle cx="200" cy="95" r="7" fill="#eab308"/>
    <path d="M 200 105 L 200 145" stroke="#16a34a" stroke-width="3"/>
    <text x="160" y="260" text-anchor="middle" font-size="13" font-weight="600" fill="#15803d">Insulin Unlocks GLUT4 Gate</text>
    <text x="160" y="280" text-anchor="middle" font-size="12" fill="#64748b">Glucose enters cell, blood sugar normal</text>
  </g>

  <!-- Right: Insulin Resistance -->
  <g transform="translate(420, 90)">
    <rect width="320" height="300" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" rx="10"/>
    <text x="160" y="35" text-anchor="middle" font-size="18" font-weight="600" fill="#dc2626">Insulin Resistance (High A1c)</text>
    <rect x="40" y="130" width="240" height="110" rx="16" fill="#fee2e2" stroke="#dc2626" stroke-width="3"/>
    <text x="160" y="195" text-anchor="middle" font-size="14" font-weight="600" fill="#991b1b">Insulin-Resistant Cell</text>
    <rect x="70" y="115" width="25" height="20" fill="#9333ea" rx="4"/>
    <text x="82" y="78" text-anchor="middle" font-size="10" font-weight="700" fill="#dc2626">Blocked</text>
    <circle cx="82" cy="95" r="8" fill="#a855f7"/>
    <rect x="180" y="115" width="40" height="20" fill="#b91c1c" rx="4"/>
    <circle cx="200" cy="95" r="7" fill="#eab308"/>
    <circle cx="225" cy="85" r="7" fill="#eab308"/>
    <circle cx="175" cy="85" r="7" fill="#eab308"/>
    <text x="200" y="68" text-anchor="middle" font-size="10" font-weight="700" fill="#b91c1c">Excess Glucose In Blood</text>
    <text x="160" y="260" text-anchor="middle" font-size="13" font-weight="600" fill="#b91c1c">Signaling Impaired</text>
    <text x="160" y="280" text-anchor="middle" font-size="12" fill="#64748b">Glucose builds up in blood → Elevated A1C</text>
  </g>
  <text x="400" y="420" text-anchor="middle" font-size="12" fill="#94a3b8">Source: LabPulse Clinical Explainer Diagrams</text>
</svg>"""


def generate_anatomical_diagram(
    topic: str,
    title: str = "",
) -> dict[str, Any]:
    """Generates an intuitive, patient-friendly anatomical diagram explaining a lab biomarker mechanism.

    Persists the diagram to Google Cloud Storage (GCS), local disk, and returns a base64
    `image_markdown` snippet that renders directly inside the chat interface.

    Args:
        topic: The clinical topic or biomarker (e.g., 'Arterial Plaque', 'HDL vs LDL', 'Kidney Filtration', 'eGFR', 'Glucose', 'Insulin Resistance').
        title: Optional custom diagram title.

    Returns:
        A dictionary with diagram ID, topic, description, image_markdown, and cloud GCS URI.
    """
    clean_topic = topic.strip().lower()
    now = datetime.datetime.now(datetime.timezone.utc)
    diagram_id = f"diag_{now.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    if any(k in clean_topic for k in ["artery", "arterial", "plaque", "ldl", "hdl", "cholesterol", "lipid"]):
        diagram_type = "Arterial Impact & Plaque"
        svg_content = _generate_artery_diagram()
        explanation = "Illustrates how excess LDL particles deposit in arterial walls creating atherosclerotic plaque, contrasted against open flow maintained by HDL."
    elif any(k in clean_topic for k in ["kidney", "nephron", "egfr", "creatinine", "bun", "renal", "filtration"]):
        diagram_type = "Kidney Nephron Filtration"
        svg_content = _generate_kidney_diagram()
        explanation = "Visualizes nephron capillary filtration and clinical eGFR stages from normal (>90) to moderate and severe reduction."
    else:
        diagram_type = "Insulin & Glucose Uptake"
        svg_content = _generate_glucose_diagram()
        explanation = "Visualizes cellular glucose absorption via GLUT4 transporters and explains how insulin resistance leads to elevated blood glucose and HbA1c."

    # Save to local storage
    file_name = f"{diagram_id}.svg"
    local_path = os.path.join(_LOCAL_DIAGRAM_DIR, file_name)
    with open(local_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    # Save to Cloud Storage
    gcs_uri = None
    bucket = _get_gcs_bucket()
    if bucket:
        try:
            blob = bucket.blob(f"diagrams/{file_name}")
            blob.upload_from_string(svg_content, content_type="image/svg+xml")
            gcs_uri = f"gs://{bucket.name}/diagrams/{file_name}"
        except Exception:
            pass

    # Create clean image URL and self-contained base64 data URI
    b64_svg = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
    data_uri = f"data:image/svg+xml;base64,{b64_svg}"
    diagram_title = title or diagram_type
    image_url = f"/api/diagrams/{file_name}"
    image_markdown = f"![{diagram_title}]({image_url})"

    return {
        "success": True,
        "diagram_id": diagram_id,
        "title": diagram_title,
        "topic": topic,
        "diagram_type": diagram_type,
        "explanation": explanation,
        "image_url": image_url,
        "image_markdown": image_markdown,
        "data_uri": data_uri,
        "gcs_uri": gcs_uri,
        "local_path": local_path,
        "display_instruction": (
            f"The diagram has been generated. You MUST embed this exact markdown snippet in your response: {image_markdown} "
            "so that the diagram renders directly and visually for the user in their chat message."
        ),
    }
