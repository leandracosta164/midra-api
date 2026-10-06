from app.services.municipal_zoning_page_discovery import (
    discover_zoning_page_links,
    is_official_municipal_site,
    municipal_site_root,
)


def test_municipal_site_root_accepts_municipality_specific_host():
    assert municipal_site_root(
        "https://www.perthamboynj.org/government/departments/code_enforcement",
        "Perth Amboy City",
    ) == "https://www.perthamboynj.org/"


def test_state_page_is_not_municipal_site_merely_because_it_is_nj_gov():
    assert is_official_municipal_site(
        "https://www.nj.gov/dca/news/news/2023/20230613.shtml",
        "Perth Amboy City",
    ) is False


def test_discovers_explicit_same_host_zoning_page_from_homepage():
    content = b'''
      <a href="/government/departments/code_enforcement">Code Enforcement</a>
      <a href="/cms/One.aspx?pageId=20618142&amp;portalId=11205008">Perth Amboy Zoning Map</a>
    '''
    result = discover_zoning_page_links(page_url="https://www.perthamboynj.org/", content=content)
    assert result == [{
        "label": "Perth Amboy Zoning Map",
        "url": "https://www.perthamboynj.org/cms/One.aspx?pageId=20618142&portalId=11205008",
    }]


def test_does_not_treat_external_arcgis_target_as_municipal_zoning_page():
    content = b'<a href="https://example.maps.arcgis.com/apps/instant/basic/index.html?appid=0123456789abcdef0123456789abcdef">Zoning Viewer</a>'
    assert discover_zoning_page_links(page_url="https://city.example/", content=content) == []


def test_does_not_return_zoning_pdf_as_intermediate_page():
    content = b'<a href="/files/zoning-map.pdf">Zoning Map</a>'
    assert discover_zoning_page_links(page_url="https://city.example/", content=content) == []
