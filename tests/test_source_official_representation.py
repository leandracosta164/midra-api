from app.services.source_official_representation import evaluate_official_zoning_representation


TARGET = {
    "source_url": "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c"
}


def test_official_zoning_page_can_verify_exact_target_url_without_legal_control():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/government/departments/economic_community_development/perth_amboy_zoning_map",
        official_page_content=f'<h1>Perth Amboy Zoning Map</h1><a href="{TARGET["source_url"]}">Interactive Zoning Viewer</a>',
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_ZONING_REPRESENTATION_VERIFIED"
    assert result["authority_verified"] is True
    assert result["authoritative"] is True
    assert result["legal_control_confirmed"] is False
    assert "EXACT_TARGET_URL_REFERENCE" in result["signals"]


def test_official_zoning_page_can_verify_stable_arcgis_item_id():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/zoning",
        official_page_content="Interactive Zoning Viewer app 09bd902a48ef45348d2d59283c89673c",
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_ZONING_REPRESENTATION_VERIFIED"
    assert "EXACT_ARCGIS_ITEM_ID_REFERENCE" in result["signals"]


def test_dca_or_external_page_cannot_establish_municipal_official_representation():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.nj.gov/dca/example",
        official_page_content=f'Zoning Map <a href="{TARGET["source_url"]}">viewer</a>',
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_REPRESENTATION_NOT_VERIFIED"
    assert result["reason"] == "OFFICIAL_MUNICIPAL_PAGE_NOT_VERIFIED"


def test_official_page_link_without_zoning_context_is_not_enough():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/resources",
        official_page_content=f'<a href="{TARGET["source_url"]}">GIS resource</a>',
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_REPRESENTATION_NOT_VERIFIED"
    assert result["reason"] == "ZONING_CONTEXT_NOT_ESTABLISHED"


def test_similar_arcgis_target_not_explicitly_linked_is_not_verified():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/zoning",
        official_page_content="Zoning Map and Interactive Zoning Viewer are available here.",
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_REPRESENTATION_NOT_VERIFIED"
    assert result["reason"] == "TARGET_NOT_EXPLICITLY_LINKED_FROM_OFFICIAL_ZONING_CONTEXT"


def test_positive_official_representation_never_claims_legal_control():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/zoning",
        official_page_content="Zoning Map: 09bd902a48ef45348d2d59283c89673c",
        target_source=TARGET,
    )
    assert result["authority_verified"] is True
    assert result["legal_control_confirmed"] is False


def test_official_code_enforcement_page_with_visible_zoning_section_can_verify_exact_target():
    # Live municipal pages do not always use the exact phrase "Zoning Map" in a
    # heading. A visible Zoning section plus the exact viewer link is sufficient
    # publication evidence, while exact target binding remains mandatory.
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/government/departments/code_enforcement",
        official_page_content=(
            '<main><h1>Code Enforcement</h1><h2>Zoning</h2>'
            f'<a href="{TARGET["source_url"]}">View zoning map</a></main>'
        ),
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_ZONING_REPRESENTATION_VERIFIED"
    assert result["authority_verified"] is True
    assert result["legal_control_confirmed"] is False


def test_zoning_word_hidden_only_in_script_does_not_establish_context():
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/resources",
        official_page_content=(
            '<script>window.topic = "zoning";</script>'
            f'<a href="{TARGET["source_url"]}">GIS resource</a>'
        ),
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_REPRESENTATION_NOT_VERIFIED"
    assert result["reason"] == "ZONING_CONTEXT_NOT_ESTABLISHED"



def test_redirect_wrapped_exact_target_url_is_verified_without_trusting_wrapper():
    target = {"source_url": "https://maps.example.com/zoning/viewer?layer=official"}
    wrapped = (
        "https://security.example.net/redirect?u="
        "https%3A%2F%2Fmaps.example.com%2Fzoning%2Fviewer%3Flayer%3Dofficial"
    )
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/zoning",
        official_page_content=f'<h1>Zoning Map</h1><a href="{wrapped}">Explore the Map</a>',
        target_source=target,
    )
    assert result["status"] == "OFFICIAL_ZONING_REPRESENTATION_VERIFIED"
    assert "REDIRECT_WRAPPED_TARGET_REFERENCE" in result["signals"]
    assert "EXACT_TARGET_URL_REFERENCE" in result["signals"]
    assert result["legal_control_confirmed"] is False


def test_redirect_wrapper_with_different_destination_does_not_verify_target():
    wrapped = (
        "https://security.example.net/redirect?u="
        "https%3A%2F%2Ftopology.maps.arcgis.com%2Fapps%2Finstant%2Fbasic%2Findex.html%3Fappid%3D"
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/zoning",
        official_page_content=f'<h1>Zoning Map</h1><a href="{wrapped}">Explore the Map</a>',
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_REPRESENTATION_NOT_VERIFIED"
    assert result["reason"] == "TARGET_NOT_EXPLICITLY_LINKED_FROM_OFFICIAL_ZONING_CONTEXT"


def test_redirect_decoding_does_not_replace_official_page_or_zoning_context_guards():
    wrapped = (
        "https://security.example.net/redirect?u="
        "https%3A%2F%2Ftopology.maps.arcgis.com%2Fapps%2Finstant%2Fbasic%2Findex.html%3Fappid%3D"
        "09bd902a48ef45348d2d59283c89673c"
    )
    result = evaluate_official_zoning_representation(
        municipality="Perth Amboy City",
        official_page_url="https://www.perthamboynj.org/resources",
        official_page_content=f'<a href="{wrapped}">GIS resource</a>',
        target_source=TARGET,
    )
    assert result["status"] == "OFFICIAL_REPRESENTATION_NOT_VERIFIED"
    assert result["reason"] == "ZONING_CONTEXT_NOT_ESTABLISHED"
