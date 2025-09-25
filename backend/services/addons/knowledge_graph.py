import networkx as nx
from typing import List, Dict

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_relation(self, source: str, relation: str, target: str, metadata: Dict | None = None):
        self.graph.add_node(source, type="entity")
        self.graph.add_node(target, type="entity")
        self.graph.add_edge(source, target, relation=relation, metadata=metadata or {})

    def query_relations(self, node: str) -> List[Dict]:
        if node not in self.graph:
            return []
        results = []
        for target in self.graph.successors(node):
            edge_data = self.graph.get_edge_data(node, target)
            results.append({
                "source": node,
                "relation": edge_data.get("relation"),
                "target": target,
                "metadata": edge_data.get("metadata", {})
            })
        return results

knowledge_graph = KnowledgeGraph()
