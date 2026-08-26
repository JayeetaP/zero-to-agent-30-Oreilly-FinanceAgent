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
    assert "beginner-friendly" not in ui_copy.lower()
    assert "Use $4.2bn instead of USD 4.2 billion" not in ui_copy
    assert "Share a durable preference" in ui_copy
    assert "preferred sources or topics to exclude" in ui_copy
    assert "Add to active memory" in ui_copy
    assert "Save separately" in ui_copy
    assert "Cumulative snapshot at version" in ui_copy
    assert "Active memory" in ui_copy
    assert "Memory history" in ui_copy


def test_feedback_is_proposed_before_preferences_are_written(tmp_path: Path, monkeypatch) -> None:
    from backend import memory

    memory_file = tmp_path / "memory.db"
    monkeypatch.setattr(memory, "MEMORY_DB_FILE", memory_file)
    monkeypatch.setattr(memory, "LEGACY_MEMORY_FILE", tmp_path / "legacy.json")
    memory._manager_for.cache_clear()
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

    approval = client.post(
        "/api/memory/approve",
        json={"patch": proposal, "feedback": "Use $4.2bn and lead with the implication."},
    )
    assert approval.status_code == 200
    assert approval.json()["version"] == 1
    assert approval.json()["history"][0]["changes"]
    assert memory_file.exists()


def test_source_feedback_changes_only_source_priority() -> None:
    _, _, briefing = run_sample_workflow()
    current = PreferencePatch()
    current.research.preferred_sources = ["Reuters"]
    current.editorial.lead_with_implication = True
    current.display.currency_style = "$4.2bn"

    response = client.post(
        "/api/feedback",
        json={
            "mode": "sample",
            "feedback": "Prioritize Bloomberg over Reuters.",
            "briefing": briefing,
            "current_preferences": current.model_dump(),
        },
    )

    assert response.status_code == 200
    proposal = response.json()["result"]
    assert proposal["research"]["preferred_sources"] == ["Bloomberg", "Reuters"]
    assert proposal["editorial"] == current.editorial.model_dump()
    assert proposal["display"] == current.display.model_dump()


def test_three_feedback_rounds_create_visible_history_and_can_be_reactivated(
    tmp_path: Path, monkeypatch
) -> None:
    from backend import memory

    monkeypatch.setattr(memory, "MEMORY_DB_FILE", tmp_path / "memory.db")
    monkeypatch.setattr(memory, "LEGACY_MEMORY_FILE", tmp_path / "legacy.json")
    memory._manager_for.cache_clear()

    first = PreferencePatch()
    first.editorial.lead_with_implication = True
    second = first.model_copy(deep=True)
    second.display.currency_style = "$4.2bn"
    third = second.model_copy(deep=True)
    third.research.preferred_sources = ["Reuters"]

    rounds = [
        (first, "Lead with the implication."),
        (second, "Use compact currency."),
        (third, "Prioritize Reuters."),
    ]
    for patch, feedback in rounds:
        response = client.post(
            "/api/memory/approve",
            json={"patch": patch.model_dump(), "feedback": feedback},
        )
        assert response.status_code == 200

    saved = client.get("/api/memory").json()
    assert saved["active_version"] == 3
    assert saved["latest_version"] == 3
    assert [item["version"] for item in saved["history"]] == [3, 2, 1]
    assert saved["history"][0]["changes"][0]["path"] == "research.preferred_sources"
    assert saved["history"][1]["changes"][0]["path"] == "display.currency_style"

    activated = client.post("/api/memory/activate", json={"version": 1})
    assert activated.status_code == 200
    assert activated.json()["active_version"] == 1
    assert activated.json()["latest_version"] == 3
    assert activated.json()["preferences"]["editorial"]["lead_with_implication"] is True
    assert activated.json()["preferences"]["display"]["currency_style"] == "USD 4.2 billion"


def test_separate_memory_version_does_not_replace_active_memory(tmp_path: Path, monkeypatch) -> None:
    from backend import memory

    monkeypatch.setattr(memory, "MEMORY_DB_FILE", tmp_path / "memory.db")
    monkeypatch.setattr(memory, "LEGACY_MEMORY_FILE", tmp_path / "legacy.json")
    memory._manager_for.cache_clear()

    active = PreferencePatch()
    active.editorial.lead_with_implication = True
    first = client.post(
        "/api/memory/approve",
        json={
            "patch": active.model_dump(),
            "feedback": "Lead with the implication.",
            "strategy": "merge",
            "base_version": 0,
        },
    )
    assert first.status_code == 200

    separate = active.model_copy(deep=True)
    separate.research.preferred_sources = ["Bloomberg"]
    second = client.post(
        "/api/memory/approve",
        json={
            "patch": separate.model_dump(),
            "feedback": "Keep Bloomberg as a separate option.",
            "strategy": "separate",
            "base_version": 1,
        },
    )
    saved = second.json()
    assert second.status_code == 200
    assert saved["saved_version"] == 2
    assert saved["saved_strategy"] == "separate"
    assert saved["active_version"] == 1
    assert saved["latest_version"] == 2
    assert saved["preferences"]["research"]["preferred_sources"] == []
    assert saved["history"][0]["strategy"] == "separate"
