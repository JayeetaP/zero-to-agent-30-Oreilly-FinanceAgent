# Architecture

## One local process

FastAPI serves the browser files and a small JSON API. There is no Node process, frontend compiler,
container, database server, or cloud runtime.

```text
Browser (HTML, CSS, JavaScript)
          |
          v
FastAPI at localhost:8000
          |
          +-- recorded real-news Sample Run
          |
          +-- Agno Agent -> local Ollama model
                          -> DDGS public search tool
```

## Visible workflow

```text
BriefRequest
  -> Coverage Planner (3 broad sections)
  -> News Researcher (dated candidates with links)
  -> Briefing Writer (executive summary, sections, sources)
  -> Feedback proposal
  -> human approval
  -> local presentation preferences
```

The business order is fixed. Agentic decisions happen inside planning, evidence selection,
explanation, and feedback classification.

## Typed briefing contract

An `AnalystBriefing` contains an executive summary, sourced takeaways, exactly three sections,
optional upcoming events, and a complete source catalog. Each section may contain up to three
developments. The workflow never creates blank placeholder items.

## Runtime modes

- **Live Briefing:** Agno uses a local Ollama model and free public metasearch.
- **Sample Run:** FastAPI reads `data/sample_run.json`, recorded on August 25, 2026 from real articles.

Both modes return the same Pydantic models.

## Responsibilities

- **Agno:** model calls, structured output, and public search tools.
- **Plain Python:** workflow order, concurrent section research, URL validation, source IDs, and approval.
- **Skills:** agent playbooks stored in Git.
- **Rules:** evidence, document-shape, and writing boundaries.
- **Preferences:** approved presentation choices written to a gitignored JSON file.
