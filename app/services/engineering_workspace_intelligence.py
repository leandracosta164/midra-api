from pathlib import Path

"""Phase 5.74 — project workspace/file intelligence and desktop-connector boundary."""

VISIBILITY={"LOCAL_WORKING","INTERNAL_CLOUD","CLIENT_APPROVED","ISSUED"}
FILE_ROLES={"SOURCE_DESIGN","WORKING_OUTPUT","ISSUED_DELIVERABLE","REFERENCE","CALCULATION","REPORT"}

def authorize_workspace(*, workspace_id, job_number, local_root, authorized_by):
    if not (authorized_by or "").strip():
        raise ValueError("workspace authorization required")
    return {
        "workspace_id":workspace_id,"job_number":job_number,"local_root":local_root,
        "authorized_by":authorized_by,"active":True,"files":[],
    }

def register_workspace_file(*, workspace, relative_path, file_role, visibility="LOCAL_WORKING",
                            modified_at=None, fingerprint=None, software=None):
    if file_role not in FILE_ROLES: raise ValueError("unsupported file role")
    if visibility not in VISIBILITY: raise ValueError("unsupported visibility")
    if relative_path.startswith(("/", "\\")) or ".." in Path(relative_path).parts:
        raise ValueError("file must remain inside authorized workspace")
    r=_copy(workspace)
    existing=next((x for x in r["files"] if x["relative_path"]==relative_path),None)
    if existing:
        existing.update(modified_at=modified_at,fingerprint=fingerprint or existing.get("fingerprint"),
                        software=software or existing.get("software"))
        return r
    r["files"].append({
        "file_id":f'{workspace["workspace_id"]}:{len(r["files"])+1}',
        "relative_path":relative_path,"file_role":file_role,"visibility":visibility,
        "modified_at":modified_at,"fingerprint":fingerprint,"software":software,
        "client_visible":False,"issued":False,
    })
    return r

def set_file_visibility(*, workspace, file_id, visibility, authorized_by):
    if visibility not in VISIBILITY: raise ValueError("unsupported visibility")
    if not (authorized_by or "").strip(): raise ValueError("authorization required")
    r=_copy(workspace); f=_file(r,file_id)
    # Local design source files cannot accidentally become client deliverables.
    if f["file_role"]=="SOURCE_DESIGN" and visibility=="CLIENT_APPROVED":
        raise ValueError("source design files cannot be client-published")
    f["visibility"]=visibility
    f["client_visible"]=visibility=="CLIENT_APPROVED"
    return r

def issue_workspace_file(*, workspace, file_id, issued_at, authorized_by, submission_id=None):
    if not (authorized_by or "").strip(): raise ValueError("issue authorization required")
    r=_copy(workspace); f=_file(r,file_id)
    if f["file_role"]=="SOURCE_DESIGN":
        raise ValueError("source design file cannot be issued as deliverable")
    f["issued"]=True; f["issued_at"]=issued_at; f["submission_id"]=submission_id
    f["visibility"]="ISSUED"; f["client_visible"]=False
    return r

def client_portal_publish(*, workspace, file_id, authorized_by):
    if not (authorized_by or "").strip(): raise ValueError("client publication authorization required")
    r=_copy(workspace); f=_file(r,file_id)
    if not f.get("issued"):
        raise ValueError("only issued deliverables may be published to client portal")
    if f["file_role"]=="SOURCE_DESIGN":
        raise ValueError("source design files are never client portal deliverables")
    f["visibility"]="CLIENT_APPROVED"; f["client_visible"]=True
    return r

def desktop_connector_manifest(*, workspace):
    """Metadata for the connector; no authority to browse outside local_root."""
    return {
        "workspace_id":workspace["workspace_id"],"job_number":workspace["job_number"],
        "authorized_root":workspace["local_root"],"active":workspace["active"],
        "tracked_files":[{"file_id":x["file_id"],"relative_path":x["relative_path"],
                          "modified_at":x.get("modified_at"),"fingerprint":x.get("fingerprint")}
                         for x in workspace["files"]],
    }

def client_portal_files(*, workspace):
    return [dict(x) for x in workspace["files"] if x.get("client_visible")]

def _file(workspace,file_id):
    for f in workspace["files"]:
        if f["file_id"]==file_id: return f
    raise KeyError(file_id)

def _copy(workspace):
    r=dict(workspace); r["files"]=[dict(x) for x in workspace.get("files",[])]
    return r

def workspace_policy():
    return {
        "desktop_connector_is_bridge_not_second_project_manager":True,
        "connector_access_limited_to_authorized_root":True,
        "working_files_private_by_default":True,
        "source_design_files_not_client_publishable":True,
        "client_portal_requires_explicit_publication":True,
        "website_does_not_arbitrarily_browse_local_computer":True,
    }

