from typing import Dict, List, Callable

class WorkflowEngine:
    def __init__(self):
        self.workflows: Dict[str, List[str]] = {}
        self.registry: Dict[str, Callable] = {}

    def register_task(self, name: str, func: Callable):
        self.registry[name] = func

    def define_workflow(self, name: str, steps: List[str]):
        self.workflows[name] = steps

    def run(self, name: str, context: Dict | None = None) -> Dict:
        if name not in self.workflows:
            return {"status": "error", "message": f"Workflow {name} not found"}
        context = context or {}
        results = []
        for step in self.workflows[name]:
            func = self.registry.get(step)
            if func:
                try:
                    results.append({"step": step, "result": func(context)})
                except Exception as e:
                    results.append({"step": step, "result": f"error: {e}"})
            else:
                results.append({"step": step, "result": "not registered"})
        return {"workflow": name, "results": results}

workflow_engine = WorkflowEngine()
