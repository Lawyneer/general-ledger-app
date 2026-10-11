from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.staticfiles import StaticFiles

from .routes import accounts_router, journal_router, statements_router
from .database import init_db

init_db()

STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(title="Ledger")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(accounts_router, prefix="/api/v1")
app.include_router(journal_router, prefix="/api/v1")
app.include_router(statements_router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)