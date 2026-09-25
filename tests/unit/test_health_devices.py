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

"""Unit tests for Health Devices module & Wearable Telemetry."""

import pytest
from app.health_devices import get_health_device_metrics, DEVICE_PROFILES


def test_supported_device_brands():
    """Ensure all major wearable ecosystems are supported."""
    assert "apple_health" in DEVICE_PROFILES
    assert "fitbit" in DEVICE_PROFILES
    assert "garmin" in DEVICE_PROFILES
    assert "google_health_connect" in DEVICE_PROFILES


def test_health_devices_telemetry_schema():
    """Verify health devices returns heart rate, body temp, sleep, and SpO2 metrics."""
    res = get_health_device_metrics("patient_unit_test", "apple_health")
    assert res["success"] is True
    assert res["patient_id"] == "patient_unit_test"
    assert "heart_rate" in res
    assert "body_temperature" in res
    assert "sleep" in res
    assert "vitals" in res

    # Heart Rate bounds
    hr = res["heart_rate"]
    assert 40 <= hr["resting_bpm"] <= 120
    assert hr["status_badge"] == "OPTIMAL"

    # Body Temperature
    temp = res["body_temperature"]
    assert 96.0 <= temp["current_temp_f"] <= 104.0
    assert "delta_f" in temp

    # Sleep Metrics
    sleep = res["sleep"]
    assert sleep["total_sleep_hours"] > 0
    assert 0 <= sleep["sleep_score"] <= 100
    assert "deep_sleep_percent" in sleep["stages"]

    # SpO2
    vitals = res["vitals"]
    assert 90.0 <= vitals["spo2_percent"] <= 100.0


def test_health_devices_brand_fallback():
    """Unknown brands should fallback cleanly to apple_health."""
    res = get_health_device_metrics("patient_fallback", "unknown_smartwatch_brand")
    assert res["success"] is True
    assert res["device_brand"] == "apple_health"
