from .intent_router import router

def handle_cad_takeoff(message, context):
    # TODO: replace with real cad_takeoff logic
    return {"service": "cad_takeoff", "result": "Handled by cad_takeoff"} 

# Register service on import
router.register("cad_takeoff", ['\\bcad\\b', '\\bdxf\\b', 'take\\s*off'], handle_cad_takeoff)
