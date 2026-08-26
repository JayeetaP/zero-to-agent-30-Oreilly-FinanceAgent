from typing import Literal

from pydantic import BaseModel, Field, field_validator


FocusArea = Literal[
    "global-markets",
    "stocks",
    "private-credit",
    "rates-bonds",
    "banking-deals",
    "commodities-currencies",
]
RunMode = Literal["sample", "live"]


class BriefRequest(BaseModel):
    focus: FocusArea = "global-markets"
    question: str = Field(min_length=3, max_length=500)
    time_window_days: int = Field(default=7, ge=1, le=365)
    preferred_sources: list[str] = Field(default_factory=list, max_length=10)
    custom_domains: list[str] = Field(default_factory=list, max_length=10)
    broader_web: bool = True
    mode: RunMode = "live"

    @field_validator("custom_domains")
    @classmethod
    def clean_domains(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            domain = value.strip().lower().replace("https://", "").replace("http://", "")
            domain = domain.split("/")[0]
            if domain and domain not in cleaned:
                cleaned.append(domain)
        return cleaned


class SectionPlan(BaseModel):
    title: str
    purpose: str
    queries: list[str] = Field(min_length=1, max_length=3)


class ResearchPlan(BaseModel):
    sections: list[SectionPlan] = Field(min_length=3, max_length=3)


class NewsCandidate(BaseModel):
    headline: str
    source: str
    url: str
    publication_date: str
    evidence_excerpt: str
    relevance: str
    watch_next: str


class SectionResearchResult(BaseModel):
    section_title: str
    candidates: list[NewsCandidate] = Field(default_factory=list, max_length=8)
    coverage_note: str | None = None


class ResearchBundle(BaseModel):
    sections: list[SectionResearchResult] = Field(min_length=3, max_length=3)


class SourceRecord(BaseModel):
    id: str
    publisher: str
    title: str
    publication_date: str
    url: str

    @field_validator("url")
    @classmethod
    def require_web_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("Source URL must be an absolute web URL")
        return value


class SourcedStatement(BaseModel):
    text: str
    source_ids: list[str] = Field(min_length=1, max_length=4)


class BriefingItem(BaseModel):
    headline: str
    summary: str
    analyst_implication: str
    watch_next: str
    source_ids: list[str] = Field(min_length=1, max_length=3)


class BriefingSection(BaseModel):
    title: str
    summary: str
    source_ids: list[str] = Field(default_factory=list, max_length=8)
    items: list[BriefingItem] = Field(default_factory=list, max_length=3)
    coverage_note: str | None = None


class UpcomingEvent(BaseModel):
    date: str
    event: str
    why_it_matters: str
    source_ids: list[str] = Field(min_length=1, max_length=3)


class DraftBriefing(BaseModel):
    executive_summary: str
    executive_source_ids: list[str] = Field(min_length=1, max_length=8)
    key_takeaways: list[SourcedStatement] = Field(min_length=3, max_length=5)
    sections: list[BriefingSection] = Field(min_length=3, max_length=3)
    upcoming_events: list[UpcomingEvent] = Field(default_factory=list, max_length=5)


class AnalystBriefing(BaseModel):
    title: str
    focus: str
    question: str
    generated_at: str
    coverage_window: str
    mode: RunMode
    executive_summary: str
    executive_source_ids: list[str] = Field(min_length=1, max_length=8)
    key_takeaways: list[SourcedStatement] = Field(min_length=3, max_length=5)
    sections: list[BriefingSection] = Field(min_length=3, max_length=3)
    upcoming_events: list[UpcomingEvent] = Field(default_factory=list, max_length=5)
    sources: list[SourceRecord] = Field(min_length=1)
    sample_captured_at: str | None = None


class ResearchPreferences(BaseModel):
    preferred_sources: list[str] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)


class EditorialPreferences(BaseModel):
    tone: str = "direct, professional, analyst-oriented"
    lead_with_implication: bool = False
    jargon_level: str = "define unfamiliar terms"


class DisplayPreferences(BaseModel):
    currency_style: str = "USD 4.2 billion"
    date_style: str = "August 25, 2026"


class PreferencePatch(BaseModel):
    research: ResearchPreferences = Field(default_factory=ResearchPreferences)
    editorial: EditorialPreferences = Field(default_factory=EditorialPreferences)
    display: DisplayPreferences = Field(default_factory=DisplayPreferences)


class ResearchRequest(BaseModel):
    request: BriefRequest
    plan: ResearchPlan


class EditorRequest(BaseModel):
    request: BriefRequest
    plan: ResearchPlan
    research: ResearchBundle


class FeedbackRequest(BaseModel):
    mode: RunMode = "live"
    feedback: str = Field(min_length=3, max_length=1000)
    briefing: AnalystBriefing
    current_preferences: PreferencePatch = Field(default_factory=PreferencePatch)


class ApprovalRequest(BaseModel):
    patch: PreferencePatch
    feedback: str = Field(default="Approved preference update", max_length=1000)


class MemoryActivateRequest(BaseModel):
    version: int = Field(ge=1)
