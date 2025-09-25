from .intent_router import router

def handle_bim(message, context):
    # TODO: replace with real bim logic
    return {"service": "bim", "result": "Handled by bim"} 

# Register service on import
router.register("bim", ['\\bbim\\b', '\\bifc\\b'], handle_bim)
