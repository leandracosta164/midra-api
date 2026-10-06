from __future__ import annotations

from typing import Any
from urllib.parse import unquote, urlparse, urlunparse
from posixpath import normpath
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import io
import re

import httpx

DCA_ZONING_DIRECTORY_XLSX = (
    "https://www.nj.gov/dca/library/home/Zoning_Information_Directory.xlsx"
)
DCA_DIRECTORY_PAGE = "https://www.nj.gov/dca/news/news/2023/20230613.shtml"
REQUEST_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
USER_AGENT = "MIDRA-Engineering-Property-Intelligence/1.0 (municipal-source-discovery)"


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _municipality_key(value: object) -> str:
    text = _normalize(value)
    text = re.sub(r"\b(city|township|borough|town|village|town of|city of)\b", " ", text)
    return " ".join(text.split())


def _is_url(value: object) -> bool:
    return str(value or "").strip().startswith(("https://", "http://"))


def _xml_text(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def _resolve_sheet_relationship(sheet_path: str, target: str) -> str:
    if target.startswith("http://") or target.startswith("https://"):
        return target
    if target.startswith("/"):
        return target.lstrip("/")
    base = sheet_path.rsplit("/", 1)[0]
    return normpath(f"{base}/{target}")


def _xlsx_rows(content: bytes) -> list[list[str]]:
    """Read XLSX tabular data, resolving worksheet hyperlinks when present."""
    ns = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with ZipFile(io.BytesIO(content)) as z:
        names = set(z.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = [_xml_text(si) for si in root.findall("m:si", ns)]

        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sheets = workbook.find("m:sheets", ns)
        if sheets is None:
            return []
        first = sheets[0]
        target = rel_map.get(first.attrib.get("{%s}id" % ns["r"]))
        if not target:
            return []
        sheet_path = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
        root = ET.fromstring(z.read(sheet_path))

        hyperlink_targets: dict[str, str] = {}
        sheet_rels_path = f"xl/worksheets/_rels/{sheet_path.rsplit('/', 1)[-1]}.rels"
        if sheet_rels_path in names:
            sheet_rels = ET.fromstring(z.read(sheet_rels_path))
            for rel in sheet_rels.findall("pr:Relationship", ns):
                rid = rel.attrib.get("Id")
                target = rel.attrib.get("Target")
                if rid and target:
                    hyperlink_targets[rid] = _resolve_sheet_relationship(sheet_path, target)

        hyperlinks: dict[str, str] = {}
        hyperlink_root = root.find("m:hyperlinks", ns)
        if hyperlink_root is not None:
            for link in hyperlink_root.findall("m:hyperlink", ns):
                ref = link.attrib.get("ref")
                rid = link.attrib.get("{%s}id" % ns["r"])
                target = hyperlink_targets.get(rid) if rid else link.attrib.get("location")
                if ref and target and (target.startswith("http://") or target.startswith("https://")):
                    hyperlinks[ref] = target

        rows: list[list[str]] = []
        for row in root.findall(".//m:sheetData/m:row", ns):
            vals: list[str] = []
            for cell in row.findall("m:c", ns):
                ref = cell.attrib.get("r", "")
                value = cell.find("m:v", ns)
                text = "" if value is None else value.text or ""
                if cell.attrib.get("t") == "s" and text:
                    try:
                        text = shared[int(text)]
                    except (ValueError, IndexError):
                        pass
                elif cell.attrib.get("t") == "inlineStr":
                    inline = cell.find("m:is", ns)
                    text = _xml_text(inline) if inline is not None else ""
                text = text.strip()
                # Prefer the actual external hyperlink target over a display/value string.
                if ref in hyperlinks:
                    text = hyperlinks[ref]
                vals.append(text)
            rows.append(vals)
        return rows


def _header_index(headers: list[str], predicate) -> int | None:
    for i, value in enumerate(headers):
        if predicate(_normalize(value)):
            return i
    return None



def _clean_source_url(value: object) -> str | None:
    url = str(value or "").strip()
    if not _is_url(url):
        return None
    parsed = urlparse(url)
    if not parsed.netloc:
        return None
    # Guard against malformed ArcGIS app links where a display label was appended to appid.
    if "appid=" in parsed.query:
        query = parsed.query
        prefix, appid = query.split("appid=", 1)
        if len(appid) > 32 and re.match(r"^[0-9a-fA-F]{32}", appid):
            tail = appid[32:]
            if tail and not tail.startswith("&"):
                query = prefix + "appid=" + appid[:32]
                return urlunparse(parsed._replace(query=query))
    return url

def _extract_sources(headers: list[str], values: list[str]) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for i, value in enumerate(values):
        value = _clean_source_url(value)
        if not value:
            continue
        label = headers[i] if i < len(headers) and headers[i] else f"source_{i + 1}"
        sources[label] = {
            "url": value.strip(),
            "source_type": "dca_zoning_information_directory_link",
            "authoritative": False,
            "discovered_from": DCA_DIRECTORY_PAGE,
        }
    return sources


def discover_municipality_sources(
    municipality: str | None,
    *,
    client: Any | None = None,
) -> dict[str, Any]:
    """Discover DCA-indexed municipal zoning source links without asserting legal validity."""
    requested = str(municipality or "").strip()
    if not requested:
        return {"status": "MUNICIPALITY_REQUIRED", "registered": False, "municipality": None, "sources": {}}

    close_client = False
    if client is None:
        client = httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
        close_client = True
    try:
        response = client.get(DCA_ZONING_DIRECTORY_XLSX)
        response.raise_for_status()
        rows = _xlsx_rows(response.content)
        if not rows:
            return {"status": "DCA_SOURCE_INDEX_UNAVAILABLE", "registered": False, "municipality": requested, "sources": {}}

        header_row = max(range(min(10, len(rows))), key=lambda i: sum(bool(x) for x in rows[i]))
        headers = rows[header_row]
        municipality_idx = _header_index(headers, lambda h: "municip" in h and ("name" in h or h == "municipality"))
        if municipality_idx is None:
            municipality_idx = _header_index(headers, lambda h: "municip" in h)
        if municipality_idx is None:
            return {"status": "DCA_SOURCE_INDEX_UNAVAILABLE", "registered": False, "municipality": requested, "sources": {}, "notes": ["The DCA directory did not expose a municipality column."]}

        target = _municipality_key(requested)
        matches: list[tuple[str, dict[str, dict[str, Any]]]] = []
        for values in rows[header_row + 1:]:
            if municipality_idx >= len(values):
                continue
            name = values[municipality_idx].strip()
            if _municipality_key(name) != target:
                continue
            matches.append((name, _extract_sources(headers, values)))

        if not matches:
            return {
                "status": "DCA_SOURCE_INDEX_NOT_FOUND",
                "registered": False,
                "municipality": requested,
                "sources": {},
                "discovery_source": DCA_DIRECTORY_PAGE,
                "notes": [
                    "No matching municipality was found in the DCA statewide zoning information directory.",
                    "This does not establish that authoritative municipal sources do not exist.",
                ],
            }

        source_map: dict[str, dict[str, Any]] = {}
        for _, sources in matches:
            source_map.update(sources)
        return {
            "status": "DCA_SOURCES_DISCOVERED",
            "registered": True,
            "municipality": requested,
            "canonical_name": matches[0][0],
            "sources": source_map,
            "discovery_source": DCA_DIRECTORY_PAGE,
            "notes": [
                "Sources were discovered from the New Jersey DCA statewide zoning information directory.",
                "DCA states that its links may not represent every currently effective local source and recommends confirmation with the appropriate municipal official.",
                "Discovery does not establish parcel-specific zoning or project-rule applicability.",
            ],
        }
    except (httpx.HTTPError, ValueError, TypeError, KeyError, ET.ParseError, OSError) as exc:
        return {
            "status": "DCA_SOURCE_DISCOVERY_UNAVAILABLE",
            "registered": False,
            "municipality": requested,
            "sources": {},
            "discovery_source": DCA_DIRECTORY_PAGE,
            "notes": [f"DCA source discovery could not be completed: {exc.__class__.__name__}."],
        }
    finally:
        if close_client:
            client.close()
