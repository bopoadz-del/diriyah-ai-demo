from .intent_router import router

def handle_rag_engine(message, context):
    # TODO: replace with real rag_engine logic
    return {"service": "rag_engine", "result": "Handled by rag_engine"} 

# Register service on import
router.register("rag_engine", ['\\brag\\b', '\\bsearch\\b', '\\bmemory\\b'], handle_rag_engine)
