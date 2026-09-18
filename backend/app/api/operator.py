from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth import Principal, require_operator
from app.db.dependencies import get_db
from app.models.incident import Incident
from app.models.evidence import IncidentEvidence
from app.models.operations import IncidentAssignment, OperatorNote, IncidentStatusHistory, RoutingDecision
from app.schemas.operations import AssignmentCreate, AssignmentResponse, NoteCreate, NoteResponse, HistoryResponse, RoutingResponse, OperatorEvidenceResponse, OperatorIncidentResponse
from app.services.storage import create_evidence_signed_url
from app.services.rate_limit import limit_operator_request

# This router contains the currently exposed operator API. The limiter depends
# on authentication so each validated principal has an independent quota.
router=APIRouter(prefix="/operator",tags=["operator"],dependencies=[Depends(limit_operator_request)])
def incident_or_404(db,id):
    item=db.get(Incident,id)
    if not item: raise HTTPException(404,"Incident not found")
    return item
@router.get("/incidents",response_model=list[OperatorIncidentResponse])
def queue(status:str|None=None, severity:str|None=None, review_required:bool|None=None, db:Session=Depends(get_db)):
    q=db.query(Incident)
    if status: q=q.filter(Incident.status==status)
    if severity: q=q.filter(Incident.severity==severity)
    rows = [_operator_response(db, item) for item in q.order_by(Incident.created_at.desc()).all()]
    return [row for row in rows if review_required is None or (row.routing and row.routing.manual_review_required) == review_required]

def _operator_response(db, incident):
    return OperatorIncidentResponse(
        incident=incident,
        routing=db.query(RoutingDecision).filter(RoutingDecision.incident_id == incident.id).first(),
        assignment=db.query(IncidentAssignment).filter(IncidentAssignment.incident_id == incident.id).first(),
    )


@router.get("/incidents/{incident_id}/evidence", response_model=OperatorEvidenceResponse)
def latest_evidence(incident_id: int, db: Session = Depends(get_db)):
    """Issue an operator-authorized, time-limited URL for the latest image."""

    incident_or_404(db, incident_id)
    evidence = (
        db.query(IncidentEvidence)
        .filter(IncidentEvidence.incident_id == incident_id)
        .order_by(IncidentEvidence.created_at.desc())
        .first()
    )
    if evidence is None:
        return OperatorEvidenceResponse()

    # The browser receives only a short-lived URL after the router's existing
    # operator/admin dependency has authorized this request; storage secrets
    # and private object paths remain server-side.
    return OperatorEvidenceResponse(
        url=create_evidence_signed_url(evidence.storage_path),
    )

@router.get("/incidents/{incident_id}", response_model=OperatorIncidentResponse)
def detail(incident_id:int,db:Session=Depends(get_db)):
    return _operator_response(db, incident_or_404(db, incident_id))
@router.post("/incidents/{incident_id}/assignment",response_model=AssignmentResponse)
def assign(incident_id:int,payload:AssignmentCreate,principal:Principal=Depends(require_operator),db:Session=Depends(get_db)):
    incident_or_404(db,incident_id)
    row=db.query(IncidentAssignment).filter(IncidentAssignment.incident_id==incident_id).first()
    if row: row.assigned_to=payload.assigned_to; row.assigned_by=principal.name
    else: row=IncidentAssignment(incident_id=incident_id,assigned_to=payload.assigned_to,assigned_by=principal.name); db.add(row)
    db.commit(); db.refresh(row); return row
@router.post("/incidents/{incident_id}/notes",response_model=NoteResponse)
def note(incident_id:int,payload:NoteCreate,principal:Principal=Depends(require_operator),db:Session=Depends(get_db)):
    incident_or_404(db,incident_id); row=OperatorNote(incident_id=incident_id,author=principal.name,content=payload.content); db.add(row); db.commit(); db.refresh(row); return row
@router.get("/incidents/{incident_id}/history",response_model=list[HistoryResponse])
def history(incident_id:int,db:Session=Depends(get_db)):
    incident_or_404(db,incident_id); return db.query(IncidentStatusHistory).filter(IncidentStatusHistory.incident_id==incident_id).order_by(IncidentStatusHistory.created_at).all()
@router.get("/incidents/{incident_id}/routing",response_model=RoutingResponse|None)
def routing(incident_id:int,db:Session=Depends(get_db)):
    incident_or_404(db,incident_id); return db.query(RoutingDecision).filter(RoutingDecision.incident_id==incident_id).first()
