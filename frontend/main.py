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

"""Responsive FastAPI web server & proxy for LabPulse on Cloud Run.

Features:
- Dedicated drag-and-drop file upload to Google Cloud Storage (GCS).
- Multimodal lab report processing (PDF text extraction, PNG/JPG vision).
- Forwards requests to local ADK (/run_sse) or deployed A2A Agent Runtime.
- Supplies A2UI cards, reference range data, and doctor checklist components.
"""

from __future__ import annotations

import base64
import datetime
import io
import json
import os
import uuid
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from google.cloud import storage
    _storage_client = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
except Exception:
    _storage_client = None

app = FastAPI(title="LabPulse Web Frontend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOCAL_AGENT_URL = os.environ.get("LOCAL_AGENT_URL", "http://127.0.0.1:8080")
RESOURCE = os.environ.get("AGENT_ENGINE_RESOURCE_NAME")
GCS_BUCKET_NAME = (
    os.environ.get("LAB_STORAGE_BUCKET")
    or os.environ.get("LOGS_BUCKET_NAME")
    or "bwg3-qwiklabs-gcp-03-1a2bb3dfcd68"
)

_session_map: dict[str, str] = {}


def _upload_bytes_to_gcs(file_bytes: bytes, filename: str, content_type: str) -> str | None:
    """Uploads file bytes to Google Cloud Storage and returns the gs:// URI."""
    if not _storage_client or not GCS_BUCKET_NAME:
        return None
    try:
        bucket = _storage_client.bucket(GCS_BUCKET_NAME)
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_name = filename.replace(" ", "_").replace("/", "_")
        blob_path = f"uploads/{now_str}_{uuid.uuid4().hex[:6]}_{safe_name}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        return f"gs://{GCS_BUCKET_NAME}/{blob_path}"
    except Exception as e:
        print(f"Warning: Could not upload to GCS: {e}")
        return None


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extracts text content from an uploaded PDF file."""
    if not pypdf:
        return ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for i, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            if txt.strip():
                pages_text.append(f"--- Page {i + 1} ---\n{txt.strip()}")
        return "\n\n".join(pages_text)
    except Exception as e:
        return f"[PDF parsing note: Could not extract digital text: {e}]"


async def _get_or_create_local_session(client: httpx.AsyncClient, user_id: str) -> str:
    """Gets an existing local ADK session or creates a new one."""
    if user_id in _session_map:
        return _session_map[user_id]

    create_url = f"{LOCAL_AGENT_URL}/apps/app/users/{user_id}/sessions"
    try:
        resp = await client.post(create_url, json={}, timeout=10)
        if resp.status_code == 200:
            sess_id = resp.json().get("id")
            if sess_id:
                _session_map[user_id] = sess_id
                return sess_id
    except Exception:
        pass

    fallback_id = str(uuid.uuid4())
    _session_map[user_id] = fallback_id
    return fallback_id


@app.post("/api/upload")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """Uploads a lab report (PDF, PNG, JPG) to GCS and extracts initial content."""
    filename = file.filename or "uploaded_lab_report"
    content_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()

    gcs_uri = _upload_bytes_to_gcs(file_bytes, filename, content_type)
    extracted_text = ""
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        extracted_text = _extract_pdf_text(file_bytes)

    return JSONResponse({
        "success": True,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(file_bytes),
        "gcs_uri": gcs_uri or f"gs://{GCS_BUCKET_NAME}/uploads/{filename}",
        "extracted_preview": extracted_text[:400] if extracted_text else "",
        "has_digital_text": bool(extracted_text.strip()),
    })


@app.post("/chat")
async def chat(
    message: str = Form(""),
    user_id: str = Form("labpulse-patient"),
    gcs_uri: str = Form(""),
    file: UploadFile | None = File(None),
):
    """Processes conversational turns, uploaded files, and GCS URIs."""
    parts_to_send: list[dict[str, Any]] = []
    file_context_lines: list[str] = []

    # Handle direct file attachment from form
    if file and file.filename:
        filename = file.filename
        content_type = file.content_type or "application/octet-stream"
        file_bytes = await file.read()
        uploaded_gcs_uri = _upload_bytes_to_gcs(file_bytes, filename, content_type)
        effective_gcs_uri = uploaded_gcs_uri or gcs_uri or f"gs://{GCS_BUCKET_NAME}/uploads/{filename}"

        file_context_lines.append(f"Patient uploaded lab test report file: '{filename}'")
        file_context_lines.append(f"GCS Storage URI: {effective_gcs_uri}")

        if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            extracted = _extract_pdf_text(file_bytes)
            if extracted:
                file_context_lines.append(f"Extracted PDF Document Text:\n```text\n{extracted}\n```")
        elif content_type.startswith("image/"):
            b64_img = base64.b64encode(file_bytes).decode("utf-8")
            parts_to_send.append({
                "inline_data": {
                    "mime_type": content_type,
                    "data": b64_img,
                }
            })
            file_context_lines.append("Patient attached an image scan of their lab paperwork (included as visual input).")
    elif gcs_uri:
        file_context_lines.append(f"Patient uploaded lab report stored at GCS URI: {gcs_uri}")

    if file_context_lines:
        file_context_lines.append(
            "[AUTOMATIC STORAGE INSTRUCTION: Store this lab test report to persistent storage immediately using store_uploaded_labtest by default. Do not prompt the user for permission to save.]"
        )

    context_str = "\n".join(file_context_lines)
    full_prompt = f"{context_str}\n\nPatient Note/Question: {message}".strip() if context_str else message.strip()

    if not full_prompt and not parts_to_send:
        return JSONResponse({"parts": [{"kind": "text", "text": "Please provide your question or upload a lab test report."}]})

    if full_prompt:
        parts_to_send.insert(0, {"text": full_prompt})

    # Forward to local ADK agent runner
    async with httpx.AsyncClient(timeout=120) as client:
        session_id = await _get_or_create_local_session(client, user_id)
        run_url = f"{LOCAL_AGENT_URL}/run_sse"
        payload = {
            "appName": "app",
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": parts_to_send,
            },
        }

        collected_parts: list[dict[str, Any]] = []
        try:
            async with client.stream("POST", run_url, json=payload) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                        content = event.get("content", {})
                        for part in content.get("parts", []):
                            inline_data = part.get("inline_data")
                            if inline_data and inline_data.get("mime_type") == "application/json+a2ui":
                                b64_d = inline_data.get("data", "")
                                raw_json = base64.b64decode(b64_d).decode("utf-8")
                                collected_parts.append({"kind": "a2ui", "data": json.loads(raw_json)})
                            elif "text" in part and part["text"]:
                                collected_parts.append({"kind": "text", "text": part["text"]})
                    except Exception:
                        pass
        except Exception as e:
            return JSONResponse({"parts": [{"kind": "text", "text": f"Error reaching LabPulse Agent: {e}"}]})

    if not collected_parts:
        collected_parts = [{"kind": "text", "text": "(LabPulse evaluated your results. No additional response was generated.)"}]

    return JSONResponse({"parts": collected_parts})


@app.get("/api/diagrams/{filename}")
@app.get("/diagrams/{filename}")
async def serve_diagram(filename: str):
    """Serves a generated SVG diagram directly from disk or downloads from GCS."""
    local_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app",
        "storage",
        "diagrams",
    )
    local_file = os.path.join(local_dir, filename)
    if os.path.isfile(local_file):
        with open(local_file, "rb") as f:
            return Response(content=f.read(), media_type="image/svg+xml")

    # If not on local disk, fetch from GCS
    if _storage_client and GCS_BUCKET_NAME:
        try:
            bucket = _storage_client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(f"diagrams/{filename}")
            if blob.exists():
                data = blob.download_as_bytes()
                return Response(content=data, media_type="image/svg+xml")
        except Exception as e:
            print(f"Error fetching diagram {filename} from GCS: {e}")

    return Response(status_code=404, content=f"Diagram {filename} not found.")


@app.get("/api/image-proxy")
async def image_proxy(uri: str):
    """Proxies images from GCS (gs:// or https://storage.googleapis.com) with auth."""
    if not _storage_client:
        return Response(status_code=500, content="Storage client not configured.")

    try:
        bucket_name = GCS_BUCKET_NAME
        blob_path = uri

        if uri.startswith("gs://"):
            parts = uri[5:].split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ""
        elif "storage.googleapis.com/" in uri:
            parts = uri.split("storage.googleapis.com/", 1)[1].split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ""

        bucket = _storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        if not blob.exists():
            return Response(status_code=404, content="Image not found in storage.")

        content = blob.download_as_bytes()
        media_type = blob.content_type or "image/svg+xml"
        if blob_path.endswith(".svg"):
            media_type = "image/svg+xml"
        elif blob_path.endswith(".png"):
            media_type = "image/png"
        elif blob_path.endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"

        return Response(content=content, media_type=media_type)
    except Exception as e:
        return Response(status_code=500, content=f"Error retrieving image: {e}")


@app.get("/api/health-devices")
async def health_devices_endpoint(device: str = "apple_health", patient_id: str = "default_patient"):
    """Returns connected health device telemetry (heart rate, body temp, sleep, SpO2)."""
    try:
        from app.health_devices import get_health_device_metrics
        data = get_health_device_metrics(patient_id=patient_id, device_type=device)
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.get("/api/lab-history")
async def lab_history_endpoint(patient_id: str = "default_patient"):
    """Returns all stored lab test reports and recorded entries for review."""
    try:
        from app.lab_storage import list_stored_labtests
        from app.clinical_tools import get_lab_history

        stored = list_stored_labtests()
        recorded = get_lab_history()
        return JSONResponse({
            "success": True,
            "patient_id": patient_id,
            "stored_reports": stored,
            "recorded_history": recorded,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@app.post("/api/compare-results")
async def compare_results_endpoint(request: Request):
    """Compares multiple lab results or visits and calculates percentage changes with high/low badges."""
    try:
        from app.clinical_calculator import calculate_biomarker_percentage_change
        from app.lab_storage import get_stored_labtest

        body = await request.json()
        baseline_id = body.get("baseline_test_id")
        current_id = body.get("current_test_id")
        custom_baseline = body.get("baseline_biomarkers", {})
        custom_current = body.get("current_biomarkers", {})

        baseline_map: dict[str, float] = {}
        current_map: dict[str, float] = {}
        baseline_label = baseline_id or "Baseline Visit"
        current_label = current_id or "Current Visit"

        # If test IDs provided, load contents
        if baseline_id:
            b_data = get_stored_labtest(baseline_id)
            if b_data.get("success"):
                baseline_label = f"{b_data.get('file_name', baseline_id)} ({b_data.get('created_at', '')[:10]})"
                baseline_map.update(b_data.get("extracted_biomarkers") or {})
        if current_id:
            c_data = get_stored_labtest(current_id)
            if c_data.get("success"):
                current_label = f"{c_data.get('file_name', current_id)} ({c_data.get('created_at', '')[:10]})"
                current_map.update(c_data.get("extracted_biomarkers") or {})

        baseline_map.update(custom_baseline)
        current_map.update(custom_current)

        # Fallback sample clinical comparison if empty
        if not baseline_map and not current_map:
            baseline_label = "Visit 1 (June 2026)"
            current_label = "Visit 2 (September 2026)"
            baseline_map = {
                "Total Cholesterol": 248.0,
                "LDL Cholesterol": 168.0,
                "HDL Cholesterol": 38.0,
                "Triglycerides": 210.0,
                "Fasting Glucose": 114.0,
                "HbA1c": 6.2,
                "eGFR": 78.0,
            }
            current_map = {
                "Total Cholesterol": 210.0,
                "LDL Cholesterol": 132.0,
                "HDL Cholesterol": 44.0,
                "Triglycerides": 170.0,
                "Fasting Glucose": 102.0,
                "HbA1c": 5.8,
                "eGFR": 84.0,
            }

        unit_map = {
            "Total Cholesterol": "mg/dL",
            "LDL Cholesterol": "mg/dL",
            "HDL Cholesterol": "mg/dL",
            "Triglycerides": "mg/dL",
            "Fasting Glucose": "mg/dL",
            "HbA1c": "%",
            "eGFR": "mL/min/1.73m²",
            "Creatinine": "mg/dL",
            "BUN": "mg/dL",
            "WBC": "x10³/µL",
        }

        comparisons = []
        all_keys = list(dict.fromkeys(list(baseline_map.keys()) + list(current_map.keys())))
        for k in all_keys:
            b_val = baseline_map.get(k)
            c_val = current_map.get(k)
            unit = unit_map.get(k, "")

            if b_val is not None and c_val is not None:
                calc = calculate_biomarker_percentage_change(
                    biomarker_name=k,
                    baseline_value=float(b_val),
                    current_value=float(c_val),
                    unit=unit,
                )
                comparisons.append({
                    "biomarker": k,
                    "baseline_value": b_val,
                    "current_value": c_val,
                    "unit": unit,
                    "absolute_change": calc.get("absolute_change"),
                    "percentage_change": calc.get("percentage_change"),
                    "direction": calc.get("direction"),
                    "clinical_trend": calc.get("clinical_trend"),
                    "summary": calc.get("summary"),
                })
            else:
                comparisons.append({
                    "biomarker": k,
                    "baseline_value": b_val,
                    "current_value": c_val,
                    "unit": unit,
                    "percentage_change": None,
                    "direction": "N/A",
                    "clinical_trend": "UNCOMPARABLE",
                    "summary": f"Data available only for one visit ({b_val if b_val is not None else c_val} {unit}).",
                })

        return JSONResponse({
            "success": True,
            "baseline_label": baseline_label,
            "current_label": current_label,
            "comparisons": comparisons,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# Static UI serving
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", os.environ.get("FRONTEND_PORT", 3000)))
    print(f"Starting LabPulse web frontend on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
