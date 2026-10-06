from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from app.models.engineering_property_proposal_client_response import (
    EngineeringPropertyProposalClientResponse,
)


def test_postgresql_identifier_lengths_and_index_compilation():
    dialect = postgresql.dialect()
    table = EngineeringPropertyProposalClientResponse.__table__

    names = []
    for constraint in table.constraints:
        if constraint.name:
            names.append(constraint.name)
    for index in table.indexes:
        assert index.name
        names.append(index.name)
        sql = str(CreateIndex(index).compile(dialect=dialect))
        assert "CREATE INDEX" in sql or "CREATE UNIQUE INDEX" in sql

    assert names
    for name in names:
        dialect.validate_identifier(name)
        assert len(name.encode("utf-8")) <= 63


def test_client_response_indexes_are_explicit_and_stable():
    table = EngineeringPropertyProposalClientResponse.__table__
    names = {index.name for index in table.indexes}
    assert names == {
        "ix_epp_client_resp_release",
        "ix_epp_client_resp_property",
        "ix_epp_client_resp_request",
        "ix_epp_client_resp_proposal",
        "ix_epp_client_resp_number",
        "ix_epp_client_resp_status",
    }
