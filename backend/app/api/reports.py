from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import get_pothole_model_path
from app.db.dependencies import get_db
from app.schemas.report import ReportResponse
from app.services.analysis import AnalysisService
from app.services.pothole_detector import PotholeDetector
from app.services.report import ReportService, ReportValidationError

router = APIRouter(tags=["reports"])


@router.post("/reports", response_model=ReportResponse, status_code=201)
def submit_report(
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Submit one citizen pothole report and return its completed assessment."""
    service = ReportService(
        AnalysisService(detector=PotholeDetector(get_pothole_model_path()))
    )
    try:
        return service.submit(
            db=db,
            description=description,
            latitude=latitude,
            longitude=longitude,
            file_bytes=photo.file.read(),
            content_type=photo.content_type,
            filename=photo.filename,
        )
    except (ReportValidationError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        # V1 rejects reports that cannot be confirmed as potholes.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to submit report")
