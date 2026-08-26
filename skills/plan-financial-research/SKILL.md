# Plan financial research

## Owner

Planner Agent

## Purpose

Convert an analyst focus, a news question, a time window, and approved research preferences into exactly three beginner-friendly research sections.

## Inputs

- focus area;
- natural-language question;
- time window;
- source directions;
- approved research preferences.

## Output

A `ResearchPlan` with exactly three `SectionPlan` objects. Each section has a title, purpose, and one to three search queries.

## Method

1. Identify the decision context in the user's question.
2. Separate company/deal evidence from broader market or policy context.
3. Choose three sections that overlap as little as possible.
4. Write plain titles a finance newcomer can understand.
5. Return structured output; do not search the web or draft the briefing.
