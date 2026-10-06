
"""Extract explicit ArcGIS item/service references from cached app content."""
from __future__ import annotations
import json, re
from typing import Any

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)
_ITEM_RE = re.compile(r"(?<![A-Za-z0-9])[0-9a-f]{32}(?![A-Za-z0-9])", re.I)

def discover_arcgis_cached_references(content: bytes | str) -> dict[str, Any]:
    if isinstance(content, bytes):
        text = content.decode("utf-8", errors="ignore")
    else:
        text = content
    urls = []
    for u in _URL_RE.findall(text):
        u = u.rstrip(".,);]}") 
        if u not in urls:
            urls.append(u)
    item_ids = []
    for item_id in _ITEM_RE.findall(text):
        item_id = item_id.lower()
        if item_id not in item_ids:
            item_ids.append(item_id)
    service_urls = [
        u for u in urls
        if "/FeatureServer" in u or "/MapServer" in u
    ]
    web_map_ids = []
    try:
        data = json.loads(text)
        def walk(v):
            if isinstance(v, dict):
                for k, x in v.items():
                    lk = str(k).lower()
                    if lk in {"webmap", "webmapid", "web_map_id"} and isinstance(x, str):
                        if re.fullmatch(r"[0-9a-f]{32}", x, re.I):
                            web_map_ids.append(x.lower())
                    walk(x)
            elif isinstance(v, list):
                for x in v: walk(x)
        walk(data)
    except Exception:
        pass
    for x in web_map_ids:
        if x not in item_ids: item_ids.append(x)
    return {
        "status": "REFERENCES_DISCOVERED" if (urls or item_ids) else "NO_REFERENCES_FOUND",
        "item_ids": item_ids,
        "web_map_ids": web_map_ids,
        "service_urls": service_urls,
        "urls": urls,
    }
