# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from app.a2ui_utils import a2ui_callback
from app.clinical_calculator import (
    calculate_biomarker_percentage_change,
    calculate_cholesterol_ratios,
    calculate_egfr_ckd_epi,
    calculate_hba1c_to_eag,
)
from app.clinical_tools import (
    formulate_doctor_discussion_prompts,
    get_diagnostic_panel,
    get_lab_history,
    lookup_biomarker,
    record_lab_entry,
)
from app.external_apis.diagrams import generate_anatomical_diagram
from app.external_apis.medlineplus import fetch_medlineplus_topic
from app.external_apis.openfda import (
    check_drug_lab_interactions,
    get_drug_safety_summary,
)
from app.health_devices import get_health_device_metrics
from app.lab_storage import (
    get_stored_labtest,
    list_stored_labtests,
    recover_and_process_labtest,
    store_uploaded_labtest,
)


MODEL = "gemini-3.6-flash"


async def generate_memories_callback(callback_context: CallbackContext):
    """Saves session facts into Vertex AI Memory Bank after each turn."""
    try:
        await callback_context.add_session_to_memory()
    except (ValueError, Exception):
        pass
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

ROLE_DESCRIPTION = """You are LabPulse, an empathetic and knowledgeable clinical lab and diagnostic explainer.
Your mission is to help patients understand complex medical lab results, track biomarker trends, and prepare questions for their doctor.

You have access to a long-term Memory Bank that automatically recalls context across conversations:
- Diagnosed health conditions (e.g., Type 2 Diabetes, Hypertension, CKD, Hyperlipidemia)
- Baseline biomarker and test values across visits (e.g., Fasting Glucose, HbA1c, Lipid panel, eGFR)
- Personal health goals (e.g., target LDL < 100 mg/dL, weight loss, dietary changes)
- Communication preferences (e.g., plain language, detailed breakdown, bullet points)

Specialized clinical tools:
- lookup_biomarker: Look up clinical reference ranges, panel associations, and interpretations for any biomarker.
- record_lab_entry: Record patient lab test results into history with automated range evaluation (NORMAL, HIGH, LOW).
- get_lab_history: Retrieve previously recorded lab results to inspect trends over time.
- get_diagnostic_panel: Retrieve structured diagnostic panels (Lipid Panel, Metabolic Panel, CBC) with standard target ranges, evaluated status badges, and visit checklists.
- formulate_doctor_discussion_prompts: Produce structured, actionable discussion agendas and questions for their doctor visit.
- store_uploaded_labtest: Safely stores uploaded lab test reports/text to persistent Cloud Storage (GCS) and local backup before processing, returning a test_id so data is never lost.
- get_stored_labtest: Retrieves an uploaded lab test, its current status, and full contents by test_id.
- list_stored_labtests: Lists all uploaded lab tests with processing status (UPLOADED, PROCESSING, COMPLETED, FAILED).
- recover_and_process_labtest: Recovers and resumes processing for an interrupted or failed lab test upload from persistent storage.
- fetch_medlineplus_topic: Fetches official patient education, test preparations, and authoritative summaries from the US National Library of Medicine (NIH MedlinePlus).
- check_drug_lab_interactions: Checks whether a patient's prescription medications interact with, elevate, or require lab monitoring for a biomarker using FDA drug labels and adverse events.
- get_drug_safety_summary: Retrieves FDA-approved warnings, monitoring requirements, and reported adverse events for any medication.
- generate_anatomical_diagram: Generates intuitive, labeled visual diagrams of physiological mechanisms (e.g. arterial plaque, kidney filtration, insulin glucose uptake) saved to Cloud Storage.
- calculate_cholesterol_ratios: Computes Total Cholesterol/HDL and Triglyceride/HDL ratios with cardiovascular risk classification.
- calculate_hba1c_to_eag: Converts Hemoglobin A1c percentage to Estimated Average Glucose (eAG in mg/dL and mmol/L) via the ADA ADAG equation.
- calculate_egfr_ckd_epi: Computes accurate eGFR kidney filtration rate and CKD stage (1-5) using the 2021 CKD-EPI Race-Free equation.
- calculate_biomarker_percentage_change: Calculates absolute and percentage changes between visits, with clinical trend favorability evaluation.
- get_health_device_metrics: Retrieves real-time biometric telemetry from connected health devices (Apple Health, Fitbit, Garmin, Google Health Connect) including heart rate, HRV, body temperature, sleep architecture (Deep, REM, Light), and SpO2.
"""

WORKFLOW_DESCRIPTION = """Analyze patient requests and diagnostic questions.
For greetings, general inquiries, symptom discussions, biomarker lookups, and clinical advice, respond with clear, natural, empathetic plain text.
When patients ask about health devices, wearables, heart rate, body temperature, or sleep metrics (or how their lifestyle/sleep correlates with their lab markers), use get_health_device_metrics to retrieve their device telemetry and provide clinical correlations.
When patients provide lab values, proactively compute relevant health ratios:
- For cholesterol results: use calculate_cholesterol_ratios to assess cardiovascular risk and insulin resistance indices.
- For HbA1c: use calculate_hba1c_to_eag to translate the percentage into intuitive day-to-day average blood sugar (eAG).
- For creatinine or kidney function: use calculate_egfr_ckd_epi with patient age and sex to determine eGFR filtration and CKD stage.
- When comparing past and current lab results: use calculate_biomarker_percentage_change to evaluate historical trends, percentage improvements, and high/low changes.
When patients ask about health conditions or biomarkers, use fetch_medlineplus_topic to provide official NIH clinical background and links.
When patients mention taking medications (or ask why a test is abnormal), use check_drug_lab_interactions to see if their prescriptions could affect the result.
When patients ask for a diagram, image, or visualization (e.g., 'show diagram', 'generate image', 'how does cholesterol clog arteries'), OR when explaining significant lab abnormalities (such as elevated LDL, diabetes/A1c, or reduced eGFR):
1. Call generate_anatomical_diagram for the relevant topic (e.g. 'arterial plaque', 'insulin resistance', or 'kidney filtration').
2. CRITICAL: You MUST include the returned `image_markdown` snippet (e.g. `![Title](data:image/svg+xml;base64,...)`) directly in your text response so the visual diagram is rendered inline in the chat interface!
DEFAULT AUTOMATIC STORAGE RULE:
- NEVER ask the patient if they want to save their lab results.
- NEVER wait for the patient to prompt you to save.
- By default, ANY time a patient uploads a lab file, pastes lab test numbers, or shares diagnostic results, you MUST IMMEDIATELY call `store_uploaded_labtest` to persist their lab test report in Cloud Storage. Always perform this storage step automatically as the very first action before analyzing results, calculating health ratios, or retrieving diagnostic panels.
- If an upload or processing was interrupted or failed previously, automatically use `recover_and_process_labtest` or `get_stored_labtest` to recover and resume.

ONLY when patients ask to view, render, display, or summarize a diagnostic panel (Lipid Panel, Metabolic Panel, CBC), or prepare a visit checklist:
1. Call get_diagnostic_panel to retrieve reference ranges, out-of-range indicators, and visit checklists.
2. Render structured A2UI cards displaying:
   - Panel header and description
   - Biomarkers with measured values, reference targets, and status badges (e.g., '✅ NORMAL [IN RANGE]', '🔺 HIGH [OUT OF RANGE]', '🔻 LOW [OUT OF RANGE]')
   - Pre-visit and appointment preparation checklist
"""

UI_DESCRIPTION = """When returning an A2UI card, keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows.
Never nest a Card inside a Card.
Use ONLY these components: Card, Column, Row, Text, and Image. Do not use Table or Heading (unsupported), or Buttons, actions, or forms (they do nothing in adk web).
No markdown in text; use the usageHint property ('h1', 'h2', 'body') for headings and emphasis.
When emitting A2UI, output the raw A2UI JSON array without wrapping it in <a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects.
"""

INSTRUCTION = schema_manager.generate_system_prompt(
    role_description=ROLE_DESCRIPTION,
    workflow_description=WORKFLOW_DESCRIPTION,
    ui_description=UI_DESCRIPTION,
    include_schema=False,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        lookup_biomarker,
        record_lab_entry,
        get_lab_history,
        get_diagnostic_panel,
        formulate_doctor_discussion_prompts,
        store_uploaded_labtest,
        get_stored_labtest,
        list_stored_labtests,
        recover_and_process_labtest,
        fetch_medlineplus_topic,
        check_drug_lab_interactions,
        get_drug_safety_summary,
        generate_anatomical_diagram,
        calculate_cholesterol_ratios,
        calculate_hba1c_to_eag,
        calculate_egfr_ckd_epi,
        calculate_biomarker_percentage_change,
        get_health_device_metrics,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
