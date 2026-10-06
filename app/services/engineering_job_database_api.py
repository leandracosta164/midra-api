"""MIDRA Engineering Milestone 6.3 — database repository + Job Operations API foundation.

Provides a SQLite-backed reference repository and application-service API over the
Milestone 6.2 unified Job record. SQLite keeps this milestone self-contained for local
development; the contract remains suitable for a later PostgreSQL production adapter.
"""

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from app.services.engineering_unified_job_record import (
    create_job_record, attach_section, set_job_state, record_job_event, unified_job_view
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS engineering_jobs (
    job_number TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    state TEXT NOT NULL,
    project_name TEXT NOT NULL,
    project_type TEXT NOT NULL,
    source TEXT NOT NULL,
    property_address TEXT,
    client_id TEXT,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_engineering_jobs_state
ON engineering_jobs(state);
"""

class SQLiteJobRepository:
    def __init__(self, database_path):
        self.database_path=str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        con=sqlite3.connect(self.database_path)
        con.row_factory=sqlite3.Row
        return con

    def _initialize(self):
        with self._connect() as con:
            con.executescript(SCHEMA)

    def save(self, job, *, expected_version=None):
        with self._connect() as con:
            row=con.execute(
                "SELECT version FROM engineering_jobs WHERE job_number=?",
                (job["job_number"],)
            ).fetchone()

            if row is None:
                if expected_version not in (None,0):
                    raise ValueError("job version conflict")
                con.execute(
                    """INSERT INTO engineering_jobs
                    (job_number,version,state,project_name,project_type,source,
                     property_address,client_id,payload_json)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    _row_values(job)
                )
            else:
                current=int(row["version"])
                if expected_version is not None and current != expected_version:
                    raise ValueError("job version conflict")
                con.execute(
                    """UPDATE engineering_jobs SET
                    version=?,state=?,project_name=?,project_type=?,source=?,
                    property_address=?,client_id=?,payload_json=?
                    WHERE job_number=?""",
                    (
                        job["version"],job["state"],job["project_name"],
                        job["project_type"],job["source"],
                        job.get("property_address"),job.get("client_id"),
                        json.dumps(job,sort_keys=True),job["job_number"]
                    )
                )
        return deepcopy(job)

    def get(self, job_number):
        with self._connect() as con:
            row=con.execute(
                "SELECT payload_json FROM engineering_jobs WHERE job_number=?",
                (job_number,)
            ).fetchone()
        if row is None:
            raise KeyError(job_number)
        return json.loads(row["payload_json"])

    def exists(self, job_number):
        with self._connect() as con:
            row=con.execute(
                "SELECT 1 FROM engineering_jobs WHERE job_number=?",(job_number,)
            ).fetchone()
        return row is not None

    def list_jobs(self, *, state=None):
        sql="SELECT payload_json FROM engineering_jobs"
        args=()
        if state:
            sql+=" WHERE state=?"; args=(state,)
        sql+=" ORDER BY job_number"
        with self._connect() as con:
            rows=con.execute(sql,args).fetchall()
        return [json.loads(x["payload_json"]) for x in rows]

def _row_values(job):
    return (
        job["job_number"],job["version"],job["state"],job["project_name"],
        job["project_type"],job["source"],job.get("property_address"),
        job.get("client_id"),json.dumps(job,sort_keys=True)
    )

class JobOperationsAPI:
    """Application-service boundary suitable for future HTTP route handlers."""

    def __init__(self, repository):
        self.repository=repository

    def create_job(self, *, job_number, project_name, project_type, source,
                   property_address=None, client_id=None):
        if self.repository.exists(job_number):
            raise ValueError("job number already exists")
        job=create_job_record(
            job_number=job_number,project_name=project_name,
            project_type=project_type,source=source,
            property_address=property_address,client_id=client_id)
        self.repository.save(job)
        return unified_job_view(job=job)

    def get_job(self, job_number):
        return unified_job_view(job=self.repository.get(job_number))

    def list_jobs(self, *, state=None):
        return [unified_job_view(job=x)
                for x in self.repository.list_jobs(state=state)]

    def connect_section(self, *, job_number, section, reference_id,
                        summary=None, authorized_by=None):
        current=self.repository.get(job_number)
        expected=current["version"]
        updated=attach_section(
            job=current,section=section,reference_id=reference_id,
            summary=summary,authorized_by=authorized_by)
        self.repository.save(updated,expected_version=expected)
        return unified_job_view(job=updated)

    def change_state(self, *, job_number, state, authorized_by, reason=None):
        current=self.repository.get(job_number)
        expected=current["version"]
        updated=set_job_state(
            job=current,state=state,authorized_by=authorized_by,reason=reason)
        self.repository.save(updated,expected_version=expected)
        return unified_job_view(job=updated)

    def add_event(self, *, job_number, event_type, reference_id=None, summary=None):
        current=self.repository.get(job_number)
        expected=current["version"]
        updated=record_job_event(
            job=current,event_type=event_type,
            reference_id=reference_id,summary=summary)
        self.repository.save(updated,expected_version=expected)
        return unified_job_view(job=updated)

def database_api_policy():
    return {
        "database_backed_job_repository":True,
        "repository_contract_preserved":True,
        "application_api_separate_from_storage":True,
        "duplicate_job_numbers_blocked":True,
        "optimistic_concurrency_preserved":True,
        "sqlite_is_local_reference_not_final_production_database":True,
        "midra_engineering_only":True,
    }
