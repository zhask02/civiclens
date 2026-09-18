"""Conservative, data-driven internal authority routing."""
from app.enums.incident import AuthorityType
from app.models.operations import Authority, RoutingDecision
from app.schemas.location import CivicContext, LocationContext

class RoutingService:
    def resolve(self, db, incident_id: int, context: LocationContext) -> RoutingDecision:
        """Create the current conservative internal routing decision."""
        authorities = db.query(Authority).filter(Authority.active == True).all()
        road = (context.osm_road or "").casefold()
        match = next((a for a in authorities if a.routing_key and a.routing_key.casefold() in road), None)
        if context.civic_context == CivicContext.CAMPUS:
            match = next((a for a in authorities if a.authority_type == AuthorityType.CAMPUS_PRIVATE), None)
            if match:
                return self._persist(db, self._decision(incident_id, match, "campus_context", "Campus location context matched the configured facilities authority.", "high", False))
        if match:
            return self._persist(db, self._decision(incident_id, match, "configured_road_match", "Configured authority routing key matched OSM road evidence.", "medium", False))
        unknown = next((a for a in authorities if a.authority_type == AuthorityType.UNKNOWN), None)
        return self._persist(db, self._decision(incident_id, unknown, "manual_review", "Available location evidence does not establish road ownership.", "low", True))

    @staticmethod
    def _persist(db, decision: RoutingDecision) -> RoutingDecision:
        # v1 has one current decision: reruns update it rather than retaining
        # conflicting automated recommendations.
        existing = db.query(RoutingDecision).filter(
            RoutingDecision.incident_id == decision.incident_id
        ).first()
        if existing is not None:
            for field in ("authority_id", "jurisdiction", "source", "reason", "confidence", "manual_review_required"):
                setattr(existing, field, getattr(decision, field))
            return existing
        db.add(decision)
        return decision

    @staticmethod
    def _decision(incident_id, authority, source, reason, confidence, manual):
        return RoutingDecision(incident_id=incident_id, authority_id=authority.id if authority else None, jurisdiction=authority.jurisdiction if authority else "unknown", source=source, reason=reason, confidence=confidence, manual_review_required=manual)
