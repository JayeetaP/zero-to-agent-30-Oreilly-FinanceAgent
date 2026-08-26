# Briefing contract

These are deterministic checks around the agents:

1. A research plan contains exactly three sections.
2. A final briefing contains exactly three sections.
3. Each final section contains exactly three items.
4. Every item includes a headline, what happened, why it matters, what to watch, a source label, and a URL.
5. Empty or unsupported slots become `insufficient evidence`; they are never filled with invented material.
6. Currency, date, and percentage display preferences are applied by formatters after content generation.
7. A preference patch cannot become memory without an explicit human approval event.
