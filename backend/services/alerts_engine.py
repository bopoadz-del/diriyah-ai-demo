from .intent_router import router

def handle_alerts_engine(message, context):
    # TODO: replace with real alerts_engine logic
    return {"service": "alerts_engine", "result": "Handled by alerts_engine"} 

# Register service on import
router.register("alerts_engine", ['\\balert\\b'], handle_alerts_engine)
