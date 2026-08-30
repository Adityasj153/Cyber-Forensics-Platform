import re
from datetime import datetime, timezone

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class WindowsEVTXParser(BaseParser):
    source_type = "windows_evtx"

    _EVTX_MAGIC = b"ElfFile\x00"
    _SHA256_PATTERN = re.compile(r"\b([0-9a-fA-F]{40,})\b")
    _IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    # Header: 8/20/2026 9:14:00 AM | INFO | 4688 | Security | Message
    # (accepts single or double digit month/day/hour, pipe or space separators)
    _HEADER_PATTERN = re.compile(
        r"^(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM))\s*"
        r"[\|]\s*(?:INFO|WARNING|ERROR|AUDIT_SUCCESS|AUDIT_FAILURE)\s*"
        r"[\|]\s*(\d+)\s*[\|]\s*([^|]+?)\s*[\|]\s*(.*)$",
        re.IGNORECASE,
    )
    # Matches rename targets (-> report.docx.locked), quoted filenames,
    # and absolute windows paths
    _RENAME_PATTERN = re.compile(r"->\s*([\w\- .]+\.\w+)", re.IGNORECASE)
    _QUOTED_PATTERN = re.compile(r'"([^"]+\.\w+)"')
    _PATH_PATTERN = re.compile(r"([A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]+\.\w+)")

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if lower.endswith(".evtx"):
            return True
        if data[:8] == self._EVTX_MAGIC:
            return True
        try:
            text = data.decode("utf-8", errors="replace")
            return any(self._HEADER_PATTERN.match(line.strip()) for line in text.splitlines()[:20])
        except Exception:
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
            events.append(
                ParsedEvent(
                    timestamp=datetime.now(timezone.utc),
                    source_type=self.source_type,
                    action="log_entry",
                    detail=text.strip()[:2000],
                    raw_line=text.strip()[:5000],
                )
            )

        return events

    def _extract_filename(self, message: str) -> str | None:
        rename = self._RENAME_PATTERN.search(message)
        if rename:
            return rename.group(1)
        quoted = self._QUOTED_PATTERN.search(message)
        if quoted:
            return quoted.group(1)
        path = self._PATH_PATTERN.search(message)
        if path:
            return path.group(1)
        return None

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

        date_str, time_str, event_id, source, message = match.groups()
        source = source.strip() if source else ""
        message = message.strip() if message else ""
        lower = message.lower()
        try:
            ts = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M:%S %p")
            ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            ts = datetime.now(timezone.utc)

        action = self._classify_action(lower, source)
        filename = self._extract_filename(message)
        ips = self._IP_PATTERN.findall(message)
        sha = self._SHA256_PATTERN.search(message)
        file_hash = sha.group(1)[:64].lower() if sha else None

        actor = source or f"EventID:{event_id}"
        user_match = re.search(
            r"\b(?:user account\s*[:]\s*)?([\w\.\-]+@[\w\.\-]+|\buser\s+(\w+)\b)", lower
        )
        if user_match:
            actor = (user_match.group(1) or user_match.group(2)).strip()

        return ParsedEvent(
            timestamp=ts,
            source_type=self.source_type,
            actor=actor,
            action=action,
            object=filename or message[:1000],
            ip_address=ips[0] if ips else None,
            file_hash=file_hash,
            detail=message[:2000],
            raw_line=line[:5000],
        )

    @staticmethod
    def _classify_action(lower_msg: str, source: str) -> str:
        lower_src = source.lower()
        if "email" in lower_src and (
            "sent" in lower_msg or "attach" in lower_msg or "upload" in lower_msg
        ):
            return "email_sent"
        if "bluetooth" in lower_src or "bluetooth" in lower_msg:
            return "bluetooth_transfer"
        if "usb" in lower_msg:
            return "usb_transfer"
        if "ransom" in lower_msg or ("readme" in lower_msg and "decrypt" in lower_msg):
            return "ransom_note_created"
        if "file write" in lower_msg or ("file" in lower_msg and "writ" in lower_msg):
            return "file_write"
        if "file created" in lower_msg or ("file" in lower_msg and "creat" in lower_msg):
            return "file_create"
        if "file" in lower_msg and ("delet" in lower_msg or "remov" in lower_msg):
            return "file_delete"
        if "process created" in lower_msg or (
            "process" in lower_msg and ("start" in lower_msg or "creat" in lower_msg)
        ):
            return "process_start"
        if "download" in lower_msg:
            return "download_complete"
        if "extracted archive" in lower_msg or "unzip" in lower_msg:
            return "file_extract"
        if "network connection" in lower_msg or ("network" in lower_msg or "connect" in lower_msg):
            return "network_connection"
        if "dns" in lower_msg:
            return "dns_query"
        if "logon" in lower_msg:
            return "logon"
        if "logoff" in lower_msg:
            return "logoff"
        if "install" in lower_msg:
            return "software_install"
        if "registry modification" in lower_msg:
            return "registry_edit"
        if "scheduled task" in lower_msg or "taskscheduler" in lower_src:
            return "task_schedule"
        if "access" in lower_msg and ("denied" in lower_msg or "deny" in lower_msg):
            return "access_denied"
        return "event_record"
