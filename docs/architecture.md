# Architecture

## One local process

FastAPI serves both the plain browser files and a small JSON API. There is no Node process,
frontend compiler, container, database server, or cloud hosting runtime.

```text
Browser (HTML/CSS/JS)
          |
          v
FastAPI at localhost:8000
          |
          +-- fixture JSON
          |
          +-- Agno Agent -> local Ollama model
                          -> DDGS public search tool
```

## Why a workflow, not a free-form team

The order is known: plan, research, edit, then learn from feedback. A fixed workflow makes every
handoff visible to newcomers. Agentic decisions happen inside each step, where the local model
interprets the user, creates queries, evaluates evidence, synthesizes, or translates feedback.

## Typed contracts

```text
BriefRequest
  focus, question, time window, source directions
      -> ResearchPlan (exactly 3 sections)
      -> ResearchBundle (up to 6 candidates per section)
      -> AnalystBriefing (exactly 3 sections x 3 items)
      -> PreferencePatch
      -> human approval
      -> data/memory.local.json
```

The UI displays actions, state changes, counts, structured results, and errors. It does not expose
private chain-of-thought.

## Runtime modes

- **Fixture:** reads `data/news_fixture.json`; no network or model required.
- **Live:** Agno uses a local Ollama model; its `WebSearchTools` uses free public metasearch. The three
  section-research jobs run concurrently with ordinary `asyncio`.

Both modes return the same Pydantic models, so the UI does not need a second implementation.

## Responsibility boundaries

- **Agno:** model calls, structured outputs, and web-search tools.
- **Plain Python:** predictable workflow order, concurrency, URL checks, 3 x 3 enforcement, and
  memory approval.
- **Skills:** agent playbooks stored in Git.
- **Rules:** hard evidence and output boundaries.
- **Memory:** approved preferences written atomically to a gitignored JSON file.
