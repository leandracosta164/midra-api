from app.services.source_authority import evaluate_source_authority


def test_dca_municipal_source_has_provenance_and_domain_signal():
    result = evaluate_source_authority(
        municipality="Perth Amboy City",
        source={
            "source_url": "https://www.perthamboynj.org/government/departments/code_enforcement",
            "discovery_source": "https://www.nj.gov/dca/news/news/2023/20230613.shtml",
            "authority_tier": "likely_municipal_or_state_domain",
        },
    )
    assert result["status"] == "PROVENANCE_AND_DOMAIN_VERIFIED"
    assert result["authority_verified"] is True
    assert result["legal_control_confirmed"] is False


def test_dca_external_arcgis_source_keeps_legal_control_unconfirmed():
    result = evaluate_source_authority(
        municipality="Perth Amboy City",
        source={
            "source_url": "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
            "discovery_source": "https://www.nj.gov/dca/news/news/2023/20230613.shtml",
            "authority_tier": "external_or_unknown_domain",
        },
    )
    assert result["status"] == "DISCOVERY_PROVENANCE_VERIFIED"
    assert result["authority_verified"] is True
    assert result["legal_control_confirmed"] is False


def test_unknown_source_has_no_authority_signal():
    result = evaluate_source_authority(
        municipality="Perth Amboy City",
        source={"source_url": "https://example.com/zoning"},
    )
    assert result["status"] == "AUTHORITY_NOT_CONFIRMED"
    assert result["authority_verified"] is False
    assert result["legal_control_confirmed"] is False


def test_municipal_official_link_verifies_external_viewer_without_legal_control():
    result = evaluate_source_authority(
        municipality="Perth Amboy City",
        source={
            "source_url": "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c",
            "discovery_source": "https://www.nj.gov/dca/news/news/2023/20230613.shtml",
            "authority_tier": "external_or_unknown_domain",
            "municipal_official_link_verified": True,
            "municipal_official_page_url": "https://www.perthamboynj.org/government/departments/economic_community_development/perth_amboy_zoning_map",
        },
    )
    assert result["status"] == "MUNICIPAL_OFFICIAL_LINK_VERIFIED"
    assert result["authority_verified"] is True
    assert result["legal_control_confirmed"] is False
    assert "municipal_official_link_verified" in result["signals"]


def test_external_legal_provider_linked_from_verified_municipal_page_has_authority_provenance_without_dca():
    result = evaluate_source_authority(
        municipality="Example Borough",
        source={
            "source_url": "https://ecode360.com/EX0000",
            "authority_tier": "external_or_unknown_domain",
            "municipal_official_link_verified": True,
            "municipal_official_page_url": "https://www.exampleboroughnj.org/government/municipal_code",
        },
    )
    assert result["status"] == "MUNICIPAL_OFFICIAL_LINK_VERIFIED"
    assert result["authority_verified"] is True
    assert result["legal_control_confirmed"] is False
    assert "municipal_official_page_verified" in result["signals"]


def test_external_source_cannot_self_assert_official_link_from_unverified_page():
    result = evaluate_source_authority(
        municipality="Example Borough",
        source={
            "source_url": "https://ecode360.com/EX0000",
            "authority_tier": "external_or_unknown_domain",
            "municipal_official_link_verified": True,
            "municipal_official_page_url": "https://unrelated.invalid/municipal-code",
        },
    )
    assert result["status"] == "AUTHORITY_NOT_CONFIRMED"
    assert result["authority_verified"] is False
    assert result["legal_control_confirmed"] is False
