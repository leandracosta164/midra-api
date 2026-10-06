from pathlib import Path

def method_text():
    p=Path(__file__).resolve().parents[1]/"app"/"repositories"/"engineering_job.py"
    text=p.read_text(encoding="utf-8")
    start=text.index("    def reassess_returned_submission")
    end=text.find("\n    def ", start+5)
    if end < 0: end=len(text)
    return text[start:end]

def test_cancelled_return_work_is_not_terminal_for_reassessment():
    m=method_text()
    assert 'str(a.get("status","OPEN")).upper()!="DONE"' in m
    assert 'not in {"DONE","CANCELLED"}' not in m
    assert 'returned submission return work must be completed before reassessment' in m

def test_reassessment_still_requires_recorded_return_work():
    m=method_text()
    assert 'if not tied:' in m
    assert 'returned submission has no recorded return-work item' in m
