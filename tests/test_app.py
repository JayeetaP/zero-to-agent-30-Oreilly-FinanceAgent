from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import app
from backend.models import PreferencePatch


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


def sample_request() -> dict:
    return {
        "focus": "global-markets",
        "question": "What moved global financial markets this week?",
        "time_window_days": 7,
        "preferred_sources": ["Reuters", "SEC & company IR"],
        "custom_domains": [],
        "broader_web": True,
        "mode": "sample",
    }


def run_sample_workflow() -> tuple[dict, dict, dict]:
    request = sample_request()
    plan = client.post("/api/plan", json=request).json()["result"]
    research = client.post(
        "/api/research", json={"request": request, "plan": plan}
    ).json()["result"]
    briefing = client.post(
        "/api/edit", json={"request": request, "plan": plan, "research": research}
    ).json()["result"]
    return plan, research, briefing


def test_frontend_is_live_first_and_health_is_served_by_one_app() -> None:
    page = client.get("/")
    assert page.status_code == 200
    assert "Briefing Lab" in page.text
    assert "Live briefing" in page.text
    assert "Sample run" in page.text
    assert page.text.index("Live briefing") < page.text.index("Sample run")

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["model_provider"] == "Ollama"
    assert health.json()["search_provider"] == "DDGS public metasearch"


def test_sample_run_is_a_sourced_briefing_document() -> None:
    plan, research, briefing = run_sample_workflow()

    assert len(plan["sections"]) == 3
    assert len(research["sections"]) == 3
    assert len(briefing["sections"]) == 3
    assert [len(section["items"]) for section in briefing["sections"]] == [3, 2, 3]
    assert len(briefing["key_takeaways"]) >= 3
    assert briefing["executive_summary"]
    assert briefing["mode"] == "sample"
    assert briefing["sample_captured_at"]

    source_ids = {source["id"] for source in briefing["sources"]}
    assert len(source_ids) == 8
    assert all(source["url"].startswith("https://") for source in briefing["sources"])
    assert all("example." not in source["url"] for source in briefing["sources"])
    assert all(source["publication_date"] for source in briefing["sources"])
    assert set(briefing["executive_source_ids"]).issubset(source_ids)
    assert all(
        set(item["source_ids"]).issubset(source_ids)
        for section in briefing["sections"]
        for item in section["items"]
    )


def test_ui_and_sample_copy_follow_the_style_rule() -> None:
    ui_copy = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    ui_copy += (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    sample_copy = (ROOT / "data" / "sample_run.json").read_text(encoding="utf-8")

    assert "—" not in ui_copy
    assert "—" not in sample_copy
    assert "synthetic" not in ui_copy.lower()
    assert "synthetic" not in sample_copy.lower()
    assert "insufficient evidence" not in ui_copy.lower()
    assert "insufficient evidence" not in sample_copy.lower()


def test_feedback_is_proposed_before_preferences_are_written(tmp_path: Path, monkeypatch) -> None:
    from backend import workflow

    memory_file = tmp_path / "memory.local.json"
    monkeypatch.setattr(workflow, "MEMORY_FILE", memory_file)
    _, _, briefing = run_sample_workflow()

    proposal_response = client.post(
        "/api/feedback",
        json={
            "mode": "sample",
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
