from __future__ import annotations

from typing import Any
from app.agents.state import AgentState


def compose_response(answer: str, citations: list[dict[str, Any]]) -> str:
    citation_block = "\n".join(f"- {citation['source_url']}" for citation in citations)
    if citation_block:
        return f"{answer}\n\nSources:\n{citation_block}"
    return answer


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _scheme_from_chunk(chunk: dict[str, Any]) -> dict[str, Any] | None:
    metadata = chunk.get("metadata", {}) or {}
    name = _clean_text(metadata.get("scheme_name"))
    content = _clean_text(chunk.get("content"))
    if not name and content.lower().startswith("scheme:"):
        name = content.split(":", 1)[1].strip()

    if not name:
        return None

    return {
        "scheme_id": _clean_text(metadata.get("id")),
        "name": name,
        "source": _clean_text(metadata.get("source")),
        "score": chunk.get("score", 0.0),
        "metadata": metadata,
    }


def _collect_schemes(state: AgentState) -> list[dict[str, Any]]:
    schemes: list[dict[str, Any]] = []
    seen: set[str] = set()

    for result in state.get("graph_results", []) or []:
        name = _clean_text(result.get("name"))
        scheme_id = _clean_text(result.get("scheme_id"))
        key = scheme_id or name.lower()
        if name and key not in seen:
            schemes.append(
                {
                    "scheme_id": scheme_id,
                    "name": name,
                    "source": _clean_text(result.get("source")),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}) or {},
                }
            )
            seen.add(key)

    for chunk in state.get("retrieved_chunks", []) or []:
        scheme = _scheme_from_chunk(chunk)
        if not scheme:
            continue
        key = scheme["scheme_id"] or scheme["name"].lower()
        if key not in seen:
            schemes.append(scheme)
            seen.add(key)

    return schemes


def _profile_phrase(profile: dict[str, Any]) -> str:
    details = []
    occupation = _clean_text(profile.get("occupation"))
    state = _clean_text(profile.get("state"))
    background = _clean_text(profile.get("background"))
    income = profile.get("income")

    if occupation:
        details.append(occupation.replace("_", " "))
    if state:
        details.append(f"in {state}")
    if background:
        details.append(f"from a {background} background")
    if income not in (None, ""):
        details.append(f"with declared income {income}")

    return ", ".join(details)


def _scheme_sentence(scheme: dict[str, Any]) -> str:
    name = scheme["name"]
    metadata = scheme.get("metadata", {}) or {}
    benefit_type = _clean_text(metadata.get("benefit_type"))
    benefit_amount = metadata.get("benefit_amount")

    if benefit_type and benefit_amount not in (None, ""):
        return f"{name} is relevant for {benefit_type.replace('_', ' ')} support of {benefit_amount}."
    if benefit_type:
        return f"{name} is relevant for {benefit_type.replace('_', ' ')} support."
    return f"{name} appears relevant from the available scheme data."


def _eligibility_sentence(eligibility: dict[str, Any]) -> str:
    if not eligibility:
        return ""

    summaries = []
    for scheme_id, result in eligibility.items():
        eligible = result.get("eligible")
        score = result.get("score")
        explanation = _clean_text(result.get("explanation"))
        status = "eligible" if eligible else "not confirmed eligible"
        score_text = f" with a rule score of {score}" if score is not None else ""
        if explanation:
            summaries.append(f"For {scheme_id}, eligibility is {status}{score_text}: {explanation}")
        else:
            summaries.append(f"For {scheme_id}, eligibility is {status}{score_text}.")

    return " ".join(summaries)


class ResponseAgent:
    def generate(self, state: AgentState) -> dict:
        q_type = state.get("query_type", "general")
        citations = state.get("citations", [])
        eligibility = state.get("eligibility_results", {})
        profile = state.get("user_profile", {}) or {}
        schemes = _collect_schemes(state)
        profile_context = _profile_phrase(profile)

        if q_type == "eligibility" and eligibility:
            scheme_names = ", ".join(scheme["name"] for scheme in schemes[:3])
            eligibility_text = _eligibility_sentence(eligibility)
            if scheme_names:
                answer = f"For your profile, {scheme_names} are the relevant schemes found. {eligibility_text}"
            else:
                answer = eligibility_text or "Eligibility could not be confirmed from the available scheme rules."
        elif q_type == "document":
            verification = "verified" if profile.get("document_verified") else "processed"
            answer = f"Your document details were {verification} and merged into the profile context used for scheme matching."
        elif schemes:
            names = ", ".join(scheme["name"] for scheme in schemes[:3])
            intro = f"For your profile ({profile_context}), " if profile_context else "From the available scheme data, "
            detail_sentences = " ".join(_scheme_sentence(scheme) for scheme in schemes[:3])
            answer = f"{intro}{names} appear relevant. {detail_sentences}"
        else:
            answer = "No matching schemes were found in the currently loaded repository data."
            
        final_response = compose_response(answer, citations)
        return {"response": final_response}
