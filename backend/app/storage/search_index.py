import structlog
from elasticsearch import Elasticsearch

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

INDEX_NAME = "log_events"

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "case_id": {"type": "keyword"},
            "device_id": {"type": "keyword"},
            "artifact_id": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "source_type": {"type": "keyword"},
            "actor": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "action": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "object": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "ip_address": {"type": "ip"},
            "file_hash": {"type": "keyword"},
            "detail": {"type": "text"},
            "raw_line": {"type": "text"},
        }
    }
}


def _get_client() -> Elasticsearch:
    return Elasticsearch(settings.ELASTICSEARCH_URL)


def ensure_index(client: Elasticsearch | None = None) -> None:
    client = client or _get_client()
    if not client.indices.exists(index=INDEX_NAME):
        client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
        logger.info("elasticsearch_index_created", index=INDEX_NAME)


def index_log_event(event: dict, client: Elasticsearch | None = None) -> None:
    client = client or _get_client()
    ensure_index(client)
    client.index(index=INDEX_NAME, id=event["id"], body=event)


def index_log_events_bulk(events: list[dict], client: Elasticsearch | None = None) -> None:
    if not events:
        return
    client = client or _get_client()
    ensure_index(client)

    actions = []
    for event in events:
        actions.append({"index": {"_index": INDEX_NAME, "_id": event["id"]}})
        actions.append(event)

    client.bulk(operations=actions, refresh=True)
    logger.info("elasticsearch_bulk_indexed", count=len(events))


def search_log_events(
    case_id: str,
    query: str | None = None,
    source_type: str | None = None,
    action: str | None = None,
    device_id: str | None = None,
    ip_address: str | None = None,
    timestamp_from: str | None = None,
    timestamp_to: str | None = None,
    from_: int = 0,
    size: int = 50,
    client: Elasticsearch | None = None,
) -> dict:
    client = client or _get_client()
    ensure_index(client)

    must = [{"term": {"case_id": case_id}}]
    filter_clauses = []

    if query:
        must.append({
            "multi_match": {
                "query": query,
                "fields": ["actor^2", "action^2", "object^2", "detail"],
            }
        })
    if source_type:
        filter_clauses.append({"term": {"source_type": source_type}})
    if action:
        filter_clauses.append({"term": {"action.keyword": action}})
    if device_id:
        filter_clauses.append({"term": {"device_id": device_id}})
    if ip_address:
        filter_clauses.append({"term": {"ip_address": ip_address}})
    if timestamp_from or timestamp_to:
        range_clause = {"range": {"timestamp": {}}}
        if timestamp_from:
            range_clause["range"]["timestamp"]["gte"] = timestamp_from
        if timestamp_to:
            range_clause["range"]["timestamp"]["lte"] = timestamp_to
        filter_clauses.append(range_clause)

    body = {
        "query": {
            "bool": {
                "must": must,
                "filter": filter_clauses,
            }
        },
        "sort": [{"timestamp": {"order": "asc"}}],
        "from": from_,
        "size": size,
    }

    result = client.search(index=INDEX_NAME, body=body)
    return {
        "total": result["hits"]["total"]["value"],
        "events": [hit["_source"] for hit in result["hits"]["hits"]],
    }
