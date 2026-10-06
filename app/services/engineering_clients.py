"""Phase 5.51 — lightweight client/contact database."""
from datetime import datetime, timezone
CLIENT_TYPES={"INDIVIDUAL","COMPANY","ORGANIZATION","OTHER"}
CONTACT_ROLES={"CLIENT","PROPERTY_OWNER","APPLICANT","ATTORNEY","ARCHITECT","CONTRACTOR","AGENT","OTHER"}

def create_client(*,client_id,display_name,client_type,created_by,email=None,phone=None,created_at=None):
    if client_type not in CLIENT_TYPES: raise ValueError("unsupported client type")
    if any(not str(v or "").strip() for v in (client_id,display_name,created_by)): raise ValueError("missing client identity")
    return {"client_id":client_id,"display_name":display_name,"client_type":client_type,"email":email,"phone":phone,
            "created_by":created_by,"created_at":created_at or datetime.now(timezone.utc).isoformat(),"contacts":[],"relationships":[]}

def add_client_contact(*,client,contact_id,name,role,email=None,phone=None):
    if role not in CONTACT_ROLES: raise ValueError("unsupported contact role")
    if not contact_id.strip() or not name.strip(): raise ValueError("missing contact identity")
    r=_copy(client); r["contacts"].append({"contact_id":contact_id,"name":name,"role":role,"email":email,"phone":phone}); return r

def link_client_record(*,client,record_type,record_id,property_address=None):
    if not record_type.strip() or not record_id.strip(): raise ValueError("missing relationship")
    r=_copy(client); rel={"record_type":record_type,"record_id":record_id,"property_address":property_address}
    if rel not in r["relationships"]: r["relationships"].append(rel)
    return r

def intake_client_defaults(*,client):
    return {"client_id":client["client_id"],"client_name":client["display_name"],"email":client.get("email"),
            "phone":client.get("phone"),"source":"EXISTING_CLIENT_RECORD"}

def client_history(*,client):
    return {"visibility":"MIDRA_ENGINEERING_PRIVATE","client_id":client["client_id"],"display_name":client["display_name"],
            "contacts":[dict(x) for x in client["contacts"]],"work_history":[dict(x) for x in client["relationships"]]}

def potential_duplicate_client(*,existing_clients,display_name,email=None,phone=None):
    name=display_name.strip().casefold(); out=[]
    for c in existing_clients:
        se=bool(email and c.get("email") and email.casefold()==c["email"].casefold())
        sp=bool(phone and c.get("phone") and phone==c["phone"])
        sn=c.get("display_name","").strip().casefold()==name
        if se or sp or sn:
            out.append({"client_id":c["client_id"],"display_name":c["display_name"],
                        "match_reason":"EMAIL" if se else "PHONE" if sp else "NAME","requires_confirmation":True})
    return out

def _copy(c):
    r={k:v for k,v in c.items() if k not in {"contacts","relationships"}}
    r["contacts"]=[dict(x) for x in c.get("contacts",[])]; r["relationships"]=[dict(x) for x in c.get("relationships",[])]
    return r
