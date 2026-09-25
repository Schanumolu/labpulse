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

"""Health Devices & Wearables Integration Module for LabPulse.

Simulates and ingests telemetry from connected personal health devices
(Apple Health / Apple Watch, Fitbit / Pixel Watch, Garmin, and Google Health Connect).
Tracks:
- Heart Rate: Resting heart rate, current pulse, Heart Rate Variability (HRV), rhythm status.
- Body Temperature: Basal & skin temperature, deviation from personal baseline.
- Sleep Metrics: Total duration, sleep efficiency %, stages (Deep, REM, Light), sleep score.
- Blood Oxygen & Activity: SpO2 %, daily steps, active caloric expenditure.
"""

from __future__ import annotations

import datetime
from typing import Any


DEVICE_PROFILES: dict[str, dict[str, Any]] = {
    "apple_health": {
        "device_name": "Apple Watch Series 10 / Apple HealthKit",
        "sync_protocol": "HealthKit Sync v2.4",
        "supported_sensors": ["ECG", "PPG Optical Heart Rate", "Wrist Temperature", "Blood Oxygen Sensor", "Accelerometer"],
    },
    "fitbit": {
        "device_name": "Google Pixel Watch 3 / Fitbit Health API",
        "sync_protocol": "Fitbit Web API / Health Connect",
        "supported_sensors": ["Continuous Optical Heart Rate", "cEDA Stress", "Skin Temp Variation", "SpO2 Pulse Oximeter"],
    },
    "garmin": {
        "device_name": "Garmin Forerunner 965 / Garmin Connect",
        "sync_protocol": "Garmin Health API v3",
        "supported_sensors": ["Elevate v5 Heart Rate", "Pulse Ox", "Body Battery Engine", "Temperature Sensor"],
    },
    "google_health_connect": {
        "device_name": "Google Health Connect (Universal Android)",
        "sync_protocol": "Health Connect Data Store",
        "supported_sensors": ["Aggregated Multi-Device Telemetry"],
    },
}


def get_health_device_metrics(
    patient_id: str = "default_patient",
    device_type: str = "apple_health",
) -> dict[str, Any]:
    """Retrieves real-time and summary biometric telemetry from connected health devices.

    Args:
        patient_id: Identifier for the patient.
        device_type: Brand/protocol of device ('apple_health', 'fitbit', 'garmin', 'google_health_connect', or 'all').

    Returns:
        Structured dictionary with heart rate, body temperature, sleep metrics, SpO2, and clinical correlation notes.
    """
    clean_brand = device_type.strip().lower()
    if clean_brand not in DEVICE_PROFILES:
        clean_brand = "apple_health"

    profile = DEVICE_PROFILES[clean_brand]
    now = datetime.datetime.now(datetime.timezone.utc)

    # Biometric Telemetry
    heart_rate_data = {
        "resting_bpm": 62,
        "current_bpm": 68,
        "hrv_ms": 52,
        "rhythm_status": "Normal Sinus Rhythm",
        "status_badge": "OPTIMAL",
        "reference_target": "50 - 80 bpm resting",
        "clinical_insight": "Resting heart rate of 62 bpm reflects healthy parasympathetic tone and cardiovascular efficiency.",
    }

    body_temp_data = {
        "current_temp_f": 98.4,
        "current_temp_c": 36.9,
        "baseline_temp_f": 98.2,
        "delta_f": +0.2,
        "status_badge": "NORMAL",
        "reference_target": "97.6°F - 99.0°F (36.4°C - 37.2°C)",
        "clinical_insight": "Normal basal body temperature within baseline circadian range. No signs of systemic inflammation or pyrexia.",
    }

    sleep_data = {
        "total_sleep_hours": 7.4,
        "total_sleep_formatted": "7 hrs 24 mins",
        "sleep_score": 85,
        "sleep_score_label": "Good",
        "efficiency_percent": 88,
        "stages": {
            "deep_sleep_hours": 1.4,
            "deep_sleep_percent": 19,
            "rem_sleep_hours": 1.6,
            "rem_sleep_percent": 22,
            "light_core_hours": 4.4,
            "light_core_percent": 59,
        },
        "respiratory_rate_bpm": 14.1,
        "status_badge": "OPTIMAL",
        "clinical_insight": "Excellent sleep architecture. Deep sleep of 19% promotes growth hormone release, physical recovery, and optimal insulin sensitivity.",
    }

    vitals_data = {
        "spo2_percent": 98.5,
        "spo2_status": "NORMAL (95 - 100%)",
        "daily_steps": 8420,
        "step_goal": 10000,
        "active_calories_kcal": 490,
        "flights_climbed": 12,
    }

    # Clinical correlation between wearable vitals and diagnostic lab markers
    lab_correlations = [
        {
            "device_metric": "Resting Heart Rate (62 bpm) & HRV (52 ms)",
            "lab_marker": "Lipid Panel (LDL & Triglycerides)",
            "correlation": "A lower resting heart rate and higher HRV correlate with healthy autonomic cardiovascular conditioning, counterbalancing atherogenic risk from borderline LDL.",
        },
        {
            "device_metric": "Sleep Efficiency (88%) & Deep Sleep (1.4h)",
            "lab_marker": "Metabolic Panel (Fasting Glucose & HbA1c)",
            "correlation": "Adequate slow-wave deep sleep directly enhances cellular insulin sensitivity and helps maintain healthy morning fasting blood glucose levels.",
        },
        {
            "device_metric": "Body Temperature (98.4°F)",
            "lab_marker": "Complete Blood Count (WBC count & Neutrophils)",
            "correlation": "Stable basal temperature confirms absence of acute systemic infection or inflammatory spikes reflected in normal leukocyte counts.",
        },
    ]

    return {
        "success": True,
        "patient_id": patient_id,
        "device_brand": clean_brand,
        "device_name": profile["device_name"],
        "sync_protocol": profile["sync_protocol"],
        "synced_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "heart_rate": heart_rate_data,
        "body_temperature": body_temp_data,
        "sleep": sleep_data,
        "vitals": vitals_data,
        "lab_correlations": lab_correlations,
        "summary": (
            f"Health Device ({profile['device_name']}): Resting Heart Rate 62 bpm (Optimal), "
            "Body Temp 98.4°F (Normal), Sleep 7h 24m (Score 85/100, Deep Sleep 19%), SpO2 98.5%."
        ),
    }
