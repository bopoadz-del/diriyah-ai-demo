from .intent_router import router

def handle_consolidated_takeoff(message, context):
    # TODO: replace with real consolidated_takeoff logic
    return {"service": "consolidated_takeoff", "result": "Handled by consolidated_takeoff"} 

# Register service on import
router.register("consolidated_takeoff", ['\\bconsolidated\\b'], handle_consolidated_takeoff)
