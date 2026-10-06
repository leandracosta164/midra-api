"""Phase 5.40 — private MIDRA Engineering project workspace projection."""
from __future__ import annotations


WORKSPACE_SECTIONS = (
    "OVERVIEW",
    "PROPERTY",
    "INTELLIGENCE",
    "MAPS",
    "DOCUMENTS",
    "ACCEPTED_SCOPE",
    "PROPOSAL",
    "HISTORY",
)


def build_engineering_project_workspace(
    *,
    project: dict,
    property_record: dict,
    intelligence: dict,
    maps: dict,
    documents: list[dict],
    proposal_artifact: dict,
    history: list[dict],
) -> dict:
    """Assemble one private workspace without duplicating shared MIDRA evidence."""
    if project.get("project_status") != "ACTIVE":
        raise ValueError("workspace requires an active Engineering project")

    _require_match("property_record_id", project, property_record)
    _require_match("analysis_id", project, intelligence)

    accepted_artifact_id = project.get("accepted_artifact_id")
    if accepted_artifact_id and proposal_artifact.get("artifact_id") != accepted_artifact_id:
        raise ValueError("proposal artifact does not match accepted project proposal")

    return {
        "visibility": "MIDRA_ENGINEERING_PRIVATE",
        "project_status": project["project_status"],
        "sections": {
            "OVERVIEW": {
                "client": project.get("client"),
                "project_goal": project.get("project_goal"),
                "project_status": project.get("project_status"),
            },
            "PROPERTY": {
                "property_record_id": project.get("property_record_id"),
                "record": dict(property_record),
            },
            "INTELLIGENCE": {
                "analysis_id": project.get("analysis_id"),
                "analysis_snapshot_id": project.get("analysis_snapshot_id"),
                "record": dict(intelligence),
                "source": "SHARED_MIDRA_PLATFORM",
            },
            "MAPS": _map_projection(maps),
            "DOCUMENTS": {
                "items": [dict(item) for item in documents],
                "source": "SHARED_MIDRA_PLATFORM",
            },
            "ACCEPTED_SCOPE": {
                "items": [dict(item) for item in project.get("scope_snapshot", [])],
                "total": project.get("proposal_total"),
                "frozen_from_accepted_proposal": True,
            },
            "PROPOSAL": {
                "proposal_id": project.get("proposal_id"),
                "release_id": project.get("release_id"),
                "artifact": dict(proposal_artifact),
                "pdf_sha256": project.get("accepted_pdf_sha256"),
            },
            "HISTORY": {
                "items": [dict(item) for item in history],
            },
        },
    }


def _require_match(key: str, project: dict, record: dict) -> None:
    expected = project.get(key)
    actual = record.get(key)
    if expected and actual != expected:
        raise ValueError(f"{key} does not match Engineering project")


def _map_projection(maps: dict) -> dict:
    return {
        "midra_integrated_map": maps.get("midra_integrated_map"),
        "zoning_map": maps.get("zoning_map"),
        "tax_map": maps.get("tax_map"),
        "original_downloads_available": {
            "zoning_map": bool((maps.get("zoning_map") or {}).get("download_url")),
            "tax_map": bool((maps.get("tax_map") or {}).get("download_url")),
        },
        "source": "SHARED_MIDRA_PLATFORM",
    }


def workspace_section(*, workspace: dict, section: str) -> dict:
    if workspace.get("visibility") != "MIDRA_ENGINEERING_PRIVATE":
        raise ValueError("invalid Engineering workspace visibility")
    if section not in WORKSPACE_SECTIONS:
        raise ValueError("unsupported workspace section")
    return dict(workspace["sections"][section])
