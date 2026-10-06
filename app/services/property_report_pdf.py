"""Client-ready MIDRA Property PDF report renderer."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import re

PAGE_HEIGHT=792
LEFT=48
TOP=56
BOTTOM=48

def _text(value: Any) -> str:
    return str(value or "").strip()

def _ascii(value: Any) -> str:
    text=_text(value)
    for old,new in {
        "\u2013":"-","\u2014":"-","\u2022":"-","\u00b7":" - ",
        "\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"'
    }.items():
        text=text.replace(old,new)
    return text.encode("latin-1","replace").decode("latin-1")

def _escape(value: Any) -> str:
    return _ascii(value).replace("\\","\\\\").replace("(","\\(").replace(")","\\)")

def _wrap(value: Any,width: int=88) -> list[str]:
    text=re.sub(r"\s+"," ",_ascii(value)).strip()
    if not text:
        return []
    lines=[]
    current=""
    for word in text.split(" "):
        if not current:
            current=word
        elif len(current)+len(word)+1<=width:
            current+=" "+word
        else:
            lines.append(current)
            current=word
    if current:
        lines.append(current)
    return lines

def _report_lines(bundle: dict[str,Any]) -> list[dict[str,Any]]:
    prop=dict(bundle.get("property_record") or {})
    analysis=dict(bundle.get("analysis_snapshot") or {})
    evidence=dict(bundle.get("master_evidence_package") or {})
    report=dict(bundle.get("customer_report") or {})
    verification=dict(evidence.get("verification_summary") or {})
    dynamic=dict(evidence.get("dynamic_intelligence_evidence") or {})
    screening=dict(evidence.get("screening_evidence") or {})
    zoning_candidate=dict(evidence.get("zoning_candidate_evidence") or {})
    lines=[]

    def add(kind,text,indent=0):
        lines.append({"kind":kind,"text":text,"indent":indent})
    def body(text,indent=0):
        for row in _wrap(text):
            add("body",row,indent)
    def kv(label,value):
        body(f"{label}: {_text(value) or 'Not established'}")

    add("title","MIDRA Property Intelligence Report")
    add("meta",f"Report profile: {_text(bundle.get('customer_report_profile') or 'PRELIMINARY').upper()}")
    add("meta",f"Analysis ID: {_text(bundle.get('analysis_id')) or 'Not reported'}")
    add("meta",f"Generated: {datetime.now(timezone.utc).isoformat()}")
    add("space","")

    add("heading","Property")
    kv("Address",prop.get("address"))
    kv("Municipality",prop.get("municipality"))
    kv("County",prop.get("county"))
    kv("Block / Lot",f"{_text(prop.get('block')) or 'Not established'} / {_text(prop.get('lot')) or 'Not established'}")
    kv("Project goal",bundle.get("project_goal") or analysis.get("project_goal") or analysis.get("requested_work"))

    add("heading","Zoning and Property Intelligence")
    zoning=dict(analysis.get("zoning") or {})
    kv("Established zoning",zoning.get("district") or zoning.get("zoning_district") or (analysis.get("property") or {}).get("zoning_district"))
    candidate_record=dict(((zoning_candidate.get("candidate") or {}).get("record") or {}))
    kv("Mapped zoning candidate",candidate_record.get("zoning_district"))
    if candidate_record:
        kv("Candidate status","VERIFY - candidate only" if zoning_candidate.get("candidate_only") is True else zoning_candidate.get("status"))

    if dynamic:
        add("heading","Statewide Dynamic Intelligence")
        dyn_zoning=dict(dynamic.get("zoning") or {})
        dyn_record=dict(((dyn_zoning.get("candidate") or {}).get("record") or {}))
        promotion=dict(dyn_zoning.get("promotion") or {})
        applicability=dict(dynamic.get("project_applicability") or {})
        approval=dict(dynamic.get("approval_pathway") or {})
        approval_candidate=dict(dynamic.get("approval_pathway_candidate") or {})
        kv("Dynamic zoning candidate",dyn_record.get("zoning_district"))
        kv("Promotion status",promotion.get("status"))
        kv("Promotion reason",promotion.get("reason"))
        kv("Project applicability",applicability.get("status"))
        pathway=approval.get("primary_pathway") or approval_candidate.get("primary_pathway")
        kv("Approval pathway",pathway or approval.get("status"))
        bodies=list(approval.get("reviewing_bodies") or []) or list(approval_candidate.get("reviewing_bodies") or [])
        kv("Reviewing bodies",", ".join(str(x) for x in bodies) if bodies else None)
        kv("Dynamic evidence status","Promotable" if dynamic.get("dynamic_promotable") is True else "VERIFY / candidate context")

    add("heading","Environmental Screening")
    for key,label in (("wetlands","Wetlands"),("flood","Flood")):
        item=dict(screening.get(key) or {})
        record=dict(item.get("screening") or item)
        source=dict(record.get("source") or item.get("source") or {})
        kv(label,record.get("screening_result") or record.get("status") or item.get("status"))
        if source:
            source_label=_text(source.get("dataset") or source.get("agency") or source.get("url"))
            kv(f"{label} source",source_label)
            kv(f"{label} source URL",source.get("url"))
            kv(f"{label} source currentness",source.get("current_status"))
            kv(f"{label} source retrieved",source.get("retrieved_at"))
            kv(f"{label} source last checked",source.get("last_checked_at"))
            currentness_note=_text(source.get("currentness_note"))
            if currentness_note:
                body(f"{label} currentness note: {currentness_note}",1)

    add("heading","Verification / VERIFY")
    items=verification.get("items")
    if isinstance(items,list) and items:
        for item in items:
            body(f"- {_text(item)}",1)
    else:
        body("No saved verification items were reported in this delivery bundle.")

    add("heading","Report Sections")
    sections=dict(report.get("sections") or {})
    if sections:
        for key,included in sections.items():
            body(f"- {key.replace('_',' ').title()}: {'Included' if included else 'Not included in this profile'}",1)
    else:
        body("No report-section manifest was returned.")

    add("heading","Evidence Sources")
    sources=list(evidence.get("sources") or [])
    if sources:
        for index,source in enumerate(sources[:40],start=1):
            if not isinstance(source,dict):
                continue
            label=_text(source.get("label") or source.get("title") or source.get("service") or source.get("source_type") or "Source")
            url=_text(source.get("source_url") or source.get("url"))
            authority=_text(source.get("authority_tier") or source.get("evidence_status"))
            suffix=" | ".join(x for x in (authority,url) if x)
            body(f"{index}. {label}" + (f" - {suffix}" if suffix else ""),1)
    else:
        body("No source index was returned in this report profile.")

    add("heading","Professional Boundary")
    boundary=dict(bundle.get("professional_boundary") or {})
    body(boundary.get("notice") or "MIDRA Property Intelligence is research and analysis context. It does not constitute engineer review or acceptance.")
    body("Mapped parcel, zoning, wetlands, flood, and other GIS evidence is reference/screening evidence unless explicitly established otherwise by the underlying authoritative source. VERIFY conditions remain unresolved until supported review confirms them.")
    return lines

def _height(kind: str) -> int:
    return {"title":24,"heading":20,"space":10}.get(kind,12)

def _font(kind: str) -> tuple[str,int]:
    if kind=="title": return "F2",18
    if kind=="heading": return "F2",12
    if kind=="meta": return "F1",8
    return "F1",9

def _paginate(lines):
    pages=[[]]
    y=PAGE_HEIGHT-TOP
    for item in lines:
        h=_height(item["kind"])
        if y-h<BOTTOM:
            pages.append([])
            y=PAGE_HEIGHT-TOP
        pages[-1].append(item)
        y-=h
    return pages

def _page_stream(page,page_no,total):
    y=PAGE_HEIGHT-TOP
    commands=[]
    for item in page:
        kind=item["kind"]
        if kind=="space":
            y-=_height(kind)
            continue
        font,size=_font(kind)
        x=LEFT+int(item.get("indent") or 0)*12
        commands.append(f"BT /{font} {size} Tf {x} {y} Td ({_escape(item.get('text'))}) Tj ET")
        y-=_height(kind)
    commands.append(f"BT /F1 7 Tf {LEFT} 28 Td ({_escape(f'MIDRA Property | Page {page_no} of {total}')}) Tj ET")
    return ("\n".join(commands)+"\n").encode("latin-1","replace")

def _build_pdf(pages) -> bytes:
    total=len(pages)
    page_ids=[5+i*2 for i in range(total)]
    kids=" ".join(f"{x} 0 R" for x in page_ids)
    objects=[
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {total} >>".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    for i,page in enumerate(pages):
        stream=_page_stream(page,i+1,total)
        content_id=6+i*2
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii"))
        objects.append(b"<< /Length %d >>\nstream\n"%len(stream)+stream+b"endstream")
    pdf=bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets=[0]
    for idx,obj in enumerate(objects,start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"));pdf.extend(obj);pdf.extend(b"\nendobj\n")
    xref=len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"));pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(pdf)

def render_property_report_pdf(*,delivery_bundle: dict[str,Any]) -> dict[str,Any]:
    if delivery_bundle.get("status")!="PROPERTY_DELIVERY_READY":
        raise ValueError("delivery bundle is not ready")
    prop=dict(delivery_bundle.get("property_record") or {})
    if not _text(prop.get("municipality")):
        raise ValueError("property municipality is required")
    pdf_bytes=_build_pdf(_paginate(_report_lines(delivery_bundle)))
    profile=_text(delivery_bundle.get("customer_report_profile") or "PRELIMINARY").lower()
    property_id=re.sub(r"[^A-Za-z0-9_-]+","-",_text(prop.get("property_record_id") or "property"))
    return {
        "filename":f"midra-property-{property_id}-{profile}-report.pdf",
        "mime_type":"application/pdf",
        "pdf_bytes":pdf_bytes,
        "pdf_sha256":sha256(pdf_bytes).hexdigest(),
        "report_profile":profile.upper(),
        "analysis_id":delivery_bundle.get("analysis_id"),
        "professional_boundary":{"engineer_reviewed":False,"engineer_accepted":False},
    }

def verify_property_report_pdf(*,rendered: dict[str,Any]) -> bool:
    data=rendered.get("pdf_bytes")
    expected=_text(rendered.get("pdf_sha256"))
    return isinstance(data,bytes) and data.startswith(b"%PDF-") and bool(expected) and sha256(data).hexdigest()==expected
