from .intent_router import router

def handle_boq_parser(message, context):
    # TODO: replace with real boq_parser logic
    return {"service": "boq_parser", "result": "Handled by boq_parser"} 

# Register service on import
router.register("boq_parser", ['\\bboq\\b'], handle_boq_parser)
