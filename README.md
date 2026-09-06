# AdverseIQ

**AdverseIQ** is a multi-hypothesis drug interaction reasoning engine powered by **K2 Think V2**. It goes beyond simple interaction lookups by using an agentic reasoning workflow to investigate potential mechanisms, supporting evidence, and safer therapeutic alternatives.

## Overview

AdverseIQ analyzes drug combinations using a **5-tool agent loop** that dynamically gathers and reasons over pharmacological and biomedical information.

The system integrates live external data sources with LLM-based reasoning to provide structured, evidence-informed drug interaction analysis in real time.

## Key Features

* **Multi-Hypothesis Drug Interaction Reasoning**

  * Generates and evaluates multiple possible explanations for an interaction rather than relying on a single conclusion.

* **5-Tool Agent Loop**

  * Coordinates specialized tools during the reasoning process to gather relevant drug and biomedical information.

* **Live PubMed Search**

  * Retrieves relevant biomedical literature using **PubMed E-Utilities**.

* **CYP Enzyme Profiling**

  * Investigates potential pharmacokinetic interactions involving cytochrome P450 enzymes.

* **Drug Class Identification**

  * Identifies the pharmacological classes of medications to support mechanism-level reasoning.

* **Safer Alternative Generation**

  * Suggests potentially safer medication alternatives when clinically relevant interactions are identified.

* **Real-Time Reasoning**

  * Uses **Server-Sent Events (SSE)** to stream reasoning progress and results to the frontend.

* **Self-Healing Structured Output**

  * Implements a **6-stage JSON repair pipeline** to recover malformed model responses and maintain reliable structured outputs.

## Technology Stack

### Frontend

* **Next.js**

### Backend

* **Python**
* **FastAPI**
* **K2 Think V2 API**

### Biomedical APIs & Data Sources

* **PubMed E-Utilities**
* **OpenFDA**
* **RxNav**

### Database

* **PostgreSQL / SQL**
* **Supabase**

### Communication

* **REST APIs**
* **Server-Sent Events (SSE)**

## Core Components

```text
AdverseIQ
├── Frontend
│   └── Next.js
│
├── Backend
│   ├── FastAPI
│   ├── K2 Think V2 integration
│   ├── Agent orchestration
│   ├── SSE streaming
│   └── JSON repair pipeline
│
├── Agent Tools
│   ├── PubMed search
│   ├── CYP profiling
│   ├── Drug class identification
│   ├── Drug information retrieval
│   └── Safer alternative generation
│
└── Data Layer
    ├── Supabase
    ├── SQL
    ├── OpenFDA
    ├── RxNav
    └── PubMed
```


## Disclaimer

AdverseIQ is intended for **research, educational, and decision-support purposes**.

It should **not** be used as a substitute for professional medical judgment, clinical guidelines, pharmacist review, or direct patient assessment. Medication changes should always be evaluated by a qualified healthcare professional.
## Link
* https://adverseiq.netlify.app/
