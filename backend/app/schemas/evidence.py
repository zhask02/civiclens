from datetime import datetime

from pydantic import BaseModel


class EvidenceCreate(BaseModel):
    file_url: str
    file_type: str


class EvidenceResponse(BaseModel):
    id: int
    incident_id: int
    file_url: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True