from app.services.source_legal_control_binding import bind_legal_control_to_source


CONTROL = """
The City adopts the Official Zoning Map. The original Official Zoning Map shall be
used as the final authority as to the current status of zoning districts.
"""


def test_binding_rejects_target_when_legal_control_evidence_is_missing():
    result = bind_legal_control_to_source(
        legal_content="View the official zoning map online.",
        target_source={"source_url": "https://maps.example.gov/zoning"},
    )
    assert result["legal_control_confirmed"] is False
    assert result["reason"] == "CONTROLLING_LEGAL_EVIDENCE_NOT_ESTABLISHED"


def test_binding_rejects_same_label_or_municipal_domain_without_exact_reference():
    result = bind_legal_control_to_source(
        legal_content=CONTROL,
        target_source={
            "label": "Official Zoning Map",
            "source_url": "https://maps.example.gov/zoning",
            "authoritative": True,
        },
    )
    assert result["legal_control_confirmed"] is False
    assert result["reason"] == "TARGET_IDENTITY_NOT_EXPLICITLY_REFERENCED"


def test_binding_accepts_exact_target_url_in_controlling_legal_text():
    url = "https://maps.example.gov/zoning"
    result = bind_legal_control_to_source(
        legal_content=CONTROL + f" The controlling electronic map is {url}.",
        target_source={"source_url": url},
    )
    assert result["status"] == "LEGAL_CONTROL_TARGET_BOUND"
    assert result["legal_control_confirmed"] is True
    assert result["identity_signals"] == ["EXACT_TARGET_URL_REFERENCE"]


def test_binding_accepts_exact_arcgis_app_id_in_controlling_legal_text():
    item_id = "09bd902a48ef45348d2d59283c89673c"
    target = f"https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid={item_id}"
    result = bind_legal_control_to_source(
        legal_content=CONTROL + f" The controlling electronic map has ArcGIS item ID {item_id}.",
        target_source={"source_url": target},
    )
    assert result["legal_control_confirmed"] is True
    assert result["identity_signals"] == ["EXACT_ARCGIS_ITEM_ID_REFERENCE"]


def test_binding_does_not_trust_a_separate_official_page_link_chain():
    result = bind_legal_control_to_source(
        legal_content=CONTROL,
        legal_source_url="https://www.example.gov/code/zoning",
        target_source={
            "source_url": "https://thirdparty.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
            "municipal_official_link_verified": True,
            "municipal_official_page_url": "https://www.example.gov/zoning-map",
        },
    )
    assert result["legal_control_confirmed"] is False
    assert result["reason"] == "TARGET_IDENTITY_NOT_EXPLICITLY_REFERENCED"
