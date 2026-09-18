"""Unit coverage for conservative, data-driven internal routing."""
from app.enums.incident import AuthorityType
from app.models.operations import Authority, RoutingDecision
from app.schemas.location import CivicContext, LocationContext
from app.services.routing import RoutingService

class Query:
    def __init__(self, values): self.values = values
    def filter(self, *args): return self
    def all(self): return self.values
    def first(self): return self.values[0] if self.values else None

class DB:
    def __init__(self, authorities): self.authorities, self.decisions = authorities, []
    def query(self, model): return Query(self.authorities if model is Authority else self.decisions)
    def add(self, value): self.decisions.append(value)

def authority(id, kind, key=None):
    return Authority(id=id, name=kind.value, authority_type=kind, jurisdiction="test", routing_key=key, active=True)

def test_campus_route_persists_configured_private_authority():
    campus = authority(1, AuthorityType.CAMPUS_PRIVATE)
    db = DB([campus])
    decision = RoutingService().resolve(db, 10, LocationContext(latitude=12.9, longitude=80.2, civic_context=CivicContext.CAMPUS))
    assert decision.authority_id == 1
    assert decision.confidence == "high"
    assert decision.manual_review_required is False
    assert db.decisions == [decision]

def test_unknown_route_requires_manual_review_when_evidence_is_insufficient():
    unknown = authority(2, AuthorityType.UNKNOWN)
    db = DB([unknown])
    decision = RoutingService().resolve(db, 10, LocationContext(latitude=12.9, longitude=80.2))
    assert decision.authority_id == 2
    assert decision.source == "manual_review"
    assert decision.confidence == "low"
    assert decision.manual_review_required is True
