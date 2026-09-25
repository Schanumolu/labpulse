# LabPulse — Diagnostic Biomarker Explainer & Health Intelligence Platform

**LabPulse** is an agentic clinical intelligence application powered by **Google Agent Development Kit (ADK)**, **Gemini 2.5 Flash**, **Vertex AI Memory Bank**, and **Google Cloud Platform**. 

LabPulse transforms complex, intimidating diagnostic lab reports (PDF, image scans, raw numbers) into clear, empathetic, and actionable medical explanations paired with real-time connected wearable health telemetry.


## 🚀 Live Cloud Deployment

- **Cloud Run Web Application**: [https://labpulse-frontend-439352070082.us-east1.run.app](https://labpulse-frontend-439352070082.us-east1.run.app)
- **Vertex AI Agent Runtime ID**: `projects/439352070082/locations/us-east1/reasoningEngines/6370401046543466496`
- **A2A Protocol**: Fully compliant Agent-to-Agent standard with streaming and A2UI card rendering.

---

## 🌟 Key Features

### 1. Multi-Modal Lab Ingestion with Default Cloud Storage
- **Top Drag-and-Drop Zone**: Direct upload of lab reports in **PDF, PNG, JPG, and CSV/TXT** formats.
- **Default Automatic Storage**: Lab documents are immediately uploaded to Google Cloud Storage (`gs://<bucket>/uploads/...`) and stored without requiring any prompting or confirmation from the user.
- **Mid-Process Failure Recovery**: If parsing or model inference is interrupted, raw tests can be retrieved and resumed at any time using `store_uploaded_labtest` and `recover_and_process_labtest`.

### 2. Connected Health Devices & Wearable Telemetry
- **Multi-Brand Wearable Ingestion**: Connects with **Apple Health (Apple Watch)**, **Fitbit / Pixel Watch**, **Garmin Connect**, and **Google Health Connect**.
- **Live Biometric Telemetry**:
  - ❤️ **Heart Rate**: Resting heart rate (bpm), current pulse, and Heart Rate Variability (HRV in ms) with arrhythmia checks.
  - 🌡️ **Body Temperature**: Basal temperature and circadian baseline deviation (e.g. `+0.2°F`).
  - 🌙 **Sleep Architecture**: Total sleep duration, Sleep Score (0–100), efficiency percentage, and stage breakdown (Deep, REM, Light/Core).
  - 🫁 **SpO2 & Activity**: Blood oxygen saturation percentage, daily step count, and active calories.
- **Cross-Domain Correlation**: Correlates wearable lifestyle data (e.g. resting heart rate, deep sleep) directly with diagnostic lab markers (e.g. lipid panels, fasting glucose, systemic inflammation).

### 3. Patient Lab Results History & Multi-Result Comparison
- **Stored Reports Archive**: Interactive modal to browse all previously uploaded lab test files, timestamps, and extracted biomarker summaries.
- **Interactive Multi-Visit Delta Comparison**:
  - Compare any two visits or reports side-by-side (e.g., *Visit 1 June 2026* vs *Visit 2 September 2026*).
  - Automatically calculates absolute change and percentage change (`-21.4%`, `+15.8%`).
  - **High / Low & Clinical Favorability Indicators**:
    - 🟢 **Favorable (Improvement)**: e.g. LDL dropped, HDL increased, eGFR improved.
    - 🔴 **Unfavorable (Elevated / Decline)**: e.g. triglycerides spiked, kidney filtration declined.
    - 🟡 **Stable**: Marker stayed consistent within range.
  - **One-Click Agent Briefing**: Send the comparison table directly to LabPulse for an appointment briefing.

### 4. Interactive A2UI Diagnostic Cards
- **Rich Diagnostic Panels**: Renders structured cards for **Lipid Panel**, **Basic / Comprehensive Metabolic Panel (BMP/CMP)**, and **Complete Blood Count (CBC)**.
- **Reference Range Visualizer**: Color-coded range bars (`[Min -----●----- Max]`) illustrating where patient markers fall relative to optimal medical cutoffs.
- **Color-Coded Status Badges**: 🟢 Optimal, 🟡 Borderline / Watch, 🔴 Elevated / Out-of-Range.

### 5. Validated Clinical Calculators
- **Total Cholesterol / HDL Ratio**: Assesses cardiovascular atherogenic risk profile.
- **Triglyceride / HDL Ratio**: Evaluates surrogate markers for insulin resistance and metabolic syndrome.
- **HbA1c to Estimated Average Glucose (eAG)**: Translates glycated hemoglobin into intuitive daily blood sugar using the ADA ADAG clinical equation.
- **2021 CKD-EPI Race-Free eGFR**: Calculates kidney filtration rate and Kidney Disease Staging (Stages 1 through 5) based on serum creatinine, age, and sex.

### 6. External Clinical Integrations
- **NIH MedlinePlus Connect API**: Fetches official clinical background summaries and patient education links.
- **openFDA Drug Safety API**: Cross-references patient medications against lab markers to detect drug-induced biomarker elevations or adverse interactions.
- **Anatomical Explainer Diagrams**: Automatically generates and renders clean anatomical diagrams (e.g. arterial plaque formation, nephron filtration, insulin resistance).

### 7. Interactive Doctor Discussion Checklist
- Interactive checklist of tailored questions for the patient's next physician appointment.
- Add custom questions, mark items as discussed, **Copy to Clipboard**, and **Export as .txt**.

---

## 🏛️ Architecture

```
[ Patient / Browser ]
        │
        ▼ (HTTP / Multipart / WebSocket)
[ LabPulse FastAPI Frontend (Port 8085) ] ──► [ Google Cloud Storage ] (PDF/Image Store)
        │                                         ▲
        ▼ (A2A Protocol / ADK REST)              │
[ ADK LabPulse Agent (Port 8080) ] ───────────────┘
        ├── Vertex AI Memory Bank (Long-Term Patient Memory)
        ├── Gemini 2.5 Flash (Clinical Reasoning & A2UI Output)
        ├── Clinical Calculator Engine (ADA eAG, CKD-EPI eGFR, TC/HDL, Trig/HDL)
        ├── Health Devices Ingestion Engine (Apple Health, Fitbit, Garmin)
        ├── NIH MedlinePlus & openFDA Drug Safety APIs
        └── Anatomical SVG Diagram Engine
```

---

## 🚀 Local Quick Start

### 1. Prerequisites
- Python 3.12+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Google Cloud SDK authenticated (`gcloud auth application-default login`)

### 2. Install Dependencies
```bash
uv sync
```

### 3. Run the ADK Agent (Backend)
```bash
uv run --env-file .env adk web --port 8080 --host 0.0.0.0 --allow_origins "*" --reload_agents .
```

### 4. Run the LabPulse Web Frontend
```bash
cd frontend
FRONTEND_PORT=8085 uv run --env-file ../.env python main.py
```
Open **`http://localhost:8085`** in your browser.

---

## 📡 API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/chat` | `POST` | Core conversational endpoint connecting to ADK Agent with A2UI support |
| `/api/upload` | `POST` | Multipart upload for lab documents (PDF, PNG, JPG) to Google Cloud Storage |
| `/api/health-devices` | `GET` | Retrieves wearable vitals (Heart Rate, Body Temp, Sleep, SpO2) by brand |
| `/api/lab-history` | `GET` | Lists all stored lab reports, timestamps, and recorded biomarker entries |
| `/api/compare-results` | `POST` | Computes multi-visit biomarker percentage changes with high/low badges |
| `/api/diagrams/{filename}` | `GET` | Serves generated anatomical explainer diagrams |

---

## 🧪 Running Unit Tests

Run the full test suite covering clinical calculators, external APIs, and health devices:

```bash
uv run pytest tests/unit
```

All tests execute locally and validate:
- Clinical equations (CKD-EPI 2021, ADA ADAG, TC/HDL ratio, biomarker percentage deltas)
- External API connectors (openFDA, MedlinePlus, SVG diagrams)
- Connected wearable health telemetry data structures and brand fallbacks.

---

## 🔒 Privacy & Safety Notice
*LabPulse is an educational biomarker intelligence explainer tool designed to assist patients in understanding diagnostic reports and preparing questions for their healthcare providers. It is not a substitute for professional medical advice, diagnosis, or treatment.*
