"""MIDRA Engineering Milestone 6.2 — Unified Job Record & persistence contract.

Creates a durable, repository-neutral aggregate for a MIDRA Engineering Job. Existing
subsystems can attach references/summaries to one Job without being collapsed into one
giant object or silently changing professional/project state.
"""

from copy import deepcopy
from datetime import datetime, timezone

JOB_STATES={"ACTIVE","WAITING","ON_HOLD","READY_FOR_REVIEW","CLOSEOUT","CLOSED"}
SECTIONS={
    "client","property","estimate","workflow","workspace","design",
    "submissions","reviews","correspondence","billing","client_portal"
}

def _now():
    return datetime.now(timezone.utc).isoformat()

def create_job_record(*, job_number, project_name, project_type, source,
                      property_address=None, client_id=None):
    now=_now()
    return {
        "job_number":job_number,
        "project_name":project_name,
        "project_type":project_type,
        "source":source,
        "property_address":property_address,
        "client_id":client_id,
        "state":"ACTIVE",
        "version":1,
        "created_at":now,
        "updated_at":now,
        "sections":{},
        "events":[],
    }

def attach_section(*, job, section, reference_id, summary=None, authorized_by=None):
    if section not in SECTIONS:
        raise ValueError("unsupported job section")
    r=deepcopy(job)
    r["sections"][section]={
        "reference_id":reference_id,
        "summary":deepcopy(summary or {}),
        "updated_by":authorized_by,
    }
    return _touch(r)

def set_job_state(*, job, state, authorized_by, reason=None):
    if state not in JOB_STATES:
        raise ValueError("unsupported job state")
    if not (authorized_by or "").strip():
        raise ValueError("job state change requires authorization")
    r=deepcopy(job)
    previous=r["state"]
    r["state"]=state
    r["events"].append({
        "event_type":"JOB_STATE_CHANGED",
        "from_state":previous,
        "to_state":state,
        "reason":reason,
        "authorized_by":authorized_by,
    })
    return _touch(r)

def record_job_event(*, job, event_type, reference_id=None, summary=None):
    r=deepcopy(job)
    r["events"].append({
        "event_type":event_type,
        "reference_id":reference_id,
        "summary":summary,
    })
    return _touch(r)

def unified_job_view(*, job):
    return {
        "job_number":job["job_number"],
        "project_name":job["project_name"],
        "project_type":job["project_type"],
        "source":job["source"],
        "property_address":job.get("property_address"),
        "client_id":job.get("client_id"),
        "state":job["state"],
        "version":job["version"],
        "connected_sections":{
            k:v["reference_id"] for k,v in job["sections"].items()
        },
        "section_summaries":{
            k:deepcopy(v.get("summary",{})) for k,v in job["sections"].items()
        },
        "event_count":len(job["events"]),
    }

class InMemoryJobRepository:
    """Persistence contract reference implementation.

    Production can later replace this with SQLAlchemy/PostgreSQL without changing the
    domain-facing save/get/version semantics.
    """
    def __init__(self):
        self._jobs={}

    def save(self, job, *, expected_version=None):
        key=job["job_number"]
        current=self._jobs.get(key)
        if current is not None and expected_version is not None:
            if current["version"] != expected_version:
                raise ValueError("job version conflict")
        if current is None and expected_version not in (None,0):
            raise ValueError("job version conflict")
        self._jobs[key]=deepcopy(job)
        return deepcopy(self._jobs[key])

    def get(self, job_number):
        if job_number not in self._jobs:
            raise KeyError(job_number)
        return deepcopy(self._jobs[job_number])

    def exists(self, job_number):
        return job_number in self._jobs

    def list_jobs(self):
        return [deepcopy(self._jobs[k]) for k in sorted(self._jobs)]

def persist_update(*, repository, job, expected_version):
    """Optimistic concurrency prevents one screen/process from overwriting another."""
    return repository.save(job, expected_version=expected_version)

def _touch(job):
    job["version"]+=1
    job["updated_at"]=_now()
    return job

def unified_job_policy():
    return {
        "one_canonical_job_number":True,
        "subsystems_attach_by_reference":True,
        "job_record_does_not_duplicate_entire_subsystem_state":True,
        "state_changes_are_authorized":True,
        "optimistic_concurrency_supported":True,
        "repository_is_replaceable_with_database_backend":True,
        "midra_property_not_required":True,
    }
