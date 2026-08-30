import asyncio
import json
from collections import defaultdict
from typing import Any

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_case_access
from app.core.config import get_settings
from app.db.models.base_models import Device, User
from app.db.session import get_db
from app.storage.search_index import search_log_events

router = APIRouter(prefix="/api/cases", tags=["nl-query"])

settings = get_settings()


class NLQueryRequest(BaseModel):
    question: str


class FilterParams(BaseModel):
    source_type: str | None = None
    action: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    timestamp_from: str | None = None
    timestamp_to: str | None = None
    query: str | None = None
    offset: int | None = 0
    size: int | None = 50


class NLQueryResponse(BaseModel):
    filters: FilterParams
    llm_reasoning: str


class NLQueryExecuteRequest(BaseModel):
    question: str


class NLQueryExecuteResponse(BaseModel):
    answer: str
    cited_event_ids: list[str]
    filters_applied: FilterParams
    total_found: int


SYSTEM_PROMPT = """You are a query translation assistant for a cyber forensics platform.

Your ONLY task is to translate a natural language question into structured filter parameters against the LogEvent table.
You must NOT answer the question — only extract the filters.

The LogEvent table has these filterable fields:
- source_type: log source (e.g. windows_evtx, android_logcat, linux_syslog, network_generic)
- action: what happened (e.g. file_write, file_transfer, usb_insert, email_sent, network_connect)
- device_id: UUID of the device — ONLY use if the user explicitly names a device that exists in the case
- ip_address: IP address — ONLY use if the user explicitly mentions a specific IP
- timestamp_from / timestamp_to: ISO 8601 datetime range
- query: free-text keyword search across event details
- offset: pagination offset (default 0)
- size: max results (default 50, max 1000)

Rules:
- If the user asks about a device/entity that is NOT mentioned by name in the case data, set device_id, ip_address, and query to null — do not guess or invent values
- If no meaningful filters can be extracted, return all nulls (the investigator will browse all events)
- NEVER fabricate filter values. Only populate a field if the user explicitly states it.
- Your output must be valid JSON matching the FilterParams schema

Output format: return a JSON object with:
- "filters": the FilterParams object (all fields optional/null except offset/size which default to 0/50)
- "llm_reasoning": a brief 1-sentence explanation of what you extracted and why anything unclear was left null

Example:
User: "Show me all USB events from yesterday"
{
  "filters": {"source_type": null, "action": "usb_insert", "device_id": null, "ip_address": null, "timestamp_from": "2024-01-01T00:00:00Z", "timestamp_to": "2024-01-02T00:00:00Z", "query": null, "offset": 0, "size": 50},
  "llm_reasoning": "Extracted action=usb_insert and a yesterday date range. Left device_id/ip_address null as no specific device/IP was mentioned."
}
"""


@router.post("/{case_id}/nl-query", response_model=NLQueryResponse)
async def nl_query(
    case_id: str,
    body: NLQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
) -> NLQueryResponse:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="NL query service not configured: ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": body.question,
                }
            ],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NL query service error: {exc}")

    raw_text = response.content[0].text.strip()

    try:
        parsed = json.loads(raw_text)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="NL query service returned malformed JSON. Try rephrasing your question.",
        )

    filters_data: dict[str, Any] = parsed.get("filters", {})
    llm_reasoning: str = parsed.get("llm_reasoning", "")

    validated_filters = FilterParams(
        source_type=filters_data.get("source_type"),
        action=filters_data.get("action"),
        device_id=filters_data.get("device_id"),
        ip_address=filters_data.get("ip_address"),
        timestamp_from=filters_data.get("timestamp_from"),
        timestamp_to=filters_data.get("timestamp_to"),
        query=filters_data.get("query"),
        offset=filters_data.get("offset", 0),
        size=min(filters_data.get("size", 50), 1000),
    )

    return NLQueryResponse(filters=validated_filters, llm_reasoning=llm_reasoning)


def _format_answer_from_events(events: list[dict], filters: FilterParams) -> tuple[str, list[str]]:
    if not events:
        return "No events found matching your query.", []

    cited_ids: list[str] = []

    by_action: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        by_action[e.get("action", "unknown")].append(e)

    lines = [f"Found {len(events)} event(s)."]

    if len(by_action) == 1:
        action_name = list(by_action.keys())[0]
        lines.append(f"All {len(events)} events involve: **{action_name}**.")
    else:
        lines.append("Event breakdown by action type:")
        for action, evts in sorted(by_action.items()):
            lines.append(f"  - {action}: {len(evts)} event(s)")

    actors = sorted({e.get("actor") for e in events if e.get("actor")})
    if actors:
        lines.append(f"Actors observed: {', '.join(actors)}.")

    objects = sorted({e.get("object") for e in events if e.get("object")})
    if objects:
        obj_samples = objects[:5]
        more = f" (+{len(objects)-5} more)" if len(objects) > 5 else ""
        lines.append(f"Objects: {', '.join(obj_samples)}{more}.")

    ips = sorted({e.get("ip_address") for e in events if e.get("ip_address")})
    if ips:
        lines.append(f"IP addresses: {', '.join(ips)}.")

    files = sorted({e.get("file_hash") for e in events if e.get("file_hash")})
    if files:
        lines.append(f"File hashes ({len(files)} total): {', '.join(files[:3])}{' ...' if len(files) > 3 else ''}.")

    timestamps = [e.get("timestamp") for e in events if e.get("timestamp")]
    if timestamps:
        lines.append(f"Time range: {min(timestamps)} → {max(timestamps)}.")

    cited_ids = [e.get("id") for e in events if e.get("id")][:20]

    return " ".join(lines), cited_ids


async def _call_llm(question: str) -> tuple[FilterParams, str]:
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="NL query service not configured: ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": question}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NL query service error: {exc}")

    raw_text = response.content[0].text.strip()

    try:
        parsed = json.loads(raw_text)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="NL query service returned malformed JSON. Try rephrasing your question.",
        )

    filters_data: dict[str, Any] = parsed.get("filters", {})
    llm_reasoning: str = parsed.get("llm_reasoning", "")

    validated_filters = FilterParams(
        source_type=filters_data.get("source_type"),
        action=filters_data.get("action"),
        device_id=filters_data.get("device_id"),
        ip_address=filters_data.get("ip_address"),
        timestamp_from=filters_data.get("timestamp_from"),
        timestamp_to=filters_data.get("timestamp_to"),
        query=filters_data.get("query"),
        offset=filters_data.get("offset", 0),
        size=min(filters_data.get("size", 50), 1000),
    )

    return validated_filters, llm_reasoning


@router.post("/{case_id}/nl-query/execute", response_model=NLQueryExecuteResponse)
async def nl_query_execute(
    case_id: str,
    body: NLQueryExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
) -> NLQueryExecuteResponse:
    filters, _ = await _call_llm(body.question)

    if filters.device_id:
        result = await db.execute(select(Device).where(Device.id == filters.device_id, Device.case_id == case_id))
        if not result.scalar_one_or_none():
            filters.query = (filters.query or "") + " " + filters.device_id
            filters.device_id = None

    def _search() -> dict:
        return search_log_events(
            case_id=case_id,
            query=filters.query,
            source_type=filters.source_type,
            action=filters.action,
            device_id=filters.device_id,
            ip_address=filters.ip_address,
            timestamp_from=filters.timestamp_from,
            timestamp_to=filters.timestamp_to,
            from_=filters.offset or 0,
            size=filters.size or 50,
        )

    search_result = await asyncio.to_thread(_search)
    events: list[dict] = search_result.get("events", [])
    total: int = search_result.get("total", 0)

    answer, cited_ids = _format_answer_from_events(events, filters)

    return NLQueryExecuteResponse(
        answer=answer,
        cited_event_ids=cited_ids,
        filters_applied=filters,
        total_found=total,
    )
