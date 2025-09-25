def validate_quantities(cad_result, boq_result):
    diffs = []
    for item in cad_result.get("items", []):
        boq_qty = boq_result.get(item["name"])
        if boq_qty and abs(boq_qty - item["qty"]) > 0.05 * boq_qty:
            diffs.append({
                "item": item["name"],
                "cad": item["qty"],
                "boq": boq_qty,
                "flag": "Mismatch >5%"
            })
    return diffs
