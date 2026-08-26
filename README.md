# Briefing Lab

Briefing Lab is a small financial-news agent demo that runs on your computer. It shows how a planner,
researcher, writer, and feedback agent turn current public news into a cited briefing document.

The project is designed for workshops and first-time agent builders:

- one Python process serves the API and browser UI;
- plain HTML, CSS, and JavaScript with no frontend build;
- four Agno agent roles with readable skills and shared rules;
- a local open model through Ollama, with no paid model API key;
- current-news discovery through public DDGS metasearch;
- a dated Sample Run made from real public articles;
- human approval before presentation preferences are saved.

There is no React, Node server, Docker, database, `.openai` folder, Wrangler, or Vinext setup.

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
```

The UI makes every stage runnable on its own and displays the structured handoff between stages. It
shows actions and results, not private model reasoning.

## Repository structure

```text
briefing-lab/
├── backend/                  # FastAPI endpoints, Agno agents, workflow, schemas
├── frontend/                 # plain index.html, styles.css, app.js
├── skills/                   # one readable playbook for each agent role
├── rules/                    # evidence, briefing, and editorial contracts
├── data/sample_run.json      # real, dated, sourced workshop fallback
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

Feedback follows a human approval boundary:

1. The Feedback Agent proposes a preference patch.
2. The UI shows the proposed tone, currency, date, and source changes.
3. Nothing is saved until the user approves it.
4. Approved preferences are written to ignored local file `data/memory.local.json`.

## API

```text
POST /api/plan
POST /api/research
POST /api/edit
POST /api/feedback
POST /api/memory/approve
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
| [Agno](https://docs.agno.com/) | Agent roles, local model integration, tools, and structured responses |
| [Agno Ollama tool-use example](https://docs.agno.com/examples/models/ollama/chat/tool-use) | Reference pattern for an Agno agent using Ollama and `WebSearchTools` |
| [Ollama](https://ollama.com/) | Runs the language model locally |
| [Qwen 3.5](https://ollama.com/library/qwen3.5) | Default open model family |
| [DDGS](https://pypi.org/project/ddgs/) | Public web and news metasearch used by Agno `WebSearchTools` |
| [FastAPI](https://fastapi.tiangolo.com/) | Local API and static-file server |
| [Pydantic](https://docs.pydantic.dev/latest/) | Request, agent handoff, and briefing validation |
| [Uvicorn](https://www.uvicorn.org/) | Local ASGI server |
| [HTTPX](https://www.python-httpx.org/) | Ollama health checks and API testing |
| [python-dotenv](https://saurabh-kumar.com/python-dotenv/) | Optional local environment configuration |
| [pytest](https://docs.pytest.org/en/stable/) | Automated workflow and evidence-contract tests |
| [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web) | HTML, CSS, and browser JavaScript reference |

## Evidence boundaries

- A live article must have an absolute URL, title, excerpt, and publication date before it can appear.
- Preferred publications guide ranking. They are not automatic endorsements.
- A local model does not know current news without the search stage.
- Search snippets and paywalled pages can provide limited evidence.
- The briefing explains collected evidence. It does not predict prices or recommend trades.
