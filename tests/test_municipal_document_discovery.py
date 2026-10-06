from app.services.municipal_document_discovery import discover_explicit_municipal_documents


def test_discovers_explicit_pdf_ordinance_link():
    content = b'<a href="/files/ordinance-430.pdf">Chapter 430 Zoning Ordinance (PDF)</a>'
    result = discover_explicit_municipal_documents(page_url="https://city.example/", content=content)
    assert result == [{"label": "Chapter 430 Zoning Ordinance (PDF)", "url": "https://city.example/files/ordinance-430.pdf"}]


def test_discovers_explicit_civiclive_document_endpoint():
    content = b'<a href="/common/pages/DisplayFile.aspx?itemId=123">Zoning Ordinance</a>'
    result = discover_explicit_municipal_documents(page_url="https://city.example/code", content=content)
    assert result[0]["url"] == "https://city.example/common/pages/DisplayFile.aspx?itemId=123"


def test_discovers_getfile_ordinance_document():
    content = b'<a href="/common/pages/GetFile.ashx?key=abc">Ordinance Amendment</a>'
    result = discover_explicit_municipal_documents(page_url="https://city.example/", content=content)
    assert result[0]["url"] == "https://city.example/common/pages/GetFile.ashx?key=abc"


def test_ignores_generic_pdf_without_ordinance_context():
    content = b'<a href="/files/agenda.pdf">Planning Board Agenda (PDF)</a>'
    assert discover_explicit_municipal_documents(page_url="https://city.example/", content=content) == []


def test_deduplicates_explicit_document_links():
    content = b'''<a href="/files/ordinance.pdf">Ordinance PDF</a>\n<a href="/files/ordinance.pdf">Ordinance PDF</a>'''
    result = discover_explicit_municipal_documents(page_url="https://city.example/", content=content)
    assert len(result) == 1
