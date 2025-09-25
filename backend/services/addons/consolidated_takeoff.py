import asyncio

class CADTakeoffService:
    def process_drawing(self, cad_file: str):
        # Placeholder mock
        return {"walls": 120, "doors": 18, "windows": 25}

class BOQParserService:
    def parse_boq(self, boq_file: str):
        # Placeholder mock
        return {"Concrete": 500, "Steel": 200, "Tiles": 1000}

class ConsolidatedTakeoffService:
    def __init__(self):
        self.cad_service = CADTakeoffService()
        self.boq_service = BOQParserService()

    async def consolidate_async(self, cad_file: str, boq_file: str) -> dict:
        cad_task = asyncio.to_thread(self.cad_service.process_drawing, cad_file)
        boq_task = asyncio.to_thread(self.boq_service.parse_boq, boq_file)
        cad_data, boq_data = await asyncio.gather(cad_task, boq_task)
        return {**cad_data, **boq_data}
