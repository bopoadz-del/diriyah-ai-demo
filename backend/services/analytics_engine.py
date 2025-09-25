from .intent_router import router

def handle_analytics_engine(message, context):
    # TODO: replace with real analytics_engine logic
    return {"service": "analytics_engine", "result": "Handled by analytics_engine"} 

# Register service on import
router.register("analytics_engine", ['\\banalytics\\b', '\\bkpi\\b'], handle_analytics_engine)
