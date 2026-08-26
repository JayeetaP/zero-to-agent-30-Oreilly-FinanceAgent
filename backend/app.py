from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import APP_HOST, APP_PORT, FRONTEND_DIR, OLLAMA_HOST, OLLAMA_MODEL
from .models import (
    ApprovalRequest,
    BriefRequest,
    EditorRequest,
    FeedbackRequest,
    ResearchRequest,
)
from .workflow import (
    LiveModeUnavailable,
    approve_memory,
    create_plan,
    edit_briefing,
    load_memory,
    ollama_status,
    propose_preferences,
    research_sections,
)


app = FastAPI(
    title="Briefing Lab API",
    description="A small local API for the financial-news agent teaching demo.",
    version="1.0.0",
)


def _result(value, trace: list[str]) -> dict:
    return {"result": value.model_dump(mode="json"), "trace": trace}


def _live_error(error: LiveModeUnavailable) -> HTTPException:
    return HTTPException(status_code=503, detail=str(error))


@app.get("/api/health")
async def health() -> dict:
    model_status = await ollama_status()
    return {
        "status": "ok",
        "model_provider": "Ollama",
        "search_provider": "DDGS public metasearch",
        "ollama_host": OLLAMA_HOST,
        "configured_model": OLLAMA_MODEL,
        **model_status,
    }


@app.post("/api/plan")
async def plan(request: BriefRequest) -> dict:
    try:
        result, trace = await create_plan(request)
        return _result(result, trace)
    except LiveModeUnavailable as error:
        raise _live_error(error) from error


@app.post("/api/research")
async def research(payload: ResearchRequest) -> dict:
    try:
        result, trace = await research_sections(payload.request, payload.plan)
        return _result(result, trace)
    except LiveModeUnavailable as error:
        raise _live_error(error) from error


@app.post("/api/edit")
async def edit(payload: EditorRequest) -> dict:
    try:
        result, trace = await edit_briefing(payload.request, payload.plan, payload.research)
        return _result(result, trace)
    except LiveModeUnavailable as error:
        raise _live_error(error) from error


@app.post("/api/feedback")
async def feedback(payload: FeedbackRequest) -> dict:
    try:
        result, trace = await propose_preferences(
            payload.mode,
            payload.feedback,
            payload.briefing,
            payload.current_preferences,
        )
        return _result(result, trace)
    except LiveModeUnavailable as error:
        raise _live_error(error) from error


@app.get("/api/memory")
async def memory() -> dict:
    return load_memory()


@app.post("/api/memory/approve")
async def approve(payload: ApprovalRequest) -> dict:
    return approve_memory(payload.patch)


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
