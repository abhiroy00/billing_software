from datetime import date, datetime, timedelta

from database.models.audit_log import AuditLog
from services import audit_service


def _seed(db_session):
    """3 events: 2 aaj, 1 kal — alag actions/entities."""
    now = datetime.now()
    rows = [
        AuditLog(user_id=None, action="create", entity_type="customer",
                 entity_id="1", description="Created customer Ravi",
                 timestamp=now),
        AuditLog(user_id=None, action="update", entity_type="invoice",
                 entity_id="CH-1", description="Updated invoice total",
                 timestamp=now),
        AuditLog(user_id=None, action="delete", entity_type="customer",
                 entity_id="2", description="Deleted customer Bala",
                 timestamp=now - timedelta(days=1)),
    ]
    db_session.add_all(rows)
    db_session.flush()
    return rows


def test_list_logs_newest_first_with_username(db_session):
    _seed(db_session)

    rows = audit_service.list_logs(db_session)
    assert len(rows) == 3
    assert rows[0]["action"] == "delete"  # sabse naya id sabse upar
    assert rows[0]["username"] == "—"  # user_id None
    assert rows[0]["entity_type"] == "customer"


def test_list_logs_search(db_session):
    _seed(db_session)

    rows = audit_service.list_logs(db_session, query="ravi")
    assert len(rows) == 1
    assert rows[0]["description"] == "Created customer Ravi"

    rows = audit_service.list_logs(db_session, query="CH-1")
    assert len(rows) == 1
    assert rows[0]["entity_type"] == "invoice"


def test_list_logs_action_and_entity_filter(db_session):
    _seed(db_session)

    assert len(audit_service.list_logs(db_session, action="create")) == 1
    assert len(audit_service.list_logs(db_session, entity_type="customer")) == 2
    assert len(audit_service.list_logs(db_session, action="update", entity_type="customer")) == 0


def test_list_logs_date_range(db_session):
    _seed(db_session)
    today = date.today()

    rows = audit_service.list_logs(db_session, date_from=today, date_to=today)
    assert len(rows) == 2

    yesterday = today - timedelta(days=1)
    rows = audit_service.list_logs(db_session, date_from=yesterday, date_to=yesterday)
    assert len(rows) == 1
    assert rows[0]["action"] == "delete"


def test_list_logs_limit(db_session):
    _seed(db_session)

    rows = audit_service.list_logs(db_session, limit=2)
    assert len(rows) == 2


def test_distinct_filter_options(db_session):
    _seed(db_session)

    assert sorted(audit_service.distinct_actions(db_session)) == ["create", "delete", "update"]
    assert sorted(audit_service.distinct_entity_types(db_session)) == ["customer", "invoice"]


def test_count_since(db_session):
    _seed(db_session)

    assert audit_service.count_since(db_session, datetime.now() - timedelta(hours=1)) == 2
    assert audit_service.count_since(db_session, datetime.now() + timedelta(hours=1)) == 0
