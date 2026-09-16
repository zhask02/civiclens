from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.incidents import router as incident_router
from app.api.reports import router as report_router

app = FastAPI()

# The local Vite origin is explicitly allowed so the separate citizen web app
# can call the FastAPI API in development. Production origins belong in the
# deployment configuration before public release.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(incident_router)
app.include_router(report_router)
