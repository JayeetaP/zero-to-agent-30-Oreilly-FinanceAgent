# Search and ground news

## Owner

News Research Agent

## Purpose

Find recent evidence for one planned section. The workflow reuses this skill across all three sections and may run those searches in parallel.

## Inputs

- one `SectionPlan`;
- time window;
- preferred domains;
- broader-web permission.

## Output

Up to five `NewsCandidate` objects with title, canonical URL, source, publication date, evidence excerpt, and relevance explanation.

## Method

1. Search preferred domains first.
2. Broaden only when the user allows it and evidence is insufficient.
3. Open candidate pages and extract dates, URLs, and supporting excerpts.
4. Group repeated coverage of the same underlying development.
5. Reject candidates without inspectable support.
6. Return evidence, not polished briefing copy.
