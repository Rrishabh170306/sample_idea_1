from __future__ import annotations

import os
import logging
from typing import Any

from app.graph.knowledge_graph import GraphBuilder, NodeType, RelationType

logger = logging.getLogger(__name__)


class GraphIngestor:
    """Ingests graph data into Neo4j using the async driver.

    Builds an in-memory GraphBuilder representation from scheme dicts,
    exports it as parameterised Cypher, and runs it against Neo4j.
    Falls back gracefully if Neo4j is unavailable.
    """

    def __init__(self, uri: str | None = None, auth: tuple[str, str] | None = None):
        self.uri = uri or os.getenv("NEO4J_URI") or "bolt://neo4j:7687"
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

    def _get_driver(self):
        """Return an AsyncGraphDatabase driver, or None if unavailable."""
        try:
            from neo4j import AsyncGraphDatabase
        except ImportError:
            logger.warning("neo4j package not installed; skipping graph ingestion")
            return None
        if self.auth:
            return AsyncGraphDatabase.driver(self.uri, auth=self.auth)
        return AsyncGraphDatabase.driver(self.uri)

    async def _run_cypher(self, statements: list[str]) -> None:
        """Run a list of Cypher statements in a single session."""
        driver = self._get_driver()
        if driver is None:
            return
        try:
            async with driver.session() as session:
                for stmt in statements:
                    s = stmt.strip()
                    if not s:
                        continue
                    try:
                        await session.run(s)
                    except Exception:
                        logger.exception("Cypher statement failed: %s", s[:200])
        except Exception:
            logger.exception("Neo4j session failed")
        finally:
            await driver.close()

    async def ensure_constraints(self) -> None:
        """Create uniqueness constraints and indexes on first startup."""
        constraints = [
            "CREATE CONSTRAINT scheme_id IF NOT EXISTS FOR (s:Scheme) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT state_id IF NOT EXISTS FOR (s:State) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT dept_id IF NOT EXISTS FOR (d:Department) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT ministry_id IF NOT EXISTS FOR (m:Ministry) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT beneficiary_id IF NOT EXISTS FOR (b:BeneficiaryType) REQUIRE b.id IS UNIQUE",
            "CREATE CONSTRAINT category_id IF NOT EXISTS FOR (c:Category) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
        ]
        driver = self._get_driver()
        if driver is None:
            return
        try:
            async with driver.session() as session:
                for c in constraints:
                    try:
                        await session.run(c)
                    except Exception:
                        logger.debug("Constraint may already exist: %s", c[:80])
        except Exception:
            logger.warning("Could not create Neo4j constraints — Neo4j may not be ready yet")
        finally:
            await driver.close()

    async def ingest_scheme(self, scheme: dict[str, Any]) -> None:
        """Ingest a single scheme dict into Neo4j using MERGE statements."""
        try:
            statements = self._build_cypher_statements(scheme)
            if not statements:
                logger.debug("No Cypher generated for scheme %s", scheme.get("scheme_id"))
                return
            await self._run_cypher(statements)
            logger.info("Graph ingested for scheme %s", scheme.get("scheme_id"))
        except Exception:
            logger.exception("Graph ingestion failed for scheme %s", scheme.get("scheme_id"))

    def _build_cypher_statements(self, scheme: dict[str, Any]) -> list[str]:
        """Build MERGE-based Cypher statements for a scheme dict.

        Using MERGE avoids duplicate nodes on re-ingestion.
        """
        stmts: list[str] = []
        scheme_id = scheme.get("scheme_id") or ""
        if not scheme_id:
            return stmts

        name = (scheme.get("name") or "Unknown").replace("'", "\\'")
        status = (scheme.get("status") or "active").replace("'", "\\'")
        official_url = (scheme.get("official_url") or "").replace("'", "\\'")
        state_raw = (scheme.get("state") or "Central").replace("'", "\\'")
        ministry_raw = (scheme.get("ministry") or "").replace("'", "\\'")
        department_raw = (scheme.get("department") or "").replace("'", "\\'")

        # Scheme node
        stmts.append(
            f"MERGE (s:Scheme {{id: '{scheme_id}'}}) "
            f"SET s.name = '{name}', s.status = '{status}', s.official_url = '{official_url}'"
        )

        # State node + relationship
        state_id = state_raw.upper().replace(" ", "_")
        stmts.append(f"MERGE (st:State {{id: '{state_id}'}}) SET st.name = '{state_raw}'")
        stmts.append(
            f"MATCH (st:State {{id: '{state_id}'}}), (s:Scheme {{id: '{scheme_id}'}}) "
            f"MERGE (st)-[:HAS_SCHEME]->(s)"
        )

        # Ministry node + relationship
        if ministry_raw:
            min_id = ministry_raw.lower().replace(" ", "_")
            stmts.append(f"MERGE (m:Ministry {{id: '{min_id}'}}) SET m.name = '{ministry_raw}'")
            stmts.append(
                f"MATCH (m:Ministry {{id: '{min_id}'}}), (s:Scheme {{id: '{scheme_id}'}}) "
                f"MERGE (m)-[:MANAGES]->(s)"
            )

        # Department node + relationship
        if department_raw:
            dept_id = department_raw.lower().replace(" ", "_")
            stmts.append(f"MERGE (d:Department {{id: '{dept_id}'}}) SET d.name = '{department_raw}'")
            stmts.append(
                f"MATCH (d:Department {{id: '{dept_id}'}}), (s:Scheme {{id: '{scheme_id}'}}) "
                f"MERGE (d)-[:MANAGES]->(s)"
            )

        # Beneficiary type nodes
        for beneficiary in scheme.get("target_beneficiaries") or []:
            b = str(beneficiary).lower().replace("'", "\\'").replace(" ", "_")
            stmts.append(f"MERGE (b:BeneficiaryType {{id: '{b}'}}) SET b.type = '{b}'")
            stmts.append(
                f"MATCH (b:BeneficiaryType {{id: '{b}'}}), (s:Scheme {{id: '{scheme_id}'}}) "
                f"MERGE (b)-[:ELIGIBLE_FOR]->(s)"
            )

        # Document nodes
        for doc in scheme.get("documents_required") or []:
            if isinstance(doc, dict):
                doc_type = str(doc.get("type", "general")).replace("'", "\\'")
                doc_name = str(doc.get("name", "")).replace("'", "\\'")
            else:
                doc_type = "general"
                doc_name = str(doc).replace("'", "\\'")
            if doc_name:
                doc_id = f"{doc_type}_{doc_name}".lower().replace(" ", "_")
                stmts.append(
                    f"MERGE (doc:Document {{id: '{doc_id}'}}) "
                    f"SET doc.type = '{doc_type}', doc.name = '{doc_name}'"
                )
                stmts.append(
                    f"MATCH (s:Scheme {{id: '{scheme_id}'}}), (doc:Document {{id: '{doc_id}'}}) "
                    f"MERGE (s)-[:REQUIRES_DOCUMENT]->(doc)"
                )

        # Category (caste/social) nodes
        eligibility = scheme.get("eligibility") or {}
        caste_categories = eligibility.get("caste_category") or []
        for cat in caste_categories:
            cat_id = str(cat).lower().replace("'", "\\'").replace(" ", "_")
            stmts.append(f"MERGE (c:Category {{id: '{cat_id}'}}) SET c.name = '{cat}'")
            stmts.append(
                f"MATCH (s:Scheme {{id: '{scheme_id}'}}), (c:Category {{id: '{cat_id}'}}) "
                f"MERGE (s)-[:TARGETS_CATEGORY]->(c)"
            )

        return stmts

    async def ingest_relationships(self, relationships: list[dict[str, Any]]) -> None:
        """Ingest explicit relationship dicts into Neo4j."""
        stmts: list[str] = []
        for rel in relationships:
            src = str(rel.get("source_id", "")).replace("'", "\\'")
            tgt = str(rel.get("target_id", "")).replace("'", "\\'")
            rel_type = str(rel.get("type", "RELATED_TO")).upper()
            if src and tgt:
                stmts.append(
                    f"MATCH (a {{id: '{src}'}}), (b {{id: '{tgt}'}}) "
                    f"MERGE (a)-[:{rel_type}]->(b)"
                )
        if stmts:
            await self._run_cypher(stmts)

    async def query_schemes_for_profile(
        self,
        state: str,
        occupation: str | None = None,
        category: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Query Neo4j for schemes matching a user profile."""
        driver = self._get_driver()
        if driver is None:
            return []

        state_id = state.upper().replace(" ", "_")
        cypher = (
            f"MATCH (st:State {{id: '{state_id}'}})-[:HAS_SCHEME]->(s:Scheme) "
            f"RETURN s.id AS scheme_id, s.name AS name, s.status AS status, "
            f"s.official_url AS official_url LIMIT {top_k}"
        )
        results: list[dict[str, Any]] = []
        try:
            async with driver.session() as session:
                records = await session.run(cypher)
                async for record in records:
                    results.append(dict(record))
        except Exception:
            logger.exception("Neo4j query failed")
        finally:
            await driver.close()
        return results
