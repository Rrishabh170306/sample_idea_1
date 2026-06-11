from __future__ import annotations


FIND_SCHEMES_BY_STATE = """
MATCH (state:State {name: $state})-[:HAS_SCHEME]->(scheme:Scheme)
RETURN scheme
LIMIT $limit
"""

FIND_SIMILAR_SCHEMES = """
MATCH (scheme:Scheme {id: $scheme_id})-[:SIMILAR_TO]->(other:Scheme)
RETURN other
LIMIT $limit
"""

TRAVERSE_ELIGIBILITY = """
MATCH (scheme:Scheme {id: $scheme_id})-[:HAS_ELIGIBILITY]->(rule:EligibilityRule)
RETURN rule
"""
