from datetime import datetime, timezone
import csv
import io
import json
import re

from app.ingestion.parsers.base import BaseParser, ParsedEvent


def normalize_hash(value):
    """Normalize a file hash to fit the file_hash String(64) column.

    Hashes are treated as 64-char sha256 hex strings. Any longer value (e.g. a
    66-char odd-length hex in some sources) is truncated to 64 chars to match
    the behavior of the windows_evtx and android parsers.
    """
    if not value:
        return None
    return str(value)[:64].lower()


class NetworkGenericParser(BaseParser):
    source_type = "network_generic"

    _IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _TIMESTAMP_PATTERN = re.compile(
        r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
    )

    def detect(self, filename: str, data: bytes) -> bool:
        lower = filename.lower()
        if any(ext in lower for ext in [".csv", ".json", ".log", ".pcap", ".firewall", ".isp", ".network"]):
            return True
        try:
            text = data.decode("utf-8", errors="replace")
            first_500 = text[:500]
            if self._IP_PATTERN.search(first_500):
                return True
            if self._TIMESTAMP_PATTERN.search(first_500):
                return True
        except Exception:
            pass
        return False

    def parse(self, data: bytes) -> list[ParsedEvent]:
        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            text = data.decode("latin-1", errors="replace")

        text = text.strip()
        if not text:
            return []

        if text.startswith("{") or text.startswith("["):
            return self._parse_json(text)
        elif "," in text.split("\n")[0] if text.split("\n") else False:
            return self._parse_csv(text)
        else:
            return self._parse_plaintext(text)

    def _parse_json(self, text: str) -> list[ParsedEvent]:
        events = []
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                events.extend(self._parse_json_item(item))
        except json.JSONDecodeError:
            return self._parse_plaintext(text)
        return events

    def _parse_json_item(self, item: dict) -> list[ParsedEvent]:
        # Flatten nested event arrays (timeline_events / events / logs)
        for nested_key in ("timeline_events", "events", "logs", "entries"):
            nested = item.get(nested_key)
            if isinstance(nested, list):
                return [
                    ev
                    for sub in nested
                    for ev in self._parse_json_item(sub) if isinstance(sub, dict)
                ]
        # Handle a plain flat event
        ts = self._extract_timestamp(item)
        ip = item.get("ip_address") or item.get("src_ip") or item.get("source_ip") or item.get("dest_ip")
        action = item.get("action") or item.get("event") or "network_event"
        file_hash = item.get("hash") or item.get("sha256") or item.get("file_hash")
        obj = item.get("object") or item.get("dest_ip") or item.get("destination") or item.get("dst")
        if not obj and "detail" in item:
            obj = item.get("detail")
        return [ParsedEvent(
            timestamp=ts,
            source_type=self.source_type,
            actor=item.get("actor")
            or item.get("source")
            or item.get("src_ip")
            or item.get("src")
            or item.get("device"),
            action=action,
            object=obj,
            ip_address=ip,
            file_hash=normalize_hash(file_hash),
            detail=item.get("detail") or json.dumps(item)[:2000],
            raw_line=json.dumps(item)[:5000],
            extra=item,
        )]

    def _parse_csv(self, text: str) -> list[ParsedEvent]:
        events = []
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            ts = self._extract_timestamp(row)
            events.append(ParsedEvent(
                timestamp=ts,
                source_type=self.source_type,
                actor=row.get("src_ip") or row.get("source") or row.get("src"),
                action=row.get("action") or row.get("event") or "network_event",
                object=row.get("dest_ip") or row.get("destination") or row.get("dst"),
                ip_address=row.get("src_ip") or row.get("source_ip"),
                file_hash=normalize_hash(row.get("hash") or row.get("sha256")),
                detail=str(dict(row))[:2000],
                raw_line=str(dict(row))[:5000],
                extra=dict(row),
            ))
        return events

    def _parse_plaintext(self, text: str) -> list[ParsedEvent]:
        events = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            ts = datetime.now(timezone.utc)
            ts_match = self._TIMESTAMP_PATTERN.search(line)
            if ts_match:
                try:
                    ts_str = ts_match.group(1)
                    ts_str = ts_str.replace("Z", "+00:00")
                    ts = datetime.fromisoformat(ts_str)
                except ValueError:
                    ts = datetime.now(timezone.utc)

            ips = self._IP_PATTERN.findall(line)
            action = "network_event"
            lower_line = line.lower()
            if "block" in lower_line or "deny" in lower_line:
                action = "connection_blocked"
            elif "accept" in lower_line or "allow" in lower_line:
                action = "connection_allowed"
            elif "syn" in lower_line:
                action = "connection_attempt"
            elif "dns" in lower_line:
                action = "dns_query"

            events.append(ParsedEvent(
                timestamp=ts,
                source_type=self.source_type,
                actor=ips[0] if ips else None,
                action=action,
                object=ips[1] if len(ips) > 1 else None,
                ip_address=ips[0] if ips else None,
                detail=line[:2000],
                raw_line=line[:5000],
            ))

        return events

    def _extract_timestamp(self, data: dict) -> datetime:
        for key in ("timestamp", "time", "datetime", "@timestamp", "ts", "date"):
            if key in data:
                try:
                    val = str(data[key]).replace("Z", "+00:00")
                    return datetime.fromisoformat(val)
                except (ValueError, TypeError):
                    continue
        return datetime.now(timezone.utc)
