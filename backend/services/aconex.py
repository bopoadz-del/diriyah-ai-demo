from .intent_router import router

def handle_aconex(message, context):
    # TODO: replace with real aconex logic
    return {"service": "aconex", "result": "Handled by aconex"} 

# Register service on import
router.register("aconex", ['\\baconex\\b'], handle_aconex)
