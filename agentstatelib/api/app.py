from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from agentstatelib.api.dashboard import DASHBOARD_HTML
from agentstatelib.memory.store import SQLiteStore


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
        version="0.2.0",
        description="Self-hosted coordination layer for parallel multi-agent AI systems",
    )

    app.state.store = SQLiteStore(db_path)
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


app = create_app()
