"""Phase 5.32 PDF-ready artifact contract for MIDRA Engineering proposals.

Transforms an intact Phase 5.31 release snapshot into a deterministic,
client-safe PDF render manifest.  This phase owns rendering instructions and
artifact identity only: it does not send email, accept a proposal, bill a
client, or expose private pricing / MIDRA Intelligence internals.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any

from app.services.engineering_proposal_release import verify_proposal_release_snapshot


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_filename_part(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", _text(value)).strip("._-")
    return text or "proposal"


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def build_proposal_pdf_artifact_manifest(*, release: dict[str, Any]) -> dict[str, Any]:
    """Build the immutable instructions for rendering one approved proposal PDF.

    The Phase 5.31 release remains the source of truth.  The document model is
    copied without enrichment from private pricing, evidence, or analysis data.
    """
    if not verify_proposal_release_snapshot(release=release):
        raise ValueError("proposal release snapshot failed integrity verification")
    if release.get("release_type") != "MIDRA_ENGINEERING_PROPOSAL_RELEASE":
        raise ValueError("unsupported release type")

    document = deepcopy(release.get("document_model") or {})
    if document.get("document_type") != "MIDRA_ENGINEERING_PROPOSAL":
        raise ValueError("release does not contain a MIDRA Engineering proposal")
    if document.get("status") != "APPROVED_READY_TO_SEND":
        raise ValueError("only an approved proposal release can produce a PDF artifact")

    header = document.get("header") or {}
    proposal_number = _text(header.get("proposal_number"))
    proposal_date = _text(header.get("date"))
    if not proposal_number or not proposal_date:
        raise ValueError("proposal number and date are required for PDF rendering")

    # Reassert the product layout contract at the artifact boundary.
    if header.get("logo_position") != "top_left":
        raise ValueError("MIDRA Engineering logo must be top-left")
    if header.get("proposal_number_position") != "top_right" or header.get("date_position") != "top_right":
        raise ValueError("proposal number and date must be top-right")
    if header.get("title") != "PROPOSAL" or header.get("title_position") != "center_below_header":
        raise ValueError("PROPOSAL title must be centered below the header")

    scope = document.get("scope_of_services") or []
    if not scope:
        raise ValueError("proposal must contain scope of services")
    for service in scope:
        if set(service.keys()) != {"service", "price"}:
            raise ValueError("client scope rows may contain only service and price")

    release_id = _text(release.get("release_id"))
    content_sha = _text(release.get("content_sha256"))
    if not release_id or not content_sha:
        raise ValueError("release identity is incomplete")

    filename = f"MIDRA_Engineering_Proposal_{_safe_filename_part(proposal_number)}.pdf"
    render_payload = {
        "release_id": release_id,
        "release_content_sha256": content_sha,
        "document_model": document,
        "layout": {
            "page_size": "LETTER",
            "logo": {"position": "top_left"},
            "proposal_metadata": {"position": "top_right", "fields": ["proposal_number", "date"]},
            "title": {"text": "PROPOSAL", "position": "center_below_header"},
            "scope": {"descriptions_allowed": False, "show_individual_prices": True, "show_total": True},
            "sections_after_scope": ["EXCLUSIONS / ADDITIONAL SERVICES", "TERMS", "ACCEPT PROPOSAL"],
        },
    }

    return {
        "artifact_type": "MIDRA_ENGINEERING_PROPOSAL_PDF",
        "release_id": release_id,
        "proposal_number": proposal_number,
        "filename": filename,
        "mime_type": "application/pdf",
        "render_payload": render_payload,
        "render_payload_sha256": _canonical_sha256(render_payload),
        "client_safe": True,
        "immutable_source_release": True,
        "transport": {
            "sent": False,
            "automatic_send": False,
            "requires_separate_authorized_send_action": True,
        },
    }


def verify_proposal_pdf_artifact_manifest(*, artifact: dict[str, Any]) -> bool:
    payload = artifact.get("render_payload")
    expected = _text(artifact.get("render_payload_sha256"))
    if not isinstance(payload, dict) or not expected:
        return False
    return _canonical_sha256(payload) == expected
