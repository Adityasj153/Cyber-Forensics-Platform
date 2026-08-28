import structlog
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base_models import LogEvent, CorrelationEdge, Entity
from app.ai_engine.correlation.entity_graph import build_entity_graph, persist_entities
from app.ai_engine.explainability.shap_explainer import explain_correlation

logger = structlog.get_logger()

MODEL_VERSION = "cross_device_v1"


def _pair_devices(devices: set) -> list[tuple[str, str]]:
    """Return device key pairs for correlation edges (deterministic ordering)."""
    ordered = sorted(devices)
    if len(ordered) >= 2:
        return [(ordered[0], ordered[1])]
    return []


async def run_cross_device_correlation(case_id: str, db: AsyncSession) -> list[dict]:
    graph, entities = await build_entity_graph(case_id, db)
    persisted_entities = await persist_entities(case_id, entities, db)

    edges_found = []

    # Find file hash appearing on multiple devices
    hash_nodes = [n for n in graph.nodes if graph.nodes[n].get("entity_type") == "hash"]
    for hash_node in hash_nodes:
        connected_devices = set()
        connected_files = set()
        evidence_events = []

        for neighbor in graph.neighbors(hash_node):
            node_data = graph.nodes[neighbor]
            if node_data.get("entity_type") == "device":
                connected_devices.add(neighbor)
            elif node_data.get("entity_type") == "file":
                connected_files.add(neighbor)

            edge_data = graph.edges[hash_node, neighbor]
            if "event_ids" in entities.get(neighbor, {}):
                evidence_events.extend(entities[neighbor]["events"][:10])

        if len(connected_devices) > 1:
            confidence = min(0.95, 0.6 + 0.1 * len(connected_devices))
            explanation = explain_correlation(
                relation_type="cross_device_file",
                entities={
                    "hash": hash_node,
                    "devices": list(connected_devices),
                    "files": list(connected_files),
                },
                evidence_count=len(evidence_events),
            )

            for a_key, b_key in _pair_devices(connected_devices):
                edge_record = {
                    "entity_a_key": a_key,
                    "entity_b_key": b_key,
                    "relation_type": "cross_device_file",
                    "confidence": confidence,
                    "evidence_event_ids": evidence_events[:50],
                    "explanation": explanation,
                }
                edges_found.append(edge_record)

    # Find file appearing on device + being transferred (USB/BT/email)
    file_nodes = [n for n in graph.nodes if graph.nodes[n].get("entity_type") == "file"]
    for file_node in file_nodes:
        connected_devices = set()
        for neighbor in graph.neighbors(file_node):
            if graph.nodes[neighbor].get("entity_type") == "device":
                connected_devices.add(neighbor)

        # Check if same file hash appears elsewhere
        for neighbor in list(graph.neighbors(file_node)):
            if graph.nodes[neighbor].get("entity_type") == "hash":
                for hash_neighbor in graph.neighbors(neighbor):
                    if graph.nodes[hash_neighbor].get("entity_type") == "device":
                        connected_devices.add(hash_neighbor)

        if len(connected_devices) > 1:
            confidence = 0.85
            explanation = explain_correlation(
                relation_type="file_transfer_chain",
                entities={
                    "file": file_node,
                    "devices": list(connected_devices),
                },
                evidence_count=0,
            )
            for a_key, b_key in _pair_devices(connected_devices):
                edge_record = {
                    "entity_a_key": a_key,
                    "entity_b_key": b_key,
                    "relation_type": "file_transfer_chain",
                    "confidence": confidence,
                    "evidence_event_ids": [],
                    "explanation": explanation,
                }
                edges_found.append(edge_record)

    # Find IP connected to multiple devices
    ip_nodes = [n for n in graph.nodes if graph.nodes[n].get("entity_type") == "ip"]
    for ip_node in ip_nodes:
        connected_devices = set()
        for neighbor in graph.neighbors(ip_node):
            if graph.nodes[neighbor].get("entity_type") == "device":
                connected_devices.add(neighbor)
            elif graph.nodes[neighbor].get("entity_type") == "actor":
                for actor_neighbor in graph.neighbors(neighbor):
                    if graph.nodes[actor_neighbor].get("entity_type") == "device":
                        connected_devices.add(actor_neighbor)

        if len(connected_devices) > 1:
            confidence = 0.75
            explanation = explain_correlation(
                relation_type="shared_ip",
                entities={
                    "ip": ip_node,
                    "devices": list(connected_devices),
                },
                evidence_count=0,
            )
            for a_key, b_key in _pair_devices(connected_devices):
                edge_record = {
                    "entity_a_key": a_key,
                    "entity_b_key": b_key,
                    "relation_type": "shared_ip",
                    "confidence": confidence,
                    "evidence_event_ids": [],
                    "explanation": explanation,
                }
                edges_found.append(edge_record)

    # Persist correlation edges, linking the actual correlated entities
    entity_map = {e.entity_type + ":" + e.value: e for e in persisted_entities}
    for edge_data in edges_found:
        a_key = edge_data.get("entity_a_key")
        b_key = edge_data.get("entity_b_key")
        entity_a = entity_map.get(a_key) if a_key else None
        entity_b = entity_map.get(b_key) if b_key else None

        if entity_a and entity_b:
            edge = CorrelationEdge(
                case_id=case_id,
                entity_a_id=entity_a.id,
                entity_b_id=entity_b.id,
                relation_type=edge_data["relation_type"],
                confidence=edge_data["confidence"],
                evidence_event_ids=edge_data["evidence_event_ids"],
                explanation_json=edge_data["explanation"],
                model_version=MODEL_VERSION,
            )
            db.add(edge)

    await db.flush()

    logger.info(
        "cross_device_correlation_complete",
        case_id=case_id,
        edges_found=len(edges_found),
    )

    return edges_found
