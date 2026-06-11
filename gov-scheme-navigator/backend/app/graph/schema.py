from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NodeDefinition:
    label: str
    properties: list[str]


@dataclass(slots=True)
class RelationshipDefinition:
    start_label: str
    relationship_type: str
    end_label: str


GRAPH_NODES = [
    NodeDefinition("Scheme", ["id", "name", "status"]),
    NodeDefinition("State", ["name", "code"]),
    NodeDefinition("Department", ["name"]),
    NodeDefinition("Ministry", ["name"]),
    NodeDefinition("BeneficiaryType", ["type"]),
    NodeDefinition("Document", ["type", "name"]),
    NodeDefinition("EligibilityRule", ["field", "operator", "value"]),
    NodeDefinition("Category", ["name"]),
]

GRAPH_RELATIONSHIPS = [
    RelationshipDefinition("State", "HAS_SCHEME", "Scheme"),
    RelationshipDefinition("Ministry", "OVERSEES", "Department"),
    RelationshipDefinition("Department", "MANAGES", "Scheme"),
    RelationshipDefinition("BeneficiaryType", "ELIGIBLE_FOR", "Scheme"),
    RelationshipDefinition("Scheme", "REQUIRES_DOCUMENT", "Document"),
    RelationshipDefinition("Scheme", "HAS_ELIGIBILITY", "EligibilityRule"),
    RelationshipDefinition("Scheme", "TARGETS_CATEGORY", "Category"),
    RelationshipDefinition("Scheme", "SIMILAR_TO", "Scheme"),
    RelationshipDefinition("Scheme", "SUPERSEDES", "Scheme"),
]
