from datetime import datetime, timezone
import re

from app.ingestion.parsers.base import BaseParser, ParsedEvent


class AndroidUSBBTParser(BaseParser):
    source_type = "android_usb_bt"

    _USB_FILE_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+.*?USB.*?(\S+\.\w+)\s*(?:to|from)\s*(.+)",
        re.IGNORECASE,
    )
    _BT_FILE_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+.*?Bluetooth.*?(\S+\.\w+)\s*(?:sent|received|transferred)\s*(?:to|from)?\s*(.*)",
        re.IGNORECASE,
    )
    _GENERIC_TRANSFER = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.*)",
        re.IGNORECASE,
    )

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if "usb" in lower or "bluetooth" in lower or "btsnoop" in lower or "transfer" in lower:
            return True
        try:
            text = data.decode("utf-8", errors="replace")
            first_lines = text[:500]
            return bool(self._USB_FILE_PATTERN.search(first_lines) or self._BT_FILE_PATTERN.search(first_lines))
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

            ts = None
            action = "file_transfer"
            filename_obj = None
            detail = line

            usb_match = self._USB_FILE_PATTERN.match(line)
            bt_match = self._BT_FILE_PATTERN.match(line)
            generic_match = self._GENERIC_TRANSFER.match(line)

            if usb_match:
                ts_str, fname, target = usb_match.groups()
                filename_obj = fname
                detail = f"USB transfer: {fname} to {target}"
                action = "usb_transfer"
            elif bt_match:
                ts_str, fname, target = bt_match.groups()
                filename_obj = fname
                detail = f"Bluetooth transfer: {fname} to {target}"
                action = "bluetooth_transfer"
            elif generic_match:
                ts_str, rest = generic_match.groups()
                detail = rest
            else:
                continue

            if ts_str:
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    ts = ts.replace(tzinfo=timezone.utc)
                except ValueError:
                    ts = datetime.now(timezone.utc)
            else:
                ts = datetime.now(timezone.utc)

            events.append(ParsedEvent(
                timestamp=ts,
                source_type=self.source_type,
                action=action,
                object=filename_obj,
                detail=detail[:2000],
                raw_line=line[:5000],
            ))

        return events
