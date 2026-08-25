import structlog
from app.ingestion.parsers.base import BaseParser, ParsedEvent

logger = structlog.get_logger()

_registry: list[BaseParser] = []


def register_parser(parser: BaseParser) -> None:
    _registry.append(parser)
    logger.info("parser_registered", source_type=parser.source_type, parser=type(parser).__name__)


def get_all_parsers() -> list[BaseParser]:
    return list(_registry)


def detect_format(filename: str, data: bytes) -> BaseParser | None:
    for parser in _registry:
        try:
            if parser.detect(filename, data):
                logger.info(
                    "format_detected",
                    filename=filename,
                    source_type=parser.source_type,
                    parser=type(parser).__name__,
                )
                return parser
        except Exception:
            logger.warning(
                "parser_detect_error",
                parser=type(parser).__name__,
                filename=filename,
                exc_info=True,
            )
    logger.warning("format_unknown", filename=filename)
    return None


def parse_file(filename: str, data: bytes) -> list[ParsedEvent]:
    parser = detect_format(filename, data)
    if parser is None:
        raise ValueError(f"Unsupported log format: {filename}")
    return parser.parse(data)
