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

"""Storage module for uploaded patient lab tests with failure recovery support.

Stores raw uploaded tests to Google Cloud Storage (GCS) and local backup so they
can be retrieved at any time or resumed if parsing / result generation is interrupted.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any

_LOCAL_STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    "uploaded_labtests",
)
os.makedirs(_LOCAL_STORAGE_DIR, exist_ok=True)


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


def store_uploaded_labtest(
    raw_content: str,
    file_name: str = "lab_report.txt",
    patient_id: str = "default_patient",
) -> dict[str, Any]:
    """Stores an uploaded lab test document or raw results into persistent storage before processing.

    This ensures raw test data is safely preserved if parsing or analysis is interrupted in the middle.

    Args:
        raw_content: The text, CSV, JSON, or lab report content provided by the patient.
        file_name: The original filename or label (e.g. 'lipid_sept2026.pdf', 'blood_work.txt').
        patient_id: Patient or user identifier.

    Returns:
        A dictionary containing the assigned test_id, storage status, timestamps, and cloud URI.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    short_uuid = uuid.uuid4().hex[:6]
    test_id = f"lab_{now.strftime('%Y%m%d_%H%M%S')}_{short_uuid}"

    record: dict[str, Any] = {
        "test_id": test_id,
        "patient_id": patient_id,
        "file_name": file_name,
        "status": "UPLOADED",
        "raw_content": raw_content,
        "uploaded_at": now.isoformat(),
        "last_updated": now.isoformat(),
        "extracted_biomarkers": [],
        "error_message": None,
        "gcs_uri": None,
    }

    # 1. Write to local storage
    local_path = os.path.join(_LOCAL_STORAGE_DIR, f"{test_id}.json")
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    # 2. Write to Cloud Storage if available
    bucket = _get_gcs_bucket()
    if bucket:
        try:
            blob = bucket.blob(f"uploaded_labtests/{test_id}.json")
            blob.upload_from_string(
                json.dumps(record, indent=2),
                content_type="application/json",
            )
            record["gcs_uri"] = f"gs://{bucket.name}/uploaded_labtests/{test_id}.json"
            # Update local mirror with GCS uri
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
        except Exception as e:
            record["gcs_error"] = str(e)

    return {
        "success": True,
        "test_id": test_id,
        "status": "UPLOADED",
        "file_name": file_name,
        "gcs_uri": record.get("gcs_uri"),
        "message": f"Lab test '{file_name}' safely stored under ID '{test_id}'. Data is preserved for retrieval or recovery.",
    }


def get_stored_labtest(test_id: str) -> dict[str, Any]:
    """Retrieves a previously stored lab test record by its test_id.

    Args:
        test_id: The unique identifier generated when the lab test was uploaded.

    Returns:
        The full test record including raw content, status, and any extracted biomarkers.
    """
    # Try local first
    local_path = os.path.join(_LOCAL_STORAGE_DIR, f"{test_id}.json")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Try GCS
    bucket = _get_gcs_bucket()
    if bucket:
        try:
            blob = bucket.blob(f"uploaded_labtests/{test_id}.json")
            if blob.exists():
                data = json.loads(blob.download_as_text())
                # Sync locally
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return data
        except Exception as e:
            return {"error": f"Failed reading from Cloud Storage: {e}"}

    return {"error": f"Lab test with ID '{test_id}' not found."}


def list_stored_labtests(patient_id: str = "") -> list[dict[str, Any]]:
    """Lists all stored lab test uploads, showing their status (UPLOADED, PROCESSING, COMPLETED, FAILED).

    Args:
        patient_id: Optional patient filter. If empty, returns all uploads.

    Returns:
        A list of lab test summaries with test_id, file_name, status, upload time, and error details.
    """
    results = []

    # Read from local storage dir
    if os.path.exists(_LOCAL_STORAGE_DIR):
        for fname in sorted(os.listdir(_LOCAL_STORAGE_DIR), reverse=True):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(_LOCAL_STORAGE_DIR, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if not patient_id or data.get("patient_id") == patient_id:
                            results.append({
                                "test_id": data.get("test_id"),
                                "file_name": data.get("file_name"),
                                "patient_id": data.get("patient_id"),
                                "status": data.get("status"),
                                "uploaded_at": data.get("uploaded_at"),
                                "biomarker_count": len(data.get("extracted_biomarkers") or []),
                                "error_message": data.get("error_message"),
                                "gcs_uri": data.get("gcs_uri"),
                            })
                except Exception:
                    continue

    return results


def update_labtest_status(
    test_id: str,
    status: str,
    extracted_biomarkers: list[dict[str, Any]] | None = None,
    error_message: str = "",
) -> dict[str, Any]:
    """Updates the processing status of a stored lab test (e.g. PROCESSING, COMPLETED, FAILED).

    Args:
        test_id: The unique identifier of the stored lab test.
        status: The new status ('PROCESSING', 'COMPLETED', 'FAILED').
        extracted_biomarkers: List of extracted biomarker dictionaries, if available.
        error_message: Error details if processing failed in the middle.

    Returns:
        Confirmation dictionary with the updated record state.
    """
    record = get_stored_labtest(test_id)
    if "error" in record:
        return record

    record["status"] = status
    record["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if extracted_biomarkers is not None:
        record["extracted_biomarkers"] = extracted_biomarkers
    if error_message:
        record["error_message"] = error_message

    # Save to local
    local_path = os.path.join(_LOCAL_STORAGE_DIR, f"{test_id}.json")
    with open(local_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    # Save to GCS
    bucket = _get_gcs_bucket()
    if bucket:
        try:
            blob = bucket.blob(f"uploaded_labtests/{test_id}.json")
            blob.upload_from_string(
                json.dumps(record, indent=2),
                content_type="application/json",
            )
        except Exception:
            pass

    return {
        "success": True,
        "test_id": test_id,
        "status": status,
        "message": f"Updated lab test '{test_id}' status to {status}.",
    }


def recover_and_process_labtest(test_id: str) -> dict[str, Any]:
    """Recovers a stored lab test that failed or was interrupted, parsing its raw content and recording results.

    Args:
        test_id: The ID of the stored lab test to recover and process.

    Returns:
        The recovered test record with extracted biomarkers and clinical range evaluations.
    """
    from app.clinical_tools import lookup_biomarker, record_lab_entry

    record = get_stored_labtest(test_id)
    if "error" in record:
        return record

    raw_text = record.get("raw_content", "")
    update_labtest_status(test_id, status="PROCESSING")

    try:
        extracted = []
        # Parse simple key-value or line-based test values
        # e.g. "Glucose: 115 mg/dL", "LDL 142", "HbA1c = 6.8%"
        import re

        patterns = [
            r"([a-zA-Z0-9\s\-]+)[\:\=\s]+([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z\%\/\^0-9]+)?",
        ]

        for line in raw_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            for pat in patterns:
                match = re.search(pat, line_str)
                if match:
                    raw_name = match.group(1).strip()
                    val_str = match.group(2).strip()
                    unit_str = (match.group(3) or "").strip()

                    lookup = lookup_biomarker(raw_name)
                    if lookup.get("found"):
                        val_float = float(val_str)
                        canonical_unit = unit_str or lookup.get("unit", "")
                        rec = record_lab_entry(
                            biomarker_name=lookup["name"],
                            value=val_float,
                            unit=canonical_unit,
                            notes=f"Recovered from {record.get('file_name', 'upload')}",
                        )
                        extracted.append(rec.get("entry"))
                    break

        update_labtest_status(
            test_id,
            status="COMPLETED",
            extracted_biomarkers=extracted,
        )

        return {
            "success": True,
            "test_id": test_id,
            "status": "COMPLETED",
            "file_name": record.get("file_name"),
            "extracted_count": len(extracted),
            "biomarkers": extracted,
            "message": f"Successfully recovered and parsed {len(extracted)} biomarkers from test '{test_id}'.",
        }
    except Exception as e:
        update_labtest_status(test_id, status="FAILED", error_message=str(e))
        return {
            "success": False,
            "test_id": test_id,
            "status": "FAILED",
            "error": str(e),
            "message": f"Recovery failed: {e}. Raw content remains safely stored for another attempt.",
        }
