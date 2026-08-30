import re
from datetime import datetime, timezone

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class LinuxSyslogParser(BaseParser):
    source_type = "linux_syslog"

    # RFC 3164 style: Aug 24 14:05:01 hostname process[pid]: message
    _SYSLOG_PATTERN = re.compile(
        r"(\w{3})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+?)(?:\[(\d+)\])?:\s+(.*)"
    )

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if "syslog" in lower or lower.endswith(".log") or lower.endswith(".syslog"):
            try:
                text = data.decode("utf-8", errors="replace")
                first_lines = text[:500]
                return bool(self._SYSLOG_PATTERN.search(first_lines))
            except Exception:
                return False
        return False

    def parse(self, data: bytes) -> list[ParsedEvent]:
        events = []
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")

        year = datetime.now(timezone.utc).year

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            match = self._SYSLOG_PATTERN.match(line)
            if not match:
                continue

            month_str, day, time_str, hostname, process, pid, message = match.groups()

            try:
                ts = datetime.strptime(f"{year} {month_str} {day} {time_str}", "%Y %b %d %H:%M:%S")
                ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = datetime.now(timezone.utc)

            action = "log_entry"
            lower_msg = message.lower()
            if "error" in lower_msg or "fail" in lower_msg:
                action = "error"
            elif "warning" in lower_msg or "warn" in lower_msg:
                action = "warning"
            elif "accepted" in lower_msg or "login" in lower_msg or "session opened" in lower_msg:
                action = "logon"
            elif "session closed" in lower_msg or "logout" in lower_msg:
                action = "logoff"
            elif "sudo" in lower_msg:
                action = "privilege_escalation"
            elif "cron" in process.lower():
                action = "cron_execution"

            actor = process
            if pid:
                actor = f"{process}[{pid}]"

            events.append(
                ParsedEvent(
                    timestamp=ts,
                    source_type=self.source_type,
                    actor=actor,
                    action=action,
                    object=hostname,
                    detail=message[:2000],
                    raw_line=line[:5000],
                )
            )

        return events
