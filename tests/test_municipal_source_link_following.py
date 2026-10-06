from app.services.municipal_source_link_following import (
    discover_ordinance_links,
    discover_explicit_document_links,
)


def test_discovers_explicit_city_ordinances_link():
    html = b'<a href="https://ecode360.com/35019251">View City Ordinances</a>'
    result = discover_ordinance_links(page_url="https://www.example.nj.us/code", content=html)
    assert result == [{"label": "View City Ordinances", "url": "https://ecode360.com/35019251"}]


def test_resolves_relative_link():
    html = b'<a href="/ordinances">Zoning Ordinances</a>'
    result = discover_ordinance_links(page_url="https://www.example.nj.us/code", content=html)
    assert result[0]["url"] == "https://www.example.nj.us/ordinances"


def test_ignores_unrelated_links():
    html = b'<a href="/about">About Us</a><a href="/maps">Maps</a>'
    assert discover_ordinance_links(page_url="https://www.example.nj.us/", content=html) == []


def test_deduplicates_explicit_links():
    html = b'<a href="/ordinances">City Ordinances</a><a href="/ordinances">View City Ordinances</a>'
    result = discover_ordinance_links(page_url="https://www.example.nj.us/", content=html)
    assert len(result) == 1


def test_discovers_explicit_official_ordinance_pdf():
    html = b'<a href="/files/ordinance-430.pdf">Chapter 430 Zoning Ordinance (PDF)</a>'
    result = discover_explicit_document_links(page_url="https://www.example.nj.us/code", content=html)
    assert result == [{"label": "Chapter 430 Zoning Ordinance (PDF)", "url": "https://www.example.nj.us/files/ordinance-430.pdf"}]


def test_document_discovery_does_not_guess_pdf_urls():
    html = b'<p>Chapter 430 Zoning Ordinance</p>'
    assert discover_explicit_document_links(page_url="https://www.example.nj.us/code", content=html) == []


def test_discovers_local_laws_and_ordinances_link():
    content = b'<a href="https://ecode360.com/PE0514">i Local Laws &amp; Ordinances</a>'
    result = discover_ordinance_links(page_url="https://www.example.gov/", content=content)
    assert result == [{"label": "i Local Laws &amp; Ordinances", "url": "https://ecode360.com/PE0514"}]


def test_discovers_city_code_link():
    content = b'<a href="https://ecode360.com/EX1234">City Code</a>'
    result = discover_ordinance_links(page_url="https://www.example.gov/zoning", content=content)
    assert result == [{"label": "City Code", "url": "https://ecode360.com/EX1234"}]
