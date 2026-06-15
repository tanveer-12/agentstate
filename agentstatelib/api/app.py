from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from agentstatelib.api.dashboard import DASHBOARD_HTML
from agentstatelib.memory.store import SQLiteStore
from agentstatelib.router.graph import AgentGraph


def create_app(db_path: str = "agentstatelib.db") -> FastAPI:
    """
    Create and configure the agentstatelib FastAPI application.

    Pass a custom db_path using pytest's tmp_path fixture in tests
    to get an isolated database per test.

    The server uses self-configured API keys via the
    AGENTSTATE_API_KEYS environment variable — there is no central
    key registry.
    """
    app = FastAPI(
        title="agentstatelib API",
        version="0.5.0",
        description="Self-hosted coordination layer for parallel multi-agent AI systems",
    )

    store = SQLiteStore(db_path)
    app.state.store = store
    # Shared graph instance so the approval endpoints can call resume_from_approval.
    # Callers that run their own AgentGraph should replace app.state.graph after
    # create_app() returns if they need the approval endpoints to reflect their run.
    app.state.graph = AgentGraph(store=store)

    from agentstatelib.api.routes import router

    app.include_router(router, prefix="/v1")

    @app.get(
        "/dashboard",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(content=DASHBOARD_HTML)

    return app


# Module-level instance for: uvicorn agentstatelib.api.app:app
app = create_app()
