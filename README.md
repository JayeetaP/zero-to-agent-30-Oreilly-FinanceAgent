# Briefing Lab

Briefing Lab is a small financial-news agent demo that runs on your computer. It shows how a planner,
researcher, writer, and feedback agent turn current public news into a cited briefing document.

The project is designed as a clear workshop example for financial analysts and can be customized for any domain:

- one Python process serves the API and browser UI;
- plain HTML, CSS, and JavaScript with no frontend build;
- four Agno agent roles with readable skills and shared rules;
- a local open model through Ollama, with no paid model API key;
- current-news discovery through public DDGS metasearch;
- a dated Sample Run made from real public articles;
- human approval before versioned preferences are saved in Agno memory.

There is no React, Node server, Docker, database server, `.openai` folder, Wrangler, or Vinext setup.
Agno stores local memory in one gitignored SQLite file.

## What the demo teaches

```text
Question and source preferences
        |
        v
Coverage Planner       chooses three broad sections
        |
        v
News Researcher        searches, checks dates and URLs, removes duplicates
        |
        v
Briefing Writer        creates the executive summary and sourced briefing
        |
        v
Feedback Agent         proposes tone and display preferences for approval
        |
        v
Agno Memory            versions approved preferences and shares the active version
```

The UI makes every stage runnable on its own and displays the structured handoff between stages. The
activity stream labels agent starts, memory reads, model and tool calls, queued search queries,
validation, results, and elapsed time. It shows operational telemetry, not private model reasoning.

## Repository structure

```text
briefing-lab/
├── backend/                  # FastAPI endpoints, Agno agents, workflow, schemas
├── frontend/                 # plain index.html, styles.css, app.js
├── skills/                   # one readable playbook for each agent role
├── rules/                    # evidence, briefing, and editorial contracts
├── data/sample_run.json      # real, dated, sourced workshop fallback
├── data/memory.db            # local Agno memory, created at runtime and ignored by Git
├── memory/                   # default presentation preferences
├── docs/architecture.md      # short technical architecture reference
├── tests/                    # evidence and workflow contract tests
├── requirements.txt
└── .env.example
```

## Quick start

Prerequisites:

- [Python 3.11 or newer](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads)

Clone and run:

```bash
git clone https://github.com/JayeetaP/zero-to-agent-30-Oreilly-FinanceAgent.git
cd zero-to-agent-30-Oreilly-FinanceAgent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m backend.app
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Select **Sample Run** to use the recorded Global Markets briefing immediately. The sample was captured
on August 25, 2026 and contains real article titles, publication dates, and source links. It does not
call a model or the internet.

## Enable live AI and current news

Install [Ollama](https://ollama.com/download), then download the default
[Qwen 3.5 9B model](https://ollama.com/library/qwen3.5):

```bash
ollama pull qwen3.5:9b
```

Start Ollama if it is not already running:

```bash
ollama serve
```

The Ollama desktop application may already provide the local server. Do not start a second server if
the application is running.

Optional configuration:

```bash
cp .env.example .env
```

Change `OLLAMA_MODEL` in `.env` if you want to use another installed local model. Restart the Python
server after changing the configuration. Live mode can take several minutes on a laptop because the
planner and writer run locally.

No OpenAI API key or paid search key is required. Agno 3.0 loads an OpenAI-compatible response adapter
when its Ollama integration is imported, which is why the `openai` compatibility package appears in
`requirements.txt`. This application does not create an OpenAI client or send requests to OpenAI.

## Briefing output

Every briefing contains:

- an executive summary with source references;
- three to five sourced takeaways;
- exactly three broad briefing sections;
- up to three supported developments in each section;
- upcoming events when the collected evidence supports them;
- a source appendix with publisher, publication date, and direct link.

The workflow does not invent blank stories to fill a quota. When coverage is thin, the document shows
one coverage note instead.

## Agent skills, rules, and memory

Each agent has a Markdown skill in `skills/`. Shared constraints live in `rules/`. The backend loads
these files at runtime, so workshop participants can change agent behavior without rewriting Python.

Feedback follows a human approval boundary and uses Agno's native memory components:

1. The Feedback Agent proposes a preference patch.
2. The UI shows each proposed value beside the current value.
3. Nothing is saved until the user approves it.
4. The user chooses whether to add the proposal to cumulative active memory or save it as a separate inactive snapshot.
5. Agno `MemoryManager` writes the append-only approved version to `data/memory.db`.
6. The UI shows each version's new changes and its complete cumulative snapshot, plus a control to restore an earlier snapshot.

The Planner and Researcher use source and exclusion preferences. The Writer uses tone, implication
order, and jargon preferences. The browser renderer applies currency and date formatting. Memory may
change presentation and coverage direction, but it cannot change source evidence.

## API

```text
POST /api/plan
POST /api/research
POST /api/edit
POST /api/feedback
POST /api/memory/approve
POST /api/memory/activate
GET  /api/memory
GET  /api/health
```

FastAPI generates interactive documentation at
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Run the tests

```bash
python -m pytest -q
```

The tests cover the live-first UI, real Sample Run, source links, publication dates, citation IDs,
writing rules, and approval boundary.

## Tools used

| Tool | Role in this project |
| --- | --- |
| [Python](https://www.python.org/) | Application runtime |
| [Agno](https://docs.agno.com/) | Agent roles, local model integration, tools, structured responses, and memory |
| [Agno Memory](https://docs.agno.com/memory/overview) | `MemoryManager`, `UserMemory`, and shared user memory concepts |
| [Agno Memory Cookbooks](https://github.com/agno-agi/agno/tree/main/cookbook/11_memory) | Persistent and shared-memory implementation examples |
| [Agno Ollama tool-use example](https://docs.agno.com/examples/models/ollama/chat/tool-use) | Reference pattern for an Agno agent using Ollama and `WebSearchTools` |
| [Ollama](https://ollama.com/) | Runs the language model locally |
| [Qwen 3.5](https://ollama.com/library/qwen3.5) | Default open model family |
| [DDGS](https://pypi.org/project/ddgs/) | Public web and news metasearch used by Agno `WebSearchTools` |
| [FastAPI](https://fastapi.tiangolo.com/) | Local API and static-file server |
| [Pydantic](https://docs.pydantic.dev/latest/) | Request, agent handoff, and briefing validation |
| [Uvicorn](https://www.uvicorn.org/) | Local ASGI server |
| [HTTPX](https://www.python-httpx.org/) | Ollama health checks and API testing |
| [python-dotenv](https://saurabh-kumar.com/python-dotenv/) | Optional local environment configuration |
| [SQLAlchemy](https://www.sqlalchemy.org/) | Local SQLite persistence used by Agno memory |
| [pytest](https://docs.pytest.org/en/stable/) | Automated workflow and evidence-contract tests |
| [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web) | HTML, CSS, and browser JavaScript reference |

## Evidence boundaries

- A live article must have an absolute URL, title, excerpt, and publication date before it can appear.
- Preferred publications guide ranking. They are not automatic endorsements.
- A local model does not know current news without the search stage.
- Search snippets and paywalled pages can provide limited evidence.
- The briefing explains collected evidence. It does not predict prices or recommend trades.
