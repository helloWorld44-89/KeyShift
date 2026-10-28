import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from conftest import TEST_KEY
from app import create_app, db
from app import upgrade_schema


@pytest.fixture
def file_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'KeyShift.db'}",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
        "ENCRYPTION_KEY": TEST_KEY,
    })
    with app.app_context():
        yield app
        db.session.remove()
        db.engine.dispose()


def schema_diff():
    with db.engine.connect() as conn:
        return compare_metadata(MigrationContext.configure(conn), db.metadata)


def test_fresh_database_matches_models(file_app):
    upgrade_schema(file_app)
    assert {"users", "ssids", "alembic_version"} <= set(inspect(db.engine).get_table_names())
    assert schema_diff() == []


# Schema of databases created before migrations existed
LEGACY_SCHEMA = [
    "CREATE TABLE users (id INTEGER NOT NULL, username TEXT NOT NULL, password TEXT, "
    "admin BOOLEAN, active BOOLEAN, \"apiKey\" TEXT, PRIMARY KEY (id))",
    "CREATE TABLE ssids (id INTEGER NOT NULL, \"ssidName\" TEXT NOT NULL, \"ssidPW\" TEXT, "
    "\"lastChanged\" DATETIME, \"siteID\" TEXT, \"wlanGroupID\" TEXT, \"ssidID\" TEXT, status BOOLEAN, "
    "hidden BOOLEAN, \"pwRotate\" BOOLEAN, \"rotateFrequency\" TEXT, \"qrCode\" BOOLEAN, "
    "\"isGuest\" BOOLEAN, PRIMARY KEY (id))",
]


def test_existing_database_is_stamped_and_keeps_data(file_app):
    for stmt in LEGACY_SCHEMA:
        db.session.execute(text(stmt))
    db.session.execute(text(
        "INSERT INTO users (username, password, admin, active) VALUES ('old', 'x', 1, 1)"))
    db.session.execute(text(
        "INSERT INTO ssids (ssidName, ssidPW, siteID, ssidID, isGuest) "
        "VALUES ('Home', 'pw', 's', 'abc', 1)"))
    db.session.commit()
    assert "alembic_version" not in inspect(db.engine).get_table_names()

    upgrade_schema(file_app)

    assert "alembic_version" in inspect(db.engine).get_table_names()
    assert db.session.execute(text("SELECT username FROM users")).scalar() == "old"
    assert schema_diff() == []

    # the plaintext Wi-Fi password was encrypted in place, and still reads back
    raw = db.session.execute(text("SELECT ssidPW FROM ssids")).scalar()
    assert raw.startswith("enc:v1:") and "pw" != raw
    from app.models import SSID
    assert SSID.query.one().ssidPW == "pw"
    assert SSID.query.one().failCount == 0


def test_downgrade_restores_plaintext_passwords(file_app):
    from flask_migrate import downgrade
    upgrade_schema(file_app)
    db.session.execute(text(
        "INSERT INTO ssids (ssidName, ssidPW, siteID, ssidID) VALUES ('Home', 'enc', 's', 'abc')"))
    from app.crypto import encrypt
    db.session.execute(text("UPDATE ssids SET ssidPW = :v"), {"v": encrypt("secret")})
    db.session.commit()
    downgrade(revision="bfabed8737bc")
    assert db.session.execute(text("SELECT ssidPW FROM ssids")).scalar() == "secret"


def test_upgrade_is_repeatable(file_app):
    upgrade_schema(file_app)
    upgrade_schema(file_app)
    assert schema_diff() == []
