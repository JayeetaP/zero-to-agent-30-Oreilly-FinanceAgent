from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.websearch import WebSearchTools

from .config import OLLAMA_HOST, OLLAMA_MODEL
from .models import (
    AnalystBriefing,
    PreferencePatch,
    ResearchPlan,
    SectionResearchResult,
)
from .skills import load_rules, load_skill


def local_model() -> Ollama:
    return Ollama(
        id=OLLAMA_MODEL,
        host=OLLAMA_HOST,
        timeout=240,
        keep_alive="30m",
        options={"temperature": 0.2},
    )


def planner_agent() -> Agent:
    return Agent(
        id="planner",
        name="Planner Agent",
        model=local_model(),
        instructions=[
            load_skill("plan-financial-research"),
            "Return exactly three sections. Keep titles understandable to a finance newcomer.",
        ],
        output_schema=ResearchPlan,
        use_json_mode=True,
        add_datetime_to_context=True,
        telemetry=False,
        retries=1,
    )


def news_search_tool(time_limit: str) -> WebSearchTools:
    return WebSearchTools(
        backend="auto",
        enable_search=True,
        enable_news=True,
        timelimit=time_limit,
        fixed_max_results=8,
        timeout=20,
    )


def research_agent() -> Agent:
    return Agent(
        id="news-researcher",
        name="News Research Agent",
        model=local_model(),
        instructions=[
            load_skill("search-and-ground-news"),
            load_rules(),
            "The workflow already ran the search tool. Evaluate only the supplied results. "
            "Never invent or alter a URL, date, publisher, or excerpt.",
        ],
        output_schema=SectionResearchResult,
        use_json_mode=True,
        add_datetime_to_context=True,
        telemetry=False,
        retries=1,
    )


def editor_agent() -> Agent:
    return Agent(
        id="briefing-editor",
        name="Briefing Editor Agent",
        model=local_model(),
        instructions=[
            load_skill("write-three-section-briefing"),
            load_rules(),
            "Use only the supplied research. Preserve source URLs exactly.",
        ],
        output_schema=AnalystBriefing,
        use_json_mode=True,
        add_datetime_to_context=True,
        telemetry=False,
        retries=1,
    )


def feedback_agent() -> Agent:
    return Agent(
        id="feedback-memory",
        name="Feedback & Memory Agent",
        model=local_model(),
        instructions=[
            load_skill("learn-briefing-preferences"),
            "Return a proposal only. Do not claim that memory has already been saved.",
        ],
        output_schema=PreferencePatch,
        use_json_mode=True,
        telemetry=False,
        retries=1,
    )
