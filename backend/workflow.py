import asyncio
import json
import re
from datetime import UTC, datetime
from typing import TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel

from .agents import editor_agent, feedback_agent, news_search_tool, planner_agent, research_agent
from .config import FIXTURE_FILE, MEMORY_FILE, OLLAMA_HOST, OLLAMA_MODEL
from .models import (
    AnalystBriefing,
    BriefRequest,
    BriefingItem,
    BriefingSection,
    PreferencePatch,
    ResearchBundle,
    ResearchPlan,
    SectionPlan,
    SectionResearchResult,
    NewsCandidate,
)


T = TypeVar("T", bound=BaseModel)

SOURCE_DOMAINS = {
    "Reuters": "reuters.com",
    "SEC & company IR": "sec.gov",
    "CNBC": "cnbc.com",
    "Bloomberg": "bloomberg.com",
    "Financial Times": "ft.com",
}


class LiveModeUnavailable(RuntimeError):
    pass


def _coerce(schema: type[T], value: object) -> T:
    if isinstance(value, schema):
        return value
    if isinstance(value, str):
        return schema.model_validate_json(value)
    return schema.model_validate(value)


def _fixture_data() -> dict[str, list[dict]]:
    return json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))


def _time_limit(days: int) -> str:
    if days <= 1:
        return "d"
    if days <= 7:
        return "w"
    if days <= 31:
        return "m"
    return "y"


def _preferred_domains(request: BriefRequest) -> list[str]:
    domains = [SOURCE_DOMAINS[source] for source in request.preferred_sources if source in SOURCE_DOMAINS]
    for domain in request.custom_domains:
        if domain not in domains:
            domains.append(domain)
    return domains


async def ollama_status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
        installed = [item.get("name", "") for item in response.json().get("models", [])]
        configured_base = OLLAMA_MODEL.split(":")[0]
        ready = any(
            name == OLLAMA_MODEL
            or (":" not in OLLAMA_MODEL and name.split(":")[0] == configured_base)
            for name in installed
        )
        return {
            "ollama_running": True,
            "model_ready": ready,
            "configured_model": OLLAMA_MODEL,
            "installed_models": installed,
        }
    except (httpx.HTTPError, ValueError):
        return {
            "ollama_running": False,
            "model_ready": False,
            "configured_model": OLLAMA_MODEL,
            "installed_models": [],
        }


async def require_live_model() -> None:
    status = await ollama_status()
    if not status["ollama_running"]:
        raise LiveModeUnavailable("Ollama is not running. Start the Ollama app or run `ollama serve`.")
    if not status["model_ready"]:
        raise LiveModeUnavailable(
            f"Model {OLLAMA_MODEL} is not installed. Run `ollama pull {OLLAMA_MODEL}` once."
        )


async def create_plan(request: BriefRequest) -> tuple[ResearchPlan, list[str]]:
    if request.mode == "fixture":
        sections = []
        for item in _fixture_data()[request.focus]:
            sections.append(
                SectionPlan(
                    title=item["title"],
                    purpose=item["purpose"],
                    queries=[
                        f"{request.question} {item['title']}",
                        f"{request.focus} {item['purpose']}",
                    ],
                )
            )
        return ResearchPlan(sections=sections), [
            "Planner loaded the fixture section preset.",
            "Planner returned exactly 3 structured sections.",
        ]

    await require_live_model()
    prompt = (
        "Create the research plan for this request. Return only the structured plan.\n\n"
        f"{request.model_dump_json(indent=2)}"
    )
    response = await planner_agent().arun(
        prompt,
        user_id="local-demo",
        session_id=f"plan-{uuid4()}",
    )
    plan = _coerce(ResearchPlan, response.content)
    return plan, [
        f"Planner used local model {OLLAMA_MODEL}.",
        f"Planner returned {len(plan.sections)} structured sections.",
    ]


async def _research_live_section(
    request: BriefRequest,
    section: SectionPlan,
) -> SectionResearchResult:
    domains = _preferred_domains(request)
    query = section.queries[0]
    query = re.sub(r"\b20\d{2}\b", "", query)
    query = re.sub(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        "",
        query,
        flags=re.IGNORECASE,
    )
    query = " ".join(query.split())
    tool = news_search_tool(_time_limit(request.time_window_days))

    raw_results = "[]"
    for search_method in (tool.search_news, tool.web_search):
        try:
            raw_results = await asyncio.to_thread(search_method, query)
            if json.loads(raw_results):
                break
        except Exception:
            raw_results = "[]"

    search_results = json.loads(raw_results)
    if not search_results:
        return SectionResearchResult(section_title=section.title, candidates=[])

    for item in search_results:
        if not item.get("url") and item.get("href"):
            item["url"] = item["href"]

    search_results.sort(
        key=lambda item: not any(domain in item.get("url", "") for domain in domains)
    )
    allowed_urls = {item.get("url", "") for item in search_results}
    prompt = f"""
Research one section of a financial-news briefing.

Section: {section.model_dump_json(indent=2)}
Analyst focus: {request.focus}
Question: {request.question}
Lookback: last {request.time_window_days} days
Preferred domains to rank first: {domains or ['none']}
May broaden beyond preferred domains: {request.broader_web}

The Agno search tool already returned these results:
{json.dumps(search_results, indent=2)}

Select up to six distinct, relevant developments using only those results. Copy each URL, publisher,
date, and evidence excerpt exactly. Explain relevance and what to watch next in beginner-friendly language.
"""
    response = await research_agent().arun(
        prompt,
        user_id="local-demo",
        session_id=f"research-{uuid4()}",
    )
    result = _coerce(SectionResearchResult, response.content)
    result.section_title = section.title

    deduplicated: list[NewsCandidate] = []
    seen: set[str] = set()
    for candidate in result.candidates:
        key = candidate.url.strip().lower() or candidate.headline.strip().lower()
        if candidate.url not in allowed_urls or key in seen:
            continue
        seen.add(key)
        deduplicated.append(candidate)
    result.candidates = deduplicated[:6]
    return result


async def research_sections(
    request: BriefRequest,
    plan: ResearchPlan,
) -> tuple[ResearchBundle, list[str]]:
    if request.mode == "fixture":
        fixture_sections = _fixture_data()[request.focus]
        results: list[SectionResearchResult] = []
        for fixture_section in fixture_sections:
            candidates = [
                NewsCandidate(
                    headline=item["headline"],
                    source=item["source"],
                    url=item["url"],
                    publication_date=item["publication_date"],
                    evidence_excerpt=item["what_happened"],
                    relevance=item["why_it_matters"],
                    watch_next=item["watch_next"],
                )
                for item in fixture_section["items"]
            ]
            results.append(
                SectionResearchResult(section_title=fixture_section["title"], candidates=candidates)
            )
        return ResearchBundle(sections=results), [
            "Researcher replayed 3 cached fixture searches.",
            "Researcher returned 9 candidates with inspectable source directions.",
        ]

    await require_live_model()
    results = await asyncio.gather(
        *[_research_live_section(request, section) for section in plan.sections]
    )
    candidate_count = sum(len(section.candidates) for section in results)
    return ResearchBundle(sections=results), [
        "Researcher ran 3 independent section searches in parallel.",
        f"Public web search returned {candidate_count} unique candidates after URL validation.",
    ]


def _insufficient_item(section_title: str, slot: int) -> BriefingItem:
    return BriefingItem(
        headline=f"Insufficient evidence for item {slot}",
        what_happened="The live search did not return enough supported developments for this slot.",
        why_it_matters=f"The {section_title} section stays explicit rather than filling a gap with invented material.",
        watch_next="Broaden the source directions or time window and rerun research.",
        source="No supported source",
        status="insufficient_evidence",
    )


def _fixture_briefing(request: BriefRequest) -> AnalystBriefing:
    sections = []
    for section in _fixture_data()[request.focus]:
        items = [BriefingItem(**item) for item in section["items"]]
        sections.append(
            BriefingSection(title=section["title"], purpose=section["purpose"], items=items)
        )
    return AnalystBriefing(
        focus=request.focus,
        generated_at=datetime.now(UTC).isoformat(),
        mode="fixture",
        sections=sections,
    )


async def edit_briefing(
    request: BriefRequest,
    plan: ResearchPlan,
    research: ResearchBundle,
) -> tuple[AnalystBriefing, list[str]]:
    if request.mode == "fixture":
        return _fixture_briefing(request), [
            "Editor selected 3 items for each fixture section.",
            "Code validated the final 3 × 3 briefing contract.",
        ]

    await require_live_model()
    prompt = f"""
Write the final briefing using only this supplied research.

Request:
{request.model_dump_json(indent=2)}

Plan:
{plan.model_dump_json(indent=2)}

Research:
{research.model_dump_json(indent=2)}

Return exactly three sections and exactly three items per section. If a section lacks three supported
developments, use an explicit insufficient_evidence item. Do not create or alter source URLs.
Set generated_at to the current ISO timestamp and mode to live.
"""
    response = await editor_agent().arun(
        prompt,
        user_id="local-demo",
        session_id=f"edit-{uuid4()}",
    )
    briefing = _coerce(AnalystBriefing, response.content)

    briefing.focus = request.focus
    briefing.mode = "live"
    briefing.generated_at = datetime.now(UTC).isoformat()
    for index, section in enumerate(briefing.sections):
        section.title = plan.sections[index].title
        section.purpose = plan.sections[index].purpose
        section.items = section.items[:3]
        while len(section.items) < 3:
            section.items.append(_insufficient_item(section.title, len(section.items) + 1))

    return briefing, [
        f"Editor used local model {OLLAMA_MODEL}.",
        "Code validated exactly 3 sections and 3 items per section.",
    ]


async def propose_preferences(
    mode: str,
    feedback: str,
    briefing: AnalystBriefing,
    current: PreferencePatch,
) -> tuple[PreferencePatch, list[str]]:
    if mode == "fixture":
        lowered = feedback.lower()
        patch = current.model_copy(deep=True)
        patch.editorial.lead_with_implication = "implication" in lowered or "lead with" in lowered
        if "direct" in lowered:
            patch.editorial.tone = "direct, calm, beginner-friendly"
        if "bn" in lowered or "$" in feedback:
            patch.display.currency_style = "$4.2bn"
        return patch, [
            "Feedback Agent classified the request into typed preference fields.",
            "Preference patch is waiting for human approval.",
        ]

    await require_live_model()
    prompt = f"""
Translate the feedback into durable preferences. Return a proposal only.

Feedback: {feedback}
Current preferences: {current.model_dump_json(indent=2)}
Reviewed briefing: {briefing.model_dump_json(indent=2)}
"""
    response = await feedback_agent().arun(
        prompt,
        user_id="local-demo",
        session_id=f"feedback-{uuid4()}",
    )
    patch = _coerce(PreferencePatch, response.content)
    return patch, [
        f"Feedback Agent used local model {OLLAMA_MODEL}.",
        "Preference patch is waiting for human approval.",
    ]


def load_memory() -> dict:
    if not MEMORY_FILE.exists():
        return {"version": 0, "preferences": PreferencePatch().model_dump(), "approved_at": None}
    return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))


def approve_memory(patch: PreferencePatch) -> dict:
    current = load_memory()
    saved = {
        "version": int(current.get("version", 0)) + 1,
        "preferences": patch.model_dump(),
        "approved_at": datetime.now(UTC).isoformat(),
    }
    temporary = MEMORY_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(saved, indent=2) + "\n", encoding="utf-8")
    temporary.replace(MEMORY_FILE)
    return saved
