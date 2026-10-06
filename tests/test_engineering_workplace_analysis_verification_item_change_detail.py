from types import SimpleNamespace

from app.services.engineering_workplace_portfolio import _workplace_analysis_verification_item_change_detail


def run(run_id: str, *, general=None, zoning=None, environmental=None):
    return SimpleNamespace(
        analysis_run_id=run_id,
        analysis={
            "verification_items": list(general or []),
            "zoning_candidate_verification_items": list(zoning or []),
            "environmental_verification_items": list(environmental or []),
        },
    )


def test_verification_item_change_detail_preserves_recorded_items_and_categories():
    selected=run(
        "analysis-old",
        general=["VERIFY ownership"],
        environmental=["VERIFY WETLANDS: confirm mapping"],
    )
    latest=run(
        "analysis-new",
        general=["VERIFY ownership", "VERIFY access"],
        zoning=["VERIFY ZONING CANDIDATE: confirm authority"],
    )

    result=_workplace_analysis_verification_item_change_detail(
        selected_run=selected,
        latest_run=latest,
    )

    assert result["comparison_mode"] == "RECORDED_VERIFICATION_ITEMS_ONLY"
    assert result["added_item_count"] == 2
    assert result["removed_item_count"] == 1
    assert {item["text"] for item in result["added_items"]} == {
        "VERIFY access",
        "VERIFY ZONING CANDIDATE: confirm authority",
    }
    assert result["removed_items"][0]["text"] == "VERIFY WETLANDS: confirm mapping"
    assert result["removed_items"][0]["category"] == "ENVIRONMENTAL"


def test_verification_item_change_detail_same_run_has_no_changes():
    latest=run("analysis-new", general=[{"message":"VERIFY source currency", "code":"SOURCE_CURRENTNESS"}])
    result=_workplace_analysis_verification_item_change_detail(selected_run=latest, latest_run=latest)
    assert result["is_latest"] is True
    assert result["added_items"] == []
    assert result["removed_items"] == []
