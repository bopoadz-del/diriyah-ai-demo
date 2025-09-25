from prometheus_client import Counter, Histogram

intent_accuracy = Counter("intent_accuracy_total", "Count of intent classifications by outcome", ["intent", "outcome"])
service_latency = Histogram("service_latency_seconds", "Latency of backend services", ["service"])
user_feedback = Counter("user_feedback_total", "User satisfaction feedback", ["type"])
alert_validation = Counter("alert_validation_total", "Alert validation outcomes", ["type"])

# Feature metrics
intent_requests = Counter("intent_requests_total", "Intents classified", ["intent"])
context_adjustments = Counter("context_adjustments_total", "Intents adjusted by context")
entity_extractions = Counter("entity_extractions_total", "Entity extractions")
spacy_entities_extracted = Counter("spacy_entities_extracted_total", "spaCy entities extracted")
memory_queries = Counter("memory_queries_total", "Vector memory retrievals")
workflow_runs = Counter("workflow_runs_total", "Workflow executions", ["workflow"])
suggestions_made = Counter("suggestions_made_total", "Predictive suggestions", ["intent"])
alerts_analyzed = Counter("alerts_analyzed_total", "Alerts analyzed", ["priority"])
alert_suggestions = Counter("alert_suggestions_total", "Alert suggestions generated", ["type"])
proactive_triggers = Counter("proactive_triggers_total", "Proactive triggers fired", ["message"])
reports_generated = Counter("reports_generated_total", "Reports generated", ["package"])
report_mode = Counter("report_mode_total", "Report requests by mode", ["mode"])
preferences_set = Counter("preferences_set_total", "User preferences set", ["key"])
access_decisions = Counter("access_decisions_total", "Access control decisions", ["result","action"])
explanations_given = Counter("explanations_given_total", "Explanations produced")
project_intel_requests = Counter("project_intel_requests_total", "Project intel analyses run", ["project"])
