from backend.api import qto

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import projects, chats, alerts, chat
from .middleware.tenant import TenantMiddleware
from .db import init_db

app = FastAPI(title="Diriyah Brain AI Heavy")

app.add_middleware(TenantMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(chats.router)
app.include_router(alerts.router)
app.include_router(chat.router)

@app.on_event("startup")
def startup_event():
    init_db()

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8080, reload=True)

app.include_router(qto.router, prefix='/api')

from backend.api import ai, auth, connectors, google_drive, users, analytics, aconex

app.include_router(ai.router, prefix='/api')

app.include_router(auth.router, prefix='/api')

app.include_router(connectors.router, prefix='/api')

app.include_router(google_drive.router, prefix='/api')

app.include_router(users.router, prefix='/api')

app.include_router(analytics.router, prefix='/api')

app.include_router(aconex.router, prefix='/api')


# --- Injected Phase 1 Router Registration ---
from backend.api import (
    document_classifier, invoice_parser, data_normalizer, knowledge_graph,
    forecast_engine, anomaly_detector, compliance_monitor, semantic_search,
    rag_memory, meeting_summarizer, action_item_extractor, ifc_parser,
    cobie_connector, bcf_connector
)

app.include_router(document_classifier.router, prefix="/api")
app.include_router(invoice_parser.router, prefix="/api")
app.include_router(data_normalizer.router, prefix="/api")
app.include_router(knowledge_graph.router, prefix="/api")
app.include_router(forecast_engine.router, prefix="/api")
app.include_router(anomaly_detector.router, prefix="/api")
app.include_router(compliance_monitor.router, prefix="/api")
app.include_router(semantic_search.router, prefix="/api")
app.include_router(rag_memory.router, prefix="/api")
app.include_router(meeting_summarizer.router, prefix="/api")
app.include_router(action_item_extractor.router, prefix="/api")
app.include_router(ifc_parser.router, prefix="/api")
app.include_router(cobie_connector.router, prefix="/api")
app.include_router(bcf_connector.router, prefix="/api")

# Addons routers (18-feature bundle)
from .api.addons import chat_addons
app.include_router(chat_addons.router, prefix='/api')
