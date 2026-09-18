"""Small server-side authorization boundary for CivicLens v1 operations."""
import hmac
import os
from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, status

@dataclass(frozen=True)
class Principal:
    role: str
    name: str

def _token(role: str) -> str | None:
    return os.getenv(f"CIVICLENS_{role.upper()}_TOKEN")

def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication is required", {"WWW-Authenticate": "Bearer"})
    supplied = authorization.removeprefix("Bearer ")
    for role in ("admin", "operator"):
        configured = _token(role)
        if configured and hmac.compare_digest(supplied, configured):
            return Principal(role=role, name=role)
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication token", {"WWW-Authenticate": "Bearer"})

def require_operator(principal: Principal = Depends(current_principal)) -> Principal:
    if principal.role not in {"operator", "admin"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operator access is required")
    return principal

def require_admin(principal: Principal = Depends(current_principal)) -> Principal:
    if principal.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access is required")
    return principal
