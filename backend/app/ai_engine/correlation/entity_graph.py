import structlog
import networkx as nx
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base_models import LogEvent, Entity

logger = structlog.get_logger()

MODEL_VERSION = "entity_graph_v1"


async def build_entity_graph(case_id: str, db: AsyncSession) -> nx.Graph:
    graph = nx.Graph()

    result = await db.execute(
        select(LogEvent).where(LogEvent.case_id == case_id).order_by(LogEvent.timestamp)
    )
    events = result.scalars().all()

    entities = {}

    for event in events:
        # Extract device entity
        if event.device_id:
            dev_key = f"device:{event.device_id}"
            if dev_key not in entities:
                entities[dev_key] = {
                    "type": "device",
                    "value": str(event.device_id),
                    "events": [],
                }
            entities[dev_key]["events"].append(str(event.id))
            graph.add_node(dev_key, entity_type="device", value=str(event.device_id))

        # Extract actor entity
        if event.actor:
            actor_key = f"actor:{event.actor}"
            if actor_key not in entities:
                entities[actor_key] = {
                    "type": "user",
                    "value": event.actor,
                    "events": [],
                }
            entities[actor_key]["events"].append(str(event.id))
            graph.add_node(actor_key, entity_type="user", value=event.actor)

        # Extract IP entity
        if event.ip_address:
            ip_key = f"ip:{event.ip_address}"
            if ip_key not in entities:
                entities[ip_key] = {
                    "type": "ip",
                    "value": event.ip_address,
                    "events": [],
                }
            entities[ip_key]["events"].append(str(event.id))
            graph.add_node(ip_key, entity_type="ip", value=event.ip_address)

        # Extract file/hash entity
        if event.file_hash:
            hash_key = f"hash:{event.file_hash}"
            if hash_key not in entities:
                entities[hash_key] = {
                    "type": "hash",
                    "value": event.file_hash,
                    "events": [],
                }
            entities[hash_key]["events"].append(str(event.id))
            graph.add_node(hash_key, entity_type="hash", value=event.file_hash)

        # Extract file name entity (from object field when it looks like a filename)
        if event.object and _looks_like_filename(event.object):
            file_key = f"file:{event.object}"
            if file_key not in entities:
                entities[file_key] = {
                    "type": "file",
                    "value": event.object,
                    "events": [],
                }
            entities[file_key]["events"].append(str(event.id))
            graph.add_node(file_key, entity_type="file", value=event.object)

            # Connect file to its hash if both exist
            if event.file_hash:
                hash_key = f"hash:{event.file_hash}"
                graph.add_edge(file_key, hash_key, relation="has_hash", weight=1.0)

        # Build edges: device-actor, device-ip, device-file connections
        if event.device_id:
            dev_key = f"device:{event.device_id}"
            if event.actor:
                graph.add_edge(dev_key, f"actor:{event.actor}", relation="actor_on_device", weight=0.8)
            if event.ip_address:
                graph.add_edge(dev_key, f"ip:{event.ip_address}", relation="network_activity", weight=0.7)
            if event.object and _looks_like_filename(event.object):
                graph.add_edge(dev_key, f"file:{event.object}", relation="file_on_device", weight=0.9)

    logger.info(
        "entity_graph_built",
        case_id=case_id,
        nodes=graph.number_of_nodes(),
        edges=graph.number_of_edges(),
        events_processed=len(events),
    )

    return graph, entities


def _looks_like_filename(value: str) -> bool:
    if not value or len(value) > 500:
        return False
    extensions = (".xlsx", ".docx", ".pdf", ".exe", ".zip", ".txt", ".jpg", ".png", ".csv", ".locked")
    lower = value.lower()
    return any(lower.endswith(ext) for ext in extensions)


async def persist_entities(case_id: str, entities: dict, db: AsyncSession) -> list[Entity]:
    persisted = []
    for key, data in entities.items():
        entity = Entity(
            case_id=case_id,
            entity_type=data["type"],
            value=data["value"],
            metadata={"event_count": len(data["events"]), "event_ids": data["events"][:50]},
        )
        db.add(entity)
        persisted.append(entity)
    await db.flush()
    logger.info("entities_persisted", case_id=case_id, count=len(persisted))
    return persisted
