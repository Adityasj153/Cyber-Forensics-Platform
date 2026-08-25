from datetime import datetime, timezone
import re

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class AndroidLogcatParser(BaseParser):
    source_type = "android_logcat"

    # logcat format: MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message
    _LOGCAT_PATTERN = re.compile(
        r"(\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+?)\s*:\s+(.*)"
    )

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if "logcat" in lower or "android" in lower:
            return True
        try:
            text = data.decode("utf-8", errors="replace")
            first_lines = text[:500]
            return bool(self._LOGCAT_PATTERN.search(first_lines))
        except Exception:
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
            match = self._LOGCAT_PATTERN.match(line)
            if not match:
                continue

            date_str, time_str, pid, tid, level, tag, message = match.groups()

            try:
                ts = datetime.strptime(f"{year} {date_str} {time_str}", "%Y %m-%d %H:%M:%S.%f")
                ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = datetime.now(timezone.utc)

            action = "log_entry"
            lower_msg = message.lower()
            lower_tag = tag.lower()

            if "usb" in lower_tag or "usb" in lower_msg:
                action = "usb_event"
            elif "bluetooth" in lower_tag or "bt" in lower_tag or "bluetooth" in lower_msg:
                action = "bluetooth_event"
            elif "wifi" in lower_tag or "wifi" in lower_msg or "wlan" in lower_msg:
                action = "wifi_event"
            elif "file" in lower_msg and ("copy" in lower_msg or "transfer" in lower_msg or "send" in lower_msg):
                action = "file_transfer"
            elif "install" in lower_msg or "package" in lower_tag:
                action = "app_install"
            elif "start" in lower_msg or "launch" in lower_msg:
                action = "app_start"
            elif level in ("E", "F"):
                action = "error"
            elif level == "W":
                action = "warning"

            events.append(ParsedEvent(
                timestamp=ts,
                source_type=self.source_type,
                actor=f"pid:{pid}/tag:{tag}",
                action=action,
                object=tag,
                detail=message[:2000],
                raw_line=line[:5000],
                extra={"level": level, "pid": pid, "tid": tid},
            ))

        return events
