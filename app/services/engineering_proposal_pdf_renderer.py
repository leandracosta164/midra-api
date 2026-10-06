"""Phase 5.33 binary PDF renderer for approved MIDRA Engineering proposals.

Consumes only an intact Phase 5.32 PDF artifact manifest and emits deterministic,
client-safe PDF bytes. Rendering is deliberately transport-free: creating a PDF
never sends, accepts, bills, or mutates the approved proposal release.

The renderer uses only the Python standard library so MIDRA's backend does not
acquire a PDF-package runtime dependency at this boundary. The top-left brand
slot renders the MIDRA Engineering wordmark until a final graphic logo asset is
wired into the presentation layer; the placement contract remains top-left.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.services.engineering_proposal_pdf_artifact import verify_proposal_pdf_artifact_manifest

PAGE_W = 612
PAGE_H = 792
LEFT = 54
RIGHT = 558
TOP = 744
BOTTOM = 54


def _text(value: Any) -> str:
    return str(value or "").strip()


def _pdf_text(value: Any) -> str:
    # Core PDF Helvetica/Helvetica-Bold are WinAnsi. Normalize unsupported chars.
    text = _text(value).replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    text = text.encode("cp1252", "replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _money_text(value: Any) -> str:
    return _text(value)


def _wrap(text: str, max_chars: int) -> list[str]:
    words = _text(text).split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _content_stream(document: dict[str, Any]) -> bytes:
    header = document["header"]
    project = document.get("project") or {}
    prepared = document.get("prepared_for") or {}
    scope = document.get("scope_of_services") or []
    exclusions = document.get("exclusions_additional_services") or []
    terms = document.get("terms") or []

    cmds: list[str] = []

    def text(x: float, y: float, value: Any, *, size: int = 10, bold: bool = False) -> None:
        font = "F2" if bold else "F1"
        cmds.append(f"BT /{font} {size} Tf {x:.1f} {y:.1f} Td ({_pdf_text(value)}) Tj ET")

    def line(x1: float, y1: float, x2: float, y2: float, width: float = 0.6) -> None:
        cmds.append(f"{width:.1f} w {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S")

    # Header: locked product layout.
    text(LEFT, TOP, "MIDRA ENGINEERING", size=16, bold=True)  # top-left brand/logo slot
    text(414, TOP, f"Proposal No. {_text(header.get('proposal_number'))}", size=9, bold=True)
    text(455, TOP - 15, _text(header.get("date")), size=9)
    text(270, TOP - 55, "PROPOSAL", size=15, bold=True)
    line(LEFT, TOP - 68, RIGHT, TOP - 68)

    y = TOP - 92
    text(LEFT, y, "PROJECT", size=9, bold=True); y -= 15
    project_name = project.get("name") if isinstance(project, dict) else project
    project_address = project.get("address") if isinstance(project, dict) else ""
    text(LEFT, y, project_name, size=10, bold=True); y -= 14
    if _text(project_address):
        text(LEFT, y, project_address, size=9); y -= 22
    else:
        y -= 8

    text(LEFT, y, "Prepared For", size=9, bold=True); y -= 14
    prepared_name = prepared.get("name") if isinstance(prepared, dict) else prepared
    text(LEFT, y, prepared_name, size=10); y -= 30

    text(LEFT, y, "SCOPE OF SERVICES", size=11, bold=True); y -= 10
    line(LEFT, y, RIGHT, y); y -= 20
    for row in scope:
        service = _text(row.get("service"))
        price = _money_text(row.get("price"))
        text(LEFT, y, service, size=10)
        # Right aligned approximately using character width; values are short currency strings.
        x_price = RIGHT - max(42, len(price) * 5.4)
        text(x_price, y, price, size=10)
        y -= 19
    line(390, y + 7, RIGHT, y + 7); y -= 3
    text(LEFT, y, "TOTAL", size=10, bold=True)
    total = _money_text(document.get("total"))
    text(RIGHT - max(42, len(total) * 5.7), y, total, size=10, bold=True)
    y -= 31

    def section(title: str, items: list[Any], y: float) -> float:
        text(LEFT, y, title, size=10, bold=True); y -= 10
        line(LEFT, y, RIGHT, y); y -= 16
        for item in items:
            raw = item if isinstance(item, str) else _text(item)
            for idx, wrapped in enumerate(_wrap(raw, 92)):
                prefix = "- " if idx == 0 else "  "
                text(LEFT, y, prefix + wrapped, size=8)
                y -= 12
        return y - 15

    y = section("EXCLUSIONS / ADDITIONAL SERVICES", exclusions, y)
    y = section("TERMS", terms, y)

    # Acceptance block. Keep it client-facing and unsigned at render time.
    if y < 125:
        # This phase intentionally rejects overflow rather than silently creating
        # an incomplete/misleading proposal. Multi-page composition comes later.
        raise ValueError("proposal content exceeds single-page Phase 5.33 rendering capacity")
    text(245, y, "ACCEPT PROPOSAL", size=10, bold=True); y -= 28
    text(LEFT, y, "Client: ______________________________", size=9)
    text(365, y, "Date: ______________", size=9)

    # Footer identifies the professional-services product, not Intelligence internals.
    line(LEFT, BOTTOM + 15, RIGHT, BOTTOM + 15, 0.4)
    text(LEFT, BOTTOM, "MIDRA ENGINEERING", size=7, bold=True)
    text(445, BOTTOM, _text(header.get("proposal_number")), size=7)
    return ("\n".join(cmds) + "\n").encode("cp1252", "replace")


def _build_pdf(stream: bytes) -> bytes:
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>"
    )
    objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"endstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def render_proposal_pdf(*, artifact: dict[str, Any]) -> dict[str, Any]:
    """Render an intact Phase 5.32 artifact to actual PDF bytes, without transport."""
    if not verify_proposal_pdf_artifact_manifest(artifact=artifact):
        raise ValueError("proposal PDF artifact manifest failed integrity verification")
    if artifact.get("artifact_type") != "MIDRA_ENGINEERING_PROPOSAL_PDF":
        raise ValueError("unsupported proposal artifact type")
    if artifact.get("client_safe") is not True or artifact.get("immutable_source_release") is not True:
        raise ValueError("proposal artifact must be client-safe and release-backed")

    payload = artifact.get("render_payload") or {}
    document = payload.get("document_model") or {}
    layout = payload.get("layout") or {}
    if layout.get("logo", {}).get("position") != "top_left":
        raise ValueError("logo position contract violated")
    if layout.get("proposal_metadata", {}).get("position") != "top_right":
        raise ValueError("proposal metadata position contract violated")
    if layout.get("title") != {"text": "PROPOSAL", "position": "center_below_header"}:
        raise ValueError("proposal title position contract violated")

    pdf_bytes = _build_pdf(_content_stream(document))
    return {
        "render_type": "MIDRA_ENGINEERING_PROPOSAL_PDF_BINARY",
        "filename": artifact.get("filename"),
        "mime_type": "application/pdf",
        "pdf_bytes": pdf_bytes,
        "pdf_sha256": sha256(pdf_bytes).hexdigest(),
        "release_id": artifact.get("release_id"),
        "proposal_number": artifact.get("proposal_number"),
        "client_safe": True,
        "transport": {
            "sent": False,
            "automatic_send": False,
            "requires_separate_authorized_send_action": True,
        },
    }


def verify_rendered_proposal_pdf(*, rendered: dict[str, Any]) -> bool:
    data = rendered.get("pdf_bytes")
    expected = _text(rendered.get("pdf_sha256"))
    return isinstance(data, bytes) and data.startswith(b"%PDF-") and bool(expected) and sha256(data).hexdigest() == expected
