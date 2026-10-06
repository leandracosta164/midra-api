from app.services import municipality_source_discovery as discovery


class FakeResponse:
    def __init__(self, content=b"fixture"):
        self.content = content
    def raise_for_status(self):
        return None


class FakeClient:
    def get(self, url, params=None):
        return FakeResponse()


def test_discovers_municipal_sources_from_dca_directory(monkeypatch):
    monkeypatch.setattr(
        discovery,
        "_xlsx_rows",
        lambda content: [
            ["Municipality", "Zoning Map", "Zoning Ordinance"],
            ["Test Township", "https://example.test/zoning-map.pdf", "https://example.test/code"],
        ],
    )
    result = discovery.discover_municipality_sources("Test Township", client=FakeClient())
    assert result["status"] == "DCA_SOURCES_DISCOVERED"
    assert result["registered"] is True
    assert result["sources"]["Zoning Map"]["url"].endswith("zoning-map.pdf")


def test_missing_municipality_returns_verify_safe_status(monkeypatch):
    monkeypatch.setattr(
        discovery,
        "_xlsx_rows",
        lambda content: [["Municipality", "Zoning Map"], ["Other Township", "https://example.test/map"]],
    )
    result = discovery.discover_municipality_sources("Unknown Township", client=FakeClient())
    assert result["status"] == "DCA_SOURCE_INDEX_NOT_FOUND"
    assert result["registered"] is False


def test_matches_municipality_without_governmental_suffix(monkeypatch):
    monkeypatch.setattr(
        discovery,
        "_xlsx_rows",
        lambda content: [
            ["Municipality", "Zoning Map"],
            ["Perth Amboy City", "https://example.test/perth-amboy-map"],
        ],
    )
    result = discovery.discover_municipality_sources("Perth Amboy", client=FakeClient())
    assert result["status"] == "DCA_SOURCES_DISCOVERED"
    assert result["canonical_name"] == "Perth Amboy City"

from zipfile import ZipFile
import io


def test_clean_source_url_truncates_arcgis_appid_with_appended_display_text():
    result = discovery._clean_source_url(
        "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid="
        "09bd902a48ef45348d2d59283c89673cCity%20of%20Perth%20Amboy%20Zoning%20Viewer"
    )
    assert result.endswith("?appid=09bd902a48ef45348d2d59283c89673c")


def test_xlsx_rows_prefers_external_hyperlink_target():
    workbook = b'''<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
    </workbook>'''
    workbook_rels = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Target="worksheets/sheet1.xml" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>
    </Relationships>'''
    sheet = b'''<?xml version="1.0" encoding="UTF-8"?>
    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Municipality</t></is></c><c r="B1" t="inlineStr"><is><t>Zoning Map</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Perth Amboy City</t></is></c><c r="B2" t="inlineStr"><is><t>City of Perth Amboy Zoning Viewer</t></is></c></row></sheetData>
      <hyperlinks><hyperlink ref="B2" r:id="rId2"/></hyperlinks>
    </worksheet>'''
    sheet_rels = b'''<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId2" Target="https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c" TargetMode="External" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"/>
    </Relationships>'''
    buf = io.BytesIO()
    with ZipFile(buf, "w") as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/worksheets/_rels/sheet1.xml.rels", sheet_rels)
    rows = discovery._xlsx_rows(buf.getvalue())
    assert rows[1][1] == "https://topology.maps.arcgis.com/apps/instant/basic/index.html?appid=09bd902a48ef45348d2d59283c89673c"
