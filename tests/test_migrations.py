import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app import create_app, db
from app import upgrade_schema


@pytest.fixture
def file_app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'KeyShift.db'}",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
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


def test_existing_database_is_stamped_and_keeps_data(file_app):
    db.create_all()  # how every install before migrations was created
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
    assert db.session.execute(text("SELECT ssidPW FROM ssids")).scalar() == "pw"
    assert schema_diff() == []


def test_upgrade_is_repeatable(file_app):
    upgrade_schema(file_app)
    upgrade_schema(file_app)
    assert schema_diff() == []


def test_running_migrations_does_not_break_app_logging(file_app):
    import logging
    root = logging.getLogger()
    app_logger = logging.getLogger("app.routes.auth")
    handlers, level = list(root.handlers), root.level
    upgrade_schema(file_app)
    assert root.handlers == handlers and root.level == level
    assert app_logger.disabled is False
