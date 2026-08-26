# Financial News Briefing Agent: Simple Build Plan

**Status:** Local fixture and live-news paths implemented  
**Audience:** Developers who are new to finance and agents  
**Stack:** Plain HTML/CSS/JavaScript + FastAPI + Agno + Ollama + DDGS public search

## Goal

A user chooses an analyst focus, asks a news question, and gives preferred source directions.
Four understandable agents create exactly three sections with three relevant news items in each.
Feedback becomes a proposed preference and affects future briefings only after human approval.

The application helps an analyst decide what to investigate. It does not recommend trades or
assume that a preferred source is automatically correct.

## One visible workflow

```text
Focus + question + preferred sources
                  |
                  v
          1. Planner Agent
        exactly three sections
                  |
                  v
       2. News Research Agent
  three section searches in parallel
                  |
                  v
       3. Briefing Editor Agent
   exactly three items per section
                  |
                  v
             Final briefing

Feedback -> 4. Feedback & Memory Agent
         -> proposed typed preference
         -> human approval
         -> saved for the next run
```

The order is fixed because the business process is known. The agents remain agentic inside each
step: they interpret the request, design research sections, find evidence, select items, explain
relevance, and translate feedback.

## Four agents

| Agent | Decision it owns | Skill |
|---|---|---|
| Planner | Which three research sections best fit the request? | `plan-financial-research` |
| News Research | Which recent, supported developments belong in each section? | `search-and-ground-news` |
| Briefing Editor | Which three items should be included and how should they be explained? | `write-three-section-briefing` |
| Feedback & Memory | Which durable preference is the user asking to reuse? | `learn-briefing-preferences` |

Skills are version-controlled playbooks. Rules are code-validated boundaries. Runtime memory is
user-approved JSON and never rewrites a skill.

## Repository structure

```text
briefing-lab/
├── backend/                   # FastAPI API, Agno agents, workflow, schemas
├── frontend/                  # plain index.html, styles.css, app.js
├── skills/                    # one readable playbook per agent
├── rules/                     # evidence and output contracts
├── data/news_fixture.json     # reliable no-network demo
├── memory/                    # defaults; approved local memory is gitignored
├── tests/                     # fixture workflow and memory tests
├── requirements.txt
└── README.md
```

There is one server and no frontend build step. Run `python -m backend.app`, then open
`http://127.0.0.1:8000`.

## Runtime modes

- **Fixture:** no model, key, or network; ideal for a reliable workshop.
- **Live news:** Agno agents use a local Ollama model and DDGS public web search. No paid API key.

Both modes return the same Pydantic-validated JSON shapes.

## Definition of done

1. One command serves both UI and API.
2. Planner always returns three sections.
3. Live research exposes publisher, URL, date, excerpt, relevance, and next watch point.
4. Editor returns three items per section or explicit insufficient-evidence slots.
5. Feedback cannot persist before approval.
6. A new user can run fixture mode from the README in under five minutes.
