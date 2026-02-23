"""
DTO models — describe what crosses the HTTP boundary (request and response bodies).
These are shaped around the FastAPI contract, not the AI layer.
"""

from pydantic import BaseModel, Field


# ── Requests ──────────────────────────────────────────────────────────────────

class IdeasRequest(BaseModel):
    tech_stack: str
    domain: str | None = None
    level: str | None = None
    enable_multi_query: bool = False
    count: int = Field(default=3, ge=1, le=5)


class ExpandRequest(BaseModel):
    run_id: str = Field(..., description="Run ID from POST /ideas response")
    pid: int = Field(..., ge=1, description="ID of the idea to expand (1-based from that run)")


class ExportRequest(BaseModel):
    run_id: str = Field(..., description="Run ID from POST /ideas response")
    pid: int = Field(..., ge=1, description="ID of the expanded idea to export (must have been expanded first)")
