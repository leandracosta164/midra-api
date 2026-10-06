"""Phase 5.75 — Job/workspace/design-output/submission linkage."""

RELATION_TYPES={
    "GENERATES","DERIVED_FROM","SUPPORTS","ISSUED_AS",
    "INCLUDED_IN_SUBMISSION","RESPONDS_TO_COMMENT"
}

def create_project_artifact_graph(*, job_number, workspace_id):
    return {"job_number":job_number,"workspace_id":workspace_id,
            "artifacts":{},"relations":[]}

def register_artifact(*, graph, artifact_id, artifact_kind, label,
                      file_id=None, revision=None, status="WORKING"):
    r=_copy(graph)
    r["artifacts"][artifact_id]={
        "artifact_id":artifact_id,"artifact_kind":artifact_kind,"label":label,
        "file_id":file_id,"revision":revision,"status":status,
    }
    return r

def link_artifacts(*, graph, source_id, target_id, relation_type,
                   authorized_by=None):
    if relation_type not in RELATION_TYPES:
        raise ValueError("unsupported relation type")
    if source_id not in graph["artifacts"] or target_id not in graph["artifacts"]:
        raise KeyError("both artifacts must be registered")
    if relation_type in {"ISSUED_AS","INCLUDED_IN_SUBMISSION"} and not (authorized_by or "").strip():
        raise ValueError("authorized linkage required")
    r=_copy(graph)
    edge={"source_id":source_id,"target_id":target_id,
          "relation_type":relation_type}
    if authorized_by: edge["authorized_by"]=authorized_by
    if edge not in r["relations"]: r["relations"].append(edge)
    return r

def downstream_artifacts(*, graph, artifact_id):
    ids=[x["target_id"] for x in graph["relations"] if x["source_id"]==artifact_id]
    return [dict(graph["artifacts"][x]) for x in ids]

def submission_contents(*, graph, submission_id):
    ids=[x["source_id"] for x in graph["relations"]
         if x["target_id"]==submission_id and x["relation_type"]=="INCLUDED_IN_SUBMISSION"]
    return [dict(graph["artifacts"][x]) for x in ids]

def trace_comment_response(*, graph, comment_id):
    ids=[x["source_id"] for x in graph["relations"]
         if x["target_id"]==comment_id and x["relation_type"]=="RESPONDS_TO_COMMENT"]
    return [dict(graph["artifacts"][x]) for x in ids]

def command_center_artifact_view(*, graph):
    submissions=[a for a in graph["artifacts"].values()
                 if a["artifact_kind"]=="SUBMISSION"]
    return {
        "job_number":graph["job_number"],"workspace_id":graph["workspace_id"],
        "artifact_count":len(graph["artifacts"]),
        "relation_count":len(graph["relations"]),
        "submissions":[dict(x) for x in submissions],
    }

def _copy(graph):
    return {"job_number":graph["job_number"],"workspace_id":graph["workspace_id"],
            "artifacts":{k:dict(v) for k,v in graph.get("artifacts",{}).items()},
            "relations":[dict(x) for x in graph.get("relations",[])]}

def artifact_linkage_policy():
    return {
        "one_graph_per_job_workspace":True,
        "working_sources_can_generate_outputs":True,
        "submission_membership_requires_authorization":True,
        "issue_relationship_requires_authorization":True,
        "comments_can_link_to_correcting_artifacts":True,
        "source_files_remain_distinct_from_issued_outputs":True,
    }
