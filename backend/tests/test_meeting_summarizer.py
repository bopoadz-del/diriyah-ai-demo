from backend.services.meeting_summarizer import summarize_transcript


def test_summarize_transcript_produces_structured_minutes() -> None:
    transcript = (
        "Project Manager: Let's review the foundation progress. Concrete pour completed for zones A and B, "
        "but zone C delayed by the rebar delivery.\n"
        "Design Lead: Decision: Approve revised façade panels with bronze finish.\n"
        "Operations Lead: Action assigned to Procurement to place the order by Friday.\n"
        "Structural Engineer: Issue: Elevator core vendor still awaiting final drawings; this is becoming critical.\n"
        "Project Manager: Action assigned to Sarah to deliver the updated drawings by Tuesday.\n"
    )

    summary = summarize_transcript(transcript)

    assert "Key decisions" in summary["summary"]
    assert any("façade panels" in decision["description"] for decision in summary["decisions"])
    assert any(item.get("owner") == "Procurement" for item in summary["action_items"])
    assert any(item.get("owner") == "Sarah" for item in summary["action_items"])
    assert any(issue.get("severity") == "high" for issue in summary["issues"])


def test_summarize_transcript_handles_empty_input() -> None:
    assert summarize_transcript("") == {
        "summary": "",
        "decisions": [],
        "action_items": [],
        "issues": [],
    }
