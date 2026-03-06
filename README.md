# AdverseIQ — Drug Interaction Reasoning API

A clinical decision-support backend that uses the **K2 Think V2** reasoning model to analyse drug-drug and drug-herb interactions. It goes beyond simple interaction lookups by generating multi-step mechanistic explanations, ranked differential hypotheses, and patient-personalised risk assessments.

---

## Features

### Three Analysis Strategies

| Strategy | Endpoint | Description |
|---|---|---|
| **Rapid Check** | `POST /api/analyze` (`strategy: "rapid"`) | Single-pass interaction check with urgency, confidence, and a one-step causal mechanism |
| **Mechanism Trace** | `POST /api/analyze` (`strategy: "mechanism"`) | Step-by-step pharmacokinetic/pharmacodynamic causal chain (typically 4–6 steps) with per-step evidence citations |
| **Mystery Solver** | `POST /api/analyze` (`strategy: "hypothesis"`) | Generates 8–11 ranked differential hypotheses, a reasoning tree, and literature-backed confidence scoring |

### Streaming
- `POST /api/analyze/stream` — Server-Sent Events (SSE) stream for Mystery Solver; yields live reasoning tokens, stage progress, and a final JSON result

### Patient Context Modifiers
All three strategies accept a `patientContext` object and adjust analysis accordingly:

| Field | Clinical Impact |
|---|---|
| `age` | Elderly (≥65): reduced CYP450/renal clearance (Klotz 2009); Pediatric: weight-based dosing adjustments |
| `sex` | Female: CYP3A4 activity ~20% higher (Walsky 2004); QTc prolongation risk elevated |
| `renalImpairment` | `mild/moderate/severe` — flags narrow therapeutic index renally-cleared drugs (digoxin, lithium, metformin, vancomycin, dabigatran, gabapentin) against KDIGO 2012 |
| `hepaticImpairment` | `mild/moderate/severe` — flags narrow TI hepatically-metabolised drugs (warfarin, phenytoin, tacrolimus, fentanyl) against Child-Pugh/Verbeeck 2008 |
| `pregnant` | Checks against 20+ teratogenic/fetotoxic drugs; serotonergic drugs escalate urgency immediately (FDA 2011); follows Briggs 12th Ed / FDA PLLR / ACOG |

### Rule-Based Urgency Escalation
A two-stage urgency assessor runs independently of K2 and never de-escalates:

- **Pattern check** — serotonin syndrome drugs, anticoagulant + NSAID, QT-prolonging pairs, nephrotoxic combinations, narrow TI drugs
- **Patient escalation** — pregnancy + teratogen → **emergent**; severe renal/hepatic + narrow TI → escalate; female + ≥2 QT drugs → urgent; elderly + ≥3 meds → urgent

### Drug & Herb Lookup
- Supabase-backed interaction database (drugs + herbs)
- Herb detection with `isHerb` flag (St. John's Wort, ginkgo, valerian, etc.)
- Drug name normalisation (brand → generic)
- `GET /api/drugs/search?q=` — typeahead search

### PubMed Integration
- Mystery Solver fetches the top 5 relevant PubMed abstract snippets per query and injects them into the K2 prompt as literature evidence

### Exports
- `POST /api/export/pdf` — generates a formatted clinical PDF report (fpdf2, no GTK/system deps)
- `POST /api/export/json` — returns a structured JSON envelope with metadata and `analysis_id`

### Analysis Persistence
- `POST /api/analyses` — saves a result to Supabase
- `GET /api/analyses/{id}` — retrieves a saved result by UUID (for audit trail and PDF regeneration)

### Demo Cases
Three pre-cached demo cases served instantly without K2 calls:
- `GET /api/cases/warfarin` — warfarin + fluconazole (CYP2C9 inhibition)
- `GET /api/cases/stjohnswort` — metformin + St. John's Wort (hyperglycaemia)
- `GET /api/cases/serotonin` — tramadol + sertraline (serotonin syndrome)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI + uvicorn |
| AI Model | K2 Think V2 via OpenAI-compatible API |
| Database | Supabase (via async HTTP — no direct Postgres) |
| PDF | fpdf2 |
| Settings | pydantic-settings |
| JSON repair | json-repair (handles malformed K2 output) |

---

## Installation

### Prerequisites
- Python 3.11+
- A [Supabase](https://supabase.com) project with `drugs`, `herbs`, `interactions`, and `analyses` tables
- A K2 API key from [k2think.ai](https://k2think.ai)

### 1. Clone & create a virtual environment

```bash
git clone <your-repo-url>
cd adverseiq-backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in `adverseiq-backend/`:

```env
K2_API_KEY=your_k2_api_key
K2_BASE_URL=https://api.k2think.ai/v1
K2_MODEL=MBZUAI-IFM/K2-Think-v2

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

FRONTEND_URL=http://localhost:3000
```

### 4. Run the server

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### 5. Run tests

```bash
# Full integration test suite (requires server running)
python scripts/test_all.py

# Patient context / urgency escalation unit tests (no server needed)
python scripts/test_patient_context.py
```

---

## API Reference

### Health
```
GET /health
```

### Drug Search
```
GET /api/drugs/search?q={query}
```

### Analyze
```
POST /api/analyze
Content-Type: application/json

{
  "medications": [
    { "displayName": "warfarin" },
    { "displayName": "fluconazole" }
  ],
  "symptoms": [
    { "description": "bruising", "severity": "moderate" }
  ],
  "strategy": "rapid" | "mechanism" | "hypothesis",
  "patientContext": {
    "age": 72,
    "sex": "female",
    "renalImpairment": "moderate",
    "hepaticImpairment": "none",
    "pregnant": false
  }
}
```

### Stream (Mystery Solver only)
```
POST /api/analyze/stream
```
Returns SSE events: `stage`, `thinking`, `result`, `error`

### Demo Cases
```
GET /api/cases/warfarin
GET /api/cases/stjohnswort
GET /api/cases/serotonin
```

### Export
```
POST /api/export/pdf
POST /api/export/json
```

### Persistence
```
POST /api/analyses
GET  /api/analyses/{analysis_id}
```

---

## Deployment (Render)

The `render.yaml` is pre-configured. Set these secret environment variables in the Render dashboard:

| Variable | Description |
|---|---|
| `K2_API_KEY` | Your K2 API key |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `FRONTEND_URL` | Your deployed frontend URL (for CORS) |

`K2_BASE_URL` is already set in `render.yaml`.

---

## Disclaimer

AdverseIQ is clinical decision **support** only. It is not a substitute for professional medical judgment. All outputs should be confirmed clinically before acting.
