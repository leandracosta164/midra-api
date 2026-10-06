"""MIDRA Engineering workspace/dashboard product contract.

Transforms a persistent Engineering Job into the practical workspace the user will open.
The workspace remains an operational projection: it never silently marks professional
work approved, corrected, complete, or ready for issue.
"""
from copy import deepcopy
from app.repositories.engineering_job import SQLAlchemyEngineeringJobRepository
from app.services.engineering_persistent_command_center import job_to_command_center_card

WORKSPACE_SECTIONS=(
    "workflow","workspace","design","submissions","reviews",
    "post_completion_work","project_completion","project_closure","project_archive","warranty_issues","closeout","punch_list","change_orders","submittals","rfis","field_reports","meetings","milestones","correspondence","billing","client_portal","command_center"
)

def engineering_workspace(job):
    sections=job.sections or {}
    card=job_to_command_center_card(job)
    connected={}
    summaries={}
    for name in WORKSPACE_SECTIONS:
        value=sections.get(name)
        if value:
            connected[name]=value.get("reference_id")
            summaries[name]=deepcopy(value.get("summary",{}))

    action_items=deepcopy(((sections.get("action_items") or {}).get("summary",{}).get("items",[])))
    dependencies=deepcopy(((sections.get("dependencies") or {}).get("summary",{}).get("items",[])))
    reviews=deepcopy(((sections.get("reviews") or {}).get("summary",{}).get("items",[])))
    packages=deepcopy(((sections.get("submission_packages") or {}).get("summary",{}).get("items",[])))

    attention_items=[]
    for item in action_items:
        if item.get("status") in {"OPEN","IN_PROGRESS","BLOCKED"}:
            attention_items.append({
                "kind":"ACTION","reference_id":item.get("action_id"),"title":item.get("title"),
                "status":item.get("status"),"due_at":item.get("due_at"),
                "priority":item.get("priority","NORMAL"),"owner":item.get("owner"),
                "message":"Action requires project work.",
            })
    for item in dependencies:
        if item.get("status") in {"WAITING","FOLLOW_UP_DUE"}:
            attention_items.append({
                "kind":"DEPENDENCY","reference_id":item.get("dependency_id"),"title":item.get("title"),
                "status":item.get("status"),"due_at":item.get("follow_up_at") or item.get("due_at"),
                "priority":"HIGH" if item.get("status")=="FOLLOW_UP_DUE" else "NORMAL",
                "owner":item.get("waiting_on"),"message":"Project is waiting on another party.",
            })
    for review in reviews:
        open_comments=[c for c in review.get("comments",[]) if c.get("requires_action",True) and c.get("status") not in {"VERIFIED","NOT_APPLICABLE"}]
        if open_comments:
            attention_items.append({
                "kind":"REVIEW","reference_id":review.get("review_id"),"title":review.get("title"),
                "status":"OPEN_COMMENTS","due_at":review.get("due_at"),"priority":"HIGH",
                "owner":review.get("reviewer"),"message":f"{len(open_comments)} review comment(s) remain unresolved.",
            })
    for item in packages:
        if item.get("status") in {"READY","RETURNED"}:
            attention_items.append({
                "kind":"SUBMISSION","reference_id":item.get("package_id"),"title":item.get("title"),
                "status":item.get("status"),"due_at":item.get("due_at"),
                "priority":"HIGH" if item.get("status")=="RETURNED" else "NORMAL",
                "owner":item.get("recipient"),"message":"Submission package requires attention.",
            })
    priority_order={"URGENT":0,"HIGH":1,"NORMAL":2,"LOW":3}
    attention_items.sort(key=lambda x:(priority_order.get(x.get("priority","NORMAL"),2),x.get("due_at") or "9999-12-31",x.get("title") or ""))
    attention_summary={
        "items":attention_items,"count":len(attention_items),
        "urgent_count":sum(1 for x in attention_items if x.get("priority")=="URGENT"),
        "high_count":sum(1 for x in attention_items if x.get("priority")=="HIGH"),
    }

    primary=attention_items[0] if attention_items else None
    if primary is None:
        next_move={
            "type":"NONE","reference_id":None,"title":"No immediate action required",
            "message":"No current workflow record requires action or follow-up.",
            "owner":None,"due_at":None,"priority":"NORMAL",
        }
    elif primary.get("kind")=="ACTION":
        next_move={
            "type":"DO_WORK","reference_id":primary.get("reference_id"),
            "title":primary.get("title"),"message":"Complete or advance the highest-priority action item.",
            "owner":primary.get("owner"),"due_at":primary.get("due_at"),"priority":primary.get("priority","NORMAL"),
        }
    elif primary.get("kind")=="DEPENDENCY":
        next_move={
            "type":"FOLLOW_UP" if primary.get("status")=="FOLLOW_UP_DUE" else "WAIT",
            "reference_id":primary.get("reference_id"),"title":primary.get("title"),
            "message":"Follow up on this dependency." if primary.get("status")=="FOLLOW_UP_DUE" else "No internal work is created while this external dependency is pending.",
            "owner":primary.get("owner"),"due_at":primary.get("due_at"),"priority":primary.get("priority","NORMAL"),
        }
    elif primary.get("kind")=="REVIEW":
        next_move={
            "type":"ADDRESS_REVIEW","reference_id":primary.get("reference_id"),
            "title":primary.get("title"),"message":primary.get("message"),
            "owner":primary.get("owner"),"due_at":primary.get("due_at"),"priority":primary.get("priority","HIGH"),
        }
    else:
        next_move={
            "type":"ADVANCE_SUBMISSION","reference_id":primary.get("reference_id"),
            "title":primary.get("title"),"message":"Advance the submission package based on its current status.",
            "owner":primary.get("owner"),"due_at":primary.get("due_at"),"priority":primary.get("priority","NORMAL"),
        }

    active_actions=[a for a in action_items if a.get("status") in {"OPEN","IN_PROGRESS","BLOCKED"}]
    blocked_actions=[a for a in active_actions if a.get("status")=="BLOCKED"]
    waiting_dependencies=[d for d in dependencies if d.get("status") in {"WAITING","FOLLOW_UP_DUE"}]
    followups=[d for d in waiting_dependencies if d.get("status")=="FOLLOW_UP_DUE"]
    unresolved_reviews=[
        r for r in reviews
        if any(c.get("requires_action",True) and c.get("status") not in {"VERIFIED","NOT_APPLICABLE"}
               for c in r.get("comments",[]))
    ]
    returned_packages=[p for p in packages if p.get("status")=="RETURNED"]

    health_signals=[]
    if blocked_actions:
        health_signals.append({"type":"BLOCKED_ACTIONS","count":len(blocked_actions),"message":f"{len(blocked_actions)} action item(s) are blocked."})
    if followups:
        health_signals.append({"type":"FOLLOW_UP_DUE","count":len(followups),"message":f"{len(followups)} external follow-up(s) are due."})
    if returned_packages:
        health_signals.append({"type":"RETURNED_SUBMISSIONS","count":len(returned_packages),"message":f"{len(returned_packages)} submission package(s) were returned."})
    if unresolved_reviews:
        health_signals.append({"type":"UNRESOLVED_REVIEWS","count":len(unresolved_reviews),"message":f"{len(unresolved_reviews)} review cycle(s) contain unresolved actionable comments."})
    if active_actions:
        health_signals.append({"type":"ACTIVE_ACTIONS","count":len(active_actions),"message":f"{len(active_actions)} action item(s) remain active."})
    if waiting_dependencies:
        health_signals.append({"type":"WAITING_DEPENDENCIES","count":len(waiting_dependencies),"message":f"{len(waiting_dependencies)} external dependency item(s) remain pending."})

    if blocked_actions or returned_packages:
        health_state="BLOCKED_OR_RETURNED"
        health_message="Recorded workflow contains blocked work or a returned submission."
    elif followups or unresolved_reviews:
        health_state="ATTENTION_REQUIRED"
        health_message="Recorded workflow contains follow-up or unresolved review work."
    elif active_actions or waiting_dependencies:
        health_state="ACTIVE"
        health_message="Project workflow is active with recorded work or external dependencies."
    else:
        health_state="CLEAR"
        health_message="No active workflow exception is currently recorded."

    project_health={
        "state":health_state,
        "message":health_message,
        "signals":health_signals,
        "counts":{
            "active_actions":len(active_actions),
            "blocked_actions":len(blocked_actions),
            "waiting_dependencies":len(waiting_dependencies),
            "follow_up_due":len(followups),
            "unresolved_reviews":len(unresolved_reviews),
            "returned_submissions":len(returned_packages),
        },
    }

    project_brief={
        "headline":next_move.get("title") or "No immediate action required",
        "workflow_state":project_health.get("state"),
        "workflow_message":project_health.get("message"),
        "next_move_type":next_move.get("type"),
        "next_move_message":next_move.get("message"),
        "next_move_owner":next_move.get("owner"),
        "next_move_due_at":next_move.get("due_at"),
        "attention_count":attention_summary.get("count",0),
        "high_attention_count":attention_summary.get("high_count",0),
        "urgent_attention_count":attention_summary.get("urgent_count",0),
        "active_action_count":project_health.get("counts",{}).get("active_actions",0),
        "waiting_dependency_count":project_health.get("counts",{}).get("waiting_dependencies",0),
        "unresolved_review_count":project_health.get("counts",{}).get("unresolved_reviews",0),
        "returned_submission_count":project_health.get("counts",{}).get("returned_submissions",0),
        "summary_lines":[
            project_health.get("message"),
            next_move.get("message"),
        ],
    }

    # 8.7 Agent-Ready Contract
    # This is a deterministic read model over the same workflow projections used by
    # the UI. It gives future MIDRA Intelligence a stable, structured context
    # without duplicating business logic or granting autonomous professional action.
    agent_context={
        "schema":"midra.engineering.agent_context",
        "schema_version":"1.0",
        "mode":"READ_ONLY",
        "project_ref":{
            "job_number":job.job_number,
            "project_name":job.project_name,
            "project_type":job.project_type,
        },
        "brief":deepcopy(project_brief),
        "health":deepcopy(project_health),
        "attention":deepcopy(attention_summary),
        "next_move":deepcopy(next_move),
        "guardrails":{
            "professional_actions_require_approval":True,
            "automatic_professional_completion":False,
            "automatic_issue_or_submission":False,
            "may_invent_project_work":False,
        },
        "capabilities":{
            "read_project_context":True,
            "propose_next_steps":True,
            "execute_professional_action":False,
            "issue_or_submit":False,
        },
        # 8.8 Machine-readable operation boundary for future MIDRA Intelligence.
        # These are policy classifications, not claims that an AI action tool exists.
        "operation_policy":{
            "READ_PROJECT_CONTEXT":{
                "classification":"READ_ONLY_ALLOWED",
                "changes_project_state":False,
                "requires_human_approval":False,
            },
            "PROPOSE_NEXT_STEP":{
                "classification":"PROPOSAL_ONLY",
                "changes_project_state":False,
                "requires_human_approval":False,
            },
            "MUTATE_PROJECT_RECORD":{
                "classification":"APPROVAL_REQUIRED",
                "changes_project_state":True,
                "requires_human_approval":True,
            },
            "PROFESSIONAL_APPROVAL":{
                "classification":"HUMAN_PROFESSIONAL_ONLY",
                "changes_project_state":True,
                "requires_human_approval":True,
            },
            "ISSUE_OR_SUBMIT":{
                "classification":"HUMAN_AUTHORIZATION_REQUIRED",
                "changes_project_state":True,
                "requires_human_approval":True,
            },
        },
        "agent_contract":{
            "default_effect":"NO_CHANGE",
            "unknown_operation":"DENY",
            "approval_must_be_explicit":True,
            "recorded_workflow_is_source_of_truth":True,
        },
        # 8.9 Human Control Contract: model-agnostic, explicit, scoped,
        # revocable authorization. MIDRA policy remains authoritative.
        "human_control":{
            "control_owner":"MIDRA_USER",
            "ai_provider_authority":"NONE",
            "authorization_model":"EXPLICIT_SCOPED",
            "authorization_defaults":{
                "state_change":"DENY",
                "external_communication":"DENY",
                "issue_or_submit":"DENY",
                "professional_approval":"DENY",
            },
            "authorization_rules":{
                "must_identify_operation":True,
                "must_identify_target":True,
                "must_be_current":True,
                "may_be_revoked":True,
                "may_not_be_inferred_from_prior_approval":True,
                "may_not_expand_scope":True,
            },
            "audit_requirements":{
                "record_state_changes":True,
                "record_authorization":True,
                "record_actor":True,
                "record_timestamp":True,
                "record_result":True,
            },
            "provider_portability":{
                "model_agnostic":True,
                "provider_may_not_override_midra_policy":True,
                "provider_may_not_be_source_of_truth":True,
            },
            # 9.0 exposes the current control posture as a compact,
            # read-only projection for future clients/agents.
            "control_summary":{
                "mode":"HUMAN_CONTROLLED",
                "state_changes":"EXPLICIT_AUTHORIZATION_REQUIRED",
                "external_actions":"EXPLICIT_AUTHORIZATION_REQUIRED",
                "professional_actions":"HUMAN_PROFESSIONAL_ONLY",
                "unknown_actions":"DENY",
            },
            # 9.1 describes what an authorization must contain.
            # This is a contract only; it does not create or grant authorization.
            "authorization_requirements":{
                "schema":"midra.engineering.authorization_requirements",
                "schema_version":"1.0",
                "required_fields":[
                    "operation",
                    "target",
                    "authorized_by",
                    "authorized_at",
                ],
                "scope_rules":{
                    "operation_required":True,
                    "target_required":True,
                    "actor_required":True,
                    "timestamp_required":True,
                    "authorization_must_be_current":True,
                    "reuse_for_other_operation":False,
                    "reuse_for_other_target":False,
                },
                "missing_or_invalid_authorization":"DENY",
            },
            # 9.2 defines the immutable audit evidence expected whenever a
            # future authorized operation changes state or reaches outside MIDRA.
            "authorization_audit_contract":{
                "schema":"midra.engineering.authorization_audit",
                "schema_version":"1.0",
                "record_required_for":[
                    "STATE_CHANGE",
                    "EXTERNAL_ACTION",
                    "ISSUE_OR_SUBMIT",
                ],
                "required_evidence":[
                    "operation",
                    "target",
                    "authorized_by",
                    "authorized_at",
                    "actor",
                    "executed_at",
                    "result",
                ],
                "recording_rules":{
                    "record_before_and_after_state_when_applicable":True,
                    "record_authorization_reference":True,
                    "record_provider_when_ai_assisted":True,
                    "record_failure_result":True,
                    "silent_execution":False,
                },
                "professional_approval_record":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 9.3 defines the lifecycle of an explicit authorization.
            # Authorization is temporary, scoped, revocable, and never self-renewing.
            "authorization_lifecycle":{
                "schema":"midra.engineering.authorization_lifecycle",
                "schema_version":"1.0",
                "states":[
                    "NOT_AUTHORIZED",
                    "AUTHORIZED",
                    "CONSUMED",
                    "REVOKED",
                    "EXPIRED",
                ],
                "initial_state":"NOT_AUTHORIZED",
                "terminal_states":[
                    "CONSUMED",
                    "REVOKED",
                    "EXPIRED",
                ],
                "rules":{
                    "explicit_grant_required":True,
                    "authorization_is_single_scope":True,
                    "may_be_revoked_before_execution":True,
                    "consumed_after_authorized_execution":True,
                    "terminal_state_may_not_execute":True,
                    "automatic_renewal":False,
                    "prior_authorization_may_not_reactivate":False,
                },
                "invalid_or_unknown_state":"DENY",
            },
            # 9.4 defines the fail-closed validation gates that a future
            # authorization must satisfy before any controlled action can proceed.
            "authorization_validation":{
                "schema":"midra.engineering.authorization_validation",
                "schema_version":"1.0",
                "required_checks":[
                    "authorization_present",
                    "state_is_authorized",
                    "operation_matches",
                    "target_matches",
                    "authorizing_actor_present",
                    "authorization_is_current",
                    "authorization_not_revoked",
                    "authorization_not_consumed",
                    "authorization_not_expired",
                ],
                "decision_rule":"ALL_CHECKS_MUST_PASS",
                "on_failed_check":"DENY",
                "on_missing_check":"DENY",
                "on_unknown_check":"DENY",
                "provider_may_bypass_validation":False,
            },
            # 10.7 produces an explicit ALLOW/DENY decision only after every
            # delegation validation check passes; providers cannot override it.
            "delegation_decision":{
                "schema":"midra.engineering.delegation_decision",
                "schema_version":"1.0",
                "possible_decisions":[
                    "ALLOW",
                    "DENY",
                ],
                "allow_requires":"ALL_DELEGATION_VALIDATION_CHECKS_PASS",
                "deny_when":[
                    "VALIDATION_FAILED",
                    "VALIDATION_MISSING",
                    "VALIDATION_UNKNOWN",
                    "DELEGATION_NOT_ACTIVE",
                    "DELEGATION_NOT_CURRENT",
                ],
                "decision_scope":{
                    "delegator_specific":True,
                    "delegate_specific":True,
                    "operation_specific":True,
                    "target_specific":True,
                    "single_use":True,
                    "scope_expansion":False,
                },
                "default_decision":"DENY",
                "provider_may_override_decision":False,
            },
            # 10.8 binds a delegation decision to the same controlled-operation
            # identity so delegation cannot be transferred to another operation.
            "delegation_operation_binding":{
                "schema":"midra.engineering.delegation_operation_binding",
                "schema_version":"1.0",
                "required_bindings":[
                    "operation_id",
                    "delegator_actor_id",
                    "delegate_actor_id",
                    "operation",
                    "target",
                    "delegation_decision",
                ],
                "binding_rules":{
                    "operation_id_must_match_controlled_operation":True,
                    "delegator_must_match_delegation":True,
                    "delegate_must_match_execution_actor":True,
                    "operation_must_match_authorized_operation":True,
                    "target_must_match_authorized_target":True,
                    "decision_must_be_allow":True,
                    "binding_is_single_operation":True,
                    "binding_may_not_transfer":True,
                },
                "missing_or_mismatched_binding":"DENY",
                "provider_may_rebind_operation":False,
            },
            # 10.9 defines how delegated authority is consumed after a future
            # controlled operation attempt, preventing reuse of the same delegation.
            "delegation_consumption":{
                "schema":"midra.engineering.delegation_consumption",
                "schema_version":"1.0",
                "consumption_trigger":"CONTROLLED_OPERATION_ATTEMPT",
                "required_evidence":[
                    "operation_id",
                    "delegator_actor_id",
                    "delegate_actor_id",
                    "delegation_decision",
                    "attempted_at",
                    "result",
                ],
                "consumption_rules":{
                    "allow_decision_required":True,
                    "matching_operation_binding_required":True,
                    "consume_after_attempt":True,
                    "consume_on_success":True,
                    "consume_on_failure":True,
                    "consume_on_denied_execution_attempt":True,
                    "consumed_delegation_may_not_be_reused":True,
                    "consumption_may_not_expand_scope":True,
                    "consumption_may_not_grant_authority":True,
                },
                "missing_consumption_evidence":"CONTROL_VIOLATION",
                "provider_may_restore_consumed_delegation":False,
            },
            # 11.0 provides one read-only summary of delegation control state
            # without creating, validating, consuming, or granting delegation.
            "delegation_control_status":{
                "schema":"midra.engineering.delegation_control_status",
                "schema_version":"1.0",
                "control_chain":[
                    "DELEGATE",
                    "ACTIVATE",
                    "VALIDATE",
                    "DECIDE",
                    "BIND_OPERATION",
                    "CONSUME",
                ],
                "status_fields":[
                    "delegation_state",
                    "delegator_actor_id",
                    "delegate_actor_id",
                    "operation_id",
                    "operation",
                    "target",
                    "decision",
                    "consumption_state",
                ],
                "projection_rules":{
                    "read_only":True,
                    "recorded_evidence_only":True,
                    "unknown_value":"UNKNOWN",
                    "missing_value":"NOT_RECORDED",
                    "may_not_infer_delegation":True,
                    "may_not_infer_authority":True,
                    "may_not_reactivate_consumed_delegation":True,
                    "may_not_grant_authority":True,
                },
                "professional_delegation_status":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.1 defines explicit revocation controls so an active delegation
            # can be withdrawn before use without deleting its audit history.
            "delegation_revocation":{
                "schema":"midra.engineering.delegation_revocation",
                "schema_version":"1.0",
                "required_fields":[
                    "operation_id",
                    "delegated_by",
                    "delegated_to",
                    "revoked_by",
                    "revoked_at",
                    "reason",
                ],
                "revocation_rules":{
                    "active_delegation_required":True,
                    "revoker_authority_required":True,
                    "revocation_is_immediate":True,
                    "revocation_preserves_history":True,
                    "revoked_delegation_may_not_execute":True,
                    "revoked_delegation_may_not_reactivate":True,
                    "revocation_may_not_expand_scope":True,
                    "revocation_may_not_grant_authority":True,
                },
                "missing_or_invalid_revocation":"DENY",
                "provider_may_revoke_or_restore_delegation":False,
                "professional_revocation":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.2 defines time-bounded delegation expiration so delegated
            # authority cannot remain active indefinitely or renew itself.
            "delegation_expiration":{
                "schema":"midra.engineering.delegation_expiration",
                "schema_version":"1.0",
                "required_fields":[
                    "operation_id",
                    "delegated_by",
                    "delegated_to",
                    "effective_at",
                    "expires_at",
                ],
                "expiration_rules":{
                    "expires_at_required":True,
                    "expires_at_after_effective_at":True,
                    "expired_delegation_may_not_execute":True,
                    "expiration_is_automatic_at_boundary":True,
                    "automatic_renewal":False,
                    "expired_delegation_may_not_reactivate":True,
                    "new_explicit_delegation_required_after_expiration":True,
                    "expiration_preserves_history":True,
                    "expiration_may_not_grant_authority":True,
                },
                "missing_or_invalid_expiration":"DENY",
                "provider_may_extend_or_renew_delegation":False,
                "professional_expiration":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.3 defines delegation evidence integrity so the recorded grant,
            # lifecycle, decision, binding, and consumption remain traceably linked.
            "delegation_evidence_integrity":{
                "schema":"midra.engineering.delegation_evidence_integrity",
                "schema_version":"1.0",
                "required_evidence":[
                    "delegation_record",
                    "delegation_lifecycle_record",
                    "delegation_validation_record",
                    "delegation_decision_record",
                    "operation_binding_record",
                    "consumption_or_terminal_state_record",
                ],
                "integrity_rules":{
                    "same_operation_id_required":True,
                    "same_delegator_required":True,
                    "same_delegate_required":True,
                    "same_operation_required":True,
                    "same_target_required":True,
                    "chronological_consistency_required":True,
                    "terminal_state_may_not_be_overwritten":True,
                    "evidence_may_not_be_silently_replaced":True,
                    "integrity_check_may_not_grant_authority":True,
                },
                "on_missing_evidence":"NOT_VERIFIED",
                "on_mismatched_evidence":"DISCREPANCY",
                "provider_may_rewrite_evidence":False,
                "professional_evidence_integrity":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.4 defines the final read-only completion state for a delegation
            # after its evidence chain reaches a valid terminal condition.
            "delegation_completion":{
                "schema":"midra.engineering.delegation_completion",
                "schema_version":"1.0",
                "completion_states":[
                    "INCOMPLETE",
                    "COMPLETE",
                    "REQUIRES_REVIEW",
                ],
                "required_conditions":[
                    "delegation_record_present",
                    "delegation_identity_consistent",
                    "delegation_terminal_state_recorded",
                    "operation_binding_consistent_when_used",
                    "consumption_evidence_present_when_used",
                    "no_open_delegation_discrepancy",
                ],
                "completion_rules":{
                    "default_state":"INCOMPLETE",
                    "all_required_conditions_for_complete":True,
                    "open_discrepancy_state":"REQUIRES_REVIEW",
                    "missing_evidence_state":"INCOMPLETE",
                    "completion_is_read_only":True,
                    "completion_may_not_reactivate_delegation":True,
                    "completion_may_not_grant_authority":True,
                    "completion_may_not_imply_professional_approval":True,
                },
                "professional_completion":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.5 defines a compact read-only readiness projection for future
            # controlled actions. Readiness summarizes evidence; it never authorizes.
            "controlled_action_readiness":{
                "schema":"midra.engineering.controlled_action_readiness",
                "schema_version":"1.0",
                "readiness_states":[
                    "NOT_READY",
                    "READY_FOR_HUMAN_AUTHORIZATION",
                    "REQUIRES_REVIEW",
                ],
                "required_signals":[
                    "operation_identity_defined",
                    "actor_identity_defined",
                    "target_defined",
                    "applicable_control_contracts_present",
                    "no_open_control_discrepancy",
                ],
                "readiness_rules":{
                    "default_state":"NOT_READY",
                    "all_required_signals_for_ready":True,
                    "open_discrepancy_state":"REQUIRES_REVIEW",
                    "missing_signal_state":"NOT_READY",
                    "ready_state_does_not_authorize_execution":True,
                    "ready_state_requires_separate_explicit_authorization":True,
                    "readiness_is_read_only":True,
                    "readiness_may_not_grant_authority":True,
                    "readiness_may_not_imply_professional_approval":True,
                },
                "provider_may_promote_readiness_to_authority":False,
                "professional_readiness":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.6 defines the structured request presented for explicit human
            # authorization after an action is ready; the request grants no authority.
            "controlled_action_request":{
                "schema":"midra.engineering.controlled_action_request",
                "schema_version":"1.0",
                "required_fields":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "actor_type",
                    "requested_by",
                    "requested_at",
                    "purpose",
                ],
                "request_rules":{
                    "readiness_must_be_ready_for_human_authorization":True,
                    "operation_identity_must_match":True,
                    "target_must_match":True,
                    "actor_identity_must_match":True,
                    "purpose_required":True,
                    "request_is_not_authorization":True,
                    "request_may_not_execute":True,
                    "request_may_not_expand_scope":True,
                    "request_may_not_grant_authority":True,
                },
                "missing_or_mismatched_request":"DENY",
                "provider_may_self_approve_request":False,
                "professional_request":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.7 defines the read-only review projection shown to the human
            # before authorization; review cannot approve or execute the request.
            "controlled_action_review":{
                "schema":"midra.engineering.controlled_action_review",
                "schema_version":"1.0",
                "review_states":[
                    "PENDING_HUMAN_REVIEW",
                    "READY_FOR_DECISION",
                    "REQUIRES_CORRECTION",
                ],
                "review_fields":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "actor_type",
                    "requested_by",
                    "requested_at",
                    "purpose",
                    "readiness_state",
                ],
                "review_rules":{
                    "request_identity_must_match":True,
                    "request_scope_must_match":True,
                    "readiness_state_must_be_visible":True,
                    "missing_or_mismatched_context_requires_correction":True,
                    "review_is_read_only":True,
                    "review_is_not_authorization":True,
                    "review_may_not_execute":True,
                    "review_may_not_grant_authority":True,
                    "review_may_not_imply_professional_approval":True,
                },
                "provider_may_approve_from_review":False,
                "professional_review":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.8 defines the explicit human decision on a reviewed controlled
            # action request. Only an APPROVE decision may proceed to authorization.
            "controlled_action_review_decision":{
                "schema":"midra.engineering.controlled_action_review_decision",
                "schema_version":"1.0",
                "decision_states":[
                    "APPROVE",
                    "REJECT",
                    "RETURN_FOR_CORRECTION",
                ],
                "required_fields":[
                    "operation_id",
                    "decision",
                    "decided_by",
                    "decided_at",
                ],
                "decision_rules":{
                    "human_decision_required":True,
                    "review_state_must_be_ready_for_decision":True,
                    "operation_identity_must_match":True,
                    "approve_may_proceed_to_authorization":True,
                    "approve_is_not_authorization":True,
                    "reject_may_not_proceed":True,
                    "return_for_correction_may_not_proceed":True,
                    "decision_may_not_execute":True,
                    "decision_may_not_expand_scope":True,
                    "decision_may_not_grant_authority":True,
                },
                "missing_or_invalid_decision":"DENY",
                "provider_may_make_human_decision":False,
                "professional_decision":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 11.9 binds an approved review decision to the existing explicit
            # authorization controls; approval alone never becomes authorization.
            "controlled_action_authorization_binding":{
                "schema":"midra.engineering.controlled_action_authorization_binding",
                "schema_version":"1.0",
                "required_bindings":[
                    "operation_id",
                    "review_decision",
                    "authorized_operation",
                    "authorized_target",
                    "authorized_actor",
                    "authorization_state",
                ],
                "binding_rules":{
                    "review_decision_must_be_approve":True,
                    "authorization_must_be_separate_and_explicit":True,
                    "operation_id_must_match":True,
                    "operation_must_match":True,
                    "target_must_match":True,
                    "actor_must_match":True,
                    "authorization_state_must_be_authorized":True,
                    "binding_may_not_expand_scope":True,
                    "binding_may_not_transfer":True,
                    "binding_may_not_grant_authority":True,
                },
                "missing_or_mismatched_binding":"DENY",
                "provider_may_create_or_override_authorization_binding":False,
                "professional_authorization_binding":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.0 defines the final pre-execution gate. It evaluates whether the
            # reviewed request and explicit authorization are aligned; it never executes.
            "controlled_action_execution_gate":{
                "schema":"midra.engineering.controlled_action_execution_gate",
                "schema_version":"1.0",
                "gate_states":[
                    "BLOCKED",
                    "ELIGIBLE_FOR_CONTROLLED_EXECUTION",
                    "REQUIRES_REVIEW",
                ],
                "required_conditions":[
                    "review_decision_is_approve",
                    "authorization_binding_valid",
                    "authorization_state_is_authorized",
                    "operation_identity_matches",
                    "target_matches",
                    "actor_matches",
                    "no_open_control_discrepancy",
                ],
                "gate_rules":{
                    "default_state":"BLOCKED",
                    "all_required_conditions_for_eligibility":True,
                    "missing_condition_state":"BLOCKED",
                    "open_discrepancy_state":"REQUIRES_REVIEW",
                    "eligibility_is_not_execution":True,
                    "eligibility_may_not_bypass_controlled_execution_contract":True,
                    "gate_is_read_only":True,
                    "gate_may_not_expand_scope":True,
                    "gate_may_not_grant_authority":True,
                },
                "provider_may_open_or_override_gate":False,
                "professional_execution_gate":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.1 defines the immutable envelope handed to a future controlled
            # executor after the execution gate is eligible. The envelope cannot execute.
            "controlled_execution_envelope":{
                "schema":"midra.engineering.controlled_execution_envelope",
                "schema_version":"1.0",
                "required_fields":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "actor_type",
                    "authorization_reference",
                    "authorization_state",
                    "execution_gate_state",
                    "prepared_at",
                ],
                "envelope_rules":{
                    "execution_gate_must_be_eligible":True,
                    "authorization_state_must_be_authorized":True,
                    "operation_identity_must_match":True,
                    "operation_must_match":True,
                    "target_must_match":True,
                    "actor_must_match":True,
                    "authorization_reference_required":True,
                    "envelope_is_immutable_after_preparation":True,
                    "envelope_is_not_execution":True,
                    "envelope_may_not_expand_scope":True,
                    "envelope_may_not_grant_authority":True,
                },
                "missing_or_mismatched_envelope":"DENY",
                "provider_may_rewrite_or_self_authorize_envelope":False,
                "professional_execution_envelope":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.2 validates the immutable execution envelope immediately before
            # any future executor may attempt the controlled operation.
            "controlled_execution_preflight":{
                "schema":"midra.engineering.controlled_execution_preflight",
                "schema_version":"1.0",
                "preflight_states":[
                    "NOT_CLEARED",
                    "CLEARED_FOR_EXECUTION_ATTEMPT",
                    "REQUIRES_REVIEW",
                ],
                "required_checks":[
                    "execution_envelope_present",
                    "execution_envelope_immutable",
                    "execution_gate_is_eligible",
                    "authorization_state_is_authorized",
                    "authorization_is_current",
                    "operation_identity_matches",
                    "operation_matches",
                    "target_matches",
                    "actor_matches",
                    "no_open_control_discrepancy",
                ],
                "preflight_rules":{
                    "default_state":"NOT_CLEARED",
                    "all_required_checks_must_pass":True,
                    "failed_or_missing_check_state":"NOT_CLEARED",
                    "open_discrepancy_state":"REQUIRES_REVIEW",
                    "clearance_is_single_attempt":True,
                    "clearance_is_not_execution":True,
                    "clearance_may_not_bypass_controlled_execution_contract":True,
                    "preflight_is_read_only":True,
                    "preflight_may_not_expand_scope":True,
                    "preflight_may_not_grant_authority":True,
                },
                "provider_may_clear_or_override_preflight":False,
                "professional_execution_preflight":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.3 defines the single-use permit issued only after preflight is
            # cleared. The permit authorizes no action beyond the exact controlled attempt.
            "controlled_execution_permit":{
                "schema":"midra.engineering.controlled_execution_permit",
                "schema_version":"1.0",
                "permit_states":[
                    "NOT_ISSUED",
                    "ISSUED",
                    "CONSUMED",
                    "INVALIDATED",
                ],
                "required_fields":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "authorization_reference",
                    "preflight_state",
                    "issued_by",
                    "issued_at",
                ],
                "permit_rules":{
                    "preflight_must_be_cleared_for_execution_attempt":True,
                    "authorization_must_be_current":True,
                    "operation_identity_must_match":True,
                    "operation_must_match":True,
                    "target_must_match":True,
                    "actor_must_match":True,
                    "permit_is_single_use":True,
                    "permit_consumed_on_execution_attempt":True,
                    "permit_cannot_be_reused":True,
                    "permit_cannot_expand_scope":True,
                    "permit_cannot_transfer":True,
                    "permit_does_not_imply_success":True,
                },
                "missing_or_invalid_permit":"DENY",
                "provider_may_issue_restore_or_expand_permit":False,
                "professional_execution_permit":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.4 defines the atomic boundary around one controlled execution
            # attempt. It requires an issued permit and records the attempt without
            # claiming success, verification, or professional approval.
            "controlled_execution_attempt":{
                "schema":"midra.engineering.controlled_execution_attempt",
                "schema_version":"1.0",
                "attempt_states":[
                    "NOT_ATTEMPTED",
                    "ATTEMPTED",
                    "DENIED",
                ],
                "required_evidence":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "permit_state",
                    "attempted_at",
                    "attempt_result",
                ],
                "attempt_rules":{
                    "permit_must_be_issued":True,
                    "operation_identity_must_match":True,
                    "operation_must_match":True,
                    "target_must_match":True,
                    "actor_must_match":True,
                    "attempt_consumes_permit":True,
                    "attempt_result_must_be_recorded":True,
                    "attempt_does_not_imply_success":True,
                    "attempt_does_not_imply_verification":True,
                    "attempt_may_not_expand_scope":True,
                    "attempt_may_not_grant_authority":True,
                    "missing_or_invalid_permit_denies_attempt":True,
                },
                "provider_may_self_authorize_or_bypass_attempt_boundary":False,
                "professional_execution_attempt":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.5 defines the evidence boundary immediately after a controlled
            # execution attempt. It captures outcome evidence without deciding verification.
            "controlled_execution_outcome":{
                "schema":"midra.engineering.controlled_execution_outcome",
                "schema_version":"1.0",
                "outcome_states":[
                    "NOT_RECORDED",
                    "SUCCEEDED",
                    "FAILED",
                    "DENIED",
                ],
                "required_evidence":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "attempted_at",
                    "attempt_result",
                    "recorded_at",
                ],
                "outcome_rules":{
                    "execution_attempt_must_be_recorded":True,
                    "operation_identity_must_match":True,
                    "operation_must_match":True,
                    "target_must_match":True,
                    "actor_must_match":True,
                    "outcome_must_match_attempt_result":True,
                    "failure_and_denial_must_be_preserved":True,
                    "outcome_is_append_only":True,
                    "outcome_does_not_imply_verification":True,
                    "outcome_does_not_imply_completion":True,
                    "outcome_may_not_grant_authority":True,
                },
                "missing_outcome_evidence":"NOT_RECORDED",
                "mismatched_outcome_evidence":"DISCREPANCY",
                "provider_may_rewrite_or_promote_outcome":False,
                "professional_execution_outcome":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.6 binds the new permit/attempt/outcome evidence to MIDRA's
            # existing execution-verification contract. It does not perform verification.
            "controlled_execution_verification_handoff":{
                "schema":"midra.engineering.controlled_execution_verification_handoff",
                "schema_version":"1.0",
                "handoff_states":[
                    "NOT_READY_FOR_VERIFICATION",
                    "READY_FOR_VERIFICATION",
                    "REQUIRES_REVIEW",
                ],
                "required_evidence":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "permit_consumed",
                    "execution_attempt_recorded",
                    "execution_outcome_recorded",
                    "attempt_result",
                    "outcome_state",
                ],
                "handoff_rules":{
                    "operation_identity_must_match":True,
                    "operation_must_match":True,
                    "target_must_match":True,
                    "actor_must_match":True,
                    "permit_must_be_consumed":True,
                    "execution_attempt_must_be_recorded":True,
                    "execution_outcome_must_be_recorded":True,
                    "attempt_and_outcome_must_agree":True,
                    "mismatch_requires_review":True,
                    "handoff_is_not_verification":True,
                    "handoff_may_not_change_outcome":True,
                    "handoff_may_not_grant_authority":True,
                },
                "missing_evidence_state":"NOT_READY_FOR_VERIFICATION",
                "mismatched_evidence_state":"REQUIRES_REVIEW",
                "next_control":"execution_verification",
                "provider_may_verify_rewrite_or_override_handoff":False,
                "professional_verification_handoff":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.7 provides one compact read-only projection across the controlled
            # action path. It reports recorded control state without creating authority.
            "controlled_action_control_status":{
                "schema":"midra.engineering.controlled_action_control_status",
                "schema_version":"1.0",
                "control_path":[
                    "READINESS",
                    "REQUEST",
                    "REVIEW",
                    "REVIEW_DECISION",
                    "AUTHORIZATION_BINDING",
                    "EXECUTION_GATE",
                    "EXECUTION_ENVELOPE",
                    "EXECUTION_PREFLIGHT",
                    "EXECUTION_PERMIT",
                    "EXECUTION_ATTEMPT",
                    "EXECUTION_OUTCOME",
                    "VERIFICATION_HANDOFF",
                    "EXECUTION_VERIFICATION",
                    "OPERATION_COMPLETION",
                ],
                "status_fields":[
                    "operation_id",
                    "operation",
                    "target",
                    "actor_id",
                    "readiness_state",
                    "review_decision",
                    "authorization_state",
                    "execution_gate_state",
                    "preflight_state",
                    "permit_state",
                    "attempt_state",
                    "outcome_state",
                    "verification_handoff_state",
                    "verification_state",
                    "completion_state",
                ],
                "status_rules":{
                    "recorded_evidence_only":True,
                    "unknown_or_missing_state":"NOT_RECORDED",
                    "status_is_read_only":True,
                    "status_may_not_infer_authorization":True,
                    "status_may_not_infer_success":True,
                    "status_may_not_infer_completion":True,
                    "status_may_not_execute":True,
                    "status_may_not_grant_authority":True,
                },
                "provider_may_promote_or_override_status":False,
                "professional_control_status":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.8 closes the controlled-action control sequence as a durable
            # capability boundary. It reuses existing controls instead of adding
            # another execution lifecycle and makes the future agent-facing posture explicit.
            "controlled_action_capability_boundary":{
                "schema":"midra.engineering.controlled_action_capability_boundary",
                "schema_version":"1.0",
                "capability_classes":{
                    "READ_CONTEXT":"READ_ONLY_ALLOWED",
                    "ANALYZE_CONTEXT":"READ_ONLY_ALLOWED",
                    "PROPOSE_ACTION":"PROPOSAL_ONLY",
                    "PREPARE_CONTROLLED_ACTION":"HUMAN_REVIEW_REQUIRED",
                    "AUTHORIZE_ACTION":"HUMAN_ONLY",
                    "EXECUTE_CONTROLLED_ACTION":"EXISTING_CONTROL_CHAIN_REQUIRED",
                    "PROFESSIONAL_APPROVAL":"HUMAN_PROFESSIONAL_ONLY",
                    "ISSUE_OR_SUBMIT":"HUMAN_AUTHORIZATION_REQUIRED",
                },
                "execution_control_chain":[
                    "controlled_action_readiness",
                    "controlled_action_request",
                    "controlled_action_review",
                    "controlled_action_review_decision",
                    "controlled_action_authorization_binding",
                    "controlled_action_execution_gate",
                    "controlled_execution_envelope",
                    "controlled_execution_preflight",
                    "controlled_execution_permit",
                    "controlled_execution_attempt",
                    "controlled_execution_outcome",
                    "controlled_execution_verification_handoff",
                    "execution_verification",
                    "controlled_operation_completion",
                ],
                "boundary_rules":{
                    "midra_is_source_of_truth":True,
                    "business_rules_remain_in_midra":True,
                    "ai_provider_is_replaceable":True,
                    "unknown_capability_denied":True,
                    "no_provider_self_authorization":True,
                    "no_provider_scope_expansion":True,
                    "no_provider_professional_authority":True,
                    "no_second_execution_lifecycle":True,
                    "future_agent_must_use_existing_control_chain":True,
                },
                "ai_provider_authority":"NONE",
                "professional_authority":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 12.9 exposes a model-agnostic tool-access manifest for future
            # MIDRA Intelligence. It describes how an agent may discover/use MIDRA
            # capabilities without granting credentials, authority, or direct DB access.
            "agent_tool_access_manifest":{
                "schema":"midra.engineering.agent_tool_access_manifest",
                "schema_version":"1.0",
                "access_modes":[
                    "READ",
                    "ANALYZE",
                    "PROPOSE",
                    "PREPARE",
                    "CONTROLLED_ACTION",
                ],
                "tool_contract_requirements":[
                    "tool_name",
                    "capability_class",
                    "input_schema",
                    "output_schema",
                    "authorization_requirement",
                    "audit_requirement",
                ],
                "access_rules":{
                    "tools_expose_midra_capabilities_not_database_credentials":True,
                    "tool_access_does_not_grant_authority":True,
                    "tool_access_must_respect_capability_boundary":True,
                    "controlled_actions_use_existing_control_chain":True,
                    "professional_actions_remain_human_professional_only":True,
                    "unknown_tools_denied":True,
                    "provider_specific_credentials_not_required_by_contract":True,
                    "provider_can_be_replaced_without_rewriting_business_rules":True,
                },
                "future_provider_compatibility":[
                    "CLAUDE",
                    "OPENAI",
                    "OTHER_MODEL_PROVIDER",
                ],
                "direct_database_authority":"NONE",
                "ai_provider_authority":"NONE",
            },
            # 13.0 recovery 2: use the exact structured project_ref shape
            # already established by the verified agent_context contract.
            # 13.1 turns existing Project Attention into a compact, deterministic
            # intelligence focus queue. It ranks recorded attention items without
            # inventing tasks or changing project state.
            # 13.2 expands Intelligence reasoning without changing the verified
            # 13.1 Focus Queue contract. The queue describes recorded attention;
            # this sibling contract explicitly says recorded attention is not the
            # boundary of Jarvis/Claude reasoning.
            "intelligence_reasoning_space":{
                "schema":"midra.engineering.intelligence_reasoning_space",
                "schema_version":"1.0",
                "mode":"ADVISORY",
                "purpose":"OPEN_ENDED_REASONING_AND_IDEATION",
                "freedoms":{
                    "generate_new_ideas":True,
                    "propose_unrecorded_work":True,
                    "challenge_existing_priorities":True,
                    "suggest_alternative_workflows":True,
                    "explore_multiple_hypotheses":True,
                    "identify_gaps_and_opportunities":True,
                    "recommend_new_automations":True,
                    "reason_beyond_current_midra_features":True,
                },
                "interpretation":{
                    "focus_queue_is_recorded_midra_attention":True,
                    "focus_queue_is_not_reasoning_boundary":True,
                    "unrecorded_idea_may_be_proposed":True,
                    "unrecorded_idea_must_not_be_claimed_as_existing_record":True,
                },
                "provenance":{
                    "recorded_midra_fact":"MUST_IDENTIFY_AS_RECORDED",
                    "ai_inference":"MUST_IDENTIFY_AS_INFERENCE_WHEN_MATERIAL",
                    "ai_recommendation":"MUST_IDENTIFY_AS_RECOMMENDATION",
                    "ai_generated_idea":"MUST_NOT_BE_PRESENTED_AS_EXISTING_RECORD",
                },
                "action_boundary":{
                    "reasoning_does_not_require_action_authority":True,
                    "creating_an_idea_does_not_change_project_state":True,
                    "consequential_actions_use_existing_control_chain":True,
                    "security_controls_remain_enforced":True,
                    "professional_authority_remains_human":True,
                    "ai_provider_cannot_self_authorize":True,
                },
                "design_rule":"MAXIMIZE_REASONING_FREEDOM_WHILE_PRESERVING_TRUTH_SECURITY_AND_ACTION_CONTROL",
            },
            # 13.3 recovery: safety-only posture. Existing historical contracts
            # remain for compatibility and are not interpreted as a closed capability allowlist.
            "ai_safety_posture":{
                "schema":"midra.engineering.ai_safety_posture",
                "schema_version":"1.0",
                "mode":"SAFETY_ONLY",
                "default_capability_posture":"OPEN",
                "interpretation":{
                    "historical_capability_contracts_are_not_exhaustive":True,
                    "unlisted_future_capabilities_remain_open":True,
                    "normal_reasoning_ideation_analysis_research_and_proposals_remain_open":True,
                    "restrictions_require_a_safety_security_integrity_authorization_legal_or_professional_reason":True,
                },
                "safety_scope":[
                    "SECURITY_AND_CREDENTIAL_PROTECTION",
                    "DATA_INTEGRITY_AND_TRUTHFUL_PROVENANCE",
                    "DESTRUCTIVE_OR_CONSEQUENTIAL_ACTION_CONTROL",
                    "AUTHORIZATION_AND_ACCESS_CONTROL",
                    "LEGAL_AND_PROFESSIONAL_AUTHORITY",
                ],
            },
            "intelligence_focus_queue":{
                "schema":"midra.engineering.intelligence_focus_queue",
                "schema_version":"1.0",
                "mode":"READ_ONLY",
                "purpose":"PRIORITIZED_OPERATIONAL_FOCUS",
                "source":"attention_summary",
                "items":deepcopy(
                    attention_summary.get("items",[])
                    if isinstance(attention_summary,dict)
                    else []
                ),
                "item_count":len(
                    attention_summary.get("items",[])
                    if isinstance(attention_summary,dict)
                    else []
                ),
                "rules":{
                    "recorded_attention_only":True,
                    "preserve_existing_attention_order":True,
                    "no_invented_tasks":True,
                    "no_state_change":True,
                    "no_authorization_granted":True,
                    "no_professional_judgment":True,
                },
                "agent_use":{
                    "may_explain_focus":True,
                    "may_summarize_focus":True,
                    "may_propose_response":True,
                    "may_reorder_source_of_truth":False,
                    "may_execute":False,
                },
            },
            "intelligence_operational_brief":{
                "schema":"midra.engineering.intelligence_operational_brief",
                "schema_version":"1.0",
                "mode":"READ_ONLY",
                "purpose":"OPERATIONAL_BRIEFING",
                "sources":["project_brief","project_health","attention_summary","next_move"],
                "brief":{
                    "project_ref":{
                        "job_number":job.job_number,
                        "project_name":job.project_name,
                        "project_type":job.project_type,
                    },
                    "workflow_condition":project_health.get("state","UNKNOWN"),
                    "next_move":deepcopy(next_move),
                    "attention":deepcopy(attention_summary),
                    "project_brief":deepcopy(project_brief),
                },
                "agent_use":{
                    "may_read":True,"may_analyze":True,"may_summarize":True,
                    "may_propose_next_steps":True,"may_invent_project_facts":False,
                    "may_change_project_state":False,"may_authorize_action":False,
                    "may_execute_action":False,"may_make_professional_approval":False,
                },
                "rules":{
                    "recorded_midra_data_only":True,"midra_remains_source_of_truth":True,
                    "missing_data_must_remain_unknown":True,
                    "no_inferred_approval_or_acceptance":True,
                    "controlled_actions_use_existing_control_chain":True,
                },
            },
            # 9.5 defines the decision produced after authorization validation.
            # The decision is explicit, bounded, and cannot create authority.
            "authorization_decision":{
                "schema":"midra.engineering.authorization_decision",
                "schema_version":"1.0",
                "possible_decisions":[
                    "ALLOW",
                    "DENY",
                ],
                "allow_requires":"ALL_VALIDATION_CHECKS_PASS",
                "deny_when":[
                    "VALIDATION_FAILED",
                    "VALIDATION_MISSING",
                    "VALIDATION_UNKNOWN",
                    "AUTHORIZATION_NOT_CURRENT",
                ],
                "decision_scope":{
                    "operation_specific":True,
                    "target_specific":True,
                    "single_use":True,
                    "scope_expansion":False,
                },
                "default_decision":"DENY",
                "provider_may_override_decision":False,
            },
            # 9.6 defines what happens after an ALLOW decision.
            # Execution remains a separate controlled step and must be recorded.
            "controlled_execution":{
                "schema":"midra.engineering.controlled_execution",
                "schema_version":"1.0",
                "preconditions":[
                    "authorization_decision_is_allow",
                    "operation_matches_authorized_operation",
                    "target_matches_authorized_target",
                    "authorization_is_not_terminal",
                ],
                "execution_rules":{
                    "execute_only_authorized_operation":True,
                    "execute_only_authorized_target":True,
                    "scope_expansion":False,
                    "silent_execution":False,
                    "record_result":True,
                    "consume_authorization_after_attempt":True,
                },
                "professional_action_execution":"HUMAN_PROFESSIONAL_ONLY",
                "failed_or_unknown_precondition":"DENY",
                "provider_may_self_authorize":False,
            },
            # 9.7 defines the receipt produced by a future controlled
            # execution attempt so the outcome remains traceable and reviewable.
            "execution_receipt":{
                "schema":"midra.engineering.execution_receipt",
                "schema_version":"1.0",
                "required_fields":[
                    "operation",
                    "target",
                    "authorization_reference",
                    "authorized_by",
                    "actor",
                    "attempted_at",
                    "result",
                ],
                "result_states":[
                    "SUCCEEDED",
                    "FAILED",
                    "DENIED",
                ],
                "recording_rules":{
                    "record_every_attempt":True,
                    "record_failure":True,
                    "record_denial":True,
                    "record_before_and_after_state_when_applicable":True,
                    "receipt_is_append_only":True,
                    "receipt_may_not_grant_authority":True,
                },
                "missing_receipt_for_attempt":"CONTROL_VIOLATION",
                "professional_approval_receipt":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 9.8 defines post-execution verification. A recorded attempt
            # is not treated as verified merely because a receipt exists.
            "execution_verification":{
                "schema":"midra.engineering.execution_verification",
                "schema_version":"1.0",
                "verification_states":[
                    "NOT_VERIFIED",
                    "VERIFIED",
                    "DISCREPANCY",
                ],
                "required_checks":[
                    "receipt_present",
                    "receipt_matches_authorized_operation",
                    "receipt_matches_authorized_target",
                    "recorded_result_present",
                    "recorded_state_matches_result_when_applicable",
                ],
                "verification_rules":{
                    "default_state":"NOT_VERIFIED",
                    "all_checks_required_for_verified":True,
                    "failed_check_state":"DISCREPANCY",
                    "missing_check_state":"NOT_VERIFIED",
                    "verification_may_not_change_execution_result":True,
                    "verification_may_not_grant_authority":True,
                },
                "professional_verification":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 9.9 defines how a verification discrepancy is contained and
            # surfaced without silently retrying or changing recorded project state.
            "discrepancy_handling":{
                "schema":"midra.engineering.discrepancy_handling",
                "schema_version":"1.0",
                "discrepancy_states":[
                    "OPEN",
                    "UNDER_REVIEW",
                    "RESOLVED",
                ],
                "on_discrepancy":{
                    "halt_automatic_continuation":True,
                    "preserve_execution_receipt":True,
                    "preserve_recorded_result":True,
                    "surface_for_human_review":True,
                    "automatic_retry":False,
                    "automatic_state_correction":False,
                },
                "resolution_requirements":[
                    "resolution_recorded",
                    "resolved_by",
                    "resolved_at",
                ],
                "professional_discrepancy_resolution":"HUMAN_PROFESSIONAL_ONLY",
                "missing_or_unknown_resolution":"UNRESOLVED",
            },
            # 10.0 closes the control loop by defining the conditions for
            # a controlled operation to be considered operationally complete.
            "controlled_operation_completion":{
                "schema":"midra.engineering.controlled_operation_completion",
                "schema_version":"1.0",
                "required_conditions":[
                    "authorization_was_valid",
                    "execution_receipt_present",
                    "execution_result_recorded",
                    "authorization_consumed",
                    "verification_state_verified",
                    "no_open_discrepancy",
                ],
                "completion_states":[
                    "INCOMPLETE",
                    "COMPLETE",
                    "REQUIRES_REVIEW",
                ],
                "completion_rules":{
                    "default_state":"INCOMPLETE",
                    "all_required_conditions_for_complete":True,
                    "open_discrepancy_state":"REQUIRES_REVIEW",
                    "missing_evidence_state":"INCOMPLETE",
                    "completion_may_not_imply_professional_approval":True,
                    "completion_may_not_imply_agency_acceptance":True,
                    "completion_may_not_grant_new_authority":True,
                },
                "professional_completion":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 10.1 defines a compact read-only status projection for the
            # complete controlled-operation governance chain.
            "operation_control_status":{
                "schema":"midra.engineering.operation_control_status",
                "schema_version":"1.0",
                "control_chain":[
                    "AUTHORIZE",
                    "VALIDATE",
                    "DECIDE",
                    "EXECUTE",
                    "RECEIPT",
                    "VERIFY",
                    "RESOLVE_DISCREPANCY",
                    "COMPLETE",
                ],
                "status_fields":[
                    "authorization_state",
                    "decision",
                    "execution_result",
                    "verification_state",
                    "discrepancy_state",
                    "completion_state",
                ],
                "projection_rules":{
                    "read_only":True,
                    "recorded_evidence_only":True,
                    "unknown_value":"UNKNOWN",
                    "missing_value":"NOT_RECORDED",
                    "may_not_infer_approval":True,
                    "may_not_infer_agency_acceptance":True,
                    "may_not_grant_authority":True,
                },
                "professional_status":"HUMAN_PROFESSIONAL_ONLY",
            },
            # 10.2 defines the immutable identity fields that bind a future
            # controlled operation across authorization, execution, and verification.
            "operation_identity":{
                "schema":"midra.engineering.operation_identity",
                "schema_version":"1.0",
                "required_fields":[
                    "operation_id",
                    "operation",
                    "target",
                    "created_at",
                ],
                "binding_rules":{
                    "operation_id_unique":True,
                    "operation_id_immutable":True,
                    "operation_immutable_after_authorization":True,
                    "target_immutable_after_authorization":True,
                    "same_identity_required_for_receipt":True,
                    "same_identity_required_for_verification":True,
                    "same_identity_required_for_completion":True,
                },
                "identity_mismatch":"DENY",
                "provider_may_replace_identity":False,
            },
            # 10.3 defines explicit actor identity for every future controlled
            # operation so authority and execution can never be attributed ambiguously.
            "operation_actor_identity":{
                "schema":"midra.engineering.operation_actor_identity",
                "schema_version":"1.0",
                "actor_types":[
                    "MIDRA_USER",
                    "AI_ASSISTED",
                    "SYSTEM",
                ],
                "required_fields":[
                    "actor_id",
                    "actor_type",
                ],
                "identity_rules":{
                    "actor_id_required":True,
                    "actor_type_required":True,
                    "actor_identity_must_be_recorded":True,
                    "actor_may_not_inherit_authorizer_identity":True,
                    "ai_provider_is_not_authorizing_actor":True,
                    "unknown_actor":"DENY",
                },
                "professional_actor":"HUMAN_PROFESSIONAL_ONLY",
                "provider_may_impersonate_actor":False,
            },
            # 10.4 defines explicit delegation boundaries for future controlled
            # operations. Delegation never expands the delegator's authority.
            "operation_delegation":{
                "schema":"midra.engineering.operation_delegation",
                "schema_version":"1.0",
                "required_fields":[
                    "delegated_by",
                    "delegated_to",
                    "operation",
                    "target",
                    "delegated_at",
                ],
                "delegation_rules":{
                    "explicit_delegation_required":True,
                    "operation_specific":True,
                    "target_specific":True,
                    "delegate_may_not_expand_scope":True,
                    "delegate_may_not_redelegate":True,
                    "delegation_may_be_revoked":True,
                    "delegation_may_not_exceed_delegator_authority":True,
                    "prior_delegation_may_not_be_inferred":True,
                },
                "missing_or_invalid_delegation":"DENY",
                "professional_delegation":"HUMAN_PROFESSIONAL_ONLY",
                "provider_may_create_delegation":False,
            },
            # 10.5 defines finite delegation lifecycle states so delegated
            # authority cannot persist or reactivate implicitly.
            "delegation_lifecycle":{
                "schema":"midra.engineering.delegation_lifecycle",
                "schema_version":"1.0",
                "states":[
                    "NOT_DELEGATED",
                    "ACTIVE",
                    "CONSUMED",
                    "REVOKED",
                    "EXPIRED",
                ],
                "initial_state":"NOT_DELEGATED",
                "terminal_states":[
                    "CONSUMED",
                    "REVOKED",
                    "EXPIRED",
                ],
                "lifecycle_rules":{
                    "explicit_activation_required":True,
                    "active_state_required_for_use":True,
                    "may_be_revoked_before_use":True,
                    "consumed_after_authorized_use":True,
                    "terminal_state_may_not_be_used":True,
                    "automatic_renewal":False,
                    "prior_delegation_may_not_reactivate":False,
                },
                "invalid_or_unknown_state":"DENY",
                "provider_may_change_delegation_state":False,
            },
            # 10.6 defines fail-closed validation for delegated authority before
            # a future controlled operation may rely on that delegation.
            "delegation_validation":{
                "schema":"midra.engineering.delegation_validation",
                "schema_version":"1.0",
                "required_checks":[
                    "delegation_present",
                    "delegation_state_is_active",
                    "delegator_identity_matches",
                    "delegate_identity_matches",
                    "operation_matches",
                    "target_matches",
                    "delegation_is_current",
                    "delegation_not_revoked",
                    "delegation_not_consumed",
                    "delegation_not_expired",
                ],
                "decision_rule":"ALL_CHECKS_MUST_PASS",
                "on_failed_check":"DENY",
                "on_missing_check":"DENY",
                "on_unknown_check":"DENY",
                "provider_may_bypass_validation":False,
            },
        },
    }

    return {
        "agent_context":agent_context,
        "project_brief":project_brief,
        "project_health":project_health,
        "next_move":next_move,
        "attention":attention_summary,
        "identity":{
            "job_number":job.job_number,
            "project_name":job.project_name,
            "project_type":job.project_type,
            "source":job.source,
            "property_address":job.property_address,
            "client_id":job.client_id,
        },
        "status":{
            "project_state":job.state,
            "version":job.version,
            "attention":card["attention"],
            "next_action":card["next_action"],
        },
        "connected_sections":connected,
        "section_summaries":summaries,
        "operations":{
            "signals":deepcopy(
                ((sections.get("command_center") or {}).get("summary",{}).get("signals",[]))
            ),
            "open_signals":deepcopy([
                s for s in
                ((sections.get("command_center") or {}).get("summary",{}).get("signals",[]))
                if not s.get("resolved")
            ]),
        },
        "deliverables":{
            "items":deepcopy(
                ((sections.get("deliverables") or {}).get("summary",{}).get("items",[]))
            ),
            "open_count":len([
                d for d in
                ((sections.get("deliverables") or {}).get("summary",{}).get("items",[]))
                if d.get("status") not in {"APPROVED","SUPERSEDED"}
            ]),
        },
        "documents":{
            "items":deepcopy(
                ((sections.get("documents") or {}).get("summary",{}).get("items",[]))
            ),
            "count":len(
                ((sections.get("documents") or {}).get("summary",{}).get("items",[]))
            ),
        },
        "reviews":{
            "items":deepcopy(
                ((sections.get("reviews") or {}).get("summary",{}).get("items",[]))
            ),
            "open_comments":sum(
                1 for review in ((sections.get("reviews") or {}).get("summary",{}).get("items",[]))
                for comment in review.get("comments",[])
                if comment.get("requires_action",True)
                and comment.get("status") not in {"VERIFIED","NOT_APPLICABLE"}
            ),
        },
        "submission_packages":{
            "items":deepcopy(
                ((sections.get("submission_packages") or {}).get("summary",{}).get("items",[]))
            ),
            "open_count":len([
                p for p in ((sections.get("submission_packages") or {}).get("summary",{}).get("items",[]))
                if p.get("status") not in {"ACCEPTED","SUPERSEDED"}
            ]),
        },
        "dependencies":{
            "items":deepcopy(
                ((sections.get("dependencies") or {}).get("summary",{}).get("items",[]))
            ),
            "waiting_count":len([
                d for d in ((sections.get("dependencies") or {}).get("summary",{}).get("items",[]))
                if d.get("status") in {"WAITING","FOLLOW_UP_DUE"}
            ]),
        },
        "action_items":{
            "items":deepcopy(
                ((sections.get("action_items") or {}).get("summary",{}).get("items",[]))
            ),
            "open_count":len([
                a for a in ((sections.get("action_items") or {}).get("summary",{}).get("items",[]))
                if a.get("status") in {"OPEN","IN_PROGRESS","BLOCKED"}
            ]),
        },

        "lifecycle_audit":{
            "completion_status":str(((((sections.get("project_completion") or {}).get("summary",{}).get("certification")) or {}).get("status",""))).upper() or "NOT_CERTIFIED",
            "certification_count":len(((sections.get("project_completion") or {}).get("summary",{}).get("certification_history",[]))) + (1 if ((sections.get("project_completion") or {}).get("summary",{}).get("certification")) else 0),
            "reopen_count":len(((sections.get("project_completion") or {}).get("summary",{}).get("reopen_history",[]))),
            "post_completion_open_count":sum(1 for x in ((sections.get("post_completion_work") or {}).get("summary",{}).get("items",[])) if str(x.get("status","OPEN")).upper() not in {"RESOLVED","CANCELLED"}),
            "acknowledgement_count":len(((sections.get("lifecycle_audit_acknowledgements") or {}).get("summary",{}).get("items",[]))),
            "latest_acknowledgement":deepcopy(((((sections.get("lifecycle_audit_acknowledgements") or {}).get("summary",{}).get("items",[])) or [None])[-1])),
            "acknowledgement_history":list(reversed(deepcopy(((sections.get("lifecycle_audit_acknowledgements") or {}).get("summary",{}).get("items",[])))))[0:25],
        },

        "post_completion_work":{
            "items":deepcopy(((sections.get("post_completion_work") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for x in ((sections.get("post_completion_work") or {}).get("summary",{}).get("items",[])) if str(x.get("status","OPEN")).upper() not in {"RESOLVED","CANCELLED"}),
        },

        "project_completion":{
            "certification":deepcopy(((sections.get("project_completion") or {}).get("summary",{}).get("certification"))),
            "certified":str((((sections.get("project_completion") or {}).get("summary",{}).get("certification")) or {}).get("status","")).upper()=="CERTIFIED",
            "reopened":str((((sections.get("project_completion") or {}).get("summary",{}).get("certification")) or {}).get("status","")).upper()=="REOPENED",
            "certification_history":deepcopy(((sections.get("project_completion") or {}).get("summary",{}).get("certification_history",[]))),
            "reopen_history":deepcopy(((sections.get("project_completion") or {}).get("summary",{}).get("reopen_history",[]))),
        },

        "project_closure":{
            "items":deepcopy(((sections.get("project_closure") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("project_closure") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for item in ((sections.get("project_closure") or {}).get("summary",{}).get("items",[]))
                             if str(item.get("status","OPEN")).upper() in {"OPEN","IN_PROGRESS"}),
            "review_count":sum(1 for item in ((sections.get("project_closure") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="READY_FOR_REVIEW"),
            "complete_count":sum(1 for item in ((sections.get("project_closure") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="COMPLETE"),
            "waived_count":sum(1 for item in ((sections.get("project_closure") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="WAIVED"),
        },

        "project_archive":{
            "items":deepcopy(((sections.get("project_archive") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("project_archive") or {}).get("summary",{}).get("items",[]))),
            "pending_count":sum(1 for item in ((sections.get("project_archive") or {}).get("summary",{}).get("items",[]))
                                if str(item.get("status","PENDING")).upper()=="PENDING"),
            "verification_count":sum(1 for item in ((sections.get("project_archive") or {}).get("summary",{}).get("items",[]))
                                     if str(item.get("status","")).upper()=="READY_FOR_VERIFICATION"),
            "verified_count":sum(1 for item in ((sections.get("project_archive") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="VERIFIED"),
            "archived_count":sum(1 for item in ((sections.get("project_archive") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="ARCHIVED"),
        },

        "warranty_issues":{
            "items":deepcopy(((sections.get("warranty_issues") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("warranty_issues") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for item in ((sections.get("warranty_issues") or {}).get("summary",{}).get("items",[]))
                             if str(item.get("status","OPEN")).upper() in {"OPEN","IN_PROGRESS"}),
            "verification_count":sum(1 for item in ((sections.get("warranty_issues") or {}).get("summary",{}).get("items",[]))
                                     if str(item.get("status","")).upper()=="READY_FOR_VERIFICATION"),
            "resolved_count":sum(1 for item in ((sections.get("warranty_issues") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="RESOLVED"),
            "urgent_count":sum(1 for item in ((sections.get("warranty_issues") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("priority","NORMAL")).upper()=="URGENT"
                               and str(item.get("status","OPEN")).upper() not in {"RESOLVED","CANCELLED"}),
        },

        "closeout":{
            "items":deepcopy(((sections.get("closeout") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("closeout") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for item in ((sections.get("closeout") or {}).get("summary",{}).get("items",[]))
                             if str(item.get("status","OPEN")).upper() in {"OPEN","IN_PROGRESS"}),
            "review_count":sum(1 for item in ((sections.get("closeout") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="READY_FOR_REVIEW"),
            "accepted_count":sum(1 for item in ((sections.get("closeout") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="ACCEPTED"),
            "waived_count":sum(1 for item in ((sections.get("closeout") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="WAIVED"),
        },

        "punch_list":{
            "items":deepcopy(((sections.get("punch_list") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("punch_list") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for item in ((sections.get("punch_list") or {}).get("summary",{}).get("items",[]))
                             if str(item.get("status","OPEN")).upper() in {"OPEN","IN_PROGRESS"}),
            "verification_count":sum(1 for item in ((sections.get("punch_list") or {}).get("summary",{}).get("items",[]))
                                     if str(item.get("status","")).upper()=="READY_FOR_VERIFICATION"),
            "closed_count":sum(1 for item in ((sections.get("punch_list") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="CLOSED"),
            "urgent_count":sum(1 for item in ((sections.get("punch_list") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("priority","NORMAL")).upper()=="URGENT"
                               and str(item.get("status","OPEN")).upper() not in {"CLOSED","CANCELLED"}),
        },

        "change_orders":{
            "items":deepcopy(((sections.get("change_orders") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("change_orders") or {}).get("summary",{}).get("items",[]))),
            "pending_count":sum(1 for item in ((sections.get("change_orders") or {}).get("summary",{}).get("items",[]))
                                if str(item.get("status","PROPOSED")).upper() in {"PROPOSED","UNDER_REVIEW"}),
            "approved_count":sum(1 for item in ((sections.get("change_orders") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="APPROVED"),
            "rejected_count":sum(1 for item in ((sections.get("change_orders") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="REJECTED"),
            "implemented_count":sum(1 for item in ((sections.get("change_orders") or {}).get("summary",{}).get("items",[]))
                                    if str(item.get("status","")).upper()=="IMPLEMENTED"),
        },

        "submittals":{
            "items":deepcopy(((sections.get("submittals") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("submittals") or {}).get("summary",{}).get("items",[]))),
            "pending_count":sum(1 for item in ((sections.get("submittals") or {}).get("summary",{}).get("items",[]))
                                if str(item.get("status","RECEIVED")).upper() in {"RECEIVED","UNDER_REVIEW"}),
            "approved_count":sum(1 for item in ((sections.get("submittals") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper() in {"APPROVED","APPROVED_AS_NOTED"}),
            "revise_count":sum(1 for item in ((sections.get("submittals") or {}).get("summary",{}).get("items",[]))
                                if str(item.get("status","")).upper()=="REVISE_RESUBMIT"),
            "closed_count":sum(1 for item in ((sections.get("submittals") or {}).get("summary",{}).get("items",[]))
                                if str(item.get("status","")).upper()=="CLOSED"),
        },

        "rfis":{
            "items":deepcopy(((sections.get("rfis") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("rfis") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for item in ((sections.get("rfis") or {}).get("summary",{}).get("items",[]))
                             if str(item.get("status","OPEN")).upper() in {"OPEN","PENDING_RESPONSE"}),
            "answered_count":sum(1 for item in ((sections.get("rfis") or {}).get("summary",{}).get("items",[]))
                                 if str(item.get("status","")).upper()=="ANSWERED"),
            "closed_count":sum(1 for item in ((sections.get("rfis") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="CLOSED"),
            "urgent_count":sum(1 for item in ((sections.get("rfis") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("priority","NORMAL")).upper()=="URGENT"
                               and str(item.get("status","OPEN")).upper() not in {"CLOSED","CANCELLED"}),
        },

        "field_reports":{
            "items":deepcopy(((sections.get("field_reports") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("field_reports") or {}).get("summary",{}).get("items",[]))),
            "open_count":sum(1 for item in ((sections.get("field_reports") or {}).get("summary",{}).get("items",[]))
                             if str(item.get("status","OPEN")).upper() in {"OPEN","FOLLOW_UP"}),
            "follow_up_count":sum(1 for item in ((sections.get("field_reports") or {}).get("summary",{}).get("items",[]))
                                  if bool(item.get("follow_up_required")) and str(item.get("status","OPEN")).upper() not in {"CLOSED","CANCELLED"}),
            "closed_count":sum(1 for item in ((sections.get("field_reports") or {}).get("summary",{}).get("items",[]))
                               if str(item.get("status","")).upper()=="CLOSED"),
        },

        "meetings":{
            "items":deepcopy(((sections.get("meetings") or {}).get("summary",{}).get("items",[]))),
            "count":len(((sections.get("meetings") or {}).get("summary",{}).get("items",[]))),
            "scheduled_count":sum(1 for item in ((sections.get("meetings") or {}).get("summary",{}).get("items",[]))
                                  if str(item.get("status","SCHEDULED")).upper()=="SCHEDULED"),
            "completed_count":sum(1 for item in ((sections.get("meetings") or {}).get("summary",{}).get("items",[]))
                                  if str(item.get("status","")).upper()=="COMPLETED"),
        },

        "milestones":{
            "items":deepcopy(
                ((sections.get("milestones") or {}).get("summary",{}).get("items",[]))
            ),
            "count":len(
                ((sections.get("milestones") or {}).get("summary",{}).get("items",[]))
            ),
            "open_count":sum(
                1 for item in ((sections.get("milestones") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","OPEN")).upper() in {"OPEN","IN_PROGRESS","BLOCKED"}
            ),
            "blocked_count":sum(
                1 for item in ((sections.get("milestones") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","")).upper()=="BLOCKED"
            ),
            "complete_count":sum(
                1 for item in ((sections.get("milestones") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","")).upper()=="COMPLETE"
            ),
        },

        "correspondence":{
            "items":deepcopy(
                ((sections.get("correspondence") or {}).get("summary",{}).get("items",[]))
            ),
            "count":len(
                ((sections.get("correspondence") or {}).get("summary",{}).get("items",[]))
            ),
            "inbound_count":sum(
                1 for item in ((sections.get("correspondence") or {}).get("summary",{}).get("items",[]))
                if str(item.get("direction","")).upper()=="INBOUND"
            ),
            "outbound_count":sum(
                1 for item in ((sections.get("correspondence") or {}).get("summary",{}).get("items",[]))
                if str(item.get("direction","")).upper()=="OUTBOUND"
            ),
            "response_required_count":sum(
                1 for item in ((sections.get("correspondence") or {}).get("summary",{}).get("items",[]))
                if item.get("response_required") is True
                and str(item.get("response_status","PENDING")).upper() not in {"RESPONDED","CLOSED","NOT_REQUIRED"}
            ),
        },

        "billing":{
            "items":deepcopy(
                ((sections.get("billing") or {}).get("summary",{}).get("items",[]))
            ),
            "count":len(
                ((sections.get("billing") or {}).get("summary",{}).get("items",[]))
            ),
            "open_count":sum(
                1 for item in ((sections.get("billing") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","")).upper() in {"DRAFT","OPEN","ISSUED","PARTIAL","OVERDUE"}
            ),
            "overdue_count":sum(
                1 for item in ((sections.get("billing") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","")).upper()=="OVERDUE"
            ),
            "paid_count":sum(
                1 for item in ((sections.get("billing") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","")).upper()=="PAID"
            ),
        },

        "client_portal":{
            "items":deepcopy(
                ((sections.get("client_portal") or {}).get("summary",{}).get("items",[]))
            ),
            "count":len(
                ((sections.get("client_portal") or {}).get("summary",{}).get("items",[]))
            ),
            "shared_count":sum(
                1 for item in ((sections.get("client_portal") or {}).get("summary",{}).get("items",[]))
                if str(item.get("status","")).upper() in {"SHARED","PUBLISHED","AVAILABLE"}
            ),
            "acknowledgement_required_count":sum(
                1 for item in ((sections.get("client_portal") or {}).get("summary",{}).get("items",[]))
                if item.get("acknowledgement_required") is True
                and str(item.get("acknowledgement_status","PENDING")).upper() not in {"ACKNOWLEDGED","CLOSED","NOT_REQUIRED"}
            ),
            "client_action_required_count":sum(
                1 for item in ((sections.get("client_portal") or {}).get("summary",{}).get("items",[]))
                if item.get("client_action_required") is True
                and str(item.get("client_action_status","PENDING")).upper() not in {"COMPLETE","COMPLETED","CLOSED","NOT_REQUIRED"}
            ),
        },

        "activity":{
            "event_count":len(job.events or []),
            "recent_events":deepcopy((job.events or [])[-20:]),
        },
        "controls":{
            "professional_actions_require_approval":True,
            "automatic_professional_completion":False,
            "automatic_issue_or_submission":False,
        },
    }

def load_engineering_workspace(db,job_number):
    job=SQLAlchemyEngineeringJobRepository(db).get(job_number)
    return engineering_workspace(job)

def engineering_dashboard(db,state=None):
    repo=SQLAlchemyEngineeringJobRepository(db)
    workspaces=[engineering_workspace(j) for j in repo.list_jobs(state=state)]
    return {
        "project_count":len(workspaces),
        "projects":[{
            "identity":w["identity"],
            "status":w["status"],
            "activity":{"event_count":w["activity"]["event_count"]},
        } for w in workspaces]
    }
