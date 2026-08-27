from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_case_access
from app.db.models.base_models import User
from app.db.session import get_db
from app.storage.search_index import search_log_events

router = APIRouter(prefix="/api/cases", tags=["search"])


class SearchResponse(BaseModel):
    total: int
    events: list[dict]


@router.get("/{case_id}/search", response_model=SearchResponse)
async def search_events(
    case_id: str,
    query: str | None = Query(None, description="Free-text search query"),
    source_type: str | None = Query(None, description="Filter by source type (e.g., windows_evtx)"),
    action: str | None = Query(None, description="Filter by action type"),
    device_id: str | None = Query(None, description="Filter by device ID"),
    ip_address: str | None = Query(None, description="Filter by IP address"),
    timestamp_from: str | None = Query(None, description="Start of time range (ISO 8601)"),
    timestamp_to: str | None = Query(None, description="End of time range (ISO 8601)"),
    from_: int = Query(0, alias="offset", ge=0, description="Offset for pagination"),
    size: int = Query(50, ge=1, le=200, description="Max results per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
):
    result = search_log_events(
        case_id=case_id,
        query=query,
        source_type=source_type,
        action=action,
        device_id=device_id,
        ip_address=ip_address,
        timestamp_from=timestamp_from,
        timestamp_to=timestamp_to,
        from_=from_,
        size=size,
    )
    return SearchResponse(total=result["total"], events=result["events"])
