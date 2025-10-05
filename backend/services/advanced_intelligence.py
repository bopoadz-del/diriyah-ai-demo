from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


def _ensure_list(value: Any, default: Iterable[str]) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return list(default)
    return [str(value)]


def _ensure_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


@dataclass(slots=True)
class ScenarioResult:
    label: str
    projected_cost: float
    projected_risk: float
    mitigation: str


class AdvancedIntelligenceSuite:
    """Provide structured mock implementations for advanced reasoning features."""

    def __init__(self) -> None:
        self._default_documents = [
            "Foundation redesign meeting notes",
            "Geotechnical survey summary",
            "Structural safety audit from April",
        ]
        self._default_graph = {
            "geotechnical survey": "foundation redesign",
            "foundation redesign": "executive sign-off",
            "executive sign-off": "construction update",
        }

    def generate_report(
        self,
        query: str,
        goal: str | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        context = _ensure_mapping(context)
        resolved_goal = goal or context.get("goal") or "Prepare for the structural inspection next week"

        return [
            self._multi_hop_reasoning(query, context),
            self._automated_planning(resolved_goal, context),
            self._rlhf_summary(context),
            self._pipeline_optimization(context),
            self._multi_agent_debate(context),
            self._team_pattern_recognition(context),
            self._causal_inference(context),
            self._scenario_planning(context),
            self._temporal_context(context),
            self._emotional_intelligence(context),
            self._federated_learning(context),
            self._streaming_reasoning(context),
            self._causal_graph(context),
            self._root_cause_analysis(context),
            self._context_aware_defaults(context),
            self._intelligent_summaries(context),
        ]

    def _multi_hop_reasoning(self, query: str, context: Mapping[str, Any]) -> dict[str, Any]:
        documents = _ensure_list(context.get("documents"), self._default_documents)
        scored_docs = sorted(
            (
                {"document": doc, "score": self._score_document(query, doc)}
                for doc in documents
            ),
            key=lambda item: item["score"],
            reverse=True,
        )
        top_documents = [entry["document"] for entry in scored_docs[:3]]

        graph = _ensure_mapping(context.get("knowledge_graph")) or self._default_graph
        decision_chain: list[str] = []
        current = context.get("decision_start") or query.lower()
        visited = set()
        for _ in range(4):
            node = next((key for key in graph if key in current), None)
            if node is None or node in visited:
                break
            visited.add(node)
            decision_chain.append(node)
            current = graph.get(node, "")
        if current:
            decision_chain.append(current)

        steps = [
            f"Interpreted query '{query}'",
            f"Retrieved {len(top_documents)} relevant documents",
            "Traced decision chain across project knowledge graph",
            "Generated causal explanation for the change",
        ]

        return {
            "id": "multi_hop_reasoning",
            "title": "Multi-Hop Reasoning Engine",
            "summary": "Generates a chain-of-thought narrative using project knowledge graphs.",
            "highlights": top_documents,
            "details": {
                "query": query,
                "decision_chain": decision_chain,
                "steps": steps,
            },
        }

    def _automated_planning(self, goal: str, context: Mapping[str, Any]) -> dict[str, Any]:
        workflows = _ensure_mapping(context.get("workflows"))
        plan = workflows.get(goal)
        if plan is None:
            plan = [
                "check_compliance_docs",
                "verify_certifications",
                "schedule_team",
                "generate_checklist",
                "pre_inspection_validation",
            ]

        dependencies = [
            {"task": step, "depends_on": plan[idx - 1] if idx else None}
            for idx, step in enumerate(plan)
        ]

        return {
            "id": "automated_planning",
            "title": "Automated Planning & Goal Decomposition",
            "summary": f"Breaks the goal '{goal}' into executable workflow steps.",
            "highlights": plan,
            "details": {
                "goal": goal,
                "dependencies": dependencies,
            },
        }

    def _rlhf_summary(self, context: Mapping[str, Any]) -> dict[str, Any]:
        feedback_events = context.get("feedback")
        if not isinstance(feedback_events, list) or not feedback_events:
            feedback_events = [
                {"suggestion": "Use updated wind load factors", "accepted": True},
                {"suggestion": "Switch supplier for rebar", "accepted": False},
                {"suggestion": "Add cost variance alerts", "accepted": True},
            ]

        accepted = sum(1 for event in feedback_events if event.get("accepted"))
        total = len(feedback_events)
        acceptance_rate = accepted / total if total else 0.0
        most_common = Counter(event.get("reason", "preference") for event in feedback_events)

        return {
            "id": "rlhf",
            "title": "Reinforcement Learning from Human Feedback",
            "summary": f"Incorporates {total} feedback signals with {acceptance_rate:.0%} acceptance.",
            "highlights": [event["suggestion"] for event in feedback_events[:3]],
            "details": {
                "acceptance_rate": round(acceptance_rate, 2),
                "feedback_events": feedback_events,
                "top_reasons": most_common.most_common(3),
            },
        }

    def _pipeline_optimization(self, context: Mapping[str, Any]) -> dict[str, Any]:
        pipelines = context.get("pipelines")
        if not isinstance(pipelines, list) or not pipelines:
            pipelines = [
                {"name": "CAD→BOQ→Validation", "success_rate": 0.62},
                {"name": "CAD→Validation→BOQ", "success_rate": 0.81},
            ]

        best = max(pipelines, key=lambda item: item.get("success_rate", 0.0))
        improvement = best.get("success_rate", 0.0) - min(
            pipelines, key=lambda item: item.get("success_rate", 0.0)
        ).get("success_rate", 0.0)

        return {
            "id": "pipeline_optimization",
            "title": "Automated Pipeline Optimization",
            "summary": "Monitors workflow health and suggests higher performing alternatives.",
            "highlights": [f"Recommended pipeline: {best['name']}", f"Uplift: {improvement:.0%}"],
            "details": {
                "pipelines": pipelines,
                "recommended": best,
                "improvement": round(improvement, 2),
            },
        }

    def _multi_agent_debate(self, context: Mapping[str, Any]) -> dict[str, Any]:
        agents = _ensure_mapping(context.get("agents")) or {
            "structural_agent": "We need thicker beams for safety",
            "cost_agent": "But that exceeds budget by 15%",
            "scheduling_agent": "Either way, we'll miss the deadline",
        }

        resolution = "Increase beam thickness by 5% and re-phase procurement to stay within budget."

        return {
            "id": "multi_agent_debate",
            "title": "Multi-Agent Debate System",
            "summary": "Synthesizes balanced recommendations from specialist agent dialogue.",
            "highlights": list(agents.values()),
            "details": {
                "agents": agents,
                "consensus": resolution,
            },
        }

    def _team_pattern_recognition(self, context: Mapping[str, Any]) -> dict[str, Any]:
        patterns = context.get("team_patterns")
        if not isinstance(patterns, list) or not patterns:
            patterns = [
                {"pattern": "Team A underestimates concrete quantities by 8%"},
                {"pattern": "Project manager B prefers visual reports"},
                {"pattern": "Friday afternoons have highest error rates"},
            ]

        return {
            "id": "team_pattern_recognition",
            "title": "Team Pattern Recognition",
            "summary": "Learns behavioural trends to personalize recommendations.",
            "highlights": [item["pattern"] for item in patterns],
            "details": {
                "patterns": patterns,
                "confidence": 0.82,
            },
        }

    def _causal_inference(self, context: Mapping[str, Any]) -> dict[str, Any]:
        causal = _ensure_mapping(context.get("causal")) or {
            "cad_changes_delay_probability": 0.7,
            "resource_constraints_schedule_impact": 0.45,
            "recommended_hires": 2,
        }
        interventions = [
            "Hire 2 structural engineers to reduce approval delays by 60%",
            "Automate document routing to cut waiting time",
        ]

        return {
            "id": "causal_inference",
            "title": "Causal Inference Engine",
            "summary": "Identifies root drivers of schedule and cost shifts with actionable interventions.",
            "highlights": interventions,
            "details": {
                "metrics": causal,
                "interventions": interventions,
            },
        }

    def _scenario_planning(self, context: Mapping[str, Any]) -> dict[str, Any]:
        scenarios = context.get("scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            scenarios = [
                ScenarioResult(
                    label="Accelerate by 2 weeks",
                    projected_cost=1.15,
                    projected_risk=0.4,
                    mitigation="Add weekend shifts and increase QA checks",
                ),
                ScenarioResult(
                    label="Baseline",
                    projected_cost=1.0,
                    projected_risk=0.25,
                    mitigation="Maintain current staffing"
                ),
            ]

        return {
            "id": "scenario_planning",
            "title": "Scenario Planning & Simulation",
            "summary": "Runs Monte Carlo style projections for what-if timelines.",
            "highlights": [scenario.label for scenario in scenarios],
            "details": {
                "scenarios": [
                    {
                        "label": scenario.label,
                        "cost_multiplier": scenario.projected_cost,
                        "risk": scenario.projected_risk,
                        "mitigation": scenario.mitigation,
                    }
                    for scenario in scenarios
                ],
            },
        }

    def _temporal_context(self, context: Mapping[str, Any]) -> dict[str, Any]:
        temporal = context.get("temporal")
        if not isinstance(temporal, list) or not temporal:
            temporal = [
                {"statement": "Approvals usually take 3 business days"},
                {"statement": "Client reviews changes every Tuesday"},
                {"statement": "Regulation updates happen quarterly"},
            ]

        next_update = context.get("next_regulation_update", "In 3 weeks")

        return {
            "id": "temporal_context",
            "title": "Temporal Context Understanding",
            "summary": "Captures recurring cadences and time-based constraints.",
            "highlights": [item["statement"] for item in temporal],
            "details": {
                "timeline": temporal,
                "upcoming_events": next_update,
            },
        }

    def _emotional_intelligence(self, context: Mapping[str, Any]) -> dict[str, Any]:
        sentiment = _ensure_mapping(context.get("sentiment"))
        mood = sentiment.get("state")
        if mood is None:
            mood = "frustrated"
        urgency = sentiment.get("urgency", "high")
        recommendation = (
            "Provide concise solutions with an empathetic tone"
            if mood == "frustrated" and urgency == "high"
            else "Offer collaborative planning options"
        )

        return {
            "id": "emotional_intelligence",
            "title": "Emotional Intelligence Layer",
            "summary": "Adapts responses based on detected sentiment and urgency cues.",
            "highlights": [f"Sentiment: {mood}", f"Urgency: {urgency}"],
            "details": {
                "sentiment": mood,
                "urgency": urgency,
                "response_style": recommendation,
            },
        }

    def _federated_learning(self, context: Mapping[str, Any]) -> dict[str, Any]:
        nodes = context.get("federated_nodes")
        if not isinstance(nodes, list) or not nodes:
            nodes = [
                {"project": "Heritage Quarter", "status": "training", "privacy": "differential"},
                {"project": "Gateway Villas", "status": "idle", "privacy": "secure enclave"},
            ]

        participating = sum(1 for node in nodes if node.get("status") == "training")

        return {
            "id": "federated_learning",
            "title": "Federated Learning Capability",
            "summary": "Trains models across projects without exposing sensitive data.",
            "highlights": [f"{participating} active nodes"],
            "details": {
                "nodes": nodes,
                "active_nodes": participating,
            },
        }

    def _streaming_reasoning(self, context: Mapping[str, Any]) -> dict[str, Any]:
        streams = context.get("streams")
        if not isinstance(streams, list) or not streams:
            streams = [
                {"source": "site_sensors", "status": "ingesting", "anomalies": 1},
                {"source": "budget_updates", "status": "stable", "anomalies": 0},
            ]

        active_alerts = [stream for stream in streams if stream.get("anomalies")]

        return {
            "id": "streaming_reasoning",
            "title": "Real-time Streaming Reasoning",
            "summary": "Correlates live signals across projects for rapid interventions.",
            "highlights": [f"{len(streams)} streams monitored", f"{len(active_alerts)} with alerts"],
            "details": {
                "streams": streams,
                "active_alerts": active_alerts,
            },
        }

    def _causal_graph(self, context: Mapping[str, Any]) -> dict[str, Any]:
        graph = context.get("causal_graph")
        if not isinstance(graph, Mapping) or not graph:
            graph = {
                "nodes": ["Design Change", "Subsystem A", "Subsystem B", "Timeline"],
                "edges": [
                    {"from": "Design Change", "to": "Subsystem A", "impact": "scope"},
                    {"from": "Subsystem A", "to": "Subsystem B", "impact": "coordination"},
                    {"from": "Design Change", "to": "Timeline", "impact": "+2 days"},
                ],
            }

        return {
            "id": "causal_graph",
            "title": "Causal Graph Visualization",
            "summary": "Explains how changes propagate through connected systems.",
            "highlights": [f"{len(graph.get('nodes', []))} nodes", f"{len(graph.get('edges', []))} edges"],
            "details": graph,
        }

    def _root_cause_analysis(self, context: Mapping[str, Any]) -> dict[str, Any]:
        alert = _ensure_mapping(context.get("root_cause")) or {
            "alert": "Project 23% over budget",
            "contributors": {"Material cost increase": 0.6, "Scope creep": 0.4},
        }

        ranking = sorted(
            (
                {"factor": factor, "contribution": contribution}
                for factor, contribution in alert.get("contributors", {}).items()
            ),
            key=lambda item: item["contribution"],
            reverse=True,
        )

        return {
            "id": "root_cause",
            "title": "Automated Root Cause Analysis",
            "summary": alert.get("alert", ""),
            "highlights": [
                f"{entry['factor']} ({entry['contribution']:.0%})" for entry in ranking
            ],
            "details": {
                "contributors": ranking,
                "recommendation": "Prioritize supplier renegotiation and scope reset workshops",
            },
        }

    def _context_aware_defaults(self, context: Mapping[str, Any]) -> dict[str, Any]:
        domain = context.get("domain", "structural_design")
        suggestions = context.get("defaults")
        if not isinstance(suggestions, list) or not suggestions:
            suggestions = [
                "Run stability check",
                "Compare with similar projects",
                "Check material availability",
            ]

        return {
            "id": "context_defaults",
            "title": "Context-Aware Defaults",
            "summary": f"Pre-populates actions for {domain.replace('_', ' ')} workflows.",
            "highlights": suggestions,
            "details": {
                "domain": domain,
                "suggestions": suggestions,
            },
        }

    def _intelligent_summaries(self, context: Mapping[str, Any]) -> dict[str, Any]:
        summaries = context.get("summaries")
        if not isinstance(summaries, Mapping) or not summaries:
            summaries = {
                "executive": "Budget variance within 3%, timeline at moderate risk due to design approvals.",
                "technical_lead": "Foundation redesign awaiting final loads; inspection checklist auto-generated.",
            }

        return {
            "id": "intelligent_summaries",
            "title": "Intelligent Summarization",
            "summary": "Delivers tailored narratives based on audience priorities.",
            "highlights": list(summaries.values()),
            "details": {
                "summaries": summaries,
            },
        }

    @staticmethod
    def _score_document(query: str, document: str) -> int:
        keywords = [token for token in query.lower().split() if len(token) > 2]
        lowered = document.lower()
        return sum(lowered.count(keyword) for keyword in keywords)


suite = AdvancedIntelligenceSuite()

__all__ = ["AdvancedIntelligenceSuite", "suite"]
