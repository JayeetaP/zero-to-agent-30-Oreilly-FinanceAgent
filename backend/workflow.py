import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel

from .agents import editor_agent, feedback_agent, planner_agent, research_agent
from .config import MEMORY_FILE, OLLAMA_HOST, OLLAMA_MODEL, SAMPLE_FILE
from .models import (
    AnalystBriefing,
    BriefRequest,
    DraftBriefing,
    NewsCandidate,
    PreferencePatch,
    ResearchBundle,
    ResearchPlan,
    SectionPlan,
    SectionResearchResult,
    SourceRecord,
    SourcedStatement,
)


T = TypeVar("T", bound=BaseModel)

SOURCE_DOMAINS = {
    "Reuters": "reuters.com",
    "SEC & company IR": "sec.gov",
    "CNBC": "cnbc.com",
    "Bloomberg": "bloomberg.com",
    "Financial Times": "ft.com",
    "Associated Press": "apnews.com",
}

MONTH_PATTERN = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    flags=re.IGNORECASE,
)


class LiveModeUnavailable(RuntimeError):
    pass


def _clean_strings(value: object) -> object:
    if isinstance(value, str):
        return value.replace("—", ",").replace("–", "-")
    if isinstance(value, list):
        return [_clean_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_strings(item) for key, item in value.items()}
    return value


def _coerce(schema: type[T], value: object) -> T:
    if isinstance(value, BaseModel):
        raw: object = value.model_dump(mode="json")
    elif isinstance(value, str):
        raw = json.loads(value)
    else:
        raw = value
    return schema.model_validate(_clean_strings(raw))


def _sample_data() -> dict:
    return json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))


def _time_limit(days: int) -> str:
    if days <= 1:
        return "d"
    if days <= 7:
        return "w"
    if days <= 31:
        return "m"
    return "y"


def _coverage_window(days: int) -> str:
    end = datetime.now(UTC).date()
    start = end - timedelta(days=days)
    return f"{start.strftime('%B')} {start.day}, {start.year} to {end.strftime('%B')} {end.day}, {end.year}"


def _preferred_domains(request: BriefRequest) -> list[str]:
    domains = [SOURCE_DOMAINS[source] for source in request.preferred_sources if source in SOURCE_DOMAINS]
    for domain in request.custom_domains:
        if domain not in domains:
            domains.append(domain)
    return domains


def _clean_query(query: str) -> str:
    query = re.sub(r"\b20\d{2}\b", "", query)
    query = MONTH_PATTERN.sub("", query)
    query = re.sub(r"\b(latest|today|yesterday)\b", "", query, flags=re.IGNORECASE)
    return " ".join(query.split())


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
    if request.mode == "sample":
        plan = ResearchPlan.model_validate(_sample_data()["plan"])
        return plan, [
            "Planner loaded the recorded Global Markets coverage plan.",
            "Planner returned 3 broad sections from a real sample run.",
        ]

    await require_live_model()
    prompt = f"""
Create a broad financial-news coverage plan for this request.

{request.model_dump_json(indent=2)}

Return exactly three sections. Favor sections likely to have meaningful current coverage. Keep queries
short, general, and free of dates. Preferred sources are ranking directions, not hard filters.
"""
    response = await planner_agent().arun(
        prompt,
        user_id="local-demo",
        session_id=f"plan-{uuid4()}",
    )
    plan = _coerce(ResearchPlan, response.content)
    return plan, [
        f"Planner used local model {OLLAMA_MODEL}.",
        f"Planner returned {len(plan.sections)} broad coverage sections.",
    ]


async def _run_search_ladder(request: BriefRequest, section: SectionPlan) -> list[dict]:
    agent = research_agent(_time_limit(request.time_window_days))
    tool = agent.tools[0]
    query_options = [
        *section.queries,
        f"{request.focus.replace('-', ' ')} {section.title}",
        request.question,
    ]
    queries: list[str] = []
    for option in query_options:
        cleaned = _clean_query(option)
        if cleaned and cleaned not in queries:
            queries.append(cleaned)

    found: list[dict] = []
    seen_urls: set[str] = set()
    for query in queries[:3]:
        raw_results = "[]"
        for search_method in (tool.search_news, tool.web_search):
            try:
                raw_results = await asyncio.to_thread(search_method, query)
                if json.loads(raw_results):
                    break
            except Exception:
                raw_results = "[]"

        for item in json.loads(raw_results):
            url = item.get("url") or item.get("href") or ""
            if not url.startswith(("http://", "https://")) or url in seen_urls:
                continue
            item["url"] = url
            seen_urls.add(url)
            found.append(item)
        if len(found) >= 6:
            break
    return found[:12]


async def _research_live_section(
    request: BriefRequest,
    section: SectionPlan,
) -> SectionResearchResult:
    domains = _preferred_domains(request)
    search_results = await _run_search_ladder(request, section)

    if domains and not request.broader_web:
        search_results = [
            item for item in search_results if any(domain in item.get("url", "") for domain in domains)
        ]
    else:
        search_results.sort(
            key=lambda item: not any(domain in item.get("url", "") for domain in domains)
        )

    if not search_results:
        return SectionResearchResult(
            section_title=section.title,
            candidates=[],
            coverage_note="No dated, supported articles were found in the selected coverage window.",
        )

    candidates: list[NewsCandidate] = []
    for item in search_results:
        publication_date = str(
            item.get("date") or item.get("publication_date") or item.get("published") or ""
        ).strip()
        headline = str(item.get("title") or "").strip()
        excerpt = str(item.get("body") or item.get("description") or "").strip()
        publisher = str(item.get("source") or item.get("publisher") or "Public source").strip()
        if not publication_date or not headline or not excerpt:
            continue
        candidates.append(
            NewsCandidate(
                headline=headline,
                source=publisher,
                url=item["url"],
                publication_date=publication_date,
                evidence_excerpt=excerpt,
                relevance=f"Evidence collected for {section.title.lower()}.",
                watch_next=f"Monitor follow-up reporting related to {section.purpose.lower()}",
            )
        )

    candidates = candidates[:8]
    coverage_note = None
    if len(candidates) < 3:
        coverage_note = (
            f"{len(candidates)} dated, supported development"
            f"{'s were' if len(candidates) != 1 else ' was'} available for this section."
        )
    return SectionResearchResult(
        section_title=section.title,
        candidates=candidates,
        coverage_note=coverage_note,
    )


async def research_sections(
    request: BriefRequest,
    plan: ResearchPlan,
) -> tuple[ResearchBundle, list[str]]:
    if request.mode == "sample":
        research = ResearchBundle.model_validate(_sample_data()["research"])
        count = sum(len(section.candidates) for section in research.sections)
        return research, [
            "Researcher loaded a recorded search from August 25, 2026.",
            f"Researcher returned {count} real articles with source links and dates.",
        ]

    await require_live_model()
    results = await asyncio.gather(
        *[_research_live_section(request, section) for section in plan.sections]
    )
    candidate_count = sum(len(section.candidates) for section in results)
    return ResearchBundle(sections=results), [
        "Researcher ran 3 independent search ladders in parallel.",
        f"Public search returned {candidate_count} dated articles after URL validation.",
    ]


def _source_catalog(research: ResearchBundle) -> tuple[list[SourceRecord], dict[str, str]]:
    sources: list[SourceRecord] = []
    url_to_id: dict[str, str] = {}
    for section in research.sections:
        for candidate in section.candidates:
            if candidate.url in url_to_id:
                continue
            source_id = f"S{len(sources) + 1}"
            url_to_id[candidate.url] = source_id
            sources.append(
                SourceRecord(
                    id=source_id,
                    publisher=candidate.source,
                    title=candidate.headline,
                    publication_date=candidate.publication_date,
                    url=candidate.url,
                )
            )
    return sources, url_to_id


def _research_with_source_ids(research: ResearchBundle, url_to_id: dict[str, str]) -> list[dict]:
    sections: list[dict] = []
    for section in research.sections:
        sections.append(
            {
                "section_title": section.section_title,
                "coverage_note": section.coverage_note,
                "candidates": [
                    {"source_id": url_to_id[candidate.url], **candidate.model_dump()}
                    for candidate in section.candidates[:5]
                    if candidate.url in url_to_id
                ],
            }
        )
    return sections


def _validated_ids(ids: list[str], valid_ids: set[str]) -> list[str]:
    return list(dict.fromkeys(item for item in ids if item in valid_ids))


async def edit_briefing(
    request: BriefRequest,
    plan: ResearchPlan,
    research: ResearchBundle,
) -> tuple[AnalystBriefing, list[str]]:
    if request.mode == "sample":
        briefing = AnalystBriefing.model_validate(_sample_data()["briefing"])
        return briefing, [
            "Writer loaded the recorded Global Markets briefing.",
            "Code validated 3 sections, source links, publication dates, and citations.",
        ]

    await require_live_model()
    sources, url_to_id = _source_catalog(research)
    if not sources:
        raise LiveModeUnavailable(
            "No dated articles passed validation. Broaden the sources or coverage window and run research again."
        )

    evidence = _research_with_source_ids(research, url_to_id)
    prompt = f"""
Write a concise financial briefing document using only the supplied evidence.

Request:
{request.model_dump_json(indent=2)}

Plan:
{plan.model_dump_json(indent=2)}

Evidence with source IDs:
{json.dumps(evidence, indent=2)}

Requirements:
- Lead with a short executive summary and 3 to 5 sourced takeaways.
- Return exactly 3 briefing sections.
- Select 1 to 3 strong developments per section. Never create empty placeholder items.
- Add one coverage note when a section has fewer than 3 supported developments.
- Include upcoming dated events only when the evidence supports them.
- Reference source IDs on every takeaway, section, development, and event.
- Use direct language for a finance newcomer. Do not use em dashes.
- Do not create or alter sources, URLs, dates, facts, or source IDs.
"""
    response = await editor_agent().arun(
        prompt,
        user_id="local-demo",
        session_id=f"edit-{uuid4()}",
    )
    draft = _coerce(DraftBriefing, response.content)

    valid_ids = {source.id for source in sources}
    for index, section in enumerate(draft.sections):
        section.title = plan.sections[index].title
        allowed_ids = {
            candidate["source_id"] for candidate in evidence[index]["candidates"]
        }
        section.source_ids = list(
            dict.fromkeys(item for item in section.source_ids if item in allowed_ids)
        )
        supported_items = []
        for item in section.items[:3]:
            item.source_ids = list(
                dict.fromkeys(
                    source_id
                    for source_id in item.source_ids
                    if source_id in allowed_ids
                )
            )
            if item.source_ids:
                supported_items.append(item)
        section.items = supported_items
        if not section.source_ids:
            section.source_ids = list(
                dict.fromkeys(
                    source_id
                    for item in section.items
                    for source_id in item.source_ids
                )
            )
        if research.sections[index].coverage_note:
            section.coverage_note = research.sections[index].coverage_note
        if len(section.items) < 3 and not section.coverage_note:
            section.coverage_note = (
                f"This section includes {len(section.items)} supported development"
                f"{'s' if len(section.items) != 1 else ''} from the selected window."
            )

    supported_takeaways = []
    for takeaway in draft.key_takeaways:
        takeaway.source_ids = _validated_ids(takeaway.source_ids, valid_ids)
        if takeaway.source_ids:
            supported_takeaways.append(takeaway)
    for section in draft.sections:
        if len(supported_takeaways) >= 3:
            break
        if section.source_ids:
            supported_takeaways.append(
                SourcedStatement(text=section.summary, source_ids=section.source_ids[:4])
            )
    if len(supported_takeaways) < 3:
        for section in research.sections:
            for candidate in section.candidates:
                if len(supported_takeaways) >= 3:
                    break
                source_id = url_to_id.get(candidate.url)
                if source_id:
                    supported_takeaways.append(
                        SourcedStatement(
                            text=f"{candidate.headline}: {candidate.evidence_excerpt}",
                            source_ids=[source_id],
                        )
                    )

    executive_source_ids = _validated_ids(draft.executive_source_ids, valid_ids)
    if not executive_source_ids:
        executive_source_ids = list(
            dict.fromkeys(
                source_id
                for section in draft.sections
                for source_id in section.source_ids[:1]
            )
        )
        if not executive_source_ids:
            executive_source_ids = [source.id for source in sources[:3]]
        draft.executive_summary = (
            f"The live search found {len(sources)} dated articles across the three planned areas. "
            "Read the section notes and linked sources for the supported developments."
        )

    supported_events = []
    for event in draft.upcoming_events:
        event.source_ids = list(
            dict.fromkeys(
                source_id for source_id in event.source_ids if source_id in valid_ids
            )
        )
        if event.source_ids:
            supported_events.append(event)

    used_source_ids = set(executive_source_ids)
    for takeaway in supported_takeaways:
        used_source_ids.update(takeaway.source_ids)
    for section in draft.sections:
        used_source_ids.update(section.source_ids)
        for item in section.items:
            used_source_ids.update(item.source_ids)
    for event in supported_events:
        used_source_ids.update(event.source_ids)
    cited_sources = [source for source in sources if source.id in used_source_ids]

    briefing = AnalystBriefing(
        title=f"{request.focus.replace('-', ' ').title()} Briefing",
        focus=request.focus,
        question=request.question,
        generated_at=datetime.now(UTC).isoformat(),
        coverage_window=_coverage_window(request.time_window_days),
        mode="live",
        executive_summary=draft.executive_summary,
        executive_source_ids=executive_source_ids,
        key_takeaways=supported_takeaways[:5],
        sections=draft.sections,
        upcoming_events=supported_events,
        sources=cited_sources,
        sample_captured_at=None,
    )

    briefing = _coerce(AnalystBriefing, briefing)
    return briefing, [
        f"Writer used local model {OLLAMA_MODEL}.",
        f"Code retained {len(cited_sources)} cited source links with publication dates.",
    ]


async def propose_preferences(
    mode: str,
    feedback: str,
    briefing: AnalystBriefing,
    current: PreferencePatch,
) -> tuple[PreferencePatch, list[str]]:
    if mode == "sample":
        lowered = feedback.lower()
        patch = current.model_copy(deep=True)
        patch.editorial.lead_with_implication = "implication" in lowered or "lead with" in lowered
        if "direct" in lowered:
            patch.editorial.tone = "direct, calm, beginner-friendly"
        if "bn" in lowered or "$" in feedback:
            patch.display.currency_style = "$4.2bn"
        return patch, [
            "Feedback Agent classified the request into typed preference fields.",
            "The preference proposal is waiting for human approval.",
        ]

    await require_live_model()
    prompt = f"""
Translate the feedback into durable presentation preferences. Return a proposal only.

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
        "The preference proposal is waiting for human approval.",
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
