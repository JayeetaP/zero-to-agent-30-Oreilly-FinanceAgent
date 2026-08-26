# Briefing Lab

A deliberately small financial-news agent demo:

- one FastAPI process serves the UI and backend;
- plain HTML, CSS, and JavaScript—no Node or frontend build;
- four Agno agents with readable skills;
- a local open model through Ollama;
- current-news search through DDGS public metasearch;
- fixture mode that works without Ollama or internet;
- human-approved local memory stored as JSON.

## Repository

```text
briefing-lab/
├── backend/                  # FastAPI endpoints and Agno agents
│   ├── app.py                # one local server
│   ├── agents.py             # Agno Agent + Ollama + WebSearchTools
│   ├── workflow.py           # visible plan → research → edit flow
│   ├── models.py             # Pydantic contracts
│   └── skills.py             # loads the SKILL.md files
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── skills/                   # one playbook per agent
├── rules/                    # deterministic evidence and output rules
├── data/news_fixture.json    # reliable workshop fallback
├── memory/                   # default preference schema
├── tests/
├── requirements.txt
└── .env.example
```

There is intentionally no `package.json`, `.openai`, Wrangler, Vinext, React, Docker, or database server.

## Run the fixture demo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Fixture mode works immediately.

## Enable live news with no paid API key

Ollama is the only extra local service:

```bash
ollama pull qwen3.5:9b
ollama serve
```

If the Ollama desktop app is already running, do not run `ollama serve` separately. Select **Live news** in the UI. The backend then uses:

```python
Agent(
    model=Ollama(id="qwen3.5:9b"),
    tools=[WebSearchTools(backend="auto", enable_news=True)],
)
```

The model runs locally. Free public metasearch supplies current URLs. The code rejects invalid and duplicate URLs before the Editor sees them.

Optional configuration:

```bash
cp .env.example .env
```

No secret is required. Change `OLLAMA_MODEL` if a different local model fits your machine better.

One dependency named `openai` appears in `requirements.txt` because Agno 3.0 imports its
OpenAI-compatible response adapter while loading the Ollama package. This application never
creates an OpenAI client, sends a request to OpenAI, or reads an OpenAI API key.

## API

The teaching UI calls four small endpoints:

```text
POST /api/plan
POST /api/research
POST /api/edit
POST /api/feedback
```

Memory approval is separate:

```text
POST /api/memory/approve
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the generated API documentation.

## Tests

```bash
python -m pytest -q
```

The tests run entirely in fixture mode. They validate the one-server setup, the three-section plan, the three-by-three briefing, and the approval boundary around memory.

## Boundaries

- A preferred source is a search direction, not an endorsement.
- A local model does not know current news without the search tool.
- Public search may expose only a headline or snippet for paywalled sources.
- Live mode shows insufficient evidence instead of inventing an item.
- The briefing is educational research, not a trade recommendation.
