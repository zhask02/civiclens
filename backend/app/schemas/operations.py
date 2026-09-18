from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.incident import IncidentResponse

class AssignmentCreate(BaseModel):
    assigned_to: str = Field(min_length=1, max_length=120)
class NoteCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
class AssignmentResponse(BaseModel):
    id:int; incident_id:int; assigned_to:str; assigned_by:str; created_at:datetime
    model_config={"from_attributes":True}
class NoteResponse(BaseModel):
    id:int; incident_id:int; author:str; content:str; created_at:datetime
    model_config={"from_attributes":True}
class HistoryResponse(BaseModel):
    id:int; incident_id:int; previous_status:str; new_status:str; actor:str; source:str; created_at:datetime
    model_config={"from_attributes":True}
class RoutingResponse(BaseModel):
    incident_id:int; authority_id:int|None; jurisdiction:str; source:str; reason:str; confidence:str; manual_review_required:bool; created_at:datetime
    model_config={"from_attributes":True}

class OperatorIncidentResponse(BaseModel):
    incident: IncidentResponse
    routing: RoutingResponse | None = None
    assignment: AssignmentResponse | None = None
