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
          |
          +-- Agno MemoryManager -> local SQLite file
```

## Visible workflow

```text
BriefRequest
  -> Coverage Planner (3 broad sections)
  -> News Researcher (dated candidates with links)
  -> Briefing Writer (executive summary, sections, sources)
  -> Feedback proposal
  -> human approval
  -> versioned Agno user memory
  -> active preferences shared with the next run
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
- **MemoryManager and UserMemory:** approved preference versions stored through Agno.
- **SQLite:** one gitignored local file, with no separate database server.

## Memory boundary

The application does not enable automatic or agentic memory updates. The Feedback Agent returns a
typed proposal, the user approves it, and only then does `MemoryManager` save a new version. One stable
record points to the active cumulative version and append-only records preserve the approval history.
Approval can merge a proposal into active memory or save it separately without changing the active
record. Each history entry retains both its delta and its complete snapshot. Research,
editorial, and display preferences feed the relevant stages, but source validation remains code-owned.
