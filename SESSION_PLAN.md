# Zero to Agent in 30 Minutes: Local Demo Plan

**Session:** Build a Financial News Agent That Turns Headlines into Analyst Briefings  
**Audience:** Developers who may be new to finance and agents  
**Surface:** Briefing Lab at `http://127.0.0.1:8000`

## Audience takeaway

```text
Define -> plan three sections -> research -> write 3 x 3 -> feedback -> approve memory
```

Attendees should understand:

- **Agent:** owns a decision.
- **Skill:** the reusable playbook it follows.
- **Rule:** a hard boundary code validates.
- **Memory:** an approved preference reused later.

## Run of show

| Time | Segment | What appears in the UI |
|---|---|---|
| 0:00–3:00 | Why this agent | Too much news becomes one focused nine-item briefing. |
| 3:00–6:00 | Define | Focus, question, time window, and source directions. |
| 6:00–9:00 | Planner | Three section titles and purposes. |
| 9:00–14:00 | Researcher | Three searches, candidates, and evidence fields. |
| 14:00–19:00 | Editor | Three sections with three sourced items each. |
| 19:00–24:00 | Feedback | Proposed preference, human approval, visible JSON memory. |
| 24:00–27:00 | Repository | Frontend, backend, one skill, one rule, one test. |
| 27:00–30:00 | Q&A | Questions or a switch from fixture to live mode. |

Open with: “This agent does not predict prices. It helps a person decide what to investigate next.”

## UI walkthrough

1. Select **Sustainable research** and ask: “What material sustainability developments happened
   in the last seven days?”
2. Choose Reuters and SEC/company IR as search directions.
3. Run the Planner and show its three structured sections.
4. Run the Researcher and show the three parallel section tasks and evidence metadata.
5. Run the Editor and inspect one item's event, relevance, next watch point, and source.
6. Give feedback: “Use $4.2bn instead of USD 4.2 billion. Lead with the implication.”
7. Review the typed proposal, approve it, and show the saved preference JSON.

Use fixture mode first. If Ollama and the model are ready, switch to live news to show the same
workflow using current search results.

## Short code tour

Open only:

1. `frontend/app.js` — visible workflow state and four Run buttons.
2. `backend/workflow.py` — fixed orchestration and parallel research.
3. `backend/agents.py` — Agno Agent, Ollama, and web-search components.
4. `skills/search-and-ground-news/SKILL.md` — the Researcher's playbook.
5. `rules/briefing-contract.md` — the deterministic 3 x 3 and evidence boundary.

## Before the session

```bash
source .venv/bin/activate
python -m pytest -q
python -m backend.app
```

- Confirm fixture mode works without Ollama.
- Optionally cache one successful live run.
- Keep the browser at 90–100% zoom.
- Delete `data/memory.local.json` if you want a clean feedback demo.
- Use **Run full briefing** if time is short.

End with: “A useful agent system makes its work understandable: what it was asked, which agent
acted, what evidence it used, what it produced, and what it learned—with permission—from the human.”
