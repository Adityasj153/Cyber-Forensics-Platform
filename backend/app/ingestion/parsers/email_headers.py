from datetime import datetime, timezone
from email import message_from_string

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class EmailHeadersParser(BaseParser):
    source_type = "email_headers"

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if lower.endswith(".eml") or "email" in lower or "mail" in lower or "header" in lower:
            return True
        try:
            text = data.decode("utf-8", errors="replace")
            if (
                text.startswith("From:")
                or text.startswith("Received:")
                or "MIME-Version:" in text[:500]
            ):
                return True
        except Exception:
            return False
        return False

    def parse(self, data: bytes) -> list[ParsedEvent]:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")

        events = []
        msg = message_from_string(text)

        date_str = msg.get("Date", "")
        ts = datetime.now(timezone.utc)
        if date_str:
            try:
                from email.utils import parsedate_to_datetime  # noqa: PLC0415

                ts = parsedate_to_datetime(date_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        from_addr = msg.get("From", "unknown")
        to_addr = msg.get("To", "unknown")
        subject = msg.get("Subject", "(no subject)")

        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                filename = part.get_filename()
                if filename:
                    attachments.append(filename)

        detail = f"Email from {from_addr} to {to_addr}: {subject}"
        if attachments:
            detail += f" [Attachments: {', '.join(attachments)}]"

        events.append(
            ParsedEvent(
                timestamp=ts,
                source_type=self.source_type,
                actor=from_addr,
                action="email_sent",
                object=subject[:500],
                detail=detail[:2000],
                raw_line=text[:5000],
                extra={
                    "from": from_addr,
                    "to": to_addr,
                    "subject": subject,
                    "attachments": attachments,
                },
            )
        )

        received_headers = msg.get_all("Received", [])
        events.extend(
            ParsedEvent(
                timestamp=ts,
                source_type=self.source_type,
                actor=from_addr,
                action="email_relay",
                object=recv[:500],
                detail=recv[:2000],
                raw_line=recv[:5000],
            )
            for recv in received_headers
        )

        return events
