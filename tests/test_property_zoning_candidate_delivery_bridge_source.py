from pathlib import Path

api=(Path(__file__).resolve().parents[1]/"app"/"api"/"property_records.py").read_text(encoding="utf-8")
assert "def _delivery_zoning_candidate_from_analysis" in api
assert 'candidate_evidence.get("candidate_only") is not True' in api
assert '"geometry_definitive": False' in api
assert "zoning_candidate_evidence=_delivery_zoning_candidate_from_analysis(analysis)" in api
print("MIDRA Property 1.48 durable candidate-delivery bridge source contract: PASS")
