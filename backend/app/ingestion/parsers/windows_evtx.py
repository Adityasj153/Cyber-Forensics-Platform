from datetime import datetime, timezone
import re

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class WindowsEVTXParser(BaseParser):
    source_type = "windows_evtx"

    _EVTX_MAGIC = b"ElfFile\x00"
    _HEADER_PATTERN = re.compile(
        r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2}\s*(?:AM|PM))\s+"
        r"(?:INFO|WARNING|ERROR|AUDIT_SUCCESS|AUDIT_FAILURE)\s+"
        r"(\d+)\s+(.+?)\s+\|\s+(.*)",
        re.IGNORECASE,
    )

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if lower.endswith(".evtx"):
            return True
        if data[:8] == self._EVTX_MAGIC:
            return True
        return False

    def parse(self, data: bytes) -> list[ParsedEvent]:
        events = []
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parsed = self._parse_line(line)
            if parsed:
                events.append(parsed)

        if not events and text.strip():
            events.append(ParsedEvent(
                timestamp=datetime.now(timezone.utc),
                source_type=self.source_type,
                action="log_entry",
                detail=text.strip()[:2000],
                raw_line=text.strip()[:5000],
            ))

        return events

    def _parse_line(self, line: str) -> ParsedEvent | None:
        match = self._HEADER_PATTERN.match(line)
        if not match:
            return ParsedEvent(
                timestamp=datetime.now(timezone.utc),
                source_type=self.source_type,
                action="log_entry",
                detail=line[:2000],
                raw_line=line[:5000],
            )

        date_str, time_str, event_id, message = match.groups()
        try:
            ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M:%S %p")
            ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)

        action = "event_record"
        lower_msg = message.lower()
        if "logon" in lower_msg:
            action = "logon"
        elif "logoff" in lower_msg:
            action = "logoff"
        elif "file" in lower_msg and ("creat" in lower_msg or "writ" in lower_msg):
            action = "file_write"
        elif "file" in lower_msg and ("delet" in lower_msg or "remov" in lower_msg):
            action = "file_delete"
        elif "process" in lower_msg and ("start" in lower_msg or "creat" in lower_msg):
            action = "process_start"
        elif "network" in lower_msg or "connect" in lower_msg:
            action = "network_connection"
        elif "install" in lower_msg:
            action = "software_install"
        elif "download" in lower_msg:
            action = "download_complete"

        return ParsedEvent(
            timestamp=ts,
            source_type=self.source_type,
            actor=f"EventID:{event_id}",
            action=action,
            object=message[:1000],
            detail=message[:2000],
            raw_line=line[:5000],
        )
