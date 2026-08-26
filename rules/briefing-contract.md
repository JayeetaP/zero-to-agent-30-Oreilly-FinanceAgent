# Briefing contract

These checks sit around the agents:

1. A research plan contains exactly three broad sections.
2. A briefing contains an executive summary and three to five sourced takeaways.
3. A briefing contains exactly three sections.
4. Each section contains zero to three supported developments. Empty slots are never rendered.
5. Every displayed development cites at least one source ID.
6. Every source record has a publisher, title, publication date, and absolute URL.
7. Unsupported source IDs are removed before the response reaches the UI.
8. A thin section gets one coverage note instead of invented content.
9. Currency and date preferences are applied after factual generation.
10. A preference cannot be saved without an explicit human approval event.
