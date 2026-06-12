from __future__ import annotations

import os
import logging
from typing import Any

from app.graph.knowledge_graph import GraphBuilder

logger = logging.getLogger(__name__)


class GraphIngestor:
    """Ingests graph data into Neo4j using the async driver.

    This is best-effort and logs failures without raising to avoid breaking ingestion.
    """

    def __init__(self, uri: str | None = None, auth: tuple[str, str] | None = None):
        self.uri = uri or os.getenv("NEO4J_URI") or "bolt://neo4j:7687"
        # If auth tuple provided, use it; otherwise parse NEO4J_AUTH env var
        if auth:
            self.auth = auth
        else:
            neo_auth = os.getenv("NEO4J_AUTH")
            user = os.getenv("NEO4J_USER")
            pwd = os.getenv("NEO4J_PASSWORD")
            if user and pwd:
                self.auth = (user, pwd)
            elif neo_auth and "/" in neo_auth:
                u, p = neo_auth.split("/", 1)
                self.auth = (u, p)
            else:
                self.auth = None

    async def ingest_scheme(self, scheme: dict[str, Any]) -> None:
        try:
            builder = GraphBuilder()
            builder.build_from_scheme(scheme)
            cypher = builder.export_to_cypher()

            # If there is nothing to run, return
            if not cypher.strip():
                logger.debug("No Cypher generated for scheme %s", scheme.get("scheme_id"))
                return

            # Import neo4j lazily
            try:
                from neo4j import AsyncGraphDatabase
            except Exception:
                logger.exception("Neo4j driver not available; skipping graph ingestion")
                return

            driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth) if self.auth else AsyncGraphDatabase.driver(self.uri)

            async with driver.session() as session:
                # Execute each statement separately to make debugging easier
                for stmt in cypher.splitlines():
                    s = stmt.strip()
                    if not s:
                        continue
                    try:
                        await session.run(s)
                    except Exception:
                        logger.exception("Failed to execute Cypher statement: %s", s)

            await driver.close()
            logger.info("Graph ingested for scheme %s", scheme.get("scheme_id"))
        except Exception as exc:
            logger.exception("Graph ingestion failed: %s", exc)

    async def ingest_relationships(self, relationships: list[dict[str, Any]]) -> None:
        # Simple helper to ingest a list of relationships; relationships expected as dicts
        for rel in relationships:
            try:
                # Build minimal scheme-like dict for builder
                builder = GraphBuilder()
                builder.add_relationship(rel.get("source_id"), rel.get("target_id"), rel.get("type"))
                cypher = builder.export_to_cypher()
                if not cypher.strip():
                    continue
                try:
                    from neo4j import AsyncGraphDatabase
                except Exception:
                    logger.exception("Neo4j driver not available; skipping relationship ingestion")
                    return

                driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth) if self.auth else AsyncGraphDatabase.driver(self.uri)
                async with driver.session() as session:
                    for stmt in cypher.splitlines():
                        s = stmt.strip()
                        if not s:
                            continue
                        try:
                            await session.run(s)
                        except Exception:
                            logger.exception("Failed to execute Cypher statement: %s", s)
                await driver.close()
            except Exception:
                logger.exception("Failed to ingest relationship: %s", rel)
from __future__ import annotations

import os
import logging
from typing import Any

from app.graph.knowledge_graph import GraphBuilder

logger = logging.getLogger(__name__)


class GraphIngestor:
    """Ingests graph data into Neo4j using the async driver.

    This is best-effort and logs failures without raising to avoid breaking ingestion.
    """

    def __init__(self, uri: str | None = None, auth: tuple[str, str] | None = None):
        self.uri = uri or os.getenv("NEO4J_URI") or "bolt://neo4j:7687"
        # If auth tuple provided, use it; otherwise parse NEO4J_AUTH env var
        if auth:
            self.auth = auth
        else:
            neo_auth = os.getenv("NEO4J_AUTH")
            user = os.getenv("NEO4J_USER")
            pwd = os.getenv("NEO4J_PASSWORD")
            if user and pwd:
                self.auth = (user, pwd)
            elif neo_auth and "/" in neo_auth:
                u, p = neo_auth.split("/", 1)
                self.auth = (u, p)
            else:
                self.auth = None

    async def ingest_scheme(self, scheme: dict[str, Any]) -> None:
        try:
            builder = GraphBuilder()
            builder.build_from_scheme(scheme)
            cypher = builder.export_to_cypher()

            # If there is nothing to run, return
            if not cypher.strip():
                logger.debug("No Cypher generated for scheme %s", scheme.get("scheme_id"))
                return

            # Import neo4j lazily
            try:
                from neo4j import AsyncGraphDatabase
            except Exception:
                logger.exception("Neo4j driver not available; skipping graph ingestion")
                return

            driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth) if self.auth else AsyncGraphDatabase.driver(self.uri)

            async with driver.session() as session:
                # Execute each statement separately to make debugging easier
                for stmt in cypher.splitlines():
                    s = stmt.strip()
                    if not s:
                        continue
                    try:
                        await session.run(s)
                    except Exception:
                        logger.exception("Failed to execute Cypher statement: %s", s)

            await driver.close()
            logger.info("Graph ingested for scheme %s", scheme.get("scheme_id"))
        except Exception as exc:
            logger.exception("Graph ingestion failed: %s", exc)

    async def ingest_relationships(self, relationships: list[dict[str, Any]]) -> None:
        # Simple helper to ingest a list of relationships; relationships expected as dicts
        for rel in relationships:
            try:
                # Build minimal scheme-like dict for builder
                builder = GraphBuilder()
                builder.add_relationship(rel.get("source_id"), rel.get("target_id"), rel.get("type"))
                cypher = builder.export_to_cypher()
                if not cypher.strip():
                    continue
                try:
                    from neo4j import AsyncGraphDatabase
                except Exception:
                    logger.exception("Neo4j driver not available; skipping relationship ingestion")
                    return

                driver = AsyncGraphDatabase.driver(self.uri, auth=self.auth) if self.auth else AsyncGraphDatabase.driver(self.uri)
                async with driver.session() as session:
                    for stmt in cypher.splitlines():
                        s = stmt.strip()
                        if not s:
                            continue
                        try:
                            await session.run(s)
                        except Exception:
                            logger.exception("Failed to execute Cypher statement: %s", s)
                await driver.close()
            except Exception:
                logger.exception("Failed to ingest relationship: %s", rel)
