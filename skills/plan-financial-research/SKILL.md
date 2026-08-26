# Plan financial research

## Owner

Coverage Planner

## Purpose

Turn a broad market focus, research question, and coverage window into exactly three useful sections.

## Inputs

- broad finance topic;
- natural-language question;
- coverage window;
- source directions;
- approved research preferences.

## Output

A `ResearchPlan` with exactly three `SectionPlan` objects. Each section has a plain title, a clear
purpose, and one to three short search queries.

## Method

1. Identify the market decision or understanding the question should support.
2. Choose broad areas likely to have meaningful current coverage.
3. Separate market context, company or deal catalysts, and forward risks where useful.
4. Keep the sections distinct without forcing narrow subtopics.
5. Write short topic queries without dates, months, or source-site filters.
6. Return the plan only. Do not search or draft the briefing.
