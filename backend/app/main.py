from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.incidents import router as incident_router
from app.api.reports import router as report_router

app = FastAPI()

app.include_router(health_router)
app.include_router(incident_router)
app.include_router(report_router)
