from .intent_router import router

def handle_primavera(message, context):
    # TODO: replace with real primavera logic
    return {"service": "primavera", "result": "Handled by primavera"} 

# Register service on import
router.register("primavera", ['\\bprimavera\\b', '\\.xer\\b'], handle_primavera)
