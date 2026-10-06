from types import SimpleNamespace

from app.services.zoning_spatial_bridge import resolve_dynamic_spatial_zoning_candidate


def _db(*rows):
    class Scalars:
        def all(self):
            return list(rows)

    class DB:
        def scalars(self, _statement):
            return Scalars()

    return DB()


def test_bridge_follows_explicit_app_to_webmap_to_spatial_service():
    source = SimpleNamespace(
        id=1,
        municipality="Perth Amboy City",
        label="Zoning Map Links",
        source_url="https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
        source_role="zoning_map",
        authority_tier="discovered_candidate",
        evidence_status="DISCOVERED_CANDIDATE",
        authoritative=False,
        legal_control_confirmed=False,
        active=True,
        current_content_hash="abc",
        current_status="RETRIEVED",
    )

    calls = []

    def metadata(item_id):
        calls.append(("metadata", item_id))
        if item_id == "09bd902a48ef45348d2d59283c89673c":
            return {"status": "ARCGIS_METADATA_RETRIEVED", "data": {"values": {"webmap": "676f6d399a6e4c53913d0b1dde072cd7"}}}
        return {"status": "ARCGIS_METADATA_RETRIEVED", "data": {"operationalLayers": [{
            "url": "https://services7.arcgis.com/HVAUPEhgOEfMS4MH/arcgis/rest/services/Perth_Amboy_Zoning_/FeatureServer/0",
            "title": "Perth Amboy Zoning",
            "itemId": "3c1ccbb8999b4dbfb5e08ed7d252d226",
            "layerType": "ArcGISFeatureLayer",
            "fields": [{"alias": "Zone District", "name": "Zone_code"}],
        }]}}

    def discover(data):
        return {"status": "WEBMAP_SERVICES_DISCOVERED", "layers": [{
            "url": "https://services7.arcgis.com/HVAUPEhgOEfMS4MH/arcgis/rest/services/Perth_Amboy_Zoning_/FeatureServer/0",
            "title": "Perth Amboy Zoning",
            "item_id": "3c1ccbb8999b4dbfb5e08ed7d252d226",
            "layer_type": "ArcGISFeatureLayer",
            "district_field": "Zone_code",
        }]}

    def spatial_query(**kwargs):
        calls.append(("spatial", kwargs["service_url"], kwargs["district_field"], kwargs.get("spatial_reference_wkid")))
        return {
            "status": "ZONING_CANDIDATE_RESOLVED",
            "district": "R-60",
            "attributes": {"Zone_code": "R-60"},
            "source": {"url": kwargs["service_url"], "district_field": "Zone_code", "authoritative": False},
        }

    result = resolve_dynamic_spatial_zoning_candidate(
        municipality="Perth Amboy City",
        block="55",
        lot="1",
        geometry={"rings": [[[1, 2], [2, 3], [1, 2]]], "spatialReference": {"wkid": 4326}},
        db=_db(source),
        metadata_retriever=metadata,
        webmap_discoverer=discover,
        spatial_query=spatial_query,
    )

    assert result["status"] == "ZONING_CANDIDATE_RESOLVED"
    assert result["record"]["zoning_district"] == "R-60"
    assert result["record"]["source"]["authoritative"] is False
    assert calls[0] == ("metadata", "09bd902a48ef45348d2d59283c89673c")
    assert calls[1] == ("metadata", "676f6d399a6e4c53913d0b1dde072cd7")
    assert calls[2][0] == "spatial"
    assert calls[2][3] == 4326


def test_bridge_does_not_promote_or_guess_when_no_explicit_service_exists():
    source = SimpleNamespace(
        id=1, municipality="Perth Amboy City", label="Zoning Map Links",
        source_url="https://example.com/zoning", source_role="zoning_map",
        authority_tier="discovered_candidate", evidence_status="DISCOVERED_CANDIDATE",
        authoritative=False, legal_control_confirmed=False, active=True,
        current_content_hash=None, current_status="RETRIEVED",
    )
    result = resolve_dynamic_spatial_zoning_candidate(
        municipality="Perth Amboy City", block="55", lot="1",
        geometry={"rings": []}, db=_db(source),
        metadata_retriever=lambda *args, **kwargs: {"status": "SHOULD_NOT_RUN"},
    )
    assert result["status"] == "ZONING_NOT_RESOLVED"
    assert result["reason"] == "NO_UNIQUE_DYNAMIC_ZONING_CANDIDATE"
    assert result["attempted"][0]["reason"] == "NO_EXPLICIT_ARCGIS_ITEM_ID"



def test_bridge_preserves_explicit_catalog_authority_and_legal_control():
    source = SimpleNamespace(
        id=2, municipality="Perth Amboy City", label="Verified zoning map",
        source_url="https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
        source_role="zoning_map", authority_tier="explicitly_verified",
        evidence_status="LEGAL_CONTROL_CONFIRMED", authoritative=True,
        legal_control_confirmed=True, active=True, current_content_hash="verified",
        current_status="RETRIEVED",
    )

    def metadata(item_id):
        if item_id == "09bd902a48ef45348d2d59283c89673c":
            return {"status": "ARCGIS_METADATA_RETRIEVED", "data": {"values": {"webmap": "676f6d399a6e4c53913d0b1dde072cd7"}}}
        return {"status": "ARCGIS_METADATA_RETRIEVED", "data": {}}

    def discover(_data):
        return {"status": "WEBMAP_SERVICES_DISCOVERED", "layers": [{
            "url": "https://services.example.gov/arcgis/rest/services/Zoning/FeatureServer/0",
            "title": "Zoning", "district_field": "Zone_code",
        }]}

    def spatial_query(**kwargs):
        return {
            "status": "ZONING_CANDIDATE_RESOLVED", "district": "R-60",
            "attributes": {"Zone_code": "R-60"},
            "source": {"url": kwargs["service_url"], "district_field": "Zone_code",
                       "authoritative": False, "legal_control_confirmed": False},
        }

    result = resolve_dynamic_spatial_zoning_candidate(
        municipality="Perth Amboy City", block="55", lot="1",
        geometry={"rings": [[[1, 2], [2, 3], [1, 2]]]}, db=_db(source),
        metadata_retriever=metadata, webmap_discoverer=discover, spatial_query=spatial_query,
    )

    resolved_source = result["record"]["source"]
    assert resolved_source["authoritative"] is True
    assert resolved_source["legal_control_confirmed"] is True
