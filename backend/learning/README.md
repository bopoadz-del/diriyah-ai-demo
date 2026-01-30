# Learning Feedback Loop (Useful Mode)

This module stores human feedback, reviews it through governance, and exports
versioned JSONL datasets for offline training. No model training or promotion
occurs here.

## Example exported manifest

```json
{
  "dataset_name": "intent_routing",
  "version_tag": "20250115T120102Z",
  "workspace_id": "ws_demo",
  "schema_version": 1,
  "created_at": "2025-01-15T12:01:02+00:00",
  "record_count": 42,
  "records_path": "backend/learning_datasets/intent_routing/20250115T120102Z/records.jsonl"
}
```
