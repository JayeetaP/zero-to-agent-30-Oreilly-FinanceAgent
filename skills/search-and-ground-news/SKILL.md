# Search and ground news

## Owner

News Researcher

## Purpose

Evaluate current evidence for one planned section. The workflow runs the three sections independently.

## Inputs

- one `SectionPlan`;
- public search results from a short query ladder;
- coverage window;
- preferred domains;
- permission to include other public sources.

## Output

Up to eight `NewsCandidate` objects with a headline, source, absolute URL, publication date, evidence
excerpt, relevance explanation, and next watch point.

## Method

1. Use only results supplied by the workflow's Agno search tool.
2. Rank preferred domains first without treating them as automatic endorsements.
3. Exclude results without a publication date or working absolute URL.
4. Group repeated coverage of the same underlying event.
5. Copy source metadata exactly and explain relevance in plain language.
6. Return evidence records, not briefing prose.
