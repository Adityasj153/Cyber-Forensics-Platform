from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ParsedEvent:
    timestamp: datetime | None = None
    source_type: str = ""
    actor: str | None = None
    action: str = ""
    object: str | None = None
    ip_address: str | None = None
    file_hash: str | None = None
    detail: str | None = None
    raw_line: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    source_type: str = ""

    @abstractmethod
    def detect(self, filename: str, data: bytes) -> bool:
        """Return True if this parser can handle the given file."""
        ...

    @abstractmethod
    def parse(self, data: bytes) -> list[ParsedEvent]:
        """Parse raw file bytes into a list of ParsedEvent."""
        ...

    def parse_line(self, line: str) -> ParsedEvent | None:
        """Optional: parse a single line. Override for line-by-line parsers."""
        return None
