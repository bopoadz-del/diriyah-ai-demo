# Diriyah Brain AI (Demo)

This repository contains a **lightweight prototype** of the Diriyah Brain AI assistant.  It exposes a web interface styled like a chat application, backed by a FastAPI server.  The goal of this demo is to show how an AI assistant can answer questions about construction projects by searching Google Drive, parsing uploaded documents, and surfacing alerts – all while remaining simple to deploy and extend.

## Key Features

* **Always‑On Drive Integration:**  A service account is used to connect to a central Google Drive.  The assistant searches across the entire Drive for relevant snippets from BOQs, schedules, insurance policies and correspondence.
* **Project Scoping:**  Projects are defined in `projects.json` and users in `users.json`.  The UI presents a project selector that scopes all queries, alerts and caches to the chosen mega project.
* **Role‑Aware Answers:**  Responses are tailored to the role specified by the client (engineer, director or commercial), providing the appropriate level of detail.
* **Arabic & English Support:**  Queries containing Arabic characters trigger Arabic responses by default.  English queries are handled as usual.
* **Alerts in Chat:**  The assistant scans retrieved snippets for keywords indicating delays, insurance expiry or other risks and injects a warning message directly into the conversation.
* **PDF Export:**  Users can export the current chat history as a PDF using the **Export PDF** button in the sidebar.
* **Caching & Refresh:**  A background thread refreshes the local cache for each project every six hours.  A **Refresh Now** button lets users fetch updates on demand.  A hover tooltip on “Last update” shows when the cache was last refreshed.
* **Photo Upload with Geolocation:**  Photos captured from the device camera are tagged with latitude, longitude and elevation (when available) and stored for later processing.  A stub in `bim_adapter.py` shows how these images could be matched to BIM elements.
* **Skeleton Integrations:**  Stubs are included for WhatsApp group integration, quality/defect detection (YOLOv10), Primavera P6, Aconex, Microsoft Teams and Power BI.  These endpoints return placeholder responses and can be wired up when you are ready to integrate with real services.

## Structure

```
diriyah_brain_ai/
├── index.html           # Frontend UI (vanilla HTML/JS/CSS)
├── main.py              # FastAPI server entry point
├── drive_adapter.py     # Drive search, caching and refresh logic
├── alerts.py            # Simple rule‑based alert detection
├── export_pdf.py        # Utility to convert chat history to PDF
├── quality.py           # Stub for photo quality/defect analysis (YOLO)
├── p6.py                # Stub for Primavera P6 integration
├── aconex.py            # Stub for Aconex integration
├── teams.py             # Stub for Microsoft Teams MoM generation
├── powerbi.py           # Stub for Power BI summary integration
├── whatsapp_adapter.py  # Stub for WhatsApp group webhook
├── photos.py            # Photo upload with geolocation metadata
├── bim_adapter.py       # Stub for matching photos to BIM elements
├── token_store.py       # Simple JSON token cache (not used in service mode)
├── projects.json        # Mapping of project names to Drive folder IDs
├── users.json           # Mapping of user IDs to roles and project access
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build definition
├── render.yaml          # Render.com deployment config
├── README.md            # This file
├── test_api.py          # Minimal smoke test
├── cache/               # Populated at runtime with per‑project caches
└── static/
    └── logo.png        # Company logo (replace with your own)
```

To deploy on [Render](https://render.com), create environment variables for your service account (`GOOGLE_APPLICATION_CREDENTIALS`) and, optionally, an OpenAI API key (`OPENAI_API_KEY`) if you plan to enable language model summarisation.

## Running Locally

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Provide a Google service account key JSON file and share your project folders with that service account.  Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of the JSON file.

3. Start the server:

   ```bash
   python main.py
   ```

4. Open [http://localhost:8080](http://localhost:8080) in your browser.

You can modify `projects.json` and `users.json` to add more projects and adjust role‑based access without touching the code.