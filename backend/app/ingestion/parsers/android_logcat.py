import os
import re
from datetime import datetime, timezone

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class AndroidLogcatParser(BaseParser):
    source_type = "android_logcat"

    # logcat format: MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message
    _LOGCAT_PATTERN = re.compile(
        r"(\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+(\w)\s+(\S+?)\s*:\s*(.*)"
    )
    _SHA256_PATTERN = re.compile(r"\b([0-9a-fA-F]{40,})\b")
    _IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _FILENAME_PATTERN = re.compile(r"[\\/]?([\w\-]+\.\w+)")

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
        last_filename = None

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

            action, filename, obj, file_hash, ip_address = self._classify(
                tag, message, last_filename
            )
            if filename:
                last_filename = filename

            events.append(
                ParsedEvent(
                    timestamp=ts,
                    source_type=self.source_type,
                    actor=f"pid:{pid}/tag:{tag}",
                    action=action,
                    object=obj or filename,
                    ip_address=ip_address,
                    file_hash=file_hash,
                    detail=message[:2000],
                    raw_line=line[:5000],
                    extra={"level": level, "pid": pid, "tid": tid, "tag": tag},
                )
            )

        return events

    @staticmethod
    def _extract_filename(message: str) -> str | None:
        match = AndroidLogcatParser._FILENAME_PATTERN.search(message)
        if not match:
            return None
        # Return the basename (strip any leading path separator and directories)
        return os.path.basename(match.group(1))

    @staticmethod
    def _classify(tag: str, message: str, last_filename: str | None):
        lower_msg = message.lower()
        lower_tag = tag.lower()
        hashes = AndroidLogcatParser._SHA256_PATTERN.findall(message)
        file_hash = hashes[0][:64].lower() if hashes else None
        ips = AndroidLogcatParser._IP_PATTERN.findall(message)
        ip_address = ips[0] if ips else None

        # SHA-256 checksum line: tie to previously seen file so hash<->file edge forms
        if file_hash and last_filename:
            return "file_checksum", last_filename, last_filename, file_hash, ip_address

        # Email handling first (EmailApp tag also carries "Email sent" lines)
        if "email sent" in lower_msg or "email delivered" in lower_msg:
            recv = re.search(r"to\s+([\w\.\-]+@[\w\.\-]+)", lower_msg)
            obj = recv.group(1) if recv else None
            return "email_sent", None, obj, file_hash, ip_address
        if "attaching file" in lower_msg or "attachment" in lower_msg:
            filename = AndroidLogcatParser._extract_filename(message)
            return "email_attach", filename, filename, file_hash, ip_address

        if "file received" in lower_msg or "received via" in lower_msg or "mtp" in lower_tag:
            filename = AndroidLogcatParser._extract_filename(message)
            return "file_received", filename, filename, file_hash, ip_address
        if "sending file" in lower_msg or "opp" in lower_tag:
            filename = AndroidLogcatParser._extract_filename(message)
            return "bluetooth_transfer", filename, filename, file_hash, ip_address
        if "scanning new file" in lower_msg or "mediascanner" in lower_tag:
            filename = AndroidLogcatParser._extract_filename(message)
            return "file_scan", filename, filename, file_hash, ip_address
        if "usb" in lower_tag or "usb" in lower_msg:
            return "usb_event", None, None, file_hash, ip_address
        if "bluetooth" in lower_tag or "bt" in lower_tag or "bluetooth" in lower_msg:
            return "bluetooth_event", None, None, file_hash, ip_address
        if (
            "wifi" in lower_tag
            or "wlan" in lower_msg
            or "network" in lower_tag
            or "connectivity" in lower_tag
        ):
            return "network_event", None, None, file_hash, ip_address
        if "install" in lower_msg or "package" in lower_tag:
            return "app_install", None, None, file_hash, ip_address
        if "start" in lower_msg or "launch" in lower_msg:
            return "app_start", None, None, file_hash, ip_address
        return "log_entry", None, None, file_hash, ip_address
