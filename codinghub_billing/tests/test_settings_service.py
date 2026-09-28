import pytest

from database.models.audit_log import AuditLog
from services import settings_service


def _business_data(**overrides) -> dict:
    data = {
        "business_name": "CodingHub",
        "address": "MG Road",
        "phone": "9876543210",
        "email": "hello@codinghub.com",
        "gstin": "",
        "pan": "",
        "state": "Karnataka",
        "state_code": "29",
        "logo_path": None,
    }
    data.update(overrides)
    return data


def _invoice_data(**overrides) -> dict:
    data = {
        "prefix": "CH",
        "starting_number": 1,
        "next_number": 1,
        "terms": "Pay within 7 days.",
        "footer_text": "Thank you!",
        "signature_path": None,
    }
    data.update(overrides)
    return data


def test_update_business_success_and_audit_log(db_session):
    saved = settings_service.update_business_settings(db_session, None, _business_data())

    assert saved["business_name"] == "CodingHub"
    assert saved["email"] == "hello@codinghub.com"

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].entity_type == "settings"
    assert logs[0].entity_id == "business"


def test_update_business_trims_and_uppercases(db_session):
    saved = settings_service.update_business_settings(
        db_session, None, _business_data(gstin=" 29abcde1234f1z5 ", pan=" abcde1234f ")
    )
    assert saved["gstin"] == "29ABCDE1234F1Z5"
    assert saved["pan"] == "ABCDE1234F"


@pytest.mark.parametrize(
    "overrides,expected_snippet",
    [
        ({"business_name": ""}, "Business name"),
        ({"email": "not-an-email"}, "valid email"),
        ({"gstin": "invalid"}, "GSTIN"),
        ({"pan": "invalid"}, "PAN"),
    ],
)
def test_update_business_validation_errors(db_session, overrides, expected_snippet):
    with pytest.raises(settings_service.SettingsError, match=expected_snippet):
        settings_service.update_business_settings(db_session, None, _business_data(**overrides))


def test_update_invoice_success_and_audit_log(db_session):
    saved = settings_service.update_invoice_settings(
        db_session, None, _invoice_data(prefix=" ch ", starting_number="5", next_number="8")
    )

    assert saved["prefix"] == "CH"
    assert saved["starting_number"] == 5
    assert saved["next_number"] == 8

    logs = db_session.query(AuditLog).all()
    assert len(logs) == 1
    assert logs[0].entity_id == "invoice"


@pytest.mark.parametrize(
    "overrides,expected_snippet",
    [
        ({"prefix": ""}, "prefix"),
        ({"starting_number": 0}, "at least 1"),
        ({"next_number": 0}, "at least 1"),
        ({"starting_number": 10, "next_number": 5}, "less than the starting"),
    ],
)
def test_update_invoice_validation_errors(db_session, overrides, expected_snippet):
    with pytest.raises(settings_service.SettingsError, match=expected_snippet):
        settings_service.update_invoice_settings(db_session, None, _invoice_data(**overrides))


def test_preferences_roundtrip_and_validation(db_session):
    prefs = settings_service.get_preferences(db_session, default_tax_rate=0)
    assert prefs["default_tax_rate"] == "0"
    assert prefs["appearance_mode"] == "Light"

    saved = settings_service.update_preferences(
        db_session, None, {"default_tax_rate": "0", "appearance_mode": "Dark"}
    )
    assert saved["default_tax_rate"] == "0"
    assert saved["appearance_mode"] == "Dark"

    with pytest.raises(settings_service.SettingsError, match="GST"):
        settings_service.update_preferences(
            db_session, None, {"default_tax_rate": "99", "appearance_mode": "Dark"}
        )
    with pytest.raises(settings_service.SettingsError, match="GST"):
        settings_service.update_preferences(
            db_session, None, {"default_tax_rate": "12", "appearance_mode": "Dark"}
        )
    with pytest.raises(settings_service.SettingsError, match="Appearance"):
        settings_service.update_preferences(
            db_session, None, {"default_tax_rate": "0", "appearance_mode": "Neon"}
        )


def test_backup_dir_app_setting_roundtrip(db_session):
    assert settings_service.get_app_setting(db_session, settings_service.BACKUP_DIR_KEY, "") == ""
    settings_service.set_app_setting(db_session, settings_service.BACKUP_DIR_KEY, "/tmp/ch-backups")
    assert (
        settings_service.get_app_setting(db_session, settings_service.BACKUP_DIR_KEY, "")
        == "/tmp/ch-backups"
    )
