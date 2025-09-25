# Diriyah Brain AI

![Diriyah Logo](frontend/public/diriyah-logo.png)

## Overview
Diriyah Brain AI is an integrated platform for **mega-project delivery**, built to unify CAD/BIM data, BOQs, Primavera schedules, and Aconex documentation into one AI-driven system.

## Key Modules
- **CAD/BOQ/QTO Parsing**: Automated quantity take-off and bill of quantities parsing.
- **BIM Integration**: Direct handling of BIM/IFC models and data.
- **YOLO Vision Models**: Placeholder models (yolov8m, yolov8n, yolov8s) for site photo analysis and vision AI.
- **Speech-to-Text**: Voice commands and transcription, integrated in services.
- **API Layer**: Full suite of APIs for chat, projects, Aconex, Google Drive, QTO, and analytics.
- **Frontend**: React-based interface with Chat, Sidebar, Navbar, and live integration with backend services.

## Branding
This build is fully branded for **Diriyah Company**, replacing prior placeholders.



## 🧠 Logic Thinking Features

### 1. Intent Recognition & Routing
- Registry-based router — each service self-registers.
- Classifier fallback (TF-IDF + Logistic Regression).
- Validation layer (CAD ↔ BOQ mismatches).

### 2. Context & Memory
- Session context in chat.
- Database persistence (`projects`, `alerts`, `approvals`).
- Models stored in `backend/models/` and persisted with K8s PVC.

### 3. Reasoning / Orchestration
- Multi-service orchestration (e.g., Consolidated Takeoff).
- Fallback clarification for low-confidence intents.
- Automated validation checks → alerts.

### 4. Alerts & Monitoring
- Real-time alerts over WebSockets.
- Role- & project-based filtering (`/api/alerts`, `/api/users/me`).
- Alerts visible in:
  - Chat feed (inline, clickable).
  - Alerts Panel (filterable dashboard).
  - Visual toast popup (deployment alerts).

### 5. Slack-Driven Approvals
- Interactive Slack buttons (Approve/Reject).
- Multi-approver threshold logic.
- Threaded updates in Slack (clean UX).
- Decisions logged in DB + raised as alerts.

### 6. CI/CD Intelligence
- CI pipeline trains and tests intent model.
- Artifacts → models, Docker images, Helm charts.
- Approval-gated production deploy (via Slack).
- Rollbacks via versioned Helm charts.

### 7. Kubernetes / GitOps Integration
- Persistent DB + models (PVC).
- ArgoCD for auto-sync + drift correction.
- Multi-environment flow: **Dev → Staging → Prod (approval required)**.

---

## 🚀 Why It Matters
Diriyah Brain AI doesn’t just run commands — it *thinks*:
- Understands intent.
- Validates outputs.
- Raises alerts.
- Involves humans in critical decisions.
- Improves itself automatically via CI/CD.
- Deploys with safety gates and rollback paths.

It is **Aconex-style approvals + DevOps reasoning + project delivery intelligence** combined in one platform.


## Addons (18-feature bundle)
- New API: `POST /api/chat_addons` (ensemble intents + context + entities + memory + KG + suggestions)
- Addons services under `backend/services/addons/`
- Docker/K8s persistence for Redis+Chroma added in `deploy/k8s/`


---

## 🔭 Tracing

OpenTelemetry is enabled for the backend.

- Default exporter: OTLP → `otel-collector` in the cluster.  
- The collector currently exports to logs.  
- DevOps can extend the collector to forward to Jaeger, Tempo, or Datadog.


---

## 🐳 Docker Images

Each CI build publishes:
- `:latest` → moving pointer for dev/staging
- `:vX.Y.Z` → immutable tag for production (current: v1.21.0)


---

## 🔐 Secret Scanning & Notifications

- **Gitleaks** runs in CI to detect hardcoded secrets in commits/PRs.  
- **Slack notifications** are triggered on pipeline failures (requires `SLACK_WEBHOOK_URL` in repo secrets).  


---

## 💰 Cost Monitoring

- Kubecost manifests (`deploy/k8s/kubecost.yaml`) provide in-cluster cost visibility.  
- Access the Kubecost dashboard via the `kubecost` service (port 9003).  


---

## 🌱 Demo Data

Populate the app with demo data for quick testing:

```bash
python scripts/seed_demo_data.py
```
