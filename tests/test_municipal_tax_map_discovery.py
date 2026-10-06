from app.services.municipal_tax_map_discovery import discover_explicit_tax_map_links


def test_discovers_explicit_municipal_tax_map_page():
    html = b'<a href="/departments/assessor/tax-maps">Tax Maps</a>'
    result = discover_explicit_tax_map_links(
        page_url="https://example.gov/",
        content=html,
    )
    assert result == [{
        "label": "Tax Maps",
        "url": "https://example.gov/departments/assessor/tax-maps",
        "tax_map_sheet": None,
        "source_role": "tax_map",
    }]


def test_discovers_explicit_tax_map_pdf_sheet_number():
    html = b'<a href="/taxmaps/sheet-12.pdf">Tax Map Sheet 12</a>'
    result = discover_explicit_tax_map_links(
        page_url="https://example.gov/taxmaps",
        content=html,
    )
    assert len(result) == 1
    assert result[0]["tax_map_sheet"] == "12"
    assert result[0]["url"] == "https://example.gov/taxmaps/sheet-12.pdf"


def test_tax_map_url_can_supply_evidence_when_label_is_just_sheet():
    html = b'<a href="/taxmaps/sheet-7.pdf">Sheet 7</a>'
    result = discover_explicit_tax_map_links(
        page_url="https://example.gov/",
        content=html,
    )
    assert len(result) == 1
    assert result[0]["tax_map_sheet"] == "7"


def test_rejects_tax_map_regulations_and_templates():
    html = b"""
      <a href="/docs/tax-map-standards.pdf">Tax Map Standards</a>
      <a href="/docs/tax-map-template.dwg">Tax Map Template</a>
      <a href="/docs/tax-map-submittal.pdf">Tax Map Submittal Instructions</a>
    """
    assert discover_explicit_tax_map_links(
        page_url="https://example.gov/",
        content=html,
    ) == []


def test_does_not_treat_general_assessor_or_parcel_link_as_tax_map():
    html = b"""
      <a href="/assessor">Tax Assessor</a>
      <a href="/gis/parcels">Parcel Viewer</a>
      <a href="/property-search">Property Tax Search</a>
    """
    assert discover_explicit_tax_map_links(
        page_url="https://example.gov/",
        content=html,
    ) == []
