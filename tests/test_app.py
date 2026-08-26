from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.models import PreferencePatch


client = TestClient(app)


def fixture_request() -> dict:
    return {
        "focus": "sustainable",
        "question": "What happened in sustainable finance this week?",
        "time_window_days": 7,
        "preferred_sources": ["Reuters", "SEC & company IR"],
        "custom_domains": [],
        "broader_web": True,
        "mode": "fixture",
    }


def test_frontend_and_health_are_served_by_one_app() -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert "Briefing Lab" in page.text
    assert "Plain HTML, CSS, JS" in page.text

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["model_provider"] == "Ollama"
    assert health.json()["search_provider"] == "DDGS public metasearch"


def test_fixture_workflow_returns_three_by_three() -> None:
    request = fixture_request()

    plan_response = client.post("/api/plan", json=request)
    assert plan_response.status_code == 200
    plan = plan_response.json()["result"]
    assert len(plan["sections"]) == 3

    research_response = client.post(
        "/api/research",
        json={"request": request, "plan": plan},
    )
    assert research_response.status_code == 200
    research = research_response.json()["result"]
    assert len(research["sections"]) == 3

    edit_response = client.post(
        "/api/edit",
        json={"request": request, "plan": plan, "research": research},
    )
    assert edit_response.status_code == 200
    briefing = edit_response.json()["result"]
    assert len(briefing["sections"]) == 3
    assert all(len(section["items"]) == 3 for section in briefing["sections"])
    assert all(item["url"] for section in briefing["sections"] for item in section["items"])


def test_feedback_is_proposed_before_memory_is_written(tmp_path: Path, monkeypatch) -> None:
    from backend import workflow

    memory_file = tmp_path / "memory.local.json"
    monkeypatch.setattr(workflow, "MEMORY_FILE", memory_file)

    request = fixture_request()
    plan = client.post("/api/plan", json=request).json()["result"]
    research = client.post("/api/research", json={"request": request, "plan": plan}).json()["result"]
    briefing = client.post(
        "/api/edit",
        json={"request": request, "plan": plan, "research": research},
    ).json()["result"]

    proposal_response = client.post(
        "/api/feedback",
        json={
            "mode": "fixture",
            "feedback": "Use $4.2bn and lead with the implication.",
            "briefing": briefing,
            "current_preferences": PreferencePatch().model_dump(),
        },
    )
    proposal = proposal_response.json()["result"]
    assert proposal["display"]["currency_style"] == "$4.2bn"
    assert proposal["editorial"]["lead_with_implication"] is True
    assert not memory_file.exists()

    approval = client.post("/api/memory/approve", json={"patch": proposal})
    assert approval.status_code == 200
    assert approval.json()["version"] == 1
    assert memory_file.exists()
