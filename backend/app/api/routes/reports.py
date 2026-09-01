import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_case_access, require_role
from app.db.models.base_models import (
    Anomaly,
    Case,
    CorrelationEdge,
    Device,
    Entity,
    LogEvent,
    Report,
    ReportStatus,
    User,
    UserRole,
)
from app.db.session import get_db

router = APIRouter(prefix="/api/cases", tags=["reports"])


class ReportGenerateRequest(BaseModel):
    format: str
    title: str | None = None


class ReportResponse(BaseModel):
    id: str
    case_id: str
    format: str
    status: str
    title: str
    content_hash: str
    created_by: str
    approved_by: str | None
    approved_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ReportDetailResponse(BaseModel):
    id: str
    case_id: str
    format: str
    status: str
    title: str
    content_hash: str
    content_json: dict[str, Any]
    created_by: str
    approved_by: str | None
    approved_at: str | None
    created_at: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


async def _gather_case_data(db: AsyncSession, case_id: str) -> dict[str, Any]:
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    events_result = await db.execute(
        select(LogEvent).where(LogEvent.case_id == case_id).order_by(LogEvent.timestamp)
    )
    events = list(events_result.scalars().all())

    entities_result = await db.execute(select(Entity).where(Entity.case_id == case_id))
    entities = list(entities_result.scalars().all())

    anomalies_result = await db.execute(select(Anomaly).where(Anomaly.case_id == case_id))
    anomalies = list(anomalies_result.scalars().all())

    correlations_result = await db.execute(
        select(CorrelationEdge).where(CorrelationEdge.case_id == case_id)
    )
    correlations = list(correlations_result.scalars().all())

    devices_result = await db.execute(select(Device).where(Device.case_id == case_id))
    devices = list(devices_result.scalars().all())

    return {
        "case": {
            "id": str(case.id),
            "name": case.name,
            "description": case.description,
            "status": case.status.value if case.status else None,
            "created_by": str(case.created_by),
            "created_at": case.created_at.isoformat() if case.created_at else None,
            "updated_at": case.updated_at.isoformat() if case.updated_at else None,
        },
        "events": [
            {
                "id": str(e.id),
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "source_type": e.source_type,
                "actor": e.actor,
                "action": e.action,
                "object": e.object,
                "ip_address": e.ip_address,
                "file_hash": e.file_hash,
                "detail": e.detail,
                "device_id": str(e.device_id) if e.device_id else None,
            }
            for e in events
        ],
        "entities": [
            {
                "id": str(e.id),
                "entity_type": e.entity_type,
                "value": e.value,
                "metadata": e.entity_metadata,
            }
            for e in entities
        ],
        "anomalies": [
            {
                "id": str(a.id),
                "event_ids": a.event_ids,
                "score": a.score,
                "severity": a.severity,
                "category": a.category,
                "model_name": a.model_name,
                "review_status": a.review_status,
            }
            for a in anomalies
        ],
        "correlations": [
            {
                "id": str(c.id),
                "entity_a_id": str(c.entity_a_id),
                "entity_b_id": str(c.entity_b_id),
                "relation_type": c.relation_type,
                "confidence": c.confidence,
            }
            for c in correlations
        ],
        "devices": [
            {
                "id": str(d.id),
                "device_type": d.device_type,
                "os": d.os,
                "owner": d.owner,
                "name": d.name,
            }
            for d in devices
        ],
    }


def _build_text_report(data: dict[str, Any]) -> str:
    case = data["case"]
    lines = [
        "INVESTIGATION REPORT",
        "=" * 60,
        "",
        f"Case: {case['name']}",
        f"ID: {case['id']}",
        f"Status: {case['status']}",
        f"Created: {case['created_at']}",
        f"Description: {case['description'] or 'N/A'}",
        "",
        "=" * 60,
        "EVENT SUMMARY",
        "=" * 60,
        f"Total Events: {len(data['events'])}",
    ]

    action_counts: dict[str, int] = {}
    for e in data["events"]:
        action_counts[e["action"]] = action_counts.get(e["action"], 0) + 1
    for action, count in sorted(action_counts.items(), key=lambda x: -x[1])[:10]:
        lines.append(f"  {action}: {count}")

    lines.extend(
        [
            "",
            "=" * 60,
            f"DEVICES ({len(data['devices'])})",
            "=" * 60,
        ]
    )
    lines.extend(
        f"  - {d['name'] or d['id']} ({d['device_type']}, OS: {d['os'] or 'N/A'}, Owner: {d['owner'] or 'N/A'})"
        for d in data["devices"]
    )

    lines.extend(
        [
            "",
            "=" * 60,
            f"ENTITIES ({len(data['entities'])})",
            "=" * 60,
        ]
    )
    lines.extend(f"  [{e['entity_type']}] {e['value']}" for e in data["entities"])

    lines.extend(
        [
            "",
            "=" * 60,
            f"ANOMALIES ({len(data['anomalies'])})",
            "=" * 60,
        ]
    )
    lines.extend(
        f"  [{a['severity'].upper()}] {a['category']} (score={a['score']:.3f}, status={a['review_status']})"
        for a in data["anomalies"]
    )

    lines.extend(
        [
            "",
            "=" * 60,
            f"CORRELATIONS ({len(data['correlations'])})",
            "=" * 60,
        ]
    )
    lines.extend(
        f"  {c['relation_type']}: {c['entity_a_id'][:8]}... -> {c['entity_b_id'][:8]}... (conf={c['confidence']:.2f})"
        for c in data["correlations"]
    )

    lines.extend(
        [
            "",
            "=" * 60,
            "EVENT DETAIL (first 100)",
            "=" * 60,
        ]
    )
    lines.extend(
        f"[{e['timestamp']}] {e['action']} | actor={e['actor'] or '?'} | object={e['object'] or '?'} | ip={e['ip_address'] or '?'} | detail={str(e['detail'] or '')[:80]}"
        for e in data["events"][:100]
    )

    return "\n".join(lines)


def _build_csv(data: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "timestamp",
            "source_type",
            "action",
            "actor",
            "object",
            "ip_address",
            "file_hash",
            "device_id",
            "detail",
        ]
    )
    for e in data["events"]:
        writer.writerow(
            [
                e["timestamp"] or "",
                e["source_type"] or "",
                e["action"] or "",
                e["actor"] or "",
                e["object"] or "",
                e["ip_address"] or "",
                e["file_hash"] or "",
                e["device_id"] or "",
                (e["detail"] or "")[:200],
            ]
        )
    return output.getvalue()


def _build_pdf(data: dict[str, Any]) -> bytes:
    case = data["case"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, spaceAfter=12)
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontSize=12, spaceAfter=6, spaceBefore=12
    )
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, spaceAfter=4)

    story = []

    story.append(Paragraph(f"Investigation Report: {case['name']}", title_style))
    story.append(Paragraph(f"Case ID: {case['id']}", body_style))
    story.append(Paragraph(f"Status: {case['status']}", body_style))
    story.append(Paragraph(f"Generated: {datetime.now(timezone.utc).isoformat()}", body_style))
    story.append(Paragraph(f"Description: {case['description'] or 'N/A'}", body_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Event Summary", heading_style))
    story.append(Paragraph(f"Total events: {len(data['events'])}", body_style))

    action_counts: dict[str, int] = {}
    for e in data["events"]:
        action_counts[e["action"]] = action_counts.get(e["action"], 0) + 1
    top_actions = sorted(action_counts.items(), key=lambda x: -x[1])[:10]
    action_data = [["Action", "Count"]] + [[a, str(c)] for a, c in top_actions]
    action_table = Table(action_data, colWidths=[3 * inch, 1.5 * inch])
    action_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#475569")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#1e293b"), colors.HexColor("#0f172a")],
                ),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(action_table)
    story.append(Spacer(1, 0.15 * inch))

    if data["devices"]:
        story.append(Paragraph("Devices", heading_style))
        dev_data = [["Name", "Type", "OS", "Owner"]] + [
            [d["name"] or d["id"][:8], d["device_type"], d["os"] or "N/A", d["owner"] or "N/A"]
            for d in data["devices"]
        ]
        dev_table = Table(dev_data, colWidths=[2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
        dev_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#475569")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#1e293b"), colors.HexColor("#0f172a")],
                    ),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(dev_table)
        story.append(Spacer(1, 0.15 * inch))

    if data["anomalies"]:
        story.append(Paragraph("Anomalies", heading_style))
        anomaly_data = [["Severity", "Category", "Score", "Status"]] + [
            [a["severity"].upper(), a["category"], f"{a['score']:.3f}", a["review_status"]]
            for a in data["anomalies"]
        ]
        anomaly_table = Table(anomaly_data, colWidths=[1 * inch, 2 * inch, 1 * inch, 1.5 * inch])
        anomaly_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#475569")),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#1e293b"), colors.HexColor("#0f172a")],
                    ),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(anomaly_table)
        story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Event Detail (sample, first 50)", heading_style))
    event_data = [["Timestamp", "Action", "Actor", "Object"]] + [
        [
            e["timestamp"][:19] if e["timestamp"] else "",
            e["action"],
            e["actor"] or "",
            e["object"] or "",
        ]
        for e in data["events"][:50]
    ]
    event_table = Table(event_data, colWidths=[1.8 * inch, 1.5 * inch, 1.5 * inch, 2 * inch])
    event_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#475569")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#1e293b"), colors.HexColor("#0f172a")],
                ),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(event_table)

    doc.build(story)
    return buf.getvalue()


@router.post("/{case_id}/reports/generate", response_model=ReportDetailResponse)
async def generate_report(
    case_id: str,
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
) -> ReportDetailResponse:
    if body.format not in ("pdf", "csv", "json", "text"):
        raise HTTPException(status_code=400, detail="format must be pdf, csv, json, or text")

    case_data = await _gather_case_data(db, case_id)
    title = body.title or f"Investigation Report - {case_data['case']['name']}"

    if body.format == "json":
        content_str = json.dumps(case_data, indent=2)
        content_json = case_data
    elif body.format == "csv":
        content_str = _build_csv(case_data)
        content_json = {"format": "csv", "row_count": len(case_data["events"])}
    elif body.format == "text":
        content_str = _build_text_report(case_data)
        content_json = {"format": "text"}
    else:
        pdf_bytes = _build_pdf(case_data)
        content_str = pdf_bytes.decode("latin-1")
        content_json = {"format": "pdf", "byte_count": len(pdf_bytes)}

    content_hash = _compute_hash(content_str)

    report = Report(
        case_id=case_id,
        format=body.format,
        status=ReportStatus.DRAFT,
        title=title,
        content_hash=content_hash,
        content_json=content_json,
        created_by=current_user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return ReportDetailResponse(
        id=str(report.id),
        case_id=str(report.case_id),
        format=report.format,
        status=report.status.value,
        title=report.title,
        content_hash=report.content_hash,
        content_json=report.content_json,
        created_by=str(report.created_by),
        approved_by=None,
        approved_at=None,
        created_at=report.created_at.isoformat(),
    )


@router.get("/{case_id}/reports", response_model=list[ReportResponse])
async def list_reports(
    case_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
) -> list[ReportResponse]:
    result = await db.execute(
        select(Report).where(Report.case_id == case_id).order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return [
        ReportResponse(
            id=str(r.id),
            case_id=str(r.case_id),
            format=r.format,
            status=r.status.value,
            title=r.title,
            content_hash=r.content_hash,
            created_by=str(r.created_by),
            approved_by=str(r.approved_by) if r.approved_by else None,
            approved_at=r.approved_at.isoformat() if r.approved_at else None,
            created_at=r.created_at.isoformat(),
        )
        for r in reports
    ]


@router.patch("/{case_id}/reports/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    case_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.INVESTIGATOR)),
) -> ReportResponse:
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.case_id == case_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status == ReportStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Report is already approved")

    report.status = ReportStatus.APPROVED
    report.approved_by = current_user.id
    report.approved_at = _utcnow()
    await db.commit()
    await db.refresh(report)

    return ReportResponse(
        id=str(report.id),
        case_id=str(report.case_id),
        format=report.format,
        status=report.status.value,
        title=report.title,
        content_hash=report.content_hash,
        created_by=str(report.created_by),
        approved_by=str(report.approved_by) if report.approved_by else None,
        approved_at=report.approved_at.isoformat() if report.approved_at else None,
        created_at=report.created_at.isoformat(),
    )


@router.get("/{case_id}/reports/{report_id}/download")
async def download_report(
    case_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_case_access),
) -> StreamingResponse:
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.case_id == case_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.format == "pdf":
        pdf_bytes = _build_pdf(await _gather_case_data(db, case_id))
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{report.title}.pdf"',
                "X-Content-Hash": report.content_hash,
            },
        )
    elif report.format == "csv":
        case_data = await _gather_case_data(db, case_id)
        csv_content = _build_csv(case_data)
        return StreamingResponse(
            io.BytesIO(csv_content.encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{report.title}.csv"',
                "X-Content-Hash": report.content_hash,
            },
        )
    elif report.format == "text":
        case_data = await _gather_case_data(db, case_id)
        text_content = _build_text_report(case_data)
        return StreamingResponse(
            io.BytesIO(text_content.encode()),
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="{report.title}.txt"',
                "X-Content-Hash": report.content_hash,
            },
        )
    else:
        case_data = await _gather_case_data(db, case_id)
        json_content = json.dumps(case_data, indent=2)
        return StreamingResponse(
            io.BytesIO(json_content.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{report.title}.json"',
                "X-Content-Hash": report.content_hash,
            },
        )
