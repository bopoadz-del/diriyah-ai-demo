from .intent_router import router

def handle_vision(message, context):
    # TODO: replace with real vision logic
    return {"service": "vision", "result": "Handled by vision"} 

# Register service on import
router.register("vision", ['\\byolo\\b', '\\bphoto\\b', '\\bimage\\b'], handle_vision)
