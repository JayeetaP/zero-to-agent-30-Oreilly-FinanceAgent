from typing import Literal

from pydantic import BaseModel, Field, field_validator


FocusArea = Literal["sustainable", "consumer", "private-credit"]
RunMode = Literal["fixture", "live"]


class BriefRequest(BaseModel):
    focus: FocusArea
    question: str = Field(min_length=3, max_length=500)
    time_window_days: int = Field(default=7, ge=1, le=365)
    preferred_sources: list[str] = Field(default_factory=list, max_length=10)
    custom_domains: list[str] = Field(default_factory=list, max_length=10)
    broader_web: bool = True
    mode: RunMode = "fixture"

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
    publication_date: str | None = None
    evidence_excerpt: str
    relevance: str
    watch_next: str = "Confirm the next company, market, or policy update."


class SectionResearchResult(BaseModel):
    section_title: str
    candidates: list[NewsCandidate] = Field(default_factory=list, max_length=6)


class ResearchBundle(BaseModel):
    sections: list[SectionResearchResult] = Field(min_length=3, max_length=3)


class BriefingItem(BaseModel):
    headline: str
    what_happened: str
    why_it_matters: str
    watch_next: str
    source: str
    url: str | None = None
    publication_date: str | None = None
    status: Literal["supported", "insufficient_evidence"] = "supported"


class BriefingSection(BaseModel):
    title: str
    purpose: str
    items: list[BriefingItem] = Field(min_length=3, max_length=3)


class AnalystBriefing(BaseModel):
    focus: str
    generated_at: str
    mode: RunMode
    sections: list[BriefingSection] = Field(min_length=3, max_length=3)


class ResearchPreferences(BaseModel):
    preferred_sources: list[str] = Field(default_factory=list)
    excluded_topics: list[str] = Field(default_factory=list)


class EditorialPreferences(BaseModel):
    tone: str = "direct, calm, beginner-friendly"
    lead_with_implication: bool = False
    jargon_level: str = "define unfamiliar terms"


class DisplayPreferences(BaseModel):
    currency_style: str = "USD 4.2 billion"
    date_style: str = "25 Aug 2026"


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
    mode: RunMode = "fixture"
    feedback: str = Field(min_length=3, max_length=1000)
    briefing: AnalystBriefing
    current_preferences: PreferencePatch = Field(default_factory=PreferencePatch)


class ApprovalRequest(BaseModel):
    patch: PreferencePatch

